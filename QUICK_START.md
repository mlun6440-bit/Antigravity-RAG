# Quick Start - Asset Register ISO 55000 Specialist

## 🚀 30-Second Start

```bash
# 1. Get Gemini API key from: https://makersuite.google.com/app/apikey
# 2. Edit .env and add your API key
# 3. Run setup (one time only):
python run_asset_specialist.py --setup

# 4. Start asking questions:
python run_asset_specialist.py --interactive
```

## 📋 Common Commands

### Interactive Mode (Recommended)
```bash
python run_asset_specialist.py --interactive
```

### Ask a Single Question
```bash
python run_asset_specialist.py --query "How many assets do we have?"
```

### Get Question Suggestions
```bash
python run_asset_specialist.py --suggest
```

### Re-run Setup
```bash
python run_asset_specialist.py --setup
```

## 💡 Example Questions

**Beginner:**
- "How many assets do we have?"
- "What types of assets do we manage?"
- "Show me recently added assets"

**Maintenance:**
- "Which assets need maintenance this month?"
- "Show me overdue maintenance tasks"

**Compliance:**
- "Are we compliant with ISO 55000?"
- "What data is missing for compliance?"

**Financial:**
- "What is our total asset value?"
- "Which assets are most expensive?"

**Risk:**
- "What are our highest-risk assets?"
- "How does ISO 55000 define risk?"

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| "API key not found" | Edit `.env` and add `GEMINI_API_KEY` |
| "credentials.json not found" | Copy from YouTube project or download new |
| "Asset index not found" | Run `python run_asset_specialist.py --setup` |
| OAuth won't work | Delete `token.pickle` and try again |
| Slow responses | Normal - Gemini API takes 2-10 seconds |

## 📁 Important Files

```
Asset/
├── run_asset_specialist.py    # Main script
├── .env                        # Your API keys (EDIT THIS!)
├── credentials.json            # Google OAuth
├── README.md                   # Full documentation
├── SETUP_GUIDE.md             # Detailed setup
└── data/.tmp/                 # Cached data (auto-generated)
```

## ⚡ Pro Tips

1. **Use Interactive Mode** - Best experience for multiple questions
2. **Type "suggest"** - Get question ideas anytime
3. **Be Specific** - Better questions = better answers
4. **Cite Sources** - Answers include which files/sections
5. **ISO Expertise** - Ask about ISO 55000 standards too!

## 🆘 Need Help?

1. Read [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed setup
2. Read [README.md](README.md) for complete documentation
3. Check `workflows/` folder for specific workflow guides

---

**Ready to start?**
```bash
python run_asset_specialist.py --interactive
```
