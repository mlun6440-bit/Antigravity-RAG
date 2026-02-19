from tools.structured_query_detector import StructuredQueryDetector
import re

detector = StructuredQueryDetector()

print("Schema Columns:", detector.schema['columns'])

excluded_cols = ['id', 'Asset ID', 'created_at', 'updated_at', 'geometry', 'notes', 'comments', 'description', 'image_url']
target_columns = [col for col in detector.schema['columns'] if col.lower() not in excluded_cols]
print("Target Columns:", target_columns)

vals = detector.get_distinct_values('Category')
print(f"Distinct Categories (first 5): {vals[:5]}")

cat = "Electrical Systems,Distribution Board"
if cat in vals:
    print(f"'{cat}' IS in distinct values.")
else:
    print(f"'{cat}' is NOT in distinct values.")

normalized_cat = re.sub(r'[,\-]', ' ', cat).lower()
print(f"Normalized: '{normalized_cat}'")

query = "How many Electrical Systems,Distribution Board"
cleaned = query.lower().replace('how many', '').strip()
cleaned_norm = re.sub(r'[,\-]', ' ', cleaned)
print(f"Cleaned Query Norm: '{cleaned_norm}'")

if normalized_cat in cleaned_norm:
    print("Match should be found!")
else:
    print("Match NOT found in query string.")
