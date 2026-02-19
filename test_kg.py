import requests
import json
import sys

def test_kg():
    url = 'http://localhost:5001/api/query'
    headers = {'Content-Type': 'application/json'}
    
    # Query designed to trigger "graph" route via fast-path keywords
    payload = {
        'question': 'Identify clusters of poor assets near end-of-life'
    }
    
    print(f"Sending query: {payload['question']}")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("\nResponse Received:")
            print(f"Route: {data.get('route')}")
            print(f"Method: {data.get('method')}")
            print(f"Answer: {data.get('answer')[:200]}...") # Print first 200 chars
            
            if data.get('route') == 'graph':
                print("\nSUCCESS: Routed to Knowledge Graph!")
            else:
                print(f"\nFAILURE: Routed to {data.get('route')} instead of graph.")
                
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_kg()
