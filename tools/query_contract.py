#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic Query Contract (DQC) System
==========================================
Interactive Query Hardening - Forces ambiguous queries into deterministic shape.

Flow:
  User Question → LLM Intent → Query Contract → Always Confirm → Execute
"""

import json
import sqlite3
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field, asdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# VALUE MAPPINGS - User words → Database values
# ============================================================================

CONDITION_MAPPING = {
    # User input → DB value
    'poor': 'Poor',
    'bad': 'Poor',
    'worst': 'Poor',
    'r1': 'Poor',
    'fair': 'Fair',
    'r2': 'Fair',
    'average': 'Fair',
    'good': 'Good',
    'r3': 'Good',
    'okay': 'Good',
    'very good': 'Very Good',
    'excellent': 'Very Good',
    'great': 'Very Good',
    'r4': 'Very Good',
    'unknown': 'Unknown',
}

CRITICALITY_MAPPING = {
    'critical': 'Critical',
    'most critical': 'Critical',
    'highest': 'Critical',
    'urgent': 'Critical',
    'high': 'High',
    'high priority': 'High',
    'important': 'High',
    'medium': 'Medium',
    'moderate': 'Medium',
    'normal': 'Medium',
    'low': 'Low',
    'minor': 'Low',
    'not important': 'Low',
    'unknown': 'Unknown',
}

DATA_SOURCE_MAPPING = {
    'fulcrum': 'Fulcrum',
    'precise fire': 'Precise Fire',
    'fire': 'Precise Fire',
    'fire services': 'Precise Fire',
    'precise air': 'Precise Air',
    'hvac': 'Precise Air',
    'air conditioning': 'Precise Air',
    'scis': 'SCIS',
    'equilibrium': 'Equilibrium',
    'nu-tech': 'Nu-Tech Air Conditioning',
    'frigecorp': 'Frigecorp',
    'gwe': 'GWE Electrical',
    'electrical': 'GWE Electrical',
    'pds': 'PDS',
}

CATEGORY_PATTERNS = {
    'fire': '%Fire%',
    'electrical': '%Electrical%',
    'hvac': '%HVAC%',
    'air': '%Air%',
    'plumbing': '%Plumbing%',
    'structural': '%Structural%',
    'building': '%Building%',
    'lighting': '%Lighting%',
    'doors': '%Doors%',
    'walls': '%Walls%',
    'flooring': '%Flooring%',
    'ceiling': '%Ceiling%',
    'windows': '%Windows%',
}

STATUS_MAPPING = {
    'in service': 'In Service',
    'active': 'In Service',
    'working': 'In Service',
    'retired': 'Retired',
    'decommissioned': 'Retired',
    'broken': 'Not In Service-On Site/Broken',
    'not working': 'Not In Service-On Site/Broken',
}


# ============================================================================
# AVAILABLE OPTIONS - For UI dropdowns
# ============================================================================

FILTER_OPTIONS = {
    'condition': ['Poor', 'Fair', 'Good', 'Very Good', 'Unknown'],
    'criticality': ['Critical', 'High', 'Medium', 'Low', 'Unknown'],
    'data_source': ['Fulcrum', 'Precise Fire', 'Precise Air', 'SCIS', 'Equilibrium', 'Other'],
    'category': ['Fire Systems', 'Electrical Systems', 'HVAC', 'Plumbing Systems', 'Building Structural', 'Other'],
    'status': ['In Service', 'Retired', 'Not In Service'],
}

OUTPUT_TYPES = ['list', 'count', 'groupby']

GROUPBY_FIELDS = ['condition', 'criticality', 'data_source', 'category', 'location', 'building']


# ============================================================================
# QUERY CONTRACT DATA CLASSES
# ============================================================================

@dataclass
class FilterSpec:
    """A single filter specification."""
    field: str
    user_value: str  # What user said
    db_value: str    # Mapped DB value
    operator: str = '='  # '=', 'LIKE', 'IN'
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class QueryContract:
    """
    Deterministic Query Contract.
    Represents a fully validated query that can be executed.
    """
    action: str  # list, count, groupby
    filters: List[FilterSpec] = field(default_factory=list)
    output_type: str = 'list'
    output_columns: List[str] = field(default_factory=lambda: ['asset_id', 'asset_name', 'condition', 'criticality'])
    group_by: Optional[str] = None
    limit: int = 100
    confidence: float = 1.0
    original_question: str = ''
    
    def to_dict(self) -> Dict:
        return {
            'action': self.action,
            'filters': [f.to_dict() for f in self.filters],
            'output_type': self.output_type,
            'output_columns': self.output_columns,
            'group_by': self.group_by,
            'limit': self.limit,
            'confidence': self.confidence,
            'original_question': self.original_question,
        }
    
    def get_filter_summary(self) -> str:
        """Human-readable summary of filters."""
        if not self.filters:
            return "All assets (no filters)"
        
        parts = []
        for f in self.filters:
            parts.append(f"{f.field} = {f.db_value}")
        return ", ".join(parts)
    
    def to_sql(self) -> Tuple[str, List[str]]:
        """Convert contract to SQL query."""
        params = []
        
        # Build WHERE clause
        where_parts = []
        for f in self.filters:
            if f.operator == 'LIKE':
                where_parts.append(f"{f.field} LIKE ?")
                params.append(f.db_value)
            elif f.operator == 'IN':
                # Handle IN operator for multiple values
                values = f.db_value.split(',')
                placeholders = ','.join(['?' for _ in values])
                where_parts.append(f"{f.field} IN ({placeholders})")
                params.extend(values)
            else:
                where_parts.append(f"{f.field} = ?")
                params.append(f.db_value)
        
        where_clause = " AND ".join(where_parts) if where_parts else "1=1"
        
        # Build query based on action
        if self.action == 'count':
            sql = f"SELECT COUNT(*) as count FROM assets WHERE {where_clause}"
        elif self.action == 'groupby' and self.group_by:
            sql = f"SELECT {self.group_by}, COUNT(*) as count FROM assets WHERE {where_clause} GROUP BY {self.group_by} ORDER BY count DESC"
        else:  # list
            columns = ", ".join(self.output_columns) if self.output_columns else "*"
            sql = f"SELECT {columns} FROM assets WHERE {where_clause} LIMIT {self.limit}"
        
        return sql, params


# ============================================================================
# QUERY CONTRACT BUILDER
# ============================================================================

class QueryContractBuilder:
    """
    Builds Query Contracts from natural language using LLM intent extraction.
    """
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        import os
        import google.generativeai as genai
        from dotenv import load_dotenv
        
        load_dotenv()
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        logger.info(f"QueryContractBuilder initialized with {model_name}")
    
    def extract_intent(self, question: str) -> QueryContract:
        """
        Extract structured intent from natural language question.
        Returns a QueryContract (may need user confirmation).
        """
        prompt = self._build_extraction_prompt(question)
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={'temperature': 0.0, 'max_output_tokens': 300}
            )
            
            # Parse JSON response
            text = response.text.strip()
            if text.startswith('```'):
                text = text.split('```')[1]
                if text.startswith('json'):
                    text = text[4:]
            text = text.strip()
            
            intent = json.loads(text)
            return self._intent_to_contract(intent, question)
            
        except Exception as e:
            logger.error(f"Intent extraction failed: {e}")
            # Return empty contract for user to fill
            return QueryContract(
                action='list',
                original_question=question,
                confidence=0.0
            )
    
    def _build_extraction_prompt(self, question: str) -> str:
        return f'''Extract the query intent from this question about an asset register.

AVAILABLE FILTER FIELDS:
- condition: Poor, Fair, Good, Very Good, Unknown
- criticality: Critical, High, Medium, Low, Unknown  
- data_source: Fulcrum, Precise Fire, Precise Air, SCIS
- category: Fire, Electrical, HVAC, Plumbing, Structural
- status: In Service, Retired

ACTIONS:
- "count" - How many assets
- "list" - Show/list assets
- "groupby" - Breakdown by field

RULES:
1. Output ONLY valid JSON
2. Map user words to exact filter values
3. Include confidence 0.0-1.0

User Question: "{question}"

JSON Output format:
{{"action": "count|list|groupby", "filters": [{{"field": "...", "value": "..."}}], "group_by": null, "confidence": 0.9}}

JSON:'''

    def _intent_to_contract(self, intent: Dict, question: str) -> QueryContract:
        """Convert raw intent to validated QueryContract."""
        filters = []
        
        for f in intent.get('filters', []):
            field = f.get('field', '').lower()
            value = f.get('value', '').lower()
            
            # Map to DB value
            db_value, operator = self._map_value(field, value)
            
            if db_value:
                filters.append(FilterSpec(
                    field=field,
                    user_value=value,
                    db_value=db_value,
                    operator=operator
                ))
        
        action = intent.get('action', 'list')
        group_by = intent.get('group_by')
        confidence = intent.get('confidence', 0.5)
        
        # If groupby action, set output type
        output_type = 'groupby' if action == 'groupby' else action
        
        return QueryContract(
            action=action,
            filters=filters,
            output_type=output_type,
            group_by=group_by,
            confidence=confidence,
            original_question=question
        )
    
    def _map_value(self, field: str, value: str) -> Tuple[str, str]:
        """Map user value to DB value and determine operator."""
        value_lower = value.lower().strip()
        
        if field == 'condition':
            db_val = CONDITION_MAPPING.get(value_lower)
            return (db_val, '=') if db_val else (None, None)
        
        elif field == 'criticality':
            db_val = CRITICALITY_MAPPING.get(value_lower)
            return (db_val, '=') if db_val else (None, None)
        
        elif field == 'data_source':
            db_val = DATA_SOURCE_MAPPING.get(value_lower)
            return (db_val, '=') if db_val else (f'%{value}%', 'LIKE')
        
        elif field == 'category':
            pattern = CATEGORY_PATTERNS.get(value_lower)
            return (pattern, 'LIKE') if pattern else (f'%{value}%', 'LIKE')
        
        elif field == 'status':
            db_val = STATUS_MAPPING.get(value_lower)
            return (db_val, '=') if db_val else (None, None)
        
        else:
            # Unknown field - use LIKE for fuzzy match
            return (f'%{value}%', 'LIKE')


# ============================================================================
# QUERY CONTRACT EXECUTOR
# ============================================================================

class QueryContractExecutor:
    """Executes validated Query Contracts against the database."""
    
    def __init__(self, db_path: str = "data/assets.db"):
        self.db_path = db_path
        logger.info(f"QueryContractExecutor initialized with {db_path}")
    
    def execute(self, contract: QueryContract) -> Dict[str, Any]:
        """Execute a validated Query Contract."""
        sql, params = contract.to_sql()
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            logger.info(f"Executing: {sql} with {params}")
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            results = [dict(row) for row in rows]
            conn.close()
            
            return {
                'success': True,
                'results': results,
                'count': results[0]['count'] if contract.action == 'count' and results else len(results),
                'contract': contract.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': []
            }

    def get_distinct_values(self, field: str) -> List[str]:
        """Get distinct values for a field from the database."""
        # Whitelist fields to prevent SQL injection
        allowed_fields = ['condition', 'criticality', 'data_source', 'category', 'status', 'location', 'building']
        if field not in allowed_fields:
            return []
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get distinct values, case-insensitive sorting
            sql = f"SELECT DISTINCT {field} FROM assets WHERE {field} IS NOT NULL AND {field} != '' ORDER BY {field}"
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            values = [row[0] for row in rows]
            conn.close()
            return values
        except Exception as e:
            logger.error(f"Failed to get distinct values for {field}: {e}")
            return []


# ============================================================================
# CONFIRMATION UI GENERATOR
# ============================================================================

def generate_confirmation_ui(contract: QueryContract, dynamic_options: Dict[str, List[str]] = None) -> Dict[str, Any]:
    """
    Generate UI data for query confirmation.
    Always shown to user before execution (Option A).
    Args:
        contract: The query contract
        dynamic_options: Optional dictionary of field -> list of values from DB
    """
    # Use provided options or fall back to defaults
    options_map = dynamic_options or {}
    
    def get_options(field: str) -> List[str]:
        return options_map.get(field, FILTER_OPTIONS.get(field, []))

    def get_selected_value(field_name: str, options: List[str]) -> Optional[str]:
        """Helper to find the best matching option for a field."""
        # Find the filter for this field
        filter_spec = next((f for f in contract.filters if f.field == field_name), None)
        if not filter_spec:
            return None
            
        db_val = filter_spec.db_value
        
        # 1. Exact match
        if db_val in options:
            return db_val
            
        # 2. Case-insensitive match
        for opt in options:
            if opt.lower() == db_val.lower():
                return opt
                
        # 3. Fuzzy/LIKE match (e.g. %Fire% -> Fire)
        clean_val = db_val.replace('%', '')
        for opt in options:
            if clean_val.lower() in opt.lower() or opt.lower() in clean_val.lower():
                return opt
                
        return None

    return {
        'type': 'query_confirmation',
        'understood': {
            'action': contract.action,
            'filters': [f.to_dict() for f in contract.filters],
            'summary': contract.get_filter_summary(),
        },
        'additional_filters': {
            'condition': {
                'label': 'Condition',
                'options': get_options('condition'),
                'selected': get_selected_value('condition', get_options('condition'))
            },
            'criticality': {
                'label': 'Criticality', 
                'options': get_options('criticality'),
                'selected': get_selected_value('criticality', get_options('criticality'))
            },
            'data_source': {
                'label': 'Data Source',
                'options': get_options('data_source'),
                'selected': get_selected_value('data_source', get_options('data_source'))
            },
            'category': {
                'label': 'Category',
                'options': get_options('category'),
                'selected': get_selected_value('category', get_options('category'))
            },
            'status': {
                'label': 'Status',
                'options': get_options('status'),
                'selected': get_selected_value('status', get_options('status'))
            },
        },
        'output_options': {
            'type': {
                'label': 'Output Type',
                'options': OUTPUT_TYPES,
                'selected': contract.output_type
            },
            'group_by': {
                'label': 'Group By (if applicable)',
                'options': ['None'] + GROUPBY_FIELDS,
                'selected': contract.group_by or 'None'
            }
        },
        'original_question': contract.original_question
    }


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("DETERMINISTIC QUERY CONTRACT TEST")
    print("="*70)
    
    builder = QueryContractBuilder()
    executor = QueryContractExecutor()
    
    test_queries = [
        "How many total assets?",
        "Show poor condition assets",
        "Count critical fire assets",
        "List high priority HVAC assets",
        "Breakdown by criticality",
    ]
    
    for q in test_queries:
        print(f"\n{'='*70}")
        print(f"Question: {q}")
        print("-"*70)
        
        # Extract intent
        contract = builder.extract_intent(q)
        print(f"Contract: {contract.to_dict()}")
        
        # Generate confirmation UI
        ui = generate_confirmation_ui(contract)
        print(f"Understood: {ui['understood']['summary']}")
        
        # Execute (in real flow, would wait for user confirmation)
        result = executor.execute(contract)
        if result['success']:
            if contract.action == 'count':
                print(f"Result: {result['count']} assets")
            else:
                print(f"Result: {len(result['results'])} rows")
        else:
            print(f"Error: {result['error']}")
    
    print("\n" + "="*70)
