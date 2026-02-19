from tools.structured_query_detector import StructuredQueryDetector

detector = StructuredQueryDetector()

queries = [
    "How many Electrical Systems,Distribution Board",
    "How many Electrical Systems,Distribution Board assets",
    "How many Precise Fire assets"
]

print("\n" + "="*50)
for query in queries:
    print(f"Query: '{query}'")
    filters = detector.detect_multiple_filters(query)
    print(f" -> Detected Filters: {filters}")

    sql = detector.build_sql_query(query)
    if sql:
        print(f" -> SQL: {sql['sql']}")
        print(f" -> Params: {sql['params']}")
    else:
        print(" -> [NO SQL GENERATED]")
    print("-" * 50)
