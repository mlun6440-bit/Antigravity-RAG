# Quick Reference - Asset Register ISO 55000 Specialist

## 🚀 Start Using (3 Commands)

### 1. First Time Setup
```bash
cd "c:\Users\eralu\OneDrive\Desktop\Asset managment\N8N NAT\Asset"
py run_asset_specialist.py --setup
```

### 2. Interactive Mode (Main Way to Use)
```bash
py run_asset_specialist.py --interactive
```

### 3. Single Query
```bash
py run_asset_specialist.py --query "your question"
```

---

## 💬 What to Type in Interactive Mode

### Questions (READ)
```
How many assets do we have?
Show me poor condition assets
What does ISO 55001 say about maintenance?
Which building has the most assets?
```

### Updates (UPDATE)
```
update asset A-001 condition to Poor
change all Fair to Poor
set A-123 status to Critical
```

### Create (CREATE)
```
add new asset: Pump 6, Building C, Good condition
create asset with name: Generator 5, location: Basement
```

### Delete (DELETE)
```
delete asset A-999
remove asset A-123
```

### Special Commands
```
suggest         - Get question ideas
exit            - Quit interactive mode
```

---

## 📝 Output Format

Every answer includes:

```
Your question answered here with inline citations [1], [2], [3].

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REFERENCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1] Asset Data - Description
    Source: Asset register Part 1
    Sheet: Sheet1
    Field: Condition
    Asset IDs: A-001, A-002, ...

[2] ISO 55001:2014 - Section title
    Section: 8.3
    Pages: 24-26
    Excerpt: "Exact quote..."
```

---

## 🎯 Common Tasks

| Task | Command |
|------|---------|
| Count assets | `How many assets?` |
| Find by condition | `Show me poor condition assets` |
| Get ISO guidance | `What does ISO 55001 say about...` |
| Update one asset | `update asset A-001 condition to Poor` |
| Bulk update | `change all Fair to Poor` |
| Add asset | `add new asset: Pump 6, Building C` |
| Delete asset | `delete asset A-999` |
| Get suggestions | `suggest` |

---

## ✅ What's Working

- ✅ **Queries** - Ask anything about 1,853 assets
- ✅ **Citations** - NotebookLM-style references
- ✅ **Updates** - Single and bulk updates
- ✅ **Creates** - Add new assets
- ✅ **Deletes** - Remove assets
- ✅ **ISO Expertise** - ISO 55000/55001/55002
- ✅ **Authentication** - WRITE permissions granted

---

## 📚 Full Documentation

- **[SYSTEM_READY.md](SYSTEM_READY.md)** - Complete setup status
- **[USER_GUIDE.md](USER_GUIDE.md)** - Full manual (600+ lines)
- **[EXAMPLE_OUTPUTS.md](EXAMPLE_OUTPUTS.md)** - Real examples
- **[README.md](README.md)** - Project overview

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Gemini API key not found" | Edit .env file |
| "Asset index not found" | Run setup first |
| No citations showing | Re-run setup |
| Permission denied | Already fixed ✅ |

---

## ⚡ Quick Tips

1. **Use Interactive Mode** - Best experience
2. **Type 'suggest'** - If unsure what to ask
3. **Check References** - Verify all claims
4. **Test Before Bulk** - Update one first
5. **Chain Questions** - Ask follow-ups

---

**Start now:** `py run_asset_specialist.py --interactive`
