# RAG Patterns Reference

## Table of Contents
1. [Pipeline Architecture](#pipeline-architecture)
2. [Advanced Retrieval Techniques](#advanced-retrieval-techniques)
3. [Context Window Management](#context-window-management)
4. [GraphRAG vs Traditional RAG](#graphrag-vs-traditional-rag)
5. [Evaluation Framework](#evaluation-framework)
6. [Common Failure Modes](#common-failure-modes)

---

## Pipeline Architecture

### Standard RAG Pipeline
```
INGESTION:
Document Loading → Chunking → Metadata Enrichment → Embedding → Vector Storage
                                                              ↘ BM25 Index

QUERY:
User Query → Query Embedding → Hybrid Retrieval → Re-Ranking → Context Assembly → LLM → Response
                             ↗ BM25 Search
```

### Latency Budget
| Stage | Target | Notes |
|-------|--------|-------|
| Query embedding | 10–50ms | API call to embedding model |
| Vector search | 5–15ms | HNSW with proper tuning |
| BM25 search | 5–10ms | GIN index on tsvector |
| RRF fusion | <1ms | Simple rank computation |
| Re-ranking | 100–200ms | Cross-encoder on 50–100 candidates |
| LLM generation | 500–3000ms | Streaming, first token in 200–500ms |
| **Total** | **~700–3300ms** | Acceptable for most applications |

---

## Advanced Retrieval Techniques

### HyDE (Hypothetical Document Embeddings)
Bridges the semantic gap between short queries and long documents.

```python
def hyde_retrieve(query: str, vectorstore, llm) -> list:
    """Generate hypothetical answer, embed it, search with that embedding."""
    # Step 1: LLM generates a hypothetical answer
    hypothetical = llm.generate(
        f"Write a short paragraph that would answer this question: {query}"
    )
    # Step 2: Embed the hypothetical answer (closer to document space)
    hyde_embedding = embed_model.encode(hypothetical)
    # Step 3: Search with hypothetical embedding
    return vectorstore.similarity_search_by_vector(hyde_embedding, k=10)
```

**HyPE variant** (2025): Generate hypothetical documents at INDEX time, embed those alongside original chunks. Zero runtime overhead, up to 42% context precision improvement.

### RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval)
Builds hierarchical summary tree:
- Leaf nodes: original document chunks
- Parent nodes: LLM summaries of clustered children
- Root: summary of entire corpus
- Query searches ALL levels simultaneously

Best for: complex reasoning requiring both high-level overview and specific details.

### Adaptive RAG
Routes queries by complexity:
```python
def adaptive_rag(query: str) -> str:
    complexity = classify_query(query)  # Lightweight classifier
    
    if complexity == "simple":
        return llm.generate(query)  # No retrieval needed
    elif complexity == "moderate":
        docs = single_step_retrieve(query)
        return llm.generate(query, context=docs)
    else:  # complex
        docs = iterative_retrieve(query, max_steps=3)
        return llm.generate(query, context=docs)
```

### Agentic RAG
The LLM decides whether and how to retrieve:
1. Query analysis: Does this need retrieval? What sources?
2. Tool selection: Which vector store, database, or API to query?
3. Iterative refinement: Are retrieved results sufficient? Reformulate and re-search?
4. Synthesis: Combine information from multiple retrieval steps

Best for: multi-source queries where the retrieval strategy isn't predetermined.

### Self-RAG (Self-Reflective RAG)
After generation, the LLM evaluates:
- **Is retrieval needed?** (RETRIEVE token)
- **Is the passage relevant?** (ISREL token)
- **Is the response supported?** (ISSUP token)
- **Is the response useful?** (ISUSE token)

Achieves 5.8% hallucination rates in clinical benchmarks through citation-grounded generation.

---

## Context Window Management

### The "Lost in the Middle" Problem
LLMs show U-shaped performance: information at the beginning and end of context is recalled well, middle information shows >30% accuracy degradation.

**Mitigation strategies:**
1. Place most relevant chunks at BEGINNING and END of context
2. Limit to 5–10 chunks (not 20+)
3. Use re-ranking to ensure only the most relevant chunks are included
4. Context compression via extractive methods (2–10× compression, often IMPROVES accuracy)

### RAG vs Long Context Stuffing
Even with 128K–1M token windows, RAG outperforms stuffing:
- Effective performance degrades to 4K–32K tokens for most models
- Retrieval filters noise — the most relevant 1% is better than everything
- Cost: Processing 100K tokens per query is 50–100× more expensive than retrieving 5 chunks

### Context Assembly Template
```python
def assemble_context(query: str, chunks: list, max_tokens: int = 4000) -> str:
    """Assemble context with most relevant chunks at beginning and end."""
    if len(chunks) <= 2:
        context_chunks = chunks
    else:
        # Place best and third-best at beginning, second-best at end
        context_chunks = [chunks[0], chunks[2]] + chunks[3:] + [chunks[1]]
    
    context = "\n\n---\n\n".join([
        f"[Source: {c.metadata.get('source', 'unknown')}]\n{c.content}"
        for c in context_chunks
    ])
    
    # Truncate to token budget
    return truncate_to_tokens(context, max_tokens)
```

---

## GraphRAG vs Traditional RAG

### When GraphRAG Wins
- Multi-hop reasoning: "Which suppliers are connected to sanctioned entities through intermediaries?"
- Entity relationship queries: "What equipment in Building A shares maintenance contractors with Building B?"
- Global summarization: "What are the main themes across all inspection reports?"
- Causal chain queries: "What failures led to the compliance breach?"

### When Traditional RAG Wins (Most Cases)
- Simple factual lookups
- Document-grounded Q&A
- Any query where the answer lives in 1–3 chunks
- Systematic evaluation shows GraphRAG FREQUENTLY UNDERPERFORMS on these

### Implementation Options
- **Microsoft GraphRAG**: Full implementation, builds entity-relationship graphs from documents
- **Cognee**: Python library for GraphRAG with multiple graph backends
- **LlamaIndex**: PropertyGraph + KnowledgeGraphIndex abstractions
- **Neo4j + vector search**: Native graph + vector in one database

### Decision Rule
Use GraphRAG only when:
1. Queries require following relationships across multiple entities
2. The knowledge base has rich interconnected structure
3. Traditional RAG with hybrid search and re-ranking has been tried and found insufficient
4. The added complexity (~3× development time, ongoing graph maintenance) is justified

---

## Evaluation Framework

### Core Metrics (RAGAS Framework)
| Metric | What it measures | Target |
|--------|-----------------|--------|
| Faithfulness | Is the answer grounded in retrieved context? | >0.9 |
| Answer Relevancy | Does the answer address the question? | >0.85 |
| Context Precision | Are the retrieved chunks relevant? | >0.85 |
| Context Recall | Did we retrieve all relevant information? | >0.8 |
| Hallucination Rate | % of claims not supported by context | <5% |

### Evaluation Tools
- **RAGAS**: Automated evaluation framework (pip install ragas)
- **DeepEval**: CI/CD integration with explanatory reasoning
- **Langfuse**: Open-source tracing, token costs, retrieval quality over time

### Critical Warning
RAGAS Faithfulness was found to fail on 83% of production examples in independent testing. ALWAYS supplement automated metrics with periodic human evaluation. Build a golden test set of 50–100 (query, expected_answer, relevant_documents) triples and evaluate weekly.

### Quick Evaluation Script
```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision

results = evaluate(
    dataset=eval_dataset,  # HuggingFace Dataset format
    metrics=[faithfulness, answer_relevancy, context_precision],
    llm=eval_llm,         # Use a different LLM than the RAG generator
    embeddings=eval_embeddings
)
print(results)  # Scores per metric
```

---

## Common Failure Modes

### Retrieval Failures
| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Exact terms not found | Vector-only search | Add BM25 hybrid search |
| Semantically similar but wrong topic | Chunk too large | Reduce chunk size, add metadata filtering |
| Relevant doc exists but not retrieved | Poor chunking | Add contextual retrieval, try different chunk sizes |
| Wrong document version retrieved | No freshness management | Add timestamps, filter by recency |
| Multi-hop answer missed | Single-step retrieval | Implement iterative retrieval or GraphRAG |

### Generation Failures
| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Hallucinated facts | Weak grounding | Add re-ranking, citation requirements |
| Generic/vague answer | Too much irrelevant context | Better re-ranking, fewer chunks, MMR diversity |
| Contradictory answer | Conflicting chunks | Add source quality scoring, recency weighting |
| Incomplete answer | Answer spans multiple chunks | Parent-child retrieval, larger chunks |
| Ignores retrieved context | Lost in the middle | Reorder chunks (best at beginning/end) |
