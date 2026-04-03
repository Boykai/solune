-- Make pipeline configs and chores accessible per-user across all projects.
-- Adds github_user_id column to store ownership; queries will filter
-- by github_user_id instead of project_id for user-scoped access.

ALTER TABLE pipeline_configs ADD COLUMN github_user_id TEXT NOT NULL DEFAULT '';
ALTER TABLE chores ADD COLUMN github_user_id TEXT NOT NULL DEFAULT '';
