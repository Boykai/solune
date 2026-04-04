# Data Model: Full-Stack Plan Pipeline Enhancement

**Feature**: 016-plan-pipeline-enhancement | **Date**: 2026-04-04

## Entity Overview

```
┌─────────────┐        ┌──────────────────┐
│  chat_plans  │───1:N──│ chat_plan_steps   │
│  (extended)  │        │  (extended)       │
└──────┬──────┘        └──────────────────┘
       │
       │ 1:N
       ▼
┌──────────────────┐
│chat_plan_versions│
│   (NEW table)    │
└──────────────────┘
```

## Entities

### 1. chat_plans (EXTENDED)

Existing table with one new column added by migration 040.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| plan_id | TEXT | PK, NOT NULL | UUID, auto-generated |
| session_id | TEXT | NOT NULL, FK → user_sessions | Parent chat session |
| title | TEXT | NOT NULL | Max 256 chars |
| summary | TEXT | NOT NULL | Max 65536 chars |
| status | TEXT | NOT NULL, DEFAULT 'draft', CHECK IN ('draft','approved','completed','failed') | Lifecycle status |
| project_id | TEXT | NOT NULL | GitHub project ID |
| project_name | TEXT | NOT NULL | Display name |
| repo_owner | TEXT | NOT NULL | GitHub owner login |
| repo_name | TEXT | NOT NULL | GitHub repo name |
| parent_issue_number | INTEGER | NULLABLE | Set post-approval |
| parent_issue_url | TEXT | NULLABLE | Set post-approval |
| **version** | **INTEGER** | **NOT NULL, DEFAULT 1** | **NEW — incremented on each save** |
| created_at | TEXT | NOT NULL, DEFAULT now() | ISO 8601 timestamp |
| updated_at | TEXT | NOT NULL, DEFAULT now() | ISO 8601 timestamp |

**Indexes** (existing):
- `idx_chat_plans_session_id` on `(session_id)`
- `idx_chat_plans_status` on `(status)`

### 2. chat_plan_versions (NEW)

Snapshot table storing historical plan versions for diff computation and history browsing.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| version_id | TEXT | PK, NOT NULL | UUID, auto-generated |
| plan_id | TEXT | NOT NULL, FK → chat_plans ON DELETE CASCADE | Parent plan |
| version | INTEGER | NOT NULL | Version number at time of snapshot |
| title | TEXT | NOT NULL | Plan title at this version |
| summary | TEXT | NOT NULL | Plan summary at this version |
| steps_snapshot | TEXT | NOT NULL | JSON array of step objects at this version |
| created_at | TEXT | NOT NULL, DEFAULT now() | When this version was snapshotted |

**Indexes**:
- `idx_plan_versions_plan_id` on `(plan_id)`
- `idx_plan_versions_unique` UNIQUE on `(plan_id, version)` — enforces one snapshot per version number

**Relationships**:
- `chat_plan_versions.plan_id` → `chat_plans.plan_id` (CASCADE DELETE)

### 3. chat_plan_steps (EXTENDED)

Existing table with one new column added by migration 041.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| step_id | TEXT | PK, NOT NULL | UUID |
| plan_id | TEXT | NOT NULL, FK → chat_plans ON DELETE CASCADE | Parent plan |
| position | INTEGER | NOT NULL, CHECK ≥ 0 | 0-indexed order |
| title | TEXT | NOT NULL | Max 256 chars |
| description | TEXT | NOT NULL | Max 65536 chars |
| dependencies | TEXT | NOT NULL, DEFAULT '[]' | JSON array of step_id strings |
| issue_number | INTEGER | NULLABLE | Set post-approval |
| issue_url | TEXT | NULLABLE | Set post-approval |
| **issue_status** | **TEXT** | **NULLABLE** | **NEW — synced from GitHub: 'open', 'closed', etc.** |

**Indexes** (existing):
- `idx_chat_plan_steps_plan_id` on `(plan_id)`
- `idx_chat_plan_steps_position` UNIQUE on `(plan_id, position)`

## Backend Models (Pydantic v2)

### Plan (EXTENDED)

```python
class Plan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    title: str = Field(max_length=256)
    summary: str = Field(max_length=65536)
    status: PlanStatus = PlanStatus.DRAFT
    project_id: str
    project_name: str
    repo_owner: str
    repo_name: str
    parent_issue_number: int | None = None
    parent_issue_url: str | None = None
    version: int = 1                          # NEW
    steps: list[PlanStep] = []
    created_at: str | None = None
    updated_at: str | None = None
```

### PlanVersion (NEW)

```python
class PlanVersion(BaseModel):
    version_id: str = Field(default_factory=lambda: str(uuid4()))
    plan_id: str
    version: int
    title: str
    summary: str
    steps_snapshot: list[dict[str, Any]]      # Serialized PlanStep dicts
    created_at: str | None = None
```

