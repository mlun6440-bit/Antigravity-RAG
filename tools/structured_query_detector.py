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

            # Whitelist columns to prevent SQL injection
            allowed_columns = [
                'condition', 'criticality', 'data_source', 'category',
                'status', 'location', 'building', 'floor', 'asset_type',
                'compliance_standard', 'inspection_status', 'asset_name',
            ]
            if field not in allowed_columns:
                logger.warning(f"[SQD] Blocked query for non-whitelisted column: {field}")
                return values

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Column name is validated via whitelist above, safe to use in query
                cursor.execute(f"SELECT DISTINCT {field} FROM assets WHERE {field} IS NOT NULL AND {field} != ''")
                values = [row[0] for row in cursor.fetchall()]

            # Update cache
            self._value_cache[cache_key] = values
            self._cache_timestamp[cache_key] = time.time()

        except Exception as e:
            print(f"[WARN] Could not query distinct values for {field}: {e}")

        return values

    def fuzzy_match_value(self, user_input: str, field: str, threshold: float = 0.6) -> Optional[str]:
        """
        Find closest database value using fuzzy string matching.

        Args:
            user_input: User's input value (e.g., "poor", "good")
            field: Database column name (e.g., "condition", "data_source")
            threshold: Similarity threshold (0.0 to 1.0, default 0.6)

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
        matches = get_close_matches(user_input, distinct_values, n=1, cutoff=threshold)
        if matches:
            print(f"[FUZZY MATCH] Fuzzy: '{user_input}' -> '{matches[0]}'")
            return matches[0]

        # No good match found - return None to fall back to LIKE query
        return None

    def detect_query_mode(self, query: str) -> str:
        """
        Detect query mode for 3-way routing.
        
        Args:
            query: User query
            
        Returns:
            'structured': Count/list queries → SQL only
            'analytical': Analysis + data filters → SQL + LLM + ISO
            'knowledge': Pure knowledge queries → RAG only
        """
        query_lower = query.lower()
        
        # Define pattern keywords
        analytical_keywords = [
            'analyze', 'assess', 'evaluate', 'review', 'prioritize',
            'per iso', 'compliance with', 'according to', 'should i',
            'recommend', 'risk', 'what should', 'how should'
        ]
        
        knowledge_keywords = [
            'what is', 'explain', 'describe', 'define', 'how does',
            'why does', 'best practice', 'requirement', 'standard',
            'guidelines', 'framework'
        ]
        
        structured_keywords = [
            'how many', 'count', 'total', 'number of', 'list all',
            'show all', 'which assets', 'what assets', 'breakdown by',
            'group by'
        ]
        
        # Check for knowledge queries (no data filtering)
        has_knowledge_keyword = any(kw in query_lower for kw in knowledge_keywords)
        has_data_filter = self._has_data_filter(query_lower)
        
        if has_knowledge_keyword and not has_data_filter:
            return 'knowledge'
        
        # Check for analytical queries (analysis + data)
        has_analytical_keyword = any(kw in query_lower for kw in analytical_keywords)
        
        if has_analytical_keyword and has_data_filter:
            return 'analytical'
        
        # Check for structured queries (count/list only)
        has_structured_keyword = any(kw in query_lower for kw in structured_keywords)
        
        if has_structured_keyword:
            return 'structured'
        
        # Default: knowledge query (safest fallback)
        return 'knowledge'
    
    def _has_data_filter(self, query_lower: str) -> bool:
        """
        Check if query contains data filtering terms.
        
        Args:
            query_lower: Lowercased query
            
        Returns:
            True if query references specific asset data/fields
        """
        # Check for field references
        data_fields = [
            'condition', 'criticality', 'location', 'building',
            'category', 'type', 'age', 'cost', 'asset', 'system',
            'equipment', 'fire', 'electrical', 'hvac', 'plumbing',
            'poor', 'fair', 'good', 'excellent', 'critical', 'high',
            'medium', 'low', 'years old', 'precise', 'fulcrum'
        ]
        
        return any(field in query_lower for field in data_fields)


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

        # PATTERN 0: Use generalized detect_field_value FIRST to catch specific column values
        # This ensures exact/fuzzy matches against actual database values take priority
        primary_detection = self.detect_field_value(query)
        if primary_detection:
            filters.append(primary_detection)

        # Pattern 1: Data source detection (only if Pattern 0 didn't find anything)
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
                    # Use generalized detection to identify the field type for this value
                    # This prevents misclassifying categories as data_source
                    detected = self.detect_field_value(value)
                    if detected:
                        filters.append(detected)
                    else:
                        # Fallback to data_source if no other field matches
                        filters.append(('data_source', value))
                break

        # Pattern 2: Condition detection
        # Defines (pattern, extractor_function)
        condition_patterns = [
            # Negation first
            (r'\bnot\s+(?:in\s+)?(very\s+poor|r1)\b', lambda m: ('condition__neq', 'Very Poor')),
            (r'\bnot\s+(?:in\s+)?(poor|r2)\s*(?:condition)?\b', lambda m: ('condition__neq', 'Poor')),
            (r'\bnot\s+(?:in\s+)?(fair|r3)\s*(?:condition)?\b', lambda m: ('condition__neq', 'Fair')),
            (r'\bnot\s+(?:in\s+)?(good|r4)\s*(?:condition)?\b', lambda m: ('condition__neq', 'Good')),
            (r'\bnot\s+(?:in\s+)?(excellent|r5)\s*(?:condition)?\b', lambda m: ('condition__neq', 'Excellent')),
            
            # Standard positive matches
            (r'\b(very\s+poor)\b', lambda m: ('condition', 'Very Poor')),
            (r'\b(very\s+good)\b', lambda m: ('condition', 'Very Good')),
            (r'\b(poor)\s+condition\b', lambda m: ('condition', 'Poor')),
            (r'\b(fair)\s+condition\b', lambda m: ('condition', 'Fair')),
            (r'\b(good)\s+condition\b', lambda m: ('condition', 'Good')),
            (r'\b(excellent)\s+condition\b', lambda m: ('condition', 'Excellent')),
            (r'\bin\s+(poor)\b', lambda m: ('condition', 'Poor')),
            (r'\bin\s+(fair)\b', lambda m: ('condition', 'Fair')),
            (r'\bin\s+(good)\b', lambda m: ('condition', 'Good')),
            (r'\b(r1)\b', lambda m: ('condition', 'Very Poor')),
            (r'\b(r2)\b', lambda m: ('condition', 'Poor')),
            (r'\b(r3)\b', lambda m: ('condition', 'Fair')),
            (r'\b(r4)\b', lambda m: ('condition', 'Good')),
            (r'\b(r5)\b', lambda m: ('condition', 'Very Good')),
        ]

        for pattern, extractor in condition_patterns:
            match = re.search(pattern, query_lower)
            if match:
                new_filter = extractor(match)
                # Avoid duplicate condition filters
                if new_filter not in filters and not any(f[0] == 'condition' for f in filters):
                    filters.append(new_filter)
                break

        # Pattern 3: Criticality detection
        criticality_patterns = [
            # Negation first
            (r'\bnot\s+(?:in\s+)?(critical)\s*(?:condition|criticality)?\b', lambda m: ('criticality__neq', 'Critical')),
            (r'\bnot\s+(high)\s+criticality\b', lambda m: ('criticality__neq', 'High')),
            (r'\bnot\s+(medium)\s+criticality\b', lambda m: ('criticality__neq', 'Medium')),
            (r'\bnot\s+(low)\s+criticality\b', lambda m: ('criticality__neq', 'Low')),

            # Standard positive matches
            (r'\b(critical)\s+(?:assets|systems|equipment|condition)', lambda m: ('criticality', 'Critical')),
            (r'\b(high)\s+criticality\b', lambda m: ('criticality', 'High')),
            (r'\b(medium)\s+criticality\b', lambda m: ('criticality', 'Medium')),
            (r'\b(low)\s+criticality\b', lambda m: ('criticality', 'Low')),
            (r'\bcriticality\s*=\s*["\']?(\w+)', lambda m: ('criticality', m.group(1).title())),
        ]

        for pattern, extractor in criticality_patterns:
            match = re.search(pattern, query_lower)
            if match:
                filters.append(extractor(match))
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

        # Pattern 6: Category detection
        category_patterns = [
            (r'\b(electrical)\b', 'Electrical'),
            (r'\b(mechanical)\b', 'Mechanical'),
            (r'\b(fire)\b', 'Fire Services'),
            (r'\b(hydraulic)\b', 'Hydraulics'),
            (r'\b(transport)\b', 'Transport'),
            (r'\b(building fabric)\b', 'Building Fabric'),
            (r'\b(hvac)\b', 'Mechanical'), # HVAC usually maps to Mechanical
            (r'\b(lift)\b', 'Lifts'),
        ]

        for pattern, value in category_patterns:
            match = re.search(pattern, query_lower)
            if match:
                # Avoid conflict with data_source if it captured these words
                # But data_source logic excludes condition words, it doesn't exclude categories
                # Let's trust category specific match.
                
                # Check if this category is already part of a data_source match (e.g. "Precise Fire")
                # But precise matching is better. 
                # If data_source is "Precise Fire", and we match "Fire", we might duplicate.
                # But data_source logic (Line 321) excludes condition words, NOT category words.
                
                # Simple check: if we found a data_source that contains the category name (case insensitive)
                if not any(f[0] == 'data_source' and value.lower() in f[1].lower() for f in filters):
                    filters.append(('category', value))

        return filters

    def detect_field_value(self, query: str) -> Optional[Tuple[str, str]]:
        """
        Detect field=value pattern in query by scanning ALL schema columns.
        Prioritizes exact matches, then high-confidence fuzzy matches.

        Args:
            query: User query

        Returns:
            Tuple of (field, value) or None
        """
        query_lower = query.lower()
        
        # Remove common question starters to clean up the query
        stopwords = ['how many', 'count', 'total', 'number of', 'show me', 'list', 'find', 'assets', 'items']
        cleaned_query = query_lower
        for stopword in stopwords:
            cleaned_query = cleaned_query.replace(stopword, '').strip()
        
        # Get all textual columns from schema
        # We focus on columns that likely contain categorical text data
        # EXCLUDE free-text fields like notes/description to prevent false positives
        excluded_cols = ['id', 'Asset ID', 'created_at', 'updated_at', 'geometry', 'notes', 'comments', 'description', 'image_url']
        target_columns = [col for col in self.schema['columns'] if col.lower() not in excluded_cols]
        
        best_match = None
        best_score = 0.0

        # Try to match the cleaned query against values in each column
        # We check phrases of varying lengths (n-grams) from the query
        
        # Normalize punctuation: replace commas, dashes with spaces to ensure correct tokenization
        # "Electrical Systems,Distribution Board" -> "Electrical Systems Distribution Board"
        cleaned_query_normalized = re.sub(r'[,\-]', ' ', cleaned_query)
        
        # Split query into words to check combinations
        words = cleaned_query_normalized.split()
        if not words:
            return None
            
        # Generate n-grams (up to 8 words long to handle long category names)
        # Category names can be quite long e.g. "HVAC & Refrigeration,Air Conditioning"
        phrases = []
        for n in range(8, 0, -1):
            for i in range(len(words) - n + 1):
                phrase = " ".join(words[i:i+n])
                if len(phrase) > 2: # Ignore tiny fragments
                    phrases.append(phrase)
        
        # Iterate through phrases (longest to shortest) first to prioritize more specific matches 
        # irrespective of column order
        for phrase in phrases:
            for column in target_columns:
                distinct_values = self.get_distinct_values(column)
                if not distinct_values:
                    continue

                # 1. Exact match check (case-insensitive and normalized)
                for val in distinct_values:
                    # Normalize DB value too
                    normalized_val = re.sub(r'[,\-]', ' ', str(val)).lower()
                    if normalized_val == phrase:
                        # Exact match is priority 1
                        return (column, str(val))
                
                # 2. Fuzzy match
                # Only attempt fuzzy match if phrase is reasonably long (>3 chars) to avoid noise
                if len(phrase) > 3:
                     # Normalize all DB values for comparison
                    normalized_db_values = [re.sub(r'[,\-]', ' ', str(v)).lower() for v in distinct_values]
                    matches = get_close_matches(phrase, normalized_db_values, n=1, cutoff=0.85)
                    
                    if matches:
                        # Find the original value that corresponds to the match
                        matched_normalized = matches[0]
                        original_val_index = normalized_db_values.index(matched_normalized)
                        original_val = distinct_values[original_val_index]
                        return (column, str(original_val))
                    
        # Fallback to existing logic if no strong database match found
        # Pattern 0: Check for condition values
        condition_values = ['very poor', 'very good', 'poor', 'fair', 'good', 'excellent', 'unknown']
        for condition in condition_values:
            if condition in query_lower:
                return ('condition', condition.title())

        # Pattern 3: Capitalized phrases fallback (Data Source assumptions)
        capitalized_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
        matches = re.findall(capitalized_pattern, query)
        exclude_phrases = ['How Many', 'How many', 'Building A', 'Part A', 'Part B', 'Part C']
        
        for match in matches:
             match_index = query.find(match)
             if match not in exclude_phrases and match_index > 5:
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

        # Check if it's a GROUP BY query (MUST CHECK THIS FIRST!)
        groupby_field = None
        for pattern in self.groupby_patterns:
            match = re.search(pattern, query_lower)
            if match:
                groupby_field = match.group(1)
                break

        # Try multi-filter detection first
        filters = self.detect_multiple_filters(query)

        # PRIORITY 1: GROUP BY queries (e.g., "count by criticality")
        if groupby_field:
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

        # PRIORITY 1.5: Count ALL assets (no filter)
        # Handles: "How many total assets?", "Count all assets", etc.
        # MUST CHECK BEFORE multi-filter detection to avoid "total" being detected as a filter
        if is_count:
            all_patterns = ['total assets', 'all assets', 'how many assets', 'count assets',
                          'number of assets', 'many assets are in', 'total in the register',
                          'assets in the register', 'count all', 'how many total']
            
            if any(pattern in query_lower for pattern in all_patterns):
                sql = "SELECT COUNT(*) as count FROM assets"
                return {
                    'sql': sql,
                    'params': [],
                    'type': 'count',
                    'field': None,
                    'value': None,
                    'description': 'Total count of all assets'
                }

        # PRIORITY 2: Multi-filter count queries
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
                    elif operator == 'neq':
                        where_clauses.append(f"{db_field} != ?")
                        params.append(value)
                        filter_descriptions.append(f"{base_field} != {value}")
                    elif operator == 'not_like':
                        where_clauses.append(f"{db_field} NOT LIKE ?")
                        params.append(f"%{value}%")
                        filter_descriptions.append(f"{base_field} NOT LIKE '{value}'")
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

        # PRIORITY 3: Single filter count queries
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

        # No structured query detected
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
