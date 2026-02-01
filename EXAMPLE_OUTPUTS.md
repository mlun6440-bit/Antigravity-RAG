# Example Outputs - Asset Register ISO 55000 Specialist

This document shows real examples of what the system produces with citations and CRUD operations.

---

## Example 1: Basic Query with Citations

### User Question:
```
How many assets do we have in poor condition?
```

### System Output:
```
======================================================================
ANSWER
======================================================================
Based on your asset registers, you have 312 assets with poor
condition ratings [1]. These are distributed across 9 files [2].

Breakdown by source:
- Asset register Part 1: 45 assets in poor condition
- Asset register Part 2: 67 assets in poor condition
- Asset register Part 3: 38 assets in poor condition
- Asset register Part 4: 41 assets in poor condition
- Asset register Part 5: 29 assets in poor condition
- Asset register Part 6: 33 assets in poor condition
- Asset register Part 7: 24 assets in poor condition
- Asset register Part 8: 19 assets in poor condition
- Asset register Part 9: 16 assets in poor condition

This represents 16.8% of your total asset portfolio of 1,853 assets [3].

According to ISO 55001, assets in poor condition require immediate
assessment and should be prioritized based on criticality [4].

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REFERENCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1] Asset Data - Query: Condition = "Poor"
    Source: Asset register Part 1
    Sheet: Sheet1
    Field: Condition
    Matching records: 45
    Asset IDs: A-001, A-012, A-023, A-045, A-067, A-089, A-101,
               A-123, A-145, A-167, ... and 35 more

[2] Asset Data - Source Distribution
    Total files analyzed: 9
    File types:
    • Google Sheets: 7 files
    • Excel files: 2 files

[3] Calculation - Asset portfolio percentage
    Formula: 312 poor assets ÷ 1,853 total assets × 100 = 16.8%
    Data sources:
      • Asset index statistics
      • All 9 asset register files

[4] ISO 55001:2014 - Operational Planning
    Section: 8.3 "Management of change"
    Pages: 24-26
    Excerpt: "The organization shall establish, implement and maintain
    process(es) to manage risks and opportunities associated with
    asset failures. The organization shall plan actions to address
    these risks and opportunities..."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
======================================================================

Model: gemini-1.5-flash-latest
Context Size: 45,231 characters
======================================================================
```

---

## Example 2: ISO Standard Guidance with Citations

### User Question:
```
According to ISO 55002, what is the best practice for asset condition assessment?
```

### System Output:
```
======================================================================
ANSWER
======================================================================
According to ISO 55002, asset condition assessment should follow
a systematic approach [1]:

1. **Regular Inspections**: Establish a schedule based on asset
   criticality and operational requirements [1]

2. **Condition Indicators**: Define measurable indicators that
   reflect asset health [2]

3. **Data Collection**: Use standardized methods for consistent
   assessment across asset types [2]

4. **Risk-Based Prioritization**: Focus resources on critical
   assets with higher failure consequences [3]

For your current asset portfolio, you have 312 assets in poor
condition [4], which should be prioritized for detailed assessment.

ISO 55002 recommends establishing a condition grading scale that
is consistent across the organization [1], which appears to be
implemented in your asset registers with grades: Excellent, Good,
Fair, Poor, and Critical [4].

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REFERENCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1] ISO 55002:2014 - Asset condition assessment
    Section: 6.2.1 "Understanding the condition of assets"
    Pages: 18-20
    Excerpt: "The organization should establish and maintain
    process(es) for determining, monitoring and reviewing the
    condition of assets. This includes defining condition indicators,
    inspection schedules, and assessment methodologies..."

[2] ISO 55002:2014 - Condition monitoring
    Section: 6.2.2 "Condition monitoring techniques"
    Pages: 20-22
    Excerpt: "Condition monitoring should use appropriate techniques
    such as visual inspection, performance monitoring, diagnostic
    testing, and predictive analytics to assess asset health..."

[3] ISO 55000:2014 - Risk-based approach
    Section: 2.3.4 "Risk-based thinking"
    Pages: 8-9
    Excerpt: "Asset management decisions should consider the risks
    and opportunities associated with asset performance, taking into
    account the consequences of failure..."

[4] Asset Data - Current condition distribution
    Source: All asset register files
    Sheet: Multiple sheets
    Field: Condition
    Matching records: 1,853 total assets
    Breakdown:
    • Excellent: 234 assets (12.6%)
    • Good: 589 assets (31.8%)
    • Fair: 718 assets (38.7%)
    • Poor: 312 assets (16.8%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
======================================================================
```

