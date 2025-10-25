-- Migration: Add escalations table
-- Purpose: Track all escalations to human staff for analytics and follow-up
-- Date: 2025-01-13

CREATE TABLE IF NOT EXISTS escalations (
    -- Primary key
    id VARCHAR(50) PRIMARY KEY,

    -- Escalation details
    escalation_type VARCHAR(50) NOT NULL,  -- finance_advisor, technical_expert, sales_manager, manager
    urgency VARCHAR(20) NOT NULL,  -- low, medium, high, critical
    reason TEXT,  -- complex_financing, complaint, technical_deep_dive, etc.

    -- Customer information
    customer_phone VARCHAR(20) NOT NULL,
    customer_name VARCHAR(100),

    -- Linked entities
    conversation_id VARCHAR(100),  -- Chatwoot conversation ID
    contact_id VARCHAR(100),  -- Chatwoot contact ID

    -- Notification status
    whatsapp_sent BOOLEAN DEFAULT FALSE,
    email_sent BOOLEAN DEFAULT FALSE,
    chatwoot_assigned BOOLEAN DEFAULT FALSE,

    -- Assignment and resolution
    assigned_to VARCHAR(100),  -- Staff member handling this
    status VARCHAR(20) DEFAULT 'pending',  -- pending, in_progress, resolved, closed
    resolution_notes TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

-- Create indexes separately
CREATE INDEX idx_escalations_created_at ON escalations(created_at);
CREATE INDEX idx_escalations_status ON escalations(status);
CREATE INDEX idx_escalations_urgency ON escalations(urgency);
CREATE INDEX idx_escalations_customer_phone ON escalations(customer_phone);
CREATE INDEX idx_escalations_conversation_id ON escalations(conversation_id);

-- Add comment
COMMENT ON TABLE escalations IS 'Tracks escalations from AI agent to human staff with notification status and resolution tracking';
