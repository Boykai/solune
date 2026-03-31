# Data Model: Increase Backend Test Coverage & Fix Bugs

**Feature**: `002-backend-test-coverage` | **Date**: 2026-03-31

## Entity Overview

This feature adds no new data models or database schema changes. All changes are test-only. This document catalogs the existing entities that are the targets of new test coverage, documenting their fields, relationships, and the specific behaviors that need test verification.

## Test Target Entities

### 1. GitHubProject (projects.py)

**File**: `solune/backend/src/models/project.py`
**Test File**: `solune/backend/tests/unit/test_api_projects.py`

| Field | Type | Description | Test Relevance |
|-------|------|-------------|----------------|
| `id` | `str` | GitHub Project V2 node ID | Cache key lookups, `get_project` not-in-list |
| `title` | `str` | Project display name | List response validation |
| `number` | `int` | Project number | Endpoint path parameter |
| `url` | `str` | GitHub URL | Response serialization |
| `closed` | `bool` | Archived/closed state | Filter logic |

**Relationships**: Referenced by `ProjectListResponse.projects` (list), `TaskListResponse` (parent for tasks).

**Behaviors Under Test**:
- Rate limit detection: 403 + `X-RateLimit-Remaining: "0"` → cached stale data served
- Empty rate limit dict: 403 without rate limit headers → non-rate-limit error path
- Cache semantics: `None` (unpopulated) vs. `[]` (empty list) distinction
- Stale fallback: expired cache returns last known data on API failure
- Hash diffing: `data_hash` comparison for WebSocket push decisions

---

### 2. Task (projects.py fallback)

**File**: `solune/backend/src/models/task.py`
**Test File**: `solune/backend/tests/unit/test_api_projects.py`

| Field | Type | Description | Test Relevance |
|-------|------|-------------|----------------|
| `id` | `str` | Task node ID | DB cache lookup |
| `title` | `str` | Task title | Fallback response |
| `status` | `str` | Task status name | Status filtering |
| `assignees` | `list[str]` | Assigned users | Response serialization |

**Behaviors Under Test**:
- `get_project_tasks` exception fallback → `get_done_items()` from SQLite cache
- Task model construction from database rows vs. API responses

---

### 3. AgentCreationState (agent_creator.py)

**File**: `solune/backend/src/models/agent_creator.py`
**Test File**: `solune/backend/tests/unit/test_agent_creator.py`

| Field | Type | Description | Test Relevance |
|-------|------|-------------|----------------|
| `session_id` | `str` | Unique session UUID | Session lookup, BoundedDict key |
| `step` | `CreationStep` | Current pipeline step enum | State machine routing |
| `description` | `str` | Agent description from user | Parse command extraction |
| `status_name` | `str \| None` | Resolved status column | Fuzzy match, selection |
| `preview` | `AgentPreview \| None` | Generated agent config | AI response handling |
| `project_id` | `str` | Target project | Duplicate name scoping |
| `owner` | `str` | Repository owner | GitHub API calls |
| `repo` | `str` | Repository name | GitHub API calls |

**State Machine Transitions Under Test**:
```
PARSE_COMMAND → RESOLVE_STATUS → GENERATE_PREVIEW → CONFIRM_PREVIEW → EXECUTE_PIPELINE
                     ↓                    ↓                 ↓
              (fuzzy match)       (AI failure)       (edit → retry)
```

**Behaviors Under Test**:
- Admin auth: debug auto-promote via CAS, `ADMIN_GITHUB_USER_ID` env var, DB exception
- Status resolution: empty input, normalized match, out-of-range selection, new column
- Pipeline steps 3–7: duplicate name check, column creation, issue/PR creation, cleanup
- AI failures: `generate_agent_config()` exception, edit retry, non-list tools

---

### 4. AgentPreview (agent_creator.py)

**File**: `solune/backend/src/models/agent_creator.py`

