import json
import sqlite3
import pandas as pd

def debug_schema():
    with open('data/.tmp/asset_index.json', 'r', encoding='utf-8') as f:
        asset_index = json.load(f)
    
    assets = asset_index.get('assets', [])
    if not assets:
        print("No assets found")
        return

    df = pd.DataFrame(assets)
    original_cols = list(df.columns)
    
    # Simulate cleaning logic form GeminiQueryEngine
    df.columns = [c.replace(' ', '_').replace('-', '_').replace('.', '_') for c in df.columns]
    
    empty_cols = [c for c in df.columns if not c or c.strip() == '']
    internal_cols = [c for c in df.columns if c.startswith('_')]
    cols_to_drop = list(set(empty_cols + internal_cols))
    
    print("\n--- Columns BEFORE Drop ---")
    print(original_cols)
    
    print("\n--- Columns Dropped ---")
    print(cols_to_drop)
    
    if 'data_source' in cols_to_drop:
        print("\n[CRITICAL] 'data_source' is being DROPPED!")
    
    df = df.drop(columns=cols_to_drop, errors='ignore')
    
    print("\n--- Final Columns in SQLite ---")
    print(list(df.columns))
    
    if 'data_source' in df.columns:
        print("\n[OK] 'data_source' exists in final schema")
    else:
        print("\n[ERROR] 'data_source' MISSING from final schema")

if __name__ == "__main__":
    debug_schema()
