# Azure Migration Roadmap

**Objective:** Migrate Asset Management System from Google services to Microsoft Azure ecosystem.

**Timeline:** 6-10 weeks (phased approach)
**Budget:** $76-185/month operational cost (vs current $10-30/month)

---

## Current State (Google Stack)

```
User Browser
    ↓
Flask Web App (localhost:5000)
    ↓
Google Gemini API
    ├── gemini-1.5-flash-latest (fast retrieval)
    ├── gemini-2.5-pro (deep analysis)
    └── text-embedding-004 (semantic search)
    ↓
SQLite Database (141,887 assets)
    ↓
Google Sheets (data source)
```

**Monthly Cost:** ~$10-30 (Gemini API only)

---

## Target State (Microsoft Azure)

```
User Browser
    ↓
Azure Web App (App Service)
    ↓
Azure OpenAI Service
    ├── gpt-4o-mini (fast retrieval)
    ├── gpt-5 (deep analysis & synthesis)
    └── text-embedding-3-large (semantic search)
    ↓
Azure SQL Database OR SQLite (141,887 assets)
    ↓
Azure Blob Storage (PDF documents)
    ↓
Azure Key Vault (secrets management)
```

**Monthly Cost:** $76-185 (full Azure stack)

---

## Migration Phases

### Phase 1: LLM Migration (2-3 weeks)
**Goal:** Replace Google Gemini with Azure OpenAI, keep everything else local

**What Changes:**
- ✅ Switch from Gemini API to Azure OpenAI API
- ✅ Migrate to GPT-5 (synthesis) and GPT-4o-mini (fast queries)
- ✅ Update embedding generation
- ⏸️ Keep Flask running locally
- ⏸️ Keep SQLite database
- ⏸️ Keep Google Sheets sync

**Files to Modify:**
1. `.env` - Add Azure OpenAI credentials
2. `tools/azure_openai_query_engine.py` (NEW) - Azure API wrapper
3. `web_app.py` - Switch to Azure query engine
4. `tools/consultant_analyzer.py` - Use Azure for analysis
5. `requirements.txt` - Add `openai>=1.12.0`

**Testing:**
- Test query: "How many poor condition fire systems?"
- Test consultant analysis: "Risk assessment for electrical switchboards"
- Test citations: Verify PDF references work
- Test embeddings: Semantic search accuracy

**Cost Impact:** +$10-20/month (Azure OpenAI usage)

**Rollback:** Keep old Gemini code, switch back via .env flag

---

### Phase 2: Web Hosting Migration (1-2 weeks)
**Goal:** Move Flask app from localhost to Azure Web App

**What Changes:**
- ✅ Deploy Flask to Azure App Service
- ✅ Configure environment variables in Azure
- ✅ Set up HTTPS with custom domain (optional)
- ⏸️ SQLite stays local (on Azure VM disk)
- ⏸️ Google Sheets sync still active

**Files to Modify:**
1. `startup.py` (NEW) - Azure App Service entry point
2. `requirements.txt` - Add production dependencies
3. `.deployment` (NEW) - Azure deployment config
4. `web_app.py` - Add production config (CORS, security headers)

**Azure Resources Needed:**
- App Service Plan (B1 Basic tier: ~$13/month)
- Application Insights (monitoring: ~$0-5/month)

**Testing:**
- Access via Azure URL: `https://your-app.azurewebsites.net`
- Test all API endpoints
- Verify rate limiting works
- Check HTTPS certificate

**Cost Impact:** +$13-18/month

**Rollback:** Keep localhost running, switch DNS back

---

### Phase 3: Data Migration (2-4 weeks)
**Goal:** Move from SQLite to Azure SQL Database (optional)

**What Changes:**
- ✅ Migrate 141,887 assets to Azure SQL
- ✅ Update data sync from Google Sheets
- ✅ Rewrite queries for SQL Server syntax
- ✅ Set up automated backups

