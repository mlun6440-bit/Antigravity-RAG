#!/usr/bin/env python3
"""Debug: Trace the exact SQL query being generated."""
import os
import sys

# Force UTF-8 output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("TRACING SQL QUERY GENERATION")
print("=" * 60)

from structured_query_detector import StructuredQueryDetector
detector = StructuredQueryDetector()

# Check the database connection
print("")
print("1. Database path:", detector.db_path)

# Check if database has assets
import sqlite3
conn = sqlite3.connect(detector.db_path)
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM assets')
count = cursor.fetchone()[0]
print("   Direct count from DB:", count)
conn.close()

# Test the query
question = "How many total assets are in the register?"
print("")
print("2. Question:", question)

# Test detect_query_mode
mode = detector.detect_query_mode(question)
print("   Query mode:", mode)

# Test build_sql_query
sql_query = detector.build_sql_query(question)
print("")
print("3. Generated SQL query:")
if sql_query:
    print("   Type:", sql_query.get('type'))
    print("   SQL:", sql_query.get('sql'))
    print("   Params:", sql_query.get('params'))
    print("   Description:", sql_query.get('description'))
    
    # Execute it
    result = detector.execute_sql_query(sql_query)
    print("")
    print("4. Execution result:")
    print("   Success:", result.get('success'))
    print("   Count:", result.get('count'))
    print("   Results:", result.get('results'))
    print("   Error:", result.get('error', 'None'))
else:
    print("   SQL query was None - this is the problem!")
    
    # Check is_structured_query
    is_struct = detector.is_structured_query(question)
    print("")
    print("   is_structured_query:", is_struct)

print("")
print("=" * 60)

# Test with a simpler query
print("")
print("TESTING SIMPLER COUNT QUERY:")
simple_q = "Count all assets"
sql2 = detector.build_sql_query(simple_q)
if sql2:
    print("SQL:", sql2.get('sql'))
    result2 = detector.execute_sql_query(sql2)
    print("Result:", result2)
else:
    print("SQL query was None")
