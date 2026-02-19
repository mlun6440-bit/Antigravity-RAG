import requests
import json
import time

def test_query():
    url = "http://127.0.0.1:5001/api/query"
    headers = {"Content-Type": "application/json"}
    
    # Analytical question that should trigger widget generation
    payload = {
        "question": "how many poor HVAC assets",
        "chat_history": []
    }
    
    print(f"Sending query: {payload['question']}")
    try:
        start_time = time.time()
        response = requests.post(url, json=payload, headers=headers)
        duration = time.time() - start_time
        
        print(f"Status Code: {response.status_code}")
        print(f"Duration: {duration:.2f}s")
        
        if response.status_code == 200:
            data = response.json()
            print("\nResponse Keys:", data.keys())
            print("Answer:", data.get('answer'))
            print("Code:", data.get('code'))
            
            widgets = data.get('widgets', [])
            print(f"\nWidgets Found: {len(widgets)}")
            if widgets:
                print(json.dumps(widgets, indent=2))
            else:
                print("❌ NO WIDGETS FOUND in response!")
                print("Answer preview:", data.get('answer', '')[:200])
                print("Route:", data.get('route'))
        else:
            print("Error:", response.text)
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_query()
