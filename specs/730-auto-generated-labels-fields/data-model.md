# Data Model: Auto-Generated Project Labels & Fields on Pipeline Launch

**Feature**: 730-auto-generated-labels-fields  
**Date**: 2026-04-04  
**Status**: Complete  

## Entities

### E1: IssueMetadata (EXISTING — no changes)

**Location**: `solune/backend/src/models/recommendation.py`

| Field | Type | Default | Validation | Description |
|-------|------|---------|------------|-------------|
| priority | IssuePriority | P2 | Enum: P0, P1, P2, P3 | Issue priority level |
| size | IssueSize | M | Enum: XS, S, M, L, XL | Estimated size category |
| estimate_hours | float | 4.0 | ge=0.5, le=40.0 | Estimated hours to complete |
| start_date | str | "" | ISO 8601 YYYY-MM-DD | Suggested start date |
| target_date | str | "" | ISO 8601 YYYY-MM-DD | Target completion date |
| labels | list[str] | ["ai-generated"] | — | Suggested labels |
| assignees | list[str] | [] | — | GitHub usernames |
| milestone | str \| None | None | — | Milestone title |
| branch | str \| None | None | — | Development branch name |

### E2: IssuePriority (EXISTING — no changes)

**Location**: `solune/backend/src/models/recommendation.py`

| Value | Label | Description |
|-------|-------|-------------|
| P0 | Critical | Production down, security breach |
| P1 | High | Major functionality broken |
| P2 | Medium | Default — standard feature/bug work |
| P3 | Low | Nice-to-have, polish |

### E3: IssueSize (EXISTING — no changes)

**Location**: `solune/backend/src/models/recommendation.py`

| Value | Label | Description |
|-------|-------|-------------|
| XS | Extra Small | < 1 hour |
| S | Small | 1-4 hours |
| M | Medium | 1 day |
| L | Large | 1-3 days |
| XL | Extra Large | 3-5 days |

### E4: ClassificationResult (NEW)

**Location**: `solune/backend/src/services/label_classifier.py`

A lightweight dataclass to return labels + optional priority from the extended classifier.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| labels | list[str] | — | Validated label list (same as current classify_labels return) |
| priority | IssuePriority \| None | None | AI-detected priority, or None if not detected |

### E5: PipelineEstimate (NEW — conceptual, returned as IssueMetadata)

**Location**: `solune/backend/src/services/pipeline_estimate.py`

Not a new model class — the `estimate_from_agent_count()` function returns an `IssueMetadata` instance directly.

**Derivation Rules**:

| Input | Output Field | Formula |
|-------|-------------|---------|
| agent_count | estimate_hours | `max(0.5, min(8.0, agent_count * 0.25))` |
| estimate_hours | size | Threshold lookup (see below) |
| — | priority | Default P2 (overridable by AI) |
| — | start_date | `datetime.now(UTC).strftime("%Y-%m-%d")` |
| estimate_hours | target_date | `(today + timedelta(days=max(1, ceil(estimate_hours / 8)))).strftime("%Y-%m-%d")` |

**Size Threshold Lookup**:

| Estimate Range | Size |
|---------------|------|
| ≤ 0.5h       | XS   |
| 0.51-1.0h    | S    |
| 1.01-2.0h    | M    |
| 2.01-4.0h    | L    |
| > 4.0h       | XL   |

## Relationships

```text
execute_pipeline_launch()
  ├── classify_labels_with_priority()  → ClassificationResult
  │     ├── .labels → used for issue creation (existing flow)
  │     └── .priority → merged into IssueMetadata (overrides P2 default)
  ├── estimate_from_agent_count()  → IssueMetadata
  │     └── priority overridden by ClassificationResult.priority if present
  └── set_issue_metadata()  → applies IssueMetadata to project item
        ├── Priority (select field)
        ├── Size (select field)
        ├── Estimate (number field)
        ├── Start date (date field)
        └── Target date (date field)
```

## State Transitions

### Pipeline Launch Metadata Flow

```
[Pipeline Launch Request]
    │
    ▼
[Create Parent Issue with Labels]  ← classify_labels_with_priority()
    │
    ▼
[Add to Project (Backlog)]  ← add_to_project_with_backlog()
    │
    ▼
[Compute Estimate]  ← estimate_from_agent_count(agent_count)
    │
    ▼
[Merge AI Priority]  ← if classification returned priority, override P2
    │
    ▼
[Set Project Fields]  ← set_issue_metadata() (non-blocking)
    │
    ▼
[Continue Pipeline Execution]  ← unchanged from current flow
```

### Label Lifecycle (EXISTING — no changes)

```
[Issue Created]
    │ Labels: [ai-generated, {type}, {scope}, {domain}]
    ▼
[Agent Assigned]
    │ Labels: +agent:{slug}
    ▼
[Agent Swap]
    │ Labels: -agent:{old}, +agent:{new}, -stalled (if present)
    ▼
[Pipeline Stalled]
    │ Labels: +stalled
    ▼
[Pipeline Resumed]
    │ Labels: -stalled, +agent:{new}
    ▼
[Pipeline Complete]
    │ Labels: -pipeline:{labels} (cleanup)
```

## Validation Rules

1. **agent_count** must be ≥ 1 (at least one agent in any pipeline)
2. **estimate_hours** clamped to [0.5, 8.0] by the formula
3. **start_date** and **target_date** must be valid ISO 8601 dates
4. **priority** from AI must be a valid IssuePriority enum value or None
5. **size** must be a valid IssueSize enum value
6. **metadata failures** must not propagate — logged as warnings only
