# Tasks: Performance Review

**Input**: Design documents from `/specs/001-performance-review/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/refresh-policy.md

**Tests**: Included — explicitly requested in spec.md (FR-012, User Story 5). Tests extend existing test classes using established mock patterns.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/src/`, `solune/frontend/src/` (monorepo under `solune/`)
- **Backend tests**: `solune/backend/tests/unit/`
- **Frontend tests**: Co-located with source in `solune/frontend/src/hooks/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify existing environment, confirm all existing tests pass, and establish known-good starting state before any optimization work.

- [ ] T001 Run existing backend test suite to confirm passing state: `uv run pytest tests/unit/test_cache.py tests/unit/test_api_board.py tests/unit/test_copilot_polling.py -v` in solune/backend/
- [ ] T002 [P] Run existing frontend test suite to confirm passing state: `npx vitest run src/hooks/useRealTimeSync.test.tsx src/hooks/useBoardRefresh.test.tsx` in solune/frontend/
- [ ] T003 [P] Audit and document current implementation state of hash-based change detection (`compute_data_hash`), board cache TTL (300s), coalesced fetch (`_inflight_fetches`), and sub-issue cache invalidation per research.md RT-001 in solune/backend/src/services/cache.py and solune/backend/src/api/board.py

---

## Phase 2: Foundational — Baseline Measurement and Guardrails (US1, Priority: P1)

**Purpose**: Capture performance baselines that block ALL optimization work. Maps to User Story 1. No optimization code may be written until baselines are recorded.

**⚠️ CRITICAL**: No user story optimization work (Phases 3–7) can begin until this phase is complete.

**Goal**: Record current backend and frontend performance metrics as the "before" snapshot for every success criterion (SC-001 through SC-010).

**Independent Test**: Run all baseline measurement tests and confirm they capture meaningful metric values. Results form the "before" half of the before/after comparison.

### Baseline Tests

> **NOTE: These tests MEASURE current behavior — they establish the "before" numbers. They should PASS with current code (asserting measurement capture, not improvement thresholds).**

- [ ] T004 [US1] Add backend baseline tests measuring idle GitHub API call count over a simulated 10-minute idle window and board endpoint request cost (GitHub API calls triggered per single board fetch) in solune/backend/tests/unit/test_api_board.py
- [ ] T005 [P] [US1] Add backend baseline tests measuring polling cycle API consumption and rate-limit-aware step-skipping behavior during idle board viewing in solune/backend/tests/unit/test_copilot_polling.py
- [ ] T006 [P] [US1] Add backend baseline tests measuring cache hit rate, sub-issue fetch count during board refresh, and stale fallback behavior in solune/backend/tests/unit/test_cache.py
- [ ] T007 [P] [US1] Add frontend baseline tests measuring WebSocket message handling counts, polling-fallback query invalidation frequency, and board data fetch triggers in solune/frontend/src/hooks/useRealTimeSync.test.tsx
- [ ] T008 [P] [US1] Add frontend baseline tests measuring board reload debounce effectiveness, auto-refresh timer suppression during WebSocket connection, and concurrent trigger deduplication in solune/frontend/src/hooks/useBoardRefresh.test.tsx
- [ ] T009 [US1] Run all baseline tests (`uv run pytest` for backend, `npx vitest run` for frontend) and record "before" metric values as comments in each test file for later comparison

**Checkpoint**: Baselines captured — optimization work can now begin. All subsequent phases depend on this phase.

---

## Phase 3: User Story 2 — Reduced Backend API Consumption During Idle Board Viewing (Priority: P1) 🎯 MVP

**Goal**: Reduce idle board API consumption by ≥50% (SC-001) and board refresh API calls by ≥30% with warm sub-issue caches (SC-002). Ensure zero redundant GitHub API calls when board data is unchanged.

**Independent Test**: Open a board, leave idle for 10 minutes, measure GitHub API calls. Compare against Phase 2 baseline. Verify warm sub-issue caches reduce fetch count during auto-refresh.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation. These assert on OPTIMIZED behavior.**

- [ ] T010 [US2] Add tests verifying: (a) idle board with unchanged data produces zero redundant GitHub API refresh calls over simulated interval, and (b) warm sub-issue cache is reused (not cleared) during auto-refresh in solune/backend/tests/unit/test_api_board.py
- [ ] T011 [P] [US2] Add test verifying polling fallback does not trigger expensive full board refresh when board data hash is unchanged in solune/backend/tests/unit/test_copilot_polling.py

### Implementation for User Story 2

- [ ] T012 [P] [US2] Validate and fix sub-issue cache reuse during non-manual board refreshes — ensure `refresh=false` path preserves sub-issue cache entries and only `refresh=true` clears them per contract Rule 5 in solune/backend/src/api/board.py
- [ ] T013 [P] [US2] Validate and fix WebSocket subscription refresh logic — ensure `broadcast_to_project` does not trigger redundant board data refetches when data hash is unchanged per research RT-002 in solune/backend/src/api/projects.py
- [ ] T014 [P] [US2] Validate and fix polling loop to leverage hash-based change detection — ensure idle polling cycles with unchanged data skip board-level refresh signals per research RT-003 in solune/backend/src/services/copilot_polling/polling_loop.py

**Checkpoint**: Backend idle API consumption reduced. Verify by re-running T010–T011 tests and comparing against Phase 2 baselines.

---

## Phase 4: User Story 3 — Coherent Frontend Refresh Policy (Priority: P2)

**Goal**: Unify WebSocket, polling fallback, auto-refresh, and manual refresh under a single coherent policy per contracts/refresh-policy.md. Ensure lightweight task updates arrive in <2s (SC-003) without triggering full board refetches. Enforce max one board fetch per 2s debounce window (SC-004).

**Independent Test**: Simulate WebSocket updates, polling fallback transitions, auto-refresh timer events, and manual refresh actions. Monitor query invalidations and board data fetch count. Verify contract Rules 1–8.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation.**

- [ ] T015 [US3] Add tests verifying: (a) polling fallback calls `onRefreshTriggered` callback (not direct query invalidation) per contract Rule 3, and (b) WebSocket task update messages do not invalidate the board data query per contract Rule 1 in solune/frontend/src/hooks/useRealTimeSync.test.tsx
- [ ] T016 [P] [US3] Add tests verifying: (a) concurrent refresh triggers within 2s window result in single board fetch per contract Rule 6, and (b) auto-refresh timer is suppressed when WebSocket is connected per contract Rule 4 in solune/frontend/src/hooks/useBoardRefresh.test.tsx

### Implementation for User Story 3

- [ ] T017 [US3] Ensure polling fallback path in `useRealTimeSync` routes through `onRefreshTriggered` callback for debouncing instead of directly invalidating board data queries per contract Rule 3 in solune/frontend/src/hooks/useRealTimeSync.ts
- [ ] T018 [P] [US3] Validate debounce and deduplication logic in `requestBoardReload` — confirm `lastBoardReloadRef` + `BOARD_RELOAD_DEBOUNCE_MS` (2000ms) gate prevents duplicate fetches per contract Rule 6, and manual refresh always bypasses debounce per contract Rule 5 in solune/frontend/src/hooks/useBoardRefresh.ts
- [ ] T019 [P] [US3] Validate adaptive polling change detection (hash comparison of column item counts) and auto-refresh suppression during active WebSocket connection per contract Rule 4 in solune/frontend/src/hooks/useProjectBoard.ts

**Checkpoint**: Frontend refresh policy unified. Verify by re-running T015–T016 tests and confirming single coherent refresh behavior across all trigger sources.

---

## Phase 5: User Story 4 — Improved Board Rendering Performance (Priority: P2)

**Goal**: Achieve ≥30 FPS on boards with 50+ items (SC-005). Ensure derived-data computations do not re-execute on unchanged source data (SC-006). Reduce unnecessary child rerenders from unstable callback props.

**Independent Test**: Profile board interactions (scroll, drag-and-drop, popover open/close) on a board with 50+ items. Measure frame rates, rerender counts, and interaction response times. Compare against Phase 2 baselines.

### Implementation for User Story 4

- [ ] T020 [US4] Stabilize callback props with `useCallback` for event handlers (`onCardClick`, `onColumnAction`, `onBoardDrop`) passed to memoized board children in solune/frontend/src/pages/ProjectsPage.tsx
- [ ] T021 [US4] Memoize derived-data computations (`heroStats`, `rateLimitState`, `syncStatusLabel`, sorting/filtering aggregations) with `useMemo` to prevent re-execution when source data references are unchanged in solune/frontend/src/pages/ProjectsPage.tsx
- [ ] T022 [P] [US4] Verify `React.memo` effectiveness on `BoardColumn` — ensure parent does not pass unstable props that defeat memoization; stabilize any remaining inline callbacks or object literals in solune/frontend/src/components/board/BoardColumn.tsx
- [ ] T023 [P] [US4] Verify `React.memo` effectiveness on `IssueCard` — ensure parent does not pass unstable `onClick` or other props that defeat memoization; stabilize any remaining inline callbacks in solune/frontend/src/components/board/IssueCard.tsx
- [ ] T024 [P] [US4] Wrap `AddAgentPopover` in `React.memo` and stabilize internal `useMemo` computations (`filteredAgents`, `assignedSlugs`) to prevent rerenders from parent state changes in solune/frontend/src/components/board/AddAgentPopover.tsx
- [ ] T025 [P] [US4] Verify RAF-gating on `ChatPopup` resize drag handler and throttle any remaining high-frequency positioning listeners per research RT-005 in solune/frontend/src/components/chat/ChatPopup.tsx

**Checkpoint**: Board rendering performance improved. Verify by profiling board interactions on a 50+ item board and confirming ≥30 FPS and stable derived-data computation counts.

---

## Phase 6: User Story 5 — Verification and Regression Coverage (Priority: P3)

**Goal**: Extend test coverage to validate ALL optimized code paths (FR-012, SC-008). Ensure zero test regressions (SC-007). Provide durable regression guards so future changes do not silently reintroduce performance issues.

**Independent Test**: Run the full extended test suite and confirm all new and existing tests pass. Compare "after" metrics against Phase 2 "before" baselines.

### Tests for User Story 5

- [ ] T026 [US5] Extend cache tests with: TTL enforcement edge cases, stale fallback under rate-limit exhaustion, hash-based change detection (SHA-256 excluding `rate_limit` field), and coalesced fetch deduplication via `_inflight_fetches` in solune/backend/tests/unit/test_cache.py
- [ ] T027 [P] [US5] Extend board tests with: sub-issue cache preservation during auto-refresh, stale fallback when rate limit is exhausted mid-refresh, and manual refresh cache bypass with sub-issue clearing in solune/backend/tests/unit/test_api_board.py
- [ ] T028 [P] [US5] Extend polling tests with: idle board zero-redundant-call assertion over simulated interval, rate-limit-aware expensive step skipping, and stale rate-limit guard clearing in solune/backend/tests/unit/test_copilot_polling.py
- [ ] T029 [P] [US5] Extend real-time sync tests with: polling fallback routes through callback path, WebSocket reconnection deduplication (debounced `initial_data`), and simultaneous polling/WS reconnection handling in solune/frontend/src/hooks/useRealTimeSync.test.tsx
- [ ] T030 [P] [US5] Extend board refresh tests with: tab visibility staleness check on restore, overnight tab restoration single-refresh behavior, and manual refresh overrides debounce in solune/frontend/src/hooks/useBoardRefresh.test.tsx
- [ ] T031 [US5] Run full backend and frontend test suites to confirm zero regressions (SC-007) and record "after" metric values for comparison against Phase 2 baselines

**Checkpoint**: All tests pass, zero regressions. "After" metrics recorded alongside "before" metrics for final comparison.

---

## Phase 7: User Story 6 — Optional Second-Wave Planning (Priority: P3)

**Goal**: Produce a data-driven recommendation on whether deeper structural changes (virtualization, service decomposition) are needed based on measured before/after results.

**Independent Test**: Review the documented measurement comparison and confirm the recommendation is supported by data.

- [ ] T032 [US6] Compare before/after baseline metrics against success criteria SC-001 through SC-010 and document measurement results with pass/fail status for each criterion in specs/001-performance-review/verification-results.md
- [ ] T033 [US6] Based on measurement results: if targets not met, draft follow-on plan recommending board virtualization (for UI lag) and/or service decomposition (for API churn) with specific scope and priority; if targets met, document "no further work needed" with supporting data in specs/001-performance-review/second-wave-plan.md

**Checkpoint**: Performance review complete. Clear recommendation documented for next steps (or confirmation that no further work is needed).

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final quality checks, linting, and end-to-end verification across all modified files.

- [ ] T034 [P] Run backend linting (`uv run ruff check src/`) and type checking (`uv run pyright src/`) on all modified backend files in solune/backend/
- [ ] T035 [P] Run frontend linting (`npm run lint`), type checking (`npm run type-check`), and production build (`npm run build`) on all modified frontend files in solune/frontend/
- [ ] T036 Run quickstart.md verification commands end-to-end to confirm development setup, targeted tests, and lint/type checks all pass
- [ ] T037 Final manual verification per SC-009: confirm WebSocket updates refresh task data quickly, fallback polling remains safe, manual refresh bypasses caches as intended, and board interactions remain responsive on a representative project board

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational / US1 Baseline (Phase 2)**: Depends on Setup — **BLOCKS all optimization work (Phases 3–7)**
- **US2 Backend API (Phase 3)**: Depends on Phase 2 baselines
- **US3 Frontend Refresh (Phase 4)**: Depends on Phase 2 baselines — **can proceed in parallel with Phase 3**
- **US4 Render Optimization (Phase 5)**: Depends on Phase 4 (refresh policy must be stable before optimizing render paths)
- **US5 Verification (Phase 6)**: Depends on Phases 3, 4, and 5 (all optimizations complete)
- **US6 Second-Wave (Phase 7)**: Depends on Phase 6 (verification results needed for recommendation)
- **Polish (Phase 8)**: Depends on all desired phases being complete

### User Story Dependencies

- **US1 (P1) — Baseline**: No dependencies on other stories. BLOCKS all optimization stories.
- **US2 (P1) — Backend API**: Depends on US1. No dependencies on US3/US4. Can run in parallel with US3.
- **US3 (P2) — Frontend Refresh**: Depends on US1. No dependencies on US2. Can run in parallel with US2.
- **US4 (P2) — Render Optimization**: Depends on US3 (refresh policy must be stable). Cannot run in parallel with US3.
- **US5 (P3) — Verification**: Depends on US2, US3, US4 (all optimizations complete).
- **US6 (P3) — Second-Wave**: Depends on US5 (measurement comparison needed).

### Within Each User Story

- Tests (where included) written FIRST — verify they FAIL before implementation
- Implementation tasks in different files can run in parallel ([P] marker)
- Same-file tasks run sequentially in listed order
- Story complete before moving to next priority (unless parallel opportunity exists)

### Parallel Opportunities

**Phase 2 (US1 Baseline)**:

- T005, T006, T007, T008 can all run in parallel (different test files)

**Phase 3 (US2) and Phase 4 (US3) — inter-phase parallelism**:

- US2 (backend) and US3 (frontend) can run in parallel once baselines are complete
- Within US2: T012, T013, T014 can run in parallel (different source files)
- Within US3: T018, T019 can run in parallel (different source files)

**Phase 5 (US4)**:

- T022, T023, T024, T025 can all run in parallel (different component files)

**Phase 6 (US5)**:

- T027, T028, T029, T030 can all run in parallel (different test files)

**Phase 8 (Polish)**:

- T034, T035 can run in parallel (backend vs. frontend)

---

## Parallel Example: User Story 2 (Backend API)

```text
# Phase 3 — Tests first (sequential for same file, parallel for different files):
T010: "Add idle + cache reuse tests in test_api_board.py"
T011: "Add polling fallback test in test_copilot_polling.py"  ← parallel with T010

