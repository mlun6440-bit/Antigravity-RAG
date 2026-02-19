
import re

def test_regex():
    # Test cases for table parsing
    test_cases = [
        # Standard
        """
        | Condition | Count |
        |---|---|
        | Poor | 10 |
        | Good | 20 |
        """,
        # Tight content (no spaces)
        """
        |Condition|Count|
        |---|---|
        |Poor|10|
        |Good|20|
        """,
        # No outer pipes (GitHub flavored sometimes)
        """
        Condition | Count
        ---|---
        Poor | 10
        Good | 20
        """
    ]

    regex_3col = r'\|\s*[^\|]+\s*\|\s*([^\|]+)\s*\|\s*([0-9,]+)\s*\|'
    regex_2col = r'\|\s*([^\|]+)\s*\|\s*([0-9,]+)\s*\|'
    # Tight regex attempt (mocking what I might change it to)
    regex_2col_tight = r'\|\s*([^\|]+)\s*\|\s*([0-9,]+)\s*\|'

    print("--- Testing Existing Regex ---")
    for i, case in enumerate(test_cases):
        print(f"\nCase {i+1}:")
        rows = re.findall(regex_2col, case)
        print(f"Captured: {rows}")
        if not rows and i < 2: # Cases 1 and 2 should ideally match
             print("FAILED to capture rows.")
        elif rows:
             print("SUCCESS")
             
if __name__ == "__main__":
    test_regex()
