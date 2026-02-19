#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM SQL Generator
Uses Gemini to convert natural language queries to SQL, handling any phrasing variation.
This replaces brittle pattern matching with LLM-based intent understanding.
"""

import os
import json
import sqlite3
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LLMSQLGenerator:
    """LLM-powered SQL query generator for natural language queries."""
    
    def __init__(self, db_path: str = "data/assets.db", model_name: str = "gemini-2.0-flash-exp"):
        """
        Initialize the SQL generator.
        
        Args:
            db_path: Path to SQLite database
            model_name: Gemini model to use
        """
        self.db_path = db_path
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)
        
        # Load schema for context
        self.schema = self._load_schema()
        logger.info(f"LLMSQLGenerator initialized with {len(self.schema)} columns")
    
    def _load_schema(self) -> Dict[str, str]:
        """Load database schema for SQL generation context."""
        schema = {}
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("PRAGMA table_info(assets)")
            for col in cursor.fetchall():
                schema[col[1]] = col[2]  # column_name: data_type
            conn.close()
        except Exception as e:
            logger.error(f"Failed to load schema: {e}")
        return schema
    
    def generate_sql(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Convert natural language query to SQL using LLM.
        
        Args:
            query: Natural language question
            
        Returns:
            Dictionary with sql, params, type, and description
        """
        # Build schema description for prompt
        schema_desc = "Table: assets\nColumns:\n"
        for col, dtype in list(self.schema.items())[:30]:  # Top 30 columns for context
            schema_desc += f"  - {col} ({dtype})\n"
        
        # Sample some distinct values for key columns
        sample_values = self._get_sample_values()
        
        prompt = f"""You are an expert SQL query generator for an asset management database.

DATABASE SCHEMA:
{schema_desc}

SAMPLE VALUES (for understanding field contents):
{sample_values}

USER QUESTION: "{query}"

TASK: Generate a SQLite query to answer this question.

RULES:
1. Output ONLY valid JSON (no explanation, no markdown)
2. JSON format:
   {{"sql": "SELECT ...", "type": "count|list|groupby", "description": "brief description"}}
3. For count queries, use COUNT(*)
4. For groupby queries, use GROUP BY with ORDER BY count DESC
5. Use LIKE '%value%' for fuzzy text matching
6. Limit list queries to 100 rows

EXAMPLES:
- "How many total assets?" -> {{"sql": "SELECT COUNT(*) as count FROM assets", "type": "count", "description": "Total count of all assets"}}
- "How many poor condition assets?" -> {{"sql": "SELECT COUNT(*) as count FROM assets WHERE condition LIKE '%poor%'", "type": "count", "description": "Count of assets in poor condition"}}
- "Breakdown by criticality" -> {{"sql": "SELECT criticality, COUNT(*) as count FROM assets GROUP BY criticality ORDER BY count DESC", "type": "groupby", "description": "Assets grouped by criticality"}}

JSON OUTPUT:"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,
                    max_output_tokens=200
                )
            )
            
            # Parse JSON response
            text = response.text.strip()
            # Clean markdown if present
            if text.startswith('```'):
                text = text.split('```')[1]
                if text.startswith('json'):
                    text = text[4:]
            text = text.strip()
            
            result = json.loads(text)
            result['params'] = []  # LLM generates complete SQL, no params needed
            
            logger.info(f"Generated SQL: {result['sql']}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return None
        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            return None
    
    def _get_sample_values(self) -> str:
        """Get sample distinct values for key columns."""
        samples = {}
        key_cols = ['data_source', 'condition', 'criticality', 'asset_type', 'category']
        
        try:
            conn = sqlite3.connect(self.db_path)
            for col in key_cols:
                if col in self.schema:
                    cursor = conn.execute(f"SELECT DISTINCT {col} FROM assets LIMIT 5")
                    values = [row[0] for row in cursor.fetchall() if row[0]]
                    samples[col] = values[:5]
            conn.close()
        except:
            pass
        
        return "\n".join([f"{k}: {v}" for k, v in samples.items()])
    
    def execute(self, sql_query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the generated SQL query.
        
        Args:
            sql_query: Output from generate_sql()
            
        Returns:
            Dictionary with results and metadata
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(sql_query['sql'], sql_query.get('params', []))
            rows = cursor.fetchall()
            
            results = [dict(row) for row in rows]
            conn.close()
            
            return {
                'success': True,
                'results': results,
                'count': len(results),
                'sql': sql_query['sql'],
                'type': sql_query['type'],
                'description': sql_query['description']
            }
            
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': []
            }


if __name__ == "__main__":
    # Test the LLM SQL generator
    generator = LLMSQLGenerator()
    
    test_queries = [
        "How many total assets are in the register?",
        "Count all the assets",
        "What's the total number of assets we have?",
        "How many assets in poor condition?",
        "Show me the breakdown by criticality",
        "How many Precise Fire assets are there?",
    ]
    
    print("="*60)
    print("TESTING LLM SQL GENERATOR")
    print("="*60)
    
    for q in test_queries:
        print(f"\nQuery: '{q}'")
        sql_query = generator.generate_sql(q)
        if sql_query:
            print(f"SQL: {sql_query['sql']}")
            result = generator.execute(sql_query)
            if result['success']:
                if sql_query['type'] == 'count':
                    print(f"Result: {result['results'][0].get('count', 0)}")
                else:
                    print(f"Results: {len(result['results'])} rows")
            else:
                print(f"Error: {result['error']}")
        else:
            print("Failed to generate SQL")
    
    print("\n" + "="*60)
