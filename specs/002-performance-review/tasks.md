# Tasks: Performance Review

**Input**: Design documents from `/specs/002-performance-review/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/refresh-contract.yaml, quickstart.md

**Tests**: Explicitly requested (FR-016, FR-017, FR-018, User Story 5). Regression test tasks are included in the relevant user story phases and in the dedicated US5 phase.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. User Stories 1 and 3 (backend API + frontend refresh) can proceed in parallel once baselines are captured. User Story 2 (render optimization) depends on US3 refresh-path definitions. User Story 5 (regression coverage) depends on all optimization work.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `solune/backend/src/`, `solune/backend/tests/unit/`
- **Frontend**: `solune/frontend/src/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify existing project tooling and document baseline measurement methodology before any optimization work

- [ ] T001 Verify backend dev environment setup per quickstart.md: run `uv sync --locked --extra dev` in solune/backend/
- [ ] T002 Verify frontend dev environment setup per quickstart.md: run `npm install` in solune/frontend/
- [ ] T003 [P] Run existing backend tests to confirm green baseline: `uv run pytest tests/unit/test_cache.py tests/unit/test_api_board.py tests/unit/test_copilot_polling.py -v` in solune/backend/
- [ ] T004 [P] Run existing frontend tests to confirm green baseline: `npx vitest run src/hooks/useRealTimeSync.test.tsx src/hooks/useBoardRefresh.test.tsx` in solune/frontend/
- [ ] T005 [P] Run backend linting and type checks to confirm clean state: `ruff check src tests && ruff format --check src tests && uv run pyright src` in solune/backend/
- [ ] T006 [P] Run frontend linting, type checks, and build to confirm clean state: `npm run lint && npm run type-check && npm run build` in solune/frontend/

---

## Phase 2: Foundational — User Story 4: Baselines Prove Improvements Are Real (Priority: P1) 🎯 MVP

**Goal**: Capture backend and frontend performance baselines before changing any behavior. Document measurement procedures and record before-state metrics. This phase BLOCKS all optimization work because success criteria (SC-001 through SC-007) depend on having baselines.

**Independent Test**: Execute the baseline measurement procedure on the unmodified system and verify that it produces consistent, repeatable numbers for idle request count, board load time, interaction frame rates, and rerender frequency.

**⚠️ CRITICAL**: No optimization work (Phases 3–6) can begin until this phase is complete.

### Baseline Capture

- [ ] T007 [US4] Document backend baseline measurement procedure: idle API request count over 5 minutes, requests per minute, request types (GraphQL vs REST), and stale-revalidation cycle count in specs/002-performance-review/checklists/backend-baseline.md
- [ ] T008 [US4] Document frontend baseline measurement procedure: board load time-to-interactive, initial render component count, frame rate during drag/scroll, rerender count per interaction, and query invalidation count per WebSocket message type in specs/002-performance-review/checklists/frontend-baseline.md
- [ ] T009 [US4] Create before/after comparison template with columns for each metric (baseline, after, target) covering SC-001 through SC-005 in specs/002-performance-review/checklists/before-after-comparison.md

### Backend State Verification

- [ ] T010 [P] [US4] Verify board cache TTL (300s) is consistently applied by inspecting cache.set() calls and test coverage in solune/backend/src/api/board.py and solune/backend/tests/unit/test_api_board.py
- [ ] T011 [P] [US4] Verify WebSocket subscription change detection (hash comparison, refresh_ttl on unchanged, stale-revalidation limit) is fully wired in solune/backend/src/api/projects.py
- [ ] T012 [P] [US4] Verify sub-issue cache invalidation on manual refresh is fully implemented in solune/backend/src/api/board.py (lines ~388–399)
- [ ] T013 [P] [US4] Verify fallback polling does not trigger expensive board refreshes by inspecting solune/backend/src/services/copilot_polling/polling_loop.py and its interaction with board cache
- [ ] T014 [P] [US4] Verify repository resolution is centralized (no duplication) by confirming solune/backend/src/api/workflow.py uses resolve_repository() from solune/backend/src/utils.py

