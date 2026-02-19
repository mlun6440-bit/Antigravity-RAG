import sys
import os
import logging

# Setup logging to see the "Proactive Discovery found" message
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Add current dir to path
sys.path.append(os.getcwd())

from tools.pandas_analyzer import PandasAnalyzer

def test_proactive():
    print("--- TESTING PROACTIVE DISCOVERY ---")
    try:
        analyzer = PandasAnalyzer()
        query = "how many poor HVAC assets"
        print(f"Query: {query}")
        
        # This will trigger pre-analysis
        result = analyzer.analyze(query)
        
        print("\n--- FINAL RESULT ---")
        print(result.get('answer'))
        
        # We can also check the generated code to see if it used the info
        print("\n--- GENERATED CODE ---")
        print(result.get('code'))
        
        if "HVAC & Refrigeration" in str(result.get('code')):
            print("\n✅ SUCCESS: Proactive Discovery informed the final code!")
        else:
            print("\n⚠️  WARNING: Could not verify if proactive discovery was used.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_proactive()
