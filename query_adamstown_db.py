import sqlite3
import pandas as pd

conn = sqlite3.connect('data/assets.db')
query = """
SELECT COUNT(*) as count 
FROM assets 
WHERE (category LIKE '%Distribution Board%' OR category LIKE '% DB %' OR asset_name LIKE '%Distribution Board%' OR asset_name LIKE '% DB %')
  AND (location LIKE '%Adamstown%' OR building LIKE '%Adamstown%')
"""
try:
    df = pd.read_sql(query, conn)
    print(f"Adamstown Distribution Boards: {df['count'].iloc[0]}")
except Exception as e:
    print(e)
conn.close()
