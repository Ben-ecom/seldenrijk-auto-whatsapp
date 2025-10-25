-- Migration: Add RAG cache table
-- Purpose: Cache RAG search results to reduce scraping overhead
-- Date: 2025-01-13

CREATE TABLE IF NOT EXISTS rag_cache (
    -- Cache key (derived from search parameters)
    cache_key VARCHAR(255) PRIMARY KEY,

    -- Cached results (JSON format)
    results JSONB NOT NULL,

    -- Search parameters (for debugging)
    search_params JSONB,

    -- Cache metadata
    result_count INT,
    source VARCHAR(50),  -- marktplaats, website, both

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,  -- TTL: 10 minutes from creation
    last_accessed_at TIMESTAMP DEFAULT NOW(),

    -- Access tracking
    access_count INT DEFAULT 0
);

-- Create indexes separately
CREATE INDEX idx_rag_cache_expires_at ON rag_cache(expires_at);
CREATE INDEX idx_rag_cache_created_at ON rag_cache(created_at);
CREATE INDEX idx_rag_cache_source ON rag_cache(source);

-- Add comment
COMMENT ON TABLE rag_cache IS 'Caches RAG search results with 10-minute TTL to reduce scraping overhead';

-- Auto-cleanup expired cache entries (run periodically)
-- Note: This should be run by a scheduled task (Celery beat)
-- DELETE FROM rag_cache WHERE expires_at < NOW();
