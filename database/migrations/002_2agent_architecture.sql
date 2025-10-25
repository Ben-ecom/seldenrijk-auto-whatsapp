-- =====================================================
-- MIGRATION 002: 2-AGENT ARCHITECTURE TABLES
-- Adds support for Pydantic AI + Claude SDK agents
-- =====================================================

-- ============ AGENT 1: QUALIFICATIONS (Pydantic AI Output) ============
CREATE TABLE qualifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE UNIQUE,

    -- Structured Extraction Results
    full_name TEXT,
    years_experience INTEGER CHECK (years_experience >= 0 AND years_experience <= 50),
    skills TEXT[] DEFAULT '{}',

    -- Scoring (0-100 scale)
    technical_score INTEGER CHECK (technical_score BETWEEN 0 AND 40),
    soft_skills_score INTEGER CHECK (soft_skills_score BETWEEN 0 AND 40),
    experience_score INTEGER CHECK (experience_score BETWEEN 0 AND 20),
    overall_score INTEGER CHECK (overall_score BETWEEN 0 AND 100),

    -- Status
    qualification_status TEXT NOT NULL CHECK (qualification_status IN ('qualified', 'disqualified', 'pending_review')),
    disqualification_reason TEXT, -- If disqualified
    missing_info TEXT[] DEFAULT '{}', -- What info is still needed

    -- Metadata
    extraction_confidence DECIMAL(3,2) CHECK (extraction_confidence BETWEEN 0.0 AND 1.0),
    model_used TEXT DEFAULT 'gpt-4o-mini',
    extracted_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_qualifications_lead ON qualifications(lead_id);
CREATE INDEX idx_qualifications_status ON qualifications(qualification_status);
CREATE INDEX idx_qualifications_score ON qualifications(overall_score DESC);

-- ============ AGENT 2: TOOLS LOG (Claude SDK Audit Trail) ============
CREATE TABLE tools_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id), -- Which message triggered the tool

    -- Tool Execution Details
    tool_name TEXT NOT NULL CHECK (tool_name IN (
        'search_job_postings',
        'search_company_docs',
        'check_calendar_availability',
        'escalate_to_human'
    )),
    tool_input JSONB NOT NULL, -- Input parameters
    tool_output TEXT, -- Result (can be large)

    -- Performance
    execution_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,

    -- Metadata
    agent_version TEXT DEFAULT 'claude-3-5-sonnet-20241022',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tools_log_lead ON tools_log(lead_id);
CREATE INDEX idx_tools_log_tool_name ON tools_log(tool_name);
CREATE INDEX idx_tools_log_created ON tools_log(created_at DESC);

