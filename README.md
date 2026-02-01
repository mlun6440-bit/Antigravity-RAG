# Asset Register ISO 55000 Specialist

An intelligent automation system that uses Google Gemini AI with RAG (Retrieval-Augmented Generation) to answer questions about your asset registers, applying ISO 55000 series standards expertise.

## What This Does

- **Reads 9 asset register files** from Google Drive (7 Google Sheets + 2 Excel files)
- **Parses ISO 55000/55001/55002 PDFs** to create a knowledge base
- **Answers natural language questions** about your assets using Google Gemini 3.0 Flash
- **Provides ISO 55000 expert guidance** on asset management best practices
- **NotebookLM-style citations** with page numbers and exact references for full transparency
- **Natural language CRUD operations** - Update, add, or delete assets through conversational commands
- **Suggests helpful questions** for users unfamiliar with asset management
- **Interactive chat interface** for continuous Q&A

## Features

### ISO 55000 Specialist Capabilities
- Deep knowledge of ISO 55000, 55001, and 55002 standards
- Asset lifecycle management expertise
- Risk-based decision making
- Performance measurement recommendations
- Compliance checking and gap analysis

### Intelligent Query System
- Natural language understanding
- Contextual asset data retrieval (RAG)
- Relevant ISO standard citation
- Source attribution (which file, which section)
- Multi-turn conversations

### NotebookLM-Style Citations (NEW!)
- **Inline citations** [1], [2], [3] in every answer
- **Asset data citations** with exact source file, sheet name, field, and asset IDs
- **ISO standard citations** with section numbers, page numbers, and exact quotes
- **Calculation citations** showing formulas and data sources
- **Full transparency** - verify every claim the AI makes

### Natural Language CRUD Operations (NEW!)
- **UPDATE**: "update asset A-001 condition to Poor"
- **BULK UPDATE**: "change all Fair assets to Poor"
- **CREATE**: "add new asset: Pump 5, Building C, Good condition"
- **DELETE**: "delete asset A-999"
- **Confirmation prompts** before making changes
- **Change logging** for audit trail

### Beginner-Friendly
- Question suggestion system
- Categorized by difficulty (Beginner/Advanced)
- Explanations for each suggested question
- Helps users learn what they can ask

## Quick Start

### 1. Prerequisites

- **Python 3.8+** installed
- **Google Cloud Project** with these APIs enabled:
  - Google Drive API
  - Google Sheets API