### Frontend State Verification

- [ ] T015 [P] [US4] Verify refresh-source isolation: confirm WebSocket task updates only invalidate tasks query (not board data) in solune/frontend/src/hooks/useRealTimeSync.ts
- [ ] T016 [P] [US4] Verify board auto-refresh debounce (2s) and manual refresh bypass behavior in solune/frontend/src/hooks/useBoardRefresh.ts
- [ ] T017 [P] [US4] Verify adaptive polling tier configuration and change-detection hash in solune/frontend/src/hooks/useProjectBoard.ts
- [ ] T018 [P] [US4] Verify existing component memoization state for BoardColumn and IssueCard in solune/frontend/src/components/board/BoardColumn.tsx and solune/frontend/src/components/board/IssueCard.tsx

### Regression Checklist

- [ ] T019 [US4] Compile regression checklist mapping existing tests to optimization targets: cache TTL tests → SC-001, refresh dedup tests → SC-003/SC-004, polling safety tests → SC-001 in specs/002-performance-review/checklists/regression-checklist.md

**Checkpoint**: Baselines documented, current implementation state confirmed, regression checklist established. Optimization phases can now begin.

---

## Phase 3: User Story 1 — Idle Board Stops Wasting Background Requests (Priority: P1) 🎯 MVP

**Goal**: Reduce idle board API consumption by ≥50% over a 5-minute window (SC-001). Target stale-revalidation behavior in WebSocket subscriptions, sub-issue cache reuse on warm reads, and polling safety.

**Independent Test**: Open a board, leave it idle for 5 minutes, count outgoing GitHub API requests. Compare against Phase 2 baseline. Success: ≤50% of baseline request count.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T020 [P] [US1] Add test for stale-revalidation behavior: verify that an idle board with no data changes produces forced API calls no more frequently than once every 10 minutes (20 refresh intervals at 30s each) in solune/backend/tests/unit/test_api_board.py
- [ ] T021 [P] [US1] Add test for sub-issue cache warm-read path: verify that warm sub-issue caches skip API calls during board refresh in solune/backend/tests/unit/test_api_board.py
- [ ] T022 [P] [US1] Add test for polling loop safety: verify that fallback polling does not trigger full board refresh when data is unchanged in solune/backend/tests/unit/test_copilot_polling.py

### Implementation for User Story 1

- [ ] T023 [US1] Tune stale-revalidation behavior in WebSocket subscription refresh loop to reduce idle API consumption: review STALE_REVALIDATION_LIMIT and consider increasing or conditioning the forced fresh fetch in solune/backend/src/api/projects.py
- [ ] T024 [US1] Verify and strengthen sub-issue cache reuse during board data fetches: ensure warm sub-issue caches (600s TTL) materially reduce outgoing requests on board refresh in solune/backend/src/services/github_projects/service.py
- [ ] T025 [US1] Verify that polling_loop does not inadvertently trigger expensive board refreshes or redundant GitHub API calls during fallback operation in solune/backend/src/services/copilot_polling/polling_loop.py
- [ ] T026 [US1] Validate change detection suppresses redundant refresh events: confirm that unchanged data_hash on periodic refresh in the subscription loop results in refresh_ttl() only (no client notification) in solune/backend/src/api/projects.py
- [ ] T027 [US1] Run targeted backend tests to verify US1 changes: `uv run pytest tests/unit/test_api_board.py tests/unit/test_cache.py tests/unit/test_copilot_polling.py -v` in solune/backend/

**Checkpoint**: Idle board API consumption verified at ≤50% of baseline. Backend change-detection and cache-reuse paths confirmed.

---

## Phase 4: User Story 3 — Refresh Paths Are Coherent and Predictable (Priority: P2)