| Field | Type | Description | Test Relevance |
|-------|------|-------------|----------------|
| `name` | `str` | Agent display name | Duplicate check, slug generation |
| `slug` | `str` | URL-safe identifier | Special chars → sanitized |
| `description` | `str` | Agent description | YAML frontmatter generation |
| `system_prompt` | `str` | System instructions | Config file content |
| `tools` | `list[str]` | Tool identifiers | Non-list handling |
| `model` | `str` | AI model name | Config file content |

**Behaviors Under Test**:
- `tools` field receives non-list value from AI → graceful handling
- `name` with special characters → valid slug generation
- Config file generation with edge-case field values

---

### 5. Agent (agents/service.py)

**File**: `solune/backend/src/models/agents.py`
**Test File**: `solune/backend/tests/unit/test_agents_service.py`

| Field | Type | Description | Test Relevance |
|-------|------|-------------|----------------|
| `id` | `str` | Agent UUID or repo path | Source mixing (REPO vs LOCAL) |
| `slug` | `str` | URL-safe identifier | Duplicate detection, preference overlay key |
| `name` | `str` | Display name | YAML frontmatter parsing |
| `description` | `str` | Agent description | Missing field defaults |
| `source` | `AgentSource` | REPO \| LOCAL | Bulk update source filtering |
| `lifecycle_status` | `AgentStatus` | ACTIVE \| PENDING_* | Tombstone filtering, cleanup |
| `default_model_id` | `str \| None` | Preferred model | Preference overlay |
| `default_model_name` | `str \| None` | Model display name | Preference overlay |
| `icon_name` | `str \| None` | UI icon | Runtime preference save |
| `tools` | `list[str] \| None` | Tool IDs | Resolution, MCP normalization |

**Behaviors Under Test**:
- `list_agents()`: repo agents + local preference overlay from DB
- Stale cache fallback: expired TTL returns last data on error
- Session pruning: remove stale sessions from BoundedDict
- `bulk_update_models()`: REPO + LOCAL sources, partial failure
- Tombstone filtering: exclude `PENDING_DELETION` agents from list
- YAML frontmatter: missing fields → defaults, parse errors → fallback, no frontmatter
- Tool resolution: MCP normalization, wildcard vs explicit, dedup, invalid configs
- `create_agent()`: slug from special chars, AI failure fallback, raw vs enhanced mode

---

### 6. Chore (chores/service.py)

**File**: `solune/backend/src/models/chores.py`
**Test File**: `solune/backend/tests/unit/test_chores_service.py`

| Field | Type | Description | Test Relevance |
|-------|------|-------------|----------------|
| `id` | `str` | Chore UUID | CAS update target |
| `name` | `str` | Display name | Preset seeding uniqueness |
| `preset_id` | `str \| None` | Built-in preset identifier | Idempotent seed check |
| `status` | `ChoreStatus` | active \| paused | Schedule evaluation filter |
| `schedule_type` | `str \| None` | "time" \| "count" \| None | Trigger evaluation |
| `schedule_value` | `str \| None` | Cron or count value | Trigger evaluation |
| `enabled` | `int` | 0 or 1 (SQLite boolean) | Boolean→int conversion |
| `auto_merge` | `int` | 0 or 1 (SQLite boolean) | Boolean→int conversion |
| `last_triggered_at` | `str \| None` | ISO timestamp or None | CAS WHERE clause |
| `last_triggered_count` | `int \| None` | Execution count | CAS increment |
| `execution_count` | `int` | Total executions | Post-trigger update |
| `current_issue_number` | `int \| None` | Open issue number | 1-open-instance constraint |
| `current_issue_node_id` | `str \| None` | Open issue GraphQL ID | clear_current_issue() |
| `project_id` | `str` | Parent project | Scoping for all queries |

