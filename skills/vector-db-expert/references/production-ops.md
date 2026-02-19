# Production Operations Reference

## Table of Contents
1. [Monitoring and Observability](#monitoring-and-observability)
2. [Cost Optimization](#cost-optimization)
3. [Data Freshness](#data-freshness)
4. [Security](#security)
5. [Backup and Recovery](#backup-and-recovery)
6. [Scaling Strategies](#scaling-strategies)

---

## Monitoring and Observability

### Key Metrics
| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Query latency p50 | <20ms | >50ms |
| Query latency p99 | <100ms | >500ms |
| Cache hit ratio | >99% | <95% |
| Connection count | <80% of max | >90% of max |
| Index scan ratio | >95% | <80% (sequential scans) |
| Embedding API latency | <100ms | >500ms |
| Re-ranker latency | <200ms | >500ms |

### pgvector-Specific Monitoring
```sql
-- Is the HNSW index being used? (vs sequential scan)
EXPLAIN ANALYZE
SELECT id FROM documents ORDER BY embedding <=> $1 LIMIT 10;
-- Look for "Index Scan using idx_docs_embedding" not "Seq Scan"

-- Cache hit ratio
SELECT sum(heap_blks_hit) / NULLIF(sum(heap_blks_hit + heap_blks_read), 0)
FROM pg_statio_user_tables WHERE relname = 'documents';

-- Index size monitoring
SELECT pg_size_pretty(pg_indexes_size('documents')) AS index_size;

-- Active connections
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';
```

### RAG Pipeline Tracing
Use **Langfuse** (open-source) for end-to-end observability:
- Trace each retrieval + generation step
- Track token costs per query
- Monitor retrieval quality over time
- A/B test pipeline changes

```python
from langfuse import Langfuse
langfuse = Langfuse()

trace = langfuse.trace(name="rag_query", input=query)
retrieval_span = trace.span(name="retrieval")
# ... retrieve documents ...
retrieval_span.end(output={"doc_count": len(docs), "top_score": scores[0]})

generation_span = trace.span(name="generation")
# ... generate answer ...
generation_span.end(output={"tokens": token_count, "model": model_name})
```

### Recall Monitoring
Periodically compare approximate (HNSW) vs exact (brute-force) search:
```sql
-- Exact search (no index)
SET LOCAL enable_indexscan = off;
SELECT id FROM documents ORDER BY embedding <=> $1 LIMIT 10;

-- Compare with index search results to measure actual recall
```

---

## Cost Optimization

### Embedding Costs
| Strategy | Savings | Tradeoff |
|----------|---------|----------|
| Use text-embedding-3-small instead of large | 85% | ~2% quality loss |
| Use voyage-3.5-lite instead of voyage-3.5 | 67% | Minimal quality loss |
| Batch via OpenAI Batch API (24hr) | 50% | Latency (not for real-time) |
| Self-host BGE-M3 | 100% | GPU infrastructure cost |
| Cache frequent query embeddings | 30–50% | Cache management |

### Storage Costs
| Strategy | Compression | Quality Impact |
|----------|------------|----------------|
| MRL truncation (3072→512 dims) | 6× | ~4% loss |
| halfvec (float32→float16) | 2× | <0.5% loss |
| MRL + halfvec combined | 12× | ~4.5% loss |
| MRL + int8 quantization | 24× | ~3% loss |
| Binary quantization + rescore | 32× | <2% with rescoring |

### Infrastructure Costs
- Self-hosted pgvector costs ~75% less than Pinecone at comparable scale
- ARM instances (AWS Graviton) deliver ~15% better price-performance
- Right-size: most teams over-provision. Start small, scale based on actual p99 latency
- Supabase Pro ($25/mo) handles 1M+ vectors with proper indexing

### Query Cost Reduction
- Cache embedding of frequent queries (LRU cache, Redis)
- Cache full search results for identical queries (TTL: 5–60 minutes)
- Reduce ef_search for low-priority queries
- Use MRL smaller dimensions for initial filtering, full dimensions for final ranking

---

## Data Freshness

### Strategies by Update Frequency

**Real-time (seconds)**: Direct insert/update + HNSW (handles dynamic inserts well)
```python
# Webhook or event-driven: embed and insert immediately
embedding = embed(new_document.content)
supabase.from_('documents').upsert({
    'id': new_document.id,
    'content': new_document.content,
    'embedding': embedding,
    'updated_at': 'now()'
}).execute()
```

**Near-real-time (minutes)**: Queue + batch processing
```python
# n8n/Power Automate triggers batch embedding every 5 minutes
# Process queue of changed documents
```

**Periodic (hours/days)**: Scheduled re-embedding pipeline
```python
# Daily job: find documents changed since last run
# Re-embed and upsert
```

### Model Version Management
```sql
-- Store model version with each embedding
ALTER TABLE documents ADD COLUMN embedding_model_version text DEFAULT 'v1';

-- When upgrading models, batch re-embed:
-- 1. Add new column or update in place
-- 2. Process in batches of 1000
-- 3. Rebuild index after completion
UPDATE documents SET
    embedding = new_embedding_function(content),
    embedding_model_version = 'v2'
WHERE embedding_model_version = 'v1'
LIMIT 1000;  -- Process in batches
```

### IVFFlat Re-indexing
IVFFlat needs re-indexing when data grows by 50%+:
```sql
-- Non-blocking rebuild
REINDEX INDEX CONCURRENTLY idx_ivf;
-- Or drop and recreate with updated lists count
```

HNSW does NOT need re-indexing for new data — it handles inserts natively.

---

## Security

### Data Protection
- **Embeddings are sensitive**: Researchers have demonstrated partial text reconstruction from embeddings. Treat embeddings with same rigor as source data
- **Encrypt at rest**: Supabase encrypts by default (AES-256)
- **Encrypt in transit**: Enforce `sslmode=require` for all connections
- **API key management**: Use Supabase Vault for embedding API keys. Never expose `service_role` key to client-side code

### Access Control (Supabase)
```sql
-- Enable RLS
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Users can only read their own documents
CREATE POLICY "Users read own docs"
    ON documents FOR SELECT
    USING (auth.uid() = user_id);

-- Users can only insert their own documents
CREATE POLICY "Users insert own docs"
    ON documents FOR INSERT
    WITH CHECK (auth.uid() = user_id);
```

### Multi-Tenant Isolation
1. **RLS policies**: Filter by tenant_id, enforced at database level
2. **Partition by tenant**: Strongest isolation, separate indexes per tenant
3. **Separate databases**: Maximum isolation for enterprise compliance (e.g., government)

### Audit Trail
```sql
-- Log all vector search queries
CREATE TABLE search_audit (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id),
    query_text text,
    result_count int,
    top_similarity float,
    searched_at timestamptz DEFAULT now()
);
```

---

## Backup and Recovery

### Supabase Backup
- **Pro plan**: Automatic daily backups + point-in-time recovery (PITR) via WAL archiving
- **Manual backup**: Dashboard → Database → Backups
- **pg_dump**: Run against direct connection (port 5432), NOT through Supavisor

```bash
# Manual pg_dump (includes vector data)
pg_dump -h db.xxxx.supabase.co -p 5432 -U postgres -d postgres \
  --no-owner --no-acl -Fc > backup.dump

# Restore
pg_restore -h db.xxxx.supabase.co -p 5432 -U postgres -d postgres backup.dump
```

### Self-Hosted pgvector Backup
```bash
# Full backup with compression
pg_dump -Fc -Z 9 dbname > backup_$(date +%Y%m%d).dump

# Incremental via WAL archiving (for PITR)
archive_mode = on
archive_command = 'cp %p /backup/wal/%f'
```

### Recovery Testing
- **Test restores regularly** — an untested backup is not a backup
- Restore to a staging environment monthly
- Verify vector search works after restore (indexes may need rebuild)
- Document RTO (Recovery Time Objective) and RPO (Recovery Point Objective)

---

## Scaling Strategies

### Vertical Scaling (pgvector)
1. Increase RAM to fit HNSW index in shared_buffers
2. Use NVMe SSDs for disk-based operations
3. Increase max_parallel_workers for parallel queries
4. Use halfvec to halve memory requirements

### Horizontal Scaling Triggers
Move from pgvector to distributed database when:
- >100M vectors and growing
- p99 latency consistently >100ms despite tuning
- Need >10K QPS sustained
- Geographic distribution required

### Read Replicas (Supabase)
```
Write queries → Primary (port 5432)
Read queries → Read replica (separate connection string)
```

Supabase supports read replicas on Pro+ plans. Vector search queries can be routed to replicas.

### Sharding Strategies (Milvus/Distributed)
- **By tenant**: Each tenant in separate partition/shard
- **By time**: Recent data on fast storage, historical on cold
- **By document type**: Different indexes for different content types
- **Geographic**: Replicas in regions close to users
