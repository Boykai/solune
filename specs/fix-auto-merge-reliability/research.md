# Research: Fix Auto-Merge Reliability (4 Root Causes)

**Feature**: Fix Auto-Merge Reliability | **Date**: 2026-04-06

## Research Tasks

### R1: Retry Window Coverage for Slow CI

**Question**: What retry constants provide adequate coverage for CI suites up to 15 minutes?

**Finding**: Current constants (`MAX_AUTO_MERGE_RETRIES=3`, `AUTO_MERGE_RETRY_BASE_DELAY=60.0`) yield a total backoff of 60 + 120 + 240 = 420s (~7 min). This is insufficient for CI suites exceeding 7 minutes.

**Decision**: `MAX_AUTO_MERGE_RETRIES=5`, `AUTO_MERGE_RETRY_BASE_DELAY=45.0`
**Rationale**: Exponential backoff: 45 + 90 + 180 + 360 + 720 = 1395s (~23.25 min). Covers 15-min CI with 8-min margin. First retry at 45s is faster than current 60s for quick CI completions.

**Alternatives considered**:
- 60s × 5 retries = 60 + 120 + 240 + 480 + 960 = 1860s (~31 min) — first retry too slow, total excessive
- 30s × 7 retries = 30 + 60 + 120 + 240 + 480 + 960 + 1920 = 3810s (~63 min) — too many attempts, excessive total
- 45s × 4 retries = 45 + 90 + 180 + 360 = 675s (~11.25 min) — insufficient for 15-min CI

---

### R2: L2 SQLite Fallback for Pipeline State

**Question**: Does `get_pipeline_state_async()` correctly restore the `auto_merge` flag from SQLite?

**Finding**: Yes. The `_row_to_pipeline_state()` function in `pipeline_state_store.py` parses the `metadata` JSON column and extracts `auto_merge` with `metadata.get("auto_merge", False)`. The `_pipeline_state_to_row()` function serializes `auto_merge` into the metadata JSON on write via `set_pipeline_state()`.

**Code evidence**:
- `pipeline_state_store.py:_row_to_pipeline_state()` — line `auto_merge=metadata.get("auto_merge", False)`
- `pipeline_state_store.py:get_pipeline_state_async()` — falls back to SQLite on L1 miss, calls `_row_to_pipeline_state()`
- Existing test: `test_async_get_falls_back_to_sqlite_on_l1_miss()` verifies L2 recovery

**Decision**: Use `get_pipeline_state_async()` as Step B in webhook helper
**Rationale**: Already implemented and tested; no new code needed for L2 lookup itself

---

### R3: Project-Level Auto-Merge Resolution

**Question**: How to resolve `project_id` from `issue_number` when pipeline state is already removed?

**Finding**: The `_issue_main_branches` cache (from `pipeline_state_store.py`) maps `issue_number → MainBranchInfo` containing branch, PR, and repository info. However, it does not directly contain `project_id`. The `project_id` can be resolved from:

1. `get_pipeline_state_async(issue_number)` — returns `PipelineState.project_id` if L2 still has the row
2. `_issue_main_branches` → iterate to match issue → but no `project_id` in `MainBranchInfo`
3. Task registry / project settings queries — more complex

**Decision**: Chain L2 lookup first (Step B gets `project_id` from `PipelineState`), then fall back to scanning project settings if L2 also misses
**Rationale**: L2 will have the state in most cases (removed from L1 but still in SQLite). Only when both L1+L2 miss do we need the project-level fallback. In that case, the webhook already has `owner/repo` which can be used to find the project.

**Alternative considered**: Adding `project_id` to `MainBranchInfo` — requires schema migration and model change

---

### R4: is_auto_merge_enabled() Safety in Webhook Context

**Question**: Is `is_auto_merge_enabled()` safe to call from webhook handlers?

**Finding**: Yes. The function:
- Takes `aiosqlite.Connection` + `project_id` as parameters
- Has a 10-second in-memory TTL cache (`_auto_merge_cache`)
- Queries only the canonical `__workflow__` row in `project_settings`
- Is already called in `_advance_pipeline()` and `_transition_after_pipeline_complete()` (async contexts)

The webhook handlers (`handle_check_run_event`, `handle_check_suite_event`) are already async, so calling an async function is safe.

**Decision**: Reuse `is_auto_merge_enabled()` as Step C
**Rationale**: Already exists, tested, and cached; no new code needed

---

### R5: Deferred Removal vs. Pending State Field

**Question**: Should we add a `PipelineState.merge_pending` field or defer removal?

**Finding**: Adding a field requires:
- Schema migration for the SQLite `pipeline_states` table
- Model change in `PipelineState` dataclass
- Metadata serialization/deserialization updates
- All callers of `is_complete` would need updating

Deferred removal requires:
- Moving `remove_pipeline_state()` call from one location to multiple outcome branches
- Adding `remove_pipeline_state()` to retry loop terminals
- A `finally` safety net in the retry loop

**Decision**: Deferred removal
**Rationale**: Simpler — no schema changes, no model changes, no migration. The retry loop already has clear terminal points (merged, devops_needed, merge_failed, exhausted).

---

### R6: Impact on Existing remove_pipeline_state Callers

**Question**: Are there other callers of `remove_pipeline_state()` that need adjustment?

**Finding**: `remove_pipeline_state()` is called in 5 locations in `pipeline.py`:
1. **Line 1932** — `_handle_transition_result()` after status transition (unrelated to auto-merge path)
2. **Line 2166** — `_advance_pipeline()` when queue-mode pipeline is queued (unrelated)
3. **Line 2256** — `_advance_pipeline()` on pipeline completion (separate from transition_after_pipeline_complete)
4. **Line 2507** — `_transition_after_pipeline_complete()` — **THIS IS THE TARGET**
5. Line 1917 — Comment reference only

Only line 2507 needs to be deferred. The other callers are in different code paths and don't interact with auto-merge retry.

**Decision**: Only modify the removal at line 2507
**Rationale**: Surgical change — other callers operate in contexts where state should be removed immediately

---

## Summary

All NEEDS CLARIFICATION items resolved. No unknowns remain. The implementation plan can proceed with high confidence using existing infrastructure:
- `get_pipeline_state_async()` for L2 fallback ✅
- `is_auto_merge_enabled()` for project-level fallback ✅
- Deferred removal pattern for state preservation ✅
- 45s × 5 exponential backoff for retry coverage ✅
