-- ============================================
-- Seldenrijk Auto - Supabase Database Schema
-- ============================================
--
-- Purpose: Vehicle inventory with pgvector for semantic search
-- Migration: From Docker Redis (volatile) to Supabase (persistent)
--
-- ============================================

-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- VEHICLE INVENTORY TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS vehicle_inventory (
    -- Primary identifiers
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(255) UNIQUE NOT NULL,  -- From scraper (wire:key attribute)

    -- Vehicle details
    brand VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    title TEXT NOT NULL,  -- Full title (e.g., "Audi Q5 3.0 TDI quattro")

    -- Pricing & specs
    price INTEGER NOT NULL,  -- In euros
    build_year INTEGER,
    mileage INTEGER,  -- In kilometers
    fuel VARCHAR(50),  -- diesel, benzine, hybride, elektrisch
    transmission VARCHAR(50),  -- automaat, handgeschakeld

    -- Rich content for embeddings
    full_description TEXT,  -- Concatenated: brand + model + fuel + transmission + features

    -- Vector embedding (OpenAI text-embedding-3-small = 1536 dimensions)
    embedding vector(1536),

    -- Media & links
    url TEXT NOT NULL,
    image_url TEXT,

    -- Inventory management
    available BOOLEAN DEFAULT true,
    scraped_at TIMESTAMP DEFAULT NOW(),
    last_updated TIMESTAMP DEFAULT NOW(),

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Vector similarity search index (IVFFlat algorithm)
-- Using cosine similarity for semantic search
CREATE INDEX IF NOT EXISTS vehicle_embedding_idx
ON vehicle_inventory
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Fast lookup by brand/model/fuel (exact matching)
CREATE INDEX IF NOT EXISTS vehicle_brand_idx ON vehicle_inventory(brand);
CREATE INDEX IF NOT EXISTS vehicle_model_idx ON vehicle_inventory(model);
CREATE INDEX IF NOT EXISTS vehicle_fuel_idx ON vehicle_inventory(fuel);
CREATE INDEX IF NOT EXISTS vehicle_available_idx ON vehicle_inventory(available);

-- Fast filtering by price/mileage/year
CREATE INDEX IF NOT EXISTS vehicle_price_idx ON vehicle_inventory(price);
CREATE INDEX IF NOT EXISTS vehicle_mileage_idx ON vehicle_inventory(mileage);
CREATE INDEX IF NOT EXISTS vehicle_year_idx ON vehicle_inventory(build_year);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS vehicle_search_idx
ON vehicle_inventory(brand, fuel, available);

-- ============================================
-- FUNCTIONS FOR VECTOR SEARCH
-- ============================================

-- Function: Search vehicles by semantic similarity + filters
CREATE OR REPLACE FUNCTION match_vehicles(
    query_embedding vector(1536),
    max_price INT DEFAULT NULL,
    fuel_type VARCHAR DEFAULT NULL,
    max_mileage INT DEFAULT NULL,
    min_year INT DEFAULT NULL,
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id INT,
    external_id VARCHAR,
    brand VARCHAR,
    model VARCHAR,
    title TEXT,
    price INT,
    build_year INT,
    mileage INT,
    fuel VARCHAR,
    transmission VARCHAR,
    full_description TEXT,
    url TEXT,
    image_url TEXT,
    available BOOLEAN,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        v.id,
        v.external_id,
        v.brand,
        v.model,
        v.title,
        v.price,
        v.build_year,
        v.mileage,
        v.fuel,
        v.transmission,
        v.full_description,
        v.url,
        v.image_url,
        v.available,
        1 - (v.embedding <=> query_embedding) AS similarity
    FROM vehicle_inventory v
    WHERE v.available = true
        AND (max_price IS NULL OR v.price <= max_price)
        AND (fuel_type IS NULL OR v.fuel = fuel_type)
        AND (max_mileage IS NULL OR v.mileage <= max_mileage)
        AND (min_year IS NULL OR v.build_year >= min_year)
        AND (1 - (v.embedding <=> query_embedding)) > match_threshold
    ORDER BY v.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================
-- MIGRATION HELPER FUNCTION
-- ============================================

-- Function: Upsert vehicle (insert or update if exists)
CREATE OR REPLACE FUNCTION upsert_vehicle(
    p_external_id VARCHAR,
    p_brand VARCHAR,
    p_model VARCHAR,
    p_title TEXT,
    p_price INT,
    p_build_year INT,
    p_mileage INT,
    p_fuel VARCHAR,
    p_transmission VARCHAR,
    p_full_description TEXT,
    p_embedding vector(1536),
    p_url TEXT,
    p_image_url TEXT,
    p_available BOOLEAN DEFAULT true
)
RETURNS INT
LANGUAGE plpgsql
AS $$
DECLARE
    vehicle_id INT;
BEGIN
    INSERT INTO vehicle_inventory (
        external_id, brand, model, title, price, build_year, mileage,
        fuel, transmission, full_description, embedding, url, image_url, available
    )
    VALUES (
        p_external_id, p_brand, p_model, p_title, p_price, p_build_year, p_mileage,
        p_fuel, p_transmission, p_full_description, p_embedding, p_url, p_image_url, p_available
    )
    ON CONFLICT (external_id) DO UPDATE SET
        brand = EXCLUDED.brand,
        model = EXCLUDED.model,
        title = EXCLUDED.title,
        price = EXCLUDED.price,
        build_year = EXCLUDED.build_year,
        mileage = EXCLUDED.mileage,
        fuel = EXCLUDED.fuel,
        transmission = EXCLUDED.transmission,
        full_description = EXCLUDED.full_description,
        embedding = EXCLUDED.embedding,
        url = EXCLUDED.url,
        image_url = EXCLUDED.image_url,
        available = EXCLUDED.available,
        last_updated = NOW()
    RETURNING id INTO vehicle_id;

    RETURN vehicle_id;
END;
$$;

-- ============================================
-- EXAMPLE QUERIES
-- ============================================

-- Example 1: Exact brand/model search
-- SELECT * FROM vehicle_inventory
-- WHERE brand = 'Audi' AND model LIKE '%Q5%' AND fuel = 'diesel' AND available = true;

-- Example 2: Semantic search (requires embedding)
-- SELECT * FROM match_vehicles(
--     query_embedding := '[0.1, 0.2, ...]'::vector,  -- From OpenAI API
--     max_price := 50000,
--     fuel_type := 'diesel',
--     max_mileage := 150000,
--     match_threshold := 0.7,
--     match_count := 5
-- );

-- Example 3: Filter by price range
-- SELECT brand, model, price, mileage
-- FROM vehicle_inventory
-- WHERE price BETWEEN 20000 AND 40000
-- AND available = true
-- ORDER BY price ASC;

-- ============================================
-- NOTES
-- ============================================

-- 1. Embedding Generation:
--    Use OpenAI text-embedding-3-small (1536 dimensions)
--    Input: full_description = "{brand} {model} {fuel} {transmission} {features}"
--    Example: "Audi Q5 3.0 TDI quattro diesel automaat panoramadak leder navigatie"

-- 2. Vector Index (IVFFlat):
--    - Lists parameter (100) = optimal for ~10K-100K vectors
--    - For <1K vehicles (Seldenrijk): lists=10 would work too
--    - Cosine similarity: 1 = identical, 0 = opposite
--    - match_threshold=0.7 = require 70% similarity

-- 3. Migration Plan:
--    Step 1: Run this SQL in Supabase dashboard
--    Step 2: Use /app/scripts/migrate_redis_to_supabase.py to transfer data
--    Step 3: Update scraper to save directly to Supabase
--    Step 4: Remove Redis inventory code

-- 4. Maintenance:
--    - Scraper runs every 30 minutes (reduced from 2 hours)
--    - Uses upsert_vehicle() function to avoid duplicates
--    - available=false for sold vehicles (soft delete)
