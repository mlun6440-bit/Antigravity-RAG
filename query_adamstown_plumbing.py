import sqlite3
import pandas as pd

conn = sqlite3.connect('data/assets.db')
query = """
SELECT COUNT(*) as count 
FROM assets 
WHERE (category LIKE '%Plumbing%' OR category LIKE '%Hydraulics%' OR category LIKE '%Hot Water%')
  AND (location LIKE '%Adamstown%' OR building LIKE '%Adamstown%')
"""
try:
    df = pd.read_sql(query, conn)
    print(f"Adamstown Plumbing Assets: {df['count'].iloc[0]}")
except Exception as e:
    print(e)
conn.close()
