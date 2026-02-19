import sqlite3
import pandas as pd

conn = sqlite3.connect('data/assets.db')
query = """
SELECT criticality, COUNT(*) as count 
FROM assets 
WHERE (category LIKE '%HVAC%' OR category LIKE '%hvac%' OR category LIKE '%Mechanical%')
  AND (condition = 'Poor' OR condition = 'poor')
GROUP BY criticality
"""
try:
    df = pd.read_sql(query, conn)
    print("--- Distribution of POOR HVAC Assets by Criticality ---")
    print(df.to_string(index=False))
except Exception as e:
    print(e)
conn.close()
