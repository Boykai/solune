# Tasks: Test Isolation & State-Leak Remediation

**Input**: Design documents from `/specs/019-test-isolation-remediation/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are NOT explicitly requested as new additions — this feature IS test infrastructure. Verification tasks use existing tests with randomized ordering.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/` and `solune/frontend/` at repository root
- Backend tests: `solune/backend/tests/`
- Frontend tests: `solune/frontend/src/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new project initialization needed — this feature modifies existing test infrastructure. Verify current state before making changes.

- [ ] T001 Verify current `_clear_test_caches` fixture in `solune/backend/tests/conftest.py` clears only 3 globals and identify the exact lines to expand
- [ ] T002 [P] Audit all module-level mutable globals against the inventory in `data-model.md` to confirm completeness before modifying the fixture

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational blocking prerequisites — all user stories modify independent files/areas. US1 (backend fixture expansion) is the critical path; US2–US4 can proceed after US1.

**⚠️ CRITICAL**: US1 must complete before US2 verification (pytest-randomly requires the expanded fixture to pass with random ordering).

---

## Phase 3: User Story 1 — Backend Tests Pass in Any Order (Priority: P1) 🎯 MVP

**Goal**: Every backend unit test produces the same result regardless of execution order by expanding the central autouse fixture to clear ALL 20+ module-level mutable globals.

**Independent Test**: Run `uv run pytest tests/unit/ --randomly-seed=12345 -x -q` — all tests pass.

### Implementation for User Story 1

#### Step 1.1 — Expand fixture to clear ALL collections (`.clear()`)

- [ ] T003 [US1] Add clearing of `_messages`, `_proposals`, `_recommendations`, `_locks` from `src.api.chat` in `solune/backend/tests/conftest.py`
- [ ] T004 [US1] Add clearing of `_pipeline_states`, `_issue_main_branches`, `_issue_sub_issue_map`, `_agent_trigger_inflight` from `src.services.pipeline_state_store` in `solune/backend/tests/conftest.py`
- [ ] T005 [US1] Add clearing of `_project_launch_locks` from `src.services.pipeline_state_store` in `solune/backend/tests/conftest.py` — ⚠️ BUG FIX: never cleared anywhere
- [ ] T006 [US1] Add clearing of `_transitions`, `_workflow_configs` from `src.services.workflow_orchestrator` in `solune/backend/tests/conftest.py`
- [ ] T007 [US1] Add clearing of `_agent_trigger_inflight` from `src.services.workflow_orchestrator.transitions` in `solune/backend/tests/conftest.py`
- [ ] T008 [US1] Add clearing of `_tracking_table_cache` from `src.services.workflow_orchestrator.orchestrator` in `solune/backend/tests/conftest.py`
- [ ] T009 [US1] Add clearing of all 15 copilot_polling/state collections (`_monitored_projects`, `_processed_issue_prs`, `_review_requested_cache`, `_posted_agent_outputs`, `_claimed_child_prs`, `_pending_agent_assignments`, `_system_marked_ready_prs`, `_copilot_review_first_detected`, `_copilot_review_requested_at`, `_recovery_last_attempt`, `_merge_failure_counts`, `_pending_auto_merge_retries`, `_pending_post_devops_retries`, `_background_tasks`, `_app_polling_tasks`) in `solune/backend/tests/conftest.py`
- [ ] T010 [US1] Add clearing of `_queue_mode_cache`, `_auto_merge_cache` from `src.services.settings_store` in `solune/backend/tests/conftest.py`
- [ ] T011 [US1] Add clearing of `_signal_pending` from `src.services.signal_chat` in `solune/backend/tests/conftest.py`
- [ ] T012 [US1] Add clearing of `_oauth_states` from `src.services.github_auth` in `solune/backend/tests/conftest.py`
- [ ] T013 [US1] Add clearing of `_agent_sessions` from `src.services.agent_creator` in `solune/backend/tests/conftest.py`

#### Step 1.2 — Reset event-loop-bound locks

- [ ] T014 [US1] Reset `_store_lock` to `None` on `src.services.pipeline_state_store` in `solune/backend/tests/conftest.py`
- [ ] T015 [US1] Reset `_ws_lock` to `None` on `src.services.websocket` in `solune/backend/tests/conftest.py`
- [ ] T016 [US1] Reset `_polling_state_lock` and `_polling_startup_lock` to fresh `asyncio.Lock()` instances on `src.services.copilot_polling.state` in `solune/backend/tests/conftest.py`

#### Step 1.3 — Reset Optional/singleton values to `None`

- [ ] T017 [US1] Reset `_orchestrator_instance` to `None` on `src.services.workflow_orchestrator.orchestrator` in `solune/backend/tests/conftest.py`
- [ ] T018 [US1] Reset `_db` to `None` on `src.services.pipeline_state_store` in `solune/backend/tests/conftest.py`
- [ ] T019 [US1] Reset `_cached_files` and `_cached_warnings` to `None` on `src.services.template_files` in `solune/backend/tests/conftest.py`
- [ ] T020 [US1] Reset `_cache` to `None` on `src.services.app_templates.registry` in `solune/backend/tests/conftest.py`
- [ ] T021 [US1] Reset `_db` to `None` on `src.services.done_items_store` in `solune/backend/tests/conftest.py`
- [ ] T022 [US1] Reset `_encryption_service` to `None` on `src.services.session_store` in `solune/backend/tests/conftest.py`

#### Step 1.4 — Reset scalars and stateful objects to defaults

- [ ] T023 [US1] Reset `_polling_task` to `None`, `_polling_state` to `PollingState()`, `_activity_window` via `.clear()`, `_consecutive_idle_polls` to `0`, `_adaptive_tier` to `"medium"`, `_consecutive_poll_failures` to `0` on `src.services.copilot_polling.state` in `solune/backend/tests/conftest.py`

#### Step 1.5 — Structure the expanded fixture

- [ ] T024 [US1] Organize all clearing logic into a `_reset()` helper function called both before yield and after yield in the `_clear_test_caches` fixture in `solune/backend/tests/conftest.py`

#### Step 1.6 — Verify

- [ ] T025 [US1] Run `uv run pytest tests/unit/ -x -q` from `solune/backend/` — all tests pass with the expanded fixture

**Checkpoint**: Backend unit tests pass with all module-level globals being cleared between tests. The confirmed `_project_launch_locks` bug (T005) is fixed.

---

## Phase 4: User Story 2 — Random Test Ordering Catches Future Regressions (Priority: P2)

**Goal**: Test execution order is randomized by default so any new ordering dependency is surfaced immediately.

**Independent Test**: Run `uv run pytest tests/unit/ -x -q` and verify the output begins with `Using --randomly-seed=XXXX`.

### Implementation for User Story 2

- [ ] T026 [US2] Add `pytest-randomly>=3.16.0` to `[project.optional-dependencies] dev` in `solune/backend/pyproject.toml`
- [ ] T027 [US2] Run `uv sync --extra dev` from `solune/backend/` to install the new dependency
- [ ] T028 [US2] Run `uv run pytest tests/unit/ --randomly-seed=12345 -x -q` from `solune/backend/` — all tests pass
- [ ] T029 [US2] Run `uv run pytest tests/unit/ --randomly-seed=99999 -x -q` from `solune/backend/` — all tests pass
- [ ] T030 [US2] Run `uv run pytest tests/unit/ --randomly-seed=42 -x -q` from `solune/backend/` — all tests pass

**Checkpoint**: Backend tests pass with three different random seed values, demonstrating order-independence.

---

## Phase 5: User Story 3 — Frontend Tests Produce Deterministic Results (Priority: P2)

**Goal**: Each frontend test starts with clean timer, UUID counter, and mock state — assertions are deterministic regardless of execution order.

**Independent Test**: Run `npx vitest run --reporter=verbose` from `solune/frontend/` — no regressions.

### Implementation for User Story 3

#### Step 3.1 — Fix fake timer leak

- [ ] T031 [P] [US3] Add `afterEach(() => { vi.useRealTimers(); })` to `solune/frontend/src/hooks/useFileUpload.test.ts`

#### Step 3.2 — Reset UUID counter

- [ ] T032 [P] [US3] Move `_counter` to module scope (if needed) and add `beforeEach(() => { _counter = 0; })` in `solune/frontend/src/test/setup.ts`

#### Step 3.3 — Add spy restoration to test files missing cleanup

- [ ] T033 [P] [US3] Add `afterEach(() => { vi.restoreAllMocks(); })` to `solune/frontend/src/layout/TopBar.test.tsx`
- [ ] T034 [P] [US3] Add `afterEach(() => { vi.restoreAllMocks(); })` to `solune/frontend/src/layout/AuthGate.test.tsx`
- [ ] T035 [P] [US3] Change `vi.resetAllMocks()` to `vi.restoreAllMocks()` in `afterEach` in `solune/frontend/src/hooks/useAuth.test.tsx`

#### Step 3.4 — Verify

- [ ] T036 [US3] Run `npx vitest run --reporter=verbose` from `solune/frontend/` — all tests pass with no regressions

**Checkpoint**: Frontend tests produce deterministic results — UUID counter resets, fake timers are restored, spy wrappers don't leak.

---

## Phase 6: User Story 4 — Existing Integration Tests Continue Working (Priority: P3)

**Goal**: The integration conftest's `_reset_integration_state` fixture remains intact as defense-in-depth, coexisting with the expanded central fixture.

**Independent Test**: Run `uv run pytest tests/integration/ -x -q` from `solune/backend/` — all integration tests pass.

### Implementation for User Story 4

- [ ] T037 [US4] Verify `_reset_integration_state` fixture in `solune/backend/tests/integration/conftest.py` is unchanged — no modifications needed
- [ ] T038 [US4] Run `uv run pytest tests/integration/ -x -q` from `solune/backend/` — all integration tests pass with expanded central fixture layered underneath
- [ ] T039 [US4] Verify no errors occur from double-clearing (central fixture + integration fixture both clear overlapping state)

**Checkpoint**: Integration tests pass with the expanded fixture and existing defense-in-depth layer coexisting without conflict.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final verification across all user stories and coverage validation.

- [ ] T040 Run backend unit tests with `--randomly-seed=12345` from `solune/backend/` — all pass
- [ ] T041 Run backend unit tests with `--randomly-seed=99999` from `solune/backend/` — all pass
- [ ] T042 Run backend unit tests with `--randomly-seed=42` from `solune/backend/` — all pass
- [ ] T043 Run `npx vitest run --reporter=verbose` from `solune/frontend/` — no regressions
- [ ] T044 Verify backend coverage ≥75% with `uv run pytest tests/ --cov --cov-fail-under=75` from `solune/backend/`
- [ ] T045 Verify frontend coverage ≥50% with `npx vitest run --coverage` from `solune/frontend/`
- [ ] T046 Run `uv run pytest tests/integration/ -x -q` from `solune/backend/` — integration tests pass
- [ ] T047 Run `uv run pytest tests/concurrency/ -x -q` from `solune/backend/` — concurrency tests pass (if applicable)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — audit and verification only
- **Foundational (Phase 2)**: No blocking prerequisites for this feature
- **User Story 1 (Phase 3)**: Can start immediately — CRITICAL path, MVP
- **User Story 2 (Phase 4)**: Depends on US1 completion (expanded fixture must be in place for random ordering to pass)
- **User Story 3 (Phase 5)**: Independent of backend stories — can run in parallel with US1/US2
- **User Story 4 (Phase 6)**: Depends on US1 completion (need expanded fixture to verify integration coexistence)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start immediately — no dependencies on other stories. **This is the MVP.**
- **User Story 2 (P2)**: Depends on US1 — pytest-randomly requires the expanded fixture to pass with random ordering
- **User Story 3 (P2)**: Independent — frontend changes do not depend on backend changes. Can run in parallel with US1.
- **User Story 4 (P3)**: Depends on US1 — need the expanded fixture to verify integration coexistence

### Within User Story 1

- T003–T013 (collection clearing) can be done as a single batch edit to `conftest.py`
- T014–T016 (lock resets) can be done in the same edit
- T017–T022 (singleton resets) can be done in the same edit
- T023 (scalar resets) can be done in the same edit
- T024 (structural organization) wraps all of the above into a `_reset()` helper
- T025 (verification) must run last

### Parallel Opportunities

- **US1 and US3 can run in parallel** — backend fixture changes (conftest.py) and frontend cleanup changes (test files) touch completely different codebases
- Within US3: T031, T032, T033, T034, T035 are all marked [P] — they edit different files and can run simultaneously
- T040–T047 (verification) should run sequentially to isolate any failures

---

## Parallel Example: User Story 3 (Frontend)

```bash
# Launch all frontend fixes together (different files, no dependencies):
Task T031: "Add afterEach vi.useRealTimers() to useFileUpload.test.ts"
Task T032: "Reset UUID counter in setup.ts"
Task T033: "Add afterEach vi.restoreAllMocks() to TopBar.test.tsx"
Task T034: "Add afterEach vi.restoreAllMocks() to AuthGate.test.tsx"
Task T035: "Change vi.resetAllMocks() to vi.restoreAllMocks() in useAuth.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Audit current fixture state
2. Complete Phase 3: Expand `_clear_test_caches` to clear ALL globals (US1)
3. **STOP and VALIDATE**: Run `uv run pytest tests/unit/ -x -q` — all pass
4. This alone fixes the critical state-leak problem

