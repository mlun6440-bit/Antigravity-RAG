
import sqlite3
import os

db_path = 'data/memory.db'

if not os.path.exists(db_path):
    print(f"Error: {db_path} does not exist.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    print("--- Table: exchanges ---")
    cursor.execute("PRAGMA table_info(exchanges)")
    exchanges_cols = [row[1] for row in cursor.fetchall()]
    print(f"Columns: {exchanges_cols}")
    
    print("\n--- Table: memory_insights ---")
    cursor.execute("PRAGMA table_info(memory_insights)")
    insights_cols = [row[1] for row in cursor.fetchall()]
    print(f"Columns: {insights_cols}")
    
    # Check for expected columns
    expected_exchanges = ['route', 'intent']
    missing_exchanges = [c for c in expected_exchanges if c not in exchanges_cols]
    
    if missing_exchanges:
        print(f"\n[ERROR] Missing columns in 'exchanges': {missing_exchanges}")
    else:
        print("\n[OK] 'exchanges' table looks correct.")

except Exception as e:
    print(f"Error inspecting DB: {e}")
finally:
    conn.close()
