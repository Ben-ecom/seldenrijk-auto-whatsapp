-- Migration: Add lead scores table
-- Purpose: Track lead scoring history for analytics and trend analysis
-- Date: 2025-01-13

CREATE TABLE IF NOT EXISTS lead_scores (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Customer identification
    customer_phone VARCHAR(20) NOT NULL,
    contact_id VARCHAR(100),  -- Chatwoot contact ID
    conversation_id VARCHAR(100),  -- Chatwoot conversation ID

    -- Score data
    lead_score INT NOT NULL,  -- 0-100
    lead_quality VARCHAR(20) NOT NULL,  -- HOT, WARM, LUKEWARM, COLD

    -- Score components (for analysis)
    score_breakdown JSONB,  -- {car_inquiry: 30, budget_mentioned: 20, ...}

    -- Conversation signals
    interest_level VARCHAR(30),  -- browsing, considering, ready-to-buy
    urgency VARCHAR(20),  -- low, medium, high, critical
    sentiment VARCHAR(20),  -- positive, neutral, negative
    conversation_stage VARCHAR(50),  -- initial-inquiry, information-gathering, ...

    -- Car preferences snapshot
    interested_in_make VARCHAR(50),
    interested_in_model VARCHAR(50),
    interested_in_fuel_type VARCHAR(20),
    budget_max DECIMAL(10, 2),

    -- Behavioral flags
    test_drive_requested BOOLEAN DEFAULT FALSE,
    has_trade_in BOOLEAN DEFAULT FALSE,
    needs_financing BOOLEAN DEFAULT FALSE,
    escalated BOOLEAN DEFAULT FALSE,

    -- Timestamps
    scored_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes separately
CREATE INDEX idx_lead_scores_customer_phone ON lead_scores(customer_phone);
CREATE INDEX idx_lead_scores_lead_quality ON lead_scores(lead_quality);
CREATE INDEX idx_lead_scores_scored_at ON lead_scores(scored_at);
CREATE INDEX idx_lead_scores_lead_score ON lead_scores(lead_score DESC);
CREATE INDEX idx_lead_scores_conversation_id ON lead_scores(conversation_id);

-- Add comment
COMMENT ON TABLE lead_scores IS 'Historical lead scoring data for analytics and trend analysis';

-- Create view for latest lead scores per customer
CREATE OR REPLACE VIEW latest_lead_scores AS
SELECT DISTINCT ON (customer_phone)
    *
FROM lead_scores
ORDER BY customer_phone, scored_at DESC;

COMMENT ON VIEW latest_lead_scores IS 'Most recent lead score for each unique customer';
