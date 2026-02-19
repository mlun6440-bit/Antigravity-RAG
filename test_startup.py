import sys
print("Starting import...")
try:
    import google.generativeai as genai
    print("Import successful")
except Exception as e:
    print(f"Import failed: {e}")
print("Done")