**Files to Modify:**
1. `tools/database_manager.py` - Add Azure SQL support
2. `tools/migrate_to_azure_sql.py` (NEW) - Migration script
3. `.env` - Add Azure SQL connection string
4. All query functions - Update SQL syntax

**Azure Resources Needed:**
- Azure SQL Database (Basic tier: ~$5/month)
- OR keep SQLite (no additional cost)

**Testing:**
- Verify all 141,887 assets migrated correctly
- Test query performance (<100ms target)
- Validate full-text search works
- Test concurrent user access

**Cost Impact:** +$5-10/month (if using Azure SQL)

**Recommendation:** Consider keeping SQLite to save costs unless you need:
- Multi-user concurrent writes
- Advanced reporting features
- Integration with Power BI

**Rollback:** Restore SQLite from backup

---

### Phase 4: PDF Storage Migration (1 week)
**Goal:** Move ISO standard PDFs to Azure Blob Storage

**What Changes:**
- ✅ Upload PDFs to Azure Blob Storage
- ✅ Update citation system to load from Blob
- ✅ Configure CDN for faster delivery (optional)

**Files to Modify:**
1. `tools/pdf_manager.py` (NEW) - Blob Storage integration
2. `web_app.py` - Update PDF serving endpoint
3. `templates/index.html` - Update PDF.js viewer URL

**Azure Resources Needed:**
- Blob Storage (Hot tier: ~$0.02/GB/month)
- Estimated: 500MB of PDFs = ~$0.01/month

**Testing:**
- Click citation [1] - verify PDF loads
- Test auto-scroll to page number
- Verify PDF viewer works in all browsers

**Cost Impact:** <$1/month

**Rollback:** Point PDF URLs back to local files

---

## Complete Cost Breakdown

### Current Google Stack
| Service | Cost/Month |
|---------|-----------|
| Gemini API (1000 queries) | $10-30 |
| Localhost hosting | $0 |
| **Total** | **$10-30** |

### Azure Stack (Phase 1 Only)
| Service | Cost/Month |
|---------|-----------|
| Azure OpenAI (1000 queries) | $20-50 |
| Localhost hosting | $0 |
| **Total** | **$20-50** |

### Azure Stack (All Phases)
| Service | Cost/Month |
|---------|-----------|
| Azure OpenAI (1000 queries) | $20-50 |
| App Service (B1 Basic) | $13 |
| Azure SQL (Basic) OR SQLite | $5 or $0 |
| Blob Storage (500MB) | <$1 |
| Application Insights | $0-5 |
| Key Vault | $0 (free tier) |
| **Total (with SQL)** | **$76-185** |
| **Total (SQLite)** | **$38-69** |

**Recommendation:** Phase 1 + Phase 2 only = $33-68/month (7x more functionality, 3x cost)

---

## Detailed Implementation: Phase 1 (LLM Migration)

### Step 1: Azure OpenAI Setup (30 minutes)

**1. Create Azure OpenAI Resource:**
```bash
# Login to Azure
az login

# Create resource group
az group create --name rg-asset-management --location australiaeast

# Create Azure OpenAI service
az cognitiveservices account create \
  --name openai-asset-management \
  --resource-group rg-asset-management \
  --kind OpenAI \
  --sku S0 \
  --location australiaeast
```

**2. Deploy Models:**
- Go to Azure Portal → Azure OpenAI Studio
- Deploy `gpt-5` (name it "gpt-5") - For deep analysis and synthesis
- Deploy `gpt-4o-mini` (name it "gpt-4o-mini") - For fast retrieval
- Deploy `text-embedding-3-large` (name it "text-embedding")

**3. Get API Keys:**
```bash
az cognitiveservices account keys list \
  --name openai-asset-management \
  --resource-group rg-asset-management
```

Copy `key1` to `.env`

---

### Step 2: Update Environment Variables (5 minutes)

