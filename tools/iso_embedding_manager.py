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
        self.embedding_model = 'models/text-embedding-004'
        self.embedding_dimension = 768

        print(f"[OK] ISO Embedding Manager initialized (model: {self.embedding_model})")

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

        # Calculate similarities
        results = []
        for chunk in chunks:
            # Check if chunk has embedding
            if 'embedding' not in chunk:
                print(f"[WARN] Chunk missing embedding, skipping: {chunk.get('chunk_id', 'unknown')}")
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
                     top_k: int = 5, vector_weight: float = 0.7,
                     keyword_weight: float = 0.3) -> List[Tuple[Dict[str, Any], float]]:
        """
        Hybrid search combining vector similarity and keyword matching.

        Args:
            query: Search query
            chunks: List of chunk dictionaries
            top_k: Number of top results to return
            vector_weight: Weight for vector similarity (0.0 to 1.0)
            keyword_weight: Weight for keyword matching (0.0 to 1.0)

        Returns:
            List of (chunk, combined_score) tuples
        """
        # Vector search
        vector_results = self.semantic_search(query, chunks, top_k=top_k * 2, similarity_threshold=0.0)
        vector_scores = {id(chunk): score for chunk, score in vector_results}

        # Keyword search (simple BM25-like scoring)
        query_lower = query.lower()
        query_terms = set(query_lower.split())
        keyword_scores = {}

        for chunk in chunks:
            text = chunk.get('text', '').lower()
            score = 0

            # Count term frequencies
            for term in query_terms:
                if len(term) > 2:  # Ignore very short terms
                    count = text.count(term)
                    if count > 0:
                        # Simple scoring: more occurrences = higher score
                        score += count * (1 / (1 + count))  # Diminishing returns

            if score > 0:
                keyword_scores[id(chunk)] = score

        # Normalize keyword scores to 0-1 range
        if keyword_scores:
            max_keyword_score = max(keyword_scores.values())
            if max_keyword_score > 0:
                keyword_scores = {k: v / max_keyword_score for k, v in keyword_scores.items()}

        # Combine scores
        combined_results = []
        all_chunks = {id(chunk): chunk for chunk in chunks}
        all_chunk_ids = set(vector_scores.keys()) | set(keyword_scores.keys())

        for chunk_id in all_chunk_ids:
            chunk = all_chunks[chunk_id]

            # Get scores (default to 0 if not found)
            vec_score = vector_scores.get(chunk_id, 0.0)
            kw_score = keyword_scores.get(chunk_id, 0.0)

            # Calculate weighted combination
            combined_score = (vector_weight * vec_score) + (keyword_weight * kw_score)

            if combined_score > 0:
                combined_results.append((chunk, combined_score))

        # Sort by combined score
        combined_results.sort(key=lambda x: x[1], reverse=True)

        return combined_results[:top_k]

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
        kb['embedding_metadata'] = {
            'model': self.embedding_model,
            'dimension': self.embedding_dimension,
            'total_chunks': len(chunks)
        }

        # Save
        with open(kb_file, 'w', encoding='utf-8') as f:
            json.dump(kb, f, indent=2, ensure_ascii=False)

        print(f"[OK] Saved {len(chunks)} chunks with embeddings to {kb_file}")


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


if __name__ == '__main__':
    example_usage()