### Incremental Delivery

1. US1 → Backend fixture expansion → Validate → **MVP delivered** (critical fix)
2. US2 → Add pytest-randomly → Validate with 3 seeds → **Regression safety net active**
3. US3 → Frontend cleanup → Validate with vitest → **Frontend deterministic**
4. US4 → Integration verification → Validate → **Defense-in-depth confirmed**
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. **Developer A**: US1 (backend fixture) → US2 (pytest-randomly) → US4 (integration verification)
2. **Developer B**: US3 (frontend cleanup) — completely independent of backend work
3. Final: Both developers verify Phase 7 together

---

## Summary

| Metric | Value |
|--------|-------|
| **Total tasks** | 47 |
| **US1 tasks** (P1 — Backend fixture) | 23 (T003–T025) |
| **US2 tasks** (P2 — pytest-randomly) | 5 (T026–T030) |
| **US3 tasks** (P2 — Frontend cleanup) | 6 (T031–T036) |
| **US4 tasks** (P3 — Integration verification) | 3 (T037–T039) |
| **Setup tasks** | 2 (T001–T002) |
| **Verification tasks** | 8 (T040–T047) |
| **Parallel opportunities** | US1 ∥ US3; T031–T035 all [P]; T003–T013 batchable |
| **MVP scope** | US1 only (Phase 3) |
| **Files modified** | 7 (conftest.py, pyproject.toml, 5 frontend test files) |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US1 tasks (T003–T024) should be implemented as a single atomic edit to `conftest.py` — they are split into individual tasks for traceability and review, not for separate implementation
- The `_project_launch_locks` bug fix (T005) is a confirmed bug from issue #1077 — it is the highest-value individual fix
- Lock resets (T014–T016) MUST use `= None`, NEVER `= asyncio.Lock()` — see research.md R1
- `useAdaptivePolling.test.ts` already has correct cleanup — no changes needed (verified in contracts/frontend-cleanup.md)
- Scope excludes: pytest-xdist parallelization, refactoring globals into DI (architectural), adding new tests
