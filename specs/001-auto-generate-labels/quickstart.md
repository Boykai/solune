# Quickstart: Auto-generate Labels for GitHub Parent Issues

**Feature**: 001-auto-generate-labels
**Date**: 2026-03-31
**Prerequisites**: [plan.md](./plan.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

## Overview

This feature adds a centralized `LabelClassificationService` that uses the existing AI completion provider to auto-generate content-based labels for parent GitHub issues. All three issue creation paths (pipeline launch, task creation, agent tool) call this shared service instead of hardcoding labels or applying none.

## New Files

### 1. `solune/backend/src/services/label_classifier.py`

The core service module. Contains:
- `classify_labels(title, description, *, github_token) -> list[str]` — Main async function
- `validate_labels(raw_labels: list[str]) -> list[str]` — Pure validation/dedup function
- `TYPE_LABELS`, `DEFAULT_TYPE_LABEL`, `ALWAYS_INCLUDED_LABEL` — Category constants

### 2. `solune/backend/src/prompts/label_classification.py`

Prompt template for the AI classifier. Dynamically injects the label taxonomy from `constants.LABELS` to satisfy FR-010. Returns a JSON object with a `labels` array.

### 3. `solune/backend/tests/unit/test_label_classifier.py`

Unit tests covering:
- Valid classification with mocked AI response
- Fallback on AI failure
- Validation: taxonomy filtering, dedup, type label default, "ai-generated" guarantee
- Empty/whitespace input handling

## Modified Files

### 1. `solune/backend/src/api/pipelines.py` — `execute_pipeline_launch()`

**Before** (~line 346):
```python
issue_labels = ["ai-generated"]
if _pipeline_name:
    issue_labels.append(build_pipeline_label(_pipeline_name))
```

**After**:
```python
from src.services.label_classifier import classify_labels

issue_labels = await classify_labels(
    title=issue_title_override or _derive_issue_title(issue_description),
    description=issue_description,
    github_token=session.access_token,
)
if _pipeline_name:
    pipeline_label = build_pipeline_label(_pipeline_name)
    if pipeline_label not in issue_labels:
        issue_labels.append(pipeline_label)
```

### 2. `solune/backend/src/api/tasks.py` — `create_task()`

**Before** (~line 103):
```python
issue = await github_projects_service.create_issue(
    access_token=session.access_token,
    owner=owner,
    repo=repo,
    title=request.title,
    body=request.description or "",
)
```

**After**:
```python
from src.services.label_classifier import classify_labels

issue_labels = await classify_labels(
    title=request.title,
    description=request.description or "",
    github_token=session.access_token,
)

issue = await github_projects_service.create_issue(
    access_token=session.access_token,
    owner=owner,
    repo=repo,
    title=request.title,
    body=request.description or "",
    labels=issue_labels,
)
```

### 3. `solune/backend/src/services/agent_tools.py` — `create_project_issue()`

**Before** (~line 388):
```python
async def create_project_issue(
    context: FunctionInvocationContext,
    title: str,
    body: str,
) -> ToolResult:
```

**After**:
```python
async def create_project_issue(
    context: FunctionInvocationContext,
    title: str,
    body: str,
    labels: list[str] | None = None,
) -> ToolResult:
```

And before the `create_issue` call:
```python
from src.services.label_classifier import classify_labels

if labels:
    issue_labels = labels
else:
    issue_labels = await classify_labels(
        title=title,
        description=body,
        github_token=github_token,
    )

issue = await service.create_issue(
    ...,
    labels=issue_labels,
)
```

## Implementation Order

1. **Create `label_classifier.py`** — Core service with `classify_labels()` and `validate_labels()`
2. **Create `label_classification.py`** — Prompt template
3. **Create `test_label_classifier.py`** — Unit tests for the service
4. **Modify `pipelines.py`** — Integrate classifier into pipeline launch path
5. **Modify `tasks.py`** — Integrate classifier into task creation path
6. **Modify `agent_tools.py`** — Add `labels` parameter and classifier integration

## Verification

After implementation, verify each path:

```bash
# Run unit tests
cd solune/backend
uv run pytest tests/unit/test_label_classifier.py -v

# Run existing tests to confirm no regressions
uv run pytest tests/unit/ -v --tb=short

# Lint
uv run ruff check src/services/label_classifier.py src/prompts/label_classification.py
uv run pyright src/services/label_classifier.py
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Use `CompletionProvider` (not Agent Framework) | Single-shot classification doesn't need multi-turn agent conversation |
| Truncate description to 2,000 chars | Balance between accuracy and token cost; first 2K chars contain core intent |
| JSON output from AI | Reliably parseable; avoids comma/whitespace edge cases |
| `validate_labels()` as pure function | Testable in isolation; can be reused outside AI path |
| Fallback to `["ai-generated", "feature"]` | Minimum valid label set per spec invariants |
| No caching | Each issue has unique content; cache hit rate would be near zero |
