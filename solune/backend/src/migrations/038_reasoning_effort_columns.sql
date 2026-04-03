-- Add reasoning_effort columns to user_preferences and global_settings.
-- Stores the selected reasoning level (e.g. "high", "xhigh") for chat and agent models.

ALTER TABLE user_preferences ADD COLUMN ai_reasoning_effort TEXT DEFAULT '';
ALTER TABLE user_preferences ADD COLUMN ai_agent_reasoning_effort TEXT DEFAULT '';

ALTER TABLE global_settings ADD COLUMN ai_reasoning_effort TEXT DEFAULT '';
ALTER TABLE global_settings ADD COLUMN ai_agent_reasoning_effort TEXT DEFAULT '';
