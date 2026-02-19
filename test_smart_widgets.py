
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tools.pandas_analyzer import PandasAnalyzer

def test_smart_widgets():
    analyzer = PandasAnalyzer()
    
    # TestCase 1: Should NOT have a chart (Simple lookup)
    q1 = "What is the condition of asset 123?"
    a1 = "The condition of asset 123 is Poor."
    print(f"\n--- Test 1: Simple Lookup ---")
    print(f"Q: {q1}")
    widgets1 = analyzer._generate_widgets(q1, a1, result=None)
    print(f"Widgets: {widgets1}")
    
    # TestCase 2: SHOULD have a chart (Aggregation)
    q2 = "Breakdown of assets by condition"
    a2 = """
    | Condition | Count |
    |---|---|
    | Poor | 10 |
    | Good | 20 |
    """
    print(f"\n--- Test 2: Aggregation ---")
    print(f"Q: {q2}")
    widgets2 = analyzer._generate_widgets(q2, a2, result=None)
    print(f"Widgets: {widgets2}")

if __name__ == "__main__":
    test_smart_widgets()