**Add to `.env`:**
```bash
# Azure OpenAI Configuration
AZURE_OPENAI_KEY=your-key-here
AZURE_OPENAI_ENDPOINT=https://openai-asset-management.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_GPT5=gpt-5
AZURE_OPENAI_DEPLOYMENT_GPT4O_MINI=gpt-4o-mini
AZURE_OPENAI_DEPLOYMENT_EMBEDDING=text-embedding

# Feature flags (for gradual rollover)
USE_AZURE_OPENAI=true  # Set to false to rollback to Gemini
```

---

### Step 3: Create Azure Query Engine (1 hour)

**Create `tools/azure_openai_query_engine.py`:**

```python
"""
Azure OpenAI Query Engine
Replaces Google Gemini with Azure OpenAI (Microsoft LLMs)
"""

import os
from openai import AzureOpenAI
from typing import List, Dict, Any

class AzureOpenAIQueryEngine:
    def __init__(self):
        """Initialize Azure OpenAI client"""
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-02-15-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )

        # Model mappings (Gemini → Azure OpenAI)
        self.fast_model = os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT4O_MINI")  # Was: gemini-1.5-flash
        self.synthesis_model = os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT5")   # Was: gemini-2.5-pro
        self.embedding_model = os.getenv("AZURE_OPENAI_DEPLOYMENT_EMBEDDING")

    def query_fast(self, prompt: str, system_prompt: str = None) -> str:
        """
        Fast retrieval using GPT-4o-mini
        Equivalent to: gemini-1.5-flash-latest
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.fast_model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )

        return response.choices[0].message.content

    def query_synthesis(self, prompt: str, system_prompt: str = None, context: str = None) -> str:
        """
        Deep analysis and synthesis using GPT-5
        Equivalent to: gemini-2.5-pro
        Best for: Multi-source reasoning, expert analysis, ISO framework application
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if context:
            messages.append({"role": "system", "content": f"Context:\n{context}"})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.synthesis_model,
            messages=messages,
            temperature=0.7,
            max_tokens=4000
        )

        return response.choices[0].message.content

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings using text-embedding-3-large
        Equivalent to: text-embedding-004
        """
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=texts
        )

        return [item.embedding for item in response.data]
```

---

### Step 4: Update Web App (30 minutes)

**Modify `web_app.py`:**

Find the section that initializes Gemini and replace with:

```python
# Feature flag: Use Azure OpenAI or Gemini
USE_AZURE = os.getenv("USE_AZURE_OPENAI", "false").lower() == "true"

if USE_AZURE:
    from tools.azure_openai_query_engine import AzureOpenAIQueryEngine
    query_engine = AzureOpenAIQueryEngine()
    print("✅ Using Azure OpenAI (Microsoft LLMs)")
else:
    # Keep existing Gemini code as fallback
    import google.generativeai as genai
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    print("⚠️ Using Google Gemini (fallback mode)")
```

Update query functions:

```python
@app.route('/api/query', methods=['POST'])
def handle_query():
    question = request.json.get('question')

    # Stage 1: Fast retrieval
    if USE_AZURE:
        relevant_assets = query_engine.query_fast(
            prompt=f"Find assets matching: {question}",
            system_prompt="You are an asset management search expert."
        )
    else:
        # Existing Gemini code
        relevant_assets = gemini_flash.generate_content(...)

    # Stage 2: Deep analysis and synthesis
    if USE_AZURE:
        answer = query_engine.query_synthesis(
            prompt=question,
            system_prompt="You are an ISO 55000 asset management consultant.",
            context=relevant_assets
        )
    else:
        # Existing Gemini code
        answer = gemini_pro.generate_content(...)

    return jsonify({"answer": answer})
```

---

### Step 5: Update Consultant Analyzer (30 minutes)

**Modify `tools/consultant_analyzer.py`:**

