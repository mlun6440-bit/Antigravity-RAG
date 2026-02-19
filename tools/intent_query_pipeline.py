#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Intent-Based Query Architecture
================================
Human Question → LLM (intent extraction) → Validated JSON Intent → Deterministic Engine → LLM (explanation)

This separates:
1. Language understanding (LLM) - handles ALL phrasing variations
2. Query execution (deterministic code) - 100% reliable
3. Result explanation (LLM) - human-readable output
"""

import os
import json
import sqlite3
import logging
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# STRICT JSON INTENT SCHEMAS (Simple validation)
# ============================================================================

VALID_ACTIONS = ['count', 'groupby', 'list', 'knowledge', 'error']
VALID_FIELDS = ['data_source', 'condition', 'criticality', 'asset_type', 'category', 'location']

def validate_intent(intent: Dict) -> Dict:
    """Validate intent structure."""
    if not isinstance(intent, dict):
        return {"action": "error", "error": "Intent must be a dictionary"}
    
    action = intent.get('action', 'error')
    if action not in VALID_ACTIONS:
        return {"action": "error", "error": f"Invalid action: {action}"}
    
    # Normalize filters
    if 'filters' in intent and intent['filters'] in [None, {}, []]:
        intent['filters'] = None
    
    return intent


# ============================================================================
# LLM INTENT EXTRACTOR
# ============================================================================

class IntentExtractor:
    """Extracts structured intent from natural language using LLM."""
    
    INTENT_PROMPT = '''You are an intent extraction system for an Asset Management database.
Convert the user's question into a STRICT JSON intent.

AVAILABLE ACTIONS:
1. "count" - Count assets (with optional filters)
2. "groupby" - Breakdown/group by a field  
3. "list" - List specific assets
4. "knowledge" - ISO 55000 or conceptual questions

DATABASE FIELDS (for filters/groupby):
- data_source: The source system (e.g., "Precise Fire", "Fulcrum")
- condition: Asset condition (e.g., "R1 Poor", "R4 Good")
- criticality: Criticality level (e.g., "Critical", "High", "Medium", "Low")
- asset_type: Type of asset
- category: Asset category
- location: Asset location

RULES:
1. Output ONLY valid JSON, no explanation
2. Use "count" with filters:null for total counts
3. Match field names exactly from the list above
4. For knowledge/ISO questions, use action:"knowledge"

EXAMPLES:
User: "How many total assets?"
{"action": "count", "filters": null}

User: "Count assets in poor condition"
{"action": "count", "filters": {"condition": "poor"}}

User: "How many Precise Fire assets are critical?"
{"action": "count", "filters": {"data_source": "Precise Fire", "criticality": "critical"}}

User: "Breakdown by criticality"
{"action": "groupby", "group_field": "criticality", "filters": null}

User: "What does ISO 55001 say about risk?"
{"action": "knowledge", "topic": "risk management", "source": "ISO 55001"}

User: "{query}"
'''

    def __init__(self, model_name: str = "gemini-2.0-flash"):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        logger.info(f"IntentExtractor initialized with {model_name}")
    
    def extract(self, query: str) -> Dict[str, Any]:
        """
        Extract structured intent from natural language query.
        
        Args:
            query: User's question in any phrasing
            
        Returns:
            Validated intent dictionary
        """
        # Use replace instead of format to avoid issues with JSON curly braces
        prompt = self.INTENT_PROMPT.replace("{query}", query)
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,
                    max_output_tokens=150
                )
            )
            
            # Parse JSON
            text = response.text.strip()
            if text.startswith('```'):
                text = text.split('```')[1]
                if text.startswith('json'):
                    text = text[4:]
            text = text.strip()
            
            intent = json.loads(text)
            
            # Validate using the simple function
            validated = validate_intent(intent)
            logger.info(f"Extracted intent: {validated}")
            return validated
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return {"action": "error", "error": "Failed to parse intent"}
        except Exception as e:
            logger.error(f"Intent extraction failed: {e}")
            return {"action": "error", "error": str(e)}


# ============================================================================
# DETERMINISTIC QUERY ENGINE
# ============================================================================

class DeterministicQueryEngine:
    """Executes intents deterministically - no LLM in the data path."""
    
    # Map user-friendly field values to database values
    VALUE_MAPPINGS = {
        'condition': {
            'poor': ['R1 Poor', 'Poor'],
            'fair': ['R2 Fair', 'Fair'],
            'average': ['R3 Average', 'Average'],
            'good': ['R4 Good', 'Good'],
        },
        'criticality': {
            'critical': ['Critical', 'CRITICAL'],
            'high': ['High', 'HIGH'],
            'medium': ['Medium', 'MEDIUM'],
            'low': ['Low', 'LOW'],
        }
    }
    
    def __init__(self, db_path: str = "data/assets.db"):
        self.db_path = db_path
        logger.info(f"DeterministicQueryEngine initialized with {db_path}")
    
    def execute(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute intent deterministically.
        
        Args:
            intent: Validated intent dictionary
            
        Returns:
            Result with data and metadata
        """
        action = intent.get('action')
        
        if action == 'error':
            return {'success': False, 'error': intent.get('error')}
        
        if action == 'count':
            return self._execute_count(intent)
        elif action == 'groupby':
            return self._execute_groupby(intent)
        elif action == 'list':
            return self._execute_list(intent)
        elif action == 'knowledge':
            return {'success': True, 'type': 'knowledge', 'data': intent}
        else:
            return {'success': False, 'error': f'Unknown action: {action}'}
    
    def _execute_count(self, intent: Dict) -> Dict:
        """Execute count query."""
        filters = intent.get('filters')
        
        if not filters:
            # Total count - no filters
            sql = "SELECT COUNT(*) as count FROM assets"
            params = []
        else:
            # Build WHERE clause
            where_parts = []
            params = []
            
            for field, value in filters.items():
                db_field = self._normalize_field(field)
                db_values = self._normalize_value(field, value)
                
                if len(db_values) == 1:
                    where_parts.append(f"{db_field} LIKE ?")
                    params.append(f"%{db_values[0]}%")
                else:
                    # OR multiple possible values
                    placeholders = " OR ".join([f"{db_field} LIKE ?" for _ in db_values])
                    where_parts.append(f"({placeholders})")
                    params.extend([f"%{v}%" for v in db_values])
            
            where_clause = " AND ".join(where_parts)
            sql = f"SELECT COUNT(*) as count FROM assets WHERE {where_clause}"
        
        return self._execute_sql(sql, params, 'count', intent)
    
    def _execute_groupby(self, intent: Dict) -> Dict:
        """Execute groupby query."""
        group_field = self._normalize_field(intent['group_field'])
        filters = intent.get('filters')
        
        if filters:
            where_parts = []
            params = []
            for field, value in filters.items():
                db_field = self._normalize_field(field)
                where_parts.append(f"{db_field} LIKE ?")
                params.append(f"%{value}%")
            where_clause = " WHERE " + " AND ".join(where_parts)
        else:
            where_clause = ""
            params = []
        
        sql = f"SELECT {group_field}, COUNT(*) as count FROM assets{where_clause} GROUP BY {group_field} ORDER BY count DESC"
        
        return self._execute_sql(sql, params, 'groupby', intent)
    
    def _execute_list(self, intent: Dict) -> Dict:
        """Execute list query."""
        filters = intent.get('filters')
        limit = intent.get('limit', 20)
        
        if filters:
            where_parts = []
            params = []
            for field, value in filters.items():
                db_field = self._normalize_field(field)
                where_parts.append(f"{db_field} LIKE ?")
                params.append(f"%{value}%")
            where_clause = " WHERE " + " AND ".join(where_parts)
        else:
            where_clause = ""
            params = []
        
        sql = f"SELECT * FROM assets{where_clause} LIMIT {limit}"
        
        return self._execute_sql(sql, params, 'list', intent)
    
    def _normalize_field(self, field: str) -> str:
        """Normalize field name to database column."""
        # Handle common variations
        mappings = {
            'source': 'data_source',
            'type': 'asset_type',
        }
        return mappings.get(field.lower(), field)
    
    def _normalize_value(self, field: str, value: str) -> List[str]:
        """Get possible database values for a user value."""
        field_lower = field.lower()
        value_lower = value.lower()
        
        if field_lower in self.VALUE_MAPPINGS:
            if value_lower in self.VALUE_MAPPINGS[field_lower]:
                return self.VALUE_MAPPINGS[field_lower][value_lower]
        
        return [value]
    
    def _execute_sql(self, sql: str, params: List, query_type: str, intent: Dict) -> Dict:
        """Execute SQL and return results."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            logger.info(f"Executing: {sql} with params {params}")
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            results = [dict(row) for row in rows]
            conn.close()
            
            return {
                'success': True,
                'type': query_type,
                'sql': sql,
                'results': results,
                'count': results[0]['count'] if query_type == 'count' and results else len(results),
                'intent': intent
            }
            
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            return {'success': False, 'error': str(e)}


# ============================================================================
# RESULT EXPLAINER (LLM for human-readable output)
# ============================================================================

class ResultExplainer:
    """Uses LLM to format results into human-readable responses."""
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        api_key = os.getenv('GEMINI_API_KEY')
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
    
    def explain(self, result: Dict[str, Any], original_question: str) -> str:
        """
        Format result into human-readable response.
        
        Args:
            result: Query result from DeterministicQueryEngine
            original_question: User's original question
            
        Returns:
            Human-readable answer
        """
        if not result.get('success'):
            return f"I couldn't process that query: {result.get('error', 'Unknown error')}"
        
        query_type = result.get('type')
        
        # For simple counts, don't need LLM
        if query_type == 'count':
            count = result.get('count', 0)
            intent = result.get('intent', {})
            filters = intent.get('filters')
            
            if not filters:
                return f"**{count:,}** total assets."
            else:
                filter_desc = " and ".join([f"{k}={v}" for k, v in filters.items()])
                return f"**{count:,}** assets matching {filter_desc}."
        
        # For complex results, use LLM to explain
        prompt = f"""Given this data result, provide a brief, clear answer to the user's question.

