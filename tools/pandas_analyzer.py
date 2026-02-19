#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pandas Data Analyzer (Gemini Code Execution)
============================================
Allows the LLM to write and execute Pandas code to analyze the asset database.
Mimics the "Gemini in Sheets" analytical capability.
"""

import sqlite3
import pandas as pd
import logging
import re
import traceback
import sys
import io
import os
from typing import Dict, Any, Optional, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PandasAnalyzer:
    """
    Loads asset data into a DataFrame and lets Gemini write code to analyze it.
    """
    
    def __init__(self, db_path: str = "data/assets.db", model_name: str = "gemini-2.0-flash"):
        self.db_path = db_path
        self.model_name = model_name
        self.df = None
        
        # Initialize Gemini
        import google.generativeai as genai
        from dotenv import load_dotenv
        load_dotenv()
        self.model = None  # Always initialize to prevent AttributeError
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            logger.warning("GEMINI_API_KEY not found. PandasAnalyzer will fail to generate code.")
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
            
        # Load data on init (or lazy load)
        self._load_data()
        
    def _load_data(self):
        """Load assets table into memory."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Optimize: Only load columns if needed, but for now load all to give LLM full context
                self.df = pd.read_sql_query("SELECT * FROM assets", conn)
            logger.info(f"PandasAnalyzer loaded {len(self.df)} rows from {self.db_path}")
            
            # Clean up numeric columns that might be strings
            numeric_cols = ['current_age', 'useful_life', 'replacement_cost', 'risk_score', 'expected_life', 'remaining_life']
            for col in numeric_cols:
                if col in self.df.columns:
                    self.df[col] = pd.to_numeric(self.df[col], errors='coerce')

            # Auto-calculate remaining_life (in months) where missing
            # Formula: remaining_life = expected_life - months_since_install
            self._calculate_remaining_life()

        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            self.df = pd.DataFrame() # Empty fallback

    def _calculate_remaining_life(self):
        """Auto-calculate remaining_life in months where it is missing."""
        try:
            if 'install_date' not in self.df.columns or 'expected_life' not in self.df.columns:
                return

            from datetime import datetime
            today = pd.Timestamp.now()

            # Parse install_date
            self.df['install_date_parsed'] = pd.to_datetime(self.df['install_date'], dayfirst=True, errors='coerce')

            # Months since install
            self.df['_months_elapsed'] = (
                (today.year - self.df['install_date_parsed'].dt.year) * 12 +
                (today.month - self.df['install_date_parsed'].dt.month)
            )

            # Only fill remaining_life where it is currently null/zero AND expected_life is available
            mask = self.df['remaining_life'].isna() & self.df['expected_life'].notna() & self.df['install_date_parsed'].notna()
            self.df.loc[mask, 'remaining_life'] = (
                self.df.loc[mask, 'expected_life'] - self.df.loc[mask, '_months_elapsed']
            ).clip(lower=0)

            filled = mask.sum()
            logger.info(f"[PandasAnalyzer] Auto-calculated remaining_life for {filled} assets (in months)")

            # Clean up temp columns (only if they exist)
            temp_cols = [c for c in ['install_date_parsed', '_months_elapsed'] if c in self.df.columns]
            if temp_cols:
                self.df.drop(columns=temp_cols, inplace=True)

        except Exception as e:
            logger.error(f"[PandasAnalyzer] remaining_life calculation failed: {e}")

    def analyze(self, question: str) -> Dict[str, Any]:
        """
        Analyze the dataframe using LLM-generated Python code.
        """
        if self.df is None or self.df.empty:
            return {'error': 'No data available for analysis'}
            
        # 1. Proactive Discovery (New Step 0)
        # Verify search terms against actual data values BEFORE generating final code.
        evidence = self._perform_pre_analysis(question)
        if evidence:
            logger.info(f"[ANALYZER] Proactive Discovery found:\n{evidence}")
            
        # 2. Generate Python Code
        code = self._generate_code(question, evidence=evidence)
        if not code:
            return {'error': 'Failed to generate analysis code'}
            
        logger.info(f"[PandasAnalyzer] Generated code:\n{code}")
        
        # 3. Execute Code
        result = self._execute_code(code)
        
        # Add proactive discovery evidence to the result
        result['evidence'] = evidence
        
        # 5. Generate Widgets (Charts/Stat Cards)
        # Only generating widgets if we have a successful result with data
        if result.get('status') == 'success':
            try:
                # Use raw_result for accurate type checking (e.g. Stat Cards for scalars)
                raw_res = result.get('raw_result')
                result['widgets'] = self._generate_widgets(question, result.get('answer', ''), result=raw_res)
            except Exception as e:
                logger.error(f"[WIDGETS] Failed to generate widgets: {e}")
                result['widgets'] = []
        
        # Cleanup raw_result to avoid JSON serialization errors in Flask
        if 'raw_result' in result:
            del result['raw_result']
        
        
        # 4. Fallback Self-Correction
        if self._is_zero_result(result):
            logger.info("[ANALYZER] Zero result detected. Retrying with corrected code using real DB values...")
            corrected_code = self._generate_diagnostic_code(question, code)
            corrected_result = self._execute_code(corrected_code)

            if corrected_result.get('status') == 'success' and not self._is_zero_result(corrected_result):
                # Corrected code found results — use them
                result["answer"] = corrected_result["answer"]
                result["code"] = corrected_code
                result["status"] = "success"
            else:
                # Still 0 — report honestly
                result["answer"] = "0"
                result["status"] = "success"
        
        return result

    def _perform_pre_analysis(self, question: str) -> str:
        """
        Identify missing or blank values in key columns to aid analysis.
        Target Columns: Fulcrum ID, Condition Rating, Install Date, Asset Design Life, Manufacture Date
        """
        try:
            # 1. Map user-friendly names to actual DB columns
            # Using schema: asset_id, condition_score, install_date, expected_life
            column_map = {
                'Fulcrum ID': 'asset_id', 
                'Condition Rating': 'condition_score',
                'Install Date': 'install_date',
                'Asset Design Life': 'expected_life', 
                'Manufacture Date': 'manufacture_date', # Column may not exist in DB schema
                'Asset ID': 'asset_id' # Fallback
            }
            
            # 2. Determine which columns to check based on the question
            # If the user asks about "blanks", "missing", "incomplete", check ALL target columns
            # Otherwise, use the LLM to pick relevant ones (or just check all for robustness)
            
            # For this specific "missing values" insight, we'll check the target list if the question implies data quality
            is_data_quality_query = any(q in question.lower() for q in ['blank', 'missing', 'null', 'empty', 'incomplete', 'check', 'validate'])
            
            target_cols = []
            if is_data_quality_query:
                # Check all key columns defined in the map
                target_cols = list(column_map.keys())
            else:
                # Not a data quality query — skip blank/missing evidence to avoid noise
                return ""

            evidence_parts = []
            
            for friendly_name in target_cols:
                db_col = column_map[friendly_name]
                
                if db_col not in self.df.columns:
                    # Report missing column if it's critical
                    if friendly_name == 'Manufacture Date':
                         evidence_parts.append(f"Column '{friendly_name}' ({db_col}) does not exist in the database.")
                    continue
                
                # Count actual missing values (NaN/None)
                missing_count = self.df[db_col].isna().sum()
                
                # Count empty strings (if string type)
                empty_string_count = 0
                if pd.api.types.is_string_dtype(self.df[db_col]):
                    # Check for empty strings and whitespace-only strings
                    # Only check non-null values to avoid NaN->string 'nan' false negatives
                    non_null = self.df[db_col].dropna()
                    empty_string_count = (non_null.astype(str).str.strip() == '').sum()
                    
                    # Also check for explicit "null" strings if that's a concern, but user asked for "blanks"
                    # We can report them separately if needed, but grouping them as "potential missing" is often better
                    
                total_missing = missing_count + empty_string_count
                
                if total_missing > 0:
                    evidence_parts.append(f"Column '{friendly_name}' ({db_col}) has **{total_missing}** blank/missing entries.")
                else:
                    # Optional: confirm it's clean
                    # evidence_parts.append(f"Column '{friendly_name}' ({db_col}) is fully populated (no blanks).")
                    pass

            if not evidence_parts and is_data_quality_query:
                 return "Checked target columns (Fulcrum ID, Condition, etc.) and found NO blank or missing values."

            return "\n".join(evidence_parts)

        except Exception as e:
            logger.error(f"Pre-analysis failed: {e}")
            return ""

    def _is_zero_result(self, result: dict) -> bool:
        """Check if the result indicates 'nothing found'."""
        if result.get('status') == 'error': return False
        ans = str(result.get('answer', '')).lower()

        # 1. Exact matches
        if ans.strip() in ['0', 'none', 'no', 'false']: return True

        # 2. Key phrases
        if 'empty dataframe' in ans: return True
        if 'no assets found' in ans: return True
        if 'found 0 assets' in ans: return True

        # 3. Regex for "**0**" or " 0 assets"
        if re.search(r'\*\*0\*\*\s+assets', ans): return True
        if re.search(r'found\s+0\s+', ans): return True
        if re.search(r'returned\s+0\s+', ans): return True

        # 4. Pattern "Number of X: 0" or "X: 0" at end of line
        if re.search(r':\s*0\s*$', ans.strip()): return True
        if re.search(r':\s*0\b', ans): return True

        return False

    def _get_real_data_evidence(self, question: str) -> str:
        """
        Inspect actual DB values for category and condition to guide retry code generation.
        Returns a string listing real unique values — no LLM hallucination.
        """
        try:
            q = question.lower()
            parts = []

            # Always show real category values that match the question keywords
            category_keywords = ['hvac', 'fire', 'electrical', 'plumbing', 'structural',
                                  'building', 'mechanical', 'lift', 'elevator', 'security',
                                  'lighting', 'ground', 'furniture', 'it/', 'communication',
                                  'waste', 'specialist', 'transport']
            matched_cats = []
            for kw in category_keywords:
                if kw in q:
                    hits = self.df[self.df['category'].str.contains(kw, case=False, na=False)]['category'].unique()
                    matched_cats.extend(hits.tolist())

            if matched_cats:
                unique_cats = sorted(set(matched_cats))[:20]
                parts.append(f"Real category values matching the question: {unique_cats}")
            else:
                # Show top 20 most common categories
                top_cats = self.df['category'].dropna().value_counts().head(20).index.tolist()
                parts.append(f"Top category values in DB: {top_cats}")

            # Always show real condition values
            real_conditions = sorted(self.df['condition'].dropna().unique().tolist())
            parts.append(f"Real condition values in DB: {real_conditions}")

            return "\n".join(parts)
        except Exception as e:
            logger.error(f"_get_real_data_evidence failed: {e}")
            return ""

    def _generate_diagnostic_code(self, question: str, failed_code: str) -> str:
        """Ask LLM to write corrected code using REAL data values (not hallucinated ones)."""
        real_evidence = self._get_real_data_evidence(question)
        columns = list(self.df.columns)
        prompt = f"""You are a Python Data Analyst fixing a query that returned 0 results.

The user asked: "{question}"

The previous code returned 0. Here are the REAL values that exist in the database:
{real_evidence}

Using ONLY the real values above, write corrected Python code to answer the user's question.
- Use str.contains() with case=False, na=False for category
- Use exact == match for condition (with correct capitalisation from the real values above)
- Assign final result to variable `result`
- Output ONLY the Python code, no explanations.

DATAFRAME COLUMNS: {columns}
"""
        return self._get_llm_response(prompt)

    def _generate_code(self, question: str, evidence: str = "") -> str:
        """Prompt Gemini to write pandas code."""
        
        # Get schema info
        columns = list(self.df.columns)
        dtypes = str(self.df.dtypes)
        sample = str(self.df.head(3))
        
        evidence_context = ""
        if evidence:
            evidence_context = f"\n### REAL-TIME DATA EVIDENCE (Found in DB)\n{evidence}\n"

        prompt = f"""You are a Python Data Analyst.

STRICT GUARDRAIL:
1. You must ONLY write code to answer questions related to the Asset Register.
2. If the user asks about ANYTHING else (e.g. general knowledge, history, cooking), you must REFUSE by setting `result = "I can only assist with Asset Management inquiries."`.
3. Do not generate code for unrelated tasks.

        You have a pandas DataFrame named `df`.
        
### DATAFRAME INFO
Columns: {columns}
Data Types:
{dtypes}
Sample Data:
{sample}
{evidence_context}

### MANDATORY CATEGORY LOOKUP (copy-paste these filters exactly - DO NOT invent category names):
- HVAC / air con / mechanical / cooling / heating  -> df['category'].str.contains('HVAC & Refrigeration', case=False, na=False)
- Plumbing / water / hydraulic / toilet / drainage -> df['category'].str.contains('Plumbing', case=False, na=False)
- Electrical / lighting / switchboard / solar      -> df['category'].str.contains('Electrical Systems', case=False, na=False)
- Fire / sprinkler / extinguisher / EWIS           -> df['category'].str.contains('Fire Systems', case=False, na=False)
- Building / structural / fabric / roofing / doors -> df['category'].str.contains('Building Structural', case=False, na=False)
- Security / CCTV / access control / alarm         -> df['category'].str.contains('Security Systems', case=False, na=False)
- Transport / lift / elevator                      -> df['category'].str.contains('Transportation', case=False, na=False)
- Grounds / garden / playground                    -> df['category'].str.contains('Grounds', case=False, na=False)
- Furniture / fittings / lockers                   -> df['category'].str.contains('Furniture Fittings', case=False, na=False)
- Specialist / fuel / medical / school             -> df['category'].str.contains('Specialist Equipment', case=False, na=False)
- IT / BMS / AV / server / intercom                -> df['category'].str.contains('IT/Communication', case=False, na=False)
- Waste / cleaning / pest                          -> df['category'].str.contains('Waste Cleaning', case=False, na=False)

### MANDATORY CONDITION FILTER (use exact match, capital first letter):
- Poor condition   -> df['condition'] == 'Poor'
- Fair condition   -> df['condition'] == 'Fair'
- Good condition   -> df['condition'] == 'Good'
- Very Good        -> df['condition'] == 'Very Good'
- Unknown          -> df['condition'] == 'Unknown'
NEVER use str.contains for condition - always use == with exact capitalisation.

### IMPORTANT RULES
1. ALWAYS use `df['column_name']` syntax - never bare column names.
2. If 'REAL-TIME DATA EVIDENCE' is provided above, PRIORITIZE those exact values in your filters.
3. Use `str.contains(..., case=False, na=False)` for category/location/name columns.
4. Assign final result to variable `result`.

### DOMAIN KNOWLEDGE (Asset Categories & Synonyms)
CRITICAL: The `category` column uses the format "Parent Category,Subcategory". Always use `str.contains` with the EXACT parent category name shown below (case-insensitive).

COMPLETE LIST OF PARENT CATEGORIES (use these exact strings in str.contains):
1.  **Building Structural & Fabric** → `df['category'].str.contains('Building Structural', case=False, na=False)`
    Subcategories: Automatic Doors, Ceiling, Disabled Access, Door Closer - Manual, Door Lock, Doors & Door Hardware, External Paint, Facade, Fire/Smoke/Exit Door, Flooring, Guttering, Height Safety, Manual Swing Door, Other, Paintwork, Roller Doors, Roofing, Security Barriers & Structures, Signage & Livery (Non-Powered), Signage & Livery (Powered), Stairs & Ramps, Wall Finishes-Paint, Walls, Window Shades & Furnishings, Windows

2.  **Communication Systems** → `df['category'].str.contains('Communication Systems', case=False, na=False)`
    Subcategories: BMS Field Equipment

3.  **Electrical Systems** → `df['category'].str.contains('Electrical Systems', case=False, na=False)`
    Subcategories: Battery Chargers, Distribution Board, Elec Outlets & Circuits, Electrical Distribution, Electrical Switches & Outlets, Electrical Transformer, Electricity Meter, Emergency & Exit Lighting, Emergency Power Generation, Lighting, Lightning Protection, Main Switchboard, Mechanical Switchboard, Other, Power Factor Correction, Residual Current Device, Solar Power, Switchgear, UPS

4.  **Fire Systems** → `df['category'].str.contains('Fire Systems', case=False, na=False)`
    Subcategories: EWIS, Fire Alarm System, Fire Blanket, Fire Dampers, Fire Detection, Fire Extinguisher, Fire Hydrants & Hose Reels, Fire Pumps, Fire Sprinkler System, Other
    User terms: "fire", "sprinkler", "extinguisher", "EWIS", "fire alarm", "fire pump", "fire hydrant"

5.  **Furniture Fittings & Equipment** → `df['category'].str.contains('Furniture Fittings', case=False, na=False)`
    Subcategories: Barbeque, Bathroom Fittings, Benches/Tables, Clothes Dryer, Dishwasher, First Aid Equipment, Freezer, Hand Dryers, Kitchen Fittings, Lockers, Microwave, Office Equipment, Office Storage, Other, Paper Towel Dispenser, Refrigerator, Seating, Shelving & Racking, Toilet Roll Holders, Washing Machine, Whiteboards & Blackboards

6.  **Grounds & Gardens** → `df['category'].str.contains('Grounds', case=False, na=False)`
    Subcategories: Bike Storage, Flags & Monuments, Gardening Equipment, Gates & Fences, Indoor Plants, Landscaping, Linemarking, Outdoor Structures, Playground, Pools Spa & Sauna, Roads & Hardstands, Sports/Gym Equipment

7.  **HVAC & Refrigeration** → `df['category'].str.contains('HVAC & Refrigeration', case=False, na=False)`
    Subcategories: Air Curtains, Air Handling Units, Boilers, Ceiling Fan, Chemical Dosing, Chillers, Compressor, Condensor, Cool Room, Cooling Towers, Duct, Evaporative Cooling, Fans, HVAC Control, HVAC Equipment, HVAC Pumps, Heaters, Other, Packaged AC, Portable AC, Split AC, VRV System, Variable Speed Drive, Window/Wall Box AC
    User terms: "HVAC", "air conditioning", "AC", "heating", "cooling", "chiller", "boiler", "air handler", "mechanical"

8.  **IT/Communication Systems** → `df['category'].str.contains('IT/Communication', case=False, na=False)`
    Subcategories: AV Equipment, BMS, Desktop PC, Intercom, Radio Equipment, Server Equipment, Telephone Equipment

9.  **Plumbing Systems** → `df['category'].str.contains('Plumbing', case=False, na=False)`
    Subcategories: Domestic Water Pump, Emergency Shower/Eyewash, Floor Drain, Gas Supply, Grease Trap, Hot Water Service, Irrigation Systems, Other, Sewage System, Sewage Treatment, Shower, Sink/Basin, Stormwater Systems, Tapware & Sanitaryware, Toilet, Urinal, Water Boiling/Cooling Unit, Water Features, Water Meter, Water Reticulation, Water Tanks, Water Treatment, Water Valves
    User terms: "plumbing", "hydraulic", "water", "sewage", "drainage", "hot water", "toilet", "sink", "urinal"

10. **Security Systems** → `df['category'].str.contains('Security Systems', case=False, na=False)`
    Subcategories: Access Control, Alarm Monitoring, Alarm Zone, CCTV Camera, CCTV System, Duress System, Entry Detection Systems, Intruder Alarm System, Other, Secure Storage

11. **Specialist Equipment** → `df['category'].str.contains('Specialist Equipment', case=False, na=False)`
    Subcategories: Car Wash, Fuel/Oil Pumps, Fuel/Oil System Controls, Fuel/Oil Tanks, Kitchen Equipment, Ladder, Medical & Laboratory Equipment, Retail Furniture & Equipment, School Equipment, Vehicle Maintenance, Warehouse/Packing Equipment

12. **Transportation Systems** → `df['category'].str.contains('Transportation', case=False, na=False)`
    Subcategories: Dumb Waiters, Lifts
    User terms: "lift", "elevator", "vertical transport", "dumb waiter"

13. **Waste Cleaning & Pest Control** → `df['category'].str.contains('Waste Cleaning', case=False, na=False)`
    Subcategories: Cleaning Equipment, Pest Control, Sharps Bin, Waste Bins

CONDITION values in DB are exactly: 'Poor', 'Fair', 'Good', 'Very Good', 'Unknown' (capital first letter).
Always filter condition with: `df['condition'] == 'Poor'` (exact match with capital P).

### COLUMN DEFINITIONS & MAPPING
- **"Fulcrum ID"**: Map to `asset_id` column (UUID format).
- **"Condition"**: User might ask for "Condition" or "Rating". Use `condition_score` (1=Excellent, 5=Very Poor) OR `condition` (Text description).
- **"Install Date"**: Map to `install_date`.
- **"Design Life"**: Map to `expected_life` (years).
- **"Data Source"**: Map to `data_source`.
- **"Manufacturer"**: Information may be in `notes` or `tags`. No dedicated column.
- **"Location"**: Use `location`, `building`, `floor`, or `room` columns.
- **"Asset Description"**: Map to `asset_name` or `asset_type`.
- **"Criticality"**: Use `criticality` column (Values: 'Critical', 'High', 'Medium', 'Low').
- **"Replacement Cost"**: Map to `replacement_cost` (Currency).
- **"Maintenance Cost"**: Map to `annual_maintenance_cost`.
- **"Remaining Life"**: Map to `remaining_life` (years).
- **"Age"**: Map to `current_age` (years).
- **"Next Service"**: Map to `next_maintenance_date` or `next_inspection_date`.
- **"Compliance"**: Map to `compliance_standard`.

### TASK
Write Python code to answer this question: "{question}"

### RULES
1. ALWAYS use `df['column_name']` syntax - NEVER use bare column names like `category` or `condition`.
2. The DataFrame is named `df` and is already loaded - do NOT redefine it.
3. Perform necessary filtering, aggregation, or calculation.
4. **CRITICAL**: Assign your final answer (string, number, or dataframe) to a variable named `result`.
5. If the result is a DataFrame, use `result = result_df.to_html(index=False, classes='data-table')`. DataFrames MUST be returned as HTML tables.
6. Handle case-insensitivity for string matches (use `df['col'].str.contains(..., case=False, na=False)`).
7. Do NOT plot charts, just return data/text.
8. Return ONLY the python code, no markdown backticks.
9. CORRECT: `df[df['category'].str.contains('HVAC')]` — WRONG: `df[category.str.contains('HVAC')]`

### QUESTION
{question}

### PYTHON CODE
"""
        return self._get_llm_response(prompt)

    def _get_llm_response(self, prompt: str) -> str:
        """Helper to call Gemini and clean code output."""
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={'temperature': 0.0}
            )
            text = response.text.strip()
            
            # Robust code extraction using regex
            # 1. Look for ```python ... ```
            match = re.search(r'```python\s*(.*?)```', text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
            
            # 2. Look for generic ``` ... ```
            match = re.search(r'```\s*(.*?)```', text, re.DOTALL)
            if match:
                return match.group(1).strip()
            
            # 3. Fallback: Assume the whole text is code if no backticks found (risky but sometimes needed)
            # But usually Gemini wraps in backticks. If it didn't, it might be chatty.
            # Let's try to strip lines starting with non-code? No, too complex. 
            # If no backticks, just return as is, but log it.
            logger.warning("[PandasAnalyzer] No code blocks found in response. Returning raw text.")
            return text
            
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            return ""

    def _execute_code(self, code: str) -> Dict[str, Any]:
        """Execute the code in a restricted environment."""
        
        # Capture stdout
        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output
        
        # Execution context
        local_scope = {
            'df': self.df, 
            'pd': pd,
            'result': None
        }
        
        status = 'success'
        error_msg = None
        
        try:
            # Dangerous! Only distinct internal usage.
            exec(code, {}, local_scope)
            
            result = local_scope.get('result')
            # If result is not set, maybe they printed it?
            output = redirected_output.getvalue()
            
            if result is None and output:
                result = output.strip()
            if result is None:
                result = "Code executed but no `result` variable was set."
                
        except Exception as e:
            status = 'error'
            error_msg = str(e)
            result = traceback.format_exc()
            logger.error(f"Code execution error: {e}")
            
        finally:
            sys.stdout = old_stdout
            
        return {
            'status': status,
            'code': code,
            'answer': str(result),
            'raw_result': result, # Pass raw object for widget generation (removed before JSON)
            'error': error_msg,
            'output': redirected_output.getvalue()
        }

    def _judge_visualization_need(self, question: str, answer: str) -> str:
        """
        Ask Gemini if this answer NEEDS a visualization.
        Returns: 'bar_chart', 'pie_chart', 'stat_card', or 'none'
        """
        if not self.model: return 'none'
        
        try:
            prompt = f"""You are a UI UX expert. Decide if this answer warrants a visualization.
            
            Q: {question}
            A: {answer[:1500]}
            
            Rules:
            1. "stat_card": Single calculated number, count, or KPI (e.g. "Total calculated is 50", "Found 5 assets").
            2. "bar_chart": Comparison of categories (e.g. counts by building, cost by type).
            3. "pie_chart": Proportional breakdown (e.g. status distribution, percentage split).
            4. "none": Simple text lists, descriptions, tabular data with too many rows (>10), or direct lookups without aggregation.
            
            Return ONLY the one keyword: stat_card, bar_chart, pie_chart, or none.
            """
            response = self.model.generate_content(prompt)
            decision = response.text.strip().lower()
            
            # Sanitize response
            if 'stat_card' in decision: return 'stat_card'
            if 'pie' in decision: return 'pie_chart'
            if 'bar' in decision: return 'bar_chart'
            
            return 'none'
        except Exception as e:
            logger.error(f"[JUDGE] Visualization decision failed: {e}")
            return 'none' # Fail safe to clean UI

    def _generate_widgets(self, question: str, answer: str, result: Any = None) -> List[Dict[str, Any]]:
        """
        Generate UI widgets based on the analysis result.
        Uses _judge_visualization_need to decide, then regex/scalar logic to extract.
        """
        # 0. Smart Decision: Ask LLM if visualization is needed
        try:
            decision = self._judge_visualization_need(question, answer)
            logger.info(f"[WIDGETS] Judge decision: {decision}")
        except Exception:
            decision = 'none' # Fallback
            
        if decision == 'none':
            return []

        widgets = []
        q_lower = question.lower()
        
        # 1. Stat Cards (Single Numbers)
        if decision == 'stat_card':
            # Check scalar result directly (most reliable)
            try:
                if result is not None and isinstance(result, (int, float, np.integer, np.floating)):
                    widgets.append({
                        'type': 'stat_card',
                        'title': f'Analysis: {question}',
                        'data': {
                            'label': 'Count' if 'count' in q_lower else 'Result',
                            'value': str(result),
                            'trend': 'neutral'
                        }
                    })
                    return widgets
            except Exception:
                pass

            # Look for markdown patterns like "**123** assets"
            import re
            number_match = re.search(r'\*\*([0-9,.]+)\*\* (assets|items|records|total)', answer, re.IGNORECASE)
            if number_match:
                count = number_match.group(1)
                label = number_match.group(2).title()
                widgets.append({
                    'type': 'stat_card',
                    'title': f'Total {label}',
                    'value': count,
                    'status': 'success'
                })
            return widgets

        # 2. Charts (Bar/Pie)
        if decision in ['bar_chart', 'pie_chart']:
            chart_type = decision
            
            # Extract table data from markdown for the chart
            import re
            rows_3col = re.findall(r'\|\s*[^\|]+\s*\|\s*([^\|]+)\s*\|\s*([0-9,]+)\s*\|', answer)
            rows_2col = re.findall(r'\|\s*([^\|]+)\s*\|\s*([0-9,]+)\s*\|', answer)
            
            clean_rows = []
            candidate_rows = rows_3col if len(rows_3col) > 0 else rows_2col

            if len(candidate_rows) > 0:
                for row in candidate_rows:
                    label_text, val_str = row[0].strip(), row[1].strip()
                    if '---' in label_text or '---' in val_str: continue
                    if label_text.lower() in ['count', 'value', 'total']: continue

                    try:
                        val = int(val_str.replace(',', ''))
                        clean_rows.append({'label': label_text, 'value': val})
                    except ValueError:
                        continue

                # If we extracted valid data rows, generate the widget
                if len(clean_rows) >= 1: 
                    widgets.append({
                        'type': chart_type,
                        'title': f'Analysis: {question}',
                        'data': {
                            'labels': [r['label'] for r in clean_rows],
                            'datasets': [{
                                'label': 'Count',
                                'data': [r['value'] for r in clean_rows],
                                'backgroundColor': ['#667eea', '#764ba2', '#ff9800', '#4caf50', '#f44336'] * 3
                            }]
                        }
                    })
            return widgets
            
        return []

if __name__ == "__main__":
    # Test
    analyzer = PandasAnalyzer()
    q = "Count assets with 'DB' or 'Switchboard' in description"
    print(f"Analyzing: {q}")
    res = analyzer.analyze(q)
    print("\nResult:")
    print(res['answer'])