### PlanStep (EXTENDED)

```python
class PlanStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid4()))
    plan_id: str
    position: int = Field(ge=0)
    title: str = Field(max_length=256)
    description: str = Field(max_length=65536)
    dependencies: list[str] = []
    issue_number: int | None = None
    issue_url: str | None = None
    issue_status: str | None = None           # NEW
```

### StepFeedback (NEW — request schema only, not persisted)

```python
class StepFeedback(BaseModel):
    comment: str = Field(min_length=1, max_length=4096)
```

### StepCreate (NEW — request schema for step CRUD)

```python
class StepCreate(BaseModel):
    title: str = Field(max_length=256)
    description: str = Field(max_length=65536)
    dependencies: list[str] = []
    position: int | None = None               # Auto-assigned if omitted
```

### StepUpdate (NEW — request schema for step CRUD)

```python
class StepUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=256)
    description: str | None = Field(default=None, max_length=65536)
    dependencies: list[str] | None = None
```

### StepReorder (NEW — request schema for bulk reorder)

```python
class StepReorder(BaseModel):
    step_ids: list[str]                       # Ordered list of step IDs in new positions
```

### PlanApproveRequest (EXTENDED — optional selective approval)

```python
class PlanApproveRequest(BaseModel):
    step_ids: list[str] | None = None         # NEW — None means approve all
```

## Frontend Types (TypeScript)

### PlanVersion (NEW)

```typescript
export interface PlanVersion {
  version_id: string;
  plan_id: string;
  version: number;
  title: string;
  summary: string;
  steps_snapshot: PlanStep[];
  created_at: string;
}
```

### PlanStep (EXTENDED)

```typescript
export interface PlanStep {
  step_id: string;
  position: number;
  title: string;
  description: string;
  dependencies: string[];
  issue_number?: number;
  issue_url?: string;
  issue_status?: string;         // NEW
}
```

### Plan (EXTENDED)

```typescript
export interface Plan {
  plan_id: string;
  session_id: string;
  title: string;
  summary: string;
  status: PlanStatus;
  project_id: string;
  project_name: string;
  repo_owner: string;
  repo_name: string;
  parent_issue_number?: number;
  parent_issue_url?: string;
  version: number;               // NEW
  steps: PlanStep[];
  created_at: string;
  updated_at: string;
}
```

### StepFeedback (NEW)

```typescript
export interface StepFeedbackRequest {
  comment: string;
}
```

### StepCreateRequest (NEW)

```typescript
export interface StepCreateRequest {
  title: string;
  description: string;
  dependencies?: string[];
  position?: number;
}
```

### StepUpdateRequest (NEW)

```typescript
export interface StepUpdateRequest {
  title?: string;
  description?: string;
  dependencies?: string[];
}
```

### StepReorderRequest (NEW)

```typescript
export interface StepReorderRequest {
  step_ids: string[];
}
```

### PlanApproveRequest (EXTENDED)

```typescript
export interface PlanApproveRequest {
  step_ids?: string[];           // NEW — undefined means approve all
}
```

### ThinkingEvent (EXTENDED)

```typescript
export type ThinkingPhase = 'researching' | 'planning' | 'refining';

// NEW SSE event types
export interface ToolsUsedEvent {
  tool_name: string;
  duration_ms: number;
}

export interface ContextGatheredEvent {
  sources: string[];
}

export interface PlanDiffEvent {
  added: string[];      // step_ids
  removed: string[];    // step_ids
  changed: string[];    // step_ids
}
```

## State Transitions

### Plan Status Lifecycle

```
                    ┌──────────┐
         ┌────────▶│  draft    │◀──────────┐
         │         └─────┬────┘           │
         │               │                │
    (version++)     approve            refine
         │               │            (save_plan)
         │               ▼
         │         ┌──────────┐
         └─────────│ approved  │
                   └─────┬────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        ┌──────────┐         ┌──────────┐
        │completed │         │  failed   │
        └──────────┘         └──────────┘
```

### Version Increment Rules

1. `save_plan()` is called → snapshot current state → increment `version` → overwrite
2. Step CRUD mutations (add/edit/delete/reorder) → snapshot → increment → apply change
3. Version is monotonically increasing; no rollback support (historical versions are read-only)

## Validation Rules

### DAG Validation (applied on every dependency-modifying mutation)

1. All `dependencies` reference valid `step_id` values within the same plan
2. No self-references (step cannot depend on itself)
3. No circular dependencies (Kahn's algorithm: sorted count must equal input count)
4. Validation failure returns HTTP 422 with cycle details

### Step Position Constraints

1. Positions are 0-indexed, contiguous, and unique within a plan
2. Reorder operations must include all step IDs (no partial reorder)
3. Add step: default position = max(existing positions) + 1
4. Delete step: remaining positions are compacted (no gaps)
