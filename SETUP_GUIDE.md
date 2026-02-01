# Setup Guide - Asset Register ISO 55000 Specialist

This guide will walk you through setting up the system for the first time.

## Step-by-Step Setup

### Step 1: Get Google Gemini API Key

1. Go to https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Click **"Create API Key"** or **"Get API Key"**
4. Copy the API key (starts with `AIzaSy...`)

**Important**: Keep this key secret! Never share it publicly.

### Step 2: Configure API Key

1. Open the `.env` file in the Asset/ directory
2. Find the line: `GEMINI_API_KEY=your_gemini_api_key_here`
3. Replace `your_gemini_api_key_here` with your actual API key
4. Save the file

Example:
```env
GEMINI_API_KEY=AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz1234567
```

### Step 3: Set Up Google OAuth Credentials

You can reuse the credentials from the YouTube analytics project:

#### Option A: Copy Existing Credentials (Easiest)
```bash
# Copy from YouTube project
copy "..\U tube analysis\credentials.json" credentials.json
```

#### Option B: Download New Credentials
1. Go to https://console.cloud.google.com/
2. Select your project (or create a new one)
3. Enable these APIs:
   - Google Drive API
   - Google Sheets API
4. Create OAuth 2.0 credentials:
   - Application type: Desktop app
   - Name: "Asset Register Specialist"
5. Download `credentials.json`
6. Place it in the Asset/ directory

### Step 4: Install Python Dependencies

```bash
# Navigate to Asset directory
cd "c:\Users\eralu\OneDrive\Desktop\Asset managment\N8N NAT\Asset"

# Install all required packages
pip install -r requirements.txt
```

**Expected packages**:
- google-api-python-client
- google-auth
- google-generativeai
- pandas
- PyPDF2
- pdfplumber
- python-dotenv
- etc.

### Step 5: Verify Google Drive Access

1. Open Google Drive: https://drive.google.com/
2. Navigate to the RAG1 folder
3. Verify you can see:
   - 7 Google Sheets (Asset register Part 1-7)
   - 2 Excel files (part_8.xlsx, part_9.xlsx)
   - 3 PDF files (ISO 55000/55001/55002)

### Step 6: Run Initial Setup

```bash
python run_asset_specialist.py --setup
```

**What happens**:
1. **OAuth authentication** (first time only)
   - Browser window will open
   - Sign in to Google
   - Grant permissions
   - Browser will show "Authentication successful"
   - Close browser and return to terminal

2. **Fetch asset registers**
   - Downloads all 9 asset files
   - Reads Google Sheets via API
   - Downloads Excel files
   - Downloads PDF files
   - Combines into single JSON

3. **Parse ISO standards**
   - Extracts text from PDFs
   - Chunks into sections
   - Creates searchable knowledge base

4. **Index asset data**
   - Analyzes schema
   - Creates searchable indexes
   - Generates statistics

**Expected output**:
```
=== ASSET REGISTER ISO 55000 SPECIALIST - SETUP ===

STEP 1: Fetching Asset Registers from Google Drive
----------------------------------------------------------------------
✓ Authenticated with Google
✓ Found 12 files in folder
Reading Google Sheet: Asset register Part 1...
  ✓ Sheet 'Sheet1': 245 rows
[... more files ...]

✓ Combined data saved to: data/.tmp/asset_registers_combined.json
  - Google Sheets: 7
  - Excel files: 2
  - PDF files: 3

STEP 2: Parsing ISO 55000 Standard Documents
----------------------------------------------------------------------
Extracting text from ASISO55000-20241.pdf...
  ✓ Extracted 125,432 characters
[... more PDFs ...]

✓ Knowledge base saved to: data/.tmp/iso_knowledge_base.json
  - Total standards: 3
  - Total chunks: 287

STEP 3: Indexing Asset Data
----------------------------------------------------------------------
Processing: Asset register Part 1
  ✓ Sheet 'Sheet1': 245 records
[... more files ...]

✓ Total assets extracted: 1,853

✓ Index saved to: data/.tmp/asset_index.json
  - Total assets: 1,853
  - Total fields: 42
  - Indexed fields: 15

✓ SETUP COMPLETE!
```

**Time required**: 3-5 minutes

### Step 7: Test the System

