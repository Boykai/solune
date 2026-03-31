-- Migration 035: Chat plans for /plan mode
CREATE TABLE IF NOT EXISTS chat_plans (
    plan_id       TEXT PRIMARY KEY NOT NULL,
    session_id    TEXT NOT NULL,
    title         TEXT NOT NULL,
    summary       TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'draft'
                  CHECK (status IN ('draft', 'approved', 'completed', 'failed')),
    project_id    TEXT NOT NULL,
    project_name  TEXT NOT NULL,
    repo_owner    TEXT NOT NULL,
    repo_name     TEXT NOT NULL,
    parent_issue_number INTEGER,
    parent_issue_url    TEXT,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (session_id) REFERENCES user_sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chat_plan_steps (
    step_id       TEXT PRIMARY KEY NOT NULL,
    plan_id       TEXT NOT NULL,
    position      INTEGER NOT NULL CHECK (position >= 0),
    title         TEXT NOT NULL,
    description   TEXT NOT NULL,
    dependencies  TEXT NOT NULL DEFAULT '[]',
    issue_number  INTEGER,
    issue_url     TEXT,
    FOREIGN KEY (plan_id) REFERENCES chat_plans(plan_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chat_plans_session_id ON chat_plans(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_plans_status ON chat_plans(status);
CREATE INDEX IF NOT EXISTS idx_chat_plan_steps_plan_id ON chat_plan_steps(plan_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_chat_plan_steps_position ON chat_plan_steps(plan_id, position);