- **OAuth 2.0 credentials** (`credentials.json`)
- **Google Gemini API key** (get from https://makersuite.google.com/app/apikey)

### 2. Installation

```bash
# Navigate to Asset directory
cd "c:\Users\eralu\OneDrive\Desktop\Asset managment\N8N NAT\Asset"

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

1. **Copy OAuth credentials**:
   - Place `credentials.json` in the Asset/ directory
   - (You can reuse the one from "U tube analysis" folder)

2. **Set up Gemini API key**:
   - Edit `.env` file
   - Replace `your_gemini_api_key_here` with your actual API key

```env
GEMINI_API_KEY=AIzaSy...your_actual_key_here
```

### 4. Initial Setup (Run Once)

```bash
python run_asset_specialist.py --setup
```

This will:
1. Fetch all 9 asset register files from Google Drive
2. Download and parse 3 ISO standard PDFs
3. Index all asset data for fast searching
4. Create knowledge base for RAG

**Expected time**: 3-5 minutes

### 5. Start Using

#### Ask a Question
```bash
python run_asset_specialist.py --query "How many assets do we have?"
```

#### Interactive Mode (Recommended)
```bash
python run_asset_specialist.py --interactive
```

#### Get Question Suggestions
```bash
python run_asset_specialist.py --suggest
```

## Usage Examples

### Single Query
```bash
python run_asset_specialist.py --query "Which assets need maintenance this month?"
```

### Interactive Session
```bash
python run_asset_specialist.py --interactive

# Then type questions like:
# > What types of assets do we manage?
# > Show me high-risk assets
# > Are we compliant with ISO 55000?
# > suggest  (to see question ideas)
# > exit  (to quit)
```

### Question Suggestions
```bash
# All difficulty levels
python run_asset_specialist.py --suggest

# Beginner only
python run_asset_specialist.py --suggest --difficulty beginner --num 5

# Advanced only
python run_asset_specialist.py --suggest --difficulty advanced --num 5
```

## Example Questions

### Beginner Questions
- "How many total assets are in the register?"
- "What types of assets do we manage?"
- "Show me recently added assets"
- "What fields are tracked for each asset?"

### Maintenance Questions
- "Which assets need maintenance this month?"
- "Show me assets with overdue maintenance"
- "What is the maintenance history for asset X?"

### Compliance Questions
- "Are our asset records compliant with ISO 55000?"
- "What asset data is missing for ISO 55001 compliance?"
- "How should we track asset lifecycle per ISO 55000?"

### Financial Questions
- "What is our total asset value?"
- "Which assets are most expensive?"
- "Show me assets approaching end of useful life"

### Risk Questions
- "What are our highest-risk assets?"
- "How does ISO 55000 define asset risk?"
- "Which critical assets lack risk assessments?"

### Advanced Questions
- "What is our asset lifecycle cost profile?"
- "How can we optimize asset replacement strategies?"
- "How do our practices align with ISO 55000 objectives?"

## Project Structure

```
Asset/
├── run_asset_specialist.py       # Main orchestrator script
├── .env                           # Configuration (API keys)
├── .env.template                  # Configuration template
├── requirements.txt               # Python dependencies
├── credentials.json               # Google OAuth credentials
├── token.pickle                   # OAuth token (auto-generated)
│
├── tools/                         # Execution tools (WAT Layer 3)
│   ├── drive_reader.py            # Fetch Google Drive files
│   ├── iso_pdf_parser.py          # Parse ISO standard PDFs with page tracking
│   ├── asset_data_indexer.py     # Index asset data
│   ├── gemini_query_engine.py    # Gemini API + RAG with citations
│   ├── citation_formatter.py      # NotebookLM-style citation formatting
│   ├── command_parser.py          # Natural language CRUD command parsing
│   ├── asset_updater.py           # Update/Create/Delete operations
│   └── question_suggester.py     # Generate question suggestions
│
├── workflows/                     # SOP documentation (WAT Layer 1)
│   ├── fetch_asset_registers.md
│   ├── query_asset_specialist.md
│   └── suggest_questions.md
│
├── data/
│   └── .tmp/                      # Temporary/cached data
│       ├── asset_registers_combined.json
│       ├── asset_index.json
│       ├── iso_knowledge_base.json
│       ├── *.xlsx                 # Downloaded Excel files
│       └── *.pdf                  # Downloaded ISO PDFs
│
├── CLAUDE.md                      # WAT framework instructions
└── README.md                      # This file
```

## How It Works

### WAT Framework Architecture

This project follows the **WAT (Workflows, Agents, Tools)** architecture:

1. **Workflows** (Layer 1): Markdown SOPs in `workflows/` define what to do
2. **Agents** (Layer 2): You (or AI) make intelligent decisions
3. **Tools** (Layer 3): Python scripts execute deterministic tasks

### RAG (Retrieval-Augmented Generation) Flow

```
User Question
     ↓
[Context Retrieval]
     ├── Search relevant assets (keyword matching)
     ├── Find relevant ISO sections
     └── Compile statistics
     ↓
[Prompt Construction]
     ├── System prompt: "You are an ISO 55000 expert..."
     ├── Retrieved context (assets + ISO standards)
     └── User question
     ↓
[Gemini API Call]
     ↓
[Formatted Answer]
     ├── Answer text
     ├── Asset citations
     ├── ISO clause references
     └── Recommendations
```

## Configuration

### Environment Variables (.env)

```env
# Google Drive
ASSET_REGISTER_FOLDER_ID=1nyQoHepnlQC2q4OT558B_h29nFHQuGEj

# Google Gemini AI
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-1.5-flash-latest

# System
MAX_CONTEXT_TOKENS=1000000
CACHE_EXPIRY_HOURS=24
DEBUG_MODE=False
```

### Google Drive Folder Contents

Your Google Drive folder should contain:
- **Asset register Part 1-7** (Google Sheets)
- **part_8.xlsx, part_9.xlsx** (Excel files)
- **ASISO55000-20241.pdf** (ISO 55000 standard)
- **ASISO55001-20241.pdf** (ISO 55001 standard)
- **ASISO55002-20241.pdf** (ISO 55002 standard)

## Troubleshooting

### "Gemini API key not found"
**Solution**:
1. Get API key from https://makersuite.google.com/app/apikey
2. Edit `.env` file
3. Replace `your_gemini_api_key_here` with actual key

### "credentials.json not found"
**Solution**:
1. Copy `credentials.json` from YouTube analytics project
2. Or download new one from Google Cloud Console
3. Place in Asset/ directory

### "Asset index not found"
**Solution**:
Run setup first:
```bash
python run_asset_specialist.py --setup
```

### OAuth Browser Won't Open
**Solution**:
1. Delete `token.pickle`
2. Run setup again
3. Browser will open for authentication

### Slow Queries
**Reasons**:
- Large context being sent to Gemini
- Many assets matching query
- Network latency

**Solutions**:
- Reduce `max_assets` in gemini_query_engine.py
- Use more specific questions
- Check internet connection

### Poor Answer Quality
**Solutions**:
- Ensure ISO PDFs were parsed successfully
- Check asset index has complete data
- Try more specific questions
- Verify RAG context is being retrieved

## Performance

### Response Times
- Simple queries: 2-5 seconds
- Complex queries: 5-10 seconds
- Setup (first time): 3-5 minutes

### API Costs
- **Google Drive/Sheets API**: Free (within quota)
- **Gemini 1.5 Flash**: ~$0.01 per 1000 queries
- **Very low cost** for typical usage

### Data Sizes
- Asset registers: ~15 MB total
- ISO PDFs: ~28 MB total
- Index files: ~5-10 MB
- Disk space needed: ~100 MB

## Advanced Usage

### Use Different Gemini Model
```bash
# Edit .env
GEMINI_MODEL=gemini-1.5-pro-latest  # More capable, slower, more expensive
```

### Re-fetch Data
```bash
# Delete cached data
rm -rf data/.tmp/*

# Re-run setup
python run_asset_specialist.py --setup
```

### Use Individual Tools
```bash
# Fetch only
python tools/drive_reader.py --folder-id YOUR_FOLDER_ID

# Parse ISO only
python tools/iso_pdf_parser.py

# Index only
python tools/asset_data_indexer.py

# Query only
python tools/gemini_query_engine.py --query "Your question"

# Suggestions only
python tools/question_suggester.py
```

## Documentation

### Complete Guides
- **[USER_GUIDE.md](USER_GUIDE.md)** - Comprehensive user manual with examples
- **[EXAMPLE_OUTPUTS.md](EXAMPLE_OUTPUTS.md)** - Real system output examples with citations
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Detailed setup instructions
- **[QUICK_START.md](QUICK_START.md)** - Fast start guide
- **[IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)** - Development status and roadmap

### Workflow Guides
- **[workflows/fetch_asset_registers.md](workflows/fetch_asset_registers.md)** - Fetch data from Google Drive
- **[workflows/query_asset_specialist.md](workflows/query_asset_specialist.md)** - Query patterns
- **[workflows/update_assets.md](workflows/update_assets.md)** - Update operations guide
- **[workflows/suggest_questions.md](workflows/suggest_questions.md)** - Question suggestions

## Future Enhancements

### Planned Features
- [ ] Semantic search with embeddings (better than keyword matching)
- [ ] Conversation history/memory
- [ ] Export reports to Google Slides/Sheets
- [ ] Email notifications
- [ ] Web UI interface
- [ ] Multi-language support
- [ ] Custom prompt templates
- [ ] Query result caching
- [ ] Undo/redo for CRUD operations
- [ ] Multi-field bulk updates

### Possible Integrations
- N8N workflows (as originally planned)
- Slack/Teams chatbot
- Dashboard visualization
- Scheduled reports
- Compliance tracking

## Contributing

This project follows the WAT framework principles:
- **Workflows**: Update markdown SOPs when you learn new edge cases
- **Tools**: Keep Python scripts deterministic and testable
- **Agents**: Document decision-making logic

## License

Internal use for asset management.

## Support

For issues or questions:
1. Check workflow documentation in `workflows/`
2. Review troubleshooting section above
3. Check Google Drive folder structure
4. Verify API keys and credentials

## Credits

Built with:
- **Google Gemini 1.5 Flash** - LLM inference
- **Google Drive/Sheets API** - Data access
- **ISO 55000 series** - Asset management standards
- **WAT Framework** - Architecture pattern

---

**Version**: 2.0
**Last Updated**: 2026-01-29
**Status**: Production Ready

**New in v2.0:**
- ✅ NotebookLM-style citations with full transparency
- ✅ Natural language CRUD operations (Update, Create, Delete)
- ✅ Enhanced ISO PDF parsing with page number tracking
- ✅ Comprehensive user guide and examples
