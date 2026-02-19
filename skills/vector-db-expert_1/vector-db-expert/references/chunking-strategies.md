# Chunking Strategies Reference

## Table of Contents
1. [Recursive Character Splitting](#recursive-character-splitting)
2. [Contextual Retrieval](#contextual-retrieval)
3. [Late Chunking](#late-chunking)
4. [Parent-Child Retrieval](#parent-child-retrieval)
5. [Metadata Enrichment](#metadata-enrichment)
6. [Chunk Size Tuning](#chunk-size-tuning)

---

## Recursive Character Splitting

The recommended default. Applies separators hierarchically: paragraph breaks → line breaks → sentences → words → characters.

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,       # tokens (approximate via ~4 chars/token)
    chunk_overlap=75,     # 15% overlap — NVIDIA benchmark optimal
    separators=["\n\n", "\n", ". ", " ", ""],
    length_function=len,  # Replace with tiktoken for exact token counting
)
chunks = splitter.split_documents(documents)
```

### Token-Accurate Splitting
```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
import tiktoken

tokenizer = tiktoken.encoding_for_model("text-embedding-3-small")
splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    encoding_name="cl100k_base",
    chunk_size=512,
    chunk_overlap=75
)
```

### Separator Customization by Document Type
- **Markdown**: `["\n## ", "\n### ", "\n#### ", "\n\n", "\n", ". ", " "]`
- **Python code**: `["\nclass ", "\ndef ", "\n\n", "\n", " "]`
- **HTML**: `["</div>", "</p>", "</section>", "\n\n", "\n", ". "]`
- **Legal/standards**: `["\nSection ", "\nClause ", "\n\n", "\n", ". "]`

---

## Contextual Retrieval

Anthropic's approach: prepend LLM-generated context to each chunk before embedding. The highest-impact single improvement to RAG retrieval quality.

### Impact
- Contextual embeddings alone: **35% fewer retrieval failures**
- + contextual BM25: **49% fewer failures**
- + re-ranking: **67% fewer failures**
- Cost via prompt caching: ~$1.02 per million document tokens

### Implementation
```python
def situate_context(full_document: str, chunk: str) -> str:
    """Generate context prefix for a chunk using the full document."""
    prompt = f"""<document>
{full_document}
</document>
Here is a chunk from the document:
<chunk>
{chunk}
</chunk>
Provide a short succinct context (2-3 sentences) to situate this chunk
within the overall document for retrieval purposes. Answer only with the
context, nothing else."""
    
    context = llm.generate(prompt)  # Use prompt caching for cost efficiency
    return f"{context}\n\n{chunk}"

# Apply before embedding
contextual_chunks = [situate_context(doc, chunk) for chunk in chunks]
embeddings = embed_model.encode(contextual_chunks)
```

### Cost Optimization
- Use prompt caching (cache the full document, vary only the chunk)
- Anthropic prompt caching: 90% cost reduction on cached prefix
- Process in parallel with rate limiting
- Only apply to high-value document collections

---

## Late Chunking

Jina AI's approach: encode the entire document through the transformer FIRST, then apply chunk boundaries AFTER encoding. Every token sees full document context during attention computation.

### When to Use
- Documents with heavy anaphoric references ("it", "the company", "this standard")
- Technical standards and regulations with cross-references
- Long narrative documents where context builds progressively
- Avoids the LLM cost of contextual retrieval

### Implementation
```python
from transformers import AutoModel, AutoTokenizer

model = AutoModel.from_pretrained('jinaai/jina-embeddings-v3', trust_remote_code=True)
tokenizer = AutoTokenizer.from_pretrained('jinaai/jina-embeddings-v3')

# Encode entire document
inputs = tokenizer(full_document, return_tensors='pt', max_length=8192, truncation=True)
outputs = model(**inputs)
token_embeddings = outputs.last_hidden_state[0]  # All token embeddings

# Apply chunk boundaries post-encoding
chunk_embeddings = []
for start, end in chunk_boundaries:
    chunk_emb = token_embeddings[start:end].mean(dim=0)
    chunk_emb = chunk_emb / chunk_emb.norm()  # Normalize
    chunk_embeddings.append(chunk_emb)
```

---

## Parent-Child Retrieval

Embed small chunks for search precision, return parent chunks for LLM context.

### Architecture
- **Child chunks**: 200–400 tokens — embedded and searched
- **Parent chunks**: 1000–2000 tokens — returned as context to LLM
- Each child stores a `parent_id` reference

### LlamaIndex Auto-Merging
```python
from llama_index.core.node_parser import HierarchicalNodeParser, get_leaf_nodes
from llama_index.core.retrievers import AutoMergingRetriever

node_parser = HierarchicalNodeParser.from_defaults(
    chunk_sizes=[2048, 512, 128]  # Parent → child → grandchild
)
nodes = node_parser.get_nodes_from_documents(documents)
leaf_nodes = get_leaf_nodes(nodes)

# Auto-merging: when multiple children from same parent are retrieved,
# automatically return the parent instead
retriever = AutoMergingRetriever(
    vector_retriever, storage_context, simple_ratio_thresh=0.5
)
```

### SQL Pattern for Supabase
```sql
-- Table structure
CREATE TABLE chunks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid REFERENCES documents(id),
    parent_chunk_id uuid REFERENCES chunks(id),  -- NULL for parent chunks
    content text NOT NULL,
    embedding vector(1536),
    chunk_level int DEFAULT 0,  -- 0=parent, 1=child
    token_count int
);

-- Search children, return parents
WITH matched_children AS (
    SELECT parent_chunk_id, 1 - (embedding <=> $1) AS similarity
    FROM chunks
    WHERE chunk_level = 1
    ORDER BY embedding <=> $1
    LIMIT 20
)
SELECT DISTINCT ON (p.id) p.id, p.content, MAX(mc.similarity) AS best_score
FROM matched_children mc
JOIN chunks p ON p.id = mc.parent_chunk_id
GROUP BY p.id, p.content
ORDER BY p.id, best_score DESC
LIMIT 5;
```

---

## Metadata Enrichment

### Minimum Metadata per Chunk
Every chunk should carry: `document_id`, `source/filename`, `page_number`, `section_header`, `chunk_index`, `timestamp`, `document_type`, `language`.

### Enhanced Metadata (LLM-Generated)
- **Summary**: 1-2 sentence description of chunk content
- **Keywords**: 3-5 domain-specific terms extracted from chunk
- **Hypothetical questions**: Questions the chunk could answer (for HyDE-style matching)
- **Entity references**: Named entities, standards numbers, equipment IDs

### Prepend Metadata Before Embedding
```python
def enrich_chunk_for_embedding(chunk, metadata):
    """Prepend metadata to chunk text before generating embedding."""
    prefix = f"Document: {metadata['source']}\n"
    prefix += f"Section: {metadata['section_header']}\n"
    if metadata.get('summary'):
        prefix += f"Summary: {metadata['summary']}\n"
    return f"{prefix}\n{chunk}"
```

Prepending section headers and document titles significantly improves retrieval for complex queries. The embedding captures both the metadata context and the chunk content.

---

## Chunk Size Tuning

### Starting Points
| Use case | Chunk size | Overlap |
|----------|-----------|---------|
| Factoid Q&A | 256–512 tokens | 10–15% |
| Document search | 512 tokens | 15% |
| Summarization | 512–1024 tokens | 10% |
| Code | Function boundaries | 0–10% |
| Legal/compliance | 512 tokens + contextual retrieval | 15% |

### Tuning Protocol
1. Start at 512 tokens / 15% overlap
2. Generate 50+ test queries with known relevant passages
3. Measure Recall@5 and Recall@10
4. Experiment: try 256, 512, 1024 token sizes
5. If precision is poor (too much irrelevant text in results), decrease chunk size
6. If context is insufficient (answers feel incomplete), increase chunk size or use parent-child
7. If specific terms are missed, add hybrid BM25 search

### Common Failure Modes
- **Chunk too small**: Loses context, answer spans multiple chunks
- **Chunk too large**: Dilutes embedding with irrelevant content, lower recall
- **No overlap**: Information at chunk boundaries is split and lost
- **Fixed-size ignoring structure**: Splits mid-sentence or mid-paragraph
- **No metadata**: Chunks lose provenance, can't filter by source/section