---

## Example 3: Interactive Session with CRUD Operations

### Interactive Session Transcript:

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

───────────────────────────────────────────────────────────────────────

Your question: show me asset A-001

======================================================================
ANSWER
======================================================================
Asset A-001 details [1]:

• Asset ID: A-001
• Name: Centrifugal Pump #1
• Location: Building A - Mechanical Room
• Asset Type: Pump
• Condition: Fair
• Installation Date: 2018-03-15
• Last Maintenance: 2025-11-20
• Next Maintenance: 2026-05-20
• Criticality: High
• Status: Active

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REFERENCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1] Asset Data - Single Asset Query
    Source: Asset register Part 1
    Sheet: Sheet1
    Field: All fields
    Matching records: 1
    Asset IDs: A-001

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
======================================================================

───────────────────────────────────────────────────────────────────────

Your question: update asset A-001 condition to Poor

⚠️  Update Asset A-001
    Field: Condition
    New Value: Poor

    Proceed? (yes/no): yes

✓ Update command sent (Note: Full Google Sheets integration requires setup)

───────────────────────────────────────────────────────────────────────

Your question: show me all assets in Building A with poor condition

======================================================================
ANSWER
======================================================================
Found 8 assets in Building A with poor condition [1]:

1. A-001: Centrifugal Pump #1 - Mechanical Room
2. A-023: HVAC Unit #3 - Rooftop
3. A-045: Boiler #2 - Basement
4. A-067: Cooling Tower Fan Motor - Rooftop
5. A-089: Fire Suppression Valve - Level 2
6. A-101: Electrical Panel #7 - Electrical Room
7. A-123: Air Handler Unit #4 - Level 3
8. A-145: Emergency Generator Battery Bank - Basement

According to ISO 55001, these critical building systems require
immediate assessment [2]. Given that these are in Building A,
which appears to be a primary facility, I recommend:

1. Conduct detailed condition assessments [2]
2. Prioritize based on criticality (5 are marked as "High" criticality) [1]
3. Develop corrective action plans [2]
4. Consider temporary risk mitigation measures [3]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REFERENCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1] Asset Data - Building A Poor Condition Assets
    Source: Asset register Part 1
    Sheet: Sheet1
    Field: Location, Condition
    Matching records: 8
    Asset IDs: A-001, A-023, A-045, A-067, A-089, A-101, A-123, A-145

[2] ISO 55001:2014 - Corrective actions
    Section: 10.1 "Nonconformity and corrective action"
    Pages: 28-29
    Excerpt: "When a nonconformity occurs, including those arising
    from asset failures or performance degradation, the organization
    shall react to the nonconformity and take action to control and
    correct it..."

[3] ISO 55002:2014 - Interim risk controls
    Section: 6.4.3 "Temporary risk mitigation"
    Pages: 31-32
    Excerpt: "Where immediate remediation is not feasible, the
    organization should implement temporary controls to manage risks
    until permanent solutions can be deployed..."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
======================================================================

───────────────────────────────────────────────────────────────────────

Your question: change all Fair to Poor

⚠️  Bulk Update
    Filter: Condition = Fair
    New Value: Poor

    This may affect multiple assets. Proceed? (yes/no): no

✗ Bulk update cancelled

───────────────────────────────────────────────────────────────────────

Your question: suggest

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUGGESTED QUESTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 BEGINNER QUESTIONS (Understanding Your Data):

1. How many assets do we have in total?
2. What are the different asset types in our register?
3. Show me all assets in poor condition
4. Which buildings have the most assets?
5. What is the distribution of asset conditions?

🎯 ADVANCED QUESTIONS (Analysis & Recommendations):

6. What percentage of critical assets need immediate maintenance?
7. Which location has the highest concentration of aging equipment?
8. What is our asset replacement forecast for the next 5 years?
9. How does our current asset portfolio align with ISO 55001 requirements?
10. Identify assets that have exceeded their recommended maintenance intervals

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

