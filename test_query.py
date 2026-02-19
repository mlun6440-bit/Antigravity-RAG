import requests
import json

url = 'http://127.0.0.1:5000/api/query'
payload = {'question': 'How many assets are there?'}
headers = {'Content-Type': 'application/json'}

try:
    print(f"Sending POST to {url} with {payload}")
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Method used: {data.get('method', 'Unknown')}")
    print(f"Answer: {data.get('answer', 'No answer')}")
    if data.get('sql_query'):
        print(f"SQL Query: {data.get('sql_query')}")
except Exception as e:
    print(f"Error: {e}")
