#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAISS Index Manager
Manages FAISS vector indexes for efficient similarity search.
"""

import os
import numpy as np
import logging
from typing import Tuple, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FAISSIndexManager:
    """Wrapper for FAISS vector index."""

    def __init__(self, dimension: int = 768):
        """
        Initialize FAISS manager.
        
        Args:
            dimension: Vector dimension (default 768 for Gemini embeddings)
        """
        self.dimension = dimension
        self.index = None
        self.is_available = False
        
        try:
            import faiss
            self.faiss = faiss
            # Use Inner Product (IP) for cosine similarity (assuming normalized vectors)
            self.index = faiss.IndexFlatIP(dimension)
            self.is_available = True
            logger.info(f"FAISS initialized with dimension {dimension} (FlatIP)")
        except ImportError:
            logger.warning("FAISS not installed. Run 'pip install faiss-cpu' to enable fast vector search.")
            self.is_available = False

    def build_index(self, embeddings: List[np.ndarray]) -> bool:
        """
        Build a new index from a list of embeddings.
        
        Args:
            embeddings: List of numpy arrays (embeddings)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available or not embeddings:
            return False
            
        try:
            # Convert to float32 numpy array required by FAISS
            data = np.array(embeddings).astype('float32')
            
            # Normalize for cosine similarity (IndexFlatIP uses dot product)
            self.faiss.normalize_L2(data)
            
            # Reset and train
            self.index.reset()
            self.index.add(data)
            
            logger.info(f"Built FAISS index with {self.index.ntotal} vectors")
            return True
        except Exception as e:
            logger.error(f"Failed to build FAISS index: {e}")
            return False

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> Tuple[List[int], List[float]]:
        """
        Search the index for similar vectors.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            
        Returns:
            Tuple of (indices, scores)
        """
        if not self.is_available or not self.index or self.index.ntotal == 0:
            return [], []
            
        try:
            # Prepare query vector
            q_vec = np.array([query_embedding]).astype('float32')
            self.faiss.normalize_L2(q_vec)
            
            # Search
            scores, indices = self.index.search(q_vec, top_k)
            
            # Return as simple lists
            return indices[0].tolist(), scores[0].tolist()
        except Exception as e:
            logger.error(f"FAISS search failed: {e}")
            return [], []

    def save_index(self, filepath: str) -> bool:
        """Save index to disk."""
        if not self.is_available or not self.index:
            return False
        try:
            self.faiss.write_index(self.index, filepath)
            logger.info(f"Saved FAISS index to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")
            return False

    def load_index(self, filepath: str) -> bool:
        """Load index from disk."""
        if not self.is_available:
            return False
        if not os.path.exists(filepath):
            return False
            
        try:
            self.index = self.faiss.read_index(filepath)
            logger.info(f"Loaded FAISS index from {filepath} ({self.index.ntotal} vectors)")
            return True
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")
            return False

if __name__ == "__main__":
    # Test stub
    manager = FAISSIndexManager()
    if manager.is_available:
        # Create random data
        data = [np.random.rand(768) for _ in range(10)]
        manager.build_index(data)
        
        # Search
        q = np.random.rand(768)
        idxs, scores = manager.search(q, top_k=3)
        print(f"Indices: {idxs}, Scores: {scores}")
    else:
        print("FAISS not available for testing")
