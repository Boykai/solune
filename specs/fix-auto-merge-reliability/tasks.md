# Tasks: Fix Auto-Merge Reliability (4 Root Causes)

**Input**: Design documents from `/specs/fix-auto-merge-reliability/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are explicitly requested in the feature specification (Phase 4) and across all user stories.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app (backend)**: `solune/backend/src/`, `solune/backend/tests/`
- All changes are backend-only; no frontend changes required

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify existing project structure, dependencies, and test infrastructure before making changes

- [ ] T001 Verify existing test suite passes by running `uv run pytest tests/unit/test_auto_merge.py -v` in `solune/backend/`
- [ ] T002 Verify linting and type checking pass by running `uv run ruff check src/ tests/` and `uv run pyright src/` in `solune/backend/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No new foundational infrastructure is needed — all changes reuse existing modules and infrastructure

**⚠️ CRITICAL**: No new database migrations, models, or shared infrastructure required. All phases can proceed in parallel since they touch different functions/files.

**Checkpoint**: Foundation ready — all existing tests pass, user story implementation can begin

---

## Phase 3: User Story 1 — Auto-Merge Succeeds After Slow CI (Priority: P1) 🎯 MVP

**Goal**: Extend the retry budget so auto-merge succeeds for CI suites taking up to 15 minutes, covering ~23 minutes total with exponential backoff (45s, 90s, 180s, 360s, 720s).

**Independent Test**: Create a pipeline with auto-merge enabled and verify the retry constants produce a total backoff window ≥ 900 seconds (15 minutes). Verify fast CI (< 5 min) still merges on first retry.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T003 [P] [US1] Add `TestRetryWindowConstants.test_max_auto_merge_retries_is_five` asserting `MAX_AUTO_MERGE_RETRIES == 5` in `solune/backend/tests/unit/test_auto_merge.py`
- [ ] T004 [P] [US1] Add `TestRetryWindowConstants.test_auto_merge_retry_base_delay_is_45` asserting `AUTO_MERGE_RETRY_BASE_DELAY == 45.0` in `solune/backend/tests/unit/test_auto_merge.py`
- [ ] T005 [P] [US1] Add `TestRetryWindowConstants.test_total_backoff_covers_slow_ci` asserting total exponential backoff `sum(45 * 2**i for i in range(5))` ≥ 900 seconds in `solune/backend/tests/unit/test_auto_merge.py`

### Implementation for User Story 1

- [ ] T006 [US1] Update `MAX_AUTO_MERGE_RETRIES` from `3` to `5` at line ~209 in `solune/backend/src/services/copilot_polling/state.py`
- [ ] T007 [US1] Update `AUTO_MERGE_RETRY_BASE_DELAY` from `60.0` to `45.0` at line ~210 in `solune/backend/src/services/copilot_polling/state.py`
- [ ] T008 [US1] Run `uv run pytest tests/unit/test_auto_merge.py -v -k TestRetryWindowConstants` in `solune/backend/` to verify new tests pass

**Checkpoint**: Retry window extended to ~23 minutes. Fast CI still merges quickly. US1 is fully functional and independently testable.

---

## Phase 4: User Story 2 — Auto-Merge Recovers After State Eviction (Priority: P2)

**Goal**: Add L2 (SQLite) and project-level fallback to `_get_auto_merge_pipeline()` so auto-merge intent is recovered even when the in-memory cache is evicted or the service restarts.

**Independent Test**: Simulate an L1 cache miss by clearing in-memory state, trigger a CI completion webhook, and verify the system recovers auto-merge intent from persistent storage (L2 SQLite) or project-level settings.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T009 [P] [US2] Add `TestWebhookL2Fallback.test_l1_miss_l2_hit_returns_pipeline` — mock `get_pipeline_state()` returning `None`, mock `get_pipeline_state_async()` returning `PipelineState` with `auto_merge=True`, assert function returns metadata dict in `solune/backend/tests/unit/test_auto_merge.py`
- [ ] T010 [P] [US2] Add `TestWebhookL2Fallback.test_l1_l2_miss_project_auto_merge_returns_metadata` — mock both L1 and L2 returning `None`, mock `is_auto_merge_enabled()` returning `True`, assert function returns metadata dict with `project_id` in `solune/backend/tests/unit/test_auto_merge.py`
- [ ] T011 [P] [US2] Add `TestWebhookL2Fallback.test_all_miss_returns_none` — mock L1, L2, and project-level all returning `None`/`False`, assert function returns `None` in `solune/backend/tests/unit/test_auto_merge.py`

