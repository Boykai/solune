-- Migration 037: Agent Import Support
-- Feature: Awesome Copilot Agent Import (003-copilot-agent-import)
-- Adds import lifecycle columns to agent_configs for catalog-imported agents.

ALTER TABLE agent_configs ADD COLUMN agent_type TEXT NOT NULL DEFAULT 'custom';
ALTER TABLE agent_configs ADD COLUMN catalog_source_url TEXT;
ALTER TABLE agent_configs ADD COLUMN catalog_agent_id TEXT;
ALTER TABLE agent_configs ADD COLUMN raw_source_content TEXT;
ALTER TABLE agent_configs ADD COLUMN imported_at TEXT;

-- Index for duplicate detection (FR-008): one import per catalog agent per project
CREATE INDEX IF NOT EXISTS idx_agent_configs_catalog
    ON agent_configs(catalog_agent_id, project_id);
