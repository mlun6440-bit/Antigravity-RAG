import sqlite3
import pandas as pd

# Connect to database
conn = sqlite3.connect('data/assets.db')

print("=== DIRECT DATABASE QUERY ===\n")

# 1. Check what columns exist
print("1. Checking available columns:")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(assets)")
columns = [row[1] for row in cursor.fetchall()]
print(f"   Columns: {', '.join(columns[:15])}...\n")

# 2. Check unique values in 'category' containing 'HVAC'
print("2. Categories containing 'HVAC':")
df = pd.read_sql("SELECT DISTINCT category FROM assets WHERE category LIKE '%HVAC%' OR category LIKE '%hvac%'", conn)
print(f"   {df['category'].tolist()}\n")

# 3. Check unique values in 'condition'
print("3. Unique condition values:")
df = pd.read_sql("SELECT DISTINCT condition FROM assets", conn)
print(f"   {df['condition'].tolist()}\n")

# 4. Query: HVAC assets with Poor condition
print("4. QUERYING: HVAC + Poor condition")
query = """
SELECT COUNT(*) as count 
FROM assets 
WHERE (category LIKE '%HVAC%' OR category LIKE '%hvac%')
  AND (condition = 'Poor' OR condition = 'poor')
"""
result = pd.read_sql(query, conn)
print(f"   Result: {result['count'].iloc[0]} poor HVAC assets\n")

# 5. Show sample of these assets
print("5. Sample of poor HVAC assets:")
query_sample = """
SELECT asset_id, asset_name, category, condition 
FROM assets 
WHERE (category LIKE '%HVAC%' OR category LIKE '%hvac%')
  AND (condition = 'Poor' OR condition = 'poor')
LIMIT 5
"""
sample = pd.read_sql(query_sample, conn)
print(sample.to_string())

conn.close()