```python
import os
from tools.azure_openai_query_engine import AzureOpenAIQueryEngine

USE_AZURE = os.getenv("USE_AZURE_OPENAI", "false").lower() == "true"

if USE_AZURE:
    query_engine = AzureOpenAIQueryEngine()

def analyze_with_consultant(question: str, initial_answer: str, assets: list) -> dict:
    """Apply ISO 55000 frameworks using Azure OpenAI"""

    # Load asset management consultant skill
    skill_context = load_skill("asset-management-consultant")

    analysis_prompt = f"""
    {skill_context}

    Question: {question}
    Initial Answer: {initial_answer}
    Asset Data: {assets}

    Provide consultant-level analysis with:
    1. Risk assessment (ISO 55000 framework)
    2. Lifecycle costing recommendations
    3. Compliance requirements
    4. Actionable recommendations
    """

    if USE_AZURE:
        analysis = query_engine.query_synthesis(
            prompt=analysis_prompt,
            system_prompt="You are a senior asset management consultant specializing in ISO 55000."
        )
    else:
        # Existing Gemini code
        analysis = gemini_pro.generate_content(analysis_prompt)

    return {"analysis": analysis}
```

---

### Step 6: Update Requirements (5 minutes)

**Modify `requirements.txt`:**

```txt
# Existing dependencies
Flask==3.0.0
google-generativeai==0.3.2  # Keep for fallback
pandas==2.1.4
python-dotenv==1.0.0

# NEW: Azure OpenAI
openai>=1.12.0
azure-identity>=1.15.0

# Existing dependencies continue...
```

Install new dependencies:
```bash
pip install openai>=1.12.0 azure-identity>=1.15.0
```

---

### Step 7: Testing Checklist

**Test Suite:**

1. **Basic Query Test:**
   ```
   Question: "How many assets do we have?"
   Expected: Returns count of 141,887 assets
   ✅ Verify answer matches SQLite count
   ```

2. **Condition Filter Test:**
   ```
   Question: "How many poor condition fire systems?"
   Expected: Returns filtered count with risk assessment
   ✅ Verify matches: SELECT COUNT(*) FROM assets WHERE condition='Poor' AND type LIKE '%fire%'
   ```

3. **Consultant Analysis Test:**
   ```
   Question: "Risk assessment for electrical switchboards over 20 years old"
   Expected: Triggers consultant mode with:
   - Risk matrix (likelihood × consequence)
   - ISO 55000 citations
   - Budget estimates
   - Recommendations
   ✅ Verify consultant analysis section appears
   ```

4. **Citation Test:**
   ```
   Question: "What does ISO 55000 say about risk management?"
   Expected: Returns answer with citations [1] [2] [3]
   ✅ Click citation → PDF viewer opens
   ✅ PDF auto-scrolls to correct page
   ```

5. **Embedding Test:**
   ```
   Question: "Fire safety equipment needing maintenance"
   Expected: Semantic search finds relevant assets
   ✅ Compare results to old Gemini embeddings
   ✅ Verify accuracy is 95%+
   ```

6. **Performance Test:**
   ```
   Run 10 queries back-to-back
   ✅ Average response time: <5 seconds
   ✅ No rate limit errors
   ✅ No timeout errors
   ```

7. **Cost Test:**
   ```
   Run 100 test queries
   ✅ Check Azure OpenAI usage in portal
   ✅ Verify cost is ~$0.50-1.00 per 100 queries
   ```

---

### Step 8: Rollback Plan

**If something breaks:**

1. **Immediate Rollback (30 seconds):**
   ```bash
   # Set in .env
   USE_AZURE_OPENAI=false

   # Restart Flask
   Ctrl+C
   python web_app.py
   ```
   System reverts to Google Gemini immediately.

2. **Troubleshooting:**
   - Check Azure OpenAI deployment names match .env
   - Verify API key is correct
   - Check quota limits in Azure Portal
   - Review error logs in terminal

3. **Partial Rollback:**
   ```python
   # Use Azure for fast queries, Gemini for deep analysis
   USE_AZURE_FAST = true
   USE_AZURE_DEEP = false
   ```

