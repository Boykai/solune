# Quickstart: Fix Auto-Merge Reliability (4 Root Causes)

**Feature**: Fix Auto-Merge Reliability | **Date**: 2026-04-06

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Repository cloned at project root

## Files to Modify

| # | File | Phase | Change Description |
|---|------|-------|--------------------|
| 1 | `solune/backend/src/services/copilot_polling/state.py` | 1 | Update `MAX_AUTO_MERGE_RETRIES` (3→5) and `AUTO_MERGE_RETRY_BASE_DELAY` (60→45) |
| 2 | `solune/backend/src/api/webhooks.py` | 2 | Make `_get_auto_merge_pipeline()` async with L2 + project-level fallback; update callers |
| 3 | `solune/backend/src/services/copilot_polling/pipeline.py` | 3 | Defer `remove_pipeline_state()` when auto-merge returns `retry_later` |
| 4 | `solune/backend/src/services/copilot_polling/auto_merge.py` | 3 | Add `remove_pipeline_state()` to all retry loop terminal branches |
| 5 | `solune/backend/tests/unit/test_auto_merge.py` | 4 | Add tests for new retry constants, L2 fallback, deferred removal |

## Implementation Steps

### Step 1: Extend Retry Window (Phase 1)

```python
# state.py — lines 208-209
MAX_AUTO_MERGE_RETRIES: int = 5           # was 3
AUTO_MERGE_RETRY_BASE_DELAY: float = 45.0  # was 60.0
```

### Step 2: Webhook L2 + Project-Level Fallback (Phase 2)

```python
# webhooks.py — replace _get_auto_merge_pipeline (lines 49-72)
async def _get_auto_merge_pipeline(issue_number: int, owner: str, repo: str) -> dict[str, Any] | None:
    # Step A: L1 cache
    pipeline = _cp.get_pipeline_state(issue_number)
    if pipeline and pipeline.is_complete and getattr(pipeline, "auto_merge", False):
        return {"project_id": getattr(pipeline, "project_id", ""), ...}

    # Step B: L2 SQLite fallback
    pipeline = await get_pipeline_state_async(issue_number)
    if pipeline and pipeline.is_complete and getattr(pipeline, "auto_merge", False):
        return {"project_id": getattr(pipeline, "project_id", ""), ...}

    # Step C: Project-level fallback
    # resolve project_id, then check is_auto_merge_enabled()
```

Update callers at lines ~823 and ~917 to use `await` and pass `owner`, `repo`.

### Step 3: Defer Pipeline State Removal (Phase 3)

In `pipeline.py:_transition_after_pipeline_complete()`:
- Remove the unconditional `_cp.remove_pipeline_state(issue_number)` at line 2507
- Add conditional removal based on merge outcome:
  - `auto_merge_active = False` → remove immediately
  - `merged` → remove after Done transition
  - `devops_needed` → remove after dispatch
  - `merge_failed` → remove immediately
  - `retry_later` → **DO NOT remove**

In `auto_merge.py:_auto_merge_retry_loop()`:
- Add `_cp.remove_pipeline_state(issue_number)` after each terminal:
  - merged (after Done transition)
  - devops_needed (after dispatch)
  - merge_failed (after broadcast)
  - retries exhausted (after broadcast)
- Add `finally` safety net

### Step 4: Tests (Phase 4)

Add tests to `test_auto_merge.py` covering:
- `MAX_AUTO_MERGE_RETRIES == 5`, `AUTO_MERGE_RETRY_BASE_DELAY == 45.0`
- Total backoff ≥ 900 seconds
- L2 fallback in webhook (mock L1 miss, L2 hit)
- Project-level fallback (mock L1+L2 miss, project enabled)
- Deferred removal (state persists on `retry_later`)

## Verification

```bash
cd solune/backend

# Run targeted tests
PATH=$HOME/.local/bin:$PATH uv run pytest tests/unit/test_auto_merge.py -v

# Run full backend unit suite
PATH=$HOME/.local/bin:$PATH uv run pytest tests/unit/ -v --tb=short

# Lint and type check
PATH=$HOME/.local/bin:$PATH uv run ruff check src/ tests/
PATH=$HOME/.local/bin:$PATH uv run ruff format --check src/ tests/
PATH=$HOME/.local/bin:$PATH uv run pyright src/
```

## Key APIs Used (Read-Only, No Changes)

| Function | Module | Purpose |
|----------|--------|---------|
| `get_pipeline_state()` | `pipeline_state_store` | L1 cache read (sync) |
| `get_pipeline_state_async()` | `pipeline_state_store` | L2 SQLite fallback (async) |
| `is_auto_merge_enabled()` | `settings_store` | Project-level auto-merge check |
| `remove_pipeline_state()` | `workflow_orchestrator.transitions` | L1+L2 state removal |
| `_resolve_issue_for_pr()` | `webhooks` | PR → issue reverse lookup |