User's Question: "{original_question}"
Result Type: {query_type}
Data: {json.dumps(result.get('results', [])[:10], indent=2)}

Instructions:
- Be concise but complete
- Format numbers with commas
- Use markdown for emphasis
- Include a brief summary if showing a table
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except:
            # Fallback to raw results
            return f"Found {result.get('count', 0)} results."


# ============================================================================
# MAIN PIPELINE
# ============================================================================

class IntentBasedQueryPipeline:
    """
    Complete pipeline:
    Human Question → Intent → Deterministic Execution → Explanation
    """
    
    def __init__(self):
        self.intent_extractor = IntentExtractor()
        self.query_engine = DeterministicQueryEngine()
        self.explainer = ResultExplainer()
        logger.info("IntentBasedQueryPipeline initialized")
    
    def process(self, question: str) -> Dict[str, Any]:
        """
        Process a user question through the full pipeline.
        
        Args:
            question: User's natural language question
            
        Returns:
            Complete response with answer and metadata
        """
        # Step 1: Extract intent (LLM handles language variation)
        intent = self.intent_extractor.extract(question)
        
        # Step 2: Execute deterministically (no LLM unpredictability)
        result = self.query_engine.execute(intent)
        
        # Step 3: Format result for human (LLM for explanation only)
        answer = self.explainer.explain(result, question)
        
        return {
            'question': question,
            'intent': intent,
            'result': result,
            'answer': answer,
            'success': result.get('success', False)
        }


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("INTENT-BASED QUERY ARCHITECTURE TEST")
    print("="*70)
    
    pipeline = IntentBasedQueryPipeline()
    
    test_queries = [
        "How many total assets are in the register?",
        "How many assets do we have altogether?",
        "Count all assets",
        "What's the total number of assets?",
        "How many assets are in poor condition?",
        "Count critical assets from Precise Fire",
        "Breakdown by criticality",
    ]
    
    for q in test_queries:
        print(f"\n{'='*70}")
        print(f"QUESTION: {q}")
        print("-"*70)
        
        response = pipeline.process(q)
        
        print(f"INTENT: {response['intent']}")
        print(f"ANSWER: {response['answer']}")
        print(f"SUCCESS: {response['success']}")
