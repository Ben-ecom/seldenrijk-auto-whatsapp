# Supabase pgvector Guide

Complete guide for using pgvector with Supabase for vector similarity search.

## Overview

**pgvector:** PostgreSQL extension for vector similarity search
**Supabase:** Provides managed PostgreSQL with pgvector enabled

**Use Cases:**
- Semantic search (RAG)
- Document similarity
- Recommendation systems
- Clustering and classification

## Setup

### Enable pgvector Extension

```sql
-- Run in Supabase SQL Editor
CREATE EXTENSION IF NOT EXISTS vector;
```

### Create Vector Table

```sql
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(1536),  -- OpenAI embedding size
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for fast similarity search
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**Index Types:**
- `ivfflat`: Fast approximate search (recommended)
- `hnsw`: Faster but more memory (PostgreSQL 16+)

**Distance Functions:**
- `vector_cosine_ops`: Cosine distance (most common)
- `vector_l2_ops`: Euclidean distance (L2)
- `vector_ip_ops`: Inner product

## Inserting Vectors

### Python Client

```python
from supabase import create_client
import os

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Insert document with embedding
supabase.table("documents").insert({
    "content": "This is a document about cars",
    "embedding": [0.1, 0.2, ...],  # 1536 dimensions
    "metadata": {
        "source": "manual",
        "category": "automotive"
    }
}).execute()
```

### Batch Insert

```python
documents = [
    {
        "content": "Document 1",
        "embedding": embedding_1,
        "metadata": {"category": "A"}
    },
    {
        "content": "Document 2",
        "embedding": embedding_2,
        "metadata": {"category": "B"}
    }
]

supabase.table("documents").insert(documents).execute()
```

## Vector Similarity Search

### Basic Similarity Search

```sql
SELECT
    id,
    content,
    metadata,
    1 - (embedding <=> '[0.1, 0.2, ...]'::vector) AS similarity
FROM documents
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 5;
```

**Distance Operators:**
- `<=>`: Cosine distance
- `<->`: Euclidean distance (L2)
- `<#>`: Inner product

### Python Client

```python
# Vector search
query_embedding = [0.1, 0.2, ...]  # Your query embedding

results = supabase.rpc(
    "match_documents",
    {
        "query_embedding": query_embedding,
        "match_threshold": 0.7,
        "match_count": 5
    }
).execute()
```

### RPC Function for Search

Create this function in Supabase:

```sql
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10
)
RETURNS TABLE(
    id BIGINT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        documents.id,
        documents.content,
        documents.metadata,
        1 - (documents.embedding <=> query_embedding) AS similarity
    FROM documents
    WHERE 1 - (documents.embedding <=> query_embedding) > match_threshold
    ORDER BY documents.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

## Filtering + Vector Search

### Metadata Filtering

```sql
-- SQL
SELECT
    id,
    content,
    1 - (embedding <=> $1::vector) AS similarity
FROM documents
WHERE
    metadata->>'category' = 'automotive'
    AND 1 - (embedding <=> $1::vector) > 0.7
