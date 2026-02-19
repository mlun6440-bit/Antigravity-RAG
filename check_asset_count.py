import json

# Load the asset index
with open('data/.tmp/asset_index.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Assets in JSON: {len(data.get('assets', []))}")
print(f"Total assets stat: {data.get('statistics', {}).get('total_assets', 0)}")
print(f"Keys in data: {list(data.keys())}")
