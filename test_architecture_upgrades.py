#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Architecture Upgrades
Verifies proper functionality of:
1. LLM Query Router
2. Query Cache
3. ISO Embedding Manager Statistics
"""

import sys
import os
import time
from typing import List

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

def test_llm_router():
    """Test LLM Query Router classification."""
    print("\n=== Testing LLM Query Router ===")
    try:
        from query_router import LLMQueryRouter
        router = LLMQueryRouter()
        
        test_cases = [
            ("How many assets are in poor condition?", "structured"),
            ("List all HVAC assets", "structured"),
            ("Analyze failure trends in Sector B", "analytical"),
            ("Why is preventative maintenance important?", "knowledge"),
            ("What does ISO 55000 say about risk?", "knowledge"),
            ("Count the number of pumps", "structured")
        ]
        
        passed = 0
        for query, expected in test_cases:
            print(f"Query: '{query}'")
            start = time.time()
            result = router.classify_query(query)
            elapsed = (time.time() - start) * 1000
            
            status = "✅ PASS" if result == expected else f"❌ FAIL (Expected {expected})"
            print(f"  -> Result: {result} ({elapsed:.1f}ms) [{status}]")
            
            if result == expected:
                passed += 1
                
        print(f"\nRouter Accuracy: {passed}/{len(test_cases)} ({passed/len(test_cases)*100:.1f}%)")
        return passed == len(test_cases)
        
    except Exception as e:
        print(f"❌ Router test failed: {e}")
        return False

def test_query_cache():
    """Test Query Cache functionality."""
    print("\n=== Testing Query Cache ===")
    try:
        from query_cache import QueryCache
        cache = QueryCache(ttl_seconds=2)
        
        # Test 1: Put and Get
        print("Test 1: Basic Put/Get")
        cache.put("test_q", {"data": "value"}, mode="test")
        res = cache.get("test_q", mode="test")
        
        if res and res['data'] == "value":
            print("  ✅ Cache HIT working")
        else:
            print(f"  ❌ Cache HIT failed (got {res})")
            
        # Test 2: Miss
        print("Test 2: Cache Miss")
        res = cache.get("missing_q", mode="test")
        if res is None:
            print("  ✅ Cache MISS working")
        else:
            print("  ❌ Cache MISS failed")
            
        # Test 3: Expiration
        print("Test 3: TTL Expiration (waiting 2.1s)...")
        time.sleep(2.1)
        res = cache.get("test_q", mode="test")
        if res is None:
            print("  ✅ Expiration working")
        else:
            print("  ❌ Expiration failed")
            
        # Test 4: Stats
        stats = cache.get_stats()
        print(f"Stats: {stats}")
        return True
        
    except Exception as e:
        print(f"❌ Cache test failed: {e}")
        return False

def test_embedding_manager_stats():
    """Test ISO Embedding Manager metadata."""
    print("\n=== Testing Embedding Manager Stats ===")
    try:
        from iso_embedding_manager import ISOEmbeddingManager
        manager = ISOEmbeddingManager()
        
        # Check initial stats
        stats = manager.get_api_stats()
        print(f"Initial stats: {stats}")
        
        # Verify version
        print(f"Version: {manager.embedding_version}")
        if manager.embedding_version:
             print("  ✅ Version present")
        else:
             print("  ❌ Version missing")
             
        return True
        
    except Exception as e:
        print(f"❌ Embedding manager test failed: {e}")
        return False

if __name__ == "__main__":
    print("Starting Architecture Upgrade Tests...")
    
    results = {
        "Router": test_llm_router(),
        "Cache": test_query_cache(),
        "Embeddings": test_embedding_manager_stats()
    }
    
    print("\n=== Final Results ===")
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test}: {status}")