# Phase 3 — Implementation (all parallel — different source files):
T012: "Fix sub-issue cache reuse in board.py"
T013: "Fix WebSocket refresh logic in projects.py"
T014: "Fix polling loop change detection in polling_loop.py"
```

## Parallel Example: User Story 3 + User Story 2 (Cross-Story)

```text
# After Phase 2 baselines complete, both stories can start simultaneously:

# Developer A — US2 Backend:
T010–T014: Backend API consumption fixes

# Developer B — US3 Frontend:
T015–T019: Frontend refresh policy fixes
```

## Parallel Example: User Story 4 (Render Optimization)

```text
# Component-level tasks (all different files, all parallel):
T022: "Verify BoardColumn memo in BoardColumn.tsx"
T023: "Verify IssueCard memo in IssueCard.tsx"
T024: "Wrap AddAgentPopover in memo in AddAgentPopover.tsx"
T025: "Verify ChatPopup RAF-gating in ChatPopup.tsx"
```

---

## Implementation Strategy

### MVP First (US1 + US2 Only)

1. Complete Phase 1: Setup — verify environment
2. Complete Phase 2: US1 Baseline — capture "before" metrics **(CRITICAL — blocks everything)**
3. Complete Phase 3: US2 Backend API — highest-value backend fixes
4. **STOP and VALIDATE**: Re-run baseline tests, compare idle API call counts against SC-001 (≥50% reduction) and SC-002 (≥30% fewer calls with warm caches)
5. Deploy/demo if backend improvements are sufficient

### Incremental Delivery

1. Phases 1–2 → Baselines captured → Foundation ready
2. Phase 3 (US2) → Backend API consumption reduced → Test against SC-001, SC-002 **(MVP!)**
3. Phase 4 (US3) → Frontend refresh policy unified → Test against SC-003, SC-004
4. Phase 5 (US4) → Board rendering improved → Test against SC-005, SC-006
5. Phase 6 (US5) → Full verification → Test against SC-007, SC-008
6. Phase 7 (US6) → Recommendation documented → SC-009 validated
7. Each story adds measurable value without breaking previous stories

### Parallel Team Strategy

With multiple developers after Phase 2 baselines are complete:

1. Team completes Setup + Baseline together (Phases 1–2)
2. Once baselines are captured:
   - **Developer A**: US2 — Backend API fixes (Phase 3)
   - **Developer B**: US3 — Frontend refresh policy (Phase 4)
3. After US3 completes:
   - **Developer B**: US4 — Render optimization (Phase 5)
4. After all optimization stories complete:
   - **Team**: US5 — Verification (Phase 6) → US6 — Recommendation (Phase 7) → Polish (Phase 8)

---

## Notes

- **[P]** tasks = different files, no cross-dependencies — can execute in parallel
- **[Story]** label maps task to specific user story for traceability
- Each user story is independently completable and testable against its success criteria
- Tests (where included) must fail before implementation (TDD)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All optimizations use existing patterns (memoization, throttling, cache reuse, debouncing) — no new dependencies
- Preserve existing manual refresh semantics (`refresh=true` always bypasses caches)
- Preserve existing rate-limit handling (stale fallback, user notification)
- Reference contracts/refresh-policy.md for refresh behavior rules (Rules 1–8)
- Reference research.md for technical decisions (RT-001 through RT-008)
