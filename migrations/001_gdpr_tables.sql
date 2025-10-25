-- GDPR Compliance Tables
-- Creates tables for consent tracking, data exports, and deletions

-- Consent records table
CREATE TABLE IF NOT EXISTS consent_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id VARCHAR(255) NOT NULL,
    consent_type VARCHAR(50) NOT NULL,  -- marketing, analytics, communication
    granted BOOLEAN NOT NULL,
    ip_address VARCHAR(45),  -- IPv4 or IPv6
    user_agent TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Indexes
    CONSTRAINT consent_records_contact_id_idx UNIQUE (contact_id, consent_type, timestamp)
);

CREATE INDEX idx_consent_records_contact_id ON consent_records(contact_id);
CREATE INDEX idx_consent_records_timestamp ON consent_records(timestamp DESC);

-- Data export requests table
CREATE TABLE IF NOT EXISTS gdpr_exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    download_url TEXT,
    file_name VARCHAR(255),
    error TEXT,

    -- Constraints
    CONSTRAINT gdpr_exports_status_check CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

CREATE INDEX idx_gdpr_exports_contact_id ON gdpr_exports(contact_id);
CREATE INDEX idx_gdpr_exports_status ON gdpr_exports(status);
CREATE INDEX idx_gdpr_exports_expires_at ON gdpr_exports(expires_at);

-- Data deletion requests table
CREATE TABLE IF NOT EXISTS gdpr_deletions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    error TEXT,

    -- Constraints
    CONSTRAINT gdpr_deletions_status_check CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

CREATE INDEX idx_gdpr_deletions_contact_id ON gdpr_deletions(contact_id);
CREATE INDEX idx_gdpr_deletions_status ON gdpr_deletions(status);

-- Data retention policy tracking
CREATE TABLE IF NOT EXISTS data_retention_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_type VARCHAR(100) NOT NULL,  -- contacts, conversations, messages, analytics
    retention_days INTEGER NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT data_retention_policies_data_type_unique UNIQUE (data_type)
);

-- Insert default retention policies
INSERT INTO data_retention_policies (data_type, retention_days, description) VALUES
    ('contacts', 90, 'Contact data retained for 90 days after last interaction'),
    ('conversations', 365, 'Conversation history retained for 1 year'),
    ('consent_records', 1825, 'Consent records retained for 5 years (legal requirement)'),
    ('analytics', 730, 'Analytics data retained for 2 years')
ON CONFLICT (data_type) DO NOTHING;

-- Comments
COMMENT ON TABLE consent_records IS 'GDPR consent tracking for data processing';
COMMENT ON TABLE gdpr_exports IS 'Data export requests (Right to Data Portability)';
COMMENT ON TABLE gdpr_deletions IS 'Data deletion requests (Right to be Forgotten)';
COMMENT ON TABLE data_retention_policies IS 'Data retention policies for automated cleanup';
