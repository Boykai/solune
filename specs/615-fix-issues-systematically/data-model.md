# Data Model: Fix Issues Systematically

**Feature**: 615-fix-issues-systematically | **Date**: 2026-04-03

## Entity Changes

### 1. user_preferences (ALTER)

**Table**: `user_preferences`
**Change**: Add `ai_reasoning_effort` column

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| ai_reasoning_effort | TEXT | YES | NULL | Reasoning effort level: "low", "medium", "high", "xhigh" |

**Migration SQL**:
```sql
ALTER TABLE user_preferences ADD COLUMN ai_reasoning_effort TEXT;
```

**Validation Rules**:
- Must be one of: `NULL`, `"low"`, `"medium"`, `"high"`, `"xhigh"`, `""` (empty string)
- Stored as lowercase string
- NULL and empty string both mean "no reasoning effort" (model default)

### 2. global_settings (ALTER)

**Table**: `global_settings`
**Change**: Add `ai_reasoning_effort` column

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| ai_reasoning_effort | TEXT | YES | NULL | Global default reasoning effort level |

**Migration SQL**:
```sql
ALTER TABLE global_settings ADD COLUMN ai_reasoning_effort TEXT;
```

### 3. pipeline_configs (ALTER)

**Table**: `pipeline_configs`
**Change**: Add `github_user_id` column for user-scoped ownership

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| github_user_id | TEXT | YES | NULL | GitHub user ID who owns this pipeline |

**Migration SQL**:
```sql
ALTER TABLE pipeline_configs ADD COLUMN github_user_id TEXT;
```

**Relationships**:
- `github_user_id` references the user's GitHub ID (same as `user_preferences.github_user_id`)
- `project_id` remains for contextual association but is no longer the primary ownership key
- Preset pipelines (`is_preset = 1`) may have `github_user_id = NULL`

**State Transitions**:
- Existing pipelines: `github_user_id = NULL` (backfilled on first access)
- New pipelines: `github_user_id` set from session `github_user_id`
- Preset pipelines: `github_user_id = NULL` (global presets available to all users)

### 4. chores (ALTER)

**Table**: `chores`
**Change**: Add `github_user_id` column for user-scoped ownership

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| github_user_id | TEXT | YES | NULL | GitHub user ID who owns this chore |

**Migration SQL**:
```sql
ALTER TABLE chores ADD COLUMN github_user_id TEXT;
```

**Deprecated Columns** (kept for backward compatibility, no longer populated):
- `template_path` — No longer used; template generation removed
- `template_content` — No longer used; template generation removed
- `current_issue_number` — No longer used; tracking issue removed
- `current_issue_node_id` — No longer used; tracking issue removed
- `pr_number` — No longer used; PR generation removed
- `pr_url` — No longer used; PR generation removed
- `tracking_issue_number` — No longer used; tracking issue removed

**Relationships**:
- `github_user_id` references the user's GitHub ID
- `project_id` remains for contextual association
- `agent_pipeline_id` still references `pipeline_configs.id`

### 5. activity_events (NO SCHEMA CHANGE)

**Table**: `activity_events`
**Change**: No schema change needed. The `detail` JSON column already supports arbitrary key-value data.

**Convention for PR/Issue References in `detail`**:
```json
{
  "pr_number": 42,
  "pr_url": "https://github.com/owner/repo/pull/42",
  "issue_number": 123,
  "issue_url": "https://github.com/owner/repo/issues/123"
}
```

**Frontend Parsing Rules**:
- Keys ending in `_url` with string values → render as clickable links
- Keys ending in `_number` with numeric values → check for companion `_url` key, render as linked `#N`
- Summary text containing `#\d+` → linkify with repository base URL

### 6. ChatMessageRequest (MODEL CHANGE — no DB)

**Model**: `ChatMessageRequest` in `models/chat.py`
**Change**: Default `ai_enhance` to `True`, mark as deprecated

```python
class ChatMessageRequest(BaseModel):
    content: str
    ai_enhance: bool = Field(
        default=True,
        description="Deprecated. All messages are processed by ChatAgentService.",
    )
    file_urls: list[str]
    pipeline_id: str | None
```

## Entity Relationship Diagram

```
user_preferences
├── github_user_id (PK)
├── ai_provider
├── ai_model
├── ai_reasoning_effort  ← NEW
├── ai_agent_model
├── ai_temperature
└── ...

global_settings
├── key (PK)
├── ai_reasoning_effort  ← NEW
└── ...

pipeline_configs
├── id (PK)
├── project_id (FK → contextual, no longer primary)
├── github_user_id  ← NEW (ownership)
├── name
├── stages (JSON)
└── ...

chores
├── id (PK)
├── project_id (FK → contextual, no longer primary)
├── github_user_id  ← NEW (ownership)
├── name
├── template_path  ← DEPRECATED
├── template_content  ← DEPRECATED
├── pr_number  ← DEPRECATED
├── pr_url  ← DEPRECATED
├── tracking_issue_number  ← DEPRECATED
└── ...

activity_events
├── id (PK)
├── detail (JSON) ← Convention: include pr_url, issue_url
└── ...
```

## Combined Migration: 038_fix_issues.sql

```sql
-- Migration 038: Fix Issues Systematically (#615)
-- Settings: Add reasoning effort persistence
ALTER TABLE user_preferences ADD COLUMN ai_reasoning_effort TEXT;
ALTER TABLE global_settings ADD COLUMN ai_reasoning_effort TEXT;

-- Pipelines: Add user-scoped ownership
ALTER TABLE pipeline_configs ADD COLUMN github_user_id TEXT;

-- Chores: Add user-scoped ownership
ALTER TABLE chores ADD COLUMN github_user_id TEXT;
```

**Note**: SQLite `ALTER TABLE ADD COLUMN` is safe and non-destructive. Existing rows get `NULL` for new columns. No data migration or backfill is needed at migration time — backfill happens on first access via application logic.
