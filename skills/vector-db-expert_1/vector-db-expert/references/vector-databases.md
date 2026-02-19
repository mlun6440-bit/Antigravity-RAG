# Vector Databases Reference

## Table of Contents
1. [Detailed Comparison](#detailed-comparison)
2. [Performance Benchmarks](#performance-benchmarks)
3. [Pricing Summary](#pricing-summary)
4. [Selection Decision Tree](#selection-decision-tree)
5. [Migration Guidance](#migration-guidance)

---

## Detailed Comparison

### pgvector (Supabase)
- **Best for**: Teams already on PostgreSQL, <100M vectors, need SQL JOINs + vector search
- **Architecture**: PostgreSQL extension, single-node
- **Index types**: HNSW, IVFFlat. DiskANN via pgvectorscale extension
- **Max dimensions**: 2000 (HNSW), 2000 (IVFFlat)
- **Hybrid search**: Native via tsvector + pgvector in same query
- **Multi-tenancy**: PostgreSQL RLS (Row Level Security)
- **Key advantage**: Zero additional infrastructure — vectors live alongside relational data
- **Key limitation**: HNSW must fit in RAM. Beyond ~100M vectors, purpose-built DBs are better
- **License**: PostgreSQL license (very permissive)
- **Supabase integration**: Built-in on all plans, direct SQL access, Edge Functions, client libraries

### Pinecone
- **Best for**: Zero-ops teams wanting fastest time-to-market
- **Architecture**: Fully managed serverless, auto-scaling
- **Performance**: 7ms p99 latency, 1,146 QPS on 1M vectors
- **Hybrid search**: Sparse-dense vectors in single index
- **Multi-tenancy**: Namespaces within indexes
- **Key advantage**: No infrastructure management, automatic scaling
- **Key limitation**: Vendor lock-in (fully proprietary), higher cost at scale
- **Pricing**: Free tier (2GB), Standard $50/mo minimum, usage-based beyond that

### Qdrant
- **Best for**: Complex metadata filtering, budget-conscious teams, <50M vectors
- **Architecture**: Rust-based, single-node or distributed
- **Performance**: 1,242 QPS at 6.4ms p99 on 1M vectors
- **Hybrid search**: First-class sparse vector support (SPLADE, BM25)
- **Multi-tenancy**: Payload-based filtering with indexed fields
- **Key advantage**: Asymmetric quantization (24× compression), free 1GB cloud tier
- **Key limitation**: Performance degrades beyond 50M vectors at high QPS
- **Pricing**: Free forever 1GB cloud, then usage-based. Self-hosted: Apache 2.0
- **Unique**: Supports named vectors (multiple embeddings per record)

### Weaviate
- **Best for**: Native hybrid search, SaaS multi-tenancy
- **Architecture**: Go-based, distributed
- **Hybrid search**: Strongest native BM25 + vector with configurable fusion
- **Multi-tenancy**: Hot/warm/cold tenant tiers
- **Key advantage**: Built-in vectorizer modules (OpenAI, Cohere, etc.) — auto-embeds on insert
- **Key limitation**: Higher learning curve, complex configuration
- **Pricing**: Sandbox free, Flex $45/mo starting, Enterprise custom
- **Unique**: GraphQL-like query API, cross-reference between objects

### Milvus / Zilliz Cloud
- **Best for**: Billion-scale deployments, GPU-accelerated search
- **Architecture**: Distributed, cloud-native, tiered storage (memory → SSD → object storage)
- **Performance**: 9,704 QPS at 2.5ms p99 on 1M vectors (Zilliz Cloud benchmark leader)
- **Hybrid search**: BM25 + dense vectors via sparse indexes
- **Multi-tenancy**: Partition keys, database-level isolation
- **Key advantage**: Only credible option for 1B+ vectors. NVIDIA CAGRA GPU acceleration
- **Key limitation**: Complex to self-host (etcd, MinIO, Pulsar dependencies)
- **Pricing**: Zilliz Cloud free tier (2 collections), then CU-based. Milvus self-hosted: Apache 2.0
- **Unique**: Dynamic schema, streaming insert without recall degradation (FreshDiskANN)

### Chroma
- **Best for**: Prototyping, local development, experimentation
- **Architecture**: Embedded single-node, Rust rewrite in 2025 (4× faster)
- **Hybrid search**: BM25/SPLADE support added in 2025
- **Key advantage**: 4-line setup, pip install, Apache 2.0
- **Key limitation**: Single-node only, no horizontal scaling, <10M vectors practical limit
- **Pricing**: Free (open-source). Chroma Cloud in limited preview

---

## Performance Benchmarks

From VDBBench and independent testing on 1M vectors (1536 dims, HNSW):

| Database | QPS | p99 Latency | Recall@10 |
|----------|-----|-------------|-----------|
| Zilliz Cloud | 9,704 | 2.5ms | 99.5% |
| Qdrant | 1,242 | 6.4ms | 99.2% |
| Pinecone | 1,146 | 7ms | 99.0% |
| pgvector (tuned) | 800–1,200 | 8–15ms | 98.5% |
| Weaviate | 600–900 | 12–20ms | 98.8% |
| Chroma | 200–400 | 20–50ms | 99.0% |

Note: Benchmarks vary significantly with hardware, index params, and query patterns. Always test with YOUR workload.

### pgvectorscale (DiskANN) on 50M vectors
- 471 QPS at 99% recall
- Vectors stored on SSD, compressed index in RAM
- Enables billion-scale on single node with 64GB RAM

---

## Pricing Summary

### Managed Services (approximate, 1M vectors @ 1536 dims)
| Provider | Monthly Cost | Notes |
|----------|-------------|-------|
| Supabase Pro (pgvector) | $25 | Includes database, auth, storage |
| Pinecone Standard | $50+ | Usage-based after minimum |
| Qdrant Cloud | $30–$65 | Based on RAM/storage |
| Weaviate Flex | $45+ | Based on object count |
| Zilliz Cloud | $65+ | CU-based pricing |

### Self-Hosted (infrastructure cost only)
| Solution | Estimated Monthly | Notes |
|---------|------------------|-------|
| pgvector on AWS r6g.xlarge | ~$150 | 32GB RAM, NVMe SSD |
| Qdrant on similar | ~$150 | Single node |
| Milvus cluster (3 nodes) | ~$500 | etcd + MinIO + Pulsar |

Self-hosted pgvector costs ~75% less than Pinecone at comparable scale.

---

## Selection Decision Tree

```
Start
├── Need SQL JOINs with vector data?
│   └── YES → pgvector (Supabase)
├── Already on PostgreSQL?
│   └── YES → pgvector (Supabase)
├── Zero ops / fastest setup?
│   └── YES → Pinecone (managed) or Chroma (local prototype)
├── Complex metadata filtering primary need?
│   └── YES → Qdrant
├── Native hybrid search primary need?
│   └── YES → Weaviate
├── >100M vectors?
│   └── YES → Milvus/Zilliz
├── Budget constrained?
│   └── YES → pgvector (Supabase) or Qdrant free tier
└── Default → pgvector (Supabase) for <10M, Qdrant for 10M–100M
```

---

## Migration Guidance

### Migrating Between Vector Databases
1. **Export**: Dump vectors + metadata as JSON/Parquet
2. **Re-index**: Different databases use different index structures — no index portability
3. **Verify**: Compare recall on test queries between old and new systems
4. **Dual-write**: Run both systems in parallel before cutover

### Changing Embedding Models
- Changing models requires **re-embedding all documents** — embeddings from different models are incompatible
- Store `embedding_model_version` with each record
- Use blue-green deployment: build new index alongside old, switch when ready
- Budget for re-embedding cost: 1M chunks × $0.02/1M tokens ≈ a few cents to a few dollars