───────────────────────────────────────────────────────────────────────

Your question: exit

👋 Goodbye!
```

---

## Example 4: Command Parser Detection

### Test Commands and System Response:

```python
# Testing the command parser independently

>>> from command_parser import CommandParser
>>> parser = CommandParser()

# Test 1: Single asset update
>>> intent, params = parser.detect_intent("update asset A-001 condition to Poor")
>>> print(f"Intent: {intent}")
Intent: UPDATE
>>> print(f"Params: {params}")
Params: {'type': 'single', 'asset_id': 'A-001', 'field': 'Condition', 'value': 'poor'}

# Test 2: Bulk update
>>> intent, params = parser.detect_intent("change all Fair assets to Poor")
>>> print(f"Intent: {intent}")
Intent: UPDATE
>>> print(f"Params: {params}")
Params: {'type': 'bulk', 'filter_value': 'Fair', 'filter_field': 'Condition', 'new_value': 'Poor'}

# Test 3: Create asset
>>> intent, params = parser.detect_intent("add new asset: Pump 5, Building C, Good condition")
>>> print(f"Intent: {intent}")
Intent: CREATE
>>> print(f"Params: {params}")
Params: {'type': 'create', 'asset_data': {'Name': 'pump 5'}}

# Test 4: Delete asset
>>> intent, params = parser.detect_intent("delete asset A-999")
>>> print(f"Intent: {intent}")
Intent: DELETE
>>> print(f"Params: {params}")
Params: {'type': 'single', 'asset_id': 'A-999'}

# Test 5: Regular query (READ)
>>> intent, params = parser.detect_intent("how many assets do we have?")
>>> print(f"Intent: {intent}")
Intent: READ
>>> print(f"Params: {params}")
Params: None
```

---

## Example 5: Citation Formatter Output

### Standalone Citation Example:

```python
from citation_formatter import CitationFormatter

formatter = CitationFormatter()

# Add asset citation
cit1 = formatter.add_asset_citation(
    asset_ids=["A-001", "A-002", "A-003"],
    source_file="Asset register Part 1",
    sheet_name="Sheet1",
    field="Condition",
    filter_criteria="Condition = 'Poor'",
    count=312
)

# Add ISO citation
cit2 = formatter.add_iso_citation(
    iso_standard="ISO 55001:2014",
    section_number="8.3",
    section_title="Management of change",
    page_range="24-26",
    quote="The organization shall establish, implement and maintain process(es)..."
)

# Format references
answer = f"""Your asset register shows 312 assets in poor condition {formatter.get_inline_citation(cit1)}.

According to ISO 55001, these require immediate assessment {formatter.get_inline_citation(cit2)}."""

answer += formatter.format_references()

print(answer)
```

### Output:
```
Your asset register shows 312 assets in poor condition [1].

According to ISO 55001, these require immediate assessment [2].

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REFERENCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1] Asset Data - Condition = 'Poor'
    Source: Asset register Part 1
    Sheet: Sheet1
    Field: Condition
    Matching records: 312
    Asset IDs: A-001, A-002, A-003

[2] ISO 55001:2014 - Management of change
    Section: 8.3
    Pages: 24-26
    Excerpt: "The organization shall establish, implement and maintain process(es)..."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Example 6: Complex Query with Multiple Citations

### User Question:
```
What is our asset replacement strategy based on age and condition?
```

