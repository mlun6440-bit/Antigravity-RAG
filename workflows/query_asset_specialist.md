# Workflow: Query Asset Register Specialist

## Objective
Answer natural language questions about asset registers using Google Gemini with RAG (Retrieval-Augmented Generation) and ISO 55000 expertise.

## Prerequisites
- Asset data fetched and indexed
- ISO knowledge base created
- Gemini API key configured
- Internet connection for API calls

## Required Inputs
- **User Question**: Natural language query about assets
- **Asset Index**: `data/.tmp/asset_index.json`
- **ISO Knowledge Base**: `data/.tmp/iso_knowledge_base.json`
- **GEMINI_API_KEY**: Configured in `.env`

## Tools to Use

### Single Query Mode
```bash
cd Asset
python tools/gemini_query_engine.py --question "Your question here"
```

### Interactive Mode
```bash
cd Asset
python tools/gemini_query_engine.py --interactive
```

## Query Processing Flow

1. **Question Analysis**: Parse user question
2. **Context Retrieval (RAG)**:
   - Search relevant assets (keyword matching)
   - Find relevant ISO 55000 sections
   - Compile asset statistics
3. **Prompt Construction**:
   - System prompt (ISO 55000 specialist role)
   - Retrieved context (assets + ISO standards)
   - User question
4. **Gemini API Call**: Send to Google Gemini 1.5 Flash
5. **Response Processing**: Extract and format answer
6. **Output**: Display answer with sources

## Expected Outputs

### Successful Query
```
=== ANSWER ===
[Comprehensive answer based on asset data and ISO standards]

- Citations of specific assets
- References to ISO clauses
- Recommendations aligned with ISO 55000
- Actionable insights

=== METADATA ===
Model: gemini-1.5-flash-latest
Context Size: 15,432 characters
Status: success
```

### Failed Query
```
✗ Error: [Error message]
Status: error
```

## Example Questions

### Beginner Questions
- "How many assets do we have?"
- "What types of assets are in the register?"
- "Show me recently added assets"

### Maintenance Questions
- "Which assets need maintenance this month?"
- "What is the maintenance history of asset X?"
- "Show me overdue maintenance tasks"

### Compliance Questions
- "Are we compliant with ISO 55000?"
- "What asset data is missing for ISO 55001 compliance?"
- "How should we track asset lifecycle per ISO 55000?"

### Financial Questions
- "What is our total asset value?"
- "Which assets are most expensive?"
- "Show me depreciation by category"

### Risk Questions
- "What are our highest-risk assets?"
- "How does ISO 55000 define asset risk?"
- "Which critical assets lack risk assessments?"

## Edge Cases

### API Key Missing
**Symptom**: "Gemini API key not found"
**Solution**:
1. Get API key from https://makersuite.google.com/app/apikey
2. Add to `.env`: `GEMINI_API_KEY=your_key_here`
3. Restart tool

### Data Files Missing
**Symptom**: "File not found" errors
**Solution**:
1. Run fetch workflow first
2. Run indexing workflow
3. Run ISO parsing workflow
4. Ensure all `.tmp/` files exist

### No Relevant Context Found
**Symptom**: Answer says "no relevant data"
**Solution**:
- Rephrase question with different keywords
- Check if data actually exists in asset register
- Verify asset index was created correctly

### API Rate Limiting
**Symptom**: "429 Too Many Requests" or "Quota exceeded"
**Solution**:
- Wait and retry (Gemini has rate limits)
- Check quota usage in Google Cloud Console
- Consider upgrading API plan for production use

### Poor Answer Quality
**Symptom**: Generic or incorrect answers
**Solution**:
- Ensure ISO knowledge base was created successfully
- Check asset index has complete data
- Try more specific questions
- Verify context is being retrieved (check context_size in output)

## Performance Notes

### Response Time
- Simple queries: 2-5 seconds
- Complex queries: 5-10 seconds
- Factors: Context size, model latency, network speed

### Token Usage
- Gemini 1.5 Flash: 1M token context window
- Typical query: 5,000-20,000 tokens
- Cost: Very low (~$0.01 per 1000 queries)

### Context Quality
- More context = better answers
- Trade-off: Size vs relevance
- Current: Top 20 relevant assets + 5 ISO chunks

## ISO 55000 Specialist Behavior

The AI is prompted to act as an ISO 55000 expert, which means:

1. **Value Focus**: Answers emphasize how assets provide value
2. **Lifecycle Thinking**: Considers acquisition, operation, maintenance, disposal
3. **Risk-Based**: Applies risk-based decision making
4. **Alignment**: Links to organizational objectives
5. **Performance**: Suggests KPIs and measurement
6. **Compliance**: Checks against ISO 55001 requirements
7. **Best Practices**: Recommends ISO 55002 guidelines

## Troubleshooting

### Error: "Model not found"
- Check model name in `.env`
- Default: `gemini-1.5-flash-latest`
- Alternative: `gemini-1.5-pro-latest` (more capable, slower)

### Error: "Context too large"
- Reduce `max_assets` in code (currently 20)
- Reduce `max_chunks` for ISO content (currently 5)

### Answers lack ISO expertise
- Verify ISO PDFs were parsed successfully
- Check `iso_knowledge_base.json` has content
- Ensure ISO chunks are being retrieved

## Next Steps

### For Better Results
1. **Improve search**: Implement embeddings for semantic search
2. **Add caching**: Cache frequent queries
3. **Track history**: Remember conversation context
4. **Fine-tune prompts**: Adjust system prompt based on needs

### For Production
1. **Add logging**: Track all queries and responses
2. **Error handling**: More graceful failure modes
3. **User feedback**: Thumbs up/down on answers
4. **Analytics**: Track popular questions
