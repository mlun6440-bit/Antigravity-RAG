# Google Sheets Citation Links - Setup Guide

**Date:** 2026-02-06
**Feature:** Add clickable Google Sheets links to citation panel for client verification

---

## What Was Added

Your citation panel now includes a **"🔗 View Source Spreadsheet"** button that opens the exact Google Sheet where data was sourced.

**Before:**
```
[2] Asset Data
Source: Asset register Part 3
Sheet: part_3
Records: 6
```

**After:**
```
[2] Asset Data
Source: Asset register Part 3
Sheet: part_3
Records: 6
🔗 View Source Spreadsheet  ← NEW BUTTON
```

---

## Setup Instructions

### Step 1: Get Your Google Sheets URLs

For each asset register part (1-9), you need to get the direct URL:

1. **Open the Google Sheet in your browser**
2. **Look at the URL in the address bar** - it should look like:
   ```
   https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit#gid=0
   ```

3. **Copy the entire URL** (make sure it includes `#gid=XXXXX` at the end)

4. **Repeat for each spreadsheet part** (Parts 1-7 from Google Sheets)

---

### Step 2: Update the Configuration File

1. **Open this file:** `tools/spreadsheet_config.py`

2. **Find the `SPREADSHEET_URLS` dictionary** (around line 21)

3. **Replace the placeholder URLs** with your actual URLs:

```python
SPREADSHEET_URLS: Dict[str, str] = {
    # Replace these URLs with your actual Google Sheets URLs
    "part_1": "https://docs.google.com/spreadsheets/d/YOUR_ACTUAL_ID_HERE/edit#gid=0",
    "part_2": "https://docs.google.com/spreadsheets/d/YOUR_ACTUAL_ID_HERE/edit#gid=0",
    "part_3": "https://docs.google.com/spreadsheets/d/YOUR_ACTUAL_ID_HERE/edit#gid=0",
    "part_4": "https://docs.google.com/spreadsheets/d/YOUR_ACTUAL_ID_HERE/edit#gid=0",
    "part_5": "https://docs.google.com/spreadsheets/d/YOUR_ACTUAL_ID_HERE/edit#gid=0",
    "part_6": "https://docs.google.com/spreadsheets/d/YOUR_ACTUAL_ID_HERE/edit#gid=0",
    "part_7": "https://docs.google.com/spreadsheets/d/YOUR_ACTUAL_ID_HERE/edit#gid=0",

    # Excel files (Parts 8-9) - no direct URLs available
    "part_8": None,
    "part_9": None,
}
```

4. **Save the file**

---

### Step 3: Test the Configuration

1. **Open Command Prompt** in the project folder

2. **Run the configuration test:**
   ```bash
   python tools/spreadsheet_config.py
   ```

3. **Check the output:**
   ```
   ======================================================================
   SPREADSHEET URL CONFIGURATION
   ======================================================================

   ✅ 7 sheet(s) configured with URLs:
     • part_1: https://docs.google.com/spreadsheets/d/1Bx...
     • part_2: https://docs.google.com/spreadsheets/d/1Bx...
     • part_3: https://docs.google.com/spreadsheets/d/1Bx...
     ...
   ```

4. **If you see "⚠️ No sheets configured yet!":**
   - You need to update the URLs in Step 2

---

### Step 4: Restart the System

1. **Stop the Asset Manager** (if running)

2. **Restart using the desktop shortcut** or:
   ```bash
   python web_app.py
   ```

3. **Open your browser** to `localhost:5000`

---

## Testing the Feature

### Test 1: Basic Citation with Link

1. **Ask a question** that references asset data:
   ```
   Which assets were added most recently?
   ```

2. **Click on the citation number** [2] in the answer

3. **Citation panel should open** with source details

4. **Look for the green button** at the bottom:
   ```
   🔗 View Source Spreadsheet
   ```

5. **Click the button** - it should open the Google Sheet in a new tab

---

### Test 2: Verify Correct Sheet Opens

1. **Check the spreadsheet that opens**
   - Does it match the "Source" shown in the citation?
   - Does it show the correct data?

2. **If wrong sheet opens:**
   - Check the `#gid=XXXXX` part of your URL
   - Each tab in a Google Sheet has a unique GID
   - Make sure you copied the URL while viewing the correct tab

---

## Troubleshooting

