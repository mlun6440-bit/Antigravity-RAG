# Asset Register ISO 55000 Specialist - System Architecture

## High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────┐        ┌─────────────────────┐                   │
│  │   Web Browser        │        │  Command Line       │                   │
│  │  (localhost:5000)    │        │  Interface (CLI)    │                   │
│  │                      │        │                      │                   │
│  │  - Query Input       │        │  - Direct Queries   │                   │
│  │  - Results Display   │        │  - CRUD Operations  │                   │
│  │  - Suggestions       │        │  - Batch Updates    │                   │
│  └──────────┬───────────┘        └──────────┬──────────┘                   │
│             │                               │                               │
└─────────────┼───────────────────────────────┼───────────────────────────────┘
              │                               │
              │ HTTP/JSON                     │ Direct Python Call
              │                               │
┌─────────────▼───────────────────────────────▼───────────────────────────────┐
│                         APPLICATION LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │                      web_app.py (Flask)                        │         │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │         │
│  │  │ Rate Limiter │  │ CORS Filter  │  │ Input Sanitizer      │ │         │
│  │  │ 10/min       │  │ localhost    │  │ XSS/Injection Guard  │ │         │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘ │         │
│  │                                                                │         │
│  │  API Endpoints:                                                │         │
│  │  - POST /api/query         -> Query Handler                   │         │
│  │  - GET  /api/suggestions   -> Question Suggester              │         │
│  │  - GET  /api/status        -> System Status                   │         │
│  │  - POST /api/crud          -> CRUD Operations                 │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                                                                              │
└──────────────────────────────────┬───────────────────────────────────────────┘
                                   │
                                   │ Component Orchestration
                                   │
┌──────────────────────────────────▼───────────────────────────────────────────┐
│                          CORE PROCESSING LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              gemini_query_engine.py (Main Query Engine)             │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────┐    │   │
│  │  │              Query Processing Pipeline                      │    │   │
│  │  │                                                             │    │   │
│  │  │  1. Query Preprocessing                                    │    │   │
│  │  │     - Synonym Expansion                                    │    │   │
│  │  │     - Pattern Extraction (Asset IDs, Status Codes)         │    │   │
│  │  │     - Filter Detection                                     │    │   │
│  │  │                                                             │    │   │
│  │  │  2. Direct Field Lookup (if applicable)                    │    │   │
│  │  │     - Asset ID Index                                       │    │   │
│  │  │     - Condition Code Index                                 │    │   │
│  │  │     - Status Index                                         │    │   │
│  │  │                                                             │    │   │
│  │  │  3. Semantic Search (if embeddings available)              │    │   │
│  │  │     -> embedding_manager.py                                │    │   │
│  │  │     - Generate Query Embedding                             │    │   │
│  │  │     - Cosine Similarity Search                             │    │   │
│  │  │     - Hybrid Ranking (80% semantic + 20% keyword)          │    │   │
│  │  │                                                             │    │   │
│  │  │  4. Keyword Search (fallback/hybrid)                       │    │   │
│  │  │     - Expanded Term Matching                               │    │   │
│  │  │     - Relevance Scoring (3x for exact matches)             │    │   │
│  │  │     - Top-50 Candidates                                    │    │   │
│  │  │                                                             │    │   │
│  │  │  5. Two-Stage Reranking                                    │    │   │
│  │  │     ┌──────────────────────────────────────────────┐       │    │   │
│  │  │     │  Stage 1: Gemini Flash (Cheap & Fast)       │       │    │   │
│  │  │     │  - Rerank top-20 candidates                  │       │    │   │
│  │  │     │  - Return top-10 most relevant               │       │    │   │
│  │  │     │  - Cost: ~$0.0001 per query                  │       │    │   │
│  │  │     └──────────────────────────────────────────────┘       │    │   │
│  │  │                          │                                  │    │   │
│  │  │     ┌────────────────────▼──────────────────────────┐      │    │   │
│  │  │     │  Stage 2: Gemini Pro (Expensive & Accurate)  │      │    │   │
│  │  │     │  - Context Building with top-10 assets        │      │    │   │
│  │  │     │  - Generate comprehensive answer              │      │    │   │
│  │  │     │  - Citation formatting                        │      │    │   │
│  │  │     │  - Cost: ~$0.005 per query                    │      │    │   │
│  │  │     └───────────────────────────────────────────────┘      │    │   │
│  │  │                                                             │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────┐  │
│  │  command_parser.py   │  │  asset_updater.py    │  │ embedding_mgr.py │  │
│  │                      │  │                      │  │                  │  │
│  │  - Intent Detection  │  │  - CRUD Operations   │  │  - text-embed-004│  │
│  │  - Parameter Extract │  │  - Bulk Updates      │  │  - Cosine Sim    │  │
│  │  - Command Routing   │  │  - Validation        │  │  - Hybrid Search │  │
│  └──────────────────────┘  └──────────────────────┘  └──────────────────┘  │
│                                                                              │
│  ┌──────────────────────┐  ┌──────────────────────┐                         │
│  │ question_suggester   │  │  citation_formatter  │                         │
│  │                      │  │                      │                         │
│  │  - Context Analysis  │  │  - Source Tracking   │                         │
│  │  - Smart Suggestions │  │  - Citation Links    │                         │
│  └──────────────────────┘  └──────────────────────┘                         │
│                                                                              │
└──────────────────────────────────┬───────────────────────────────────────────┘
                                   │
                                   │ Data Access
                                   │
