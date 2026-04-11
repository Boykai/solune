-- Migration 044: Add conversations table and conversation_id to chat tables
-- Supports multi-chat panel feature with independent conversation contexts

CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL REFERENCES user_sessions(session_id) ON DELETE CASCADE,
    title           TEXT NOT NULL DEFAULT 'New Chat',
    created_at      TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at      TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at);

-- Add nullable conversation_id to existing chat tables
ALTER TABLE chat_messages ADD COLUMN conversation_id TEXT REFERENCES conversations(conversation_id) ON DELETE SET NULL;
ALTER TABLE chat_proposals ADD COLUMN conversation_id TEXT REFERENCES conversations(conversation_id) ON DELETE SET NULL;
ALTER TABLE chat_recommendations ADD COLUMN conversation_id TEXT REFERENCES conversations(conversation_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation_id ON chat_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chat_proposals_conversation_id ON chat_proposals(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chat_recommendations_conversation_id ON chat_recommendations(conversation_id);
