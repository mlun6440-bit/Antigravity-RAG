---
name: vector-db-expert
description: Expert guidance on vector embeddings, vector databases, and retrieval-augmented generation (RAG) systems. Use when users ask about choosing embedding models (OpenAI, Voyage AI, Cohere, open-source), vector database selection (pgvector/Supabase, Pinecone, Qdrant, Weaviate, Milvus/Zilliz, Chroma), chunking strategies for documents, HNSW or IVFFlat index tuning, hybrid search (BM25 + vector), re-ranking with cross-encoders, Matryoshka/MRL dimension reduction, embedding quantization, RAG pipeline architecture, contextual retrieval, GraphRAG vs traditional RAG, pgvector performance tuning, Supabase vector search functions, similarity metrics (cosine, dot product, L2), metadata filtering, multi-tenancy with RLS, production scaling, cost optimization, or any question about storing, indexing, and searching vector embeddings. Also use when building or debugging RAG applications, designing semantic search systems, or migrating between vector databases.
---

# Vector DB Expert

Expert guidance for vector embeddings, vector databases, and RAG systems. Current as of early 2025.

## Quick Decision Frameworks

### Embedding Model Selection

| Priority | Model | Cost/1M tokens |
|----------|-------|----------------|
| Budget RAG | voyage-3.5-lite or text-embedding-3-small | $0.02 |
| Quality RAG | voyage-3.5 or text-embedding-3-large | $0.06–$0.13 |
| Multilingual | Cohere Embed v4 or BGE-M3 | $0.12 / free |
| Code retrieval | voyage-code-3 | $0.18 |
| On-premise / privacy | BGE-M3 or Qwen3-Embedding | Free (self-hosted) |
| Multimodal (text+images) | Cohere Embed v4 | $0.12 text / $0.47 images |

**Full details**: See [references/embedding-models.md](references/embedding-models.md)

### Vector Database Selection

| Scale | Recommended | Why |
|-------|------------|-----|
| Prototyping (<100K) | Chroma or Qdrant free tier | Zero setup, free |
| Production (<10M) | pgvector (Supabase) | SQL-native, hybrid search, JOINs, RLS, $25/mo |
| Growth (10M–100M) | pgvector or Qdrant Cloud | Proven at scale, $100–300/mo |
| Enterprise (100M+) | Milvus self-hosted or Zilliz | Distributed, GPU-accelerated |
| Billion-scale | Milvus/Zilliz Cloud | Only credible option at this scale |

**Full details**: See [references/vector-databases.md](references/vector-databases.md)

### Chunking Strategy

| Content type | Strategy | Chunk size |
|-------------|----------|------------|
| General documents | Recursive character splitting | 512 tokens, 75-token overlap |
| Factoid Q&A | Smaller chunks | 256–512 tokens |
| Analytical/summary | Larger chunks | 512–1024 tokens |
| Code | Function/class boundaries | Varies |
| High-stakes accuracy | Contextual retrieval | 512 tokens + LLM context prefix |

**Full details**: See [references/chunking-strategies.md](references/chunking-strategies.md)

### Index Type

| Scenario | Index | Key params |
|----------|-------|-----------|
| Default production | HNSW | M=16, ef_construction=64 |
| High-accuracy (legal/medical) | HNSW | M=32, ef_construction=128 |
| Static data, fast build | IVFFlat | lists=rows/1000, probes=√lists |
| Billion-scale single node | DiskANN | Via pgvectorscale or Milvus |
| Exact results (<50K vectors) | Flat/brute-force | None |

**Full details**: See [references/indexing-and-search.md](references/indexing-and-search.md)

## Core Workflow

1. **Choose Embedding Model** → Read [references/embedding-models.md](references/embedding-models.md)
2. **Design Chunking Pipeline** → Read [references/chunking-strategies.md](references/chunking-strategies.md)
3. **Select and Configure Database** → Read [references/vector-databases.md](references/vector-databases.md), and for Supabase: [references/pgvector-playbook.md](references/pgvector-playbook.md)
4. **Build Retrieval Pipeline** → Read [references/indexing-and-search.md](references/indexing-and-search.md) for hybrid search + re-ranking
5. **Integrate with RAG** → Read [references/rag-patterns.md](references/rag-patterns.md) for advanced techniques
6. **Production Hardening** → Read [references/production-ops.md](references/production-ops.md) for monitoring, cost, security

## Critical Rules

- Always L2-normalize embeddings after MRL truncation — truncated vectors are not unit-length
- HNSW indexes must fit in shared_buffers — budget RAM as `(dimensions × 4) + (M × 8)` bytes per vector
- Use `SET LOCAL` with transaction pooling — session-level SET is lost between transactions in Supavisor
- `VACUUM ANALYZE` before creating IVFFlat indexes — IVFFlat trains on existing data
- Cosine, dot product, and L2 give identical rankings for normalized vectors — use dot product (`<#>`) for speed
- Never use vector-only search in production — always combine with BM25 keyword search (hybrid)
- Re-ranking top 50–100 candidates with a cross-encoder adds ~120ms but ~33% accuracy gain
- Treat embeddings as sensitive data — partial text reconstruction from embeddings is possible