┌──────────────────────────────────▼───────────────────────────────────────────┐
│                            DATA ACCESS LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │                     drive_reader.py                            │         │
│  │                                                                 │         │
│  │  - Google Drive API Authentication (OAuth 2.0)                 │         │
│  │  - Read Google Sheets (Parts 1-7)                              │         │
│  │  - Download Excel Files (Parts 8-9)                            │         │
│  │  - Download PDF Files (ISO Standards)                          │         │
│  │  - Token Refresh & Caching                                     │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │                   iso_pdf_parser.py                            │         │
│  │                                                                 │         │
│  │  - PDF Text Extraction                                         │         │
│  │  - Section Detection                                           │         │
│  │  - Chunk Creation (overlap for context)                        │         │
│  │  - Knowledge Base Building                                     │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                                                                              │
└──────────────────────────────────┬───────────────────────────────────────────┘
                                   │
                                   │ Read/Write Data
                                   │
┌──────────────────────────────────▼───────────────────────────────────────────┐
│                              DATA LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                   data/.tmp/ (Local Cache)                          │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────┐    │   │
│  │  │  asset_index.json (141,887 assets)                         │    │   │
│  │  │                                                             │    │   │
│  │  │  Structure:                                                │    │   │
│  │  │  {                                                          │    │   │
│  │  │    "assets": [                                             │    │   │
│  │  │      {                                                      │    │   │
│  │  │        "Asset ID": "A-001",                                │    │   │
│  │  │        "Description": "...",                               │    │   │
│  │  │        "Condition": "R3 Good",                             │    │   │
│  │  │        "Criticality": "High",                              │    │   │
│  │  │        "_source_file": "Part 1",                           │    │   │
│  │  │        ... (110 fields total)                              │    │   │
│  │  │      }                                                      │    │   │
│  │  │    ],                                                       │    │   │
│  │  │    "indexes": {                                            │    │   │
│  │  │      "by_field": {                                         │    │   │
│  │  │        "Asset ID": { "A-001": [...] },                     │    │   │
│  │  │        "Condition": { "R3 Good": [...] }                   │    │   │
│  │  │      }                                                      │    │   │
│  │  │    },                                                       │    │   │
│  │  │    "statistics": {                                         │    │   │
│  │  │      "total_assets": 141887,                               │    │   │
│  │  │      "total_fields": 110,                                  │    │   │
│  │  │      "field_stats": {...}                                  │    │   │
│  │  │    }                                                        │    │   │
│  │  │  }                                                          │    │   │
│  │  └────────────────────────────────────────────────────────────┘    │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────┐    │   │
│  │  │  iso_knowledge_base.json                                   │    │   │
│  │  │                                                             │    │   │
│  │  │  {                                                          │    │   │
│  │  │    "standards": {                                          │    │   │
│  │  │      "ISO 55000": {                                        │    │   │
│  │  │        "sections": [...],                                  │    │   │
│  │  │        "chunks": [...]                                     │    │   │
│  │  │      },                                                     │    │   │
│  │  │      "ISO 55001": {...},                                   │    │   │
│  │  │      "ISO 55002": {...}                                    │    │   │
│  │  │    },                                                       │    │   │
│  │  │    "all_chunks": [...]                                     │    │   │
│  │  │  }                                                          │    │   │
│  │  └────────────────────────────────────────────────────────────┘    │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────┐    │   │
│  │  │  asset_embeddings.npy (Optional - Not Yet Generated)       │    │   │
│  │  │                                                             │    │   │
│  │  │  - 141,887 x 768 dimensional vectors                       │    │   │
│  │  │  - Generated by text-embedding-004                         │    │   │
│  │  │  - Used for semantic search                                │    │   │
│  │  │  - Requires: pip install scikit-learn numpy                │    │   │
│  │  └────────────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────┬───────────────────────────────────────────┘
                                   │
                                   │ Source Data
                                   │
