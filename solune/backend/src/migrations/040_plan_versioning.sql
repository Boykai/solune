-- Migration 040: Plan versioning — add version column and plan_versions table
ALTER TABLE chat_plans ADD COLUMN version INTEGER NOT NULL DEFAULT 1;

CREATE TABLE IF NOT EXISTS chat_plan_versions (
    version_id  TEXT PRIMARY KEY NOT NULL,
    plan_id     TEXT NOT NULL,
    version     INTEGER NOT NULL,
    title       TEXT NOT NULL,
    summary     TEXT NOT NULL,
    steps_json  TEXT NOT NULL DEFAULT '[]',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (plan_id) REFERENCES chat_plans(plan_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_plan_versions_plan_id ON chat_plan_versions(plan_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_plan_versions_version ON chat_plan_versions(plan_id, version);