**Behaviors Under Test**:
- Preset seeding: idempotent re-seed (no duplicates), file read failure, 3 presets
- Update validation: schedule consistency, boolean→int for `enabled`/`auto_merge`, invalid column rejection
- CAS trigger: `WHERE last_triggered_at IS NULL` (first trigger), `= old_value` (match), `!= old_value` (mismatch → rowcount=0)
- `clear_current_issue()`: nullify `current_issue_number` and `current_issue_node_id`
- Column whitelist: `_CHORE_UPDATABLE_COLUMNS` set enforced before SQL execution

---

### 7. _CHORE_UPDATABLE_COLUMNS (chores/service.py — SQL Injection Defense)

**File**: `solune/backend/src/services/chores/service.py`
**Type**: `set[str]` (module-level constant)

This is a hardcoded whitelist of column names permitted in dynamic SQL `UPDATE` statements. Any column name not in this set is rejected before the query is constructed.

**Behaviors Under Test**:
- Valid column names pass through
- Invalid/malicious column names (`"name; DROP TABLE"`, `"1=1 OR name"`) are rejected
- Boolean values for `enabled`/`auto_merge` columns are converted to integers (True→1, False→0)

## Relationship Diagram

```
┌────────────────────┐     ┌──────────────────┐     ┌──────────────────────┐
│   projects.py      │     │  agent_creator.py │     │  agents/service.py   │
│                    │     │                   │     │                      │
│ GitHubProject ─────│──┐  │ AgentCreationState│◄──► │ Agent                │
│ Task               │  │  │ AgentPreview     ─│────►│ AgentCreate          │
│ ProjectListResponse│  │  │ CreationStep      │     │ AgentUpdate          │
│ TaskListResponse   │  │  │ PipelineStepResult│     │ AgentPreview         │
└────────────────────┘  │  └──────────────────┘     └──────────────────────┘
                        │                                      │
                        │  ┌──────────────────────┐           │
                        │  │  chores/service.py    │           │
                        │  │                       │           │
                        └──│ Chore                 │           │
                           │ ChoreCreate           │           │
                           │ ChoreUpdate           │           │
                           │ ChoreTriggerResult    │           │
                           │ _CHORE_UPDATABLE_COLS │           │
                           └──────────────────────┘           │
                                                              │
                        ┌──────────────────────────────────────┘
                        │
                  ┌─────▼──────────┐
                  │  Shared via DB  │
                  │  agent_configs  │
                  │  mcp_configs    │
                  │  chores         │
                  │  global_settings│
                  └────────────────┘
```

## State Transitions

### Agent Creation Pipeline (Steps 3–7)

```
Step 3: Check duplicate name
    ├── Duplicate found → return error message
    └── No duplicate → Step 4

Step 4: Save config to DB
    ├── DB error → cleanup, return error
    └── Success → Step 5

Step 5: Create GitHub issue
    ├── API error → log warning, continue (non-fatal)
    └── Success → Step 6

Step 6: Create branch + commit files
    ├── API error → cleanup partial resources
    └── Success → Step 7

Step 7: Create pull request
    ├── API error → cleanup partial resources
    └── Success → update DB with PR number, return success
```

### Chore CAS Trigger State Machine

```
                     ┌─────────────────────┐
                     │  last_triggered_at   │
                     │       = NULL         │
                     │    (never fired)     │
                     └──────────┬──────────┘
                                │
                    CAS: WHERE last_triggered_at IS NULL
                                │
                     ┌──────────▼──────────┐
                     │  last_triggered_at   │
                     │    = timestamp_1     │
                     │    (fired once)      │
                     └──────────┬──────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                                    │
   CAS: WHERE = timestamp_1              CAS: WHERE = timestamp_1
   (matches → update)                    (another process already updated)
              │                                    │
   ┌──────────▼──────────┐            ┌───────────▼─────────┐
   │  last_triggered_at   │            │   rowcount = 0      │
   │    = timestamp_2     │            │   (double-fire      │
   │    (success)         │            │    prevented)        │
   └─────────────────────┘            └─────────────────────┘
```
