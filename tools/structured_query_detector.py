#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Structured Query Detector
Detects when user queries are asking for structured field data (count, aggregation by column).
Routes these queries to SQL for 95%+ accuracy instead of semantic search.
"""

import re
from typing import Dict, List, Any, Optional, Tuple
import sqlite3
from pathlib import Path
import time
from difflib import get_close_matches


class StructuredQueryDetector:
    """
    Detects structured field queries and generates SQL queries for high accuracy.

    Examples of structured queries:
    - "How many Precise Fire assets?"  -> COUNT WHERE data_source = 'Precise Fire'
    - "Count assets by category"       -> GROUP BY category
    - "Show me all fire systems"       -> SELECT WHERE category LIKE '%fire%'
    """

    def __init__(self, db_path: str = "data/assets.db"):
        """Initialize detector with database connection."""
        self.db_path = Path(db_path)

        # Load database schema to understand available columns
        self.schema = self._load_schema()

        # Fuzzy matching cache (in-memory, 5-minute TTL)
        self._value_cache = {}  # {field: [distinct_values]}
        self._cache_timestamp = {}  # {field: timestamp}

        # Define query patterns
        self.count_patterns = [
            r'how many\s+(\w+(?:\s+\w+)*)',  # "how many X"
            r'count\s+(?:of\s+)?(\w+(?:\s+\w+)*)',  # "count X"
            r'total\s+(?:number\s+of\s+)?(\w+(?:\s+\w+)*)',  # "total X"
            r'number\s+of\s+(\w+(?:\s+\w+)*)',  # "number of X"
        ]

        self.groupby_patterns = [
            r'by\s+(\w+)',  # "count by X", "breakdown by X"
            r'breakdown\s+(?:of\s+)?(\w+)',
            r'group\s+by\s+(\w+)',
        ]

        # Common field mappings (query term -> database column)
        self.field_mappings = {
            'category': ['category', 'asset_type', 'type'],
            'location': ['location', 'building', 'site'],
            'condition': ['condition', 'condition_rating', 'status'],
            'type': ['asset_type', 'type', 'category'],
            'data_source': ['data_source', 'source'],  # NEW: Support data_source queries
            'source': ['data_source', 'source', '_source_file'],
            'criticality': ['criticality', 'risk_rating'],
            'age': ['current_age', 'age'],
            'cost': ['replacement_cost', 'cost'],
        }

    def _load_schema(self) -> Dict[str, List[str]]:
        """Load database schema to get available columns."""
        if not self.db_path.exists():
            return {'columns': [], 'tables': []}

        schema = {'columns': [], 'tables': []}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            schema['tables'] = [row[0] for row in cursor.fetchall()]

            # Get columns from main assets table
            if 'assets' in schema['tables']:
                cursor.execute("PRAGMA table_info(assets)")
                schema['columns'] = [row[1] for row in cursor.fetchall()]

            conn.close()
        except Exception as e:
            print(f"[WARN] Could not load schema: {e}")

        return schema

    def get_distinct_values(self, field: str) -> List[str]:
        """
        Get all unique values for a field from database with caching.

        Args:
            field: Database column name

        Returns:
            List of distinct values from database
        """
        cache_key = field
        cache_ttl = 300  # 5 minutes

        # Check cache freshness
        if cache_key in self._value_cache:
            age = time.time() - self._cache_timestamp.get(cache_key, 0)
            if age < cache_ttl:
                return self._value_cache[cache_key]

        # Query database for distinct values
        values = []
        try:
            if not self.db_path.exists():
                return values

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Query distinct values
            cursor.execute(f"SELECT DISTINCT {field} FROM assets WHERE {field} IS NOT NULL AND {field} != ''")
            values = [row[0] for row in cursor.fetchall()]

            conn.close()

            # Update cache
            self._value_cache[cache_key] = values
            self._cache_timestamp[cache_key] = time.time()

        except Exception as e:
            print(f"[WARN] Could not query distinct values for {field}: {e}")

        return values

    def fuzzy_match_value(self, user_input: str, field: str) -> Optional[str]:
        """
        Find closest database value using fuzzy string matching.

        Args:
            user_input: User's input value (e.g., "poor", "good")
            field: Database column name (e.g., "condition", "data_source")

        Returns:
            Matched database value or None if no good match

        Examples:
            fuzzy_match_value("poor", "condition") -> "R1 Poor"
            fuzzy_match_value("good", "condition") -> "R4 Good"
            fuzzy_match_value("por", "condition") -> "R1 Poor" (typo correction)
        """
        distinct_values = self.get_distinct_values(field)

        if not distinct_values:
            return None

        # Strategy 1: Exact match (case-insensitive)
        for db_value in distinct_values:
            if user_input.lower() == db_value.lower():
                print(f"[FUZZY MATCH] Exact: '{user_input}' -> '{db_value}'")
                return db_value

        # Strategy 2: Substring match (current LIKE behavior)
        # Only return if unambiguous (single match)
        substring_matches = [v for v in distinct_values if user_input.lower() in v.lower()]
        if len(substring_matches) == 1:
            print(f"[FUZZY MATCH] Substring: '{user_input}' -> '{substring_matches[0]}'")
            return substring_matches[0]

        # Strategy 3: Fuzzy match for typos (e.g., "por" -> "Poor")
        matches = get_close_matches(user_input, distinct_values, n=1, cutoff=0.6)
        if matches:
            print(f"[FUZZY MATCH] Fuzzy: '{user_input}' -> '{matches[0]}'")
            return matches[0]

        # No good match found - return None to fall back to LIKE query
        return None

    def is_structured_query(self, query: str) -> bool:
        """
        Determine if query is asking for structured field data.

        Args:
            query: User query

        Returns:
            True if structured query, False otherwise
        """
        query_lower = query.lower()

        # Check for count patterns
        for pattern in self.count_patterns:
            if re.search(pattern, query_lower):
                return True

        # Check for groupby patterns
        for pattern in self.groupby_patterns:
            if re.search(pattern, query_lower):
                return True

        # Check for specific field names in query
        for field_group in self.field_mappings.values():
            for field in field_group:
                if field.lower() in query_lower:
                    # If field name + count/how many -> structured
                    if any(keyword in query_lower for keyword in ['how many', 'count', 'total', 'number of']):
                        return True

        return False

    def detect_multiple_filters(self, query: str) -> List[Tuple[str, str]]:
        """
        Detect multiple field=value filters in query.

        Args:
            query: User query

        Returns:
            List of (field, value) tuples

        Examples:
            "Precise Fire assets in poor condition"
            → [('data_source', 'Precise Fire'), ('condition', 'Poor')]

            "Critical assets from Fulcrum"
            → [('criticality', 'Critical'), ('data_source', 'Fulcrum')]
        """
        filters = []
        query_lower = query.lower()

        # Pattern 1: Data source detection
        # "Precise Fire assets" or "from Precise Fire"
        asset_keywords = ['assets?', 'systems?', 'equipment', 'items?']
        for keyword in asset_keywords:
            pattern = r'(?:how many|count|total|number of)\s+(.+?)\s+' + keyword
            match = re.search(pattern, query_lower)
            if match:
                value = match.group(1).strip()
                # Get original case
                original_match = re.search(re.escape(value), query, re.IGNORECASE)
                if original_match:
                    value = original_match.group(0)
                # Remove filler words and condition words
                value = re.sub(r'\b(the|all|our|my|in|with|at)\b\s*', '', value, flags=re.IGNORECASE).strip()
                # Remove condition keywords to isolate source
                for cond in ['poor', 'fair', 'good', 'excellent', 'critical', 'high', 'low', 'medium']:
                    value = re.sub(r'\b' + cond + r'\b\s*', '', value, flags=re.IGNORECASE).strip()
                    value = re.sub(r'\s*condition\b', '', value, flags=re.IGNORECASE).strip()

                if value and len(value) > 2:
                    filters.append(('data_source', value))
                break

        # Pattern 2: Condition detection
        condition_patterns = [
            (r'\b(very\s+poor)\b', 'Very Poor'),
            (r'\b(very\s+good)\b', 'Very Good'),
            (r'\b(poor)\s+condition\b', 'Poor'),
            (r'\b(fair)\s+condition\b', 'Fair'),
            (r'\b(good)\s+condition\b', 'Good'),
            (r'\b(excellent)\s+condition\b', 'Excellent'),
            (r'\bin\s+(poor)\b', 'Poor'),
            (r'\bin\s+(fair)\b', 'Fair'),
            (r'\bin\s+(good)\b', 'Good'),
            (r'\b(r1)\b', 'Very Poor'),
            (r'\b(r2)\b', 'Poor'),
            (r'\b(r3)\b', 'Fair'),
            (r'\b(r4)\b', 'Good'),
            (r'\b(r5)\b', 'Very Good'),
        ]

        for pattern, standard_value in condition_patterns:
            if re.search(pattern, query_lower):
                filters.append(('condition', standard_value))
                break

        # Pattern 3: Criticality detection
        criticality_patterns = [
            (r'\b(critical)\s+(?:assets|systems|equipment)', 'Critical'),
            (r'\b(high)\s+criticality\b', 'High'),
            (r'\b(medium)\s+criticality\b', 'Medium'),
            (r'\b(low)\s+criticality\b', 'Low'),
            (r'\bcriticality\s*=\s*["\']?(\w+)', lambda m: m.group(1).title()),
        ]

        for pattern, value in criticality_patterns:
            match = re.search(pattern, query_lower)
            if match:
                if callable(value):
                    filters.append(('criticality', value(match)))
                else:
                    filters.append(('criticality', value))
                break

        # Pattern 4: Location detection
        location_patterns = [
            (r'\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'location'),
            (r'\bat\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'location'),
            (r'\blocation\s*=\s*["\']?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'location'),
        ]

        for pattern, field in location_patterns:
            match = re.search(pattern, query)
            if match:
                value = match.group(1).strip()
                # Don't add if it's already in data_source
                if not any(f[0] == 'data_source' and value in f[1] for f in filters):
                    filters.append((field, value))
                break

        # Pattern 5: Age/date filters
        age_patterns = [
            (r'over\s+(\d+)\s+years?\s+old', lambda m: ('current_age__gt', int(m.group(1)))),
            (r'older\s+than\s+(\d+)\s+years?', lambda m: ('current_age__gt', int(m.group(1)))),
            (r'less\s+than\s+(\d+)\s+years?\s+old', lambda m: ('current_age__lt', int(m.group(1)))),
            (r'younger\s+than\s+(\d+)\s+years?', lambda m: ('current_age__lt', int(m.group(1)))),
        ]

        for pattern, extractor in age_patterns:
            match = re.search(pattern, query_lower)
            if match:
                filters.append(extractor(match))
                break

        return filters

    def detect_field_value(self, query: str) -> Optional[Tuple[str, str]]:
        """
        Detect field=value pattern in query.

        Args:
            query: User query

        Returns:
            Tuple of (field, value) or None

        Examples:
            "How many Precise Fire assets?" -> ('data_source', 'Precise Fire')
            "Count assets in Building A" -> ('building', 'Building A')
        """
        query_lower = query.lower()

        # Remove common question starters to avoid false matches
        stopwords = ['how many', 'count', 'total', 'number of', 'show me', 'list', 'find']
        cleaned_query = query_lower
        for stopword in stopwords:
            cleaned_query = cleaned_query.replace(stopword, '').strip()

        # Pattern 0: Check for condition values FIRST (highest priority)
        # This prevents "poor" from being detected as data_source
        condition_values = ['very poor', 'very good', 'poor', 'fair', 'good', 'excellent', 'unknown']
        for condition in condition_values:
            if condition in query_lower:
                return ('condition', condition.title())

        # Pattern 1: "X Y assets" or "X Y systems" -> data_source = "X Y"
        # Example: "Precise Fire assets" -> data_source = "Precise Fire"
        asset_keywords = ['assets?', 'systems?', 'equipment', 'items?']
        for keyword in asset_keywords:
            # Match: "Capitalized Word(s) + keyword"
            # Use lookahead to find content between question words and asset keywords
            pattern = r'(?:how many|count|total|number of)\s+(.+?)\s+' + keyword
            match = re.search(pattern, query_lower)
            if match:
                value = match.group(1).strip()
                # Capitalize it properly (was lowercase from query_lower)
                # Find the original case in the query
                original_match = re.search(re.escape(value), query, re.IGNORECASE)
                if original_match:
                    value = original_match.group(0)
                # Remove common filler words
                value = re.sub(r'\b(the|all|our|my)\b\s*', '', value, flags=re.IGNORECASE).strip()
                if value:
                    return ('data_source', value)

        # Pattern 1b: Single capitalized word before asset keyword (fallback)
        for keyword in asset_keywords:
            pattern = r'([A-Z][a-z]{2,})\s+' + keyword.replace('?', '')
            match = re.search(pattern, query)
            if match:
                value = match.group(1).strip()
                # Only accept if it looks like a proper noun
                if value and value not in ['Many', 'All', 'The', 'Our', 'My', 'These', 'Those']:
                    return ('data_source', value)

        # Pattern 2: "in/at/from X" -> location/building/source
        location_patterns = [
            (r'in\s+([A-Z][a-z]+(?:\s+[A-Z])?)', 'location'),
            (r'at\s+([A-Z][a-z]+(?:\s+[A-Z])?)', 'location'),
            (r'from\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', 'data_source'),
        ]
        for pattern, field in location_patterns:
            match = re.search(pattern, query)
            if match:
                value = match.group(1).strip()
                return (field, value)

        # Pattern 3: Check if query contains recognized field values in capitalized form
        # "Precise Fire" in "How many Precise Fire assets?" -> data_source
        # BUT exclude the question words themselves
        capitalized_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
        matches = re.findall(capitalized_pattern, query)

        # Filter out question words and common phrases
        exclude_phrases = ['How Many', 'How many', 'Building A', 'Part A', 'Part B', 'Part C']

        for match in matches:
            # Check if this is after the question words
            match_index = query.find(match)
            question_words_index = max(
                query.lower().find('how many'),
                query.lower().find('count'),
                query.lower().find('total'),
                query.lower().find('number of')
            )

            # Only use matches that come AFTER the question words
            if match not in exclude_phrases and match_index > question_words_index:
                return ('data_source', match)

        return None

    def build_sql_query(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Build SQL query from natural language with multi-filter support.

        Args:
            query: User query

        Returns:
            Dictionary with SQL query, parameters, and metadata
        """
        if not self.is_structured_query(query):
            return None

        query_lower = query.lower()

        # Check if it's a COUNT query
        is_count = any(keyword in query_lower for keyword in ['how many', 'count', 'total', 'number of'])

        # Check if it's a GROUP BY query
        groupby_field = None
        for pattern in self.groupby_patterns:
            match = re.search(pattern, query_lower)
            if match:
                groupby_field = match.group(1)
                break

        # Try multi-filter detection first
        filters = self.detect_multiple_filters(query)

        if is_count and filters:
            # Multi-filter count query
            where_clauses = []
            params = []
            filter_descriptions = []

            for field, value in filters:
                db_field = self._map_to_db_column(field)

                # Handle operator suffixes (e.g., current_age__gt)
                if '__' in field:
                    base_field, operator = field.rsplit('__', 1)
                    db_field = self._map_to_db_column(base_field)

                    if operator == 'gt':
                        where_clauses.append(f"{db_field} > ?")
                        params.append(value)
                        filter_descriptions.append(f"{base_field} > {value}")
                    elif operator == 'lt':
                        where_clauses.append(f"{db_field} < ?")
                        params.append(value)
                        filter_descriptions.append(f"{base_field} < {value}")
                    elif operator == 'gte':
                        where_clauses.append(f"{db_field} >= ?")
                        params.append(value)
                        filter_descriptions.append(f"{base_field} >= {value}")
                    elif operator == 'lte':
                        where_clauses.append(f"{db_field} <= ?")
                        params.append(value)
                        filter_descriptions.append(f"{base_field} <= {value}")
                else:
                    # Regular field match - use fuzzy matching for precision
                    matched_value = self.fuzzy_match_value(value, db_field)

                    if matched_value and matched_value != value:
                        # Exact match found via fuzzy matching
                        where_clauses.append(f"{db_field} = ?")
                        params.append(matched_value)
                        filter_descriptions.append(f"{field}='{matched_value}'")
                    else:
                        # Fallback to LIKE for broad matching
                        where_clauses.append(f"{db_field} LIKE ?")
                        params.append(f"%{value}%")
                        filter_descriptions.append(f"{field}='{value}'")

            where_sql = " AND ".join(where_clauses)
            sql = f"SELECT COUNT(*) as count FROM assets WHERE {where_sql}"

            return {
                'sql': sql,
                'params': params,
                'type': 'count',
                'filters': filters,
                'filter_count': len(filters),
                'description': f"Count assets where {' AND '.join(filter_descriptions)}"
            }

        elif is_count:
            # Single filter fallback
            field_value = self.detect_field_value(query)
            if field_value:
                field, value = field_value
                db_field = self._map_to_db_column(field)

                # Use fuzzy matching for precision
                matched_value = self.fuzzy_match_value(value, db_field)

                if matched_value and matched_value != value:
                    # Exact match found via fuzzy matching
                    sql = f"SELECT COUNT(*) as count FROM assets WHERE {db_field} = ?"
                    params = [matched_value]
                    description = f"Count assets where {field} = '{matched_value}'"
                else:
                    # Fallback to LIKE for broad matching
                    sql = f"SELECT COUNT(*) as count FROM assets WHERE {db_field} LIKE ?"
                    params = [f"%{value}%"]
                    description = f"Count assets where {field} contains '{value}'"

                return {
                    'sql': sql,
                    'params': params,
                    'type': 'count',
                    'field': field,
                    'value': value,
                    'description': description
                }

        elif groupby_field:
            # Group by query
            db_field = self._map_to_db_column(groupby_field)

            sql = f"SELECT {db_field}, COUNT(*) as count FROM assets GROUP BY {db_field} ORDER BY count DESC"
            params = []

            return {
                'sql': sql,
                'params': params,
                'type': 'groupby',
                'field': groupby_field,
                'description': f"Breakdown of assets by {groupby_field}"
            }

        return None

    def _map_to_db_column(self, field_name: str) -> str:
        """
        Map query field name to database column.

        Args:
            field_name: Field name from query

        Returns:
            Actual database column name
        """
        field_lower = field_name.lower()

        # Check mappings
        for query_field, db_fields in self.field_mappings.items():
            if field_lower == query_field or field_lower in db_fields:
                # Return first matching column that exists in schema
                for db_field in db_fields:
                    if db_field in self.schema['columns']:
                        return db_field
                # Fallback to first mapping
                return db_fields[0]

        # Fallback: assume field name is correct
        return field_name

    def execute_sql_query(self, sql_query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute SQL query and return results.

        Args:
            sql_query: Query dictionary from build_sql_query()

        Returns:
            Dictionary with results and metadata
        """
        if not self.db_path.exists():
            return {
                'success': False,
                'error': 'Database not found',
                'results': []
            }

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(sql_query['sql'], sql_query['params'])
            rows = cursor.fetchall()

            results = [dict(row) for row in rows]
            conn.close()

            return {
                'success': True,
                'results': results,
                'count': len(results),
                'query_type': sql_query['type'],
                'description': sql_query['description']
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'results': []
            }


# Test function
if __name__ == '__main__':
    print("Testing Structured Query Detector...")

    detector = StructuredQueryDetector()

    test_queries = [
        "How many Precise Fire assets?",
        "Count assets by category",
        "Show me all poor condition assets",
        "What is ISO 55000?",  # Not structured
        "Total number of Building A assets",
        "Breakdown by location",
        "How many assets need replacement?",  # Not structured (no field match)
    ]

    print("\n" + "="*70)
    print("STRUCTURED QUERY DETECTION TEST")
    print("="*70)

    for query in test_queries:
        print(f"\nQuery: \"{query}\"")
        is_structured = detector.is_structured_query(query)
        print(f"  Structured: {is_structured}")

        if is_structured:
            sql_query = detector.build_sql_query(query)
            if sql_query:
                print(f"  SQL: {sql_query['sql']}")
                print(f"  Params: {sql_query['params']}")
                print(f"  Type: {sql_query['type']}")
                print(f"  Description: {sql_query['description']}")
            else:
                print("  (Could not build SQL)")

    print("\n" + "="*70)
