# pgvector Production Playbook (Supabase)

## Table of Contents
1. [Schema Design](#schema-design)
2. [Index Creation](#index-creation)
3. [PostgreSQL Tuning](#postgresql-tuning)
4. [Batch Insert Patterns](#batch-insert-patterns)
5. [Connection Pooling](#connection-pooling)
6. [Row Level Security](#row-level-security)
7. [Standard Search Functions](#standard-search-functions)
8. [Monitoring](#monitoring)

---

## Schema Design

### Standard Vector Table
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    content text NOT NULL,
    metadata jsonb DEFAULT '{}',
    embedding vector(1536),  -- Match your model's dimensions
    fts tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    embedding_model text DEFAULT 'text-embedding-3-small',
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Full-text search index
CREATE INDEX idx_documents_fts ON documents USING gin(fts);

-- Metadata GIN index for JSONB filtering
CREATE INDEX idx_documents_metadata ON documents USING gin(metadata);

-- Timestamp index for freshness queries
CREATE INDEX idx_documents_created ON documents(created_at DESC);
```

### Multi-Tenant Schema
```sql
CREATE TABLE documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    content text NOT NULL,
    embedding vector(1536),
    fts tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    metadata jsonb DEFAULT '{}'
);

-- Composite index: tenant filter + vector search
CREATE INDEX idx_docs_tenant ON documents(tenant_id);

-- Option A: Single HNSW index (works with iterative_scan for filtered queries)
CREATE INDEX idx_docs_embedding ON documents
  USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Option B: Partition by tenant (best for large multi-tenant)
-- Per-partition HNSW indexes eliminate cross-tenant scanning
CREATE TABLE documents (
    id uuid, tenant_id uuid NOT NULL,
    content text, embedding vector(1536)
) PARTITION BY LIST (tenant_id);
```

### Using halfvec for Storage Savings
```sql
-- halfvec uses float16 (2 bytes) instead of float32 (4 bytes) = 2× compression
-- Available in pgvector 0.7+
ALTER TABLE documents ADD COLUMN embedding_half halfvec(1536);

-- Convert existing embeddings
UPDATE documents SET embedding_half = embedding::halfvec;

-- Index on halfvec
CREATE INDEX idx_halfvec ON documents
  USING hnsw (embedding_half halfvec_cosine_ops);
```

---

## Index Creation

### Production HNSW Index
```sql
-- Step 1: Load ALL data first (indexes slow inserts dramatically)

-- Step 2: Analyze for accurate statistics
VACUUM ANALYZE documents;

-- Step 3: Create index concurrently (non-blocking)
CREATE INDEX CONCURRENTLY idx_docs_embedding ON documents
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- Step 4: Verify index is valid
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'documents';
```

### IVFFlat (for static datasets)
```sql
-- Data MUST exist before creating IVFFlat
VACUUM ANALYZE documents;

-- Calculate optimal lists: rows/1000 for <1M, sqrt(rows) for ≥1M
CREATE INDEX CONCURRENTLY idx_ivf ON documents
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 1000);  -- Adjust based on row count
```

### Rebuilding Indexes
```sql
-- IVFFlat: Rebuild when data grows by 50%+
REINDEX INDEX CONCURRENTLY idx_ivf;

-- HNSW: Rarely needs rebuild — handles inserts well
-- But rebuild if you changed M or ef_construction
DROP INDEX CONCURRENTLY idx_docs_embedding;
CREATE INDEX CONCURRENTLY idx_docs_embedding ON documents
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

---

## PostgreSQL Tuning

### Memory Configuration
```ini
# postgresql.conf or Supabase Dashboard → Database Settings
shared_buffers = '8GB'               # 25% of RAM; HNSW index should fit here
effective_cache_size = '24GB'         # 75% of total RAM
maintenance_work_mem = '2GB'          # Larger = faster index builds
work_mem = '256MB'                    # Per-operation sort memory
```

### Parallelism
```ini
max_parallel_maintenance_workers = 4  # Parallel HNSW builds (pgvector 0.6+)
max_parallel_workers_per_gather = 4   # Parallel query execution
max_parallel_workers = 8
```

### WAL Configuration (for bulk loads)
```ini
max_wal_size = '4GB'       # Increase for bulk operations
wal_compression = on       # Reduce WAL size
checkpoint_timeout = '30min'
```

### Hardware Sizing
| Vectors | Dims | Recommended RAM | Storage |
|---------|------|-----------------|---------|
| 1M | 1536 | 16 GB | 50 GB SSD |
| 5M | 1536 | 64 GB | 200 GB SSD |
| 10M | 1536 | 128 GB | 500 GB NVMe |
| 50M | 1536 | 512 GB | 2 TB NVMe |
| 10M | 512 | 32 GB | 100 GB SSD |

ARM instances deliver ~15% better price-performance for vector ops.

---

## Batch Insert Patterns

### Fastest: Binary COPY (>10K rows)
```sql
COPY documents (id, content, embedding) FROM STDIN WITH (FORMAT BINARY);
```

### Application Code: INSERT...UNNEST (2× faster than VALUES)
```sql
INSERT INTO documents (content, embedding)
SELECT unnest($1::text[]), unnest($2::vector[]);
```

### Supabase JavaScript Client
```javascript
const batchSize = 500;  // Optimal for Supabase
for (let i = 0; i < docs.length; i += batchSize) {
    const batch = docs.slice(i, i + batchSize);
    const { error } = await supabase.from('documents').upsert(
        batch.map(d => ({
            id: d.id,
            content: d.content,
            metadata: d.metadata,
            embedding: d.embedding
        }))
    );
    if (error) throw error;
}
```

### Python with psycopg2 (fastest for large loads)
```python
import psycopg2
from psycopg2.extras import execute_values

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# execute_values is much faster than individual inserts
data = [(doc.content, doc.metadata, doc.embedding) for doc in docs]
execute_values(
    cur,
    "INSERT INTO documents (content, metadata, embedding) VALUES %s",
    data,
    template="(%s, %s::jsonb, %s::vector)",
    page_size=500
)
conn.commit()
```

### Post-Bulk-Load Checklist
1. `VACUUM ANALYZE documents;`
2. Create indexes (if not already created)
3. Verify index is being used: `EXPLAIN ANALYZE SELECT ...`

---

## Connection Pooling

### Supavisor Transaction Mode (Port 6543)
- Releases connections after each transaction
- Session-level `SET` commands DON'T persist
- **Always use SET LOCAL within BEGIN...COMMIT**:

```sql
BEGIN;
SET LOCAL hnsw.ef_search = 100;
SET LOCAL hnsw.iterative_scan = on;  -- For filtered queries
SELECT * FROM documents ORDER BY embedding <=> $1 LIMIT 10;
COMMIT;
```

### Direct Connection (Port 5432)
- Session-level SET persists
- Limited connection count — use only for migrations and admin tasks

### Supabase Client Configuration
```javascript
// Supabase client uses Supavisor transaction mode by default
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// For vector search, use .rpc() to call server-side functions
// This ensures SET LOCAL works correctly
const { data } = await supabase.rpc('match_documents', {
    query_embedding: embedding,
    match_count: 10
});
```

---

## Row Level Security

### The Over-Filtering Problem
HNSW returns K nearest candidates → RLS filters some → fewer than K results. Three solutions:

### Solution 1: Iterative Scanning (pgvector 0.8+, Recommended)
```sql
BEGIN;
SET LOCAL hnsw.iterative_scan = on;
SET LOCAL hnsw.max_scan_tuples = 10000;
-- pgvector continues scanning until enough rows pass RLS
SELECT * FROM documents ORDER BY embedding <=> $1 LIMIT 10;
COMMIT;
```

### Solution 2: SECURITY DEFINER Function
```sql
CREATE OR REPLACE FUNCTION match_documents_for_user(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.78,
    match_count int DEFAULT 10,
    p_user_id uuid DEFAULT auth.uid()
) RETURNS TABLE (id uuid, content text, similarity float)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT d.id, d.content,
        1 - (d.embedding <=> query_embedding) AS similarity
    FROM documents d
    WHERE d.user_id = p_user_id
        AND 1 - (d.embedding <=> query_embedding) > match_threshold
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

### Solution 3: Partitioning by Tenant
```sql
-- Best for large multi-tenant: partition eliminates cross-tenant scanning
CREATE TABLE documents (...) PARTITION BY LIST (tenant_id);
-- Create per-tenant partitions with their own HNSW indexes
```

---

## Standard Search Functions

### Basic Vector Search
```sql
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(1536),
    match_count int DEFAULT 10,
    filter jsonb DEFAULT '{}'
) RETURNS TABLE (id uuid, content text, metadata jsonb, similarity float)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT d.id, d.content, d.metadata,
        1 - (d.embedding <=> query_embedding) AS similarity
    FROM documents d
    WHERE d.metadata @> filter
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

### Hybrid Search with RRF
```sql
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text text,
    query_embedding vector(1536),
    match_count int DEFAULT 10,
    full_text_weight float DEFAULT 1.0,
    semantic_weight float DEFAULT 1.0,
    rrf_k int DEFAULT 60
) RETURNS TABLE (id uuid, content text, metadata jsonb, score float)
LANGUAGE SQL AS $$
WITH full_text AS (
    SELECT id, ROW_NUMBER() OVER(
        ORDER BY ts_rank(fts, websearch_to_tsquery(query_text)) DESC
    ) AS rank
    FROM documents
    WHERE fts @@ websearch_to_tsquery(query_text)
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
    d.content, d.metadata,
    COALESCE(full_text_weight / (rrf_k + f.rank), 0.0) +
    COALESCE(semantic_weight / (rrf_k + s.rank), 0.0) AS score
FROM full_text f
FULL OUTER JOIN semantic s ON f.id = s.id
JOIN documents d ON d.id = COALESCE(f.id, s.id)
ORDER BY score DESC
LIMIT match_count;
$$;
```

---

## Monitoring

### Key Metrics to Track
```sql
-- Index usage (is the HNSW index being used?)
SELECT indexrelname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
WHERE schemaname = 'public' AND relname = 'documents';

-- Cache hit ratio (target: >99%)
SELECT
    sum(heap_blks_hit) / NULLIF(sum(heap_blks_hit) + sum(heap_blks_read), 0) AS cache_ratio
FROM pg_statio_user_tables
WHERE relname = 'documents';

-- Table size including indexes
SELECT
    pg_size_pretty(pg_total_relation_size('documents')) AS total_size,
    pg_size_pretty(pg_relation_size('documents')) AS table_size,
    pg_size_pretty(pg_indexes_size('documents')) AS index_size;

-- Slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE query LIKE '%embedding%'
ORDER BY mean_exec_time DESC LIMIT 10;
```

### Health Checks
```sql
-- Verify HNSW index is valid (not corrupted after concurrent build)
SELECT indexname, indisvalid
FROM pg_indexes JOIN pg_index ON indexrelid = (schemaname || '.' || indexname)::regclass
WHERE tablename = 'documents';

-- Connection count (stay below 80% of max)
SELECT count(*) AS active, max_conn
FROM pg_stat_activity, (SELECT setting::int AS max_conn FROM pg_settings WHERE name='max_connections') mc
WHERE state = 'active'
GROUP BY max_conn;
```
