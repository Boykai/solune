# Data Model: Full-Stack Plan Pipeline Enhancement (v2 — Copilot SDK + MAF)

**Branch**: `001-full-stack-plan-pipeline` | **Date**: 2026-04-04

## Entities

### 1. Plan (Extended)

**Table**: `chat_plans` (existing, extended)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| plan_id | TEXT | PK | UUID, existing |
| session_id | TEXT | FK → user_sessions, NOT NULL | Existing |
| title | TEXT | NOT NULL, ≤256 chars | Existing |
| summary | TEXT | NOT NULL, ≤65536 chars | Existing |
| status | TEXT | CHECK (draft/approved/completed/failed) | Existing |
| **version** | **INTEGER** | **NOT NULL DEFAULT 1** | **NEW — auto-incremented on save** |
| project_id | TEXT | NOT NULL | Existing |
| project_name | TEXT | NOT NULL | Existing |
| repo_owner | TEXT | NOT NULL | Existing |
| repo_name | TEXT | NOT NULL | Existing |
| parent_issue_number | INTEGER | nullable | Existing |
| parent_issue_url | TEXT | nullable | Existing |
| created_at | TEXT | NOT NULL, ISO 8601 | Existing |
| updated_at | TEXT | NOT NULL, ISO 8601 | Existing |

**Validation Rules**:
- `version` monotonically increases (never decreases)
- `status` transitions: draft → approved → completed/failed (no backward)
- `title` max 256 characters, `summary` max 65536 characters

### 2. PlanVersion (New)

**Table**: `chat_plan_versions` (new)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| version_id | TEXT | PK | UUID |
| plan_id | TEXT | FK → chat_plans, NOT NULL | Parent plan reference |
| version | INTEGER | NOT NULL | Version number at time of snapshot |
| title | TEXT | NOT NULL | Title at this version |
| summary | TEXT | NOT NULL | Summary at this version |
| steps_json | TEXT | NOT NULL | JSON array of step snapshots |
| created_at | TEXT | NOT NULL, ISO 8601 | Snapshot timestamp |

**Validation Rules**:
- `steps_json` must be valid JSON array
- `version` must match an existing or previous version of the parent plan
- Snapshots are immutable once created (append-only)

**Relationships**:
- `plan_id` → `chat_plans.plan_id` (CASCADE DELETE)

**Indexes**:
- `idx_plan_versions_plan_id` on `plan_id`
- `idx_plan_versions_version` on `(plan_id, version)` UNIQUE

### 3. PlanStep (Extended)

**Table**: `chat_plan_steps` (existing, extended)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| step_id | TEXT | PK | UUID, existing |
| plan_id | TEXT | FK → chat_plans, NOT NULL | Existing |
| position | INTEGER | NOT NULL, CHECK ≥ 0 | Existing |
| title | TEXT | NOT NULL, ≤256 chars | Existing |
| description | TEXT | NOT NULL, ≤65536 chars | Existing |
| dependencies | TEXT | NOT NULL DEFAULT '[]' | JSON array, existing |
| **approval_status** | **TEXT** | **DEFAULT 'pending', CHECK (pending/approved/rejected)** | **NEW — per-step approval** |
| issue_number | INTEGER | nullable | Existing |
| issue_url | TEXT | nullable | Existing |

**Validation Rules**:
- `dependencies` must be valid JSON array of step_id strings
- Dependencies must reference existing steps within the same plan (referential integrity)
- No circular dependencies (DAG validation via Kahn's algorithm)
- `position` must be unique within a plan (existing UNIQUE constraint)
- `approval_status` transitions: pending → approved/rejected

### 4. StepFeedback (New — In-Memory)

**Note**: Step feedback is transient (not persisted). It flows through the SDK elicitation handler to the agent and is incorporated into the next plan version via `save_plan`.

| Field | Type | Notes |
|-------|------|-------|
| step_id | string | Target step |
| plan_id | string | Parent plan |
| feedback_type | enum | 'comment' / 'approve' / 'reject' |
| content | string | Feedback text (for comments) |

## State Transitions

### Plan Status

```
draft ──→ approved ──→ completed
  │                      │
  │                      └──→ failed
  │
  └──→ (refined: stays draft, version increments)
```

### Plan Version Lifecycle

```
v1 (initial save_plan)
  │
  ├─ pre-hook snapshot → chat_plan_versions (v1)
  │
v2 (refinement save_plan)
  │
  ├─ pre-hook snapshot → chat_plan_versions (v2)
  │
v3 (further refinement)
  ...
```

### Step Approval Status

```
pending ──→ approved
   │
   └──→ rejected ──→ pending (if re-refined)
```

## Relationships

```
user_sessions (1) ──→ (N) chat_plans
chat_plans (1) ──→ (N) chat_plan_steps
chat_plans (1) ──→ (N) chat_plan_versions
chat_plan_steps (N) ──→ (N) chat_plan_steps  (self-referential via dependencies JSON)
```

## SDK Agent Profiles (Configuration, not persisted)

### Plan Agent Profile

```python
PLAN_AGENT_PROFILE = {
    "name": "solune-plan",
    "instructions": PLAN_SYSTEM_INSTRUCTIONS,
    "tools": ["get_project_context", "get_pipeline_list", "save_plan"],
    "permissions": "read-only",  # Except save_plan
}
```

### Speckit Agent Profiles

| Agent | Name | Tools | Permissions |
|-------|------|-------|-------------|
| speckit.plan | solune-plan | get_project_context, get_pipeline_list, save_plan | Read + save_plan |
| speckit.specify | solune-specify | get_project_context | Read-only |
| speckit.tasks | solune-tasks | get_project_context, get_pipeline_list | Read-only |
| speckit.analyze | solune-analyze | get_project_context | Read-only |
| speckit.implement | solune-implement | All regular tools | Full access |

## Migration Scripts

### 040_plan_versioning.sql

```sql
-- Add version tracking to plans
ALTER TABLE chat_plans ADD COLUMN version INTEGER NOT NULL DEFAULT 1;

-- Version snapshot table
CREATE TABLE IF NOT EXISTS chat_plan_versions (
    version_id    TEXT PRIMARY KEY,
    plan_id       TEXT NOT NULL,
    version       INTEGER NOT NULL,
    title         TEXT NOT NULL,
    summary       TEXT NOT NULL,
    steps_json    TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (plan_id) REFERENCES chat_plans(plan_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_plan_versions_plan_id ON chat_plan_versions(plan_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_plan_versions_plan_version ON chat_plan_versions(plan_id, version);
```

### 041_plan_step_status.sql

```sql
-- Add per-step approval tracking
ALTER TABLE chat_plan_steps ADD COLUMN approval_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (approval_status IN ('pending', 'approved', 'rejected'));

CREATE INDEX IF NOT EXISTS idx_plan_steps_approval ON chat_plan_steps(plan_id, approval_status);
```
