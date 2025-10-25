-- =====================================================
-- SIMPLIFIED SCHEMA FOR CUSTOM-BUILD MODEL
-- No multi-tenancy, no RLS, single-client deployment
-- =====================================================

-- ============ AUTHENTICATION ============
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    role TEXT DEFAULT 'recruiter' CHECK (role IN ('admin', 'recruiter', 'viewer')),
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- ============ LEADS & CANDIDATES ============
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Contact Info
    whatsapp_number TEXT NOT NULL,
    email TEXT,
    full_name TEXT,

    -- Qualification
    qualification_status TEXT DEFAULT 'new' CHECK (qualification_status IN ('new', 'in_progress', 'qualified', 'disqualified', 'pending_review')),
    qualification_score DECIMAL(3,2) CHECK (qualification_score BETWEEN 0.0 AND 1.0),

    -- Job Info
    job_title TEXT,
    years_experience INTEGER,
    skills TEXT[], -- Array of skill keywords

    -- CRM Sync
    crm_id TEXT, -- External CRM ID after sync
    crm_synced_at TIMESTAMP,

    -- Metadata
    source TEXT DEFAULT 'web_form', -- web_form, referral, linkedin, etc
    form_data JSONB, -- Original form submission
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_leads_whatsapp ON leads(whatsapp_number);
CREATE INDEX idx_leads_status ON leads(qualification_status);
CREATE INDEX idx_leads_crm_id ON leads(crm_id);

-- ============ MESSAGES & CHAT HISTORY ============
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,

    -- Message Content
    direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    content TEXT NOT NULL,
    message_type TEXT DEFAULT 'text' CHECK (message_type IN ('text', 'image', 'video', 'audio', 'document')),
    media_url TEXT, -- For non-text messages

    -- AI Context
    agent_name TEXT, -- Which LangGraph node sent this
    confidence_score DECIMAL(3,2), -- For AI-generated responses

    -- RAG
    embedding VECTOR(1536), -- OpenAI ada-002 embeddings for semantic search

    -- Metadata
    whatsapp_message_id TEXT UNIQUE, -- WhatsApp API message ID
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_messages_lead ON messages(lead_id);
CREATE INDEX idx_messages_direction ON messages(direction);
CREATE INDEX idx_messages_embedding ON messages USING ivfflat (embedding vector_cosine_ops); -- PGVector index

-- ============ AGENT STATE (LangGraph Checkpointing) ============
CREATE TABLE agent_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,

    -- LangGraph State
    thread_id TEXT NOT NULL, -- LangGraph thread identifier
    checkpoint_data JSONB NOT NULL, -- Full state snapshot
    current_node TEXT, -- Which node the agent is on

    -- Human-in-the-Loop
    requires_human_review BOOLEAN DEFAULT FALSE,
    human_feedback TEXT,
    human_reviewed_at TIMESTAMP,
    reviewed_by UUID REFERENCES users(id),

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_checkpoints_lead ON agent_checkpoints(lead_id);
CREATE INDEX idx_checkpoints_thread ON agent_checkpoints(thread_id);

-- ============ CRM INTEGRATIONS ============
CREATE TABLE crm_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL, -- 'salesforce', 'hubspot', 'pipedrive', 'custom'
    api_key TEXT NOT NULL, -- Encrypted in production
    base_url TEXT,
    field_mapping JSONB NOT NULL, -- Maps our fields to CRM fields
    webhook_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============ CALENDAR INTEGRATIONS (Optional) ============
CREATE TABLE calendar_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL, -- 'calendly', 'google_calendar', 'outlook'
    api_key TEXT NOT NULL,
    calendar_link TEXT, -- Public scheduling link
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============ INTERVIEW APPOINTMENTS ============
CREATE TABLE appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    recruiter_id UUID REFERENCES users(id),

    -- Appointment Details
    scheduled_at TIMESTAMP NOT NULL,
    duration_minutes INTEGER DEFAULT 30,
    meeting_type TEXT DEFAULT 'video' CHECK (meeting_type IN ('video', 'phone', 'in_person')),
    meeting_link TEXT, -- Zoom/Teams link
    status TEXT DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'cancelled', 'no_show')),

    -- Calendar Integration
    calendar_event_id TEXT, -- External calendar event ID

    -- Notes
    recruiter_notes TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_appointments_lead ON appointments(lead_id);
CREATE INDEX idx_appointments_scheduled ON appointments(scheduled_at);

-- ============ AUDIT LOGS ============
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Who & What
    user_id UUID REFERENCES users(id),
    action TEXT NOT NULL, -- 'lead_created', 'message_sent', 'qualification_updated', etc
    entity_type TEXT NOT NULL, -- 'lead', 'message', 'appointment'
    entity_id UUID,

    -- Details
    changes JSONB, -- Before/after state
    ip_address INET,
    user_agent TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);

-- ============ DASHBOARD NOTIFICATIONS ============
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Notification Content
    type TEXT NOT NULL CHECK (type IN ('new_lead', 'high_score_candidate', 'human_review_needed', 'appointment_scheduled')),
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    link TEXT, -- Deep link to relevant page

    -- State
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_unread ON notifications(user_id, is_read) WHERE is_read = FALSE;

-- ============ SYSTEM CONFIGURATION ============
CREATE TABLE system_config (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert default configuration
INSERT INTO system_config (key, value, description) VALUES
('company_info', '{"name": "Client Company Name", "logo_url": "", "primary_color": "#3b82f6"}', 'Company branding'),
('qualification_thresholds', '{"auto_qualify": 0.7, "auto_disqualify": 0.3, "human_review": 0.5}', 'Qualification score thresholds'),
('whatsapp_config', '{"provider": "360dialog", "phone_number": "+31612345678"}', 'WhatsApp integration settings'),
('ai_model', '{"provider": "anthropic", "model": "claude-3-5-sonnet-20241022"}', 'AI model configuration'),
('form_fields', '["full_name", "email", "whatsapp_number", "job_title", "years_experience", "cv_upload"]', 'Required form fields');

-- ============ ENABLE PGVECTOR ============
CREATE EXTENSION IF NOT EXISTS vector;
