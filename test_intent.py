#!/usr/bin/env python3
"""Test intent-based pipeline with multiple query variations."""
import os
import sys

# Force UTF-8 output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from dotenv import load_dotenv
load_dotenv()

from intent_query_pipeline import IntentBasedQueryPipeline

print("="*70)
print("INTENT-BASED QUERY ARCHITECTURE TEST")
print("Handles ANY phrasing - LLM extracts intent, deterministic execution")
print("="*70)

pipeline = IntentBasedQueryPipeline()

# Test different phrasings of the same query
test_queries = [
    # Total count - multiple phrasings
    "How many total assets are in the register?",
    "How many assets do we have?",
    "What's the total number of assets?",
    "Count all assets",
    
    # Filtered count
    "How many assets are in poor condition?",
    "Count critical assets",
    
    # Multi-filter
    "How many Precise Fire assets are critical?",
]

for q in test_queries:
    print(f"\n{'-'*70}")
    print(f"Q: {q}")
    
    response = pipeline.process(q)
    
    intent = response.get('intent', {})
    print(f"Intent: action={intent.get('action')}, filters={intent.get('filters')}")
    print(f"Success: {response.get('success')}")
    print(f"Answer: {response.get('answer')}")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
