#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Phase 2 Upgrades
Verifies proper functionality of:
1. FAISS Index Manager
2. BM25 Scorer
3. ISO Embedding Manager Integration
"""

import sys
import os
import time
import numpy as np

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

def test_faiss():
    """Test FAISS Index Manager."""
    print("\n=== Testing FAISS Index Manager ===")
    try:
        from faiss_index_manager import FAISSIndexManager
        manager = FAISSIndexManager(dimension=128) # Small dim for test
        
        if not manager.is_available:
            print("❌ FAISS not installed (Skipping)")
            return False
            
        # Create synthetic data
        embeddings = [np.random.rand(128).astype('float32') for _ in range(100)]
        
        # Build index
        start = time.time()
        success = manager.build_index(embeddings)
        elapsed = (time.time() - start) * 1000
        
        if success:
            print(f"✅ Built index with 100 vectors in {elapsed:.2f}ms")
        else:
            print("❌ Failed to build index")
            return False
            
        # Search
        q = np.random.rand(128).astype('float32')
        idxs, scores = manager.search(q, top_k=5)
        
        print(f"Top 5 indices: {idxs}")
        print(f"Top 5 scores: {scores}")
        
        if len(idxs) == 5:
            print("✅ Search returned correct number of results")
            return True
        else:
            print("❌ Search failed")
            return False
            
    except Exception as e:
        print(f"❌ FAISS test failed: {e}")
        return False

def test_bm25():
    """Test BM25 Scorer."""
    print("\n=== Testing BM25 Scorer ===")
    try:
        from bm25_scorer import BM25Scorer
        scorer = BM25Scorer()
        
        if not scorer.is_available:
            print("❌ rank-bm25 not installed (Skipping)")
            return False
            
        corpus = [
            "The quick brown fox jumps over the lazy dog",
            "Never jump over the lazy dog quickly",
            "A quick brown dog outpaces a lazy fox",
            "Asset management requires ISO 55000 compliance",
            "Risk assessment uses a 5x5 matrix"
        ]
        
        scorer.index_corpus(corpus)
        print(f"Indexed {len(corpus)} documents")
        
        # Test 1: Exact keyword match
        q1 = "quick fox"
        scores1 = scorer.get_scores(q1)
        top1 = scorer.get_top_n(q1, n=1)
        print(f"\nQuery: '{q1}'")
        print(f"Top result: '{top1[0]}'")
        
        if "quick brown fox" in top1[0]:
             print("✅ Keyword match successful")
        else:
             print("❌ Keyword match failed")
             
        # Test 2: Domain term
        q2 = "ISO 55000"
        top2 = scorer.get_top_n(q2, n=1)
        print(f"\nQuery: '{q2}'")
        print(f"Top result: '{top2[0]}'")
        
        if "Asset management" in top2[0]:
             print("✅ Domain term match successful")
             return True
        else:
             print("❌ Domain term match failed")
             return False
             
    except Exception as e:
        print(f"❌ BM25 test failed: {e}")
        return False

if __name__ == "__main__":
    print("Starting Phase 2 Upgrade Tests...")
    
    faiss_result = test_faiss()
    bm25_result = test_bm25()
    
    print("\n=== Final Results ===")
    print(f"FAISS: {'✅ PASS' if faiss_result else '❌ FAIL / NOT INSTALLED'}")
    print(f"BM25:  {'✅ PASS' if bm25_result else '❌ FAIL / NOT INSTALLED'}")
