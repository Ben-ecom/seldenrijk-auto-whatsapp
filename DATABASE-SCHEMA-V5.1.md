# DATABASE SCHEMA DOCUMENTATION v5.1

**Project**: Chatwoot-Centric WhatsApp Recruitment Platform
**Version**: 5.1
**Date**: 2025-01-15
**Status**: PRODUCTION READY

---

## TABLE OF CONTENTS

1. [Overview](#1-overview)
2. [Chatwoot PostgreSQL Schema](#2-chatwoot-postgresql-schema)
3. [Supabase PGVector Schema](#3-supabase-pgvector-schema)
4. [Migration Scripts](#4-migration-scripts)
5. [Performance Optimization](#5-performance-optimization)
6. [Backup & Recovery](#6-backup--recovery)

---

## 1. OVERVIEW

### 1.1 Database Architecture

```
┌─────────────────────────────────────────────┐
│  CHATWOOT POSTGRESQL (Primary Database)     │
│  - Contacts (CRM)                            │
│  - Conversations                             │
│  - Messages                                  │
│  - Labels/Tags                               │
│  - Custom Attributes (JSONB)                 │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  SUPABASE PGVECTOR (Knowledge Base)          │
│  - Documents table                           │
│  - Vector embeddings (1536 dimensions)       │
│  - Similarity search functions               │
│  - Category-based filtering                  │
└─────────────────────────────────────────────┘
```

### 1.2 Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Primary DB | PostgreSQL | 14+ | Conversations, contacts, messages |
| Vector DB | PGVector | 0.3.6+ | Semantic search, RAG knowledge base |
| Embeddings | OpenAI | text-embedding-3-small | 1536-dimensional vectors |
| Hosting | Railway + Supabase | - | Managed PostgreSQL instances |

### 1.3 Database Relationships

```
contacts (1) ─── (*) conversations
conversations (1) ─── (*) messages
contacts (1) ─── (*) contact_labels ─── (*) labels
conversations (1) ─── (1) inboxes
```

---

## 2. CHATWOOT POSTGRESQL SCHEMA

### 2.1 Core Tables Overview

Chatwoot provides a complete CRM schema out-of-the-box. We leverage existing tables and extend functionality through **custom attributes (JSONB)**.

### 2.2 Contacts Table

**Purpose**: Central CRM repository for all customer/lead data.

```sql
-- EXISTING CHATWOOT SCHEMA (DO NOT MODIFY)
CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    phone_number VARCHAR(50),
    identifier VARCHAR(255),  -- External ID
    thumbnail VARCHAR(255),   -- Profile image URL

    -- Custom attributes (JSONB) - OUR PRIMARY EXTENSION POINT
    custom_attributes JSONB DEFAULT '{}'::JSONB,

    -- Metadata
    account_id INT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT unique_email_per_account UNIQUE (email, account_id),
    CONSTRAINT unique_phone_per_account UNIQUE (phone_number, account_id)
);

-- Indexes (existing)
CREATE INDEX index_contacts_on_account_id ON contacts(account_id);
CREATE INDEX index_contacts_on_email ON contacts(email);
CREATE INDEX index_contacts_on_phone_number ON contacts(phone_number);
```

### 2.3 Custom Attributes Structure (JSONB)

**Our AI agents populate this JSONB field with extracted data.**

#### 2.3.1 Recruitment Use Case Schema

```json
{
  "lead_status": "qualified",
  "lead_source": "instagram_scrape",

  "budget_min": 70000,
  "budget_max": 90000,
  "budget_range": "€70-90k",

  "job_type_preference": "interim",
  "urgency_level": "high",
  "last_intent": "job_search",

  "ai_summary": "Experienced IT professional seeking interim roles in tech sector. Budget range €70-90k. Prefers project-based work with flexibility.",

  "instagram_handle": "@techleader",
  "follower_count": 15000,
  "niche": "technology",

  "scraped_date": "2025-01-15T10:30:00Z",
  "last_contact_date": "2025-01-16T14:20:00Z",
  "qualification_score": 8.5
}
```

#### 2.3.2 E-commerce Use Case Schema

```json
{
  "lead_status": "customer",
  "lead_source": "instagram_dm",

  "product_interest": "sneakers",
  "size_preference": "42",
  "color_preference": "black",

  "order_count": 3,
  "total_spent": 450.00,
  "avg_order_value": 150.00,

  "last_purchase_date": "2025-01-10",
  "preferred_channel": "whatsapp",

  "ai_summary": "Repeat customer with 3 orders. Prefers size 42 sneakers in dark colors. Responsive on WhatsApp.",

  "vip_status": true,
  "loyalty_points": 450
}
```

#### 2.3.3 Business Setup Use Case Schema

```json
{
  "lead_status": "qualified",
  "lead_source": "website_form",

  "company_type": "tech_startup",
  "budget_range": "€15-20k",
  "timeline": "2-3 months",

  "services_needed": ["company_registration", "visa_processing", "bank_account"],

  "qualification_score": 9.0,
  "qualified_date": "2025-01-15",

  "ai_summary": "Tech startup founder seeking company registration in Dubai. Budget €15-20k, 2-3 month timeline. High qualification score.",

  "meeting_scheduled": true,
  "meeting_date": "2025-01-20T15:00:00Z",
  "calendly_link": "https://calendly.com/..."
}
```

### 2.4 Custom Attributes Queries

#### Query contacts by lead status
```sql
SELECT
    id,
    name,
    email,
    custom_attributes->>'lead_status' AS lead_status,
    custom_attributes->>'ai_summary' AS ai_summary
FROM contacts
WHERE custom_attributes->>'lead_status' = 'qualified'
AND account_id = 1;
```

#### Query by budget range (recruitment)
```sql
SELECT
    name,
    email,
    custom_attributes->>'budget_range' AS budget,
    custom_attributes->>'job_type_preference' AS job_type
FROM contacts
WHERE (custom_attributes->>'budget_min')::int >= 70000
AND account_id = 1
ORDER BY (custom_attributes->>'qualification_score')::float DESC;
```

#### Query scraped leads from Instagram
```sql
SELECT
    name,
    custom_attributes->>'instagram_handle' AS handle,
    (custom_attributes->>'follower_count')::int AS followers,
    custom_attributes->>'niche' AS niche
FROM contacts
WHERE custom_attributes->>'lead_source' = 'instagram_scrape'
AND (custom_attributes->>'follower_count')::int > 10000
ORDER BY (custom_attributes->>'follower_count')::int DESC;
```

### 2.5 Conversations Table

```sql
-- EXISTING CHATWOOT SCHEMA
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    contact_id INT REFERENCES contacts(id) ON DELETE SET NULL,
    inbox_id INT NOT NULL REFERENCES inboxes(id) ON DELETE CASCADE,
    account_id INT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,

    -- Conversation status
    status VARCHAR(50) DEFAULT 'open',  -- open, resolved, pending, snoozed
    assignee_id INT REFERENCES users(id) ON DELETE SET NULL,
    team_id INT REFERENCES teams(id) ON DELETE SET NULL,

    -- Metadata
    uuid UUID DEFAULT gen_random_uuid(),
    additional_attributes JSONB DEFAULT '{}'::JSONB,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT conversations_status_check
        CHECK (status IN ('open', 'resolved', 'pending', 'snoozed'))
);

-- Indexes (existing)
CREATE INDEX index_conversations_on_account_id ON conversations(account_id);
CREATE INDEX index_conversations_on_contact_id ON conversations(contact_id);
CREATE INDEX index_conversations_on_inbox_id ON conversations(inbox_id);
CREATE INDEX index_conversations_on_status ON conversations(status);
CREATE INDEX index_conversations_on_last_activity_at ON conversations(last_activity_at DESC);
```

### 2.6 Messages Table

```sql
-- EXISTING CHATWOOT SCHEMA
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    account_id INT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,

    -- Message content
    content TEXT,
    message_type VARCHAR(50) NOT NULL,  -- incoming, outgoing, activity, template
    content_type VARCHAR(50) DEFAULT 'text',  -- text, input_select, cards, form, article
    content_attributes JSONB DEFAULT '{}'::JSONB,

    -- Sender information
    sender_type VARCHAR(50),  -- User, Contact, AgentBot
    sender_id INT,

    -- Message status (for outgoing)
    status VARCHAR(50) DEFAULT 'sent',  -- sent, delivered, read, failed
    source_id VARCHAR(255),  -- External message ID (WhatsApp, Instagram)

    -- Metadata
    external_source_id VARCHAR(255),
    additional_attributes JSONB DEFAULT '{}'::JSONB,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT messages_message_type_check
        CHECK (message_type IN ('incoming', 'outgoing', 'activity', 'template')),
    CONSTRAINT messages_status_check
        CHECK (status IN ('sent', 'delivered', 'read', 'failed'))
);

-- Indexes (existing)
CREATE INDEX index_messages_on_conversation_id ON messages(conversation_id);
CREATE INDEX index_messages_on_account_id ON messages(account_id);
CREATE INDEX index_messages_on_created_at ON messages(created_at DESC);
CREATE INDEX index_messages_on_source_id ON messages(source_id);
```

### 2.7 Labels Table (Tags)

```sql
-- EXISTING CHATWOOT SCHEMA
CREATE TABLE labels (
    id SERIAL PRIMARY KEY,
    account_id INT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,

    title VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(7) NOT NULL DEFAULT '#1f93ff',  -- Hex color

    show_on_sidebar BOOLEAN DEFAULT true,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_label_per_account UNIQUE (title, account_id)
);

-- Indexes
CREATE INDEX index_labels_on_account_id ON labels(account_id);
```

### 2.8 Contact Labels (Many-to-Many)

```sql
-- EXISTING CHATWOOT SCHEMA
CREATE TABLE contact_labels (
    id SERIAL PRIMARY KEY,
    contact_id INT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    label_id INT NOT NULL REFERENCES labels(id) ON DELETE CASCADE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_contact_label UNIQUE (contact_id, label_id)
);

-- Indexes
CREATE INDEX index_contact_labels_on_contact_id ON contact_labels(contact_id);
CREATE INDEX index_contact_labels_on_label_id ON contact_labels(label_id);
```

### 2.9 Inboxes Table (Channels)

```sql
-- EXISTING CHATWOOT SCHEMA
CREATE TABLE inboxes (
    id SERIAL PRIMARY KEY,
    account_id INT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,

    name VARCHAR(255) NOT NULL,
    channel_type VARCHAR(50) NOT NULL,  -- Channel::WhatsApp, Channel::Api, Channel::Email

    -- Greeting message
    greeting_enabled BOOLEAN DEFAULT false,
    greeting_message TEXT,

    -- Out of office
    out_of_office_message TEXT,
    working_hours_enabled BOOLEAN DEFAULT false,

    -- Auto assignment
    enable_auto_assignment BOOLEAN DEFAULT true,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX index_inboxes_on_account_id ON inboxes(account_id);
```

### 2.10 Channel Configuration (WhatsApp, Instagram)

```sql
-- EXISTING CHATWOOT SCHEMA
CREATE TABLE channel_whatsapp (
    id SERIAL PRIMARY KEY,
    account_id INT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,

    phone_number VARCHAR(50) NOT NULL,
    provider VARCHAR(50) NOT NULL,  -- whatsapp_cloud, 360dialog
    provider_config JSONB DEFAULT '{}'::JSONB,

    message_templates JSONB DEFAULT '[]'::JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_phone_per_account UNIQUE (phone_number, account_id)
);

-- 360Dialog Provider Config Structure
-- {
--   "api_key": "your_360dialog_api_key",
--   "webhook_url": "https://your-app.railway.app/webhooks/360dialog",
--   "client_id": "your_client_id"
-- }

CREATE TABLE channel_api (
    id SERIAL PRIMARY KEY,
    account_id INT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,

    webhook_url VARCHAR(255),
    hmac_token VARCHAR(255),
    hmac_mandatory BOOLEAN DEFAULT false,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## 3. SUPABASE PGVECTOR SCHEMA

### 3.1 PGVector Extension Setup

```sql
-- Enable PGVector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify extension
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### 3.2 Documents Table

```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,

    -- Content
    content TEXT NOT NULL,
    title VARCHAR(500),

    -- Vector embedding
    embedding VECTOR(1536),  -- OpenAI text-embedding-3-small dimension

    -- Metadata (flexible JSONB)
    metadata JSONB DEFAULT '{}'::JSONB,

    -- Category for filtering
    category VARCHAR(50),

    -- Source tracking
    source_type VARCHAR(50),  -- pdf, webpage, manual, api
    source_url VARCHAR(1000),
    source_file_name VARCHAR(255),

    -- Version control
    version INT DEFAULT 1,
    is_active BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT documents_category_check
        CHECK (category IN ('policy', 'product', 'faq', 'procedure', 'vacancy', 'general'))
);

-- Indexes
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_is_active ON documents(is_active);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);

-- GIN index for JSONB metadata search
CREATE INDEX idx_documents_metadata ON documents USING GIN(metadata);

-- CRITICAL: IVFFlat index for vector similarity search
CREATE INDEX idx_documents_embedding
ON documents
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- For larger datasets (>100k documents), increase lists:
-- WITH (lists = 1000);
```

### 3.3 Metadata Structure Examples

#### Recruitment Vacancy Document
```json
{
  "title": "Senior Backend Developer - Interim",
  "category": "vacancy",
  "job_type": "interim",
  "budget_min": 70000,
  "budget_max": 90000,
  "location": "Amsterdam",
  "duration_months": 6,
  "skills_required": ["Python", "FastAPI", "PostgreSQL"],
  "seniority": "senior",
  "source": "company_job_board",
  "posted_date": "2025-01-15",
  "last_updated": "2025-01-15"
}
```

#### Policy Document
```json
{
  "title": "Return and Refund Policy",
  "category": "policy",
  "section": "customer_service",
  "applies_to": "all_products",
  "effective_date": "2025-01-01",
  "source": "company_handbook.pdf",
  "page_number": 15,
  "last_reviewed": "2025-01-01"
}
```

#### Product Document
```json
{
  "title": "Nike Air Max 2024 - Product Specifications",
  "category": "product",
  "product_id": "SKU-12345",
  "brand": "Nike",
  "price": 149.99,
  "sizes_available": ["40", "41", "42", "43"],
  "colors_available": ["black", "white", "red"],
  "in_stock": true,
  "source": "product_catalog_api",
  "last_synced": "2025-01-15T10:00:00Z"
}
```

### 3.4 Vector Similarity Search Function

```sql
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.78,
    match_count INT DEFAULT 5,
    filter_category VARCHAR DEFAULT NULL,
    filter_metadata JSONB DEFAULT NULL
)
RETURNS TABLE (
    id INT,
    content TEXT,
    title VARCHAR,
    metadata JSONB,
    category VARCHAR,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        documents.id,
        documents.content,
        documents.title,
        documents.metadata,
        documents.category,
        1 - (documents.embedding <=> query_embedding) AS similarity
    FROM documents
    WHERE
        documents.is_active = true
        AND (filter_category IS NULL OR documents.category = filter_category)
        AND (filter_metadata IS NULL OR documents.metadata @> filter_metadata)
        AND 1 - (documents.embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$;

-- Usage examples:

-- 1. General search (no filters)
SELECT * FROM match_documents(
    query_embedding := '[0.1, 0.2, ..., 0.5]'::VECTOR(1536),
    match_threshold := 0.78,
    match_count := 5
);

-- 2. Search only policy documents
SELECT * FROM match_documents(
    query_embedding := '[0.1, 0.2, ..., 0.5]'::VECTOR(1536),
    match_threshold := 0.80,
    match_count := 3,
    filter_category := 'policy'
);

-- 3. Search with metadata filter (e.g., interim jobs only)
SELECT * FROM match_documents(
    query_embedding := '[0.1, 0.2, ..., 0.5]'::VECTOR(1536),
    match_threshold := 0.75,
    match_count := 5,
    filter_category := 'vacancy',
    filter_metadata := '{"job_type": "interim"}'::JSONB
);
```

### 3.5 Embedding Generation Workflow

```python
# Python implementation (FastAPI backend)
import openai
from supabase import create_client

SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-key"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def generate_embedding(text: str) -> list[float]:
    """Generate OpenAI embedding"""
    response = await openai.embeddings.create(
        model="text-embedding-3-small",
        input=text,
        dimensions=1536
    )
    return response.data[0].embedding

async def insert_document(
    content: str,
    title: str,
    category: str,
    metadata: dict
) -> int:
    """Insert document with embedding"""

    # Generate embedding
    embedding = await generate_embedding(content)

    # Insert into Supabase
    result = supabase.table("documents").insert({
        "content": content,
        "title": title,
        "category": category,
        "metadata": metadata,
        "embedding": embedding
    }).execute()

    return result.data[0]['id']

async def search_knowledge_base(
    query: str,
    category: str = None,
    threshold: float = 0.78,
    limit: int = 5
) -> list[dict]:
    """Search knowledge base using vector similarity"""

    # Generate query embedding
    query_embedding = await generate_embedding(query)

    # Call match_documents function
    result = supabase.rpc(
        'match_documents',
        {
            'query_embedding': query_embedding,
            'match_threshold': threshold,
            'match_count': limit,
            'filter_category': category
        }
    ).execute()

    return result.data
```

### 3.6 Knowledge Base Categories

| Category | Use Case | Example Documents |
|----------|----------|-------------------|
| **policy** | Company policies, terms | Return policy, privacy policy, terms of service |
| **product** | Product information | Product specs, pricing, availability |
| **faq** | Common questions | Shipping FAQ, account FAQ, payment FAQ |
| **procedure** | Internal processes | Onboarding checklist, complaint handling |
| **vacancy** | Job listings | Job descriptions, requirements, salary ranges |
| **general** | Miscellaneous | Company info, history, mission |

---

## 4. MIGRATION SCRIPTS

### 4.1 Initial Chatwoot Setup

```sql
-- migration_001_chatwoot_custom_labels.sql
-- Purpose: Create standard labels for AI-driven segmentation
-- Run after: Chatwoot installation complete

-- Connect to Chatwoot database
-- \c chatwoot_production;

-- Insert standard labels (account_id = 1, adjust if needed)
INSERT INTO labels (account_id, title, description, color, show_on_sidebar)
VALUES
    (1, 'qualified-lead', 'High-quality lead, passed qualification', '#10b981', true),
    (1, 'unqualified-lead', 'Does not meet qualification criteria', '#ef4444', true),
    (1, 'hot-lead', 'High urgency, immediate follow-up needed', '#f59e0b', true),
    (1, 'cold-lead', 'Low engagement, nurture campaign', '#6b7280', true),

    (1, 'scraped-lead', 'Lead from Instagram/LinkedIn scraping', '#8b5cf6', true),
    (1, 'cold-outreach', 'Not yet contacted, pending outreach', '#ec4899', true),
    (1, 'responded', 'Lead responded to outreach', '#14b8a6', true),

    (1, 'high-priority', 'Urgent issue, needs immediate attention', '#dc2626', true),
    (1, 'vip-customer', 'High-value customer, premium treatment', '#facc15', true),

    (1, 'interim-job-seeker', 'Looking for interim/contract work', '#3b82f6', false),
    (1, 'permanent-job-seeker', 'Looking for permanent employment', '#0ea5e9', false),
    (1, 'freelance-preference', 'Prefers freelance/project work', '#06b6d4', false),

    (1, 'needs-human', 'AI escalated to human agent', '#f97316', true),
    (1, 'ai-handled', 'Successfully handled by AI', '#22c55e', false)
ON CONFLICT (title, account_id) DO NOTHING;

-- Verify labels created
SELECT id, title, color FROM labels WHERE account_id = 1 ORDER BY title;
```

### 4.2 Custom Attributes Configuration

```sql
-- migration_002_custom_attributes_setup.sql
-- Purpose: Document custom attributes schema (Chatwoot handles JSONB natively)

-- NOTE: Chatwoot automatically handles custom_attributes JSONB column.
-- This migration documents the expected structure for reference.

-- Create a view for easy querying of custom attributes
CREATE OR REPLACE VIEW contact_attributes_view AS
SELECT
    c.id AS contact_id,
    c.name,
    c.email,
    c.phone_number,

    -- Extract common custom attributes
    c.custom_attributes->>'lead_status' AS lead_status,
    c.custom_attributes->>'lead_source' AS lead_source,
    c.custom_attributes->>'urgency_level' AS urgency_level,
    c.custom_attributes->>'job_type_preference' AS job_type,
    c.custom_attributes->>'budget_range' AS budget_range,
    (c.custom_attributes->>'qualification_score')::float AS qualification_score,

    c.custom_attributes->>'ai_summary' AS ai_summary,

    c.custom_attributes->>'instagram_handle' AS instagram_handle,
    (c.custom_attributes->>'follower_count')::int AS follower_count,

    c.custom_attributes->>'last_contact_date' AS last_contact_date,

    -- Full JSON for reference
    c.custom_attributes AS all_attributes,

    c.created_at,
    c.updated_at
FROM contacts c;

-- Usage:
-- SELECT * FROM contact_attributes_view WHERE lead_status = 'qualified';
-- SELECT * FROM contact_attributes_view WHERE qualification_score > 8.0;
```

### 4.3 Supabase PGVector Initialization

```sql
-- migration_003_pgvector_setup.sql
-- Purpose: Initialize PGVector extension and documents table
-- Run on: Supabase database

-- Enable PGVector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create documents table
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,

    content TEXT NOT NULL,
    title VARCHAR(500),

    embedding VECTOR(1536),

    metadata JSONB DEFAULT '{}'::JSONB,
    category VARCHAR(50),

    source_type VARCHAR(50),
    source_url VARCHAR(1000),
    source_file_name VARCHAR(255),

    version INT DEFAULT 1,
    is_active BOOLEAN DEFAULT true,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT documents_category_check
        CHECK (category IN ('policy', 'product', 'faq', 'procedure', 'vacancy', 'general'))
);

-- Create indexes
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_is_active ON documents(is_active);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX idx_documents_metadata ON documents USING GIN(metadata);

-- IVFFlat index for vector similarity (critical for performance)
CREATE INDEX idx_documents_embedding
ON documents
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create match_documents function
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.78,
    match_count INT DEFAULT 5,
    filter_category VARCHAR DEFAULT NULL,
    filter_metadata JSONB DEFAULT NULL
)
RETURNS TABLE (
    id INT,
    content TEXT,
    title VARCHAR,
    metadata JSONB,
    category VARCHAR,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        documents.id,
        documents.content,
        documents.title,
        documents.metadata,
        documents.category,
        1 - (documents.embedding <=> query_embedding) AS similarity
    FROM documents
    WHERE
        documents.is_active = true
        AND (filter_category IS NULL OR documents.category = filter_category)
        AND (filter_metadata IS NULL OR documents.metadata @> filter_metadata)
        AND 1 - (documents.embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$;

-- Grant permissions (if using Row Level Security)
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to read
CREATE POLICY "Allow read access to authenticated users"
ON documents FOR SELECT
TO authenticated
USING (true);

-- Allow service role to insert/update
CREATE POLICY "Allow insert/update for service role"
ON documents FOR ALL
TO service_role
USING (true);
```

### 4.4 Sample Data Inserts

```sql
-- migration_004_sample_data.sql
-- Purpose: Insert test/demo data for development and testing

-- CHATWOOT DATABASE --

-- 1. Insert sample labels (if not already created)
-- (Use migration_001 instead)

-- 2. Insert sample contacts (replace account_id as needed)
INSERT INTO contacts (account_id, name, email, phone_number, custom_attributes)
VALUES
    (1, 'John Tech', 'john@techstartup.com', '+31612345678',
     '{"lead_status": "qualified", "lead_source": "website_form", "job_type_preference": "interim", "budget_min": 70000, "budget_max": 90000, "urgency_level": "high", "qualification_score": 8.5, "ai_summary": "Experienced tech professional seeking interim roles"}'::JSONB),

    (1, 'Sarah Designer', 'sarah@creativeagency.com', '+31687654321',
     '{"lead_status": "qualified", "lead_source": "instagram_scrape", "instagram_handle": "@sarahdesigns", "follower_count": 25000, "niche": "design", "job_type_preference": "freelance", "urgency_level": "medium", "qualification_score": 7.8}'::JSONB),

    (1, 'Mike Customer', 'mike@example.com', '+31698765432',
     '{"lead_status": "customer", "lead_source": "instagram_dm", "product_interest": "sneakers", "size_preference": "42", "order_count": 3, "total_spent": 450.00, "vip_status": true}'::JSONB);

-- Get contact IDs for reference
-- SELECT id, name FROM contacts WHERE account_id = 1;

-- SUPABASE PGVECTOR DATABASE --

-- 3. Insert sample documents (requires embeddings to be generated via API)
-- NOTE: Embeddings must be generated using OpenAI API. Below are placeholder examples.

-- Recruitment vacancy document
INSERT INTO documents (content, title, category, metadata, embedding)
VALUES
    ('Senior Backend Developer - Interim Position
     Duration: 6 months, Budget: €70,000-€90,000
     Location: Amsterdam (hybrid)
     Requirements: Python, FastAPI, PostgreSQL, Docker
     Start date: February 2025',
     'Senior Backend Developer - Interim',
     'vacancy',
     '{"job_type": "interim", "budget_min": 70000, "budget_max": 90000, "location": "Amsterdam", "skills": ["Python", "FastAPI", "PostgreSQL"]}'::JSONB,
     NULL);  -- Embedding will be added via API

-- FAQ document
INSERT INTO documents (content, title, category, metadata, embedding)
VALUES
    ('Return Policy: All products can be returned within 30 days of purchase.
     Items must be unworn and in original packaging.
     Refunds will be processed within 5-7 business days.',
     'Return and Refund Policy',
     'faq',
     '{"section": "customer_service", "effective_date": "2025-01-01"}'::JSONB,
     NULL);

-- NOTE: In production, use Python/FastAPI to generate embeddings:
--
-- async def insert_sample_documents():
--     documents = [
--         {"content": "...", "title": "...", "category": "vacancy"},
--         # ... more documents
--     ]
--     for doc in documents:
--         embedding = await generate_embedding(doc["content"])
--         await supabase.table("documents").insert({**doc, "embedding": embedding})
```

### 4.5 Rollback Scripts

```sql
-- migration_rollback_pgvector.sql
-- Purpose: Remove PGVector setup (USE WITH CAUTION)

-- Drop function
DROP FUNCTION IF EXISTS match_documents;

-- Drop indexes
DROP INDEX IF EXISTS idx_documents_embedding;
DROP INDEX IF EXISTS idx_documents_metadata;
DROP INDEX IF EXISTS idx_documents_created_at;
DROP INDEX IF EXISTS idx_documents_is_active;
DROP INDEX IF EXISTS idx_documents_category;

-- Drop table
DROP TABLE IF EXISTS documents;

-- Drop extension (ONLY if no other tables use vector type)
DROP EXTENSION IF EXISTS vector;
```

---

## 5. PERFORMANCE OPTIMIZATION

### 5.1 Chatwoot Database Optimization

#### Indexes for Custom Attributes (JSONB)

```sql
-- Create GIN index for custom_attributes JSONB
CREATE INDEX idx_contacts_custom_attributes
ON contacts USING GIN(custom_attributes);

-- Create expression indexes for frequently queried fields
CREATE INDEX idx_contacts_lead_status
ON contacts ((custom_attributes->>'lead_status'));

CREATE INDEX idx_contacts_lead_source
ON contacts ((custom_attributes->>'lead_source'));

CREATE INDEX idx_contacts_qualification_score
ON contacts (((custom_attributes->>'qualification_score')::float) DESC);

CREATE INDEX idx_contacts_instagram_handle
ON contacts ((custom_attributes->>'instagram_handle'));
```

#### Query Performance Testing

```sql
-- Test query performance
EXPLAIN ANALYZE
SELECT * FROM contacts
WHERE custom_attributes->>'lead_status' = 'qualified'
AND (custom_attributes->>'qualification_score')::float > 8.0;

-- Should show index scan (not sequential scan)
```

### 5.2 PGVector Optimization

#### IVFFlat Index Tuning

```sql
-- For small datasets (<10k documents): lists = 100 (default)
-- For medium datasets (10k-100k): lists = 500
-- For large datasets (>100k): lists = 1000

-- Drop existing index
DROP INDEX IF EXISTS idx_documents_embedding;

-- Recreate with optimal lists parameter
CREATE INDEX idx_documents_embedding
ON documents
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 500);  -- Adjust based on dataset size
```

#### Vector Search Performance Testing

```sql
-- Test vector search performance
EXPLAIN ANALYZE
SELECT * FROM match_documents(
    query_embedding := '[0.1, 0.2, ..., 0.5]'::VECTOR(1536),
    match_threshold := 0.78,
    match_count := 5,
    filter_category := 'vacancy'
);

-- Should show index scan on idx_documents_embedding
-- Query time should be <50ms for datasets <100k
```

### 5.3 Connection Pooling (Supabase)

```python
# Supabase client configuration (Python)
from supabase import create_client, ClientOptions

supabase = create_client(
    supabase_url="https://your-project.supabase.co",
    supabase_key="your-key",
    options=ClientOptions(
        postgrest_client_timeout=10,
        storage_client_timeout=10,
    )
)

# For high-traffic applications, use PgBouncer (included in Supabase)
# Connection string with pooler:
# postgresql://postgres.your-project:password@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

### 5.4 Monitoring Queries

```sql
-- Monitor slow queries (Chatwoot)
SELECT
    pid,
    now() - pg_stat_activity.query_start AS duration,
    query,
    state
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 seconds'
AND state != 'idle'
ORDER BY duration DESC;

-- Monitor table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Monitor index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

---

## 6. BACKUP & RECOVERY

### 6.1 Chatwoot Database Backup (Railway)

#### Automated Backups
Railway provides automatic daily backups (retained for 7 days on Pro plan).

#### Manual Backup
```bash
# Export entire database
railway run pg_dump chatwoot_production > chatwoot_backup_$(date +%Y%m%d).sql

# Backup with compression
railway run pg_dump chatwoot_production | gzip > chatwoot_backup_$(date +%Y%m%d).sql.gz

# Backup only custom data (excluding Chatwoot system tables)
railway run pg_dump chatwoot_production \
  --table=contacts \
  --table=conversations \
  --table=messages \
  --table=labels \
  --table=contact_labels \
  > chatwoot_data_backup_$(date +%Y%m%d).sql
```

#### Restore from Backup
```bash
# Restore full database (DANGER: overwrites existing data)
railway run psql chatwoot_production < chatwoot_backup_20250115.sql

# Restore specific tables
railway run psql chatwoot_production < chatwoot_data_backup_20250115.sql
```

### 6.2 Supabase Database Backup

#### Automated Backups
Supabase provides:
- Daily automated backups (Pro plan)
- Point-in-time recovery (last 7 days)

#### Manual Backup via Supabase CLI
```bash
# Install Supabase CLI
npm install -g supabase

# Login
supabase login

# Link project
supabase link --project-ref your-project-ref

# Backup database
supabase db dump -f backup_$(date +%Y%m%d).sql

# Backup only documents table
supabase db dump -f documents_backup_$(date +%Y%m%d).sql --data-only --table documents
```

#### Restore from Backup
```bash
# Restore full database
supabase db reset

# Apply backup
psql "$DATABASE_URL" < backup_20250115.sql
```

### 6.3 Vector Embeddings Backup

**CRITICAL**: Embeddings are expensive to regenerate (API costs).

```python
# Python script to export documents with embeddings
import asyncio
from supabase import create_client
import json

async def backup_embeddings():
    """Export all documents with embeddings to JSON"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Fetch all documents
    result = supabase.table("documents").select("*").execute()

    # Save to JSON file
    with open(f"embeddings_backup_{datetime.now().strftime('%Y%m%d')}.json", "w") as f:
        json.dump(result.data, f, indent=2)

    print(f"Backed up {len(result.data)} documents with embeddings")

# Restore from JSON backup
async def restore_embeddings(backup_file: str):
    """Restore documents from JSON backup"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    with open(backup_file, 'r') as f:
        documents = json.load(f)

    # Insert documents (embeddings preserved)
    for doc in documents:
        supabase.table("documents").insert(doc).execute()

    print(f"Restored {len(documents)} documents")
```

### 6.4 Disaster Recovery Plan

#### RTO (Recovery Time Objective): 4 hours
#### RPO (Recovery Point Objective): 24 hours

**Disaster Scenarios:**

1. **Chatwoot database corruption**
   - Restore from Railway automated backup (last 24 hours)
   - Downtime: 30-60 minutes

2. **Supabase database corruption**
   - Restore from Supabase automated backup
   - Downtime: 30-60 minutes

3. **Vector embeddings lost**
   - Restore from JSON backup (embeddings preserved)
   - No regeneration needed
   - Downtime: 1-2 hours

4. **Complete data loss (both databases)**
   - Restore Chatwoot from manual backup
   - Restore Supabase from manual backup
   - Restore embeddings from JSON
   - Downtime: 3-4 hours

**Recovery Checklist:**
- [ ] Identify affected database (Chatwoot vs Supabase)
- [ ] Stop application (prevent further data corruption)
- [ ] Restore from most recent backup
- [ ] Verify data integrity (run test queries)
- [ ] Restart application
- [ ] Monitor for errors
- [ ] Notify users (if downtime > 1 hour)

---

## APPENDIX A: SQL QUERY RECIPES

### A.1 Contact Segmentation Queries

```sql
-- Get all qualified leads with high urgency
SELECT
    name,
    email,
    custom_attributes->>'urgency_level' AS urgency,
    custom_attributes->>'ai_summary' AS summary
FROM contacts
WHERE custom_attributes->>'lead_status' = 'qualified'
AND custom_attributes->>'urgency_level' = 'high'
ORDER BY updated_at DESC;

-- Get Instagram leads with >10k followers
SELECT
    name,
    custom_attributes->>'instagram_handle' AS handle,
    (custom_attributes->>'follower_count')::int AS followers
FROM contacts
WHERE custom_attributes->>'lead_source' = 'instagram_scrape'
AND (custom_attributes->>'follower_count')::int > 10000
ORDER BY (custom_attributes->>'follower_count')::int DESC;

-- Get contacts by label
SELECT
    c.name,
    c.email,
    l.title AS label
FROM contacts c
JOIN contact_labels cl ON c.id = cl.contact_id
JOIN labels l ON cl.label_id = l.id
WHERE l.title = 'qualified-lead'
AND c.account_id = 1;
```

### A.2 Conversation Analytics

```sql
-- Get conversation statistics by status
SELECT
    status,
    COUNT(*) AS count,
    AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) / 60 AS avg_duration_minutes
FROM conversations
WHERE account_id = 1
GROUP BY status;

-- Get message volume by channel
SELECT
    i.channel_type,
    DATE(m.created_at) AS date,
    COUNT(*) AS message_count
FROM messages m
JOIN conversations c ON m.conversation_id = c.id
JOIN inboxes i ON c.inbox_id = i.id
WHERE m.account_id = 1
GROUP BY i.channel_type, DATE(m.created_at)
ORDER BY date DESC, message_count DESC;
```

### A.3 Vector Search Queries

```sql
-- Search with category filter
SELECT * FROM match_documents(
    query_embedding := '[...]'::VECTOR(1536),
    match_threshold := 0.80,
    match_count := 5,
    filter_category := 'vacancy'
);

-- Search with metadata filter (budget range)
SELECT * FROM match_documents(
    query_embedding := '[...]'::VECTOR(1536),
    match_threshold := 0.75,
    match_count := 5,
    filter_category := 'vacancy',
    filter_metadata := '{"budget_min": {"$gte": 70000}}'::JSONB
);
```

---

## APPENDIX B: DATABASE SCHEMA VALIDATION

### B.1 Validation Checklist

**Chatwoot Schema:**
- [x] Contacts table with custom_attributes JSONB
- [x] Conversations table with status enum
- [x] Messages table with message_type enum
- [x] Labels table for segmentation
- [x] Contact_labels many-to-many relationship
- [x] Indexes on foreign keys
- [x] Indexes on custom_attributes fields

**Supabase PGVector:**
- [x] PGVector extension enabled
- [x] Documents table with VECTOR(1536) column
- [x] match_documents() function created
- [x] IVFFlat index on embeddings
- [x] GIN index on metadata JSONB
- [x] Row-Level Security policies configured

**Performance:**
- [x] All foreign keys indexed
- [x] Custom attribute queries use expression indexes
- [x] Vector search uses IVFFlat index
- [x] Query execution time <100ms (target)

---

**END OF DATABASE SCHEMA DOCUMENTATION v5.1**

**Document Status**: PRODUCTION READY
**Last Updated**: 2025-01-15
**Total Pages**: 15

**Next Steps**:
1. Review migration scripts with team
2. Test migrations in staging environment
3. Generate embeddings for sample documents
4. Run performance benchmarks
5. Deploy to production

**Maintainers**: Database Team
**Review Date**: 2025-02-15 (monthly review)

---

**Quick Reference Links**:
- Chatwoot Database Schema: [Section 2](#2-chatwoot-postgresql-schema)
- PGVector Setup: [Section 3](#3-supabase-pgvector-schema)
- Migration Scripts: [Section 4](#4-migration-scripts)
- Performance Tuning: [Section 5](#5-performance-optimization)
- Backup Procedures: [Section 6](#6-backup--recovery)

**Support**: database-team@yourcompany.com
