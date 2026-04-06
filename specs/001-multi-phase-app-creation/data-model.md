# Data Model: Multi-Phase App Creation with Auto-Merge Pipeline Orchestration

**Branch**: `copilot/create-implementation-plan-for-app` | **Date**: 2026-04-06

## Entities

### 1. AppPlanOrchestration (New — SQLite table)

Tracks the lifecycle of a plan-based app creation orchestration.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | TEXT | Primary key (UUID) | NOT NULL, PK |
| app_name | TEXT | App identifier | NOT NULL |
| project_id | TEXT | GitHub Project V2 ID | NOT NULL |
| status | TEXT | Current orchestration state | NOT NULL, DEFAULT 'planning' |
| plan_issue_number | INTEGER | Temporary planning issue number | NULL |
| plan_pr_branch | TEXT | Branch created by speckit.plan PR | NULL |
| plan_md_content | TEXT | Raw plan.md content after fetch | NULL |
| phase_count | INTEGER | Number of phases parsed | NULL |
| phase_issue_numbers | TEXT | JSON array of created phase issue numbers | NULL |
| error_message | TEXT | Error details if failed | NULL |
| created_at | TEXT | ISO 8601 timestamp | NOT NULL |
| updated_at | TEXT | ISO 8601 timestamp | NOT NULL |

**Status state machine**:
```
planning → speckit_running → parsing_phases → creating_issues → launching_pipelines → active
    ↓           ↓                ↓                 ↓                   ↓
  failed      failed           failed            failed              failed
```

**Validation rules**:
- `status` must be one of: `planning`, `speckit_running`, `parsing_phases`, `creating_issues`, `launching_pipelines`, `active`, `failed`
- `plan_issue_number` required when status ≥ `speckit_running`
- `phase_count` required when status ≥ `creating_issues`
- `phase_issue_numbers` must be valid JSON array when present

---

### 2. PlanPhase (New — in-memory dataclass)

Represents a single phase parsed from plan.md. Not persisted — used during orchestration.

| Field | Type | Description |
|-------|------|-------------|
| index | int | Phase number (1-based) |
| title | str | Phase title from heading |
| description | str | Phase description/summary |
| steps | list[str] | Numbered steps within the phase |
| depends_on_phases | list[int] | Phase indices this phase depends on |
| execution_mode | str | "sequential" or "parallel" (within wave) |

**Relationships**:
- Grouped into `waves` by dependency depth for execution ordering
- Each phase maps 1:1 to a GitHub Parent Issue
- Each phase maps 1:1 to a PipelineState with `auto_merge=True`

**State transitions**: N/A (immutable after parsing)

---

### 3. PipelineState (Extended — existing dataclass)

Add `prerequisite_issues` field to the existing `PipelineState` in `workflow_orchestrator/models.py`.

| New Field | Type | Default | Description |
|-----------|------|---------|-------------|
| prerequisite_issues | list[int] | [] | Issue numbers that must have merged PRs before this pipeline can dequeue |

**Serialization**: Stored in the existing `metadata` JSON blob in `pipeline_states` table. Deserialized in `_row_to_pipeline_state()`, serialized in `_pipeline_state_to_row()`.

**Validation rules**:
- All issue numbers in `prerequisite_issues` must reference valid GitHub issues
- An empty list means no prerequisites (standard behavior)
- Dequeue check: all prerequisite issues must have their main PR merged to the default branch

---

### 4. App (Existing — no schema changes)

The existing `App` model (`models/app.py`) is used as-is. The new `POST /apps/create-with-plan` endpoint creates an `App` record with `status=AppStatus.CREATING` and triggers orchestration as a background task.

---

## Relationships

```
AppPlanOrchestration 1──1 App (by app_name)
AppPlanOrchestration 1──* PlanPhase (parsed from plan_md_content)
PlanPhase 1──1 GitHub Issue (phase_issue_numbers[i])
PlanPhase 1──1 PipelineState (by issue_number, with prerequisite_issues)
PipelineState *──* PipelineState (via prerequisite_issues, cross-referencing)
```

## Entity Diagram

```
┌─────────────────────────┐
│ AppPlanOrchestration     │
├─────────────────────────┤
│ id (PK)                 │
│ app_name ───────────────┼──→ App.name
│ project_id              │
│ status                  │
│ plan_issue_number       │
│ plan_md_content         │
│ phase_issue_numbers[]   │──→ [GitHub Issues]
│ created_at / updated_at │
└─────────────────────────┘
         │ parsed from plan_md_content
         ▼
┌─────────────────────────┐
│ PlanPhase (in-memory)    │
├─────────────────────────┤
│ index                   │
│ title                   │
│ depends_on_phases[] ────┼──→ other PlanPhases
│ execution_mode          │
└─────────────────────────┘
         │ 1:1 mapping
         ▼
┌─────────────────────────┐
│ PipelineState (extended) │
├─────────────────────────┤
│ issue_number (existing) │
│ auto_merge = True       │
│ prerequisite_issues[] ──┼──→ other issue_numbers (merge gate)
│ queued (existing)       │
└─────────────────────────┘
```
