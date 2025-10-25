"""
Setup Supabase Schema - Execute SQL via Python client
"""
import os
from supabase import create_client, Client

# Supabase credentials from .env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ SUPABASE_URL or SUPABASE_KEY not set in .env")

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("🚀 Setting up Supabase schema...")
print("=" * 60)

# SQL statements (broken into parts for RPC execution)
sql_statements = [
    # 1. Enable pgvector extension
    """
    CREATE EXTENSION IF NOT EXISTS vector;
    """,

    # 2. Create vehicle_inventory table
    """
    CREATE TABLE IF NOT EXISTS vehicle_inventory (
        id SERIAL PRIMARY KEY,
        external_id VARCHAR(255) UNIQUE NOT NULL,
        brand VARCHAR(100) NOT NULL,
        model VARCHAR(100) NOT NULL,
        title TEXT NOT NULL,
        price INTEGER NOT NULL,
        build_year INTEGER,
        mileage INTEGER,
        fuel VARCHAR(50),
        transmission VARCHAR(50),
        full_description TEXT,
        embedding vector(1536),
        url TEXT NOT NULL,
        image_url TEXT,
        available BOOLEAN DEFAULT true,
        scraped_at TIMESTAMP DEFAULT NOW(),
        last_updated TIMESTAMP DEFAULT NOW(),
        created_at TIMESTAMP DEFAULT NOW()
    );
    """,

    # 3. Vector similarity index
    """
    CREATE INDEX IF NOT EXISTS vehicle_embedding_idx
    ON vehicle_inventory
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
    """,

    # 4. Other indexes
    """
    CREATE INDEX IF NOT EXISTS vehicle_brand_idx ON vehicle_inventory(brand);
    CREATE INDEX IF NOT EXISTS vehicle_model_idx ON vehicle_inventory(model);
    CREATE INDEX IF NOT EXISTS vehicle_fuel_idx ON vehicle_inventory(fuel);
    CREATE INDEX IF NOT EXISTS vehicle_available_idx ON vehicle_inventory(available);
    CREATE INDEX IF NOT EXISTS vehicle_price_idx ON vehicle_inventory(price);
    CREATE INDEX IF NOT EXISTS vehicle_mileage_idx ON vehicle_inventory(mileage);
    CREATE INDEX IF NOT EXISTS vehicle_year_idx ON vehicle_inventory(build_year);
    CREATE INDEX IF NOT EXISTS vehicle_search_idx ON vehicle_inventory(brand, fuel, available);
    """,

    # 5. match_vehicles function
    """
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
    """,

    # 6. upsert_vehicle function
    """
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
    """
]

# Execute each SQL statement
for idx, sql in enumerate(sql_statements, 1):
    try:
        print(f"\n{idx}. Executing SQL statement...")
        result = supabase.rpc("exec", {"query": sql}).execute()
        print(f"   ✅ Statement {idx} succeeded")
    except Exception as e:
        print(f"   ⚠️ Statement {idx} failed (may already exist): {e}")

print("\n" + "=" * 60)
print("✅ Supabase schema setup complete!")
print("\nNext steps:")
print("1. Run scraper to populate data")
print("2. Test vector search")
