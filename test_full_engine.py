#!/usr/bin/env python3
"""Test the full GeminiQueryEngine with intent-based pipeline."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from dotenv import load_dotenv
load_dotenv()

print("="*70)
print("FULL QUERY ENGINE TEST WITH INTENT-BASED PIPELINE")
print("="*70)

from gemini_query_engine import GeminiQueryEngine

engine = GeminiQueryEngine()

print(f"\nIntent Pipeline Available: {engine.intent_pipeline is not None}")

# Test queries
test_queries = [
    "How many total assets are in the register?",
    "How many assets do we have?",
    "Count poor condition assets",
]

for q in test_queries:
    print(f"\n{'-'*70}")
    print(f"Q: {q}")
    
    result = engine.query(
        question=q,
        asset_index_file='data/.tmp/asset_index.json',
        iso_kb_file='data/.tmp/iso_knowledge_base.json'
    )
    
    print(f"Model: {result.get('model')}")
    print(f"Status: {result.get('status')}")
    print(f"Answer: {result.get('answer')}")
    if result.get('sql_query'):
        print(f"SQL: {result.get('sql_query')}")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