### Implementation for User Story 2

- [ ] T012 [US2] Change `_get_auto_merge_pipeline()` signature from `def _get_auto_merge_pipeline(issue_number: int)` to `async def _get_auto_merge_pipeline(issue_number: int, owner: str, repo: str)` in `solune/backend/src/api/webhooks.py` (lines ~49-72). Only two callers exist (T015, T016 below) — confirmed via research.md R6
- [ ] T013 [US2] Add Step B (L2 fallback) — on L1 miss, call `get_pipeline_state_async(issue_number)` from `pipeline_state_store` to recover `auto_merge` from SQLite metadata JSON in `solune/backend/src/api/webhooks.py`
- [ ] T014 [US2] Add Step C (project-level fallback) — on L1+L2 miss, resolve `project_id` from `_issue_main_branches` or L2 state, then call `is_auto_merge_enabled(db, project_id)` in `solune/backend/src/api/webhooks.py`
- [ ] T015 [US2] Update caller at line ~823 in `handle_check_run_event` to use `await _get_auto_merge_pipeline(issue_number, owner, repo)` in `solune/backend/src/api/webhooks.py`
- [ ] T016 [US2] Update caller at line ~917 in `handle_check_suite_event` to use `await _get_auto_merge_pipeline(issue_number, owner, repo)` in `solune/backend/src/api/webhooks.py`
- [ ] T017 [US2] Run `uv run pytest tests/unit/test_auto_merge.py -v -k TestWebhookL2Fallback` in `solune/backend/` to verify new tests pass

**Checkpoint**: Webhook recovers auto-merge intent from L2 SQLite and project-level settings. L1 cache misses no longer cause silent merge failures.

---

## Phase 5: User Story 3 — Pipeline State Preserved During Retry (Priority: P2)

**Goal**: Defer `remove_pipeline_state()` when auto-merge returns `retry_later` so the retry loop and incoming webhook events can still find the pipeline state. Remove state only at terminal outcomes.

**Independent Test**: Trigger a merge attempt that returns `retry_later` and verify the pipeline state still exists in L1 cache. Then verify state is removed after a terminal outcome (merged, failed, exhausted).

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T018 [P] [US3] Add `TestDeferredRemoval.test_state_not_removed_on_retry_later` — verify pipeline state remains in L1 after `_transition_after_pipeline_complete` returns `retry_later` in `solune/backend/tests/unit/test_auto_merge.py`
- [ ] T019 [P] [US3] Add `TestDeferredRemoval.test_state_removed_after_retry_succeeds` — verify pipeline state is removed from L1 after retry loop completes with `merged` in `solune/backend/tests/unit/test_auto_merge.py`
- [ ] T020 [P] [US3] Add `TestDeferredRemoval.test_state_removed_after_retries_exhausted` — verify pipeline state is removed from L1 after all retries are exhausted in `solune/backend/tests/unit/test_auto_merge.py`
- [ ] T021 [P] [US3] Add `TestDeferredRemoval.test_state_removed_on_merge_failed` — verify pipeline state is removed immediately on `merge_failed` outcome in `solune/backend/tests/unit/test_auto_merge.py`
- [ ] T022 [P] [US3] Add `TestDeferredRemoval.test_finally_safety_net_removes_state` — verify `finally` block in retry loop removes state if not already removed in `solune/backend/tests/unit/test_auto_merge.py`

### Implementation for User Story 3

