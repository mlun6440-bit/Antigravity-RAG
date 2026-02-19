#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analytical Query Handler
Combines SQL filtering with LLM analysis and ISO standards guidance.
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional
import json


class AnalyticalQueryHandler:
    """
    Handles analytical queries requiring SQL + LLM + ISO guidance.
    
    Pipeline: SQL Filtering → Context Assembly → LLM Analysis → Citations
    """
    
    def __init__(self, db_path: str, gemini_model, iso_embedding_manager=None):
        """
        Initialize analytical handler.
        
        Args:
            db_path: Path to SQLite database
            gemini_model: Gemini model instance
            iso_embedding_manager: ISO embedding manager for semantic search
        """
        self.db_path = Path(db_path)
        self.model = gemini_model
        self.iso_embedding_manager = iso_embedding_manager
        
        # Connection will be created per-query for thread safety
        self.conn = None
    
    def process_query(self, question: str, iso_kb_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Process analytical query end-to-end.
        
        Args:
            question: User question
            iso_kb_file: Path to ISO knowledge base JSON
            
        Returns:
            Query result with SQL data + LLM analysis + citations
        """
        print(f"\n[ANALYTICAL] Processing: {question}")
        
        try:
            # Step 1: Extract filters from question
            filters = self.extract_filters(question)
            print(f"[ANALYTICAL] Extracted filters: {filters}")
            
            if not filters:
                # No filters found - fallback to knowledge query
                return {
                    'status': 'fallback',
                    'reason': 'No data filters detected'
                }
            
            # Step 2: Execute SQL SELECT to get assets
            assets_df = self.execute_sql_select(filters)
            print(f"[ANALYTICAL] Retrieved {len(assets_df)} assets")
            
            if len(assets_df) == 0:
                return {
                    'question': question,
                    'answer': "No assets found matching your criteria.",
                    'citations': [],
                    'model': 'Analytical (No Results)',
                    'context_size': 0,
                    'citation_count': 0,
                    'status': 'success'
                }
            
            # Step 3: Build analytical context
            context = self.build_analytical_context(assets_df, question, iso_kb_file)
            print(f"[ANALYTICAL] Built context: ~{len(context)} chars")
            
            # Step 4: Create specialized prompt
            prompt = self.create_analytical_prompt(context, question)
            
            # Step 5: Query Gemini
            print(f"[ANALYTICAL] Querying Gemini...")
            response = self.model.generate_content(prompt)
            answer = response.text
            
            # Step 6: Format result with citations
            result = self._format_result(
                question=question,
                answer=answer,
                assets_df=assets_df,
                filters=filters,
                context=context
            )
            
            return result
            
        except Exception as e:
            print(f"[ERROR] Analytical query failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def extract_filters(self, question: str) -> Dict[str, Any]:
        """
        Extract data filters from question.
        
        Args:
            question: User question
            
        Returns:
            Dictionary of field:value filters
        """
        filters = {}
        q_lower = question.lower()
        
        # Condition filters
        condition_map = {
            'poor': 'Poor',
            'fair': 'Fair', 
            'good': 'Good',
            'excellent': 'Very Good',
            'very good': 'Very Good'
        }
        for keyword, db_value in condition_map.items():
            if keyword in q_lower:
                filters['condition'] = db_value
                break
        
        # Criticality filters
        criticality_map = {
            'critical': 'Critical',
            'high': 'High',
            'medium': 'Medium',
            'low': 'Low'
        }
        for keyword, db_value in criticality_map.items():
            if keyword in q_lower:
                filters['criticality'] = db_value
                break
        
        # Asset type filters
        type_keywords = {
            'electrical': 'Electrical',
            'fire': 'Fire',
            'hvac': 'HVAC',
            'plumbing': 'Plumbing',
            'mechanical': 'Mechanical'
        }
        for keyword, db_value in type_keywords.items():
            if keyword in q_lower:
                filters['category'] = db_value
                break
        
        # Age filter (e.g., "over 20 years old")
        import re
        age_match = re.search(r'over (\d+) years? old', q_lower)
        if age_match:
            filters['age_gt'] = int(age_match.group(1))
        
        return filters
    
    def execute_sql_select(self, filters: Dict[str, Any], limit: int = 100) -> pd.DataFrame:
        """
        Execute SQL SELECT with filters.
        
        Args:
            filters: Field:value filters
            limit: Max records to return
            
        Returns:
            DataFrame with asset records
        """
        conn = sqlite3.connect(self.db_path)
        
        where_clauses = []
        params = []
        
        for field, value in filters.items():
            if field == 'age_gt':
                where_clauses.append("current_age > ?")
                params.append(value)
            else:
                # Handle LIKE for partial matches
                if field == 'category':
                    where_clauses.append(f"{field} LIKE ?")
                    params.append(f"%{value}%")
                else:
                    where_clauses.append(f"{field} = ?")
                    params.append(value)
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Select key columns for analysis
        columns = [
            'asset_id', 'asset_name', 'category', 'location',
            'condition', 'criticality', 'current_age', 'useful_life',
            'replacement_cost', 'data_source'
        ]
        
        sql = f"""
        SELECT {', '.join(columns)}
        FROM assets
        WHERE {where_sql}
        ORDER BY 
            CASE criticality
                WHEN 'Critical' THEN 1
                WHEN 'High' THEN 2
                WHEN 'Medium' THEN 3
                ELSE 4
            END,
            current_age DESC
        LIMIT ?
        """
        params.append(limit)
        
        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()
        
        return df
    
    def build_analytical_context(self, assets_df: pd.DataFrame, question: str, 
                                 iso_kb_file: Optional[str]) -> str:
        """
        Build rich context using Vector DB Expert patterns.
        
        Args:
            assets_df: Asset data from SQL
            question: User question
            iso_kb_file: Path to ISO KB
            
        Returns:
            Assembled context string
        """
        context_parts = []
        
        # === START: Critical Info ===
        
        # SQL Summary
        summary = self._create_sql_summary(assets_df)
        context_parts.append("# SQL DATA SUMMARY\n" + summary)
        
        # ISO Chunks (top 3 via semantic search)
        if self.iso_embedding_manager and iso_kb_file:
            iso_chunks = self._retrieve_iso_chunks(question, iso_kb_file, top_k=3)
            if iso_chunks:
                context_parts.append("\n# ISO STANDARDS GUIDANCE\n" + iso_chunks)
        
        # === MIDDLE: Supporting Data ===
        
        # Asset table (top 10-20)
        asset_table = self._create_asset_table(assets_df.head(15))
        context_parts.append("\n# SAMPLE ASSETS (Top 15)\n" + asset_table)
        
        # === END: Reinforcement ===
        
        # Additional context if needed
        if len(assets_df) > 15:
            context_parts.append(f"\n_Note: Showing 15 of {len(assets_df)} total assets_")
        
        return "\n".join(context_parts)
    
    def _create_sql_summary(self, df: pd.DataFrame) -> str:
        """Create SQL summary with breakdowns."""
        lines = []
        lines.append(f"**Total Assets**: {len(df)}\n")
        
        # Breakdown by criticality
        if 'criticality' in df.columns:
            crit_counts = df['criticality'].value_counts()
            lines.append("**Breakdown by Criticality**:")
            for crit, count in crit_counts.items():
                pct = (count / len(df)) * 100
                lines.append(f"- {crit}: {count} ({pct:.0f}%)")
        
        # Breakdown by condition
        if 'condition' in df.columns:
            cond_counts = df['condition'].value_counts()
            lines.append("\n**Breakdown by Condition**:")
            for cond, count in cond_counts.items():
                pct = (count / len(df)) * 100
                lines.append(f"- {cond}: {count} ({pct:.0f}%)")
        
        # Average age
        if 'current_age' in df.columns:
            avg_age = df['current_age'].mean()
            lines.append(f"\n**Average Age**: {avg_age:.1f} years")
        
        return "\n".join(lines)
    
    def _create_asset_table(self, df: pd.DataFrame) -> str:
        """Create markdown table of assets."""
        if len(df) == 0:
            return "_No assets to display_"
        
        # Select key columns
        display_cols = ['asset_id', 'asset_name', 'category', 'condition', 
                       'criticality', 'current_age', 'location']
        display_cols = [c for c in display_cols if c in df.columns]
        
        return df[display_cols].to_markdown(index=False)
    
    def _retrieve_iso_chunks(self, question: str, iso_kb_file: str, top_k: int = 3) -> str:
        """Retrieve relevant ISO chunks via semantic search."""
        try:
            # Load ISO KB
            with open(iso_kb_file, 'r', encoding='utf-8') as f:
                iso_kb = json.load(f)
            
            # Extract analytical intent for better retrieval
            analytical_terms = [
                'risk assessment', 'maintenance planning', 'asset lifecycle',
                'compliance requirements', 'condition monitoring'
            ]
            
            # Use embedding manager if available
            if self.iso_embedding_manager:
                results = self.iso_embedding_manager.search(question, top_k=top_k)
                chunks = []
                for result in results:
                    chunks.append(f"**{result.get('source', 'ISO')}** (Score: {result.get('score', 0):.2f})")
                    chunks.append(result.get('text', ''))
                return "\n\n".join(chunks)
            else:
                # Fallback: keyword search
                chunks = iso_kb.get('chunks', [])[:top_k]
                return "\n\n".join([c.get('text', '') for c in chunks])
                
        except Exception as e:
            print(f"[WARN] ISO retrieval failed: {e}")
            return ""
    
    def create_analytical_prompt(self, context: str, question: str) -> str:
        """
        Create specialized analytical prompt.
        
        Args:
            context: Assembled context
            question: User question
            
        Returns:
            Complete prompt string
        """
        return f"""You are an asset management expert analyzing real asset data against ISO 55000 standards.

=== CONTEXT ===
{context}

=== QUESTION ===
{question}

=== INSTRUCTIONS ===
Provide a comprehensive analysis including:

1. **Summary**: Quick overview with exact count and key findings
2. **Risk Assessment**: Based on ISO 55001 framework, identify risks
3. **Breakdown**: Analyze the data by criticality, condition, or other relevant dimensions
4. **Recommendations**: Specific, actionable recommendations prioritizing:
   - Critical assets (immediate attention)
   - High-risk assets (short-term planning)
   - Medium/Low (include in maintenance cycles)
5. **ISO Compliance**: Reference specific ISO standards and sections
6. **Sample Assets**: Highlight top assets requiring attention

Format your response in clear markdown with headers and bullet points.
Base all recommendations on the ACTUAL ASSET DATA provided above.
"""
    
    def _format_result(self, question: str, answer: str, assets_df: pd.DataFrame,
                      filters: Dict[str, Any], context: str) -> Dict[str, Any]:
        """Format result with proper citations."""
        
        # Build filter description
        filter_parts = []
        for field, value in filters.items():
            if field == 'age_gt':
                filter_parts.append(f"Age > {value} years")
            else:
                filter_parts.append(f"{field}='{value}'")
        filter_desc = " AND ".join(filter_parts)
        
        # Create citations
        citations = [
            {
                'number': 1,
                'type': 'asset_data',
                'source_file': 'Asset Database (SQLite)',
                'sheet_name': 'assets',
                'field': 'Multiple fields',
                'filter': f"Analytical query: {filter_desc}",
                'count': len(assets_df),
                'asset_ids': assets_df['asset_id'].tolist()[:10] if 'asset_id' in assets_df.columns else [],
                'spreadsheet_url': None
            }
        ]
        
        # Add ISO citation if ISO content was used
        if 'ISO STANDARDS' in context:
            citations.append({
                'number': 2,
                'type': 'iso_standard',
                'source_file': 'ISO 55000 Knowledge Base',
                'section': 'Multiple sections',
                'relevance': 'High',
                'url': None
            })
        
        return {
            'question': question,
            'answer': answer,
            'citations': citations,
            'model': 'Analytical (SQL + LLM)',
            'context_size': len(context),
            'citation_count': len(citations),
            'status': 'success',
            'sql_count': len(assets_df),
            'query_type': 'analytical',
            'filters': filters
        }