**Goal**: Ensure each refresh source (WebSocket, auto-refresh, fallback polling, manual) has a clear role. Lightweight task updates stay decoupled from expensive board data queries. No redundant full-board reloads from single-task updates (SC-003). Fallback polling never triggers board reload when data is unchanged (SC-004).

**Independent Test**: Simulate each refresh path independently and verify which data queries each triggers via network inspection. Confirm no unexpected full board reloads.

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T028 [P] [US3] Add test for refresh-source isolation: verify WebSocket task_update messages invalidate only tasks query and NOT board data query in solune/frontend/src/hooks/useRealTimeSync.test.tsx
- [ ] T029 [P] [US3] Add test for fallback polling isolation: verify fallback polling invalidates only tasks query and NOT board data query in solune/frontend/src/hooks/useRealTimeSync.test.tsx
- [ ] T030 [P] [US3] Add test for manual refresh cache bypass: verify manual refresh calls getBoardData with refresh=true and resets auto-refresh timer in solune/frontend/src/hooks/useBoardRefresh.test.tsx
- [ ] T031 [P] [US3] Add test for refresh deduplication: verify that overlapping refresh sources within a 2s window are coalesced into a single board reload in solune/frontend/src/hooks/useBoardRefresh.test.tsx

### Implementation for User Story 3

- [ ] T032 [US3] Verify and enforce refresh-source isolation: confirm WebSocket task_update and status_changed messages only invalidate `['projects', projectId, 'tasks']` and do NOT invalidate `['board', 'data', projectId]` in solune/frontend/src/hooks/useRealTimeSync.ts
- [ ] T033 [US3] Verify and enforce fallback polling isolation: confirm fallback polling only invalidates the tasks query and does not trigger board data reload when data is unchanged in solune/frontend/src/hooks/useRealTimeSync.ts
- [ ] T034 [US3] Verify manual refresh bypasses all caches: confirm manual refresh calls backend with `refresh=true`, cancels pending auto-refresh, and resets the timer in solune/frontend/src/hooks/useBoardRefresh.ts
- [ ] T035 [US3] Review interaction between WebSocket reconnection, auto-refresh timer, and fallback polling to ensure single coherent refresh policy per the refresh contract in solune/frontend/src/hooks/useRealTimeSync.ts and solune/frontend/src/hooks/useBoardRefresh.ts
- [ ] T036 [US3] Verify adaptive polling does not produce extra board data requests on tab switch or component remount beyond the configured stale time in solune/frontend/src/hooks/useProjectBoard.ts
- [ ] T037 [US3] Run targeted frontend tests to verify US3 changes: `npx vitest run src/hooks/useRealTimeSync.test.tsx src/hooks/useBoardRefresh.test.tsx` in solune/frontend/

**Checkpoint**: All four refresh sources have clear roles, no redundant board reloads from task updates, fallback polling is safe, manual refresh bypasses caches.

---

## Phase 5: User Story 2 — Board Interactions Feel Responsive (Priority: P2)

**Goal**: Improve board load time by ≥20% (SC-002), ensure smooth 60fps drag-and-drop (SC-005), and eliminate unnecessary re-renders from unchanged data. Low-risk optimizations only: memoization, prop stabilization, event listener throttling. No new dependencies or virtualization.

**Independent Test**: Profile board load and interaction on a representative board (5+ columns, 50+ tasks). Measure time-to-interactive and frame rates during drag/scroll/popover interactions. Compare against Phase 2 baseline.

### Implementation for User Story 2

