import sqlite3
import os
import sys

db_path = os.path.join(os.getcwd(), 'data', 'memory.db')

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    sys.exit(0)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def get_count(table):
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        return cursor.fetchone()[0]
    except Exception as e:
        return f"Error: {e}"

print("=== Memory DB Status ===")
print(f"Path: {db_path}")
print(f"Sessions: {get_count('sessions')}")
print(f"Exchanges: {get_count('exchanges')}")
print(f"Insights: {get_count('memory_insights')}")

print("\n--- Recent Insights ---")
try:
    cursor.execute("SELECT insight_type, content FROM memory_insights ORDER BY created_at DESC LIMIT 5")
    rows = cursor.fetchall()
    if rows:
        for r in rows:
            print(f"[{r[0]}] {r[1]}")
    else:
        print("No insights found.")
except Exception as e:
    print(f"Error reading insights: {e}")

print("\n--- Recent Exchanges ---")
try:
    cursor.execute("SELECT question, answer, embedding IS NOT NULL FROM exchanges ORDER BY timestamp DESC LIMIT 3")
    rows = cursor.fetchall()
    if rows:
        for r in rows:
            print(f"Q: {r[0][:50]}...")
            print(f"A: {r[1][:50]}...")
            print(f"Has Embedding: {r[2]}")
            print("-")
    else:
        print("No exchanges found.")
except Exception as e:
    print(f"Error reading exchanges: {e}")

conn.close()
