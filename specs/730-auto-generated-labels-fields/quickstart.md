# Quickstart: Auto-Generated Project Labels & Fields on Pipeline Launch

**Feature**: 730-auto-generated-labels-fields  
**Date**: 2026-04-04  

## Prerequisites

- Python 3.11+
- `uv` package manager
- Backend dependencies installed (`cd solune/backend && uv sync`)
- Access to a GitHub repository with Projects V2 enabled

## Quick Verification

### 1. Run Unit Tests for the New Estimate Module

```bash
cd solune/backend
uv run pytest tests/unit/test_pipeline_estimate.py -v
```

Expected: All tests pass — verifies heuristic formula, size mapping, date calculations.

### 2. Run Updated Label Classifier Tests

```bash
cd solune/backend
uv run pytest tests/unit/test_label_classifier.py -v
```

Expected: Existing tests pass + new priority parsing tests pass.

### 3. Run Pipeline API Tests

```bash
cd solune/backend
uv run pytest tests/unit/test_api_pipelines.py -v
```

Expected: Existing launch tests pass + new metadata integration tests pass.

### 4. Run All Backend Tests

```bash
cd solune/backend
uv run pytest --cov=src --cov-report=json \
  --ignore=tests/property --ignore=tests/fuzz \
  --ignore=tests/chaos --ignore=tests/concurrency
```

Expected: Coverage ≥ 75% (existing threshold), no regressions.

## Implementation Order

### Phase 1: Estimate + Metadata at Launch

1. **Create `pipeline_estimate.py`** (`src/services/pipeline_estimate.py`)
   - `estimate_from_agent_count(agent_count: int) -> IssueMetadata`
   - `size_from_hours(hours: float) -> IssueSize`
   - Pure functions, no I/O, easy to test

2. **Add unit tests** (`tests/unit/test_pipeline_estimate.py`)
   - Test boundary cases: 1, 2, 3, 4, 5, 8, 9, 16, 17, 20 agents
   - Test date calculation (mock `date.today()`)
   - Test `size_from_hours` threshold edges

3. **Integrate into `pipelines.py`**
   - After `add_to_project_with_backlog(ctx)` (~line 431)
   - Call `estimate_from_agent_count(_count_configured_agents(config))`
   - Call `set_issue_metadata()` with the result
   - Wrap in try/except for non-blocking behavior

### Phase 2: AI Priority Override

4. **Extend `label_classification.py` prompt**
   - Add optional `"priority"` key to expected JSON output
   - Add urgency detection rules to system prompt

5. **Add `ClassificationResult` and `classify_labels_with_priority()`** to `label_classifier.py`
   - Backward-compatible — existing `classify_labels()` unchanged
   - New function parses priority from AI response

6. **Integrate AI priority into pipeline launch**
   - Replace `classify_labels()` with `classify_labels_with_priority()` in pipeline path
   - Merge AI priority with heuristic default

### Phase 3: Verification

7. **Verify existing label lifecycle tests**
   - Confirm agent label tests exist for `_swap_agent_labels()`
   - Confirm stalled label tests exist for recovery/resume
   - Add tests only if gaps found

## Key Files

| File | Change Type | Description |
|------|------------|-------------|
| `src/services/pipeline_estimate.py` | NEW | Heuristic estimate from agent count |
| `src/services/label_classifier.py` | MODIFIED | Add ClassificationResult + classify_labels_with_priority() |
| `src/prompts/label_classification.py` | MODIFIED | Extend prompt for optional priority |
| `src/api/pipelines.py` | MODIFIED | Call set_issue_metadata() after project add |
| `tests/unit/test_pipeline_estimate.py` | NEW | Heuristic tests |
| `tests/unit/test_label_classifier.py` | MODIFIED | Priority parsing tests |
| `tests/unit/test_api_pipelines.py` | MODIFIED | Metadata integration tests |

## Configuration

### Adjustable Constants (in `pipeline_estimate.py`)

```python
# Minutes per agent — adjust if pipeline throughput changes
MINUTES_PER_AGENT: float = 15.0

# Working hours per day — used for target date calculation
HOURS_PER_DAY: float = 8.0

# Default priority when AI doesn't detect urgency
DEFAULT_PRIORITY: IssuePriority = IssuePriority.P2
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Project fields empty after launch | `set_issue_metadata()` failed silently | Check backend logs for "Failed to set pipeline metadata" warning |
| Priority always P2 | AI prompt not returning priority | Verify prompt includes priority rules; check AI response format |
| Wrong estimate | Agent count calculation off | Check `_count_configured_agents()` with pipeline config |
| Target date wrong | Timezone issue | Verify UTC date usage in `pipeline_estimate.py` |
