# Implementation Plan: Fix Auto-Merge Reliability (4 Root Causes)

**Branch**: `copilot/fix-auto-merge-reliability` | **Date**: 2026-04-06 | **Spec**: [#983](https://github.com/Boykai/solune/issues/983)
**Input**: Parent issue context — auto-merge fails when CI exceeds 7-minute retry window

## Summary

Auto-merge fails when CI takes longer than the 7-minute retry window. Four compounding root causes are identified: (1) retry budget too short (3 retries × 60s base = ~7 min), (2) pipeline state removed before merge succeeds, (3) webhook fallback only checks L1 cache, and (4) reconstructed pipelines lose the `auto_merge` flag. The fix extends the retry budget to ~23 min, adds L2 + project-level fallback to the webhook helper, and defers pipeline state removal until merge completes.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI, aiosqlite, asyncio
**Storage**: SQLite (write-through L1 `BoundedDict` + L2 SQLite via `pipeline_state_store.py`)
**Testing**: pytest + pytest-asyncio (existing `test_auto_merge.py` — 1292 lines, 12 test classes, ~40 tests)
**Target Platform**: Linux server (Docker)
**Project Type**: Web (backend API + frontend SPA)
**Performance Goals**: Auto-merge must complete within 23 minutes for slow CI suites (15 min CI + margin)
**Constraints**: No new database migrations; reuse existing `is_auto_merge_enabled()` and `get_pipeline_state_async()`
**Scale/Scope**: 4 source files changed, 1 test file extended; ~100 lines of net code change

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Specification-First** | ✅ PASS | Parent issue #983 provides detailed spec with 4 phases, line references, and acceptance criteria |
| **II. Template-Driven Workflow** | ✅ PASS | Following canonical plan template |
| **III. Agent-Orchestrated Execution** | ✅ PASS | Single `speckit.plan` agent producing plan artifacts |
| **IV. Test Optionality** | ✅ PASS | Tests are explicitly requested in Phase 4 of the spec; `test_auto_merge.py` already exists |
| **V. Simplicity and DRY** | ✅ PASS | Deferred removal simpler than adding `PipelineState.merge_pending` field; reuses existing `is_auto_merge_enabled()` |

**Gate result**: ALL PASS — proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/fix-auto-merge-reliability/
├── plan.md              # This file
├── research.md          # Phase 0 — research findings
├── data-model.md        # Phase 1 — data model impact analysis
├── quickstart.md        # Phase 1 — implementation quickstart
└── contracts/           # Phase 1 — no new API contracts needed (internal changes only)
    └── README.md        # Explanation of why no contracts are needed
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   ├── api/
│   │   └── webhooks.py                        # Phase 2: L2 + project-level fallback
│   └── services/
│       ├── copilot_polling/
│       │   ├── state.py                       # Phase 1: retry constants
│       │   ├── auto_merge.py                  # Phase 3: remove_pipeline_state in terminals
│       │   └── pipeline.py                    # Phase 3: deferred removal
│       ├── pipeline_state_store.py            # (read-only — existing L2 fallback)
│       └── settings_store.py                  # (read-only — existing is_auto_merge_enabled)
└── tests/
    └── unit/
        └── test_auto_merge.py                 # Phase 4: new tests
```

**Structure Decision**: Web application layout (backend + frontend). All changes are backend-only in the `solune/backend/` directory. No frontend changes required.

---

## Phase 0: Research & Unknowns Resolution

See [research.md](./research.md) for full findings.

### Resolved Questions

| Question | Resolution |
|----------|------------|
| What retry constants cover 15-min CI? | 45s base × 5 retries (exponential): 45 + 90 + 180 + 360 + 720 = 1395s ≈ 23 min |
| Does `get_pipeline_state_async()` restore `auto_merge`? | Yes — `_row_to_pipeline_state()` parses `metadata` JSON, extracts `auto_merge` (default `False`) |
| How to resolve `project_id` from issue number? | `_issue_main_branches[issue_number]` contains `pr_number`; `get_pipeline_state_async()` returns `PipelineState.project_id` |
| Is `is_auto_merge_enabled()` safe to call from webhooks? | Yes — only needs `aiosqlite.Connection` + `project_id`; has 10s TTL cache |
| Does `remove_pipeline_state()` affect retry loop? | Yes — L1 removal prevents webhook from finding state; L2 deletion prevents async recovery |

---

## Phase 1: Extend Retry Window (Root Cause #1)

**File**: `solune/backend/src/services/copilot_polling/state.py` (lines 208-209)

### Changes

| Constant | Current | New | Rationale |
|----------|---------|-----|-----------|
| `MAX_AUTO_MERGE_RETRIES` | 3 | 5 | 5 retries × exponential backoff = 23 min total coverage |
| `AUTO_MERGE_RETRY_BASE_DELAY` | 60.0 | 45.0 | Faster first retry (45s) while still covering 15-min CI at attempt 5 |

### New Backoff Schedule

| Attempt | Delay (s) | Cumulative (s) | Cumulative (min) |
|---------|-----------|-----------------|-------------------|
| 1 | 45 | 45 | 0.75 |
| 2 | 90 | 135 | 2.25 |
| 3 | 180 | 315 | 5.25 |
| 4 | 360 | 675 | 11.25 |
| 5 | 720 | 1395 | 23.25 |

**Coverage**: 23.25 min total > 15 min CI + 8 min margin ✅

### Dependencies

- None (standalone constant change)

---

## Phase 2: Webhook L2 + Project-Level Fallback (Root Causes #2 + #3)

**File**: `solune/backend/src/api/webhooks.py` (lines 49-72, 823, 917)

### Problem

`_get_auto_merge_pipeline()` only checks L1 cache via `get_pipeline_state()`. When pipeline state is evicted from L1 (BoundedDict capacity) or removed prematurely, the webhook cannot trigger auto-merge on CI completion events.

### Solution

Make `_get_auto_merge_pipeline()` async with 3-tier fallback:

```
Step A: L1 cache — get_pipeline_state(issue_number)         [sync, fast]
Step B: L2 SQLite — get_pipeline_state_async(issue_number)  [async, recovers from L1 miss]
Step C: Project-level — is_auto_merge_enabled(db, project_id) [async, fallback when state removed]
```

### Detailed Design

1. **Function signature change**: `def _get_auto_merge_pipeline(issue_number)` → `async def _get_auto_merge_pipeline(issue_number, owner, repo)`
2. **Step A** (existing): `_cp.get_pipeline_state(issue_number)` — returns `PipelineState | None`
3. **Step B** (new): On L1 miss, call `get_pipeline_state_async(issue_number)` from `pipeline_state_store` — restores `auto_merge` from SQLite metadata JSON
4. **Step C** (new): On A+B miss (state already removed), resolve `project_id` from `_issue_main_branches` cache entry for the issue, then call `is_auto_merge_enabled(db, project_id)` — covers the case where state was removed but project has auto-merge enabled
5. **Caller updates**: Lines 823 and 917 add `await` and pass `owner`, `repo` parameters

### project_id Resolution (Step C)

When pipeline state is gone, resolve `project_id` from `_issue_main_branches`:
- `_resolve_issue_for_pr(pr_num)` already found the `issue_number` by scanning `_issue_main_branches`
- We can also get `project_id` from that same cache entry, or from `get_pipeline_state_async()` if it hits L2

If `_issue_main_branches` doesn't have `project_id`, fall back to the pipeline state store's L2 lookup to extract it from the stored `PipelineState.project_id`.

### Dependencies

- Can proceed in parallel with Phase 1
- Callers at lines 823 and 917 must be updated after function signature change

---

## Phase 3: Defer Pipeline State Removal (Root Cause #2)

**File**: `solune/backend/src/services/copilot_polling/pipeline.py` (lines 2496-2510)
**File**: `solune/backend/src/services/copilot_polling/auto_merge.py` (lines 666-850)

### Problem

`_transition_after_pipeline_complete()` unconditionally calls `_cp.remove_pipeline_state(issue_number)` at line 2507 BEFORE the merge attempt. When merge returns `retry_later`, the state is already gone — subsequent webhook events can't find it, and the retry loop has no state to clean up.

### Solution: Deferred Removal in pipeline.py

Move `_cp.remove_pipeline_state(issue_number)` from line 2507 into each merge outcome branch:

| Merge Outcome | Removal Timing |
|---------------|----------------|
| `auto_merge_active = False` | Remove immediately (unchanged behavior) |
| `merged` | Remove after successful transition to Done |
| `devops_needed` | Remove after DevOps dispatch |
| `merge_failed` | Remove immediately (terminal failure) |
| `retry_later` | **DO NOT REMOVE** — let retry loop handle cleanup |

The existing code at line 2496-2504 already captures `_pipeline_auto_merge` before removal — this logic stays but removal is deferred.

### Solution: Add Removal to Retry Loop Terminals in auto_merge.py

In `_auto_merge_retry_loop()` (lines 692-847), add `remove_pipeline_state()` calls at each terminal:

| Terminal | Location | Action |
|----------|----------|--------|
| `merged` (success) | After Done transition | `_cp.remove_pipeline_state(issue_number)` |
| `devops_needed` | After DevOps dispatch | `_cp.remove_pipeline_state(issue_number)` |
| `merge_failed` | After failure broadcast | `_cp.remove_pipeline_state(issue_number)` |
| Retries exhausted | After exhaustion broadcast | `_cp.remove_pipeline_state(issue_number)` |
| `finally` safety net | End of function | `_cp.remove_pipeline_state(issue_number)` if not already removed |

### Auto-unregister Logic

The auto-unregister block (lines 2509-2526) that checks `count_active_pipelines_for_project()` must also be deferred — it currently runs after `remove_pipeline_state()`. For the `retry_later` path, this block should be skipped (pipeline still active). For immediate-removal paths, the block runs as before.

### Dependencies

- Can proceed in parallel with Phases 1-2
- Retry loop terminal additions depend on understanding the full `_auto_merge_retry_loop` flow (already researched)

---

## Phase 4: Tests

**File**: `solune/backend/tests/unit/test_auto_merge.py` (existing, 1292 lines, 12 test classes)

### New Test Cases

#### 4.1 Retry Window Constants

```python
class TestRetryWindowConstants:
    def test_max_auto_merge_retries_is_five(self):
        assert MAX_AUTO_MERGE_RETRIES == 5

    def test_auto_merge_retry_base_delay_is_45(self):
        assert AUTO_MERGE_RETRY_BASE_DELAY == 45.0

    def test_total_backoff_covers_slow_ci(self):
        total = sum(AUTO_MERGE_RETRY_BASE_DELAY * (2 ** i) for i in range(MAX_AUTO_MERGE_RETRIES))
        assert total >= 900  # At least 15 minutes
```

#### 4.2 Webhook L2 Fallback

```python
class TestWebhookL2Fallback:
    async def test_l1_miss_l2_hit_returns_pipeline(self):
        # L1 returns None, L2 returns PipelineState with auto_merge=True
        # → function returns pipeline metadata dict

    async def test_l1_l2_miss_project_auto_merge_returns_metadata(self):
        # L1 and L2 both return None, but is_auto_merge_enabled() returns True
        # → function returns pipeline metadata dict with project_id

    async def test_all_miss_returns_none(self):
        # L1, L2, and project-level all miss → returns None
```

#### 4.3 Deferred Removal on retry_later

```python
class TestDeferredRemoval:
    async def test_state_not_removed_on_retry_later(self):
        # When merge returns retry_later, pipeline state should still exist in L1

    async def test_state_removed_after_retry_succeeds(self):
        # When retry loop completes with merged, state should be removed

    async def test_state_removed_after_retries_exhausted(self):
        # When retries exhaust, state should be removed
```

### Existing Tests to Update

- `TestAutoMergeRetryLoop.test_retry_succeeds_on_second_attempt` — verify delay values change from 60/120 to 45/90
- `TestAutoMergeRetryLoop.test_retry_exhausted_broadcasts_failure` — verify 5 retries instead of 3

### Verification Commands

```bash
# Targeted test run
pytest tests/unit/test_auto_merge.py -v

# Full backend unit suite
pytest tests/unit/ -v --tb=short

# Linting and type checking
ruff check src/ tests/
ruff format --check src/ tests/
pyright src/
```

---

## Execution Order

```
Phase 1 ──────────────────────> (standalone)
Phase 2 ──────────────────────> (parallel with 1)
Phase 3 ──────────────────────> (parallel with 1-2)
Phase 4 ──────────────────────> (after 1-3 complete)
```

All three code phases can proceed in parallel since they touch different functions/files. Phase 4 (tests) must come after all code changes.

---

## Decisions Log

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| 45s × 5 retries (exponential) | Covers both fast (2m) and slow (15m) CI — 23 min total | 60s × 5 (too slow first retry at 60s); 30s × 7 (too many attempts) |
| Project-level fallback in webhook | Avoids new migration; reuses existing `is_auto_merge_enabled()` | New `auto_merge` column on webhook-specific table (migration overhead) |
| Deferred removal | Simpler than adding `PipelineState.merge_pending` field | New state field (more complex, requires migration) |
| `finally` safety net in retry loop | Prevents state leak if exception occurs mid-retry | Relying solely on explicit removal (risks leak on unexpected errors) |

## Out of Scope

- `_copilot_review_requested_at` in-memory loss — SQLite fallback in `_check_copilot_review_done()` already handles restarts via `copilot_review_requests` table
- Frontend changes — no UI impact from these backend reliability fixes
- New database migrations — all changes reuse existing schema and functions

## Complexity Tracking

> No constitution violations — no entries needed.

## Post-Design Constitution Re-Check

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Specification-First** | ✅ PASS | All changes traced to parent issue #983 with line-level references |
| **II. Template-Driven Workflow** | ✅ PASS | Plan follows canonical template structure |
| **III. Agent-Orchestrated Execution** | ✅ PASS | Single agent producing well-defined artifacts |
| **IV. Test Optionality** | ✅ PASS | Tests explicitly included per Phase 4 spec; extends existing test file |
| **V. Simplicity and DRY** | ✅ PASS | Reuses `is_auto_merge_enabled()`, `get_pipeline_state_async()`; deferred removal simpler than new state field |
