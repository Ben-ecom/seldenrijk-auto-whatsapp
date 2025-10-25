-- Create documents table for RAG vector storage
-- Run this in Supabase SQL Editor

-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create documents table
CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(1536),  -- OpenAI text-embedding-3-small dimensions
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Create index for fast vector similarity search
CREATE INDEX IF NOT EXISTS documents_embedding_idx
ON documents
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 4. Create index for metadata filtering
CREATE INDEX IF NOT EXISTS documents_metadata_idx
ON documents
USING GIN (metadata);

-- 5. Create RPC function for vector search
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5,
    filter_category TEXT DEFAULT NULL
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
    ORDER BY documents.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 6. Grant permissions (if needed)
-- ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Public read access" ON documents FOR SELECT USING (true);

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Documents table created successfully!';
    RAISE NOTICE '✅ Vector index created (ivfflat with cosine similarity)';
    RAISE NOTICE '✅ RPC function match_documents() created';
    RAISE NOTICE '';
    RAISE NOTICE '📋 Next steps:';
    RAISE NOTICE '1. Run: python scripts/index_documentation.py';
    RAISE NOTICE '2. Test: SELECT match_documents(''[0.1, 0.2, ...]''::vector, 0.7, 5);';
END $$;
