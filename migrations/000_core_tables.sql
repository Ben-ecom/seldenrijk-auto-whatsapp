-- Migration: Core tables for messages and conversations
-- Purpose: Base tables for WhatsApp message tracking
-- Date: 2025-01-13

CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(100) PRIMARY KEY,
    customer_phone VARCHAR(20) NOT NULL,
    contact_id VARCHAR(100),  -- Chatwoot contact ID
    status VARCHAR(20) DEFAULT 'active',  -- active, closed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_conversations_customer_phone ON conversations(customer_phone);
CREATE INDEX idx_conversations_contact_id ON conversations(contact_id);
CREATE INDEX idx_conversations_status ON conversations(status);

COMMENT ON TABLE conversations IS 'Tracks ongoing conversations with customers';

CREATE TABLE IF NOT EXISTS messages (
    id VARCHAR(100) PRIMARY KEY,
    conversation_id VARCHAR(100) REFERENCES conversations(id),
    sender_phone VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    message_type VARCHAR(20) NOT NULL,  -- incoming, outgoing
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_sender_phone ON messages(sender_phone);
CREATE INDEX idx_messages_created_at ON messages(created_at);

COMMENT ON TABLE messages IS 'Stores all WhatsApp messages';
