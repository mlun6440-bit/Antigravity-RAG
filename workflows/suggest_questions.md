# Workflow: Suggest Questions for Beginners

## Objective
Generate contextual question suggestions for users unfamiliar with asset management or ISO 55000 standards.

## Prerequisites
- Asset index created (`data/.tmp/asset_index.json`)
- Understanding of available data fields

## Required Inputs
- **Asset Index**: `data/.tmp/asset_index.json`
- **Number of suggestions**: How many questions to generate (default: 10)
- **Difficulty level**: "beginner", "advanced", or "all"

## Tools to Use

### Generate Suggestions
```bash
cd Asset
python tools/question_suggester.py --num 10 --difficulty all
```

### Beginner-Only
```bash
python tools/question_suggester.py --difficulty beginner
```

### Advanced-Only
```bash
python tools/question_suggester.py --difficulty advanced
```

## Question Categories

### Beginner Level
1. **Inventory**: Basic asset counting and categorization
2. **Data Structure**: Understanding available fields
3. **Maintenance**: Simple maintenance queries

### Intermediate Level
4. **Financial**: Asset value and cost analysis
5. **Performance**: Asset utilization and KPIs
6. **Compliance**: ISO 55000 basics

### Advanced Level
7. **Risk**: Complex risk assessment
8. **Lifecycle**: Total cost of ownership
9. **Optimization**: Strategic improvement
10. **System Analysis**: Asset interdependencies

## Expected Outputs

```
=== SUGGESTED QUESTIONS ===

[Inventory]
  • How many total assets are in the register?
    → Get an overview of your asset count

  • What types of assets do we manage?
    → Understand the diversity of your asset portfolio

[Maintenance]
  • Which assets need maintenance this month?
    → Identify upcoming maintenance requirements

  • Show me assets with overdue maintenance
    → Find maintenance backlogs

[Compliance]
  • Are our asset records compliant with ISO 55000?
    → Check ISO 55000 compliance status

  • What asset data is missing for full ISO 55000 compliance?
    → Identify compliance gaps

[Financial]
  • What is the total value of all assets?
    → Calculate total asset value

  • Which assets are approaching end of useful life?
    → Plan for asset replacement

[Risk]
  • Which assets have high risk ratings?
    → Identify high-risk assets

  • How does ISO 55000 recommend we assess asset risk?
    → Learn ISO risk assessment framework
```

## Contextual Filtering

The suggester analyzes your asset data to filter relevant questions:

### Data Analysis
- Checks which fields are available
- Identifies data categories (maintenance, financial, risk, etc.)
- Filters out questions for unavailable data

### Smart Suggestions
- If no maintenance fields → Skip maintenance questions
- If no cost/value fields → Skip financial questions
- If no risk fields → Skip risk-specific queries
- Always includes: Inventory, Compliance, General questions

## Use Cases

### For New Users
```bash
python tools/question_suggester.py --difficulty beginner --num 5
```
- Shows simple, easy-to-understand questions
- Helps users learn what they can ask
- Introduces asset management concepts

### For Training
```bash
python tools/question_suggester.py --difficulty all --num 20
```
- Demonstrates range of possible queries
- Shows ISO 55000 concepts
- Educates on best practices

### For Guided Exploration
```bash
python tools/question_suggester.py --difficulty advanced --num 5
```
- Advanced analytical questions
- Strategic optimization queries
- Deep ISO 55000 compliance checks

## Integration with Query Engine

### Interactive Mode
When using `gemini_query_engine.py --interactive`, users can type:
```
suggest
```
This will call the question suggester automatically.

### Workflow
1. User starts interactive session
2. Types "suggest" command
3. System shows 10 contextual questions
4. User picks a question
5. System processes query with Gemini

## Question Template Structure

Each question includes:
- **Question**: The actual query text
- **Category**: Thematic grouping
- **Explanation**: What the question helps you understand

Example:
```json
{
  "question": "Which assets need maintenance this month?",
  "category": "Maintenance",
  "explanation": "Identify upcoming maintenance requirements"
}
```

## Customization

### Add New Questions
Edit `tools/question_suggester.py`:
```python
"your_category": [
    {
        "question": "Your question here?",
        "category": "Your Category",
        "explanation": "What this helps users understand"
    }
]
```

### Adjust Filtering Logic
Modify `filter_relevant_questions()` method to:
- Add new data detection rules
- Change category inclusion logic
- Customize based on business needs

## Edge Cases

### No Asset Index
**Symptom**: "File not found" error
**Solution**:
1. Run fetch workflow
2. Run indexing workflow
3. Ensure `data/.tmp/asset_index.json` exists

### Empty Schema
**Symptom**: Very few suggestions generated
**Solution**:
- Verify asset data was indexed correctly
- Check asset_index.json has field definitions
- Ensure at least some assets were loaded

### Repetitive Questions
**Symptom**: Same questions appear multiple times
**Solution**:
- Questions are randomized on each run
- Run multiple times for variety
- Increase `--num` parameter

## Performance Notes
- Very fast (< 1 second)
- No API calls required
- No network dependency
- Offline-capable

## Best Practices

### For End Users
1. Start with beginner questions
2. Gradually move to advanced
3. Use suggestions as learning tool
4. Try rephrasing suggested questions

### For Administrators
1. Customize questions for your organization
2. Add domain-specific categories
3. Update explanations for clarity
4. Review suggestions periodically

## ISO 55000 Educational Value

Questions are designed to teach ISO 55000 concepts:
- **Asset lifecycle** (acquisition → operation → disposal)
- **Value realization** (how assets create value)
- **Risk management** (identifying and mitigating risks)
- **Performance monitoring** (KPIs and measurement)
- **Strategic alignment** (linking to organizational goals)
- **Continuous improvement** (optimization opportunities)

## Next Steps

### Enhancement Ideas
1. **User preferences**: Remember favorite question types
2. **Query history**: Suggest follow-up questions
3. **Adaptive learning**: Adjust based on what users actually ask
4. **Multi-language**: Translate questions
5. **Context-aware**: More sophisticated data analysis

### Integration
- Display in web UI
- Include in email reports
- Add to chatbot interface
- Generate weekly question prompts
