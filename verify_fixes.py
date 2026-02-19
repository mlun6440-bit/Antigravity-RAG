
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))
from gemini_query_engine import GeminiQueryEngine

engine = GeminiQueryEngine()
asset_index = 'data/.tmp/asset_index.json'
iso_kb = 'data/.tmp/iso_knowledge_base.json'

queries = [
    "How many assets are over 20 years old?",
    "List assets that are not in Critical condition",
    "Count High criticality electrical assets in Poor condition",
    "How many assets in Building A"
]

for q in queries:
    print(f"\nQUERY: {q}")
    result = engine.query(q, asset_index, iso_kb)
    print(f"ANSWER: {result.get('answer')}")
    print(f"MODEL: {result.get('model')}")
