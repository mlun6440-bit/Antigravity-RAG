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
import sqlite3
import logging

# Add citation support
sys.path.insert(0, os.path.dirname(__file__))
from citation_formatter import CitationFormatter
from structured_query_detector import StructuredQueryDetector

# Intent-based query pipeline (Phase 4 architecture)
try:
    from intent_query_pipeline import IntentBasedQueryPipeline
    INTENT_PIPELINE_AVAILABLE = True
except ImportError:
    INTENT_PIPELINE_AVAILABLE = False

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
        self.flash_model_name = os.getenv('GEMINI_FLASH_MODEL', 'gemini-3-flash-preview')
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

        # Try to load ISO embedding manager for ISO 55000 knowledge base
        try:
            from iso_embedding_manager import ISOEmbeddingManager
            self.iso_embedding_manager = ISOEmbeddingManager(api_key=self.api_key)
            self.use_iso_embeddings = True
            print(f"[OK] ISO semantic search enabled (vector embeddings)")
        except ImportError:
            self.iso_embedding_manager = None
            self.use_iso_embeddings = False
            print(f"[INFO] ISO embeddings not available")

        # Initialize Query Router and Cache (New Architecture)
        try:
            from query_router import LLMQueryRouter
            from query_cache import QueryCache
            
            self.query_router = LLMQueryRouter()
            self.query_cache = QueryCache(ttl_seconds=3600)
            self.use_new_architecture = True
            print(f"[OK] LLM Query Router & Cache enabled")
        except Exception as e:
            self.query_router = None
            self.query_cache = None
            self.use_new_architecture = False
            print(f"[WARN] New architecture components failed to load: {e}")

        # Initialize Intent-Based Query Pipeline (Phase 4)
        if INTENT_PIPELINE_AVAILABLE:
            try:
                self.intent_pipeline = IntentBasedQueryPipeline()
                print(f"[OK] Intent-Based Query Pipeline enabled")
            except Exception as e:
                self.intent_pipeline = None
                print(f"[WARN] Intent pipeline failed to load: {e}")
        else:
            self.intent_pipeline = None

    def load_asset_index(self, index_file: str) -> Dict[str, Any]:
        """Load asset index."""
        with open(index_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    # ==================== LIGHT SQL SUPPORT ====================
    
    def _init_sqlite_db(self, asset_index: Dict[str, Any]) -> sqlite3.Connection:
        """
        Load asset data into an in-memory SQLite database.
        
        Args:
            asset_index: Asset index dictionary
            
        Returns:
            SQLite connection
        """
        conn = sqlite3.connect(':memory:')
        assets = asset_index.get('assets', [])
        
        if not assets:
            print("[WARN] No assets found for SQL database")
            return conn
            
        # Lazy import pandas to avoid startup hang
        import pandas as pd
            
        # Convert to DataFrame and load to SQL
        df = pd.DataFrame(assets)
        
        # Clean column names (remove spaces, special chars)
        df.columns = [c.replace(' ', '_').replace('-', '_').replace('.', '_') for c in df.columns]
        
        # Remove empty column names and internal columns
        empty_cols = [c for c in df.columns if not c or c.strip() == '']
        internal_cols = [c for c in df.columns if c.startswith('_')]
        cols_to_drop = list(set(empty_cols + internal_cols))
        if cols_to_drop:
            print(f"[INFO] Dropping {len(cols_to_drop)} invalid columns: {cols_to_drop[:5]}...")
        df = df.drop(columns=cols_to_drop, errors='ignore')
        
        df.to_sql('assets', conn, index=False, if_exists='replace')
        
        print(f"[OK] Loaded {len(df)} assets into SQLite ({len(df.columns)} columns)")
        return conn
    
    def _get_sql_schema(self, conn: sqlite3.Connection) -> str:
        """Get schema description for SQL generation."""
        cursor = conn.execute("PRAGMA table_info(assets)")
        columns = cursor.fetchall()
        schema = "Table: assets\nColumns:\n"
        for col in columns:
            schema += f"  - {col[1]} ({col[2]})\n"
        return schema
    
    def _classify_query(self, question: str) -> str:
        """
        Classify if query should use SQL (analytical) or RAG (semantic).
        
        Args:
            question: User question
            
        Returns:
            'SQL' or 'RAG'
        """
        if self.use_new_architecture and self.query_router:
            # Use LLM-based routing
            return self.query_router.classify_query(question)

        # Fallback: Quick heuristic classification
        sql_keywords = ['how many', 'count', 'total', 'average', 'sum', 'list all', 
                        'show all', 'which assets', 'what assets', 'number of']
        rag_keywords = ['how to', 'how do', 'explain', 'recommend', 'should', 
                        'iso 55000', 'best practice', 'maintain', 'why']
        
        q_lower = question.lower()
        
        for kw in rag_keywords:
            if kw in q_lower:
                return 'RAG'
                
        for kw in sql_keywords:
            if kw in q_lower:
                return 'SQL'
        
        # Default to RAG for ambiguous queries
        return 'RAG'
    
    def _generate_and_execute_sql(self, question: str, conn: sqlite3.Connection) -> Dict[str, Any]:
        """
        Generate SQL from natural language and execute it.
        
        Args:
            question: User question
            conn: SQLite connection
            
        Returns:
            Query result with answer
        """
        schema = self._get_sql_schema(conn)
        
        # Ask Gemini to generate SQL
        sql_prompt = f"""You are a SQL expert. Convert this question to a SQLite query.

Schema:
{schema}

Question: {question}

Rules:
- Return ONLY the SQL query, no explanation
- Use SQLite syntax
- Table name is 'assets'
- For counts, use COUNT(*)
- For conditions, use LIKE '%value%' for partial matches
- Return at most 20 rows for list queries

SQL:"""

        try:
            response = self.flash_model.generate_content(sql_prompt) if self.flash_model else self.model.generate_content(sql_prompt)
            sql_query = response.text.strip()
            
            # Clean up the SQL (remove markdown code blocks if present)
            sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
            
            print(f"[SQL] Generated: {sql_query}")
            
            # Execute the query
            cursor = conn.execute(sql_query)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # Format result
            if len(results) == 1 and len(columns) == 1:
                # Single value (e.g., COUNT)
                answer = f"**{results[0][0]}**"
            else:
                # Table result
                if results:
                    # Build markdown table
                    answer = "| " + " | ".join(columns) + " |\n"
                    answer += "| " + " | ".join(["---"] * len(columns)) + " |\n"
                    for row in results[:20]:
                        answer += "| " + " | ".join(str(v) for v in row) + " |\n"
                else:
                    answer = "No results found."
            
            return {
                'question': question,
                'answer': answer,
                'sql_query': sql_query,
                'row_count': len(results),
                'method': 'SQL',
                'citations': [],
                'status': 'success'
            }
            
        except Exception as e:
            print(f"[SQL ERROR] {e}")
            return {
                'question': question,
                'answer': f"SQL execution failed: {e}",
                'error': str(e),
                'method': 'SQL',
                'status': 'error'
            }
    
    # ==================== END LIGHT SQL SUPPORT ====================

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
            if hasattr(self, '_retrieval_methods'):
                self._retrieval_methods.append('asset:direct_lookup')
            return direct_matches[:max_assets]

        # Try semantic embedding search if available
        if self.use_embeddings and self.embedding_manager:
            try:
                assets = asset_index.get('assets', [])
                embeddings_file = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'data', '.tmp', 'asset_embeddings.npy'
                )
                asset_embeddings = self.embedding_manager.load_embeddings(embeddings_file)
                if asset_embeddings is not None and len(asset_embeddings) == len(assets):
                    results = self.embedding_manager.search_by_embedding(
                        query, asset_embeddings, assets, top_k=max_assets
                    )
                    if results:
                        print(f"[OK] Found {len(results)} assets via semantic embedding search")
                        if hasattr(self, '_retrieval_methods'):
                            self._retrieval_methods.append('asset:embedding_search')
                        return results
                    else:
                        print(f"[WARN] Embedding search returned 0 results, falling back to keyword")
                else:
                    print(f"[INFO] Asset embeddings not found or size mismatch, using keyword search")
            except Exception as e:
                print(f"[WARN] Asset embedding search failed: {e}, falling back to keyword")

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

        if relevant_assets and hasattr(self, '_retrieval_methods'):
            self._retrieval_methods.append('asset:keyword_search')

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
            print(f"[INFO] Using Hybrid RRF Search (Vector + BM25) for ISO content")

            try:
                # Use RRF Hybrid Search
                # Returns list of (chunk, score)
                results = self.iso_embedding_manager.hybrid_search(
                    query=query,
                    chunks=all_chunks,
                    top_k=max_chunks,
                    rrf_k=60
                )

                # Extract just the chunks
                relevant_chunks = [chunk for chunk, score in results]

                if relevant_chunks:
                    print(f"[OK] Found {len(relevant_chunks)} relevant ISO chunks (RRF Hybrid)")
                    if hasattr(self, '_retrieval_methods'):
                        self._retrieval_methods.append('iso:hybrid_rrf')
                    return relevant_chunks
                else:
                    print(f"[WARN] Hybrid search returned 0 results, falling back to legacy keyword search")

            except Exception as e:
                print(f"[WARN] Hybrid search failed: {e}, falling back to legacy keyword search")
        
        # Fallback to legacy keyword search (if embeddings/manager unavailable or failed)
        print(f"[INFO] Using legacy keyword search (BM25) for ISO content")

        # Try BM25 scorer
        try:
            from bm25_scorer import BM25Scorer
            bm25 = BM25Scorer()
            if bm25.is_available:
                corpus = [
                    f"{c.get('title', c.get('section_title', ''))} {c.get('text', c.get('content', ''))}"
                    for c in all_chunks
                ]
                if bm25.index_corpus(corpus):
                    scores = bm25.get_scores(query)
                    if scores:
                        scored = [(s, c) for s, c in zip(scores, all_chunks) if s > 0]
                        scored.sort(key=lambda x: x[0], reverse=True)
                        result = [chunk for _, chunk in scored[:max_chunks]]
                        if result:
                            print(f"[OK] Found {len(result)} relevant ISO chunks (BM25 fallback)")
                            if hasattr(self, '_retrieval_methods'):
                                self._retrieval_methods.append('iso:bm25_legacy')
                            return result
        except Exception as e:
            print(f"[WARN] BM25 fallback failed: {e}")

        # Final fallback: naive term counting
        query_lower = query.lower()
        keywords = query_lower.split()
        print(f"[DEBUG] Keywords (naive fallback): {keywords}")

        relevant_chunks = []
        for chunk in all_chunks:
            score = 0
            chunk_text = chunk.get('text', chunk.get('content', '')).lower()

            for keyword in keywords:
                if len(keyword) > 2 and keyword in chunk_text:
                    score += chunk_text.count(keyword)

            if score > 0:
                relevant_chunks.append((score, chunk))

        relevant_chunks.sort(key=lambda x: x[0], reverse=True)

        result = [chunk for score, chunk in relevant_chunks[:max_chunks]]
        print(f"[OK] Found {len(result)} relevant ISO chunks (naive keyword search)")
        if result and hasattr(self, '_retrieval_methods'):
            self._retrieval_methods.append('iso:naive_keyword')
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
        """Create system prompt for ISO 55000 specialist with citations and Generative UI."""
        return """You are an expert ISO 55000 Asset Management Specialist.

STRICT GUARDRAIL:
1. You must ONLY answer questions related to Asset Management, ISO 55000 standards, and the user's specific asset data.
2. If the user asks about ANYTHING else (e.g. general knowledge, history, cooking, coding unrelated to assets, personal advice, etc.), you must POLITELY REFUSE.
3. State clearly: "I am an Asset Management Specialist. I can only assist with inquiries related to your assets or ISO 55000 standards."

Your role is to:
1. Answer questions about asset registers with high accuracy
2. Apply ISO 55000 series standards (ISO 55000, 55001, 55002) in your analysis
3. Provide insights on asset lifecycle management, risk assessment, and performance optimization
4. Suggest improvements for ISO 55000 compliance
5. **GENERATE UI WIDGETS** to visualize data when appropriate

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
- For any simple structured data (small lists), use Markdown tables.
- CRITICAL: Ensure each table row is on a NEW LINE.
- Format:
  | Asset ID | Description | Status | Condition | Location |
  |---|---|---|---|---|
  | 123 | Pump | Active | Good | Bld A |

=== GENERATIVE UI INSTRUCTIONS (CRITICAL) ===
You have access to a "Generative UI" system.
Rule: If the user asks for a comparison, breakdown, distribution, or a count that makes sense to visualize, you MUST generate a JSON Widget.
Rule: Do NOT rely solely on Markdown tables for visual data. A Chart is much better.

Supported Widgets:
1. **Stat Card** (For single important numbers)
   - Use for: "Total Assets", "Count of X", "Score"
   - JSON: {"type": "stat_card", "title": "Total Pumps", "value": "42", "status": "success", "trend": "neutral"}

2. **Bar Chart** (For comparing categories)
   - Use for: "Breakdown by Location", "Assets by Manufacturer", "Condition Status Counts"
   - JSON: {"type": "bar_chart", "title": "Condition Breakdown", "labels": ["Poor", "Fair", "Good"], "values": [5, 12, 20]}

3. **Pie Chart** (For distributions/percentages)
   - Use for: "Percentage of Critical Assets", "Proportion of X vs Y"
   - JSON: {"type": "pie_chart", "title": "Asset Criticality", "segments": [{"label": "High", "value": 10}, {"label": "Low", "value": 90}]}

OUTPUT FORMAT:
Provide your text answer normally. Then, if a visualization applies, append the JSON block at the very end.
Example:
"Based on the register, there are 15 pumps.
[Inline Citation 1]

```json
[
  {"type": "stat_card", "title": "Total Pumps", "value": "15", "status": "info"}
]
```"

MANDATORY: If the user asks for "Breakdown", "Distribution", or "Count by X", you MUST generate a Chart widget.

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

Answer concisely using inline citations [X]. If appropriate, generate UI Widgets at the end."""

    def _handle_structured_query(self, question: str, asset_index_file: str, iso_kb_file: str) -> Dict[str, Any]:
        """
        Handle structured field queries using SQL for high accuracy.
        
        Uses Intent-Based Architecture when available:
        Human Question → LLM (intent) → Deterministic SQL → LLM (explanation)

        Args:
            question: User question (e.g., "How many Precise Fire assets?")
            asset_index_file: Path to asset index (for citation metadata)
            iso_kb_file: Path to ISO knowledge base (for ISO context if needed)

        Returns:
            Query result with accurate SQL-based answer
        """
        # Try intent-based pipeline first (Phase 4 architecture)
        if INTENT_PIPELINE_AVAILABLE and hasattr(self, 'intent_pipeline'):
            try:
                result = self.intent_pipeline.process(question)
                
                if result.get('success'):
                    # Reset citations and add SQL-based citation
                    self.citation_formatter.reset()
                    
                    # Add citation for SQL query
                    intent = result.get('intent', {})
                    cit_num = self.citation_formatter.add_asset_citation(
                        asset_ids=[],
                        source_file="Asset Database (SQLite)",
                        sheet_name="assets",
                        field=str(intent.get('filters', 'All')),
                        filter_criteria=f"Intent: {intent.get('action', 'unknown')}",
                        count=result.get('result', {}).get('count', 0)
                    )
                    
                    answer = result.get('answer', '') + f" [{cit_num}]"
                    
                    print(f"[INTENT] Query handled via intent pipeline: {intent.get('action')}")
                    
                    return {
                        'question': question,
                        'answer': answer,
                        'citations': self.citation_formatter.get_citations_as_json(),
                        'model': 'SQL (Intent-Based)',
                        'context_size': 0,
                        'citation_count': self.citation_formatter.citation_counter,
                        'status': 'success',
                        'sql_query': result.get('result', {}).get('sql', ''),
                        'query_type': 'structured',
                        'intent': intent
                    }
            except Exception as e:
                print(f"[WARN] Intent pipeline failed, falling back to pattern matching: {e}")
        
        # Fallback: Pattern-based SQL generation
        sql_query = self.structured_query_detector.build_sql_query(question)

        if not sql_query:
            print("[WARN] Could not build SQL query - returning 0 results")
            # Return proper empty result instead of recursive fallback
            return {
                'question': question,
                'answer': "I couldn't find any assets matching your criteria.",
                'citations': [],
                'model': 'SQL (Structured Query)',
                'context_size': 0,
                'citation_count': 0,
                'status': 'success'
            }

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
                    value = sql_query.get('value')
                    field = sql_query.get('field')
                
                # SPECIAL CASE: Count all (no filter) 
                if field is None:
                    return f"**{count:,}** total assets."

                # Natural formatting based on field type
                if field == 'data_source':
                    return f"**{count:,}** {value} assets."
                elif field == 'condition':
                    return f"**{count:,}** assets in {value} condition."
                elif field == 'criticality':
                    return f"**{count:,}** {value} criticality assets."
                elif field == 'location':
                    return f"**{count:,}** assets in {value}."
                elif 'current_age' in field:
                    if '__gt' in field:
                        return f"**{count:,}** assets over {value} years old."
                    elif '__lt' in field:
                        return f"**{count:,}** assets under {value} years old."
                    elif '__gte' in field:
                        return f"**{count:,}** assets {value} years or older."
                    elif '__lte' in field:
                        return f"**{count:,}** assets {value} years or younger."
                    else:
                        return f"**{count:,}** assets aged {value} years."
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

    def _handle_analytical_query(self, question: str, asset_index_file: str, iso_kb_file: str) -> Dict[str, Any]:
        """
        Handle analytical queries using hybrid SQL + LLM approach.
        
        Args:
            question: User question (e.g., "Analyze poor condition electrical assets per ISO 55001")
            asset_index_file: Path to asset index (not used, we use persistent DB)
            iso_kb_file: Path to ISO knowledge base
            
        Returns:
            Query result with SQL data + LLM analysis + citations
        """
        try:
            from analytical_query_handler import AnalyticalQueryHandler
            
            handler = AnalyticalQueryHandler(
                db_path='data/assets.db',
                gemini_model=self.model,
                iso_embedding_manager=self.iso_embedding_manager
            )
            
            result = handler.process_query(question, iso_kb_file)
            
            # Check for fallback conditions
            if result.get('status') == 'fallback':
                print(f"[FALLBACK] {result.get('reason', 'Unknown reason')}")
                print("[FALLBACK] Using RAG pipeline instead...")
                # Fall back to RAG - reload through query() with knowledge mode forced
                # To avoid infinite loop, temporarily disable structured detector
                original_detector = self.structured_query_detector
                self.structured_query_detector = None
                try:
                    return self.query(question, asset_index_file, iso_kb_file)
                finally:
                    self.structured_query_detector = original_detector
            
            elif result.get('status') == 'error':
                print(f"[ERROR] Analytical query failed: {result.get('error')}")
                print("[FALLBACK] Using RAG pipeline...")
                # Same fallback logic
                original_detector = self.structured_query_detector
                self.structured_query_detector = None
                try:
                    return self.query(question, asset_index_file, iso_kb_file)
                finally:
                    self.structured_query_detector = original_detector
            
            return result
            
        except ImportError as e:
            print(f"[ERROR] Could not import AnalyticalQueryHandler: {e}")
            print("[FALLBACK] Using RAG pipeline...")
            # Fallback to RAG
            original_detector = self.structured_query_detector
            self.structured_query_detector = None
            try:
                return self.query(question, asset_index_file, iso_kb_file)
            finally:
                self.structured_query_detector = original_detector

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
        # Check cache first (if enabled)
        if self.use_new_architecture and self.query_cache:
            cached_result = self.query_cache.get(
                query=question, 
                mode='general',
                asset_index=asset_index_file,
                iso_kb=iso_kb_file
            )
            if cached_result:
                print(f"[CACHE] Returning cached result for: {question[:30]}...")
                return cached_result

        print(f"\n=== Processing Query ===")
        print(f"Question: {question}\n")

        # STEP 1: Detect query mode (3-way routing)
        query_mode = None
        if self.structured_query_detector:
            query_mode = self.structured_query_detector.detect_query_mode(question)
            print(f"[ROUTER] Query mode detected: {query_mode}")
        else:
            query_mode = 'knowledge'  # Default fallback
        
        # STEP 2: Route based on mode
        if query_mode == 'structured':
            # SQL-only path for counts/lists
            print("[STRUCTURED QUERY] Using SQL for high accuracy...")
            result = self._handle_structured_query(question, asset_index_file, iso_kb_file)
            
            # Cache result
            if self.use_new_architecture and self.query_cache and result.get('status') == 'success':
                self.query_cache.put(question, result, mode='general', asset_index=asset_index_file, iso_kb=iso_kb_file)
            return result
        
        elif query_mode == 'analytical':
            # Hybrid SQL + LLM path for analysis
            print("[ANALYTICAL QUERY] Using hybrid SQL + LLM pipeline...")
            result = self._handle_analytical_query(question, asset_index_file, iso_kb_file)
            
            # Cache result
            if self.use_new_architecture and self.query_cache and result.get('status') == 'success':
                self.query_cache.put(question, result, mode='general', asset_index=asset_index_file, iso_kb=iso_kb_file)
            return result
        
        else:  # query_mode == 'knowledge'
            # RAG-only path for knowledge questions
            print("[KNOWLEDGE QUERY] Using RAG pipeline...")
            # Fall through to existing RAG logic below

        # STEP 3: Natural language query -> use RAG pipeline

        # Track retrieval methods used during this query
        self._retrieval_methods = []

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

        # ============ LIGHT SQL ROUTING ============
        # Classify query to determine if SQL or RAG is more appropriate
        query_type = self._classify_query(question)
        print(f"[ROUTER] Query classified as: {query_type}")
        
        if query_type == 'SQL' and asset_index:
            print("[SQL MODE] Using Light SQL for analytical query...")
            conn = self._init_sqlite_db(asset_index)
            result = self._generate_and_execute_sql(question, conn)
            conn.close()
            
            if result['status'] == 'success':
                print(f"[OK] SQL query returned {result.get('row_count', 0)} rows")
                return result
            else:
                print(f"[WARN] SQL failed, falling back to RAG: {result.get('error')}")
                # Fall through to RAG
        # ============ END LIGHT SQL ROUTING ============

        # Build context (RAG path)
        print("Building context with RAG...")
        context = self.build_context(question, asset_index, iso_kb)

        # Detect if context contains asset data (not just ISO standards)
        has_asset_data = '[Asset Data]' in context or 'Asset ID' in context
        
        # Create prompt
        system_prompt = self.create_system_prompt()

        # Build the answer prompt with conditional widget instructions
        answer_section = "Please provide a comprehensive answer based on the asset data and ISO standards above.\n\nIMPORTANT FORMATTING RULES:\n1. For ANY list of assets or structured data, you MUST use a Markdown Table.\n2. CONSTRAINT: Tables must have MAXIMUM 5 COLUMNS (Select the most relevant ones).\n3. Start every table row on a NEW LINE."
        
        # Only add widget instructions if there's asset data
        if has_asset_data:
            answer_section += "\n\nWIDGET GENERATION: Since this query involves asset data, you MAY generate charts/widgets if appropriate for visualization (stat cards, bar charts, pie charts)."
        else:
            answer_section += "\n\nNOTE: This query is about ISO standards only. DO NOT generate any charts or widgets."

        full_prompt = f"""{system_prompt}

=== CONTEXT ===
{context}

=== QUESTION ===
{question}

=== ANSWER ===
{answer_section}"""


        # Query Gemini
        print("Querying Gemini...")
        try:
            response = self.model.generate_content(full_prompt)
            full_text = response.text
            
            # Extract Widgets (JSON block at the end)
            answer_text = full_text
            widgets = []
            
            # Look for JSON code block at the end
            if "```json" in full_text:
                parts = full_text.split("```json")
                if len(parts) > 1:
                    potential_json = parts[-1].split("```")[0].strip()
                    try:
                        parsed = json.loads(potential_json)
                        if isinstance(parsed, list):
                            widgets = parsed
                            print(f"[UI] Generated {len(widgets)} widgets")
                            # Remove the JSON block from the user-facing answer
                            answer_text = parts[0].strip()
                    except json.JSONDecodeError:
                        print("[WARN] Failed to parse generated UI widgets JSON")

            # Return answer and citations separately for NotebookLM-style popups
            retrieval_methods = getattr(self, '_retrieval_methods', [])
            result = {
                'question': question,
                'answer': answer_text,  # Answer WITHOUT references section or JSON widgets
                'widgets': widgets,     # Generated UI components
                'citations': self.citation_formatter.get_citations_as_json(),  # Structured citations
                'model': self.model_name,
                'context_size': len(context),
                'citation_count': self.citation_formatter.citation_counter,
                'retrieval_methods': retrieval_methods,
                'status': 'success'
            }

            print(f"\n[OK] Query successful ({self.citation_formatter.citation_counter} citations)")
            
            # Cache the result
            if self.use_new_architecture and self.query_cache:
                self.query_cache.put(
                    query=question,
                    data=result,
                    mode='general',
                    asset_index=asset_index_file,
                    iso_kb=iso_kb_file
                )
                
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
    parser.add_argument('--model', default='gemini-3-flash-preview',
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
