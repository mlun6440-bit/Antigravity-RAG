#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple test for analytical query system"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from gemini_query_engine import GeminiQueryEngine

print("Initializing engine...")
engine = GeminiQueryEngine()

# Test queries
queries = [
    ("How many Precise Air assets", "structured"),
    ("Analyze poor condition electrical assets", "analytical"),
    ("What is ISO 55001", "knowledge")
]

for query, expected in queries:
    mode = engine.structured_query_detector.detect_query_mode(query)
    result = "PASS" if mode == expected else f"FAIL (got {mode})"
    print(f"{result:10} | {query:50} | Expected: {expected}")