- [ ] T038 [P] [US2] Stabilize board data transformation output references: ensure column and item objects maintain referential equality when underlying data has not changed to maximize React.memo effectiveness in solune/frontend/src/hooks/useProjectBoard.ts
- [ ] T039 [P] [US2] Verify and strengthen BoardColumn memo boundary: ensure column.items array reference is stable across renders when column data is unchanged in solune/frontend/src/components/board/BoardColumn.tsx
- [ ] T040 [P] [US2] Verify and strengthen IssueCard memo boundary: ensure item prop references are stable and memo comparison is effective in solune/frontend/src/components/board/IssueCard.tsx
- [ ] T041 [P] [US2] Verify useMemo dependency arrays in ProjectsPage: confirm heroStats, rateLimitState, and syncStatusLabel memoizations have correct and minimal dependency arrays in solune/frontend/src/pages/ProjectsPage.tsx
- [ ] T042 [P] [US2] Verify ChatPopup event listener optimization: confirm RAF-gated resize handlers and lifecycle-scoped listeners are correctly implemented in solune/frontend/src/components/chat/ChatPopup.tsx
- [ ] T043 [P] [US2] Verify AddAgentPopover positioning: confirm Radix Popover handles positioning without custom high-frequency listeners in solune/frontend/src/components/board/AddAgentPopover.tsx
- [ ] T044 [US2] Run frontend build and type checks to verify US2 changes: `npx tsc --noEmit && npm run build` in solune/frontend/

**Checkpoint**: Board load time measurably faster, drag-and-drop smooth, no unnecessary full-board re-renders from unchanged data.

---

## Phase 6: User Story 5 — Regression Coverage Prevents Backsliding (Priority: P3)

**Goal**: Extend automated test coverage to guard against performance regressions. New tests cover backend cache behavior, change-detection logic, fallback polling safety, and frontend refresh coordination. All existing tests continue to pass (SC-006).

**Independent Test**: Run the full backend and frontend test suites. Intentionally break a guarded behavior (e.g., remove change detection) and confirm the relevant test fails.

### Backend Regression Tests

- [ ] T045 [P] [US5] Extend cache TTL and stale-data fallback test coverage: add tests for get_stale() returning expired data during API failures and hash-stability across rate-limit changes in solune/backend/tests/unit/test_cache.py
- [ ] T046 [P] [US5] Extend board endpoint test coverage: add tests for sub-issue cache hit path (warm cache skips API call), hash-based change detection on board data, and cache population on manual refresh in solune/backend/tests/unit/test_api_board.py
- [ ] T047 [P] [US5] Extend polling behavior test coverage: add tests for rate-limit-aware step skipping, polling loop not triggering board cache invalidation, and sub-issue filtering correctness in solune/backend/tests/unit/test_copilot_polling.py

### Frontend Regression Tests

- [ ] T048 [P] [US5] Extend real-time sync test coverage: add tests for WebSocket reconnection not triggering board data invalidation, message type routing (task_update vs refresh vs status_changed), and fallback activation/deactivation lifecycle in solune/frontend/src/hooks/useRealTimeSync.test.tsx
- [ ] T049 [P] [US5] Extend board refresh test coverage: add tests for auto-refresh timer reset on manual refresh, deduplication of overlapping refresh sources, and visibility API pause/resume behavior in solune/frontend/src/hooks/useBoardRefresh.test.tsx

### Verification

- [ ] T050 [US5] Run full backend test suite to confirm no regressions: `uv run pytest tests/unit/ -v` in solune/backend/
- [ ] T051 [US5] Run full frontend test suite to confirm no regressions: `npx vitest run` in solune/frontend/
- [ ] T052 [US5] Run backend lint and type checks: `ruff check src tests && ruff format --check src tests && uv run pyright src` in solune/backend/
- [ ] T053 [US5] Run frontend lint, type checks, and build: `npx eslint src/ && npx tsc --noEmit && npm run build` in solune/frontend/

**Checkpoint**: All new regression tests pass. Intentionally breaking a guarded behavior causes at least one test to fail. All existing tests continue to pass. Full CI pipeline green.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final documentation, before/after comparison, and verification across all user stories