- [ ] T023 [US3] Remove unconditional `_cp.remove_pipeline_state(issue_number)` call at line ~2507 in `solune/backend/src/services/copilot_polling/pipeline.py`
- [ ] T024 [US3] Add immediate `remove_pipeline_state()` when `auto_merge_active is False` (unchanged behavior) in `_transition_after_pipeline_complete()` in `solune/backend/src/services/copilot_polling/pipeline.py`
- [ ] T025 [US3] Add `remove_pipeline_state()` to `merged` outcome branch (after Done transition) in `_transition_after_pipeline_complete()` in `solune/backend/src/services/copilot_polling/pipeline.py`
- [ ] T026 [US3] Add `remove_pipeline_state()` to `devops_needed` outcome branch (after DevOps dispatch) in `_transition_after_pipeline_complete()` in `solune/backend/src/services/copilot_polling/pipeline.py`
- [ ] T027 [US3] Add `remove_pipeline_state()` to `merge_failed` outcome branch in `_transition_after_pipeline_complete()` in `solune/backend/src/services/copilot_polling/pipeline.py`
- [ ] T028 [US3] Skip `remove_pipeline_state()` and auto-unregister block for `retry_later` outcome — let retry loop handle cleanup in `solune/backend/src/services/copilot_polling/pipeline.py`
- [ ] T029 [US3] Add `_cp.remove_pipeline_state(issue_number)` after `merged` terminal (after Done transition) in `_auto_merge_retry_loop()` in `solune/backend/src/services/copilot_polling/auto_merge.py`
- [ ] T030 [US3] Add `_cp.remove_pipeline_state(issue_number)` after `devops_needed` terminal (after DevOps dispatch) in `_auto_merge_retry_loop()` in `solune/backend/src/services/copilot_polling/auto_merge.py`
- [ ] T031 [US3] Add `_cp.remove_pipeline_state(issue_number)` after `merge_failed` terminal (after failure broadcast) in `_auto_merge_retry_loop()` in `solune/backend/src/services/copilot_polling/auto_merge.py`
- [ ] T032 [US3] Add `_cp.remove_pipeline_state(issue_number)` after retries-exhausted terminal (after exhaustion broadcast) in `_auto_merge_retry_loop()` in `solune/backend/src/services/copilot_polling/auto_merge.py`
- [ ] T033 [US3] Add `finally` safety net at end of `_auto_merge_retry_loop()` to call `_cp.remove_pipeline_state(issue_number)` if not already removed in `solune/backend/src/services/copilot_polling/auto_merge.py`
- [ ] T034 [US3] Run `uv run pytest tests/unit/test_auto_merge.py -v -k TestDeferredRemoval` in `solune/backend/` to verify new tests pass

**Checkpoint**: Pipeline state persists during retry_later — retry loop and webhooks can find it. State is cleaned up at all terminal outcomes. No state leaks.

---

## Phase 6: User Story 4 — Existing Auto-Merge Behavior Preserved (Priority: P3)

**Goal**: Verify all existing auto-merge tests (~40 tests across 12 test classes) pass without modification. Confirm no regressions for fast CI, immediate merge, manual override, and auto-merge-disabled paths.

**Independent Test**: Run the full existing `test_auto_merge.py` test suite and verify 100% pass rate. Run the full backend unit suite to confirm no cross-module regressions.

### Implementation for User Story 4

- [ ] T035 [US4] Update existing `TestAutoMergeRetryLoop.test_retry_succeeds_on_second_attempt` if delay assertions change from 60/120 to 45/90 in `solune/backend/tests/unit/test_auto_merge.py`
- [ ] T036 [US4] Update existing `TestAutoMergeRetryLoop.test_retry_exhausted_broadcasts_failure` if retry count assertions change from 3 to 5 in `solune/backend/tests/unit/test_auto_merge.py`
- [ ] T037 [US4] Run `uv run pytest tests/unit/test_auto_merge.py -v` in `solune/backend/` — all existing + new tests must pass
- [ ] T038 [US4] Run `uv run pytest tests/unit/ -v --tb=short` in `solune/backend/` — full backend suite (4941+ tests) must pass

**Checkpoint**: All existing behavior preserved. No regressions in fast CI merges, disabled auto-merge, or manual override workflows.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final verification, linting, type checking, and cleanup across all changed files

