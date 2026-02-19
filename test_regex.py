import re

def _is_zero_result(ans_str):
    ans = ans_str.lower()
    print(f"Testing string: '{ans}'")
    
    # 1. Exact matches
    if ans.strip() in ['0', 'none', 'no', 'false']: 
        print("MATCH: Exact")
        return True
    
    # 2. Key phrases
    if 'empty dataframe' in ans: 
        print("MATCH: empty dataframe")
        return True
    if 'no assets found' in ans: 
        print("MATCH: no assets found")
        return True
    if 'found 0 assets' in ans: 
        print("MATCH: found 0 assets")
        return True
    
    # 3. Regex for "**0**" or " 0 assets"
    if re.search(r'\*\*0\*\*\s+assets', ans): 
        print("MATCH: Regex **0** assets")
        return True
    if re.search(r'found\s+0\s+', ans): 
        print("MATCH: Regex found 0")
        return True
    if re.search(r'returned\s+0\s+', ans): 
        print("MATCH: Regex returned 0")
        return True
        
    print("NO MATCH")
    return False

test_str_1 = "**0** assets matching condition=poor and asset_type=HVAC."
test_str_2 = "Found 0 matching assets."
test_str_3 = "0"

_is_zero_result(test_str_1)
_is_zero_result(test_str_2)
_is_zero_result(test_str_3)
