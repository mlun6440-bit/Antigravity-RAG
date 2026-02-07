#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemini Query Engine with RAG
ISO 55000 specialist for asset register queries using Google Gemini API.
"""

import os
import sys
import json
import argparse
from typing import Dict, List, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Add citation support
sys.path.insert(0, os.path.dirname(__file__))
from citation_formatter import CitationFormatter
from structured_query_detector import StructuredQueryDetector

# Python 3.13 handles UTF-8 natively on Windows
if sys.platform == 'win32':
    import io


class GeminiQueryEngine:
    """Query engine using Google Gemini with RAG for asset management."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None, use_two_stage: bool = True):
        """
        Initialize Gemini query engine with optional two-stage model.

        Args:
            api_key: Google Gemini API key
            model_name: Gemini model to use (defaults to GEMINI_MODEL from .env)
            use_two_stage: Use Flash for retrieval, Pro for synthesis (cost optimization)
        """
        # Load environment variables
        load_dotenv()

        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key or self.api_key == 'your_gemini_api_key_here':
            raise ValueError(
                "Gemini API key not found. Please set GEMINI_API_KEY in .env file.\n"
                "Get your API key from: https://makersuite.google.com/app/apikey"
            )

        self.model_name = model_name or os.getenv('GEMINI_MODEL', 'gemini-2.5-pro')
        self.flash_model_name = os.getenv('GEMINI_FLASH_MODEL', 'gemini-1.5-flash-latest')
        self.use_two_stage = use_two_stage

        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

        # Initialize Flash model for two-stage pipeline
        if self.use_two_stage:
            self.flash_model = genai.GenerativeModel(self.flash_model_name)
            print(f"[OK] Two-stage pipeline: {self.flash_model_name} (retrieval) -> {self.model_name} (synthesis)")
        else:
            self.flash_model = None
            print(f"[OK] Single-stage: {self.model_name}")

        # Initialize citation formatter
        self.citation_formatter = CitationFormatter()

        # Initialize structured query detector for SQL-based field queries
        try:
            self.structured_query_detector = StructuredQueryDetector()
            print(f"[OK] Structured query detector enabled (SQL-based field queries)")
        except Exception as e:
            self.structured_query_detector = None
            print(f"[WARN] Structured query detector not available: {e}")

        # Try to load embedding manager (optional, won't fail if deps missing)
        try:
            from embedding_manager import EmbeddingManager
            self.embedding_manager = EmbeddingManager(api_key=self.api_key)
            self.use_embeddings = True
            print(f"[OK] Embedding-based semantic search enabled")
        except ImportError:
            self.embedding_manager = None
            self.use_embeddings = False
            print(f"[INFO] Embeddings not available (install scikit-learn & numpy)")

        # Try to load ISO embedding manager for semantic ISO search
        try:
            from iso_embedding_manager import ISOEmbeddingManager
            self.iso_embedding_manager = ISOEmbeddingManager(api_key=self.api_key)
            self.use_iso_embeddings = True
            print(f"[OK] ISO semantic search enabled (vector embeddings)")
        except ImportError:
            self.iso_embedding_manager = None
            self.use_iso_embeddings = False
            print(f"[INFO] ISO embeddings not available")

    def load_asset_index(self, index_file: str) -> Dict[str, Any]:
        """Load asset index."""
        with open(index_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_iso_knowledge(self, kb_file: str) -> Dict[str, Any]:
        """Load ISO knowledge base."""
        with open(kb_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def preprocess_query(self, query: str) -> Dict[str, Any]:
        """
        Preprocess query to extract structured filters and expand terms.

        Args:
            query: User query

        Returns:
            Dictionary with parsed query components
        """
        import re

        # Synonym expansion for common terms
        synonyms = {
            'broken': ['broken', 'failed', 'poor', 'r1'],
            'poor': ['poor', 'failed', 'r1', 'bad'],
            'fair': ['fair', 'r2', 'average', 'medium'],
            'good': ['good', 'r3', 'excellent', 'r4', 'r5'],
            'critical': ['critical', 'high priority', 'urgent', 'essential'],
            'low': ['low', 'minor', 'non-critical']
        }

        query_lower = query.lower()
        expanded_terms = set(query_lower.split())

        # Expand synonyms
        for term in list(expanded_terms):
            for key, values in synonyms.items():
                if term in values:
                    expanded_terms.update(values)
                    break

        # Extract structured patterns
        parsed = {
            'original': query,
            'expanded_terms': list(expanded_terms),
            'asset_ids': [],
            'status_codes': [],
            'condition_codes': [],
            'has_numeric_filter': False,
            'field_value_pairs': []
        }

        # Extract Asset IDs (patterns like A-001, AST-123, etc.)
        asset_id_pattern = r'\b[A-Z]{1,4}[-_]?\d{3,6}\b'
        parsed['asset_ids'] = re.findall(asset_id_pattern, query, re.IGNORECASE)

        # Extract condition codes (R1, R2, R3, R4, R5)
        condition_pattern = r'\bR[1-5]\b'
        parsed['condition_codes'] = re.findall(condition_pattern, query, re.IGNORECASE)

        # Extract status keywords
        status_keywords = ['poor', 'fair', 'good', 'excellent', 'failed', 'working', 'operational']
        for keyword in status_keywords:
            if keyword in query_lower:
                parsed['status_codes'].append(keyword)

        # Detect numeric filters (e.g., "more than 100", "greater than 50")
        if any(word in query_lower for word in ['>', '<', 'more than', 'less than', 'greater', 'fewer']):
            parsed['has_numeric_filter'] = True

        return parsed

    def direct_field_lookup(self, parsed_query: Dict[str, Any], asset_index: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Perform direct lookup using field indexes for exact matches.

        Args:
            parsed_query: Preprocessed query
            asset_index: Asset index data

        Returns:
            List of directly matched assets
        """
        direct_matches = []
        indexes = asset_index.get('indexes', {})

        # Check for Asset ID direct lookup
        if parsed_query['asset_ids']:
            asset_id_index = indexes.get('by_field', {}).get('Asset ID', {})
            for asset_id in parsed_query['asset_ids']:
                if asset_id in asset_id_index:
                    direct_matches.extend(asset_id_index[asset_id])

        # Check for condition code lookup
        if parsed_query['condition_codes']:
            condition_index = indexes.get('by_field', {}).get('Condition', {})
            for cond in parsed_query['condition_codes']:
                if cond in condition_index:
                    direct_matches.extend(condition_index[cond])

        return direct_matches

    def search_relevant_assets(self, query: str, asset_index: Dict[str, Any], max_assets: int = 50) -> List[Dict[str, Any]]:
        """
        Enhanced search with query preprocessing and direct lookups.

        Args:
            query: User query
            asset_index: Asset index data
            max_assets: Maximum number of assets to return (increased from 20 to 50)

        Returns:
            List of relevant assets
        """
        # Preprocess query
        parsed_query = self.preprocess_query(query)

        # Try direct field lookup first
        direct_matches = self.direct_field_lookup(parsed_query, asset_index)
        if direct_matches:
            print(f"[OK] Found {len(direct_matches)} direct matches")
            return direct_matches[:max_assets]

        # Fall back to enhanced keyword search with expanded terms
        query_lower = query.lower()
        assets = asset_index.get('assets', [])
        expanded_terms = parsed_query['expanded_terms']

        relevant_assets = []
        for asset in assets:
            score = 0
            # Check if any keyword appears in asset fields
            asset_text = ' '.join([str(v).lower() for v in asset.values() if v])

            # Score based on expanded terms (better synonym matching)
            for term in expanded_terms:
                if term in asset_text:
                    # Exact field value match gets higher score
                    score += 3 if f" {term} " in f" {asset_text} " else 1

            if score > 0:
                relevant_assets.append((score, asset))

        # Sort by relevance score
        relevant_assets.sort(key=lambda x: x[0], reverse=True)

        # Return top matches
        return [asset for score, asset in relevant_assets[:max_assets]]

    def rerank_with_flash(self, query: str, assets: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Rerank assets using Gemini Flash for better relevance.

        Args:
            query: Search query
            assets: List of candidate assets
            top_k: Number of top results to return

        Returns:
            Reranked assets
        """
        if not self.use_two_stage or not self.flash_model or len(assets) <= top_k:
            return assets[:top_k]

        try:
            # Create concise asset representations
            asset_summaries = []
            for i, asset in enumerate(assets[:20]):  # Only rerank top 20
                summary = f"{i+1}. "
                if 'Asset ID' in asset:
                    summary += f"ID: {asset['Asset ID']}, "
                if 'Description' in asset:
                    summary += f"Desc: {asset['Description']}, "
                if 'Condition' in asset:
                    summary += f"Cond: {asset['Condition']}"
                asset_summaries.append(summary)

            # Ask Flash to rerank
            rerank_prompt = f"""Given this query: "{query}"

Rank these assets by relevance (1=most relevant):
{chr(10).join(asset_summaries)}

Return ONLY the numbers of the top {top_k} most relevant assets, comma-separated (e.g., "3,1,7,2,5").
"""

            response = self.flash_model.generate_content(rerank_prompt)
            rankings_text = response.text.strip()

            # Parse rankings
            try:
                rankings = [int(x.strip()) - 1 for x in rankings_text.split(',') if x.strip().isdigit()]
                reranked = [assets[i] for i in rankings if 0 <= i < len(assets)]
                print(f"[OK] Reranked {len(reranked)} assets using Flash")
                return reranked[:top_k]
            except:
                print(f"[WARN] Reranking parse failed, using original order")
                return assets[:top_k]

        except Exception as e:
            print(f"[WARN] Reranking failed: {e}, using original order")
            return assets[:top_k]

    def search_relevant_iso_content(self, query: str, iso_kb: Dict[str, Any], max_chunks: int = 5) -> List[Dict[str, Any]]:
        """
        Search for relevant ISO standard content using semantic vector search or keyword fallback.

        Args:
            query: User query
            iso_kb: ISO knowledge base
            max_chunks: Maximum number of chunks to return

        Returns:
            List of relevant ISO chunks
        """
        all_chunks = iso_kb.get('all_chunks', [])

        if not all_chunks:
            return []

        # Check if chunks have embeddings
        has_embeddings = any('embedding' in chunk for chunk in all_chunks)

        # Use vector search if embeddings are available
        if self.use_iso_embeddings and has_embeddings and self.iso_embedding_manager:
            print(f"[INFO] Using semantic vector search for ISO content (hybrid mode)")

            # Use hybrid search (vector + keyword)
            try:
                results = self.iso_embedding_manager.hybrid_search(
                    query=query,
                    chunks=all_chunks,
                    top_k=max_chunks,
                    vector_weight=0.7,  # 70% vector similarity
                    keyword_weight=0.3   # 30% keyword matching
                )

                # Extract just the chunks (results are tuples of (chunk, score))
                relevant_chunks = [chunk for chunk, score in results]

                # If semantic search returned results, use them
                if relevant_chunks:
                    print(f"[OK] Found {len(relevant_chunks)} relevant ISO chunks (semantic search)")
                    return relevant_chunks
                else:
                    print(f"[WARN] Semantic search returned 0 results, falling back to keyword search")
                    # Fall through to keyword search below

            except Exception as e:
                print(f"[WARN] Vector search failed: {e}, falling back to keyword search")
                # Fall through to keyword search below

        # Fallback to keyword search
        print(f"[INFO] Using keyword search for ISO content (total chunks: {len(all_chunks)})")
        query_lower = query.lower()
        keywords = query_lower.split()
        print(f"[DEBUG] Keywords: {keywords}")

        relevant_chunks = []
        for chunk in all_chunks:
            score = 0
            # Handle both old 'content' and new 'text' field names
            chunk_text = chunk.get('text', chunk.get('content', '')).lower()

            for keyword in keywords:
                if len(keyword) > 2 and keyword in chunk_text:
                    score += chunk_text.count(keyword)

            if score > 0:
                relevant_chunks.append((score, chunk))

        # Sort by relevance
        relevant_chunks.sort(key=lambda x: x[0], reverse=True)

        result = [chunk for score, chunk in relevant_chunks[:max_chunks]]
        print(f"[OK] Found {len(result)} relevant ISO chunks (keyword search)")
        return result

    def build_context(self, query: str, asset_index: Dict[str, Any], iso_kb: Dict[str, Any]) -> str:
        """
        Build context for RAG with citation tracking.

        Args:
            query: User query
            asset_index: Asset index
            iso_kb: ISO knowledge base

        Returns:
            Context string
        """
        # Reset citations for new query
        self.citation_formatter.reset()

        context_parts = []

        # Add asset statistics (only if asset_index provided)
        if asset_index:
            stats = asset_index.get('statistics', {})
            context_parts.append(f"=== ASSET REGISTER OVERVIEW ===")
            context_parts.append(f"Total Assets: {stats.get('total_assets', 0)}")
            context_parts.append(f"Total Fields: {stats.get('total_fields', 0)}")

            # Add field-level statistics from indexes
            indexes = asset_index.get('indexes', {})
            if indexes and 'statistics' in indexes:
                context_parts.append(f"\n=== ASSET BREAKDOWN BY KEY FIELDS ===")
                for field, field_stats in indexes['statistics'].items():
                    context_parts.append(f"\n{field}:")
                    value_counts = field_stats.get('value_counts', {})
                    for value, count in list(value_counts.items())[:15]:  # Show top 15
                        context_parts.append(f"  - {value}: {count} assets")
                    if field_stats.get('unique_values', 0) > 15:
                        context_parts.append(f"  ... and {field_stats['unique_values'] - 15} more unique values")

            # Add relevant assets with citation tracking
            relevant_assets = self.search_relevant_assets(query, asset_index)

            # Rerank with Flash if two-stage is enabled
            if relevant_assets and self.use_two_stage:
                relevant_assets = self.rerank_with_flash(query, relevant_assets, top_k=10)
        else:
            relevant_assets = []
        if relevant_assets:
            context_parts.append(f"\n=== RELEVANT ASSETS (Top {len(relevant_assets)}) ===")

            # Group by source file for citations
            by_source = {}
            for asset in relevant_assets[:10]:
                source = asset.get('_source_file', 'Unknown')
                if source not in by_source:
                    by_source[source] = []
                by_source[source].append(asset)

            # Add citation for each source file
            for source_file, assets in by_source.items():
                asset_ids = [a.get('Asset ID', a.get('ID', '')) for a in assets if a.get('Asset ID') or a.get('ID')]

                # Add citation
                cit_num = self.citation_formatter.add_asset_citation(
                    asset_ids=asset_ids,
                    source_file=source_file,
                    sheet_name=assets[0].get('_source_sheet', 'Sheet1'),
                    field='Multiple fields',
                    filter_criteria=f"Query: {query[:50]}...",
                    count=len(assets)
                )

                context_parts.append(f"\n[Citation {cit_num}] From {source_file}:")
                for i, asset in enumerate(assets, 1):
                    asset_summary = {k: v for k, v in asset.items() if not k.startswith('_')}
                    context_parts.append(f"\nAsset {i}:")
                    context_parts.append(json.dumps(asset_summary, indent=2, ensure_ascii=False))

        # Add schema info (only if asset_index provided)
        if asset_index:
            schema = asset_index.get('schema', {})
            if schema.get('fields'):
                context_parts.append(f"\n=== AVAILABLE FIELDS ===")
                fields_list = list(schema['fields'].keys())[:20]
                context_parts.append(", ".join(fields_list))

        # Add relevant ISO content with citation tracking (only if iso_kb provided)
        if iso_kb:
            relevant_iso = self.search_relevant_iso_content(query, iso_kb)
            print(f"[ISO SEARCH] Found {len(relevant_iso)} relevant ISO chunks")
        else:
            relevant_iso = []
            print(f"[ISO SEARCH] No ISO KB provided")
        if relevant_iso:
            context_parts.append(f"\n=== RELEVANT ISO 55000 STANDARDS ===")
            for i, chunk in enumerate(relevant_iso, 1):
                # Add ISO citation
                cit_num = self.citation_formatter.add_iso_citation(
                    iso_standard=chunk.get('iso_standard', 'ISO'),
                    section_number=chunk.get('section_number', 'N/A'),
                    section_title=chunk.get('title', chunk.get('section_title', '')),  # Support both 'title' and 'section_title'
                    page_range=chunk.get('page_range', 'N/A'),
                    quote=chunk.get('quote_excerpt', chunk.get('text', chunk.get('content', ''))[:200])
                )

                context_parts.append(f"\n[Citation {cit_num}] {chunk.get('iso_standard', 'ISO')} - Section {chunk.get('section_number', 'N/A')}")
                context_parts.append(f"Title: {chunk.get('section_title', '')}")
                context_parts.append(f"Pages: {chunk.get('page_range', 'N/A')}")
                content = chunk.get('text', chunk.get('content', ''))[:500]  # Limit content length
                context_parts.append(content)

        return "\n".join(context_parts)

    def create_system_prompt(self) -> str:
        """Create system prompt for ISO 55000 specialist with citations."""
        return """You are an expert ISO 55000 Asset Management Specialist.

Your role is to:
1. Answer questions about asset registers with high accuracy
2. Apply ISO 55000 series standards (ISO 55000, 55001, 55002) in your analysis
3. Provide insights on asset lifecycle management, risk assessment, and performance optimization
4. Use inline citations [1], [2], [3] when referencing data or standards
5. Suggest improvements for ISO 55000 compliance

Citation Guidelines:
- Use inline citations like [1], [2], [3] when referencing specific data or standards
- The context provided includes [Citation X] markers - reference these numbers
- Citations for asset data should reference [Citation numbers] from asset register context
- Citations for ISO standards should reference [Citation numbers] from ISO context

CRITICAL - Citation Format Rules (MUST FOLLOW):
- NEVER add a "References" section at the end of your response
- NEVER add a "Sources" section at the end of your response
- NEVER add a "Bibliography" section at the end of your response
- NEVER list citations in any format other than inline [1], [2], [3]
- The UI will automatically show citation details when users hover over the numbers
- Your response should END with your answer text, NOT with a list of sources

Formatting Guidelines for Structured Data:
- When presenting counts, breakdowns, or comparisons, use MARKDOWN TABLES
- Format tables using pipe (|) syntax:
  | Column 1 | Column 2 |
  |----------|----------|
  | Value 1  | Value 2  |
- For status/condition breakdowns, use table format like:
  | Status | Count |
  |--------|-------|
  | R1 Poor | 856 |
  | R2 Fair | 1234 |
- Tables are automatically rendered with styling in the UI
- Use tables for any data that has 3+ related items with consistent structure

General Guidelines:
- Always base answers on the provided asset data and ISO standards
- If information is missing, clearly state what's not available
- Use ISO 55000 terminology correctly
- Provide actionable recommendations
- Be clear and professional

ISO 55000 Core Principles:
- Value: Assets exist to provide value to the organization
- Alignment: Asset management aligns with organizational objectives
- Leadership: Leadership and workplace culture are determinants of value realization
- Assurance: Asset management gives assurance that assets will fulfill their required purpose
- Risk-based thinking: Asset management decisions consider risks and opportunities

Answer concisely and use inline citations [X] when referencing specific data or standards."""

    def _handle_structured_query(self, question: str, asset_index_file: str, iso_kb_file: str) -> Dict[str, Any]:
        """
        Handle structured field queries using SQL for high accuracy.

        Args:
            question: User question (e.g., "How many Precise Fire assets?")
            asset_index_file: Path to asset index (for citation metadata)
            iso_kb_file: Path to ISO knowledge base (for ISO context if needed)

        Returns:
            Query result with accurate SQL-based answer
        """
        # Build SQL query
        sql_query = self.structured_query_detector.build_sql_query(question)

        if not sql_query:
            print("[WARN] Could not build SQL query, falling back to RAG")
            # Fall back to regular RAG pipeline
            return self.query(question, asset_index_file, iso_kb_file)

        # Execute SQL query
        print(f"SQL: {sql_query['sql']}")
        print(f"Params: {sql_query['params']}")

        sql_result = self.structured_query_detector.execute_sql_query(sql_query)

        if not sql_result['success']:
            print(f"[ERROR] SQL query failed: {sql_result['error']}")
            return {
                'question': question,
                'answer': f"I encountered an error querying the database: {sql_result['error']}",
                'citations': [],
                'model': 'SQL',
                'context_size': 0,
                'citation_count': 0,
                'status': 'error'
            }

        # Format results into answer
        answer = self._format_sql_results(question, sql_query, sql_result)

        # Reset citations and add SQL-based citation
        self.citation_formatter.reset()

        # Add citation for SQL query
        cit_num = self.citation_formatter.add_asset_citation(
            asset_ids=[],  # SQL queries don't return specific asset IDs
            source_file="Asset Database (SQLite)",
            sheet_name="assets",
            field=sql_query.get('field', 'Multiple fields'),
            filter_criteria=sql_query['description'],
            count=sql_result.get('count', len(sql_result['results']))
        )

        # Add citation to answer
        answer += f" [{cit_num}]"

        print(f"[OK] SQL query returned {len(sql_result['results'])} results")

        return {
            'question': question,
            'answer': answer,
            'citations': self.citation_formatter.get_citations_as_json(),
            'model': 'SQL (Structured Query)',
            'context_size': len(str(sql_result)),
            'citation_count': self.citation_formatter.citation_counter,
            'status': 'success',
            'sql_query': sql_query['sql'],  # Include SQL for transparency
            'query_type': 'structured'
        }

    def _format_sql_results(self, question: str, sql_query: Dict[str, Any], sql_result: Dict[str, Any]) -> str:
        """
        Format SQL results into natural language answer.

        Args:
            question: Original question
            sql_query: SQL query metadata
            sql_result: SQL execution results

        Returns:
            Formatted answer text
        """
        results = sql_result['results']

        if sql_query['type'] == 'count':
            # Count query (single or multi-filter)
            if not results or len(results) == 0:
                return f"**0 assets** matching your criteria."

            count = results[0].get('count', 0)

            # Check if multi-filter
            if sql_query.get('filter_count', 0) > 1:
                # Multi-filter response - build natural description
                filters = sql_query.get('filters', [])
                description_parts = []

                for field, value in filters:
                    clean_field = field.split('__')[0] if '__' in field else field

                    if clean_field == 'data_source':
                        description_parts.insert(0, value)  # Put source first
                    elif clean_field == 'condition':
                        description_parts.append(f"in {value} condition")
                    elif clean_field == 'criticality':
                        description_parts.append(f"({value} criticality)")
                    elif clean_field == 'current_age':
                        # Age comparisons
                        if '__gt' in field:
                            description_parts.append(f"over {value} years old")
                        elif '__lt' in field:
                            description_parts.append(f"under {value} years old")
                    else:
                        description_parts.append(f"{clean_field}='{value}'")

                description = ' '.join(description_parts)
                return f"**{count:,}** {description} assets."
            else:
                # Single filter response
                # Check if we have 'field' and 'value' or need to extract from 'filters'
                if 'filters' in sql_query and sql_query['filters']:
                    field, value = sql_query['filters'][0]
                else:
                    value = sql_query.get('value', 'value')
                    field = sql_query.get('field', 'field')

                # Natural formatting based on field type
                if field == 'data_source':
                    return f"**{count:,}** {value} assets."
                elif field == 'condition':
                    return f"**{count:,}** assets in {value} condition."
                elif field == 'criticality':
                    return f"**{count:,}** {value} criticality assets."
                else:
                    return f"**{count:,}** {value} assets."

        elif sql_query['type'] == 'groupby':
            # Group by query - return breakdown as markdown table
            if not results or len(results) == 0:
                return "I found no assets to group."

            field = sql_query.get('field', 'field')
            lines = []
            lines.append(f"Here's the breakdown by {field}:\n")
            lines.append(f"| {field.title()} | Count |")
            lines.append("|" + "-" * 30 + "|" + "-" * 10 + "|")

            for row in results[:20]:  # Show top 20
                field_value = row.get(field, 'Unknown')
                count = row.get('count', 0)
                lines.append(f"| {field_value} | {count:,} |")

            if len(results) > 20:
                total_remaining = sum(row.get('count', 0) for row in results[20:])
                lines.append(f"| *...and {len(results) - 20} more* | {total_remaining:,} |")

            # Add total
            total = sum(row.get('count', 0) for row in results)
            lines.append(f"| **TOTAL** | **{total:,}** |")

            return "\n".join(lines)

        else:
            # Generic result formatting
            return f"I found {len(results)} results for your query."

    def query(self, question: str, asset_index_file: str, iso_kb_file: str) -> Dict[str, Any]:
        """
        Query the asset register with RAG.

        Args:
            question: User question
            asset_index_file: Path to asset index
            iso_kb_file: Path to ISO knowledge base

        Returns:
            Query result with answer and metadata
        """
        print(f"\n=== Processing Query ===")
        print(f"Question: {question}\n")

        # STEP 1: Check if this is a structured field query -> use SQL for accuracy
        if self.structured_query_detector:
            if self.structured_query_detector.is_structured_query(question):
                print("[STRUCTURED QUERY DETECTED] Using SQL for high accuracy...")
                return self._handle_structured_query(question, asset_index_file, iso_kb_file)

        # STEP 2: Natural language query -> use RAG pipeline
        # Load data
        asset_index = None
        if asset_index_file:
            print("Loading asset index...")
            asset_index = self.load_asset_index(asset_index_file)
        else:
            print("No asset index provided (ISO KB only mode)")

        iso_kb = None
        if iso_kb_file:
            print("Loading ISO knowledge base...")
            iso_kb = self.load_iso_knowledge(iso_kb_file)
        else:
            print("No ISO knowledge base provided")

        # Build context
        print("Building context with RAG...")
        context = self.build_context(question, asset_index, iso_kb)

        # Create prompt
        system_prompt = self.create_system_prompt()

        full_prompt = f"""{system_prompt}

=== CONTEXT ===
{context}

=== QUESTION ===
{question}

=== ANSWER ===
Please provide a comprehensive answer based on the asset data and ISO standards above."""

        # Query Gemini
        print("Querying Gemini...")
        try:
            response = self.model.generate_content(full_prompt)

            # Return answer and citations separately for NotebookLM-style popups
            result = {
                'question': question,
                'answer': response.text,  # Answer WITHOUT references section
                'citations': self.citation_formatter.get_citations_as_json(),  # Structured citations
                'model': self.model_name,
                'context_size': len(context),
                'citation_count': self.citation_formatter.citation_counter,
                'status': 'success'
            }

            print(f"\n[OK] Query successful ({self.citation_formatter.citation_counter} citations)")
            return result

        except Exception as e:
            print(f"\n[ERROR] Query failed: {e}")
            return {
                'question': question,
                'answer': None,
                'error': str(e),
                'status': 'error'
            }

    def interactive_mode(self, asset_index_file: str, iso_kb_file: str):
        """
        Interactive query mode.

        Args:
            asset_index_file: Path to asset index
            iso_kb_file: Path to ISO knowledge base
        """
        print("\n" + "="*60)
        print("=== Asset Register ISO 55000 Specialist ===")
        print("="*60)
        print("\nI'm your AI assistant with expertise in ISO 55000 asset management.")
        print("Ask me anything about your asset registers!\n")
        print("Commands:")
        print("  - Type your question")
        print("  - Type 'suggest' for question suggestions")
        print("  - Type 'exit' to quit")
        print("="*60 + "\n")

        while True:
            try:
                question = input("\nYour question: ").strip()

                if not question:
                    continue

                if question.lower() in ['exit', 'quit', 'q']:
                    print("\n👋 Goodbye!")
                    break

                if question.lower() == 'suggest':
                    print("\n[Question suggestions would be generated by question_suggester.py]")
                    continue

                # Process query
                result = self.query(question, asset_index_file, iso_kb_file)

                if result['status'] == 'success':
                    print("\n" + "="*60)
                    print("ANSWER:")
                    print("="*60)
                    print(result['answer'])
                    print("="*60)
                else:
                    print(f"\n[ERROR] Error: {result.get('error')}")

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n[ERROR] Error: {e}")


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(description='Query asset registers with Gemini AI')
    parser.add_argument('--question', '-q', help='Question to ask')
    parser.add_argument('--asset-index', default='data/.tmp/asset_index.json',
                       help='Path to asset index file')
    parser.add_argument('--iso-kb', default='data/.tmp/iso_knowledge_base.json',
                       help='Path to ISO knowledge base file')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Interactive mode')
    parser.add_argument('--model', default='gemini-1.5-flash-latest',
                       help='Gemini model to use')

    args = parser.parse_args()

    try:
        engine = GeminiQueryEngine(model_name=args.model)

        if args.interactive:
            engine.interactive_mode(args.asset_index, args.iso_kb)
        elif args.question:
            result = engine.query(args.question, args.asset_index, args.iso_kb)

            if result['status'] == 'success':
                print("\n" + "="*60)
                print("ANSWER:")
                print("="*60)
                print(result['answer'])
                print("="*60)
            else:
                print(f"\n[ERROR] Error: {result.get('error')}")
                sys.exit(1)
        else:
            print("Please provide --question or use --interactive mode")
            parser.print_help()
            sys.exit(1)

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
