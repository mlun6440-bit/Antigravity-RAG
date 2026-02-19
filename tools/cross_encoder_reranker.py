#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cross-Encoder Reranker
Two-stage retrieval: Fast hybrid search → Precise cross-encoder re-ranking
"""

import logging
from typing import List, Dict, Any, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CrossEncoderReranker:
    """Wrapper for cross-encoder based re-ranking."""

    def __init__(self, model_name: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'):
        """
        Initialize cross-encoder reranker.
        
        Args:
            model_name: HuggingFace model name (default: ms-marco-MiniLM-L-6-v2)
        """
        self.model = None
        self.is_available = False
        self.model_name = model_name
        
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(model_name)
            self.is_available = True
            logger.info(f"Cross-Encoder initialized: {model_name}")
        except ImportError:
            logger.warning("sentence-transformers not installed. Run 'pip install sentence-transformers' for re-ranking.")
            self.is_available = False
        except Exception as e:
            logger.error(f"Failed to initialize cross-encoder: {e}")
            self.is_available = False

    def rerank(self, query: str, chunks: List[Dict[str, Any]], 
               top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        """
        Re-rank chunks using cross-encoder.
        
        Args:
            query: Search query
            chunks: List of candidate chunks (with scores from first-stage retrieval)
            top_k: Number of top results to return after re-ranking
            
        Returns:
            List of (chunk, reranking_score) tuples, sorted by relevance
        """
        if not self.is_available or not self.model or not chunks:
            # Fallback: return as-is
            return [(c, 0.0) for c in chunks[:top_k]]
        
        try:
            # Prepare query-document pairs for cross-encoder
            pairs = []
            for chunk in chunks:
                # Combine title and text for full context
                text = chunk.get('text', '') or chunk.get('content', '')
                title = chunk.get('title', '') or chunk.get('section_title', '')
                
                # Limit text length to avoid memory issues (cross-encoders are slower)
                full_text = f"{title} {text}"[:800]  # Truncate to 800 chars for better context
                pairs.append([query, full_text])
            
            # Get cross-encoder scores (this is slow but accurate)
            scores = self.model.predict(pairs)
            
            # Combine chunks with their new scores
            reranked = list(zip(chunks, scores))
            
            # Sort by cross-encoder score (descending)
            reranked.sort(key=lambda x: x[1], reverse=True)
            
            logger.info(f"Re-ranked {len(chunks)} chunks → Top {top_k}")
            return reranked[:top_k]
            
        except Exception as e:
            logger.error(f"Re-ranking failed: {e}")
            # Fallback: return original order
            return [(c, 0.0) for c in chunks[:top_k]]

if __name__ == "__main__":
    # Test stub
    reranker = CrossEncoderReranker()
    if reranker.is_available:
        chunks = [
            {'text': 'The quick brown fox jumps over the lazy dog', 'title': 'Animals'},
            {'text': 'Asset management requires ISO 55000 compliance', 'title': 'Standards'},
            {'text': 'Risk assessment uses a 5x5 matrix', 'title': 'Risk'}
        ]
        
        q = "ISO 55000 standards"
        results = reranker.rerank(q, chunks, top_k=2)
        
        print(f"Query: '{q}'")
        for chunk, score in results:
            print(f"  [{score:.3f}] {chunk['title']}: {chunk['text'][:50]}")
    else:
        print("Cross-Encoder not available for testing")