---

## Phase 2-4 Summary (High-Level)

### Phase 2: Azure Web App Deployment
**Timeline:** 1-2 weeks after Phase 1 stable

**Key Steps:**
1. Create Azure App Service (B1 tier)
2. Configure environment variables in Azure Portal
3. Deploy Flask app via Git or Azure CLI
4. Set up custom domain (optional)
5. Configure SSL certificate
6. Test public URL access

**Files Needed:**
- `startup.py` - Azure App Service entry point
- `.deployment` - Build configuration
- `web.config` or `startup.txt` - Python runtime config

---

### Phase 3: Azure SQL Migration
**Timeline:** 2-4 weeks (optional)

**Key Steps:**
1. Create Azure SQL Database (Basic tier)
2. Run migration script to copy 141,887 assets
3. Update connection strings
4. Rewrite SQL queries for T-SQL syntax
5. Test all queries
6. Set up automated backups

**Recommendation:** Skip this phase to save $5-10/month. SQLite handles 141k rows easily.

---

### Phase 4: Blob Storage for PDFs
**Timeline:** 1 week

**Key Steps:**
1. Create Azure Storage Account
2. Upload ISO standard PDFs
3. Configure public read access or SAS tokens
4. Update PDF.js viewer URLs
5. Test citation system

**Cost:** <$1/month (500MB of PDFs)

---

## Migration Timeline (Gantt Chart)

```
Week 1-2    : Phase 1 - Azure OpenAI integration
Week 2      : Phase 1 - Testing and validation
Week 3      : Phase 1 - Production cutover
Week 4-5    : Phase 2 - Azure Web App deployment
Week 5      : Phase 2 - Testing and DNS cutover
Week 6-9    : Phase 3 - Azure SQL (optional)
Week 10     : Phase 4 - Blob Storage for PDFs

Critical Path: Phase 1 → Phase 2 (Phase 3 and 4 are optional)
```

---

## Success Criteria

### Phase 1 Success:
- ✅ All existing queries work identically
- ✅ Response time <5 seconds (same as Gemini)
- ✅ 95%+ accuracy on test queries
- ✅ Citations work with PDF auto-scroll
- ✅ Consultant analysis triggers correctly
- ✅ Cost <$50/month for 1000 queries

### Phase 2 Success:
- ✅ Public URL accessible via HTTPS
- ✅ Rate limiting prevents abuse
- ✅ 99.9% uptime (Azure SLA)
- ✅ Environment variables secured
- ✅ Monitoring and logging active

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Azure OpenAI quota exceeded | Medium | High | Start with low quotas, request increase |
| API syntax differences | High | Medium | Thorough testing, feature flag rollback |
| Cost overrun | Medium | Medium | Set budget alerts, monitor daily |
| Performance degradation | Low | High | Load testing before cutover |
| Data loss during migration | Low | Critical | Full backups before each phase |

---

## Decision Points

### Should you migrate?

**Migrate to Azure if:**
- ✅ You want Microsoft ecosystem integration
- ✅ You need enterprise support contracts
- ✅ You're consolidating billing under Microsoft
- ✅ You plan to add Power BI reporting
- ✅ You need multi-region hosting

**Stay on Google if:**
- ❌ Budget is tight ($10/month vs $50+/month)
- ❌ Current system works perfectly
- ❌ No business requirement for Microsoft stack
- ❌ Limited time for migration project

---

## Next Steps

1. **Review this roadmap** - Confirm phases align with your goals
2. **Approve budget** - Azure will cost 3-5x more than Gemini
3. **Start Phase 1** - I'll create the Azure OpenAI integration code
4. **Test locally** - Validate everything works before cloud deployment
5. **Phase 2-4 optional** - Decide later based on Phase 1 results

---

**Last Updated:** 2026-02-06
**Document Owner:** Asset Management System
**Reviewed By:** [Pending]
