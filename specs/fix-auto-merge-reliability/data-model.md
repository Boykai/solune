# Data Model: Fix Auto-Merge Reliability (4 Root Causes)

**Feature**: Fix Auto-Merge Reliability | **Date**: 2026-04-06

## Overview

This feature does **not** introduce new entities or schema changes. All changes operate on existing data models and infrastructure. This document catalogs the existing entities involved and how each phase interacts with them.

## Existing Entities (No Changes)

### PipelineState

**Location**: `solune/backend/src/services/workflow_orchestrator/models.py`

| Field | Type | Relevance |
|-------|------|-----------|
| `issue_number` | `int` | Primary key — used for state lookup/removal |
| `project_id` | `str` | Used for project-level auto-merge check |
| `auto_merge` | `bool` | Pipeline-level auto-merge flag (default: `False`) |
| `is_complete` | `property → bool` | Checked by webhook helper to gate merge eligibility |
| `agents` | `list[str]` | Pipeline agent sequence |
| `current_agent_index` | `int` | Tracks pipeline progress |

**Storage layers**:
- **L1**: `BoundedDict[int, PipelineState]` in `pipeline_state_store._pipeline_states` (maxlen=50,000)
- **L2**: SQLite `pipeline_states` table with `metadata` JSON column containing `auto_merge`

**Impact**: Phase 3 defers removal of `PipelineState` from both L1 and L2 when merge returns `retry_later`.

### MainBranchInfo

**Location**: `solune/backend/src/services/workflow_orchestrator/models.py`

| Field | Type | Relevance |
|-------|------|-----------|
| `pr_number` | `int` | Used by `_resolve_issue_for_pr()` to map PR → issue |
| `branch` | `str` | Main branch name |
| `owner` | `str` | Repository owner |
| `repo` | `str` | Repository name |

**Storage**: `BoundedDict[int, MainBranchInfo]` in `pipeline_state_store._issue_main_branches`

**Impact**: Phase 2 uses this cache to resolve `issue_number` → `project_id` chain.

### ProjectSettings (auto_merge column)

**Location**: SQLite `project_settings` table

| Column | Type | Relevance |
|--------|------|-----------|
| `project_id` | `TEXT` | Foreign key to GitHub project |
| `auto_merge` | `INTEGER` | 0/1 — project-level auto-merge toggle |
| `github_user_id` | `TEXT` | `'__workflow__'` for canonical row |

**Impact**: Phase 2 Step C calls `is_auto_merge_enabled()` which queries this table.

## State Lifecycle Changes (Phase 3)

### Current Flow (Broken)

```
_transition_after_pipeline_complete()
  ├── capture auto_merge flag
  ├── remove_pipeline_state()     ← ALWAYS removes here
  ├── dequeue next pipeline
  └── attempt auto-merge
       ├── merged → transition to Done
       ├── retry_later → schedule retry loop
       │    └── retry loop cannot find state (already removed!)
       ├── devops_needed → dispatch devops
       └── merge_failed → broadcast failure
```

### New Flow (Fixed)

```
_transition_after_pipeline_complete()
  ├── capture auto_merge flag
  ├── IF auto_merge NOT active:
  │    └── remove_pipeline_state()     ← immediate removal (unchanged)
  ├── dequeue next pipeline
  └── IF auto_merge active:
       ├── attempt auto-merge
       │    ├── merged → remove state → transition to Done
       │    ├── retry_later → DO NOT remove → schedule retry loop
       │    │    └── retry loop terminals all call remove_pipeline_state()
       │    ├── devops_needed → remove state → dispatch devops
       │    └── merge_failed → remove state → broadcast failure
       └── (finally safety net: remove state if still present)
```

## In-Memory State Changes (Phase 1)

### Retry Constants

| Constant | Location | Old | New |
|----------|----------|-----|-----|
| `MAX_AUTO_MERGE_RETRIES` | `state.py:209` | `3` | `5` |
| `AUTO_MERGE_RETRY_BASE_DELAY` | `state.py:210` | `60.0` | `45.0` |

### Retry Tracking

| Dict | Location | Change |
|------|----------|--------|
| `_pending_auto_merge_retries` | `state.py:206` | No change — same BoundedDict, just more attempts |

## Lookup Chain Changes (Phase 2)

### Current Webhook Lookup

```
_get_auto_merge_pipeline(issue_number)
  └── L1: get_pipeline_state(issue_number)
       └── Returns PipelineState or None
```

### New Webhook Lookup

```
_get_auto_merge_pipeline(issue_number, owner, repo)  [now async]
  ├── L1: get_pipeline_state(issue_number)
  │    └── HIT → return metadata dict
  ├── L2: get_pipeline_state_async(issue_number)
  │    └── HIT → return metadata dict (with auto_merge from SQLite)
  └── Project: is_auto_merge_enabled(db, project_id)
       └── HIT → return metadata dict (project-level auto-merge)
```

## Validation Rules

No new validation rules. Existing rules unchanged:
- `auto_merge` must be `bool` (default `False`)
- `MAX_AUTO_MERGE_RETRIES` must be positive integer
- `AUTO_MERGE_RETRY_BASE_DELAY` must be positive float

## State Transitions

No new states. Existing `AutoMergeResult.status` values unchanged:
- `merged` — PR successfully squash-merged
- `retry_later` — CI pending or mergeability unknown
- `devops_needed` — CI failure or merge conflict
- `merge_failed` — Merge API call failed
- `skipped` — No eligible PR found
