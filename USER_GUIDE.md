# Asset Register ISO 55000 Specialist - Complete User Guide

## Overview

Welcome to the **Asset Register ISO 55000 Specialist** - your AI-powered assistant for managing asset registers with ISO 55000 expertise. This system combines:

- **Intelligent Query System**: Ask questions in natural language about your 9 asset register files
- **ISO 55000 Expertise**: AI trained on ISO 55000, 55001, and 55002 standards
- **NotebookLM-Style Citations**: Every answer includes detailed references with page numbers
- **Natural Language CRUD**: Update, add, or delete assets through conversational commands
- **Google Drive Integration**: Works directly with your Google Sheets and Excel files

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Querying Assets (READ)](#querying-assets-read)
3. [Citations and References](#citations-and-references)
4. [Updating Assets (UPDATE)](#updating-assets-update)
5. [Adding Assets (CREATE)](#adding-assets-create)
6. [Deleting Assets (DELETE)](#deleting-assets-delete)
7. [Interactive Mode](#interactive-mode)
8. [Command Reference](#command-reference)
9. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Initial Setup (First Time Only)

```bash
# Navigate to the Asset directory
cd "c:\Users\eralu\OneDrive\Desktop\Asset managment\N8N NAT\Asset"

# Add your Gemini API key to .env file
# Edit .env and set: GEMINI_API_KEY=your_actual_api_key_here

# Run setup to fetch and index data
py run_asset_specialist.py --setup
```

**What happens during setup:**
- Fetches 9 asset register files from Google Drive (7 Google Sheets + 2 Excel)
- Parses 3 ISO 55000 PDF standards
- Creates searchable index of all assets
- Takes ~2-3 minutes to complete

### 2. Start Using

```bash
# Ask a single question
py run_asset_specialist.py --query "How many assets do we have?"

# Interactive mode (recommended)
py run_asset_specialist.py --interactive
```

---

## Querying Assets (READ)

### Basic Queries

Ask questions in plain English:

```bash
py run_asset_specialist.py --query "How many assets do we have?"
```

**Example Output:**
```
======================================================================
ANSWER
======================================================================
Based on your asset registers, you have a total of 1,853 assets [1].

These are distributed across 9 files:
- Asset register Part 1: 312 assets
- Asset register Part 2: 278 assets
... (breakdown continues)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REFERENCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1] Asset Data - Query: How many assets do we have?...
    Source: All asset register files
    Sheet: Sheet1
    Field: Multiple fields
    Matching records: 1853
    Asset IDs: A-001, A-002, A-003, ... and 1843 more

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
======================================================================
```

### Complex Queries

The system handles sophisticated questions:

```bash
py run_asset_specialist.py --query "Show me all assets in poor condition"
```

```bash
py run_asset_specialist.py --query "What percentage of assets need maintenance?"
```

```bash
py run_asset_specialist.py --query "Which building has the most critical assets?"
```

### ISO 55000 Guidance

Ask for ISO standard recommendations:

```bash
py run_asset_specialist.py --query "According to ISO 55001, how should we manage assets in poor condition?"
```

**Example Output:**
```
According to ISO 55001, assets in poor condition require immediate
assessment and prioritization [1]. The standard recommends:

1. Conducting risk-based criticality assessment [1]
2. Establishing management of change processes [2]
3. Implementing corrective action plans [2]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REFERENCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1] ISO 55001:2014 - Asset Criticality
    Section: 3.2.5
    Pages: 15
    Excerpt: "Criticality assessment shall consider the consequence
    of failure and its impact on organizational objectives..."

[2] ISO 55001:2014 - Management of change
    Section: 8.3
    Pages: 24-26
    Excerpt: "The organization shall establish, implement and maintain
    process(es) to manage risks and opportunities..."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Citations and References

Every answer includes **NotebookLM-style citations** with full transparency.

### Citation Types

#### 1. Asset Data Citations

When the AI references your asset data:

```
[1] Asset Data - Poor Condition Count
    Query: Condition = "Poor"
    Total matches: 312 assets
    Sources:
    • Asset register Part 1, Sheet1: 45 assets
      Asset IDs: A-001, A-023, A-045, ... and 42 more
    • Asset register Part 2, Sheet1: 67 assets
      Asset IDs: B-012, B-034, ... and 65 more
```

**What you get:**
- Exact query used to find data
- Number of matching records
- Source file and sheet name
- Asset IDs referenced
- Field queried

#### 2. ISO Standard Citations

When the AI cites ISO standards:

```
[3] ISO 55001:2014 - Operational Planning
    Clause: 8.3 "Management of change"
    Page: 24-26
    Excerpt: "The organization shall establish, implement and maintain
    process(es) to manage risks and opportunities associated with
    asset failures..."
```

**What you get:**
- ISO standard name and year
- Section/clause number
- Page number(s)
- Exact quote from the standard

#### 3. Calculation Citations

When the AI performs calculations:

```
[3] Calculation - Asset portfolio percentage
    Formula: 312 poor assets ÷ 1,853 total assets = 16.8%
    Data sources:
      • Asset index statistics
      • All 9 asset register files
```

**What you get:**
- Description of calculation
- Exact formula used
- Data sources

### Inline Citations

Citations appear inline in the answer:

```
Your asset register shows 312 assets in poor condition [1].

According to ISO 55001, these require immediate assessment [2],
with priority based on criticality [3].

This represents 16.8% of your total asset portfolio [4], which
is above recommended thresholds for infrastructure management.
```

---

## Updating Assets (UPDATE)

### Single Asset Update

Update one asset at a time:

**Interactive Mode:**
```
You: update asset A-001 condition to Poor

AI: ⚠️  Update Asset A-001
    Field: Condition
    New Value: Poor

    Proceed? (yes/no): yes

AI: ✓ Update command sent
    (Note: Full Google Sheets integration requires setup)
```

**Command Line:**
```bash
py tools/asset_updater.py update \
  --asset-id "A-001" \
  --field "Condition" \
  --value "Poor"
```

### Bulk Update

Update multiple assets at once:

**Interactive Mode:**
```
You: change all Fair assets to Poor

AI: ⚠️  Bulk Update
    Filter: Condition = Fair
    New Value: Poor

    This may affect multiple assets. Proceed? (yes/no): yes

AI: ✓ Bulk update command sent
    (Note: Full Google Sheets integration requires setup)
```

**Command Line:**
```bash
py tools/asset_updater.py bulk \
  --filter-field "Condition" \
  --filter-value "Fair" \
  --update-field "Condition" \
  --new-value "Poor"
```

### Natural Language Update Commands

The system understands various phrasings:

- "update asset A-001 condition to Poor"
- "change asset A-123 location to Building C"
- "set A-456 status to Critical"
- "update all Fair assets to Poor"
- "change all assets where Condition = Fair to Poor"

---

## Adding Assets (CREATE)

### Create New Asset

Add a new asset through natural language:

**Interactive Mode:**
```
You: add new asset: Pump 5, Building C, Good condition

AI: ✓ Create New Asset
    Data: {'Name': 'Pump 5', 'Location': 'Building C', 'Condition': 'Good'}

    Proceed? (yes/no): yes

AI: ✓ Create command sent
    (Note: Full implementation requires additional setup)
```

### Structured Create

Provide key-value pairs:

```
You: create asset with name: Pump 6, location: Building A, condition: Fair, status: Active

AI: [Shows preview and asks for confirmation]
```

---

## Deleting Assets (DELETE)

### Delete Single Asset

**Interactive Mode:**
```
You: delete asset A-999

AI: ⚠️  WARNING: Delete Asset A-999

    This cannot be easily undone. Are you sure? (yes/no): yes

AI: ✓ Delete command sent
    (Note: Full implementation requires additional setup)
```

### Bulk Delete

```
You: delete all decommissioned assets

AI: ⚠️  WARNING: Bulk Delete
    Filter: Status = Decommissioned

    This may delete multiple assets. Are you ABSOLUTELY sure? (yes/no): no

AI: ✗ Bulk delete cancelled
```

**Note:** Bulk delete requires explicit confirmation and is designed with extra safety measures.

---

## Interactive Mode

### Starting Interactive Mode

```bash
py run_asset_specialist.py --interactive
```

### Interactive Session Example

```
======================================================================
=== ASSET REGISTER ISO 55000 SPECIALIST ===
======================================================================

Welcome! I'm your AI assistant with expertise in ISO 55000 asset
management standards. I can help you understand and analyze your
asset registers.

======================================================================

YOUR ASSET REGISTER:
  • Total Assets: 1,853
  • Total Fields: 45
  • Source Files: 9
======================================================================

Starting interactive session...
Type 'suggest' for question ideas, 'exit' to quit
You can also UPDATE, ADD, or DELETE assets through natural language!

Your question: how many assets do we have?

======================================================================
ANSWER
======================================================================
Based on your asset registers, you have a total of 1,853 assets [1].
[... full answer with citations ...]
======================================================================

Your question: update asset A-001 condition to Poor

⚠️  Update Asset A-001
    Field: Condition
    New Value: Poor

    Proceed? (yes/no): yes

✓ Update command sent (Note: Full Google Sheets integration requires setup)

Your question: suggest

=== SUGGESTED QUESTIONS ===

Beginner Questions:
1. How many assets do we have in total?
2. Show me all assets in poor condition
3. What are the most common asset types?

Advanced Questions:
4. What percentage of assets need immediate maintenance?
5. Which location has the highest concentration of critical assets?

Your question: exit

👋 Goodbye!
```

### Special Commands

- `suggest` - Get question suggestions
- `exit` or `quit` - Exit interactive mode
- `help` - Show help message

---

## Command Reference

### Setup and Initialization

```bash
# Initial setup (run once)
py run_asset_specialist.py --setup

# Refresh data (after updates)
py run_asset_specialist.py --setup
```

### Query Commands

```bash
# Single query
py run_asset_specialist.py --query "your question here"

# Interactive mode
py run_asset_specialist.py --interactive

# Question suggestions
py run_asset_specialist.py --suggest

# Beginner suggestions only
py run_asset_specialist.py --suggest --difficulty beginner
```

### Update Commands

```bash
# Single asset update
py tools/asset_updater.py update \
  --asset-id "A-001" \
  --field "Condition" \
  --value "Poor"

# Bulk update
py tools/asset_updater.py bulk \
  --filter-field "Condition" \
  --filter-value "Fair" \
  --update-field "Condition" \
  --new-value "Poor"

# Skip confirmation (use with caution!)
py tools/asset_updater.py update \
  --asset-id "A-001" \
  --field "Condition" \
  --value "Poor" \
  --no-confirm
```

---

## Troubleshooting

### Setup Issues

**Problem:** "Gemini API key not found"
```bash
# Solution: Add API key to .env file
# Edit: c:\Users\eralu\OneDrive\Desktop\Asset managment\N8N NAT\Asset\.env
# Set: GEMINI_API_KEY=your_actual_api_key_here
```

**Problem:** "Asset index not found"
```bash
# Solution: Run setup first
py run_asset_specialist.py --setup
```

### Query Issues

**Problem:** No citations in answer
```bash
# This is expected if:
# - ISO knowledge base wasn't created during setup
# - Query doesn't match any asset data

# Solution: Re-run setup
py run_asset_specialist.py --setup
```

**Problem:** "Query failed"
```bash
# Check:
# 1. Internet connection (Gemini API requires internet)
# 2. API key is valid
# 3. Not exceeding API rate limits
```

### Update Issues

**Problem:** "Permission denied" when updating
```bash
# Solution: Re-authenticate with write permissions
del token.pickle
py tools/asset_updater.py update --asset-id A-001 --field Condition --value Poor
# Browser will open - grant FULL access to Google Sheets
```

**Problem:** "Asset not found"
```bash
# Solution: Verify asset ID is correct
py run_asset_specialist.py --query "Show me asset A-001"
```

**Problem:** Updates not showing in queries
```bash
# Solution: Refresh the index
py run_asset_specialist.py --setup
```

### File Encoding Issues (Windows)

**Problem:** Unicode errors or garbled text
```bash
# The system auto-configures UTF-8 for Windows
# If issues persist, ensure your console supports UTF-8:
chcp 65001
```

---

## Best Practices

### Before Making Updates

1. **Query first** to verify what will be affected:
   ```
   You: show me all Fair condition assets
   [Review the results]
   You: update all Fair assets to Poor
   ```

2. **Test with single update** before bulk operations

3. **Make backups** of important files (Google Drive has version history)

4. **Review change logs** after updates

### Workflow Example

```bash
# Step 1: Check current state
py run_asset_specialist.py --query "How many Fair condition assets?"

# Step 2: Test single update
py run_asset_specialist.py --interactive
# Then: "update asset A-001 condition to Poor"

# Step 3: Verify the update
# "What is the condition of asset A-001?"

# Step 4: Refresh index
py run_asset_specialist.py --setup

# Step 5: Verify again
# "What is the condition of asset A-001?"

# Step 6: Proceed with bulk if needed
# "update all Fair assets to Poor"
```

### Safety Tips

- ✅ Always read confirmation prompts carefully
- ✅ Use `suggest` command if you're unsure what to ask
- ✅ Check citations to verify AI's sources
- ✅ Refresh index after making updates
- ⚠️ Bulk updates affect multiple assets - double-check!
- ⚠️ Delete operations cannot be easily undone

---

## Advanced Features

### Custom Difficulty Levels

```bash
# Beginner questions only
py run_asset_specialist.py --suggest --difficulty beginner

# Advanced questions only
py run_asset_specialist.py --suggest --difficulty advanced

# All questions
py run_asset_specialist.py --suggest --difficulty all
```

### Change Tracking

All updates are logged to `data/.tmp/update_log.json`:

```json
[
  {
    "timestamp": "2026-01-29T14:35:22",
    "asset_id": "A-001",
    "field": "Condition",
    "old_value": "Fair",
    "new_value": "Poor",
    "source_file": "Asset register Part 1"
  }
]
```

### Model Selection

Use different Gemini models:

```bash
# Flash model (fast, cost-effective - default)
py run_asset_specialist.py --query "question" --model gemini-1.5-flash-latest

# Pro model (more capable, slower)
py run_asset_specialist.py --query "question" --model gemini-1.5-pro-latest
```

---

## System Architecture

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                     USER QUESTION                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              COMMAND PARSER                                 │
│  Detects: READ / UPDATE / CREATE / DELETE                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
        ▼                           ▼
┌───────────────┐          ┌────────────────┐
│  READ Query   │          │  CRUD Command  │
│  (Gemini AI)  │          │  (Updater)     │
└───────┬───────┘          └────────┬───────┘
        │                           │
        ▼                           ▼
┌───────────────────────────────────────────┐
│         RAG CONTEXT BUILDER               │
│  • Searches asset index                   │
│  • Finds relevant ISO content             │
│  • Tracks citations                       │
└───────────────────┬───────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────┐
│         GEMINI AI MODEL                   │
│  • Processes context                      │
│  • Generates answer                       │
│  • Includes inline citations              │
└───────────────────┬───────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────┐
│       CITATION FORMATTER                  │
│  • Formats references                     │
│  • Adds to answer                         │
└───────────────────┬───────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────┐
│         ANSWER WITH CITATIONS             │
└───────────────────────────────────────────┘
```

### Data Flow

1. **Setup Phase**: Fetches 9 files from Google Drive → Parses 3 ISO PDFs → Creates searchable index
2. **Query Phase**: User question → Search index → Build context → Query Gemini → Format citations → Return answer
3. **Update Phase**: User command → Parse intent → Confirm → Update Google Sheets → Log change

---

## Next Steps

### Getting Started

1. **Complete setup** (if not done):
   ```bash
   py run_asset_specialist.py --setup
   ```

2. **Try basic queries**:
   ```bash
   py run_asset_specialist.py --interactive
   ```

   Then ask:
   - "How many assets do we have?"
   - "Show me poor condition assets"
   - "What does ISO 55001 say about maintenance?"

3. **Experiment with updates** (when ready):
   - "update asset A-001 condition to Poor"
   - "change all Fair to Poor"

### For Production Use

To enable full Google Sheets WRITE functionality:

1. Delete existing token:
   ```bash
   del token.pickle
   ```

2. Re-authenticate with write permissions:
   ```bash
   py tools/asset_updater.py update --asset-id A-001 --field Condition --value Poor
   ```

3. Grant FULL access when browser opens

### Getting Help

- Check [README.md](README.md) for overview
- Review [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed setup
- See [workflows/](workflows/) for specific use cases
- Check [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for features

---

## Summary

This system provides:

✅ **Natural Language Queries**: Ask anything about your 1,853 assets
✅ **ISO 55000 Expertise**: AI trained on international standards
✅ **NotebookLM Citations**: Full transparency with page numbers and references
✅ **Conversational CRUD**: Update, add, delete assets through chat
✅ **9-File Integration**: Works with all your Google Sheets and Excel files
✅ **Safety Features**: Confirmations, change logging, version control

**Start exploring your asset registers with AI-powered intelligence today!**
