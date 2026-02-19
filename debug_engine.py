import sys
import os
import json
import logging

# Add tools to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from gemini_query_engine import GeminiQueryEngine

def test_engine():
    print("Initializing Engine...")
    engine = GeminiQueryEngine()
    
    question = "how many precise air assets are there?"
    print(f"\nQuerying: {question}")
    
    # Enable detailed logging if possible, or just rely on print statements in the class
    result = engine.query(question, 'data/.tmp/asset_index.json', 'data/.tmp/iso_knowledge_base.json')
    
    with open('debug_engine_result.txt', 'w', encoding='utf-8') as f:
        f.write(f"Result:\n{result}\n")
    print(result)

    # Inspect schema
    print("\n--- SQLite Schema ---")
    try:
        # We need to access the connection, but query() closes it.
        # We have to instantiate and init db manually to inspect.
        with open('data/.tmp/asset_index.json', 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        # Access the private method for debugging
        conn = engine._init_sqlite_db(index)
        cursor = conn.execute("PRAGMA table_info(assets)")
        columns = [row[1] for row in cursor.fetchall()]
        print(columns)
        
        if 'data_source' in columns:
            print("\n[OK] 'data_source' is in SQLite table")
        else:
            print("\n[ERROR] 'data_source' NOT in SQLite table")
            
        with open('columns.txt', 'w', encoding='utf-8') as f:
            f.write(str(columns))
            
        conn.close()
        
    except Exception as e:
        print(f"Error inspecting schema: {e}")

if __name__ == "__main__":
    test_engine()
