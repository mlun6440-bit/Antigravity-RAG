import sqlite3
import pandas as pd

conn = sqlite3.connect('data/assets.db')
query = """
SELECT COUNT(*) as count 
FROM assets 
WHERE (category LIKE '%HVAC%' OR category LIKE '%hvac%')
  AND (condition = 'Poor' OR condition = 'poor')
"""
try:
    df = pd.read_sql(query, conn)
    print(df['count'].iloc[0])
except Exception as e:
    print(e)
conn.close()