### Problem: Button doesn't appear

**Possible causes:**
1. **Sheet not configured** - URL is still set to placeholder (`YOUR_SPREADSHEET_ID_HERE`)
2. **Sheet name mismatch** - The citation says `part_3` but your config file has `Part_3` (case-sensitive)
3. **Excel file** - Parts 8-9 are Excel files and don't have Google Sheets URLs

**Solution:**
- Run `python tools/spreadsheet_config.py` to check configuration
- Make sure sheet names match exactly
- Only Google Sheets (Parts 1-7) will have clickable links

---

### Problem: Wrong spreadsheet opens

**Cause:** Incorrect GID in the URL

**Solution:**
1. Open the correct Google Sheet tab in your browser
2. Copy the FULL URL including `#gid=NUMBER`
3. Update `spreadsheet_config.py` with the correct URL
4. Restart the system

---

### Problem: "Permission denied" when clicking link

**Cause:** Client doesn't have access to your Google Sheets

**Solutions:**

**Option 1: Give clients "Viewer" access**
1. Open the Google Sheet
2. Click "Share" button
3. Add client email with "Viewer" permissions
4. Click "Send"

**Option 2: Make sheets "Anyone with link can view"**
1. Open the Google Sheet
2. Click "Share" → "Change to anyone with the link"
3. Set permission to "Viewer"
4. Click "Done"

**Option 3: Keep internal-only** (recommended if data is sensitive)
- Don't share Google Sheet access
- Only you can verify sources
- Clients see citation details but can't click through

---

## Sheet Name Reference

| Sheet Name | Type | URL Needed? |
|------------|------|-------------|
| `part_1` | Google Sheets | ✅ Yes |
| `part_2` | Google Sheets | ✅ Yes |
| `part_3` | Google Sheets | ✅ Yes |
| `part_4` | Google Sheets | ✅ Yes |
| `part_5` | Google Sheets | ✅ Yes |
| `part_6` | Google Sheets | ✅ Yes |
| `part_7` | Google Sheets | ✅ Yes |
| `part_8` | Excel | ❌ No (not supported) |
| `part_9` | Excel | ❌ No (not supported) |

---

## Files Modified

1. **`tools/spreadsheet_config.py`** (NEW)
   - Configuration file mapping sheet names to URLs
   - You must edit this file with your URLs

2. **`tools/citation_formatter.py`**
   - Updated to include `spreadsheet_url` in citation data
   - No manual changes needed

3. **`templates/index.html`**
   - Added green "View Source Spreadsheet" button
   - Added CSS styling for the button
   - No manual changes needed

---

## Advanced: Adding More Sheets

If you have additional sheets beyond Parts 1-9:

1. **Open `tools/spreadsheet_config.py`**

2. **Add new entries** to the `SPREADSHEET_URLS` dictionary:
   ```python
   "custom_sheet_name": "https://docs.google.com/spreadsheets/d/YOUR_ID/edit#gid=123",
   ```

3. **Make sure the sheet name** matches exactly what appears in citations

4. **Save and restart** the system

---

## Security Considerations

### Who Can See What?

**Your System (localhost):**
- Only you can access the Asset Manager interface
- Only you see the citations and buttons

**Google Sheets Access:**
- Controlled by Google Sheets permissions (separate from Asset Manager)
- If you give client "Viewer" access, they can view the sheet
- If you don't share access, only you can open the links

**Recommended Setup:**
- **Internal use:** Keep Google Sheets private (you only)
- **Client presentations:** Share specific sheets as "View only" temporarily
- **Sensitive data:** Don't share Google Sheets access at all

---

## Next Steps

1. ✅ Complete Step 2 (update URLs in `spreadsheet_config.py`)
2. ✅ Run Step 3 (test configuration)
3. ✅ Restart system
4. ✅ Test with a real query
5. ✅ Decide on client access permissions

---

## Support

**Configuration test command:**
```bash
python tools/spreadsheet_config.py
```

**Common sheet names to check:**
- `part_1`, `part_2`, `part_3`, etc. (lowercase)
- `Sheet1` (if you have standalone sheets)

**Need help?**
- Check that URLs include `#gid=NUMBER`
- Sheet names are case-sensitive
- Excel files (Parts 8-9) cannot have clickable links

---

**Last Updated:** 2026-02-06
**Feature Version:** 1.0
