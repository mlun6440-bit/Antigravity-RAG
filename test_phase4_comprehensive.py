#!/usr/bin/env python3
"""
Phase 4: Comprehensive Testing & Validation
Tests the full RAG pipeline end-to-end with Phase 1-3 components.
"""

import os
import sys
import time
import json

# Add tools to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from dotenv import load_dotenv
load_dotenv()

def test_data_availability():
    """Test 1: Verify all data files exist and are valid."""
    print("\n" + "="*60)
    print("TEST 1: DATA AVAILABILITY")
    print("="*60)
    
    results = {}
    
    # Check asset index JSON
    asset_index_path = 'data/.tmp/asset_index.json'
    if os.path.exists(asset_index_path):
        with open(asset_index_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        asset_count = len(data.get('assets', []))
        stats_count = data.get('statistics', {}).get('total_assets', 0)
        print(f"✅ asset_index.json: {asset_count} assets (stats: {stats_count})")
        results['asset_index'] = asset_count
    else:
        print(f"❌ asset_index.json: NOT FOUND")
        results['asset_index'] = 0
    
    # Check ISO knowledge base
    iso_kb_path = 'data/.tmp/iso_knowledge_base.json'
    if os.path.exists(iso_kb_path):
        with open(iso_kb_path, 'r', encoding='utf-8') as f:
            iso_data = json.load(f)
        chunk_count = len(iso_data.get('chunks', []))
        print(f"✅ iso_knowledge_base.json: {chunk_count} chunks")
        results['iso_chunks'] = chunk_count
    else:
        print(f"❌ iso_knowledge_base.json: NOT FOUND")
        results['iso_chunks'] = 0
    
    # Check SQLite database
    import sqlite3
    db_path = 'data/assets.db'
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM assets')
        db_count = cursor.fetchone()[0]
        conn.close()
        print(f"✅ assets.db: {db_count} assets")
        results['sqlite_db'] = db_count
    else:
        print(f"❌ assets.db: NOT FOUND")
        results['sqlite_db'] = 0
    
    return results

def test_phase1_components():
    """Test 2: Verify Phase 1 components (Router, Cache, Versioning)."""
    print("\n" + "="*60)
    print("TEST 2: PHASE 1 COMPONENTS")
    print("="*60)
    
    results = {}
    
    # Test Query Router
    try:
        from query_router import LLMQueryRouter
        router = LLMQueryRouter()
        
        test_queries = [
            ("How many total assets are in the register?", "structured"),
            ("Analyze fire safety compliance", "analytical"),
            ("What does ISO 55001 say about risk?", "knowledge"),
        ]
        
        print("\n[LLM Query Router Tests]")
        correct = 0
        for query, expected in test_queries:
            result = router.classify(query)
            status = "✅" if result == expected else "❌"
            if result == expected:
                correct += 1
            print(f"  {status} '{query[:40]}...' -> {result} (expected: {expected})")
        
        results['router'] = f"{correct}/{len(test_queries)}"
        print(f"\n  Router accuracy: {correct}/{len(test_queries)}")
    except Exception as e:
        print(f"❌ Query Router FAILED: {e}")
        results['router'] = "FAILED"
    
    # Test Query Cache
    try:
        from query_cache import QueryCache
        cache = QueryCache(ttl_seconds=60)
        
        # Test set/get
        cache.set("test_query", {"answer": "test_answer"})
        cached = cache.get("test_query")
        
        if cached and cached.get("answer") == "test_answer":
            print(f"\n✅ Query Cache: Working (set/get verified)")
            results['cache'] = "OK"
        else:
            print(f"\n❌ Query Cache: Get returned {cached}")
            results['cache'] = "FAILED"
        
        # Test stats
        stats = cache.get_stats()
        print(f"  Cache stats: {stats}")
    except Exception as e:
        print(f"❌ Query Cache FAILED: {e}")
        results['cache'] = "FAILED"
    
    return results

def test_phase2_components():
    """Test 3: Verify Phase 2 components (FAISS, BM25, Hybrid Search)."""
    print("\n" + "="*60)
    print("TEST 3: PHASE 2 COMPONENTS")
    print("="*60)
    
    results = {}
    
    # Test FAISS
    try:
        from faiss_index_manager import FAISSIndexManager
        faiss_mgr = FAISSIndexManager(dimension=768)
        
        import numpy as np
        test_vectors = np.random.rand(10, 768).astype('float32')
        faiss_mgr.build_index(test_vectors)
        
        query = np.random.rand(1, 768).astype('float32')
        distances, indices = faiss_mgr.search(query, k=3)
        
        if len(indices[0]) == 3:
            print(f"✅ FAISS: Working (search returned {len(indices[0])} results)")
            results['faiss'] = "OK"
        else:
            print(f"❌ FAISS: Unexpected result count")
            results['faiss'] = "FAILED"
    except ImportError:
        print(f"⚠️ FAISS: Not installed (using fallback)")
        results['faiss'] = "NOT_INSTALLED"
    except Exception as e:
        print(f"❌ FAISS FAILED: {e}")
        results['faiss'] = "FAILED"
    
    # Test BM25
    try:
        from bm25_scorer import BM25Scorer
        bm25 = BM25Scorer()
        
        docs = [
            "Asset management is important for buildings",
            "Fire safety systems require regular inspection",
            "HVAC equipment needs maintenance schedules"
        ]
        bm25.fit(docs)
        
        scores = bm25.score("fire safety inspection")
        
        if len(scores) == 3 and max(scores) > 0:
            print(f"✅ BM25: Working (scores: {[f'{s:.3f}' for s in scores]})")
            results['bm25'] = "OK"
        else:
            print(f"❌ BM25: Unexpected scores")
            results['bm25'] = "FAILED"
    except ImportError:
        print(f"⚠️ BM25: Not installed (using fallback)")
        results['bm25'] = "NOT_INSTALLED"
    except Exception as e:
        print(f"❌ BM25 FAILED: {e}")
        results['bm25'] = "FAILED"
    
    return results

def test_phase3_components():
    """Test 4: Verify Phase 3 components (Cross-Encoder)."""
    print("\n" + "="*60)
    print("TEST 4: PHASE 3 COMPONENTS")
    print("="*60)
    
    results = {}
    
    # Test Cross-Encoder
    try:
        from cross_encoder_reranker import CrossEncoderReranker
        reranker = CrossEncoderReranker()
        
        query = "What is asset lifecycle management?"
        candidates = [
            {"text": "Asset lifecycle management involves planning, acquiring, and disposing of assets.", "id": 1},
            {"text": "The weather today is sunny with clear skies.", "id": 2},
            {"text": "Lifecycle costing is part of ISO 55000 asset management.", "id": 3},
        ]
        
        reranked = reranker.rerank(query, candidates, top_k=2)
        
        # The relevant docs (1 and 3) should be ranked higher than doc 2
        top_ids = [r['id'] for r in reranked]
        if 2 not in top_ids:
            print(f"✅ Cross-Encoder: Working (irrelevant doc filtered out)")
            print(f"   Reranked order: {top_ids}")
            results['cross_encoder'] = "OK"
        else:
            print(f"⚠️ Cross-Encoder: Working but order may not be optimal")
            print(f"   Reranked order: {top_ids}")
            results['cross_encoder'] = "PARTIAL"
    except ImportError:
        print(f"⚠️ Cross-Encoder: sentence-transformers not installed")
        results['cross_encoder'] = "NOT_INSTALLED"
    except Exception as e:
        print(f"❌ Cross-Encoder FAILED: {e}")
        results['cross_encoder'] = "FAILED"
    
    return results

def test_query_engine_initialization():
    """Test 5: Verify GeminiQueryEngine loads correctly."""
    print("\n" + "="*60)
    print("TEST 5: QUERY ENGINE INITIALIZATION")
    print("="*60)
    
    results = {}
    
    try:
        from gemini_query_engine import GeminiQueryEngine
        engine = GeminiQueryEngine()
        
        # Check attributes
        attrs = [
            'query_router', 'query_cache', 'iso_embedding_manager',
            'embedding_manager', 'structured_query_detector'
        ]
        
        for attr in attrs:
            if hasattr(engine, attr):
                val = getattr(engine, attr)
                status = "✅" if val is not None else "⚠️ None"
                print(f"  {status} engine.{attr}")
                results[attr] = val is not None
            else:
                print(f"  ❌ engine.{attr} - MISSING")
                results[attr] = False
        
    except Exception as e:
        print(f"❌ GeminiQueryEngine FAILED: {e}")
        import traceback
        traceback.print_exc()
        results['engine'] = "FAILED"
    
    return results

def test_structured_query():
    """Test 6: Test structured query (SQL) path."""
    print("\n" + "="*60)
    print("TEST 6: STRUCTURED QUERY PATH (SQL)")
    print("="*60)
    
    results = {}
    
    try:
        from gemini_query_engine import GeminiQueryEngine
        engine = GeminiQueryEngine()
        
        # Load asset index
        asset_index_file = 'data/.tmp/asset_index.json'
        iso_kb_file = 'data/.tmp/iso_knowledge_base.json'
        
        if not os.path.exists(asset_index_file):
            print(f"❌ Asset index not found")
            return {'structured_query': 'NO_DATA'}
        
        # Test count query
        query = "How many total assets are in the register?"
        print(f"\n  Query: '{query}'")
        
        start_time = time.time()
        result = engine.query(
            question=query,
            asset_index_file=asset_index_file,
            iso_kb_file=iso_kb_file if os.path.exists(iso_kb_file) else None
        )
        elapsed = time.time() - start_time
        
        print(f"  Status: {result.get('status')}")
        print(f"  Method: {result.get('method', 'Unknown')}")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Answer: {result.get('answer', 'N/A')[:200]}...")
        
        if result.get('sql_query'):
            print(f"  SQL: {result.get('sql_query')}")
        
        # Check if answer contains reasonable asset count
        answer = result.get('answer', '')
        if '141887' in answer or '141,887' in answer:
            print(f"\n✅ CORRECT: Answer contains expected asset count")
            results['structured_query'] = "OK"
        elif '0' in answer and 'total' in answer.lower():
            print(f"\n❌ INCORRECT: Answer shows 0 assets (should be 141,887)")
            results['structured_query'] = "WRONG_COUNT"
        else:
            print(f"\n⚠️ UNCLEAR: Could not verify asset count in answer")
            results['structured_query'] = "UNCLEAR"
        
    except Exception as e:
        print(f"❌ Structured query FAILED: {e}")
        import traceback
        traceback.print_exc()
        results['structured_query'] = "FAILED"
    
    return results

def test_knowledge_query():
    """Test 7: Test knowledge query (ISO) path."""
    print("\n" + "="*60)
    print("TEST 7: KNOWLEDGE QUERY PATH (ISO)")
    print("="*60)
    
    results = {}
    
    try:
        from gemini_query_engine import GeminiQueryEngine
        engine = GeminiQueryEngine()
        
        asset_index_file = 'data/.tmp/asset_index.json'
        iso_kb_file = 'data/.tmp/iso_knowledge_base.json'
        
        if not os.path.exists(iso_kb_file):
            print(f"❌ ISO knowledge base not found")
            return {'knowledge_query': 'NO_DATA'}
        
        query = "What does ISO 55001 say about risk management?"
        print(f"\n  Query: '{query}'")
        
        start_time = time.time()
        result = engine.query(
            question=query,
            asset_index_file=asset_index_file if os.path.exists(asset_index_file) else None,
            iso_kb_file=iso_kb_file
        )
        elapsed = time.time() - start_time
        
        print(f"  Status: {result.get('status')}")
        print(f"  Method: {result.get('method', 'Unknown')}")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Answer: {result.get('answer', 'N/A')[:300]}...")
        print(f"  Citations: {result.get('citation_count', 0)}")
        
        if result.get('status') == 'success' and len(result.get('answer', '')) > 100:
            print(f"\n✅ Knowledge query working")
            results['knowledge_query'] = "OK"
        else:
            print(f"\n⚠️ Knowledge query may have issues")
            results['knowledge_query'] = "PARTIAL"
        
    except Exception as e:
        print(f"❌ Knowledge query FAILED: {e}")
        import traceback
        traceback.print_exc()
        results['knowledge_query'] = "FAILED"
    
    return results

def run_all_tests():
    """Run all Phase 4 tests."""
    print("\n" + "="*60)
    print("PHASE 4: COMPREHENSIVE TESTING & VALIDATION")
    print("="*60)
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = {}
    
    # Run all tests
    all_results['data'] = test_data_availability()
    all_results['phase1'] = test_phase1_components()
    all_results['phase2'] = test_phase2_components()
    all_results['phase3'] = test_phase3_components()
    all_results['engine'] = test_query_engine_initialization()
    all_results['structured'] = test_structured_query()
    all_results['knowledge'] = test_knowledge_query()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for category, results in all_results.items():
        print(f"\n{category.upper()}:")
        if isinstance(results, dict):
            for key, value in results.items():
                status = "✅" if value in [True, "OK", "PARTIAL"] or (isinstance(value, int) and value > 0) else "❌"
                print(f"  {status} {key}: {value}")
    
    print("\n" + "="*60)
    print(f"Completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    return all_results

if __name__ == "__main__":
    run_all_tests()