#### Test 1: Simple Query
```bash
python run_asset_specialist.py --query "How many assets do we have?"
```

Expected response should include the total count from your data.

#### Test 2: Question Suggestions
```bash
python run_asset_specialist.py --suggest --num 5
```

Should display 5 suggested questions.

#### Test 3: Interactive Mode
```bash
python run_asset_specialist.py --interactive
```

Try asking:
- "What types of assets do we manage?"
- "suggest" (to see question ideas)
- "exit" (to quit)

## Verification Checklist

After setup, verify these files exist:

```
Asset/
├── credentials.json           ✓ (OAuth credentials)
├── token.pickle              ✓ (Generated during setup)
├── .env                      ✓ (With your Gemini API key)
│
└── data/.tmp/
    ├── asset_registers_combined.json  ✓ (Combined asset data)
    ├── asset_index.json              ✓ (Searchable index)
    ├── iso_knowledge_base.json       ✓ (ISO standards knowledge base)
    ├── part_8.xlsx                   ✓ (Downloaded Excel file)
    ├── part_9.xlsx                   ✓ (Downloaded Excel file)
    ├── ASISO55000-20241.pdf          ✓ (ISO 55000 standard)
    ├── ASISO55001-20241.pdf          ✓ (ISO 55001 standard)
    └── ASISO55002-20241.pdf          ✓ (ISO 55002 standard)
```

## Troubleshooting Setup

### Issue: "Module not found" errors
**Solution**:
```bash
pip install -r requirements.txt --upgrade
```

### Issue: OAuth browser doesn't open
**Solution**:
1. Check your default browser is set
2. Try manually opening the URL shown in terminal
3. Complete authentication
4. Copy auth code back to terminal if needed

### Issue: "Permission denied" on Google Drive
**Solution**:
1. Verify the Drive folder is accessible
2. Check you're signed in with correct Google account
3. Delete `token.pickle` and re-authenticate:
```bash
del token.pickle
python run_asset_specialist.py --setup
```

### Issue: "Gemini API key invalid"
**Solution**:
1. Verify you copied the complete API key
2. Check for extra spaces in `.env` file
3. Ensure key is active in Google AI Studio
4. Generate a new key if needed

### Issue: PDF parsing fails
**Solution**:
- This is optional - system works without ISO knowledge base
- PDFs might be protected or corrupted
- You can skip this step and still query assets
- To fix: Download PDFs manually and ensure they're readable

### Issue: Setup takes very long
**Possible causes**:
- Large asset files (normal if you have many assets)
- Slow internet connection
- Google API rate limiting

**What to do**:
- Be patient - first setup always takes longer
- Don't interrupt the process
- Check progress messages
- If it fails, you can re-run setup (it will resume)

## Post-Setup Configuration

### Optional: Update Google Drive Folder ID

If you want to use a different folder:

1. Get the folder ID from the URL:
   ```
   https://drive.google.com/drive/folders/FOLDER_ID_HERE
   ```

2. Edit `.env`:
   ```env
   ASSET_REGISTER_FOLDER_ID=your_new_folder_id
   ```

3. Re-run setup:
   ```bash
   python run_asset_specialist.py --setup
   ```

### Optional: Change Gemini Model

For more capable (but slower/pricier) responses:

Edit `.env`:
```env
GEMINI_MODEL=gemini-1.5-pro-latest
```

Default `gemini-1.5-flash-latest` is recommended for most use cases.

## Next Steps

Once setup is complete:

1. **Read the README.md** for detailed usage instructions
2. **Try example questions** from the README
3. **Explore workflows/** for detailed documentation
4. **Start using interactive mode** for best experience

## Getting Help

If you encounter issues not covered here:

1. Check the **README.md** troubleshooting section
2. Review **workflow documentation** in `workflows/`
3. Check that all files in verification checklist exist
4. Verify API keys and credentials are correct
5. Try re-running setup with a fresh start:
   ```bash
   # Delete cached data
   rmdir /s data\.tmp
   del token.pickle

   # Re-run setup
   python run_asset_specialist.py --setup
   ```

## Success!

If you've completed all steps, you're ready to start using the Asset Register ISO 55000 Specialist!

Try this:
```bash
python run_asset_specialist.py --interactive
```

Happy querying! 🚀