- [ ] T054 [P] Record post-optimization backend baseline measurements (repeat T007 procedure) and fill in the "After" column in specs/002-performance-review/checklists/before-after-comparison.md
- [ ] T055 [P] Record post-optimization frontend baseline measurements (repeat T008 procedure) and fill in the "After" column in specs/002-performance-review/checklists/before-after-comparison.md
- [ ] T056 Validate before/after comparison against success criteria (SC-001 through SC-007): confirm ≥50% idle API reduction, ≥20% board load improvement, zero unnecessary full-board reloads, and all tests green in specs/002-performance-review/checklists/before-after-comparison.md
- [ ] T057 Perform manual end-to-end verification: confirm WebSocket updates refresh task data promptly, fallback polling remains safe, manual refresh bypasses caches, and board interactions are responsive
- [ ] T058 Run quickstart.md validation: execute all commands from specs/002-performance-review/quickstart.md to confirm documentation accuracy
- [ ] T059 Document any identified candidates for Phase 4 second-wave work (virtualization, service decomposition) if first-pass measurements indicate need, in specs/002-performance-review/checklists/second-wave-candidates.md

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1: Setup ─────────────────────────────────────┐
                                                     ▼
Phase 2: Foundational / US4 Baselines ──────────────┐ (BLOCKS all optimization)
                                                     ▼
Phase 3: US1 Backend API Fixes ─────────────┐       │
                                             │       │
Phase 4: US3 Frontend Refresh Fixes ────────┤  (parallel with Phase 3)
                                             │       │
                                             ▼       ▼
Phase 5: US2 Frontend Render Optimization ──┐ (depends on US3 refresh definitions)
                                             │
                                             ▼
Phase 6: US5 Regression Coverage ───────────┐ (depends on all optimization phases)
                                             │
                                             ▼
Phase 7: Polish & Verification ─────────────  (depends on everything)
```

### User Story Dependencies

- **US4 — Baselines (P1)**: No dependencies — starts immediately after setup. **BLOCKS all other user stories.**
- **US1 — Idle Board API Reduction (P1)**: Depends on US4 baselines. No dependency on other user stories. Backend-only.
- **US3 — Refresh Paths (P2)**: Depends on US4 baselines. Can proceed in parallel with US1. Frontend-only.
- **US2 — Board Responsiveness (P2)**: Depends on US4 baselines. Benefits from US3 refresh-path definitions being at least defined. Frontend-only.
- **US5 — Regression Coverage (P3)**: Depends on US1, US2, and US3 optimization work being complete.

### Within Each User Story

- Tests (where included) MUST be written and FAIL before implementation
- Verification tasks follow implementation tasks
- Run targeted test suites after each story to confirm behavior

### Parallel Opportunities

- **Phase 1**: T003, T004, T005, T006 can all run in parallel (independent environments)
- **Phase 2**: T010–T018 can all run in parallel (read-only verification of different files)
- **Phase 3 + Phase 4**: US1 (backend) and US3 (frontend) can proceed in parallel once US4 is complete
- **Phase 5**: T038–T043 can all run in parallel (different component files)
- **Phase 6**: T045–T049 can all run in parallel (different test files)
- **Phase 7**: T054 and T055 can run in parallel (backend vs frontend measurement)

---

## Parallel Example: Phase 2 (Foundational Verification)

```bash
# All backend verification tasks can run in parallel:
Task T010: "Verify board cache TTL in solune/backend/src/api/board.py"
Task T011: "Verify WebSocket change detection in solune/backend/src/api/projects.py"
Task T012: "Verify sub-issue cache invalidation in solune/backend/src/api/board.py"
Task T013: "Verify polling safety in solune/backend/src/services/copilot_polling/polling_loop.py"
Task T014: "Verify repository resolution in solune/backend/src/api/workflow.py and solune/backend/src/utils.py"