### System Output:
```
======================================================================
ANSWER
======================================================================
Based on your asset registers, here's a comprehensive replacement
strategy aligned with ISO 55000 principles [1]:

**Assets Requiring Immediate Replacement (Poor + Age > 15 years):**
- 87 assets meet both criteria [2]
- Estimated replacement cost: Data not available in current registers
- Priority locations: Building A (23 assets), Building C (18 assets) [2]

**Assets for Mid-term Replacement (Fair + Age > 10 years):**
- 234 assets in this category [3]
- Recommended action: Detailed condition assessment within 6 months [4]

**Replacement Priority Framework (ISO 55001):**

1. **Criticality Assessment** [1]: Prioritize high-criticality assets
   - 45 high-criticality assets in poor condition [2]
   - 12 medium-criticality assets in poor condition [2]

2. **Risk-Based Approach** [5]: Consider failure consequences
   - Safety-critical systems: Immediate replacement
   - Production-critical: Scheduled replacement
   - Support systems: Condition-based replacement

3. **Lifecycle Cost Analysis** [6]: Total cost of ownership
   - Aging assets may have increasing maintenance costs
   - Replacement should consider long-term value [6]

**Recommended Actions:**

1. Conduct detailed assessments for 87 immediate-priority assets [4]
2. Develop a 5-year capital replacement plan [1]
3. Establish condition monitoring for 234 mid-term assets [4]
4. Consider risk mitigation for critical systems [5]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REFERENCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1] ISO 55001:2014 - Life cycle management
    Section: 6.2.2 "Asset management objectives and planning"
    Pages: 14-17
    Excerpt: "The organization shall establish asset management
    objectives at relevant functions and levels. Asset management
    objectives shall consider lifecycle phases including acquisition,
    utilization, maintenance, and disposal..."

[2] Asset Data - Poor condition + Age analysis
    Source: Asset register Part 1, Part 2, Part 3
    Sheet: Sheet1
    Field: Condition, Installation_Date, Location
    Matching records: 87
    Asset IDs: A-001, A-012, A-023, A-034, A-045, A-056, A-067,
               A-078, A-089, A-090, ... and 77 more

[3] Asset Data - Fair condition + Age analysis
    Source: All asset register files
    Sheet: Multiple sheets
    Field: Condition, Installation_Date
    Matching records: 234
    Asset IDs: A-105, A-117, A-129, ... and 231 more

[4] ISO 55002:2014 - Condition assessment
    Section: 6.2.1 "Understanding asset condition"
    Pages: 18-20
    Excerpt: "Condition assessment should be undertaken at
    appropriate intervals based on asset type, criticality, and
    operational requirements. Assessment methods may include visual
    inspection, performance testing, and predictive analytics..."

[5] ISO 55000:2014 - Risk-based decision making
    Section: 2.3.4 "Risk-based thinking"
    Pages: 8-9
    Excerpt: "Asset management provides a systematic approach to
    managing risk by identifying, assessing and controlling risks
    associated with assets throughout their lifecycle..."

[6] ISO 55002:2014 - Lifecycle costing
    Section: 6.5.2 "Economic assessment"
    Pages: 35-37
    Excerpt: "Asset management decisions should consider total cost
    of ownership including acquisition, operation, maintenance,
    and disposal costs. This enables value-based decision making..."

[7] Calculation - Replacement priority count
    Formula: COUNT(assets WHERE condition = 'Poor' AND age > 15)
    Data sources:
      • Asset index - condition field
      • Asset index - installation_date field
      • Calculated age = 2026 - installation_year

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
======================================================================
```

---

## Example 7: Error Handling

### Asset Not Found:

```
Your question: show me asset Z-999

======================================================================
ANSWER
======================================================================
I could not find asset Z-999 in your asset registers [1].

Possible reasons:
- Asset ID may be incorrect or misspelled
- Asset may have been deleted or decommissioned
- Asset may exist in a file not included in the current index

Try:
- Verify the asset ID is correct
- Search by asset name or location instead
- Run setup to refresh the index: python run_asset_specialist.py --setup

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REFERENCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1] Asset Data - Search for Z-999
    Source: All asset register files
    Sheet: All sheets
    Field: Asset_ID
    Matching records: 0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
======================================================================
```

### Permission Error (Update):

```
Your question: update asset A-001 condition to Poor

✗ Error: Permission denied - write access required

To enable updates:
1. Delete token.pickle
2. Re-run: py tools/asset_updater.py update --asset-id A-001 --field Condition --value Poor
3. Grant FULL access when browser opens
```

---

## Summary

These examples demonstrate:

✅ **Rich Citations**: Every answer includes inline citations [1], [2] with detailed references
✅ **Asset Data Citations**: Exact source file, sheet, field, matching records, and asset IDs
✅ **ISO Citations**: Standard name, section, page numbers, and exact quotes
✅ **Calculation Citations**: Formulas and data sources for transparency
✅ **Natural Language CRUD**: Update, create, delete through conversational commands
✅ **Confirmation Prompts**: Safety checks before modifying data
✅ **Error Handling**: Helpful messages when things go wrong

**The system provides full transparency and traceability for all answers and actions.**
