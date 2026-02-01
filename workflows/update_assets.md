# Workflow: Update Asset Data

## Objective
Update asset records in Google Sheets and Excel files, including bulk updates for multiple assets at once.

## Prerequisites
- Asset data fetched and indexed
- **Write permissions** - You need to re-authenticate for write access
- Confirmation before making changes

## ⚠️ Important: Re-Authentication Required

The update tool requires **WRITE** permissions. You'll need to:

1. Delete your current token:
```bash
del token.pickle
```

2. Run the update tool - it will ask for re-authentication:
```bash
python tools/asset_updater.py update --asset-id A-001 --field Condition --value Poor
```

3. Browser will open - grant **full access** to Google Sheets and Drive

## Usage Examples

### Update Single Asset

```bash
# Update asset condition
python tools/asset_updater.py update \
  --asset-id "A-001" \
  --field "Condition" \
  --value "Poor"
```

**What happens:**
```
=== Updating Asset A-001 ===

Asset ID: A-001
Field: Condition
Current Value: Fair
New Value: Poor

Source: Asset register Part 1 / Sheet1

Proceed with update? (y/n): y

✓ Updated Asset register Part 1
  - Old Condition: Fair
  - New Condition: Poor
  - Updated in Google Sheets ✓
```

### Bulk Update by Criteria

```bash
# Update all "Fair" condition assets to "Poor"
python tools/asset_updater.py bulk \
  --filter-field "Condition" \
  --filter-value "Fair" \
  --update-field "Condition" \
  --new-value "Poor"
```

**What happens:**
```
=== Bulk Update ===
Filter: Condition = Fair
Update: Condition → Poor

Found 523 matching assets:
  1. A-015: Condition = Fair
  2. A-023: Condition = Fair
  3. A-047: Condition = Fair
  ... and 520 more

Update all 523 assets? (y/n): y

✓ Updated 523 assets
✓ Change log saved: data/.tmp/update_log.json
```

### Update Multiple Specific Assets

```bash
# Update several assets in Building A
python tools/asset_updater.py bulk \
  --filter-field "Location" \
  --filter-value "Building A" \
  --update-field "Status" \
  --new-value "Under Review"
```

### Skip Confirmation (Dangerous!)

```bash
# Auto-confirm - use with caution!
python tools/asset_updater.py update \
  --asset-id "A-001" \
  --field "Condition" \
  --value "Poor" \
  --no-confirm
```

## Common Update Scenarios

### Scenario 1: Update Asset Condition

```bash
python tools/asset_updater.py update \
  --asset-id "A-123" \
  --field "Condition" \
  --value "Poor"
```

### Scenario 2: Bulk Downgrade Condition

```bash
# Change all "Fair" to "Poor"
python tools/asset_updater.py bulk \
  --filter-field "Condition" \
  --filter-value "Fair" \
  --update-field "Condition" \
  --new-value "Poor"
```

### Scenario 3: Update Location

```bash
python tools/asset_updater.py update \
  --asset-id "A-456" \
  --field "Location" \
  --value "Building C"
```

### Scenario 4: Bulk Status Update

```bash
# Mark all assets in a location for review
python tools/asset_updater.py bulk \
  --filter-field "Location" \
  --filter-value "Site 2" \
  --update-field "Review Status" \
  --new-value "Pending"
```

### Scenario 5: Update Maintenance Date

```bash
python tools/asset_updater.py update \
  --asset-id "A-789" \
  --field "Last Maintenance" \
  --value "2026-01-28"
```

## How Updates Work

### For Google Sheets:
1. Finds the asset in the index
2. Gets the source file ID and sheet name
3. Locates the exact cell (row + column)
4. Updates via Google Sheets API
5. Changes reflect immediately in Drive

### For Excel Files:
1. Downloads the Excel file
2. Opens with pandas
3. Finds and updates the row
4. Saves the modified file
5. Re-uploads to Google Drive

## Change Tracking

Every update is logged to `data/.tmp/update_log.json`:

```json
[
  {
    "timestamp": "2026-01-28T14:35:22",
    "asset_id": "A-001",
    "field": "Condition",
    "old_value": "Fair",
    "new_value": "Poor",
    "source_file": "Asset register Part 1"
  },
  {
    "timestamp": "2026-01-28T14:36:15",
    "asset_id": "A-002",
    "field": "Condition",
    "old_value": "Good",
    "new_value": "Fair",
    "source_file": "Asset register Part 2"
  }
]
```