ORDER BY embedding <=> $1::vector
LIMIT 5;
```

```python
# Python with RPC
results = supabase.rpc(
    "match_documents_filtered",
    {
        "query_embedding": query_embedding,
        "filter_category": "automotive",
        "match_threshold": 0.7,
        "match_count": 5
    }
).execute()
```

### Advanced RPC with Filters

```sql
CREATE OR REPLACE FUNCTION match_documents_filtered(
    query_embedding VECTOR(1536),
    filter_category TEXT DEFAULT NULL,
    filter_tags TEXT[] DEFAULT NULL,
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10
)
RETURNS TABLE(
    id BIGINT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        documents.id,
        documents.content,
        documents.metadata,
        1 - (documents.embedding <=> query_embedding) AS similarity
    FROM documents
    WHERE
        1 - (documents.embedding <=> query_embedding) > match_threshold
        AND (filter_category IS NULL OR metadata->>'category' = filter_category)
        AND (filter_tags IS NULL OR metadata->'tags' ?| filter_tags)
    ORDER BY documents.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

## Hybrid Search (Vector + Full-Text)

### Full-Text Search Setup

```sql
-- Add tsvector column
ALTER TABLE documents ADD COLUMN content_tsv TSVECTOR;

-- Generate tsvector
UPDATE documents SET content_tsv = to_tsvector('english', content);

-- Create GIN index
CREATE INDEX documents_content_tsv_idx ON documents USING GIN(content_tsv);

-- Auto-update trigger
CREATE TRIGGER documents_content_tsv_update
BEFORE INSERT OR UPDATE ON documents
FOR EACH ROW EXECUTE PROCEDURE
tsvector_update_trigger(content_tsv, 'pg_catalog.english', content);
```

### Hybrid Search RPC

```sql
CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding VECTOR(1536),
    query_text TEXT,
    match_count INT DEFAULT 10
)
RETURNS TABLE(
    id BIGINT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT,
    rank FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH vector_results AS (
        SELECT
            documents.id,
            documents.content,
            documents.metadata,
            1 - (documents.embedding <=> query_embedding) AS similarity,
            ROW_NUMBER() OVER (ORDER BY documents.embedding <=> query_embedding) AS rank
        FROM documents
        ORDER BY documents.embedding <=> query_embedding
        LIMIT match_count * 2
    ),
    fts_results AS (
        SELECT
            documents.id,
            documents.content,
            documents.metadata,
            ts_rank(documents.content_tsv, plainto_tsquery('english', query_text)) AS rank,
            ROW_NUMBER() OVER (ORDER BY ts_rank(documents.content_tsv, plainto_tsquery('english', query_text)) DESC) AS rank_num
        FROM documents
        WHERE documents.content_tsv @@ plainto_tsquery('english', query_text)
        ORDER BY rank DESC
        LIMIT match_count * 2
    )
    SELECT
        COALESCE(v.id, f.id) AS id,
        COALESCE(v.content, f.content) AS content,
        COALESCE(v.metadata, f.metadata) AS metadata,
        COALESCE(v.similarity, 0.0) AS similarity,
        -- RRF (Reciprocal Rank Fusion)
        (
            1.0 / (60.0 + COALESCE(v.rank, 1000000)) +
            1.0 / (60.0 + COALESCE(f.rank_num, 1000000))
        ) AS rank
    FROM vector_results v
    FULL OUTER JOIN fts_results f ON v.id = f.id
    ORDER BY rank DESC
    LIMIT match_count;
END;
$$;
```

## Performance Optimization

### Index Tuning

```sql
-- Create HNSW index (PostgreSQL 16+, faster but more memory)
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);

-- Tune IVFFlat index
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);  -- Adjust based on table size

-- Rule of thumb: lists = rows / 1000
-- 10k rows → lists = 10
-- 100k rows → lists = 100
-- 1M rows → lists = 1000
```

### Partial Indexes

```sql
-- Index only relevant documents
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops)
WHERE metadata->>'category' = 'automotive';
```

### Query Optimization

```python
# ✅ Good - use RPC function
results = supabase.rpc("match_documents", {...}).execute()

# ❌ Bad - client-side filtering (slow)
all_docs = supabase.table("documents").select("*").execute()
filtered = [doc for doc in all_docs if similarity(doc, query) > 0.7]
```

## Monitoring

### Check Index Usage

```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'documents';
```

### Query Performance

```sql
EXPLAIN ANALYZE
SELECT *
FROM documents
ORDER BY embedding <=> '[...]'::vector
LIMIT 10;
```

## Common Patterns

### Document Chunking + Embedding

```python
async def ingest_document(document: str, metadata: dict):
    """Chunk and embed document."""

    # 1. Chunk document
    chunks = chunk_document(document, chunk_size=1000, overlap=200)

    # 2. Embed chunks
    embeddings = await batch_embed(chunks)

    # 3. Insert into Supabase
    records = [
        {
            "content": chunk,
            "embedding": emb,
            "metadata": {**metadata, "chunk_index": i}
        }
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
    ]

    supabase.table("documents").insert(records).execute()
```

### Batch Embedding

```python
async def batch_embed(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in parallel."""
    import openai

    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )

    return [item.embedding for item in response.data]
```

### Semantic Search

```python
async def semantic_search(
    query: str,
    top_k: int = 5,
    threshold: float = 0.7
) -> list[dict]:
    """Semantic search using vector similarity."""

    # 1. Embed query
    query_embedding = await embed_text(query)

    # 2. Vector search
    results = supabase.rpc(
        "match_documents",
        {
            "query_embedding": query_embedding,
            "match_threshold": threshold,
            "match_count": top_k
        }
    ).execute()

    return results.data
```

### Update Embeddings

```python
async def update_document_embedding(doc_id: int, new_content: str):
    """Update document content and embedding."""

    # 1. Generate new embedding
    new_embedding = await embed_text(new_content)

    # 2. Update database
    supabase.table("documents").update({
        "content": new_content,
        "embedding": new_embedding
    }).eq("id", doc_id).execute()
```

## Best Practices

### 1. Choose Right Embedding Model

```python
# OpenAI embeddings (recommended)
- text-embedding-3-small: 1536 dims, $0.02/1M tokens
- text-embedding-3-large: 3072 dims, $0.13/1M tokens

# Vector column size MUST match embedding dimensions
CREATE TABLE documents (
    embedding VECTOR(1536)  -- Match model output
);
```

### 2. Normalize Embeddings (if using cosine)

```python
import numpy as np

def normalize_embedding(embedding: list[float]) -> list[float]:
    """Normalize for cosine similarity."""
    arr = np.array(embedding)
    norm = np.linalg.norm(arr)
    return (arr / norm).tolist()
```

### 3. Handle Large Tables

```python
# Use cursor pagination for large tables
offset = 0
batch_size = 1000

while True:
    batch = supabase.table("documents")\
        .select("*")\
        .range(offset, offset + batch_size - 1)\
        .execute()

    if not batch.data:
        break

    # Process batch
    process_batch(batch.data)

    offset += batch_size
```

### 4. Metadata Design

```python
# ✅ Good - structured metadata
metadata = {
    "source": "api_docs",
    "category": "chatwoot",
    "language": "en",
    "tags": ["contacts", "conversations"],
    "created_at": "2025-01-15T10:00:00Z",
    "version": "1.0"
}

# Enable efficient filtering
WHERE metadata->>'category' = 'chatwoot'
AND metadata->'tags' ? 'contacts'
```

### 5. Error Handling

```python
try:
    results = supabase.rpc("match_documents", {...}).execute()
except Exception as e:
    logger.error(f"Vector search failed: {e}")
    # Fallback to keyword search
    results = supabase.table("documents")\
        .select("*")\
        .ilike("content", f"%{query}%")\
        .execute()
```

## Troubleshooting

### Slow Queries

```sql
-- Check if index is being used
EXPLAIN ANALYZE
SELECT * FROM documents
ORDER BY embedding <=> '[...]'::vector
LIMIT 10;

-- Should see: "Index Scan using documents_embedding_idx"
-- If not, rebuild index or adjust lists parameter
```

### Memory Issues

```sql
-- Reduce index memory usage (IVFFlat)
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50);  -- Fewer lists = less memory

-- Or use partial index
CREATE INDEX ON documents_recent_idx
USING ivfflat (embedding vector_cosine_ops)
WHERE created_at > NOW() - INTERVAL '30 days';
```

### Index Not Used

```sql
-- Ensure statistics are up-to-date
ANALYZE documents;

-- Rebuild index if corrupted
REINDEX INDEX documents_embedding_idx;
```

## Python Async Client

```python
from supabase import create_async_client

async def get_supabase():
    """Get async Supabase client."""
    return await create_async_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

# Usage
supabase = await get_supabase()
results = await supabase.rpc("match_documents", {...}).execute()
```

## Connection Pooling

```python
from supabase_pooler import create_pool

# Create connection pool
pool = create_pool(
    connection_string=os.getenv("SUPABASE_CONNECTION_STRING"),
    min_size=5,
    max_size=20
)

# Use pool
async with pool.acquire() as conn:
    results = await conn.fetch(
        "SELECT * FROM match_documents($1, $2)",
        query_embedding,
        5
    )
```

## Source

Documentation compiled from:
- https://supabase.com/docs/guides/ai/vector-columns
- https://github.com/pgvector/pgvector
- Supabase vector search examples
- PostgreSQL pgvector documentation
