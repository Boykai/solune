-- Migration 042: App Plan Orchestrations tracking table
-- Tracks the lifecycle of plan-driven app creation orchestrations.

CREATE TABLE IF NOT EXISTS app_plan_orchestrations (
    id TEXT PRIMARY KEY NOT NULL,
    app_name TEXT NOT NULL,
    project_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planning',
    plan_issue_number INTEGER,
    plan_pr_branch TEXT,
    plan_md_content TEXT,
    phase_count INTEGER,
    phase_issue_numbers TEXT,  -- JSON array of issue numbers
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_app_plan_orchestrations_app_name
    ON app_plan_orchestrations(app_name);

CREATE INDEX IF NOT EXISTS idx_app_plan_orchestrations_status
    ON app_plan_orchestrations(status);
