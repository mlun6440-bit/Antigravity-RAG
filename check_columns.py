import sqlite3
import pandas as pd

try:
    conn = sqlite3.connect("data/assets.db")
    df = pd.read_sql_query("SELECT * FROM assets LIMIT 1", conn)
    conn.close()
    print("Database Columns:")
    for col in df.columns:
        print(col)
except Exception as e:
    print(f"Error: {e}")
