-- Make pipeline configs and chores accessible per-user across all projects.
-- Adds github_user_id column to store ownership; queries will filter
-- by github_user_id instead of project_id for user-scoped access.
-- Update uniqueness to match the new ownership model so multiple users in
-- the same project can have same-named configs/chores and preset seeding
-- remains unique per user rather than per project.

ALTER TABLE pipeline_configs ADD COLUMN github_user_id TEXT NOT NULL DEFAULT '';
ALTER TABLE chores ADD COLUMN github_user_id TEXT NOT NULL DEFAULT '';

DROP INDEX IF EXISTS idx_pipeline_configs_preset;
DROP INDEX IF EXISTS idx_chores_preset;

CREATE UNIQUE INDEX IF NOT EXISTS idx_pipeline_configs_preset
    ON pipeline_configs(preset_id, github_user_id)
    WHERE preset_id != '';

CREATE UNIQUE INDEX IF NOT EXISTS idx_chores_preset
    ON chores(preset_id, github_user_id)
    WHERE preset_id != '';
