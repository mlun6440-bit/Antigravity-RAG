#!/usr/bin/env python3
"""Test the total assets query after fix."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from dotenv import load_dotenv
load_dotenv()

print("Testing query engine after fix...")

from gemini_query_engine import GeminiQueryEngine

engine = GeminiQueryEngine()

# Test the query that was failing
result = engine.query(
    question="How many total assets are in the register?",
    asset_index_file='data/.tmp/asset_index.json',
    iso_kb_file='data/.tmp/iso_knowledge_base.json'
)

print("\n" + "="*60)
print("RESULT:")
print("="*60)
print(f"Status: {result.get('status')}")
print(f"Method: {result.get('method', 'Unknown')}")
print(f"SQL Query: {result.get('sql_query', 'N/A')}")
print(f"Answer: {result.get('answer', 'N/A')}")
print("="*60)

# Check if answer contains the expected count
answer = result.get('answer', '')
if '141887' in answer or '141,887' in answer:
    print("\n[OK] FIX VERIFIED - Answer contains correct asset count!")
elif '0' in answer and 'total' in answer.lower():
    print("\n[FAIL] Still returning 0 - fix not working")
else:
    print(f"\n[CHECK] Answer doesn't match expected pattern - manual review needed")
