#!/usr/bin/env python3
"""Debug SQL query generation."""
import os
import sys
import sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from dotenv import load_dotenv
load_dotenv()

print("="*60)
print("SQL QUERY DEBUG")
print("="*60)

# 1. Direct DB count
print("\n1. Direct SQLite count:")
try:
    conn = sqlite3.connect('data/assets.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM assets')
    count = cursor.fetchone()[0]
    print(f"   SELECT COUNT(*) FROM assets = {count}")
    
    # Show table schema
    cursor.execute("PRAGMA table_info(assets)")
    columns = cursor.fetchall()
    print(f"\n   Columns in assets table:")
    for col in columns[:10]:
        print(f"      {col[1]} ({col[2]})")
    if len(columns) > 10:
        print(f"      ... and {len(columns)-10} more columns")
    
    conn.close()
except Exception as e:
    print(f"   ERROR: {e}")

# 2. Check what the engine uses for SQL
print("\n2. Check GeminiQueryEngine SQL setup:")
try:
    from gemini_query_engine import GeminiQueryEngine
    import json
    
    engine = GeminiQueryEngine()
    
    # Load asset index and init SQLite
    with open('data/.tmp/asset_index.json', 'r', encoding='utf-8') as f:
        asset_index = json.load(f)
    
    print(f"   Asset index has {len(asset_index.get('assets', []))} assets")
    
    # Check if engine has _init_sqlite_db method
    if hasattr(engine, '_init_sqlite_db'):
        print("   Engine has _init_sqlite_db method")
        
        # Try to init the DB
        conn = engine._init_sqlite_db(asset_index)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM assets')
        engine_count = cursor.fetchone()[0]
        print(f"   Engine's in-memory DB count: {engine_count}")
        conn.close()
    else:
        print("   Engine does NOT have _init_sqlite_db method")
        
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback
    traceback.print_exc()

# 3. Test structured query detector directly
print("\n3. Structured Query Detector SQL generation:")
try:
    from structured_query_detector import StructuredQueryDetector
    detector = StructuredQueryDetector()
    
    test_queries = [
        "How many total assets are in the register?",
        "Count all assets",
        "What is the total number of assets?",
    ]
    
    # Get schema from asset index
    with open('data/.tmp/asset_index.json', 'r', encoding='utf-8') as f:
        asset_index = json.load(f)
    
    schema = asset_index.get('schema', {})
    print(f"   Schema fields: {list(schema.keys())[:10]}...")
    
    for q in test_queries:
        is_structured, sql = detector.detect_and_generate(q, schema)
        print(f"\n   Query: '{q}'")
        print(f"   Is Structured: {is_structured}")
        print(f"   SQL: {sql}")
        
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
