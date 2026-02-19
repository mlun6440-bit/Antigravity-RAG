import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from structured_query_detector import StructuredQueryDetector

detector = StructuredQueryDetector()

question = "how many Precise Air assets"

print(f"Question: {question}")
print(f"Is structured? {detector.is_structured_query(question)}")

if detector.is_structured_query(question):
    sql_query = detector.build_sql_query(question)
    if sql_query:
        print(f"\nSQL: {sql_query['sql']}")
        print(f"Params: {sql_query['params']}")
        print(f"Description: {sql_query['description']}")
        
        result = detector.execute_sql_query(sql_query)
        print(f"\nResult: {result}")