- [ ] T039 Run `uv run ruff check src/ tests/` in `solune/backend/` — no lint errors
- [ ] T040 Run `uv run ruff format --check src/ tests/` in `solune/backend/` — formatting clean
- [ ] T041 Run `uv run pyright src/` in `solune/backend/` — no type errors
- [ ] T042 Review all changed files for consistency: `state.py`, `webhooks.py`, `pipeline.py`, `auto_merge.py`, `test_auto_merge.py`
- [ ] T043 Run quickstart.md validation — execute all verification commands from `specs/fix-auto-merge-reliability/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — verify existing state immediately
- **Foundational (Phase 2)**: No blocking prerequisites — existing infrastructure is sufficient
- **US1 (Phase 3)**: Can start after Setup — standalone constant change in `state.py`
- **US2 (Phase 4)**: Can start after Setup — parallel with US1 (different file: `webhooks.py`)
- **US3 (Phase 5)**: Can start after Setup — parallel with US1 and US2 (different files: `pipeline.py`, `auto_merge.py`)
- **US4 (Phase 6)**: Depends on US1 + US2 + US3 completion — verifies all changes together
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories — `state.py` only
- **User Story 2 (P2)**: No dependencies on other stories — `webhooks.py` only
- **User Story 3 (P2)**: No dependencies on other stories — `pipeline.py` + `auto_merge.py` only
- **User Story 4 (P3)**: Depends on US1 + US2 + US3 — regression verification

### Within Each User Story

- Tests MUST be written and FAIL before implementation (T003-T005 before T006-T007, etc.)
- Implementation tasks within a story are sequential (signature change before logic, etc.)
- Verification run at end of each story phase

### Parallel Opportunities

```
Phase 3 (US1: state.py) ──────────────> T003-T008
Phase 4 (US2: webhooks.py) ───────────> T009-T017    ← parallel with US1
Phase 5 (US3: pipeline.py/auto_merge.py) ─> T018-T034 ← parallel with US1 + US2
Phase 6 (US4: regression) ───────────────────────────> T035-T038 (after US1-3)
Phase 7 (Polish) ────────────────────────────────────> T039-T043 (after US4)
```

- All test tasks within a story marked [P] can run in parallel (different test classes)
- US1, US2, US3 implementation can proceed in parallel (different source files, no dependencies)
- US4 must wait for all code changes to complete

---

## Parallel Example: User Story 1

```bash
# Launch all tests for US1 together (they are [P] — different test methods):
Task T003: "TestRetryWindowConstants.test_max_auto_merge_retries_is_five"
Task T004: "TestRetryWindowConstants.test_auto_merge_retry_base_delay_is_45"
Task T005: "TestRetryWindowConstants.test_total_backoff_covers_slow_ci"

# Then implementation (sequential within story):
Task T006: "Update MAX_AUTO_MERGE_RETRIES in state.py"
Task T007: "Update AUTO_MERGE_RETRY_BASE_DELAY in state.py"
```

## Parallel Example: User Stories 1 + 2 + 3

```bash
# All three stories can be worked on in parallel by different developers:
Developer A: US1 tasks (T003-T008) — state.py only
Developer B: US2 tasks (T009-T017) — webhooks.py only
Developer C: US3 tasks (T018-T034) — pipeline.py + auto_merge.py only
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002) — verify clean starting state
2. Complete Phase 3: User Story 1 (T003-T008) — extend retry window
3. **STOP and VALIDATE**: Run `pytest tests/unit/test_auto_merge.py -v` — US1 tests pass
4. Deploy/demo if ready — developers immediately get longer retry window

### Incremental Delivery

1. Complete Setup → Verify clean state
2. Add User Story 1 → Test independently → **MVP: Longer retry window** 🎯
3. Add User Story 2 → Test independently → **L2 + project-level fallback**
4. Add User Story 3 → Test independently → **Deferred state removal**
5. Add User Story 4 → Run full regression → **All existing behavior preserved**
6. Polish → Lint, type check, final verification

### Parallel Team Strategy

With multiple developers:

1. All verify Setup (Phase 1) together
2. Once Setup is verified:
   - Developer A: User Story 1 (state.py — T003-T008)
   - Developer B: User Story 2 (webhooks.py — T009-T017)
   - Developer C: User Story 3 (pipeline.py + auto_merge.py — T018-T034)
3. Stories complete and integrate independently
4. Developer D: User Story 4 (regression tests — T035-T038) after A+B+C finish
5. Any developer: Polish (T039-T043)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Tests explicitly requested per spec Phase 4 — write tests FIRST (TDD), verify they fail, then implement
- No new database migrations needed — all changes reuse existing schema
- No frontend changes required — backend-only fixes
- Total: 43 tasks across 7 phases
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
