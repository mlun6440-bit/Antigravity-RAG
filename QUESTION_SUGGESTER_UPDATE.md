# Question Suggester Update - Register Improvement Focus

**Updated:** 2026-02-06
**Purpose:** Transform suggested questions to drive asset register improvement and ISO 55000 learning

---

## What Changed

The suggested questions now focus on **two strategic goals**:

1. **Improving Asset Register Quality Over Time**
2. **Building ISO 55000 Knowledge Through Practice**

---

## New Question Categories

### 1. Data Quality (Priority #1)
**Goal:** Identify and fix data gaps systematically

**Example Questions:**
- "Which critical assets lack risk assessments?"
- "Which assets have incomplete condition data?"
- "Which assets are missing installation dates?"
- "Which assets lack maintenance history?"

**How this helps:**
- Each question reveals specific data gaps
- Answers show you exactly what to fix
- Systematic improvement over time
- Better data = better decisions

---

### 2. ISO 55000 Learning (Priority #2)
**Goal:** Learn ISO standards through practical application

**Example Questions:**
- "What does ISO 55000 say about risk assessment?"
- "How should we measure asset performance per ISO 55000?"
- "What are ISO 55001 requirements for lifecycle costing?"
- "How does ISO 55000 recommend prioritizing asset interventions?"

**How this helps:**
- Learn ISO concepts in context of your data
- Build expertise incrementally
- Apply standards to real problems
- Become ISO 55000 proficient through practice

---

### 3. Critical Assets (Priority #3)
**Goal:** Identify immediate risks for action

**Example Questions:**
- "How many poor condition fire systems do we have?"
- "Show me all R4-R5 rated assets requiring immediate action"
- "Which electrical switchboards are over 20 years old?"

**How this helps:**
- Focus on life safety and critical infrastructure
- Prioritize interventions by risk
- Support urgent decision-making

---

### 4. Strategic Improvement (Priority #4)
**Goal:** Improve portfolio health systematically

**Example Questions:**
- "What building services assets need replacement in next 2 years?"
- "Which asset categories have the most data quality issues?"
- "What is the average condition rating by asset type?"
- "Which locations have the most critical condition assets?"

**How this helps:**
- Capital planning based on evidence
- Identify systematic weaknesses
- Geographic risk profiling
- Portfolio-level insights

---

### 5. Risk Assessment (Priority #5)
**Goal:** Apply ISO 55000 risk frameworks

**Example Questions:**
- "Show me high criticality assets with poor condition ratings"
- "What are the interdependencies between our critical assets?"
- "Which life safety systems lack recent inspections?"
- "What is our exposure to assets with unknown condition?"

**How this helps:**
- Risk-based prioritization (ISO 55000 core concept)
- Understand system vulnerabilities
- Quantify uncertainty risk
- Compliance risk identification

---

### 6. Lifecycle Planning (Priority #6)
**Goal:** Optimize intervention timing and capital planning

**Example Questions:**
- "Which assets need replacement in the next 2 years?"
- "Show me assets approaching end-of-life with high criticality"
- "What is the maintenance backlog for R4-R5 condition assets?"

**How this helps:**
- Age-based intervention planning
- Capital budget forecasting
- Identify maintenance deferrals causing degradation

---

### 7. Continuous Improvement (Priority #7)
**Goal:** Learn from patterns to improve strategies

**Example Questions:**
- "What patterns exist in our asset failures?"
- "Which asset types consistently degrade faster than expected?"
- "How accurate are our condition assessments compared to actual failures?"
- "What is the correlation between maintenance frequency and asset condition?"

**How this helps:**
- Evidence-based strategy improvement
- Validate assessment methods
- Optimize maintenance frequencies
- Root cause analysis of systematic issues

---

### 8. Advanced Analysis (Priority #8)
**Goal:** Strategic asset management maturity

**Example Questions:**
- "What is the lifecycle cost profile for building services vs infrastructure?"
- "How do our asset management practices align with organizational objectives per ISO 55000?"
- "What is the optimal renewal timing for assets approaching end-of-life?"
- "How can we improve asset data quality systematically?"

**How this helps:**
- Total cost of ownership analysis
- Strategic alignment (ISO 55001 requirement)
- Optimize renewal decisions
- Register maturity roadmap

---

## How to Use the New Questions

### Week 1-2: Focus on Data Quality
**Start here:**
1. "Which critical assets lack risk assessments?"
2. "Which assets have incomplete condition data?"

**Action:** Fix top 10 gaps each week

---

### Week 3-4: Learn ISO 55000
**While improving data:**
1. "What does ISO 55000 say about risk assessment?"
2. "How should we measure asset performance per ISO 55000?"

**Action:** Read cited ISO sections, apply to your register

---

### Month 2: Critical Asset Review
**Once data improves:**
1. "How many poor condition fire systems do we have?"
2. "Show me all R4-R5 rated assets requiring immediate action"

**Action:** Create intervention plans for critical assets

---

### Month 3+: Strategic Improvement
**As register matures:**
1. "Which asset categories have the most data quality issues?"
2. "What patterns exist in our asset failures?"

**Action:** Systematic improvements based on evidence

---

## Expected Outcomes

### After 3 Months:
- ✅ 50% reduction in critical data gaps
- ✅ Working knowledge of ISO 55000 risk frameworks
- ✅ All R4-R5 assets have intervention plans

### After 6 Months:
- ✅ 80% data completeness for critical assets
- ✅ ISO 55001-compliant condition assessment process
- ✅ Evidence-based capital planning

### After 12 Months:
- ✅ ISO 55001 audit-ready asset register
- ✅ Expert-level ISO 55000 knowledge
- ✅ Proactive asset management culture

---

## Key Insight

**Every question now teaches you ISO 55000 while improving your register.**

Example:
```
Question: "Which critical assets lack risk assessments?"

Answer: Shows 23 assets needing assessment

ISO Learning: Risk assessment is ISO 55000 clause 6.1 requirement

Action: Complete 5 risk assessments per week

Result: Better register + deeper ISO knowledge
```

---

## How the System Works

**Question Priority:**
1. Data Quality (find gaps)
2. ISO Learning (understand standards)
3. Critical Assets (immediate action)
4. Strategic (long-term improvement)
5. Risk (apply frameworks)
6. Lifecycle (optimize timing)
7. Continuous Improvement (learn from data)
8. Advanced (strategic maturity)

**System shows 10 random questions from these categories each time you load the page.**

**Benefit:** Regular exposure to different improvement areas and ISO concepts.

---

## Customization

Want to add PDNSW-specific questions? Edit:
`tools/question_suggester.py` lines 30-210

Example:
```python
"pdnsw_specific": [
    {
        "question": "Your custom question here?",
        "category": "PDNSW",
        "explanation": "ISO 55000: Why this matters"
    }
]
```

---

## Next Steps

1. **Restart the system** - New questions will appear immediately
2. **Start with Data Quality questions** - Fix gaps systematically
3. **Use ISO Learning questions** - Build knowledge while working
4. **Track progress** - Note which gaps you fix each week
5. **Repeat** - Questions guide continuous improvement

---

**Remember:** You're not just querying data - you're building expertise and improving the register with every question you ask.

**Last Updated:** 2026-02-06
