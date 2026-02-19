#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISO Embedding Manager
Handles vector embeddings for ISO standard chunks for semantic search.
"""

import os
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import google.generativeai as genai
from dotenv import load_dotenv


class ISOEmbeddingManager:
    """Manages vector embeddings for ISO standard chunks."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize embedding manager.

        Args:
            api_key: Google Gemini API key (optional, reads from .env if not provided)
        """
        load_dotenv()

        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key or self.api_key == 'your_gemini_api_key_here':
            raise ValueError(
                "Gemini API key not found. Please set GEMINI_API_KEY in .env file.\n"
                "Get your API key from: https://makersuite.google.com/app/apikey"
            )

        # Configure Gemini
        genai.configure(api_key=self.api_key)

        # Embedding model settings
        # Use gemini-embedding-001 (the current supported model)
        self.embedding_model = 'models/gemini-embedding-001'
        self.embedding_dimension = 3072
        self.embedding_version = 'v2.0'  # v2: Upgraded to gemini-embedding-001 (3072 dim)
        
        # API Cost Tracking
        self.api_calls = 0
        self.tokens_processed = 0  # Estimation based on char count / 4
        
        # Initialize Advanced Search Components
        try:
            from faiss_index_manager import FAISSIndexManager
            self.faiss_manager = FAISSIndexManager(dimension=self.embedding_dimension)
        except ImportError:
            self.faiss_manager = None
            
        try:
            from bm25_scorer import BM25Scorer
            self.bm25_scorer = BM25Scorer()
        except ImportError:
            self.bm25_scorer = None
            
        try:
            from cross_encoder_reranker import CrossEncoderReranker
            self.reranker = CrossEncoderReranker()
        except ImportError:
            self.reranker = None
            
        # Index state tracking
        self.indexed_chunk_ids = set()

        print(f"[OK] ISO Embedding Manager initialized (model: {self.embedding_model}, version: {self.embedding_version})")
        if self.faiss_manager and self.faiss_manager.is_available:
            print("[OK] FAISS acceleration enabled")
        if self.bm25_scorer and self.bm25_scorer.is_available:
            print("[OK] BM25 scoring enabled")
        if self.reranker and self.reranker.is_available:
            print("[OK] Cross-Encoder re-ranking enabled")

    def generate_embedding(self, text: str, task_type: str = "retrieval_document") -> np.ndarray:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed
            task_type: Task type for embedding (retrieval_document or retrieval_query)

        Returns:
            Numpy array of embedding vector (768 dimensions)
        """
        try:
            self.api_calls += 1
            # Estimate tokens (rough approximation)
            self.tokens_processed += len(text) // 4
            
            response = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type=task_type
            )
            return np.array(response['embedding'])
        except Exception as e:
            print(f"[ERROR] Failed to generate embedding: {e}")
            return np.zeros(self.embedding_dimension)

    def generate_embeddings_batch(self, texts: List[str], task_type: str = "retrieval_document",
                                  batch_size: int = 100) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts in batches.

        Args:
            texts: List of texts to embed
            task_type: Task type for embedding
            batch_size: Number of texts to process in each batch

        Returns:
            List of embedding vectors
        """
        embeddings = []
        total = len(texts)

        print(f"[INFO] Generating {total} embeddings in batches of {batch_size}...")

        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]
            batch_end = min(i + batch_size, total)

            print(f"[INFO] Processing batch {i//batch_size + 1} ({i+1}-{batch_end}/{total})...")

            for text in batch:
                embedding = self.generate_embedding(text, task_type)
                embeddings.append(embedding)

        print(f"[OK] Generated {len(embeddings)} embeddings")
        return embeddings

    def _ensure_indexes(self, chunks: List[Dict[str, Any]]):
        """Ensure FAISS and BM25 indexes are built and up-to-date."""
        current_chunk_ids = {id(c) for c in chunks}
        
        # If indexes already cover these chunks, skip
        if self.indexed_chunk_ids == current_chunk_ids:
            return

        print("[INFO] Building search indexes...")
        
        # Build FAISS Index
        if self.faiss_manager and self.faiss_manager.is_available:
            embeddings = []
            valid_chunks = []
            for chunk in chunks:
                if 'embedding' in chunk:
                    emb = chunk['embedding']
                    if isinstance(emb, list):
                        emb = np.array(emb)
                    embeddings.append(emb)
                    valid_chunks.append(chunk)
            
            if len(embeddings) > 0:
                self.faiss_manager.build_index(embeddings)
                self.faiss_chunks = valid_chunks  # Keep reference to map indices back to chunks
        
        # Build BM25 Index
        if self.bm25_scorer and self.bm25_scorer.is_available:
            corpus = []
            for chunk in chunks:
                # Combine title and text for keyword search
                text = chunk.get('text', '') or chunk.get('content', '')
                title = chunk.get('title', '') or chunk.get('section_title', '')
                corpus.append(f"{title} {text}")
            
            self.bm25_scorer.index_corpus(corpus)
            self.bm25_chunks = chunks
            
        self.indexed_chunk_ids = current_chunk_ids
        print("[OK] Search indexes updated")

    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score (0.0 to 1.0, where 1.0 is identical)
        """
        # Handle zero vectors
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    def semantic_search(self, query: str, chunks: List[Dict[str, Any]],
                       top_k: int = 5, similarity_threshold: float = 0.3) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search for most relevant chunks using semantic similarity.

        Args:
            query: Search query
            chunks: List of chunk dictionaries (must have 'embedding' key)
            top_k: Number of top results to return
            similarity_threshold: Minimum similarity score (0.0 to 1.0)

        Returns:
            List of (chunk, similarity_score) tuples, sorted by relevance
        """
        # Generate query embedding
        query_embedding = self.generate_embedding(query, task_type="retrieval_query")

        # Ensure indexes are ready
        self._ensure_indexes(chunks)

        # Use FAISS if available
        if self.faiss_manager and self.faiss_manager.is_available and hasattr(self, 'faiss_chunks'):
            indices, scores = self.faiss_manager.search(query_embedding, top_k=top_k*2) # Get more candidates
            results = []
            for i, idx in enumerate(indices):
                if idx != -1 and idx < len(self.faiss_chunks):
                    # FAISS returns cosine similarity directly if normalized
                    score = scores[i]
                    if score >= similarity_threshold:
                        results.append((self.faiss_chunks[idx], float(score)))
            
            # Sort and limit
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]

        # Fallback to Linear Scan
        results = []
        for chunk in chunks:
            # Check if chunk has embedding
            if 'embedding' not in chunk:
                # print(f"[WARN] Chunk missing embedding, skipping: {chunk.get('chunk_id', 'unknown')}")
                continue

            # Convert embedding to numpy array if it's a list
            chunk_embedding = chunk['embedding']
            if isinstance(chunk_embedding, list):
                chunk_embedding = np.array(chunk_embedding)

            # Calculate similarity
            similarity = self.cosine_similarity(query_embedding, chunk_embedding)

            # Only include if above threshold
            if similarity >= similarity_threshold:
                results.append((chunk, similarity))

        # Sort by similarity (highest first)
        results.sort(key=lambda x: x[1], reverse=True)

        # Return top k results
        return results[:top_k]

    def hybrid_search(self, query: str, chunks: List[Dict[str, Any]],
                     top_k: int = 5, rrf_k: int = 60) -> List[Tuple[Dict[str, Any], float]]:
        """
        Hybrid search using Reciprocal Rank Fusion (RRF).
        Combines Vector Search and BM25 Keyword Search results.
        
        RRF Score = 1 / (k + rank_vector) + 1 / (k + rank_keyword)
        
        Args:
            query: Search query
            chunks: List of chunk dictionaries
            top_k: Number of top results to return
            rrf_k: Constant for RRF formula (default 60 is standard)

        Returns:
            List of (chunk, rrf_score) tuples, sorted by score
        """
        self._ensure_indexes(chunks)
        
        # ── 1. Run Retrievers in Parallel ─────────────────────────────────────
        
        # A. Vector Search (Semantic)
        # Get more candidates than needed (top_k * 3) to allow for intersection
        vector_results = self.semantic_search(query, chunks, top_k=top_k * 3, similarity_threshold=0.0)
        # Create map of {chunk_id: rank} (0-indexed)
        vector_ranks = {id(chunk): rank for rank, (chunk, _) in enumerate(vector_results)}
        
        # B. Keyword Search (Lexical)
        keyword_ranks = {}
        if self.bm25_scorer and self.bm25_scorer.is_available:
            # Get raw scores
            raw_scores = self.bm25_scorer.get_scores(query)
            # Create list of (index, score) and sort
            valid_scores = []
            for i, score in enumerate(raw_scores or []):
                if i < len(self.bm25_chunks) and score > 0:
                    valid_scores.append((self.bm25_chunks[i], score))
            
            # Sort by score desc to get ranks
            valid_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Keep top candidates only
            top_keywords = valid_scores[:top_k * 3]
            keyword_ranks = {id(chunk): rank for rank, (chunk, _) in enumerate(top_keywords)}

        # ── 2. Fuse Scores (RRF) ──────────────────────────────────────────────
        all_candidates = set(vector_ranks.keys()) | set(keyword_ranks.keys())
        chunk_map = {id(c): c for c in chunks}
        
        fused_scores = []
        for chunk_id in all_candidates:
            if chunk_id not in chunk_map:
                continue
                
            # RRF Formula: sum(1 / (k + rank))
            score = 0.0
            
            if chunk_id in vector_ranks:
                score += 1.0 / (rrf_k + vector_ranks[chunk_id])
            
            if chunk_id in keyword_ranks:
                score += 1.0 / (rrf_k + keyword_ranks[chunk_id])
                
            fused_scores.append((chunk_map[chunk_id], score))
            
        # Sort by RRF score descending
        fused_scores.sort(key=lambda x: x[1], reverse=True)
        return fused_scores[:top_k]

    def add_embeddings_to_chunks(self, chunks: List[Dict[str, Any]],
                                force_regenerate: bool = False) -> List[Dict[str, Any]]:
        """
        Add embeddings to ISO chunks (or update existing ones).

        Args:
            chunks: List of chunk dictionaries
            force_regenerate: If True, regenerate all embeddings even if they exist

        Returns:
            Updated chunks with embeddings
        """
        # Separate chunks that need embedding
        chunks_to_embed = []
        texts_to_embed = []

        for chunk in chunks:
            if force_regenerate or 'embedding' not in chunk:
                chunks_to_embed.append(chunk)

                # Combine title/section_title and text/content for better embedding
                # Support both old format (content, section_title) and new format (text, title)
                text = chunk.get('text', chunk.get('content', ''))
                title = chunk.get('title', chunk.get('section_title', ''))

                if title:
                    text = f"{title}\n{text}"

                texts_to_embed.append(text)

        if not texts_to_embed:
            print("[INFO] All chunks already have embeddings")
            return chunks

        print(f"[INFO] Generating embeddings for {len(texts_to_embed)} chunks...")

        # Generate embeddings
        embeddings = self.generate_embeddings_batch(texts_to_embed)

        # Add embeddings to chunks
        for i, chunk in enumerate(chunks_to_embed):
            chunk['embedding'] = embeddings[i].tolist()  # Convert numpy array to list for JSON serialization

        print(f"[OK] Added embeddings to {len(chunks_to_embed)} chunks")

        return chunks

    def save_embeddings(self, kb_file: str, chunks: List[Dict[str, Any]]):
        """
        Save chunks with embeddings to knowledge base file.

        Args:
            kb_file: Path to ISO knowledge base JSON file
            chunks: List of chunks with embeddings
        """
        # Load existing knowledge base
        if os.path.exists(kb_file):
            with open(kb_file, 'r', encoding='utf-8') as f:
                kb = json.load(f)
        else:
            kb = {}

        # Update chunks
        kb['all_chunks'] = chunks
        
        # Add rich metadata
        from datetime import datetime
        kb['embedding_metadata'] = {
            'model': self.embedding_model,
            'version': self.embedding_version,
            'dimension': self.embedding_dimension,
            'total_chunks': len(chunks),
            'generated_at': datetime.now().isoformat(),
            'api_calls_used': self.api_calls,
            'estimated_tokens': self.tokens_processed
        }

        # Save
        with open(kb_file, 'w', encoding='utf-8') as f:
            json.dump(kb, f, indent=2, ensure_ascii=False)

        print(f"[OK] Saved {len(chunks)} chunks with embeddings to {kb_file}")
        print(f"[METADATA] Calls: {self.api_calls}, Est. Tokens: {self.tokens_processed}")


def example_usage():
    """Example of how to use the ISO Embedding Manager."""
    manager = ISOEmbeddingManager()

    # Example chunks
    chunks = [
        {
            'chunk_id': 'iso55001_s6.1_p15',
            'standard': 'ISO 55001:2014',
            'section': '6.1',
            'page': 15,
            'title': 'Risk Management',
            'text': 'The organization shall establish, implement and maintain processes for managing risk associated with assets...'
        },
        {
            'chunk_id': 'iso55001_s8.3_p24',
            'standard': 'ISO 55001:2014',
            'section': '8.3',
            'page': 24,
            'title': 'Management of Change',
            'text': 'The organization shall establish, implement and maintain process(es) to manage changes that impact the asset management system...'
        }
    ]

    # Add embeddings
    chunks_with_embeddings = manager.add_embeddings_to_chunks(chunks)

    # Semantic search
    query = "How should I handle risk assessment for assets?"
    results = manager.semantic_search(query, chunks_with_embeddings, top_k=2)

    print(f"\nSearch results for: '{query}'")
    for chunk, score in results:
        print(f"\n[{score:.3f}] {chunk['standard']} - {chunk['title']}")
        print(f"  {chunk['text'][:100]}...")


    def get_api_stats(self) -> Dict[str, Any]:
        """Get current API usage statistics."""
        return {
            'api_calls': self.api_calls,
            'tokens_processed': self.tokens_processed,
            'estimated_cost_usd': self.tokens_processed * (0.000025 / 1000)  # ~$0.000025 per 1k chars
        }

if __name__ == '__main__':
    example_usage()