-- ============ RAG: JOB POSTINGS EMBEDDINGS ============
CREATE TABLE job_postings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Job Details
    title TEXT NOT NULL,
    location TEXT NOT NULL,
    job_type TEXT CHECK (job_type IN ('fulltime', 'parttime', 'freelance')),
    salary_range TEXT,

    -- Full Content
    description TEXT NOT NULL,
    requirements TEXT NOT NULL,
    benefits TEXT,

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    posted_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_job_postings_active ON job_postings(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_job_postings_location ON job_postings(location);

-- Embeddings (chunks for better semantic search)
CREATE TABLE job_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_posting_id UUID NOT NULL REFERENCES job_postings(id) ON DELETE CASCADE,

    -- Chunk Details
    chunk_text TEXT NOT NULL, -- 500-1000 chars per chunk
    chunk_type TEXT CHECK (chunk_type IN ('title', 'description', 'requirements', 'benefits')),
    chunk_index INTEGER NOT NULL, -- Order within job posting

    -- Vector Embedding
    embedding VECTOR(1536) NOT NULL, -- OpenAI text-embedding-3-small

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_job_embeddings_job ON job_embeddings(job_posting_id);
CREATE INDEX idx_job_embeddings_vector ON job_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ============ RAG: COMPANY DOCS EMBEDDINGS ============
CREATE TABLE company_docs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Document Details
    title TEXT NOT NULL,
    doc_type TEXT CHECK (doc_type IN ('faq', 'policy', 'benefits', 'culture', 'process')),
    content TEXT NOT NULL,

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    last_updated TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_company_docs_type ON company_docs(doc_type);
CREATE INDEX idx_company_docs_active ON company_docs(is_active) WHERE is_active = TRUE;

-- Embeddings
CREATE TABLE company_doc_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id UUID NOT NULL REFERENCES company_docs(id) ON DELETE CASCADE,

    -- Chunk Details
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,

    -- Vector Embedding
    embedding VECTOR(1536) NOT NULL,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_company_doc_embeddings_doc ON company_doc_embeddings(doc_id);
CREATE INDEX idx_company_doc_embeddings_vector ON company_doc_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

-- ============ VECTOR SEARCH FUNCTIONS ============

-- Search job postings by semantic similarity
CREATE OR REPLACE FUNCTION vector_search_jobs(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 3
)
RETURNS TABLE (
    job_id UUID,
    title TEXT,
    location TEXT,
    job_type TEXT,
    chunk_text TEXT,
    chunk_type TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        jp.id AS job_id,
        jp.title,
        jp.location,
        jp.job_type,
        je.chunk_text,
        je.chunk_type,
        1 - (je.embedding <=> query_embedding) AS similarity
    FROM job_embeddings je
    JOIN job_postings jp ON je.job_posting_id = jp.id
    WHERE
        jp.is_active = TRUE
        AND 1 - (je.embedding <=> query_embedding) > match_threshold
    ORDER BY je.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Search company docs by semantic similarity
CREATE OR REPLACE FUNCTION vector_search_company_docs(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 3
)
RETURNS TABLE (
    doc_id UUID,
    title TEXT,
    doc_type TEXT,
    chunk_text TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        cd.id AS doc_id,
        cd.title,
        cd.doc_type,
        cde.chunk_text,
        1 - (cde.embedding <=> query_embedding) AS similarity
    FROM company_doc_embeddings cde
    JOIN company_docs cd ON cde.doc_id = cd.id
    WHERE
        cd.is_active = TRUE
        AND 1 - (cde.embedding <=> query_embedding) > match_threshold
    ORDER BY cde.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============ AGENT STATE TRACKING ============
-- Update agent_checkpoints table to support 2-agent system
ALTER TABLE agent_checkpoints ADD COLUMN IF NOT EXISTS agent_type TEXT CHECK (agent_type IN ('pydantic_ai', 'claude_sdk'));
ALTER TABLE agent_checkpoints ADD COLUMN IF NOT EXISTS last_extraction_at TIMESTAMP;
ALTER TABLE agent_checkpoints ADD COLUMN IF NOT EXISTS last_conversation_at TIMESTAMP;

-- ============ SAMPLE DATA FOR TESTING ============

-- Sample job posting
INSERT INTO job_postings (title, location, job_type, salary_range, description, requirements, benefits)
VALUES (
    'Senior Hairstylist',
    'Amsterdam',
    'fulltime',
    '€2500-€3500/maand',
    'We zoeken een ervaren kapper met passie voor klantcontact en moderne technieken. Je werkt in ons salon in Amsterdam centrum.',
    'Minimaal 3 jaar ervaring, kennis van kleuren en knippen, uitstekende klantvaardigheden',
    'Doorgroeimogelijkheden, opleidingsbudget, 25 vakantiedagen, pensioenregeling'
);

-- Sample company doc (FAQ)
INSERT INTO company_docs (title, doc_type, content)
VALUES (
    'Sollicitatieprocedure',
    'faq',
    'Onze sollicitatieprocedure bestaat uit 3 stappen: 1) WhatsApp screening, 2) Video kennismaking (30 min), 3) Proefdag in het salon. De hele procedure duurt ongeveer 1-2 weken.'
);

-- ============ TRIGGERS FOR UPDATED_AT ============
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_qualifications_updated_at
    BEFORE UPDATE ON qualifications
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_job_postings_updated_at
    BEFORE UPDATE ON job_postings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============ COMMENTS FOR DOCUMENTATION ============
COMMENT ON TABLE qualifications IS 'Structured extraction results from Agent 1 (Pydantic AI)';
COMMENT ON TABLE tools_log IS 'Audit trail of tool executions by Agent 2 (Claude SDK)';
COMMENT ON TABLE job_embeddings IS 'Vector embeddings of job postings for RAG semantic search';
COMMENT ON TABLE company_doc_embeddings IS 'Vector embeddings of company documents for RAG semantic search';
COMMENT ON FUNCTION vector_search_jobs IS 'Search job postings using cosine similarity (1 - distance)';
COMMENT ON FUNCTION vector_search_company_docs IS 'Search company docs using cosine similarity';
