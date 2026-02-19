import json
import os

def count_precise_air():
    path = 'data/.tmp/asset_index.json'
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    assets = data.get('assets', [])
    print(f"Total assets in index: {len(assets)}")
    
    precise_air_count = 0
    precise_air_assets = []
    
    # Check all keys for 'Precise Air'
    for asset in assets:
        match = False
        for k, v in asset.items():
            if isinstance(v, str) and 'Precise Air' in v:
                match = True
                print(f"Match found in field '{k}': {v}")
                break
        
        if match:
            precise_air_count += 1
            precise_air_assets.append(asset.get('Asset ID') or asset.get('ID', 'Unknown'))

    with open('debug_result.txt', 'w') as f:
        f.write(f"Total assets in index: {len(assets)}\n")
        f.write(f"Total 'Precise Air' assets found: {precise_air_count}\n")
        f.write(f"IDs: {precise_air_assets}\n")
    
    print(f"Results written to debug_result.txt")

if __name__ == "__main__":
    count_precise_air()
