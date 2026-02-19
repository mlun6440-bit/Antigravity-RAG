#!/usr/bin/env python3
"""Quick diagnostic for 0 assets issue."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from dotenv import load_dotenv
load_dotenv()

print("="*60)
print("QUICK DIAGNOSTIC: Why is query returning 0 assets?")
print("="*60)

# 1. Check data
import json
asset_file = 'data/.tmp/asset_index.json'
print(f"\n1. Asset Index: {asset_file}")
if os.path.exists(asset_file):
    with open(asset_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"   Assets: {len(data.get('assets', []))}")
    print(f"   Stats: {data.get('statistics', {})}")
else:
    print("   NOT FOUND!")

# 2. Check structured query detector
print("\n2. Structured Query Detector:")
try:
    from structured_query_detector import StructuredQueryDetector
    detector = StructuredQueryDetector()
    
    test_q = "How many total assets are in the register?"
    is_structured, sql = detector.detect_and_generate(test_q, {})
    print(f"   Query: '{test_q}'")
    print(f"   Is Structured: {is_structured}")
    print(f"   Generated SQL: {sql}")
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback
    traceback.print_exc()

# 3. Test the actual query path
print("\n3. Testing GeminiQueryEngine.query():")
try:
    from gemini_query_engine import GeminiQueryEngine
    engine = GeminiQueryEngine()
    
    print(f"\n   Has structured_query_detector: {hasattr(engine, 'structured_query_detector')}")
    print(f"   structured_query_detector is None: {engine.structured_query_detector is None}")
    
    # Check if SQL database is initialized
    if hasattr(engine, '_init_sqlite_db'):
        print("   Has _init_sqlite_db method: True")
    
    # Try the query
    print("\n   Running query...")
    result = engine.query(
        question="How many total assets are in the register?",
        asset_index_file=asset_file,
        iso_kb_file='data/.tmp/iso_knowledge_base.json'
    )
    
    print(f"\n   Status: {result.get('status')}")
    print(f"   Method: {result.get('method')}")
    print(f"   SQL Query: {result.get('sql_query', 'N/A')}")
    print(f"   Answer: {result.get('answer', 'N/A')[:500]}")
    
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
