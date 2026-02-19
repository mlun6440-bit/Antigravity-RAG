#!/usr/bin/env python3
"""Test analytical query system end-to-end"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from gemini_query_engine import GeminiQueryEngine
import time

def test_all_query_modes():
    """Test all 3 query modes: structured, analytical, knowledge."""
    
    print("="*70)
    print("ANALYTICAL QUERY SYSTEM - END-TO-END TEST")
    print("="*70)
    
    # Initialize engine
    try:
        engine = GeminiQueryEngine()
        print("\n[OK] Query engine initialized\n")
    except Exception as e:
        print(f"\n[FAIL] Could not initialize engine: {e}")
        return False
    
    asset_index = 'data/.tmp/asset_index.json'
    iso_kb = 'data/.tmp/iso_kb.json'
    
    test_cases = [
        # Structured queries
        {
            'name': 'Structured: Count query',
            'query': 'How many Precise Air assets',
            'expected_mode': 'structured',
            'expected_model': 'SQL'
        },
        {
            'name': 'Structured: Breakdown query',
            'query': 'Count assets by criticality',
            'expected_mode': 'structured',
            'expected_model': 'SQL'
        },
        
        # Analytical queries
        {
            'name': 'Analytical: Condition analysis',
            'query': 'Analyze my poor condition electrical assets per ISO 55001',
            'expected_mode': 'analytical',
            'expected_model': 'Analytical'
        },
        {
            'name': 'Analytical: Risk assessment',
            'query': 'Assess critical fire systems for compliance',
            'expected_mode': 'analytical',
            'expected_model': 'Analytical'
        },
        
        # Knowledge queries
        {
            'name': 'Knowledge: ISO question',
            'query': 'What is ISO 55001',
            'expected_mode': 'knowledge',
            'expected_model': None  # RAG doesn't set specific model
        },
    ]
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}/{len(test_cases)}: {test['name']}")
        print(f"{'='*70}")
        print(f"Query: {test['query']}")
        
        # Detect mode first
        if engine.structured_query_detector:
            detected_mode = engine.structured_query_detector.detect_query_mode(test['query'])
            print(f"Detected mode: {detected_mode}")
            
            if detected_mode == test['expected_mode']:
                print(f"[PASS] Mode detection correct")
            else:
                print(f"[FAIL] Mode detection wrong (expected {test['expected_mode']})")
                failed += 1
                continue
        
        # Execute query
        try:
            start_time = time.time()
            result = engine.query(test['query'], asset_index, iso_kb)
            elapsed = time.time() - start_time
            
            print(f"\nResponse time: {elapsed:.2f}s")
            print(f"Status: {result.get('status', 'unknown')}")
            print(f"Model: {result.get('model', 'unknown')}")
            
            # Check expected model
            if test['expected_model']:
                if test['expected_model'] in result.get('model', ''):
                    print(f"[PASS] Model check correct")
                else:
                    print(f"[FAIL] Model check wrong (expected {test['expected_model']})")
                    failed += 1
                    continue
            
            # Check result structure
            if 'answer' in result:
                answer_preview = result['answer'][:200]
                print(f"\nAnswer preview: {answer_preview}...")
                print(f"Citations: {result.get('citation_count', 0)}")
                print(f"[PASS] TEST COMPLETE")
                passed += 1
            else:
                print(f"[FAIL] TEST FAILED: No answer in result")
                failed += 1
                
        except Exception as e:
            print(f"[FAIL] TEST EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*70}")
    print(f"FINAL RESULTS")
    print(f"{'='*70}")
    print(f"Passed: {passed}/{len(test_cases)}")
    print(f"Failed: {failed}/{len(test_cases)}")
    print(f"Success rate: {(passed/len(test_cases)*100):.0f}%")
    print(f"{'='*70}\n")
    
    return failed == 0

if __name__ == "__main__":
    success = test_all_query_modes()
    sys.exit(0 if success else 1)
