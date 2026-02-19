#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Phase 3 Upgrades
Verifies proper functionality of Cross-Encoder Re-ranking
"""

import sys
import os
import time

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

def test_cross_encoder():
    """Test Cross-Encoder Reranker."""
    print("\n=== Testing Cross-Encoder Reranker ===")
    try:
        from cross_encoder_reranker import CrossEncoderReranker
        reranker = CrossEncoderReranker()
        
        if not reranker.is_available:
            print("❌ sentence-transformers not installed (Skipping)")
            return False
            
        # Test corpus
        chunks = [
            {'text': 'The quick brown fox jumps over the lazy dog', 'title': 'Animals'},
            {'text': 'Asset management requires ISO 55000 compliance', 'title': 'ISO Standards'},
            {'text': 'Risk assessment uses a 5x5 matrix for evaluation', 'title': 'Risk Management'},
            {'text': 'ISO 55001 specifies requirements for asset management', 'title': 'ISO 55001'},
            {'text': 'Lifecycle costing is essential for asset planning', 'title': 'Asset Planning'}
        ]
        
        # Test Query
        query = "ISO 55000 asset management standards"
        
        print(f"\nQuery: '{query}'")
        print(f"Re-ranking {len(chunks)} chunks...")
        
        start = time.time()
        results = reranker.rerank(query, chunks, top_k=3)
        elapsed = (time.time() - start) * 1000
        
        print(f"\nTop 3 results (in {elapsed:.1f}ms):")
        for i, (chunk, score) in enumerate(results, 1):
            print(f"  {i}. [{score:.3f}] {chunk['title']}: {chunk['text'][:60]}...")
            
        # Verify that ISO-related chunks are ranked higher
        top_titles = [chunk['title'] for chunk, _ in results[:2]]
        
        if 'ISO' in str(top_titles):
            print("\n✅ Re-ranking successful (ISO content prioritized)")
            return True
        else:
            print("\n❌ Re-ranking did not prioritize relevant content")
            return False
            
    except Exception as e:
        print(f"❌ Cross-Encoder test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting Phase 3 Upgrade Tests...")
    
    result = test_cross_encoder()
    
    print("\n=== Final Result ===")
    print(f"Cross-Encoder: {'✅ PASS' if result else '❌ FAIL / NOT INSTALLED'}")
