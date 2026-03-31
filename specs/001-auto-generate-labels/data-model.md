# Data Model: Auto-generate Labels for GitHub Parent Issues

**Feature**: 001-auto-generate-labels
**Date**: 2026-03-31
**Prerequisites**: [research.md](./research.md)

## Entities

### LabelTaxonomy (Existing — No Changes)

The predefined label taxonomy is the single source of truth for valid labels. It already exists in `src/constants.py` as the `LABELS` constant.

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| Type labels | `list[str]` | `constants.LABELS` | `feature`, `bug`, `enhancement`, `refactor`, `documentation`, `testing`, `infrastructure` |
| Scope labels | `list[str]` | `constants.LABELS` | `frontend`, `backend`, `database`, `api` |
| Domain labels | `list[str]` | `constants.LABELS` | `security`, `performance`, `accessibility`, `ux` |
| Status labels | `list[str]` | `constants.LABELS` | `ai-generated`, `sub-issue`, `good first issue`, `help wanted` |
| State labels | `list[str]` | `constants.LABELS` | `active`, `stalled` |

**Category Constants** (new, to be defined in `label_classifier.py` for validation):

```python
TYPE_LABELS: set[str] = {"feature", "bug", "enhancement", "refactor", "documentation", "testing", "infrastructure"}
DEFAULT_TYPE_LABEL: str = "feature"
ALWAYS_INCLUDED_LABEL: str = "ai-generated"
```

---

### LabelClassificationRequest (New — Input to Classifier)

Represents the input to the label classification service.

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `title` | `str` | Yes | max 256 chars | Issue title for classification |
| `description` | `str` | No | Truncated to 2,000 chars internally | Issue description/body for additional context |

**Validation Rules**:
- `title` must be non-empty after stripping whitespace
- If both `title` and `description` are empty/whitespace, return default labels without calling AI
- `description` is truncated to 2,000 characters before being sent to the AI prompt

---

### LabelClassificationResult (New — Output from Classifier)

Represents the validated output from the label classification service.

| Field | Type | Guaranteed | Description |
|-------|------|------------|-------------|
| `labels` | `list[str]` | Yes | Validated, deduplicated label list |

**Invariants** (post-processing guarantees):
1. All labels are present in `constants.LABELS` (invalid labels filtered out)
2. `"ai-generated"` is always present (inserted at index 0 if missing)
3. Exactly one type label is present (defaults to `"feature"` if none classified)
4. No duplicate labels
5. Label order: `"ai-generated"` first, then type label, then scope/domain labels

---

### IssueCreationPath (Existing — Behavioral Reference)

Documents the three existing paths and how they change.

| Path | File | Function | Current Labels | After Change |
|------|------|----------|----------------|--------------|
| Pipeline Launch | `src/api/pipelines.py` | `execute_pipeline_launch()` | `["ai-generated"] + pipeline:<name>` | `classified_labels + pipeline:<name>` (merged, deduplicated) |
| Task Creation | `src/api/tasks.py` | `create_task()` | (none) | `classified_labels` |
| Agent Tool | `src/services/agent_tools.py` | `create_project_issue()` | (none) | `agent_labels or classified_labels` |
| Recommendation | `src/services/workflow_orchestrator/orchestrator.py` | `_build_labels()` | AI-generated via metadata | **No change** |

---

## Relationships

```text
constants.LABELS (source of truth)
    │
    ├── Referenced by: LabelClassificationService (prompt + validation)
    ├── Referenced by: IssueLabel enum (models/recommendation.py)
    └── Referenced by: issue_generation.py prompt (existing)

LabelClassificationService
    │
    ├── Input: LabelClassificationRequest (title, description)
    ├── Output: LabelClassificationResult (validated labels)
    ├── Depends on: CompletionProvider (AI inference)
    ├── Depends on: constants.LABELS (taxonomy validation)
    │
    ├── Called by: pipelines.py → execute_pipeline_launch()
    ├── Called by: tasks.py → create_task()
    └── Called by: agent_tools.py → create_project_issue()
```

## State Transitions

This feature does not introduce new stateful entities. Label classification is a stateless, one-shot operation during issue creation. No persistence, caching, or state management is needed.

The issue creation flow state is:

```text
[User Action] → [Path Handler] → [classify_labels(title, desc)]
                                       │
                                       ├── Success → validated labels
                                       └── Failure → fallback labels
                                       │
                                  [merge with path-specific labels]
                                       │
                                  [create_issue(labels=merged)]
```
