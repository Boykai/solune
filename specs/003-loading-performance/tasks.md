# Tasks: Loading Performance

**Feature**: `003-loading-performance`  
**Input**: Design documents from `/home/runner/work/solune/solune/specs/003-loading-performance/`  
**Prerequisites**: `/home/runner/work/solune/solune/specs/003-loading-performance/plan.md` ✅, `/home/runner/work/solune/solune/specs/003-loading-performance/spec.md` ✅, `/home/runner/work/solune/solune/specs/003-loading-performance/research.md` ✅, `/home/runner/work/solune/solune/specs/003-loading-performance/data-model.md` ✅, `/home/runner/work/solune/solune/specs/003-loading-performance/quickstart.md` ✅, `/home/runner/work/solune/solune/specs/003-loading-performance/contracts/loading-performance-api.yaml` ✅

**Tests**: Included — the specification defines independent tests for each story and the plan/quickstart already name the backend unit, frontend hook/page, optional performance, and manual validation flows that must be executed.

**Organization**: Tasks are grouped by user story so each increment can be implemented and validated independently while still respecting the shared backend/frontend load-state contract.

## Format: `- [ ] T### [P?] [US#?] Description with file path`

- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[US#]**: Required on user-story tasks only
- **No [US#]**: Setup, Foundational, and Polish phases only
- Every task below includes exact absolute file paths or commands scoped to absolute repository paths

## Path Conventions

- **Feature docs**: `/home/runner/work/solune/solune/specs/003-loading-performance/`
- **Backend root**: `/home/runner/work/solune/solune/solune/backend`
- **Frontend root**: `/home/runner/work/solune/solune/solune/frontend`
- **Backend hot path**: `/home/runner/work/solune/solune/solune/backend/src/services/github_projects/board.py`
- **Project selection API**: `/home/runner/work/solune/solune/solune/backend/src/api/projects.py`
- **Board API contract**: `/home/runner/work/solune/solune/solune/backend/src/api/board.py`
- **Frontend board flow**: `/home/runner/work/solune/solune/solune/frontend/src/hooks/useProjectBoard.ts`, `/home/runner/work/solune/solune/solune/frontend/src/hooks/useProjects.ts`, `/home/runner/work/solune/solune/solune/frontend/src/pages/ProjectsPage.tsx`
- **Primary backend tests**: `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_board.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_projects.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_board.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_github_projects.py`
- **Primary frontend tests**: `/home/runner/work/solune/solune/solune/frontend/src/hooks/useProjects.test.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/hooks/useProjectBoard.test.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/pages/ProjectsPage.test.tsx`

---

## Phase 1: Setup (Baseline and Traceability)

**Purpose**: Confirm the canonical feature inputs, baseline validation commands, and the exact source files that the implementation will touch.

- [ ] T001 Audit the canonical feature docs under `/home/runner/work/solune/solune/specs/003-loading-performance/` against the current hot-path files in `/home/runner/work/solune/solune/solune/backend/src/services/github_projects/board.py`, `/home/runner/work/solune/solune/solune/backend/src/api/projects.py`, and `/home/runner/work/solune/solune/solune/frontend/src/pages/ProjectsPage.tsx`
- [ ] T002 [P] Run the backend baseline called out in `/home/runner/work/solune/solune/specs/003-loading-performance/quickstart.md` against `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_board.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_projects.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_board.py`, and `/home/runner/work/solune/solune/solune/backend/tests/unit/test_github_projects.py`
- [ ] T003 [P] Run the frontend baseline called out in `/home/runner/work/solune/solune/specs/003-loading-performance/quickstart.md` against `/home/runner/work/solune/solune/solune/frontend/src/hooks/useProjects.test.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/hooks/useProjectBoard.test.tsx`, and `/home/runner/work/solune/solune/solune/frontend/src/pages/ProjectsPage.test.tsx`
- [ ] T004 Inventory the existing dedup, polling, and stale-fallback seams in `/home/runner/work/solune/solune/solune/backend/src/services/cache.py`, `/home/runner/work/solune/solune/solune/backend/src/services/github_projects/service.py`, `/home/runner/work/solune/solune/solune/backend/src/services/copilot_polling/polling_loop.py`, and `/home/runner/work/solune/solune/solune/backend/src/main.py` before story work begins

**Checkpoint**: Canonical inputs verified, baseline commands recorded, and the exact backend/frontend integration seams are known.

---

## Phase 2: Foundational (Shared Contract and Load-State Primitives)

**Purpose**: Establish the shared load-state contract that all user stories depend on.

**⚠️ CRITICAL**: No user story work should begin until this phase is complete because every story relies on the same board-load metadata and request-shaping contract.

- [ ] T005 Define the shared `BoardLoadPolicy`, `BoardLoadState`, `DeferredBoardTask`, and `InFlightLoadKey` structures in `/home/runner/work/solune/solune/solune/backend/src/models/board.py` so backend stories share one source of truth for initial, refresh, background, and selection-warmup behavior
- [ ] T006 [P] Extend `/home/runner/work/solune/solune/solune/backend/src/api/board.py` and `/home/runner/work/solune/solune/specs/003-loading-performance/contracts/loading-performance-api.yaml` with `load_mode`, `load_state`, refresh semantics, and the `board_warmup_started` response field required by the plan
- [ ] T007 [P] Extend `/home/runner/work/solune/solune/solune/frontend/src/services/api.ts` and the schema guards under `/home/runner/work/solune/solune/solune/frontend/src/services/schemas/` to parse the new board envelope and load-state metadata
- [ ] T008 Add foundational regression coverage in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_board.py` and `/home/runner/work/solune/solune/solune/frontend/src/hooks/useProjectBoard.test.tsx` for the shared board envelope, `load_mode`, and `load_state` parsing/default behavior

**Checkpoint**: Backend and frontend share the same load-state contract, and later stories can build on it without redefining response semantics.

---

## Phase 3: User Story 1 — Fast Project Board Load on Selection (Priority: P1) 🎯 MVP

**Goal**: Start board work as soon as a project is selected and render an interactive board as early as possible for both small and large projects.

**Independent Test**: Log in, open `/projects`, select a project, and verify that the board becomes interactive using the first warmed payload instead of waiting for all follow-on work to finish.

- [ ] T009 [P] [US1] Add selection warm-up API coverage in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_projects.py` for `POST /api/v1/projects/{project_id}/select` returning quickly while scheduling board warm-up and surfacing `board_warmup_started`
- [ ] T010 [P] [US1] Add frontend flow coverage in `/home/runner/work/solune/solune/solune/frontend/src/hooks/useProjects.test.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/hooks/useProjectBoard.test.tsx`, and `/home/runner/work/solune/solune/solune/frontend/src/pages/ProjectsPage.test.tsx` for select → interactive board → no blank or broken loading state
- [ ] T011 [US1] Implement best-effort board warm-up scheduling and `board_warmup_started` response handling in `/home/runner/work/solune/solune/solune/backend/src/api/projects.py`
- [ ] T012 [US1] Refactor `/home/runner/work/solune/solune/solune/backend/src/services/github_projects/board.py` so initial loads assemble and cache an interactive board snapshot before Done/history backfill completes
- [ ] T013 [US1] Update `/home/runner/work/solune/solune/solune/frontend/src/hooks/useProjects.ts` and `/home/runner/work/solune/solune/solune/frontend/src/hooks/useProjectBoard.ts` to reuse warmed board data, preserve repeat-visit cache hits, and keep the first interactive payload query-compatible
- [ ] T014 [US1] Update `/home/runner/work/solune/solune/solune/frontend/src/pages/ProjectsPage.tsx` and any reused board-status components under `/home/runner/work/solune/solune/solune/frontend/src/components/board/` to show a loading/progress state without ever showing a blank or broken board
- [ ] T015 [US1] Run the US1 targeted validation commands from `/home/runner/work/solune/solune/specs/003-loading-performance/quickstart.md` against the backend project/board unit tests and the frontend hook/page tests

**Checkpoint**: Selecting a project warms the board path immediately, and the first board payload is independently demonstrable as interactive.

---

## Phase 4: User Story 2 — Skip Unnecessary Work for Completed Items (Priority: P1)

**Goal**: Stop fetching fresh sub-issue data for Done/closed parent issues during the initial load while preserving the existing Done-column pill experience.

**Independent Test**: Load a project with Done/closed parent issues and verify that initial board rendering skips their sub-issue fetches, still shows stored pill links, and re-fetches them only on explicit full refresh or reactivation.

- [ ] T016 [P] [US2] Add backend skip-rule coverage in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_board.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_board.py`, and `/home/runner/work/solune/solune/solune/backend/tests/unit/test_github_projects.py` for Done/closed parents being excluded from initial sub-issue fetches while active parents still fetch normally
- [ ] T017 [P] [US2] Add regression coverage in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_board.py` and `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_board.py` for cached Done-column pill rendering, all-Done projects, and active-again items on refresh
- [ ] T018 [US2] Implement Done/closed parent skip rules and active-parent-only sub-issue fetching in `/home/runner/work/solune/solune/solune/backend/src/services/github_projects/board.py`
- [ ] T019 [US2] Update `/home/runner/work/solune/solune/solune/backend/src/services/github_projects/issues.py` and `/home/runner/work/solune/solune/solune/backend/src/services/done_items_store.py` so Done-column parent cards reuse stored pill data during initial loads
- [ ] T020 [US2] Extend `/home/runner/work/solune/solune/solune/backend/src/api/board.py` and `/home/runner/work/solune/solune/solune/backend/src/services/github_projects/board.py` so explicit refresh/full-load flows re-fetch Done/closed sub-issues and reactivated items when correctness is requested
- [ ] T021 [US2] Run the US2 backend validation set from `/home/runner/work/solune/solune/specs/003-loading-performance/quickstart.md`, plus `/home/runner/work/solune/solune/solune/backend/tests/performance/test_board_load_time.py` when authenticated performance credentials are available

**Checkpoint**: Initial loads avoid the largest Done/closed sub-issue bottleneck without changing the visible Done-column pill behavior.

---

## Phase 5: User Story 3 — Eliminate Duplicate Data Fetches (Priority: P2)

**Goal**: Ensure simultaneous callers share the same upstream project-list, board-project-list, and board warm-up work instead of making duplicate external requests.

**Independent Test**: Simulate concurrent cold-start requests for project list and board list data and verify that only one upstream fetch is performed for each distinct key.

- [ ] T022 [P] [US3] Add concurrency coverage in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_projects.py` and `/home/runner/work/solune/solune/solune/backend/tests/unit/test_github_projects.py` for simultaneous `/projects`, `/board/projects`, and selection-warmup callers sharing a single upstream fetch
- [ ] T023 [US3] Implement API-level in-flight dedup keys and waiter bookkeeping in `/home/runner/work/solune/solune/solune/backend/src/services/cache.py` for user-scoped project-list and board-project-list reads
- [ ] T024 [US3] Integrate the shared dedup layer with `/home/runner/work/solune/solune/solune/backend/src/api/projects.py`, `/home/runner/work/solune/solune/solune/backend/src/api/board.py`, and `/home/runner/work/solune/solune/solune/backend/src/services/github_projects/service.py` so board warm-up and board reads coalesce around the same work key
- [ ] T025 [US3] Update `/home/runner/work/solune/solune/solune/frontend/src/hooks/useProjects.ts` and `/home/runner/work/solune/solune/solune/frontend/src/hooks/useProjects.test.tsx` so concurrent cold-start consumers reuse the same project-list query result instead of triggering duplicate loads
- [ ] T026 [US3] Run the US3 targeted backend/frontend validation commands for deduplicated project-list and board-project flows

**Checkpoint**: Cold-start duplicate work is coalesced at the backend and no longer multiplied by simultaneous consumers.

---

## Phase 6: User Story 4 — Non-Blocking Background Processing (Priority: P2)

**Goal**: Keep non-essential background work off the initial board-loading critical path and cancel stale work when the active project changes.

**Independent Test**: Select a project, verify the board becomes interactive before polling/background work begins, then rapidly switch projects and confirm stale work is cancelled rather than overwriting the active board.

- [ ] T027 [P] [US4] Add backend background-task coverage in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_projects.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_board.py`, and `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_board.py` for deferred scheduling, stale-project cancellation, and rapid-switch supersession
- [ ] T028 [P] [US4] Add UI/regression coverage in `/home/runner/work/solune/solune/solune/frontend/src/pages/ProjectsPage.test.tsx` and `/home/runner/work/solune/solune/solune/frontend/src/hooks/useProjectBoard.test.tsx` for non-blocking progress/error notices while active columns remain interactive
- [ ] T029 [US4] Implement deferred background task scheduling and cancellation for warm-up follow-on work in `/home/runner/work/solune/solune/solune/backend/src/api/projects.py` and `/home/runner/work/solune/solune/solune/backend/src/services/github_projects/board.py`
- [ ] T030 [US4] Preserve or harden delayed Copilot polling start in `/home/runner/work/solune/solune/solune/backend/src/services/copilot_polling/polling_loop.py` and `/home/runner/work/solune/solune/solune/backend/src/main.py` so initial board loads are not contended by automated polling
- [ ] T031 [US4] Update `/home/runner/work/solune/solune/solune/frontend/src/pages/ProjectsPage.tsx` and the board-status components under `/home/runner/work/solune/solune/solune/frontend/src/components/board/` to surface stale/rate-limit/progress notices only after the board is interactive
- [ ] T032 [US4] Run the US4 targeted backend/frontend validation commands and the rapid-project-switch manual smoke flow from `/home/runner/work/solune/solune/specs/003-loading-performance/quickstart.md`

**Checkpoint**: Background work is clearly deferred, cancellable, and non-blocking from the user’s perspective.

---

## Phase 7: User Story 5 — Defer Reconciliation to Background (Priority: P3)

**Goal**: Remove reconciliation from the initial response path while still merging any missing items back into the board after the user can already interact with it.

**Independent Test**: Load a board, confirm the initial response completes before reconciliation runs, and verify that any reconciled additions appear later without a page reload or user interruption.

- [ ] T033 [P] [US5] Add backend regression coverage in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_board.py` and `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_board.py` proving reconciliation is absent from initial loads and merged back after background completion
- [ ] T034 [P] [US5] Add frontend regression coverage in `/home/runner/work/solune/solune/solune/frontend/src/hooks/useProjectBoard.test.tsx` and `/home/runner/work/solune/solune/solune/frontend/src/pages/ProjectsPage.test.tsx` for silent reconciliation completion without a page reload or user-facing interruption
- [ ] T035 [US5] Refactor reconciliation in `/home/runner/work/solune/solune/solune/backend/src/services/github_projects/board.py` into deferred post-interactive tasks keyed by the load-policy and deferred-task state model from `/home/runner/work/solune/solune/solune/backend/src/models/board.py`
- [ ] T036 [US5] Update `/home/runner/work/solune/solune/solune/backend/src/api/board.py`, `/home/runner/work/solune/solune/solune/frontend/src/services/api.ts`, and `/home/runner/work/solune/solune/solune/frontend/src/hooks/useProjectBoard.ts` so reconciliation progress/completion can invalidate or refresh the board without blocking the initial response
- [ ] T037 [US5] Run the US5 targeted backend/frontend validation commands, plus the optional authenticated performance harness from `/home/runner/work/solune/solune/specs/003-loading-performance/quickstart.md` when credentials are available

**Checkpoint**: Reconciliation still guarantees eventual accuracy, but it no longer taxes the first interactive board response.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Run the final regression, performance, and manual verification gates across all stories.

- [ ] T038 Run the full backend regression command set from `/home/runner/work/solune/solune/specs/003-loading-performance/quickstart.md` on `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_board.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_projects.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_board.py`, and `/home/runner/work/solune/solune/solune/backend/tests/unit/test_github_projects.py`
- [ ] T039 [P] Run the frontend regression command set from `/home/runner/work/solune/solune/specs/003-loading-performance/quickstart.md` on `/home/runner/work/solune/solune/solune/frontend/src/hooks/useProjects.test.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/hooks/useProjectBoard.test.tsx`, and `/home/runner/work/solune/solune/solune/frontend/src/pages/ProjectsPage.test.tsx`
- [ ] T040 [P] Run `npm run type-check`, `npm run lint`, and `npm run build` in `/home/runner/work/solune/solune/solune/frontend` for the progressive-loading UI changes
- [ ] T041 [P] Run the optional authenticated checks in `/home/runner/work/solune/solune/solune/backend/tests/performance/test_board_load_time.py` and `/home/runner/work/solune/solune/solune/frontend/e2e/project-load-performance.spec.ts`
- [ ] T042 [P] Execute the manual verification flow from `/home/runner/work/solune/solune/specs/003-loading-performance/quickstart.md` across `/projects`: select small and large projects, confirm interactive-first loading, test explicit full refresh, and verify rapid-switch cancellation

**Checkpoint**: Backend correctness, frontend UX, manual flows, and optional performance checks all confirm the loading-performance work is complete.

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 (Setup) -> Phase 2 (Foundational) -> Phase 3 (US1 MVP)
                                              ├-> Phase 4 (US2)
                                              ├-> Phase 5 (US3)
                                              └-> Phase 6 (US4) after US1 + US3
                                                     └-> Phase 7 (US5) after US1 + US4
                                                           └-> Final Phase (Polish)
```

### User Story Dependencies

| Story | Priority | Depends On | Why |
|-------|----------|------------|-----|
| US1 | P1 | Phase 2 | Establishes the warm-up + interactive-load path that all later stories build on |
| US2 | P1 | US1 | Reuses the interactive-load path to decide when Done/closed work is skipped or refreshed |
| US3 | P2 | Phase 2 | Can start once the shared load-state contract exists |
| US4 | P2 | US1, US3 | Needs the warm-up path plus the dedup/cancellation primitives |
| US5 | P3 | US1, US4 | Defers reconciliation on top of the interactive-load and deferred-task infrastructure |

### Within Each Phase

- Tasks marked **[P]** touch different files and can be run in parallel after their phase prerequisites are satisfied.
- Validation tasks (`T015`, `T021`, `T026`, `T032`, `T037`, `T038`–`T042`) should execute only after the implementation tasks in the same phase are complete.
- US2 and US3 can proceed in parallel after US1 if different developers own the backend hot path versus the dedup/query layer.

---

## Parallel Execution Examples Per Story

### US1 Parallel Example

```text
Run T009 and T010 together, then split T013 and T014 once T011-T012 have defined the warmed interactive payload.
```

### US2 Parallel Example

```text
Run T016 and T017 together, then implement T018 and T019 in parallel because they touch different backend modules before finishing T020.
```

### US3 Parallel Example

```text
Run T022 first, then execute T023 (backend dedup helpers) and T025 (frontend query reuse) in parallel before wiring T024.
```

### US4 Parallel Example

```text
Run T027 and T028 together, then split T029 (deferred task orchestration) and T030 (polling timing hardening) before landing T031.
```

### US5 Parallel Example

```text
Run T033 and T034 together, then complete T035 before wiring the API/frontend completion flow in T036.
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Deliver Phase 3 (US1) so project selection immediately warms the board path and returns an interactive-first board.
3. Stop and validate the end-to-end project-selection experience with T015 before expanding scope.

### Incremental Delivery

1. Add US2 to remove the biggest Done/closed sub-issue bottleneck.
2. Add US3 to remove duplicate cold-start fetches and protect API quota.
3. Add US4 to keep background work non-blocking and cancellable.
4. Add US5 to defer reconciliation without losing eventual correctness.
5. Finish with the Polish phase for regressions, optional perf checks, and manual verification.

### Parallel Team Strategy

1. One developer owns the backend board hot path (`/home/runner/work/solune/solune/solune/backend/src/services/github_projects/board.py`) for US1, US2, and US5.
2. One developer owns the dedup/background orchestration seam in `/home/runner/work/solune/solune/solune/backend/src/services/cache.py`, `/home/runner/work/solune/solune/solune/backend/src/api/projects.py`, and `/home/runner/work/solune/solune/solune/backend/src/services/copilot_polling/polling_loop.py` for US3 and US4.
3. One developer owns the frontend loading UX in `/home/runner/work/solune/solune/solune/frontend/src/hooks/` and `/home/runner/work/solune/solune/solune/frontend/src/pages/ProjectsPage.tsx` to keep contract, state, and UI updates aligned.

---

## Notes

- Total tasks: **42**
- User-story tasks: **US1 = 7**, **US2 = 6**, **US3 = 5**, **US4 = 6**, **US5 = 5**
- MVP scope: **US1 only** after Setup + Foundational phases
- Every checklist item follows the required `- [ ] T### [P?] [US#?] Description with file path` format
