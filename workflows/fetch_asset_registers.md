# Workflow: Fetch Asset Registers from Google Drive

## Objective
Download and combine all asset register files (Google Sheets, Excel, PDFs) from Google Drive into a unified JSON structure for processing.

## Prerequisites
- Google Drive folder ID configured in `.env`
- Valid OAuth credentials (`credentials.json`)
- Google Drive API access enabled

## Required Inputs
- **ASSET_REGISTER_FOLDER_ID**: Google Drive folder ID (from `.env`)
- **credentials.json**: OAuth 2.0 client credentials
- **token.pickle**: OAuth token (auto-generated on first run)

## Tools to Use
```bash
cd Asset
python tools/drive_reader.py --folder-id $ASSET_REGISTER_FOLDER_ID --output data/.tmp/asset_registers_combined.json
```

## Expected Outputs
- **data/.tmp/asset_registers_combined.json**: Combined data from all asset register files
- **data/.tmp/*.xlsx**: Downloaded Excel files
- **data/.tmp/*.pdf**: Downloaded ISO standard PDFs

## Output Structure
```json
{
  "google_sheets": [
    {
      "file_id": "...",
      "file_name": "Asset register Part 1",
      "type": "google_sheet",
      "sheets": {
        "Sheet1": [
          {"field1": "value1", "field2": "value2", ...}
        ]
      }
    }
  ],
  "excel_files": [...],
  "pdf_files": [...],
  "metadata": {
    "total_files": 12,
    "folder_id": "..."
  }
}
```

## Edge Cases

### Missing OAuth Token
**Symptom**: "credentials.json not found" error
**Solution**:
1. Download credentials from Google Cloud Console
2. Place in Asset/ directory
3. Re-run tool - browser will open for OAuth flow

### Insufficient Permissions
**Symptom**: "403 Forbidden" or "Insufficient Permission" errors
**Solution**:
1. Delete `token.pickle`
2. Re-authenticate with correct scopes
3. Ensure Drive folder is shared with OAuth account

### Large Files Timeout
**Symptom**: Download times out for large Excel/PDF files
**Solution**:
- Files >100MB may take time - be patient
- Check internet connection
- If fails repeatedly, download manually and place in `data/.tmp/`

### Unsupported File Types
**Symptom**: Some files skipped
**Solution**:
- Tool supports: Google Sheets, Excel (.xlsx, .xls), PDF
- Other file types are ignored (by design)

## Performance Notes
- Google Sheets: Read via API (fast)
- Excel files: Downloaded then parsed (slower for large files)
- PDFs: Downloaded only (parsed in separate workflow)
- Expected runtime: 1-3 minutes for 12 files

## Troubleshooting

### Error: "Spreadsheet ID not found"
- Check folder ID in `.env` is correct
- Verify files haven't been moved or deleted

### Error: "Rate limit exceeded"
- Google API has quota limits
- Wait a few minutes and retry
- Check quota usage in Google Cloud Console

## Next Steps
After successful fetch:
1. Run asset indexing: `python tools/asset_data_indexer.py`
2. Parse ISO PDFs: `python tools/iso_pdf_parser.py`
3. Ready for querying with Gemini
