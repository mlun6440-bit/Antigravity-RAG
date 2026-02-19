import sqlite3
import pandas as pd

conn = sqlite3.connect('data/assets.db')
query = """
SELECT COUNT(*) as count 
FROM assets 
WHERE location LIKE '%Adamstown%' OR building LIKE '%Adamstown%'
"""
try:
    df = pd.read_sql(query, conn)
    print(f"Adamstown Assets: {df['count'].iloc[0]}")
    
    # Also check Poor Adamstown assets
    query_poor = """
    SELECT COUNT(*) as count 
    FROM assets 
    WHERE (location LIKE '%Adamstown%' OR building LIKE '%Adamstown%')
      AND (condition = 'Poor' OR condition = 'poor')
    """
    df_poor = pd.read_sql(query_poor, conn)
    print(f"Poor Adamstown Assets: {df_poor['count'].iloc[0]}")
    
except Exception as e:
    print(e)
conn.close()