# All frontend verification tasks can also run in parallel with backend:
Task T015: "Verify refresh-source isolation in solune/frontend/src/hooks/useRealTimeSync.ts"
Task T016: "Verify board auto-refresh debounce in solune/frontend/src/hooks/useBoardRefresh.ts"
Task T017: "Verify adaptive polling in solune/frontend/src/hooks/useProjectBoard.ts"
Task T018: "Verify component memoization in solune/frontend/src/components/board/"
```

## Parallel Example: Phase 3 + Phase 4 (Backend + Frontend in Parallel)

```bash
# Backend US1 and Frontend US3 can proceed simultaneously:
# Developer/Agent A (Backend):
Task T023: "Tune stale-revalidation in solune/backend/src/api/projects.py"
Task T024: "Verify sub-issue cache reuse in solune/backend/src/services/github_projects/service.py"
Task T025: "Verify polling safety in solune/backend/src/services/copilot_polling/polling_loop.py"

# Developer/Agent B (Frontend):
Task T032: "Verify refresh-source isolation in solune/frontend/src/hooks/useRealTimeSync.ts"
Task T033: "Verify fallback polling isolation in solune/frontend/src/hooks/useRealTimeSync.ts"
Task T034: "Verify manual refresh bypass in solune/frontend/src/hooks/useBoardRefresh.ts"
```

---

## Implementation Strategy

### MVP First (User Story 4 + User Story 1)

1. Complete Phase 1: Setup (verify environments)
2. Complete Phase 2: US4 Baselines (capture metrics, verify current state)
3. Complete Phase 3: US1 Backend API Fixes (idle request reduction)
4. **STOP and VALIDATE**: Measure idle API consumption against baseline → SC-001
5. Deploy/demo if the ≥50% idle API reduction target is met

### Incremental Delivery

1. Setup + US4 Baselines → Measurement infrastructure ready
2. Add US1 Backend API Fixes → Test independently → Verify SC-001 (≥50% idle reduction)
3. Add US3 Refresh Path Fixes → Test independently → Verify SC-003 (zero unnecessary reloads), SC-004 (safe fallback)
4. Add US2 Render Optimization → Test independently → Verify SC-002 (≥20% faster load), SC-005 (smooth drag)
5. Add US5 Regression Coverage → Test independently → Verify SC-006 (all tests pass)
6. Polish → Verify SC-007 (documented before/after comparison)
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With two developers/agents:

1. Both complete Setup + US4 Baselines together
2. Once baselines are captured:
   - **Agent A (Backend)**: US1 — Idle Board API Reduction
   - **Agent B (Frontend)**: US3 — Refresh Path Fixes → then US2 — Render Optimization
3. Both complete US5 Regression Coverage together
4. Both complete Polish together

---

## Summary

| Metric | Value |
|--------|-------|
| **Total tasks** | 59 |
| **Phase 1 — Setup** | 6 tasks |
| **Phase 2 — US4 Baselines (P1)** | 13 tasks |
| **Phase 3 — US1 Backend API (P1)** | 8 tasks (3 test + 5 impl) |
| **Phase 4 — US3 Refresh Paths (P2)** | 10 tasks (4 test + 6 impl) |
| **Phase 5 — US2 Render Optimization (P2)** | 7 tasks |
| **Phase 6 — US5 Regression Coverage (P3)** | 9 tasks (5 test + 4 verify) |
| **Phase 7 — Polish** | 6 tasks |
| **Parallel opportunities** | 38 tasks marked [P] across all phases |
| **MVP scope** | Phase 1 + Phase 2 + Phase 3 (US4 + US1 = 27 tasks) |
| **Independent test criteria per story** | Each story has a standalone verification method |

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Tests are included because FR-016, FR-017, FR-018, and User Story 5 explicitly request regression coverage
- Research confirmed: no duplicate repository resolution, frontend refresh paths already mostly separated, backend cache infrastructure fully implemented
- Research identified: stale-revalidation tuning as highest-value backend target; stable data references as highest-value frontend target
- Constraint: no new dependencies, no cache TTL changes, no polling interval changes (per spec scope boundaries)
- Phase 4 (Optional second-wave work from parent issue) is explicitly out of scope unless Phase 7 measurements prove it necessary
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
