# Scripts Directory

Utility scripts for project maintenance and data operations.

## Documentation Indexing (RAG Setup)

Scripts to index project documentation for Retrieval-Augmented Generation (RAG).

### Setup Process

#### 1. Create Supabase Table

Run `create_documents_table.sql` in Supabase SQL Editor:

```sql
-- Copy contents of scripts/create_documents_table.sql
-- Paste in Supabase SQL Editor
-- Execute
```

This creates:
- ✅ `documents` table with pgvector support
- ✅ Vector index for fast similarity search
- ✅ `match_documents()` RPC function

#### 2. Index Documentation

Run the indexing script:

```bash
# Set environment variables
export OPENAI_API_KEY="sk-..."
export SUPABASE_URL="https://xxx.supabase.co"
export SUPABASE_KEY="eyJ..."

# Run indexing
python scripts/index_documentation.py
```

**What it does:**
1. Reads all `.md` files from `documents/` directory
2. Chunks documents semantically (~1000 chars, 200 overlap)
3. Embeds chunks using OpenAI `text-embedding-3-small`
4. Stores in Supabase `documents` table with metadata

**Expected output:**
```
🚀 Starting documentation indexing...
📄 Found 7 markdown files
📖 Processing: documents/chatwoot/api-reference.md
  ✅ Created 12 chunks
📖 Processing: documents/waha/api-reference.md
  ✅ Created 8 chunks
...
📦 Total chunks created: 85
Embedding 85 texts...
✅ Embedded 85 texts
Storing 85 chunks in Supabase...
✅ Inserted batch 1/1
✅ Stored 85 chunks in Supabase
🎉 Documentation indexing complete!
```

#### 3. Verify Indexing

Test vector search in Supabase SQL Editor:

```sql
-- Count documents
SELECT COUNT(*) FROM documents;

-- Sample documents
SELECT
    id,
    LEFT(content, 100) as content_preview,
    metadata->>'category' as category,
    metadata->>'source' as source
FROM documents
LIMIT 10;

-- Test vector search (requires embedding vector)
SELECT
    id,
    LEFT(content, 100) as content_preview,
    metadata,
    similarity
FROM match_documents(
    '[0.1, 0.2, ...]'::vector,  -- Replace with actual embedding
    0.7,  -- similarity threshold
    5     -- max results
);
```

### Re-indexing

To re-index (e.g., after updating documentation):

```bash
# 1. Clear existing data
# Run in Supabase SQL Editor:
TRUNCATE TABLE documents;

# 2. Re-run indexing
python scripts/index_documentation.py
```

### Cost Estimation

**OpenAI Embedding Costs:**
- Model: `text-embedding-3-small`
- Price: $0.02 per 1M tokens
- Average doc size: ~2000 tokens/document
- 7 documents ≈ 14,000 tokens
- Cost: ~$0.0003 (less than 1 cent)

**Supabase Storage:**
- Free tier: 500 MB database
- Each chunk: ~1-2 KB
- 100 chunks ≈ 200 KB
- Well within free tier

## Troubleshooting

### Import Errors

If you get import errors:

```bash
# Install dependencies
pip install openai supabase-py

# Or if using poetry:
poetry add openai supabase-py
```

### Supabase Connection Errors

Verify environment variables:

```bash
echo $SUPABASE_URL
echo $SUPABASE_KEY
```

Ensure you're using the **service role key** (not anon key) for write operations.

### OpenAI Rate Limits

If you hit rate limits:

```python
# Modify index_documentation.py
# Add delay between batches:
import asyncio
await asyncio.sleep(1)  # Add after each embed batch
```

## Next Steps

After indexing documentation:

1. **Implement RAG Agent** - Add retrieval agent to LangGraph workflow
2. **Test Retrieval** - Query agent about technical topics
3. **Monitor Usage** - Track which docs are retrieved most often
4. **Update Regularly** - Re-index when documentation changes

## Files

- `index_documentation.py` - Main indexing script
- `create_documents_table.sql` - Supabase table setup
- `README.md` - This file

Last updated: 2025-01-15
