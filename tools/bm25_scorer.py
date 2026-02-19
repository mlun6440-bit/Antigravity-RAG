#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BM25 Scorer
Implements BM25 keyword scoring for hybrid search integration.
"""

import re
import logging
from typing import List, Dict, Any
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BM25Scorer:
    """Wrapper for BM25 keyword scoring."""

    def __init__(self):
        """Initialize BM25 Scorer."""
        self.bm25 = None
        self.is_available = False
        self.corpus = []
        
        try:
            from rank_bm25 import BM25Okapi
            self.BM25Okapi = BM25Okapi
            self.is_available = True
            logger.info("BM25 Scorer initialized")
        except ImportError:
            logger.warning("rank_bm25 not installed. Run 'pip install rank-bm25' for improved keyword search.")
            self.is_available = False

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Tokenize text with punctuation splitting for technical terms.

        'ISO-55000:2014' → ['iso', '55000', '2014']
        'R1 Poor condition' → ['r1', 'poor', 'condition']
        """
        return re.findall(r'\b\w+\b', text.lower())

    def index_corpus(self, corpus_texts: List[str]) -> bool:
        """
        Index a corpus of texts for BM25.

        Args:
            corpus_texts: List of document strings
        """
        if not self.is_available or not corpus_texts:
            return False

        try:
            tokenized_corpus = [self._tokenize(doc) for doc in corpus_texts]
            self.bm25 = self.BM25Okapi(tokenized_corpus)
            self.corpus = corpus_texts
            logger.info(f"Indexed {len(corpus_texts)} documents for BM25")
            return True
        except Exception as e:
            logger.error(f"Failed to index corpus for BM25: {e}")
            return False

    def get_scores(self, query: str) -> List[float]:
        """
        Get BM25 scores for a query against the indexed corpus.
        
        Args:
            query: Search query string
            
        Returns:
            List of float scores corresponding to corpus documents
        """
        if not self.is_available or not self.bm25:
            return []
            
        try:
            tokenized_query = self._tokenize(query)
            scores = self.bm25.get_scores(tokenized_query)
            return scores.tolist()
        except Exception as e:
            logger.error(f"BM25 scoring failed: {e}")
            return []

    def get_top_n(self, query: str, n: int = 5) -> List[str]:
        """Get top N documents for a query."""
        if not self.is_available or not self.bm25:
            return []
            
        try:
            tokenized_query = self._tokenize(query)
            return self.bm25.get_top_n(tokenized_query, self.corpus, n=n)
        except Exception as e:
            logger.error(f"BM25 top_n failed: {e}")
            return []

if __name__ == "__main__":
    # Test stub
    scorer = BM25Scorer()
    if scorer.is_available:
        docs = [
            "The quick brown fox jumps over the lazy dog",
            "Never jump over the lazy dog quickly",
            "A quick brown dog outpaces a lazy fox"
        ]
        scorer.index_corpus(docs)
        q = "quick lazy dog"
        scores = scorer.get_scores(q)
        print(f"Query: '{q}'")
        print(f"Scores: {scores}")
        print(f"Top 1: {scorer.get_top_n(q, n=1)}")
    else:
        print("BM25 not available for testing")
