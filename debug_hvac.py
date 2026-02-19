import pandas as pd
import sqlite3

try:
    c = sqlite3.connect('data/assets.db')
    df = pd.read_sql("SELECT DISTINCT category, condition FROM assets WHERE category LIKE '%Mechanical%' OR category LIKE '%Air%' OR category LIKE '%HVAC%' LIMIT 50", c)
    print(df)
    
    print("\nAlso checking 'condition' values:")
    df_cond = pd.read_sql("SELECT DISTINCT condition FROM assets", c)
    print(df_cond)
except Exception as e:
    print(e)
