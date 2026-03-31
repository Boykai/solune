# Data Model: Copilot-Style Planning Mode (v2)

**Branch**: `001-copilot-plan-mode` | **Date**: 2026-03-31 | **Spec**: [spec.md](spec.md)

## Entities

### Plan

Represents a structured implementation plan scoped to a specific project and repository.

| Field                | Type           | Constraints                                                    | Description                                          |
|----------------------|----------------|----------------------------------------------------------------|------------------------------------------------------|
| `plan_id`            | TEXT (UUID)     | PRIMARY KEY, NOT NULL                                          | Unique plan identifier                               |
| `session_id`         | TEXT (UUID)     | NOT NULL, FK → `user_sessions.session_id`                      | Parent chat session                                  |
| `title`              | TEXT            | NOT NULL, max 256 chars                                        | Plan title                                           |
| `summary`            | TEXT            | NOT NULL, max 65536 chars                                      | Plan summary/description                             |
| `status`             | TEXT            | NOT NULL, CHECK IN ('draft', 'approved', 'completed', 'failed')| Plan lifecycle status                                |
| `project_id`         | TEXT            | NOT NULL                                                       | Associated GitHub project ID                         |
| `project_name`       | TEXT            | NOT NULL                                                       | Project display name                                 |
| `repo_owner`         | TEXT            | NOT NULL                                                       | GitHub repository owner                              |
| `repo_name`          | TEXT            | NOT NULL                                                       | GitHub repository name                               |
| `parent_issue_number`| INTEGER         | NULL (populated after approval)                                | GitHub parent issue number                           |
| `parent_issue_url`   | TEXT            | NULL (populated after approval)                                | GitHub parent issue URL                              |
| `created_at`         | TEXT (ISO 8601) | NOT NULL, DEFAULT CURRENT_TIMESTAMP                            | Creation timestamp                                   |
| `updated_at`         | TEXT (ISO 8601) | NOT NULL, DEFAULT CURRENT_TIMESTAMP                            | Last-updated timestamp                               |

### PlanStep

Represents an individual step within a plan, scoped as a future GitHub issue.

| Field          | Type           | Constraints                               | Description                                       |
|----------------|----------------|-------------------------------------------|---------------------------------------------------|
| `step_id`      | TEXT (UUID)     | PRIMARY KEY, NOT NULL                     | Unique step identifier                            |
| `plan_id`      | TEXT (UUID)     | NOT NULL, FK → `chat_plans.plan_id`       | Parent plan reference                             |
| `position`     | INTEGER         | NOT NULL, CHECK >= 0                      | Step order (0-indexed)                            |
| `title`        | TEXT            | NOT NULL, max 256 chars                   | Step title (becomes issue title)                  |
| `description`  | TEXT            | NOT NULL, max 65536 chars                 | Step description (becomes issue body)             |
| `dependencies` | TEXT (JSON)     | NOT NULL, DEFAULT '[]'                    | JSON array of step_ids this step depends on       |
| `issue_number` | INTEGER         | NULL (populated after approval)           | GitHub issue number for this step                 |
| `issue_url`    | TEXT            | NULL (populated after approval)           | GitHub issue URL for this step                    |

## Relationships

```text
user_sessions (1) ──── (N) chat_plans
chat_plans    (1) ──── (N) chat_plan_steps
```

- A user session can have multiple plans (one active at a time via `is_plan_mode` session state).
- A plan has one or more steps, ordered by `position`.
- Step `dependencies` reference other `step_id`s within the same plan (self-referential via JSON array, not FK — allows flexible dependency graphs without join complexity).

## State Transitions

### Plan Status

```text
  ┌─────────┐
  │  draft   │ ← initial state (plan created/updated by agent)
  └────┬─────┘
       │ user clicks "Approve & Create Issues"
       v
  ┌──────────┐
  │ approved  │ ← issues being created
  └────┬──┬──┘
       │  │ partial failure
       │  v
       │ ┌────────┐
       │ │ failed  │ ← some/all issues failed to create (retryable)
       │ └────┬───┘
       │      │ retry
       │      v
       │ (back to approved → re-attempt creation)
       │
       │ all issues created successfully
       v
  ┌───────────┐
  │ completed  │ ← all issues created, plan is finalized
  └───────────┘
```

## Validation Rules

### Plan
- `title`: Required, non-empty, max 256 characters.
- `summary`: Required, non-empty, max 65,536 characters.
- `status`: Must be one of `draft`, `approved`, `completed`, `failed`.
- `project_id`, `project_name`, `repo_owner`, `repo_name`: All required, non-empty.
- `parent_issue_number` and `parent_issue_url`: NULL until approval; both must be set together after successful parent issue creation.

### PlanStep
- `title`: Required, non-empty, max 256 characters.
- `description`: Required, non-empty, max 65,536 characters.
- `position`: Non-negative integer, unique within a plan.
- `dependencies`: Valid JSON array; each element must be a `step_id` that exists within the same `plan_id`. No circular dependencies allowed.
- `issue_number` and `issue_url`: NULL until approval; both must be set together after successful issue creation.

### Business Rules
- A plan cannot be approved if it has zero steps.
- A plan can only be approved when in `draft` status.
- Only the `draft` status allows plan content modifications (title, summary, steps).
- A failed plan can be retried (transitions back to `approved` for re-attempt).
- Steps are ordered by `position`; gaps in position values are allowed (for insertion flexibility).

## SQLite Migration (035_chat_plans.sql)

```sql
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
```
