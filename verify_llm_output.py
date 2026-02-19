import os
import sys
from tools.gemini_query_engine import GeminiQueryEngine
from unittest.mock import MagicMock

# Mock the search_assets to avoid needing real index files
def mock_search(*args, **kwargs):
    return [
        "Asset: P-101 (Pump) | Condition: Poor | Status: Active | Loc: Building A",
        "Asset: P-102 (Pump) | Condition: Good | Status: Active | Loc: Building A",
        "Asset: P-103 (Pump) | Condition: Poor | Status: Inactive | Loc: Building B",
        "Asset: M-001 (Motor) | Condition: Good | Status: Active | Loc: Building A",
        "Asset: M-002 (Motor) | Condition: Excellent | Status: Active | Loc: Building B",
    ]

# Initialize engine
engine = GeminiQueryEngine()
engine.search_assets = mock_search

# Mock context
context = [
    "Asset: P-101 (Pump) | Condition: Poor | Status: Active | Loc: Building A",
    "Asset: P-102 (Pump) | Condition: Good | Status: Active | Loc: Building A",
    "Asset: P-103 (Pump) | Condition: Poor | Status: Inactive | Loc: Building B",
    "Asset: M-001 (Motor) | Condition: Good | Status: Active | Loc: Building A",
    "Asset: M-002 (Motor) | Condition: Excellent | Status: Active | Loc: Building B",
]

# Query
question = "Show me a breakdown of assets by condition"
# Manually construct the prompt as per query() method
system_prompt = engine.create_system_prompt()
full_prompt = f"""{system_prompt}

=== CONTEXT ===
{context}

=== QUESTION ===
{question}

=== ANSWER ===
Please provide a comprehensive answer based on the asset data and ISO standards above.

IMPORTANT FORMATTING RULES:
1. For ANY list of assets or structured data, you MUST use a Markdown Table.
2. CONSTRAINT: Tables must have MAXIMUM 5 COLUMNS (Select the most relevant ones).
3. Start every table row on a NEW LINE."""

print("--- SENDING TO GEMINI... ---")
try:
    response = engine.model.generate_content(full_prompt)
    print("\n--- RAW RESPONSE START ---")
    print(response.text)
    print("--- RAW RESPONSE END ---\n")
    
    # Check parsing
    if "```json" in response.text:
        print("[SUCCESS] JSON block detected")
    else:
        print("[FAILURE] No JSON block detected")

except Exception as e:
    print(f"Error: {e}")
