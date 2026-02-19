# Embedding Models Reference

## Table of Contents
1. [Model Comparison](#model-comparison)
2. [Matryoshka Representation Learning (MRL)](#matryoshka-mrl)
3. [Quantization Methods](#quantization-methods)
4. [Code Examples](#code-examples)
5. [Evaluation Guidance](#evaluation-guidance)

---

## Model Comparison

### Voyage AI (Benchmark Leader 2025)
- **voyage-3.5**: Best overall quality. 1024 dims default (up to 2048). $0.06/1M tokens. Outperforms text-embedding-3-large by 8.26% on NDCG@10
- **voyage-3.5-lite**: Budget option matching text-embedding-3-large quality. $0.02/1M tokens
- **voyage-3-large**: 2048 dims, context 32K tokens. $0.18/1M tokens. Best for long documents
- **voyage-code-3**: Optimized for code retrieval. $0.18/1M tokens
- **voyage-context-3**: Specifically designed for contextual chunk-level embeddings

### OpenAI text-embedding-3
- **text-embedding-3-large**: 3072 dims (native MRL to any size). $0.13/1M tokens. MTEB 64.6%. Most widely deployed
- **text-embedding-3-small**: 1536 dims. $0.02/1M tokens. Good default starting point
- Both support native `dimensions` parameter for MRL truncation in API call
- 8191 token context window

### Cohere Embed v4 (April 2025)
- 128K context length — longest available
- Native multimodal (text + images): $0.12/1M tokens text, $0.47/1M images
- Matryoshka dims: 256, 512, 1024, 1536
- Built-in binary quantization support
- 100+ language support — strongest multilingual option alongside BGE-M3

### Open-Source Models
- **BAAI/bge-large-en-v1.5**: 1024 dims, strong English retrieval, MIT license
- **BAAI/BGE-M3**: Multilingual, supports dense + sparse + colbert in one model. 8192 token context
- **Qwen3-Embedding-8B**: Top MTEB scores but requires GPU (8B params)
- **all-MiniLM-L6-v2**: 384 dims, fastest option, good for constrained environments
- **Jina-embeddings-v3**: Task-specific LoRA adapters, late chunking support, 8192 context. 1024 dims

### Choosing Between Models
1. Start with text-embedding-3-small ($0.02) for prototyping
2. If quality insufficient, upgrade to voyage-3.5 ($0.06) — best quality/cost ratio
3. If multilingual needed, use Cohere Embed v4 or BGE-M3
4. If data cannot leave premises, deploy BGE-M3 or Jina-v3
5. Always benchmark on YOUR data — MTEB scores are averages across 8 task categories

---

## Matryoshka MRL

MRL trains models so any prefix of the embedding vector is a valid representation. Halving dimensions typically costs 1–3% quality.

### Dimension Reduction Performance (text-embedding-3-large)
| Dimensions | MTEB Score | Storage/vector | vs Full |
|-----------|-----------|----------------|---------|
| 3072 (full) | 64.6% | 12,288 bytes | 100% |
| 1536 | ~63.5% | 6,144 bytes | ~98.3% |
| 1024 | ~63.0% | 4,096 bytes | ~97.5% |
| 512 | ~62.0% | 2,048 bytes | ~96.0% |
| 256 | ~60.0% | 1,024 bytes | ~93.1% |

### Critical: Normalize After Truncation
Truncated MRL vectors are NOT unit-length. Always L2-normalize:

```python
import numpy as np

embedding = np.array(raw_embedding[:target_dims])
embedding = embedding / np.linalg.norm(embedding)  # REQUIRED
```

OpenAI's API does this automatically when you pass the `dimensions` parameter. If truncating manually, normalize yourself.

---

## Quantization Methods

### Scalar/int8 (Recommended Default)
- 4× compression (float32 → int8)
- Typically <1% accuracy loss
- Supported natively in pgvector 0.7+ via `halfvec` (float16, 2× compression)

### Binary Quantization
- 32× compression (each dimension → 1 bit)
- 5–10% quality drop, rescued by rescoring top candidates with full vectors
- Works best with high-dimensional embeddings (≥768 dims)
- Native support in Cohere Embed v4

### Product Quantization (PQ)
- 16–64× compression
- Groups dimensions into sub-vectors, quantizes each with learned codebook
- Best for billion-scale datasets
- Requires training on representative data

### Optimal Production Pipeline for Large Scale
1. Binary search → retrieve top 100 candidates (ultra-fast)
2. Int8 rescoring → rerank to top 10
3. Cross-encoder reranking → final results

### Combined MRL + Quantization
text-embedding-3-large at 512 dims + int8 = **24× compression** (12,288 → 512 bytes/vector) with ~3% quality loss. At 1B vectors: ~512 GB vs ~12 TB.

---

## Code Examples

### OpenAI with MRL Truncation
```python
from openai import OpenAI
client = OpenAI()

response = client.embeddings.create(
    model="text-embedding-3-large",
    input="Your document text here",
    dimensions=512  # MRL truncation — auto-normalized
)
embedding = response.data[0].embedding  # len(embedding) == 512
```

### Voyage AI
```python
import voyageai
vo = voyageai.Client()

result = vo.embed(
    ["Your document text here"],
    model="voyage-3.5",
    input_type="document"  # Use "query" for search queries
)
embedding = result.embeddings[0]
```

### Cohere Embed v4
```python
import cohere
co = cohere.ClientV2()

response = co.embed(
    texts=["Your document text here"],
    model="embed-v4.0",
    input_type="search_document",  # "search_query" for queries
    embedding_types=["float"],
    output_dimension=512  # Matryoshka truncation
)
embedding = response.embeddings.float_[0]
```

### Open-Source with sentence-transformers
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('BAAI/bge-large-en-v1.5')
embeddings = model.encode(
    ["Your document text here"],
    normalize_embeddings=True,  # L2 normalize
    show_progress_bar=True
)
```

### Batch Embedding (Cost Optimization)
```python
# OpenAI batch API — 50% cost savings, 24hr turnaround
from openai import OpenAI
client = OpenAI()

# Process in batches of 2048 (API limit)
batch_size = 2048
all_embeddings = []
for i in range(0, len(texts), batch_size):
    batch = texts[i:i + batch_size]
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=batch
    )
    all_embeddings.extend([d.embedding for d in response.data])
```

---

## Evaluation Guidance

### Metrics for Retrieval Quality
- **NDCG@10**: Normalized Discounted Cumulative Gain — measures ranking quality
- **MRR**: Mean Reciprocal Rank — where does the first correct result appear?
- **Recall@k**: What fraction of relevant documents are in the top k results?
- **Hit Rate@k**: Binary — is any relevant document in the top k?

### Benchmarking Protocol
1. Collect 100+ domain-specific (query, relevant_documents) pairs
2. Embed all documents with candidate models
3. For each query, retrieve top-10 and compute NDCG@10, Recall@10
4. Compare models — a 2% NDCG improvement is significant
5. Factor in latency and cost per 1M tokens
6. Re-evaluate when switching chunk size or adding contextual retrieval