┌──────────────────────────────────▼───────────────────────────────────────────┐
│                         EXTERNAL DATA SOURCES                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Google Drive                                   │   │
│  │  (Folder ID: 1nyQoHepnlQC2q4OT558B_h29nFHQuGEj)                     │   │
│  │                                                                      │   │
│  │  Google Sheets:                                                     │   │
│  │  - Asset Register Part 1 (Sheet)                                    │   │
│  │  - Asset Register Part 2 (Sheet)                                    │   │
│  │  - Asset Register Part 3 (Sheet)                                    │   │
│  │  - Asset Register Part 4 (Sheet)                                    │   │
│  │  - Asset Register Part 5 (Sheet)                                    │   │
│  │  - Asset Register Part 6 (Sheet)                                    │   │
│  │  - Asset Register Part 7 (Sheet)                                    │   │
│  │                                                                      │   │
│  │  Excel Files:                                                       │   │
│  │  - Asset Register Part 8 (.xlsx)                                    │   │
│  │  - Asset Register Part 9 (.xlsx)                                    │   │
│  │                                                                      │   │
│  │  PDF Documents:                                                     │   │
│  │  - ISO 55000.pdf (Overview & Principles)                            │   │
│  │  - ISO 55001.pdf (Requirements)                                     │   │
│  │  - ISO 55002.pdf (Guidelines)                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘


┌──────────────────────────────────────────────────────────────────────────────┐
│                       EXTERNAL AI SERVICES                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                  Google Gemini API                                  │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────┐    │   │
│  │  │  gemini-1.5-flash-latest                                   │    │   │
│  │  │  - Cost: $0.075 per 1M input tokens                        │    │   │
│  │  │  - Usage: Retrieval & Reranking (Stage 1)                  │    │   │
│  │  │  - Speed: Very Fast                                        │    │   │
│  │  └────────────────────────────────────────────────────────────┘    │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────┐    │   │
│  │  │  gemini-2.5-pro                                            │    │   │
│  │  │  - Cost: $1.25 per 1M input tokens                         │    │   │
│  │  │  - Usage: Final Answer Synthesis (Stage 2)                 │    │   │
│  │  │  - Speed: Moderate                                         │    │   │
│  │  │  - Context: Up to 1M tokens                                │    │   │
│  │  └────────────────────────────────────────────────────────────┘    │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────┐    │   │
│  │  │  text-embedding-004                                        │    │   │
│  │  │  - Cost: $0.00001 per 1K tokens                            │    │   │
│  │  │  - Usage: Semantic Search Embeddings                       │    │   │
│  │  │  - Dimensions: 768                                         │    │   │
│  │  │  - Task Types: retrieval_document, retrieval_query         │    │   │
│  │  └────────────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagrams

