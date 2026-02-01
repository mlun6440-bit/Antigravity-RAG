#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Embedding Manager for Semantic Search
Uses Gemini text-embedding-004 model for generating embeddings.
"""

import os
import json
import numpy as np
from typing import Dict, List, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()


class EmbeddingManager:
    """Manages embeddings for semantic search."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize embedding manager.

        Args:
            api_key: Google API key (defaults to GEMINI_API_KEY from .env)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        genai.configure(api_key=self.api_key)
        self.embedding_model = 'models/text-embedding-004'
        print(f"[OK] Initialized embedding model: {self.embedding_model}")

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"[ERROR] Failed to generate embedding: {e}")
            return []

    def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for a query.

        Args:
            query: Search query

        Returns:
            Embedding vector
        """
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=query,
                task_type="retrieval_query"
            )
            return result['embedding']
        except Exception as e:
            print(f"[ERROR] Failed to generate query embedding: {e}")
            return []

    def asset_to_text(self, asset: Dict[str, Any]) -> str:
        """
        Convert asset to searchable text representation.

        Args:
            asset: Asset dictionary

        Returns:
            Text representation
        """
        # Focus on most important fields for search
        important_fields = [
            'Asset ID', 'Description', 'Category', 'Type',
            'Location', 'Condition', 'Status', 'Manufacturer',
            'Model', 'Function', 'Criticality'
        ]

        text_parts = []
        for field in important_fields:
            value = asset.get(field)
            if value and str(value).strip():
                text_parts.append(f"{field}: {value}")

        # Add any other non-empty fields
        for key, value in asset.items():
            if key not in important_fields and not key.startswith('_'):
                if value and str(value).strip():
                    text_parts.append(f"{key}: {value}")

        return " | ".join(text_parts)

    def compute_similarity(self, query_embedding: List[float],
                          doc_embeddings: np.ndarray) -> np.ndarray:
        """
        Compute cosine similarity between query and document embeddings.

        Args:
            query_embedding: Query embedding vector
            doc_embeddings: Document embedding matrix (n_docs x embedding_dim)

        Returns:
            Similarity scores (n_docs,)
        """
        query_emb = np.array(query_embedding).reshape(1, -1)
        similarities = cosine_similarity(query_emb, doc_embeddings)[0]
        return similarities

    def search_by_embedding(self, query: str, asset_embeddings: np.ndarray,
                           assets: List[Dict[str, Any]], top_k: int = 50) -> List[Dict[str, Any]]:
        """
        Semantic search using embeddings.

        Args:
            query: Search query
            asset_embeddings: Precomputed asset embeddings (n_assets x embedding_dim)
            assets: List of asset dictionaries
            top_k: Number of top results to return

        Returns:
            Top-k most similar assets
        """
        # Generate query embedding
        query_embedding = self.generate_query_embedding(query)
        if not query_embedding:
            return []

        # Compute similarities
        similarities = self.compute_similarity(query_embedding, asset_embeddings)

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        # Return assets with scores
        results = []
        for idx in top_indices:
            asset = assets[int(idx)].copy()
            asset['_similarity_score'] = float(similarities[int(idx)])
            results.append(asset)

        return results

    def save_embeddings(self, embeddings: np.ndarray, output_file: str):
        """
        Save embeddings to file.

        Args:
            embeddings: Embedding matrix
            output_file: Output file path
        """
        np.save(output_file, embeddings)
        print(f"[OK] Saved embeddings to {output_file}")

    def load_embeddings(self, input_file: str) -> Optional[np.ndarray]:
        """
        Load embeddings from file.

        Args:
            input_file: Input file path

        Returns:
            Embedding matrix or None if file doesn't exist
        """
        if not os.path.exists(input_file):
            return None

        embeddings = np.load(input_file)
        print(f"[OK] Loaded embeddings from {input_file}: shape {embeddings.shape}")
        return embeddings
