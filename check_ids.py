import json

def check_ids():
    with open('data/.tmp/asset_index.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    assets = data.get('assets', [])
    missing_id_count = 0
    empty_id_count = 0
    valid_id_count = 0
    
    for i, asset in enumerate(assets):
        id_val = asset.get('')
        if id_val is None:
            missing_id_count += 1
            if missing_id_count < 5:
                print(f"Missing ID example {i}: {list(asset.keys())[:5]}")
        elif id_val == "":
            empty_id_count += 1
        else:
            valid_id_count += 1
            
    print(f"Total assets: {len(assets)}")
    print(f"Missing ID key: {missing_id_count}")
    print(f"Empty ID value: {empty_id_count}")
    print(f"Valid ID value: {valid_id_count}")

if __name__ == "__main__":
    check_ids()