### 1. Query Processing Flow

```
User Query: "Show me all poor condition assets"
    │
    ▼
┌─────────────────────────────────────────┐
│ 1. Input Sanitization                   │
│    - Remove dangerous chars             │
│    - Length validation (max 1000)       │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ 2. Query Preprocessing                  │
│    - Extract: "poor" -> ["poor", "r1", │
│      "failed", "bad"]                   │
│    - Detect intent: READ operation      │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ 3. Direct Field Lookup                  │
│    - Check Condition index for "poor"   │
│    - If found -> Return immediately     │
└─────────────┬───────────────────────────┘
              │ (no direct match)
              ▼
┌─────────────────────────────────────────┐
│ 4. Keyword Search (Hybrid)              │
│    - Score each asset (0-100)           │
│    - Exact match: 3x weight             │
│    - Return top-50 candidates           │
└─────────────┬───────────────────────────┘
              │ [50 candidates]
              ▼
┌─────────────────────────────────────────┐
│ 5. Rerank with Flash (Stage 1)          │
│    - Send top-20 to Gemini Flash        │
│    - Get reranked top-10                │
│    - Cost: ~$0.0001                     │
└─────────────┬───────────────────────────┘
              │ [10 best assets]
              ▼
┌─────────────────────────────────────────┐
│ 6. Build Context (RAG)                  │
│    - Add statistics                     │
│    - Add ISO knowledge (if relevant)    │
│    - Add top-10 assets with citations   │
└─────────────┬───────────────────────────┘
              │ [Context: ~50K tokens]
              ▼
┌─────────────────────────────────────────┐
│ 7. Query Gemini Pro (Stage 2)           │
│    - Generate comprehensive answer      │
│    - Format citations                   │
│    - Cost: ~$0.005                      │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ 8. Return Answer                        │
│    - JSON response with citations       │
│    - Display in Web UI                  │
└─────────────────────────────────────────┘
```

### 2. Setup/Indexing Flow

```
User runs: python run_asset_specialist.py --setup
    │
    ▼
┌──────────────────────────────────────────┐
│ 1. Authenticate with Google Drive        │
│    - OAuth 2.0 flow                      │
│    - Save token.pickle                   │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ 2. Discover Files in Drive Folder        │
│    - List all files in folder            │
│    - Identify: Sheets, Excel, PDFs       │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ 3. Download & Parse Assets               │
│    - Parts 1-7: Google Sheets API        │
│    - Parts 8-9: Download Excel -> Parse  │
│    - Combine into single list            │
└──────────────┬───────────────────────────┘
               │ [141,887 assets]
               ▼
┌──────────────────────────────────────────┐
│ 4. Build Indexes                         │
│    - Index by Asset ID                   │
│    - Index by Condition                  │
│    - Index by Location                   │
│    - Index by Criticality                │
│    - Calculate statistics                │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ 5. Save asset_index.json                 │
│    - 141,887 assets                      │
│    - 110 fields                          │
│    - All indexes                         │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ 6. Parse ISO PDF Standards               │
│    - Extract text from PDFs              │
│    - Detect sections                     │
│    - Create chunks with overlap          │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ 7. Save iso_knowledge_base.json          │
│    - 3 standards                         │
│    - All chunks                          │
└──────────────────────────────────────────┘
```

### 3. CRUD Update Flow

