#!/usr/bin/env python3
"""Analyze database schema for Query Contract design."""
import sqlite3
import json

db_path = "data/assets.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*70)
print("DATABASE SCHEMA ANALYSIS FOR QUERY CONTRACT")
print("="*70)

# Get all columns
cursor.execute("PRAGMA table_info(assets)")
columns = cursor.fetchall()

print("\n## ALL COLUMNS:")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

# Key columns we care about for filtering
key_columns = ['condition', 'criticality', 'data_source', 'category', 
               'asset_type', 'location', 'building', 'site', 'region',
               'system', 'status']

print("\n## DISTINCT VALUES FOR KEY FILTER COLUMNS:")
print("-"*70)

for col_name in key_columns:
    # Check if column exists
    col_exists = any(c[1].lower() == col_name.lower() for c in columns)
    if not col_exists:
        # Try partial match
        matches = [c[1] for c in columns if col_name.lower() in c[1].lower()]
        if matches:
            col_name = matches[0]
        else:
            continue
    
    try:
        cursor.execute(f"SELECT DISTINCT [{col_name}], COUNT(*) FROM assets GROUP BY [{col_name}] ORDER BY COUNT(*) DESC LIMIT 15")
        values = cursor.fetchall()
        
        print(f"\n### {col_name.upper()} ({len(values)}+ distinct values)")
        for val, count in values[:10]:
            if val:
                print(f"    '{val}' ({count:,} assets)")
        if len(values) > 10:
            print(f"    ... and {len(values)-10} more")
    except Exception as e:
        print(f"  Error reading {col_name}: {e}")

# Total count
cursor.execute("SELECT COUNT(*) FROM assets")
total = cursor.fetchone()[0]
print(f"\n## TOTAL ASSETS: {total:,}")

conn.close()

print("\n" + "="*70)
print("Use this information to build the Query Contract mapping table")
print("="*70)
