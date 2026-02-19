# Indexing and Search Reference

## Table of Contents
1. [HNSW Deep Dive](#hnsw-deep-dive)
2. [IVFFlat Configuration](#ivfflat-configuration)
3. [Similarity Metrics](#similarity-metrics)
4. [Hybrid Search (BM25 + Vector)](#hybrid-search)
5. [Re-Ranking](#re-ranking)
6. [Maximal Marginal Relevance (MMR)](#mmr)

---

## HNSW Deep Dive

HNSW builds a multi-layered navigable graph. Top layers have sparse long-distance connections for coarse search; bottom layer contains all vectors with dense local connections.

### Parameters

**M** (connections per node): Controls graph connectivity.
- Default: 16. Range: 8–64
- Higher M → better recall, more memory, slower inserts
- Memory impact: M × 2 × 4 bytes per vector per layer

**ef_construction** (build-time beam width): Controls graph quality during build.
- Default: 64–200. Range: 64–512
- Higher → better graph, slower build. No memory impact after build
- Rule: ef_construction ≥ 2 × M

**ef_search** (query-time beam width): Controls search quality.
- Default: 40. Range: 50–500
- Higher → better recall, slower queries. Must be ≥ k (number of results)
- Tune this at query time based on accuracy needs

### Memory Estimation
Per vector: `(dimensions × 4) + (M × 2 × 4)` bytes (float32)

| Vectors | Dims | M | Memory |
|---------|------|---|--------|
| 1M | 1536 | 16 | ~6.3 GB |
| 1M | 512 | 16 | ~2.2 GB |
| 10M | 1536 | 16 | ~63 GB |
| 10M | 512 | 16 | ~22 GB |
| 100M | 1536 | 16 | ~630 GB |

### Recommended Configurations

**General production** (pgvector):
```sql
CREATE INDEX CONCURRENTLY idx_embedding ON documents
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

**High-accuracy** (legal, medical, compliance):
```sql
CREATE INDEX CONCURRENTLY idx_embedding ON documents
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 32, ef_construction = 128);
```

**Query-time tuning** (always use SET LOCAL with connection pooling):
```sql
BEGIN;
SET LOCAL hnsw.ef_search = 100;  -- Increase for better recall
SELECT * FROM documents ORDER BY embedding <=> $1 LIMIT 10;
COMMIT;
```

### Build Performance Tips
- Load data FIRST, create index AFTER — bulk loading into an indexed table is 10× slower
- Use `CREATE INDEX CONCURRENTLY` for non-blocking builds
- Set `maintenance_work_mem = '2GB'` or higher
- Set `max_parallel_maintenance_workers = 4` (pgvector 0.6+)
- VACUUM ANALYZE before building

---

## IVFFlat Configuration

IVFFlat partitions vectors into clusters via K-means, then searches only nearby clusters.

### Parameter Selection
- **lists** (number of clusters):
  - <1M rows: `lists = rows / 1000`
  - ≥1M rows: `lists = sqrt(rows)`
- **probes** (clusters to search at query time):
  - Start at `sqrt(lists)`
  - More probes → better recall, slower query

### When to Use IVFFlat vs HNSW
| Factor | IVFFlat | HNSW |
|--------|---------|------|
| Build time | Faster | Slower |
| Query speed | Slower | Faster |
| Recall | Lower | Higher |
| Dynamic inserts | Poor (needs retrain) | Good |
| Memory | Lower | Higher |
| Empty table? | NO — needs data first | YES — works on empty |

**Use IVFFlat** for: static/rarely-changing data, memory-constrained environments, faster build times.
**Use HNSW** for: everything else (it's the default recommendation).

### IVFFlat Example
```sql
-- MUST have data loaded first, then VACUUM ANALYZE
VACUUM ANALYZE documents;

CREATE INDEX CONCURRENTLY idx_ivf ON documents
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 1000);  -- For ~1M rows

-- Query with probes
BEGIN;
SET LOCAL ivfflat.probes = 32;  -- sqrt(1000) ≈ 32
SELECT * FROM documents ORDER BY embedding <=> $1 LIMIT 10;
COMMIT;
```

---

## Similarity Metrics

### For Normalized Vectors (All Major APIs Return These)
**Cosine similarity, dot product, and L2 distance produce IDENTICAL rankings.** Use inner product for speed:

| pgvector Operator | Metric | Speed | Use When |
|-------------------|--------|-------|----------|
| `<#>` | Negative inner product | Fastest | Normalized vectors (default choice) |
| `<=>` | Cosine distance | Fast | Normalized vectors (equivalent to above) |
| `<->` | L2 (Euclidean) distance | Fast | Unnormalized vectors |

### pgvector Index Operator Classes
```sql
-- Match operator class to your preferred distance metric:
vector_cosine_ops    -- For <=> (cosine distance)
vector_ip_ops        -- For <#> (inner product) — FASTEST for normalized
vector_l2_ops        -- For <-> (L2 distance)
```

### Similarity Score Conversion
```sql
-- Cosine similarity (0 to 1, higher = more similar)
SELECT 1 - (embedding <=> query_embedding) AS cosine_similarity

-- Inner product similarity (for normalized vectors, same as cosine)
SELECT -(embedding <#> query_embedding) AS ip_similarity

-- Common threshold: 0.78+ for "relevant" results
WHERE 1 - (embedding <=> query_embedding) > 0.78
```

---

## Hybrid Search

Combine BM25 keyword search with vector search using Reciprocal Rank Fusion (RRF).

### Why Hybrid is Non-Negotiable
- BM25 catches: exact keywords, identifiers, part numbers, proper nouns, acronyms
- Vector catches: synonyms, paraphrasing, semantic intent, conceptual similarity
- Combined: consistently 10–30% better than either alone

### RRF Formula
`RRF_score(d) = Σ 1/(k + rank(d))` where k=60 (constant, no tuning needed)

### Supabase Hybrid Search Function
```sql
CREATE OR REPLACE FUNCTION hybrid_search(
  query_text TEXT,
  query_embedding VECTOR(1536),
  match_count INT DEFAULT 10,
  full_text_weight FLOAT DEFAULT 1.0,
  semantic_weight FLOAT DEFAULT 1.0,
  rrf_k INT DEFAULT 60
) RETURNS TABLE (id BIGINT, content TEXT, metadata JSONB, score FLOAT)
LANGUAGE SQL AS $$
WITH full_text AS (
  SELECT id, ROW_NUMBER() OVER(
    ORDER BY ts_rank(fts, websearch_to_tsquery(query_text)) DESC
  ) AS rank
  FROM documents
  WHERE fts @@ websearch_to_tsquery(query_text)
  ORDER BY ts_rank(fts, websearch_to_tsquery(query_text)) DESC
  LIMIT match_count * 2
),
semantic AS (
  SELECT id, ROW_NUMBER() OVER(
    ORDER BY embedding <=> query_embedding
  ) AS rank
  FROM documents
  ORDER BY embedding <=> query_embedding
  LIMIT match_count * 2
)
SELECT
  COALESCE(f.id, s.id) AS id,
  d.content,
  d.metadata,
  COALESCE(full_text_weight / (rrf_k + f.rank), 0.0) +
  COALESCE(semantic_weight / (rrf_k + s.rank), 0.0) AS score
FROM full_text f
FULL OUTER JOIN semantic s ON f.id = s.id
JOIN documents d ON d.id = COALESCE(f.id, s.id)
ORDER BY score DESC
LIMIT match_count;
$$;
```

### Setting Up Full-Text Search Column
```sql
-- Add tsvector column
ALTER TABLE documents ADD COLUMN fts tsvector
  GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

-- Index it
CREATE INDEX idx_fts ON documents USING gin(fts);
```

---

## Re-Ranking

Cross-encoder re-ranking is the highest-ROI addition to any retrieval pipeline. Joint encoding of (query, document) pairs with full cross-attention produces far more accurate relevance scores than bi-encoder similarity.

### Two-Stage Pattern
1. **Retrieve**: Top 50–100 candidates via bi-encoder/vector index (~5ms)
2. **Re-rank**: Cross-encoder scores each (query, candidate) pair (~100–200ms)
3. **Return**: Top 5–10 re-ranked results

Impact: ~120ms additional latency, ~33% accuracy improvement.

### Re-Ranker Options
| Model | Context | Price | Notes |
|-------|---------|-------|-------|
| Cohere Rerank v3.5 | 4K tokens | $2.00/1K searches | 100+ languages, semi-structured |
| Jina Reranker v3 | 131K tokens | $0.02/1M tokens | Longest context, code-aware |
| cross-encoder/ms-marco-MiniLM-L-6-v2 | 512 tokens | Free (self-hosted) | Good baseline |
| Voyage Reranker | 32K tokens | $0.05/1M tokens | Pairs well with Voyage embeddings |

### Cohere Re-Rank Example
```python
import cohere
co = cohere.ClientV2()

results = co.rerank(
    query="fire safety compliance AS 1851",
    documents=[doc.content for doc in retrieved_docs],
    model="rerank-v3.5",
    top_n=5,
    return_documents=True
)
reranked = [(r.document.text, r.relevance_score) for r in results.results]
```

### Open-Source Re-Rank
```python
from sentence_transformers import CrossEncoder

model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
pairs = [(query, doc.content) for doc in retrieved_docs]
scores = model.predict(pairs)

# Sort by score descending
reranked = sorted(zip(retrieved_docs, scores), key=lambda x: x[1], reverse=True)
```

---

## MMR

Maximal Marginal Relevance diversifies results, preventing redundant chunks from consuming context window space.

### Formula
`MMR = λ × sim(query, doc) - (1-λ) × max(sim(doc, selected_docs))`

- λ=1.0: Pure relevance (no diversity)
- λ=0.5: Equal balance
- λ=0.7: 70% relevance, 30% diversity (recommended default)

### LangChain MMR
```python
retriever = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={
        "k": 5,              # Final results count
        "lambda_mult": 0.7,  # Relevance vs diversity
        "fetch_k": 20        # Initial candidates
    }
)
```

### When to Use MMR
- When retrieved chunks have high overlap (common with overlapping chunking)
- When context window is limited and every chunk must add new information
- When document collection has many near-duplicates