## Safety Features

### 1. Confirmation Prompts
- Shows current vs new value
- Asks for confirmation before updating
- Can be skipped with `--no-confirm` flag

### 2. Change Logging
- All updates logged with timestamp
- Old and new values recorded
- Source file tracked

### 3. Dry Run Mode
- Preview changes before applying
- Verify correct assets will be updated

### 4. Rollback Capability
- Change log allows manual rollback
- Can revert using logged old values

## Edge Cases

### Asset Not Found
**Symptom**: "Asset A-999 not found"
**Solution**:
- Verify asset ID is correct
- Run setup to refresh index
- Check asset exists in Google Drive

### Permission Denied
**Symptom**: "403 Forbidden" or "Insufficient Permission"
**Solution**:
1. Delete `token.pickle`
2. Re-run update tool
3. Grant WRITE permissions in browser

### Field Name Not Found
**Symptom**: "Column 'Condtion' not found in sheet"
**Solution**:
- Check field name spelling
- Field names are case-sensitive
- Use exact column header from spreadsheet

### Multiple Sheets in One File
**Behavior**: Updates only the source sheet
**Note**: If asset appears in multiple sheets, only one is updated

## Best Practices

### Before Bulk Updates:
1. **Query first** to see what will be affected:
```bash
python run_asset_specialist.py --query "How many assets have Condition = Fair?"
```

2. **Make a backup** of important files

3. **Test with single update** first

4. **Review change log** after updates

### Workflow:
```bash
# 1. Check current state
python run_asset_specialist.py --query "Show me Fair condition assets"

# 2. Test single update
python tools/asset_updater.py update --asset-id "A-001" --field "Condition" --value "Poor"

# 3. Verify the update
python run_asset_specialist.py --query "What is the condition of asset A-001?"

# 4. Proceed with bulk update
python tools/asset_updater.py bulk --filter-field "Condition" --filter-value "Fair" --update-field "Condition" --new-value "Poor"

# 5. Re-run setup to refresh index
python run_asset_specialist.py --setup
```

## Refreshing the Index

After making updates, refresh the index:

```bash
python run_asset_specialist.py --setup
```

This ensures queries reflect the latest data.

## Limitations

### Current Version:
- ✅ Single asset updates
- ✅ Bulk updates by filter
- ✅ Google Sheets support
- ⚠️  Excel updates (implemented but needs testing)
- ⚠️  Row number detection (simplified)
- ❌ Multi-field updates in one command
- ❌ Conditional updates (if X then Y)
- ❌ Formula preservation

### Future Enhancements:
- Import updates from CSV
- Export change report
- Undo/redo functionality
- Validate data before updating
- Update multiple fields at once

## Troubleshooting

### Error: "token.pickle has wrong permissions"
**Solution**:
```bash
del token.pickle
python tools/asset_updater.py update --asset-id A-001 --field Condition --value Poor
```

### Error: "File not found in Google Drive"
**Solution**:
- Verify file wasn't moved or deleted
- Re-run fetch to refresh file list

### Updates Not Showing in Queries
**Solution**:
```bash
# Refresh the index
python run_asset_specialist.py --setup
```

### Accidentally Updated Wrong Assets
**Solution**:
1. Check `data/.tmp/update_log.json` for old values
2. Run reverse updates using logged old values
3. Or restore from Google Drive version history

## Security Considerations

- ⚠️  Updates are **immediate** and affect live data
- 🔒 Requires explicit re-authentication for write access
- 📝 All changes are logged
- ✋ Confirmation required by default
- 🔙 Can use Google Drive version history for rollback

## Integration with Query System

After updates, the AI can verify changes:

```bash
# Before update
python run_asset_specialist.py --query "What is the condition of asset A-001?"
# Answer: "Fair"

# Update
python tools/asset_updater.py update --asset-id A-001 --field Condition --value Poor

# Refresh index
python run_asset_specialist.py --setup

# Verify
python run_asset_specialist.py --query "What is the condition of asset A-001?"
# Answer: "Poor"
```

## Next Steps

1. **Test single update** on non-critical asset
2. **Verify in Google Sheets** that change was applied
3. **Check change log** to ensure tracking works
4. **Try bulk update** with small batch
5. **Refresh index** and query to confirm

---

**Remember**: Always back up important data before bulk updates!
