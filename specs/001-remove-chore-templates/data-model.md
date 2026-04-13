# Data Model: Remove Issue Templates, Use DB + Parent Issue Intake Flow

**Feature**: 001-remove-chore-templates | **Date**: 2026-04-13

## Entity Changes

### Chore (Modified)

**File**: `solune/backend/src/models/chores.py`

| Field | Before | After | Change |
|-------|--------|-------|--------|
| `template_content: str` | Present (L36) | **Removed** | Renamed to `description` |
| `template_path: str` | Present (L35) | **Removed** | Dropped entirely |
| `description: str` | N/A | **Added** | Replaces `template_content` |
| `pr_number: int \| None` | Present (L44) | Unchanged | Retained — still set by execute_pipeline_launch for tracking |
| `pr_url: str \| None` | Present (L45) | Unchanged | Retained — still set by execute_pipeline_launch for tracking |

**Updated Model**:
```python
class Chore(BaseModel):
    id: str
    project_id: str
    name: str
    description: str                          # was template_content
    # template_path: REMOVED
    schedule_type: ScheduleType | None = None
    schedule_value: int | None = None
    status: ChoreStatus = ChoreStatus.ACTIVE
    last_triggered_at: str | None = None
    last_triggered_count: int = 0
    current_issue_number: int | None = None
    current_issue_node_id: str | None = None
    pr_number: int | None = None              # retained for trigger tracking
    pr_url: str | None = None                 # retained for trigger tracking
    tracking_issue_number: int | None = None
    execution_count: int = 0
    ai_enhance_enabled: bool = True
    agent_pipeline_id: str = ""
    is_preset: bool = False
    preset_id: str = ""
    created_at: str
    updated_at: str
```

### ChoreCreate (Modified)

**File**: `solune/backend/src/models/chores.py`

| Field | Before | After | Change |
|-------|--------|-------|--------|
| `template_content: str` | Present | **Removed** | Renamed to `description` |
| `description: str` | N/A | **Added** | Replaces `template_content` |

```python
class ChoreCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)  # was template_content
```

### ChoreInlineUpdate (Simplified)

**File**: `solune/backend/src/models/chores.py` (or inline in API)

| Field | Before | After | Change |
|-------|--------|-------|--------|
| `expected_sha: str \| None` | Present | **Removed** | No SHA tracking needed |
| `name: str \| None` | Present | Unchanged | |
| `description: str \| None` | N/A | **Added** | Replaces `template_content` |
| `template_content: str \| None` | Present | **Removed** | Renamed to `description` |

---

## Frontend Type Changes

### Chore Type (Modified)

**File**: `solune/frontend/src/types/index.ts` (L1075-1098)

| Field | Before | After | Change |
|-------|--------|-------|--------|
| `template_path: string` | L1079 | **Removed** | |
| `template_content: string` | L1080 | **Removed** | Renamed to `description` |
| `description: string` | N/A | **Added** | Replaces `template_content` |

### ChoreTemplate Type (Removed)

**File**: `solune/frontend/src/types/index.ts` (L1105-1110)

Entire type removed — no longer needed.

### ChoreCreate Type (Modified)

**File**: `solune/frontend/src/types/index.ts` (L1100-1103)

| Field | Before | After |
|-------|--------|-------|
| `template_content: string` | Present | Renamed to `description` |

### ChoreInlineUpdate Type (Simplified)

**File**: `solune/frontend/src/types/index.ts` (L1152-1160)

| Field | Before | After | Change |
|-------|--------|-------|--------|
| `expected_sha: string \| null` | Present (L1159) | **Removed** | |
| `template_content` | Present | Renamed to `description` | |

### ChoreInlineUpdateResponse Type (Simplified)

**File**: `solune/frontend/src/types/index.ts` (L1162-1168)

| Field | Before | After | Change |
|-------|--------|-------|--------|
| `pr_number` | Present | **Removed** | No PRs for inline edits |
| `pr_url` | Present | **Removed** | |
| `pr_merged` | Present | **Removed** | |
| `merge_error` | Present | **Removed** | |

### ChoreCreateResponse Type (Simplified)

**File**: `solune/frontend/src/types/index.ts` (L1178-1185)

| Field | Before | After | Change |
|-------|--------|-------|--------|
| `pr_number` | Present | **Removed** | No PRs for creation |
| `pr_url` | Present | **Removed** | |
| `pr_merged` | Present | **Removed** | |
| `merge_error` | Present | **Removed** | |

### ChoreEditState Type (Simplified)

**File**: `solune/frontend/src/types/index.ts` (L1202-1207)

| Field | Before | After | Change |
|-------|--------|-------|--------|
| `fileSha: string \| null` | Present (L1206) | **Removed** | No SHA tracking |

---

## Database Schema Changes

### Migration: `045_chore_description.sql`

```sql
-- 045_chore_description.sql
-- Rename template_content → description, drop template_path

ALTER TABLE chores RENAME COLUMN template_content TO description;
ALTER TABLE chores DROP COLUMN template_path;
```

Plus a Python-driven data migration to strip YAML front matter from existing `description` values using the `_strip_front_matter()` regex.

---

## execute_pipeline_launch() Signature Extension

**File**: `solune/backend/src/api/pipelines.py` (L293)

New parameters added:

```python
async def execute_pipeline_launch(
    *,
    project_id: str,
    issue_description: str,
    pipeline_id: str | None,
    session: UserSession,
    pipeline_project_id: str | None = None,
    target_repo: tuple[str, str] | None = None,
    auto_merge: bool = False,
    prerequisite_issues: list[int] | None = None,
    extra_labels: list[str] | None = None,          # NEW
    issue_title_override: str | None = None,         # NEW
) -> WorkflowResult:
```

**Behavior**:
- `issue_title_override`: If provided, used as issue title — takes precedence over transcript-derived and AI-derived titles.
- `extra_labels`: If provided, appended to AI-classified labels (deduplicated).

---

## Relationship Diagram

```
Chore (DB)
  ├─ description (plain text, no YAML)
  ├─ schedule_type / schedule_value
  ├─ agent_pipeline_id
  └─ current_issue_number (tracking)
       │
       ▼ trigger_chore()
  execute_pipeline_launch()
  ├─ issue_description = chore.description
  ├─ issue_title_override = chore.name
  ├─ extra_labels = ["chore"]
  ├─ pipeline_id = chore.agent_pipeline_id
  └─ session = constructed UserSession
       │
       ▼
  GitHub Issue + Sub-Issues + Agent Pipeline
```
