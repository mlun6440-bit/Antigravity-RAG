import sys
import os
import logging

# Setup logging to see the "Zero result detected" message
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Add current dir to path
sys.path.append(os.getcwd())

from tools.pandas_analyzer import PandasAnalyzer

def run_debug():
    print("--- STARTING LIVE DEBUG ---")
    try:
        analyzer = PandasAnalyzer()
        query = "how many HVAC poor assets"
        print(f"Query: {query}")
        
        result = analyzer.analyze(query)
        
        print("\n--- FINAL RESULT (Sanitized) ---")
        # Print dictionary values safely
        for k, v in result.items():
            safe_v = str(v).encode('ascii', 'ignore').decode('ascii')
            print(f"{k}: {safe_v}")
            
        if "Analysis Insight" in result.get('answer', ''):
            print("\n[SUCCESS] SELF-CORRECTION TRIGGERED!")
        else:
            print("\n[FAIL] SELF-CORRECTION DID NOT TRIGGER")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_debug()
