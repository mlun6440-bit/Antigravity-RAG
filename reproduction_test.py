from tools.structured_query_detector import StructuredQueryDetector

detector = StructuredQueryDetector()

query = "How many Electrical Systems,Distribution Board"
print(f"Testing Query: '{query}'")

filters = detector.detect_multiple_filters(query)
print(f"Filters: {filters}")

sql = detector.build_sql_query(query)
if sql:
    print(f"SQL: {sql['sql']}")
    print(f"Params: {sql['params']}")
else:
    print("Failed to build SQL")
