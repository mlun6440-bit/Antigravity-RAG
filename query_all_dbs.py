import sqlite3
import pandas as pd

conn = sqlite3.connect('data/assets.db')
query = """
SELECT COUNT(*) as count 
FROM assets 
WHERE (category LIKE '%Distribution%' OR category LIKE '% DB %' OR asset_name LIKE '%Distribution%' OR asset_name LIKE '% DB %')
"""
try:
    df = pd.read_sql(query, conn)
    print(f"Total Distribution Boards: {df['count'].iloc[0]}")
except Exception as e:
    print(e)
conn.close()