```
User: "Update asset A-001 condition to Poor"
    │
    ▼
┌──────────────────────────────────────────┐
│ 1. Intent Detection                      │
│    - command_parser.py                   │
│    - Detects: UPDATE operation           │
│    - Extracts: asset_id=A-001,           │
│      field=Condition, value=Poor         │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ 2. Require Confirmation                  │
│    - Return to user for approval         │
│    - Show preview of change              │
└──────────────┬───────────────────────────┘
               │ User confirms
               ▼
┌──────────────────────────────────────────┐
│ 3. Load Current Data                     │
│    - Read asset_index.json               │
│    - Find asset A-001                    │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ 4. Apply Update                          │
│    - Modify Condition field              │
│    - Update indexes                      │
│    - Update statistics                   │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ 5. Save to Local Cache                   │
│    - Write asset_index.json              │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ 6. Sync to Google Drive (Future)         │
│    - Update source spreadsheet           │
│    - (Not yet implemented)               │
└──────────────────────────────────────────┘
```

---

## Component Details

### Security Layer
- **Rate Limiter**: Flask-Limiter with 10/min, 100/hour limits
- **CORS**: Restricted to localhost origins only
- **Input Sanitization**: Removes `<>"'` and limits to 1000 chars
- **Logging**: All queries logged with IP + timestamp

### Query Engine Enhancements
1. **Phase 1 - Preprocessing**:
   - Synonym expansion (poor -> poor, r1, failed, bad)
   - Pattern extraction (Asset IDs, codes)
   - Direct index lookups (instant results)

2. **Phase 2 - Semantic Search** (optional):
   - text-embedding-004 for vector generation
   - Cosine similarity ranking
   - Hybrid weighting (80% semantic, 20% keyword)

3. **Phase 3 - Two-Stage Pipeline**:
   - Flash: Rerank top-20 -> top-10 (~$0.0001)
   - Pro: Generate final answer (~$0.005)
   - **80-90% cost reduction**

### Data Management
- **Local Cache**: JSON files in `data/.tmp/`
- **Google Drive**: Source of truth (read-only currently)
- **Indexes**: Pre-built for instant lookups
- **Statistics**: Cached for quick status checks

---

## Cost Optimization

### Before Optimization
```
Query: "Show poor assets"
├─ Gemini Pro: Build context + Answer
│  └─ Cost: ~$0.0125 (10K tokens @ $1.25/1M)
└─ Total: $0.0125 per query
```

### After Optimization (Two-Stage)
```
Query: "Show poor assets"
├─ Stage 1: Gemini Flash (Reranking)
│  └─ Cost: ~$0.0001 (1K tokens @ $0.075/1M)
├─ Stage 2: Gemini Pro (Answer only)
│  └─ Cost: ~$0.005 (4K tokens @ $1.25/1M)
└─ Total: ~$0.0051 per query
```

**Savings**: ~59% cost reduction + better accuracy

---

## System Statistics

- **Total Assets**: 141,887
- **Total Fields**: 110
- **Source Files**: 9 (7 Sheets + 2 Excel)
- **ISO Standards**: 3 (55000, 55001, 55002)
- **Response Time**: 2-5 seconds (with reranking)
- **Rate Limit**: 10 queries/min per IP
- **Context Size**: Up to 1M tokens (Gemini Pro)

---

## Technology Stack

### Backend
- Python 3.13
- Flask 3.x (Web framework)
- Google Gemini API (AI models)
- Google Drive API v3 (Data source)

### Machine Learning
- scikit-learn (Cosine similarity)
- numpy (Vector operations)
- Google text-embedding-004 (Embeddings)

### Security
- Flask-CORS (Origin restriction)
- Flask-Limiter (Rate limiting)
- OAuth 2.0 (Google authentication)

### Data Formats
- JSON (Local cache)
- Google Sheets (Parts 1-7)
- Excel (Parts 8-9)
- PDF (ISO standards)

---

## Future Enhancements

1. **Database Migration**: PostgreSQL for better scalability
2. **Authentication**: User login system
3. **Backup System**: Automated backups before CRUD
4. **HTTPS**: SSL/TLS for production
5. **Cost Monitoring**: Track API usage
6. **Bidirectional Sync**: Write changes back to Google Drive
7. **Advanced Analytics**: Dashboards, charts, trends

---

**Last Updated**: 2026-01-31
**Version**: 2.0 (Two-Stage Pipeline + Semantic Search)
