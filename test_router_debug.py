import sys
import os
from tools.query_router import LLMQueryRouter
from dotenv import load_dotenv

load_dotenv()

def test_router():
    queries = [
        "How many Distribution Boards do I have?",
        "Count all Electrical assets",
        "What is the condition of Asset X?",
        "Tell me about ISO 55000",
        "List all Chillers"
    ]
    
    router = LLMQueryRouter()
    
    for q in queries:
        classification = router.classify_query(q)
        print(f"Query: '{q}' -> {classification}")

if __name__ == "__main__":
    test_router()
