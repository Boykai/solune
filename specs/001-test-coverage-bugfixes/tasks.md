# Tasks: Full Coverage Push + Bug Fixes

**Input**: Design documents from `/specs/001-test-coverage-bugfixes/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests ARE the primary deliverable for this feature. All test tasks are included by design.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app (monorepo)**: `solune/backend/src/`, `solune/backend/tests/`, `solune/frontend/src/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new project initialization required — existing monorepo with established test infrastructure. Verify prerequisites are in place.

- [x] T001 Verify concurrency test files exist at `solune/backend/tests/concurrency/test_interleaving.py` and `solune/backend/tests/concurrency/test_polling_races.py` with `@pytest.mark.xfail` markers
- [x] T002 [P] Verify MCP test directory exists at `solune/backend/tests/unit/test_mcp_server/` with existing test files (test_auth.py, test_middleware.py, test_resources.py, test_server.py, test_tools_agents.py)
- [x] T003 [P] Verify frontend board component directory exists at `solune/frontend/src/components/board/` with target components (CleanUpButton.tsx, PipelineStagesSection.tsx, AddAgentPopover.tsx, etc.)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add concurrency lock infrastructure to `state.py` — MUST complete before ANY user story can proceed

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Add `import asyncio` (if not present) and `_polling_state_lock = asyncio.Lock()` to `solune/backend/src/services/copilot_polling/state.py`
- [x] T005 Add `_polling_startup_lock = asyncio.Lock()` to `solune/backend/src/services/copilot_polling/state.py`

**Checkpoint**: Lock infrastructure ready — concurrency bug fix stories can now proceed

---

## Phase 3: User Story 1 — Fix Polling State Race Condition (Priority: P1) 🎯 MVP

**Goal**: Serialize all concurrent mutations to `_polling_state` so that no field update is lost due to a race condition

**Independent Test**: Run `pytest tests/concurrency/test_interleaving.py -v` — previously-xfail test passes reliably

### Implementation for User Story 1

- [x] T006 [US1] Import `_polling_state_lock` from `state.py` in `solune/backend/src/services/copilot_polling/polling_loop.py`
- [x] T007 [US1] Guard `_polling_state` field mutations at lines 316, 323, 404-405, 494-495, 617, 713 with `async with _polling_state_lock` in `solune/backend/src/services/copilot_polling/polling_loop.py`
- [x] T008 [P] [US1] Import `_polling_state_lock` from `state.py` in `solune/backend/src/services/copilot_polling/pipeline.py`
- [x] T009 [P] [US1] Guard `_polling_state` field mutations at lines 1009-1010, 1102-1103, 3284-3285, 3464-3465 with `async with _polling_state_lock` in `solune/backend/src/services/copilot_polling/pipeline.py`
- [x] T010 [US1] Remove `@pytest.mark.xfail` marker from `solune/backend/tests/concurrency/test_interleaving.py`
- [x] T011 [US1] Verify: `pytest tests/concurrency/test_interleaving.py -v` passes without xfail

**Checkpoint**: Polling state race condition is fixed — concurrent mutations are serialized via lock

---

## Phase 4: User Story 2 — Fix Duplicate Polling Tasks (Priority: P1)

**Goal**: Ensure `ensure_polling_started()` atomically checks-and-creates polling tasks so concurrent startup calls never create duplicates

**Independent Test**: Run `pytest tests/concurrency/test_polling_races.py -v` — previously-xfail test passes reliably

### Implementation for User Story 2

- [x] T012 [US2] Import `_polling_startup_lock` from `state.py` in `solune/backend/src/services/copilot_polling/__init__.py`
- [x] T013 [US2] Wrap the check-then-create sequence in `ensure_polling_started()` (~L263-332) with `async with _polling_startup_lock` in `solune/backend/src/services/copilot_polling/__init__.py`
- [x] T014 [US2] Remove `@pytest.mark.xfail` marker from `solune/backend/tests/concurrency/test_polling_races.py`
- [x] T015 [US2] Verify: `pytest tests/concurrency/test_polling_races.py -v` passes without xfail

**Checkpoint**: Duplicate polling task race condition is fixed — exactly one task per session guaranteed

---

## Phase 5: User Story 3 — Update Stale Polling Test Mocks (Priority: P1)

**Goal**: Replace deprecated mock targets in test_api_projects.py so that tests validate current production code paths

**Independent Test**: Run `pytest tests/unit/test_api_projects.py -v` — all tests pass; `grep poll_for_copilot_completion test_api_projects.py` returns no matches

### Implementation for User Story 3

- [x] T016 [US3] Replace `get_project_repository()` patches with `resolve_repository()` mocks in `solune/backend/tests/unit/test_api_projects.py` (L253-370)
- [x] T017 [US3] Replace `poll_for_copilot_completion()` patches with `ensure_polling_started()` mocks in `solune/backend/tests/unit/test_api_projects.py` (L253-370)
- [x] T018 [US3] Update mock return values and assertions to match `resolve_repository()` / `ensure_polling_started()` signatures in `solune/backend/tests/unit/test_api_projects.py`
- [x] T019 [US3] Verify: `grep -n "poll_for_copilot_completion\|get_project_repository" solune/backend/tests/unit/test_api_projects.py` returns no results
- [x] T020 [US3] Verify: `pytest tests/unit/test_api_projects.py -v` passes

**Checkpoint**: All P1 blocking stories complete — parallel user story work can now begin

---

## Phase 6: User Story 4 — Agent Preview Regression Test (Priority: P2)

**Goal**: Add regression test confirming `_extract_agent_preview()` returns None for malformed (non-list) tools configuration

**Independent Test**: Run `pytest tests/unit/test_agents_service.py::TestExtractAgentPreview -v` — new test passes alongside existing 6 tests

### Implementation for User Story 4

- [x] T021 [US4] Add test case for non-list `tools` value (e.g., `tools="read"`) to `TestExtractAgentPreview` class in `solune/backend/tests/unit/test_agents_service.py` — assert `_extract_agent_preview()` returns None
- [x] T022 [US4] Verify: `pytest tests/unit/test_agents_service.py::TestExtractAgentPreview -v` passes (7 tests total including new one)

**Checkpoint**: Agent preview guard validated — malformed tools input safely returns None

---

## Phase 7: User Story 5 — Backend MCP Server Coverage (Priority: P2)

**Goal**: Add/enhance unit tests for MCP middleware, tool endpoints, resource handlers, and template routes — target backend coverage 79% → 81%+

**Independent Test**: Run `pytest tests/unit/test_mcp_server/ -v --cov=src/services/mcp_server --cov-report=term-missing` — coverage improves for each target module

### Implementation for User Story 5

- [x] T023 [P] [US5] Enhance `solune/backend/tests/unit/test_mcp_server/test_middleware.py` — add tests for valid token auth, missing Authorization header, malformed token format, and context cleanup after request
- [x] T024 [P] [US5] Create `solune/backend/tests/unit/test_mcp_server/test_tools_chores.py` — test `list_chores()` CRUD operations, `trigger_chore()` with error dicts, invalid project_id handling
- [x] T025 [P] [US5] Create `solune/backend/tests/unit/test_mcp_server/test_tools_chat.py` — test `send_chat_message()`, `get_metadata()`, `cleanup_preflight()`, session handling
- [x] T026 [P] [US5] Create `solune/backend/tests/unit/test_mcp_server/test_tools_activity.py` — test `get_activity()` with limit boundaries (1, 100, out-of-range), `update_item_status()` with valid/invalid IDs
- [x] T027 [P] [US5] Enhance `solune/backend/tests/unit/test_mcp_server/test_resources.py` — add tests for resource type branches (projects, agents, chores), prompt template selection paths, error responses
- [x] T028 [P] [US5] Enhance `solune/backend/tests/unit/test_api_templates.py` — add tests for category enum filtering, 404 on missing template, pagination edge cases (empty results, boundary pages)
- [x] T029 [US5] Verify: `pytest tests/unit/test_mcp_server/ -v --cov=src/services/mcp_server --cov-report=term-missing` — middleware 41% → 80%+, tools 20-30% → 70%+, resources 46% → 70%+

**Checkpoint**: MCP server components have comprehensive unit test coverage

---

## Phase 8: User Story 6 — Frontend Scroll Behavior Coverage (Priority: P3)

**Goal**: Add tests for PageTransition scroll-to-top, CleanUpSummary scroll lock, and page section IDs — catch scroll-related regressions in CI

**Independent Test**: Run `npx vitest run --run src/layout/PageTransition.test.tsx src/components/board/CleanUpSummary.test.tsx` — all new tests pass

### Implementation for User Story 6

- [x] T030 [P] [US6] Create `solune/frontend/src/layout/PageTransition.test.tsx` — test key={pathname} remount on route change, `motion-safe:animate-page-enter` animation class present, Outlet renders children, null main element guard
- [x] T031 [P] [US6] Enhance `solune/frontend/src/components/board/CleanUpSummary.test.tsx` — verify `useScrollLock(true)` is called with constant `true` on component mount
- [x] T032 [P] [US6] Enhance page-level tests to verify section anchor IDs (`#agents-catalog`, `#chores-catalog`, `#tools-catalog`) render in the DOM for catalog pages
- [x] T033 [US6] Test `scrollIntoView` behavior in AgentsPipelinePage test in `solune/frontend/src/pages/`
- [x] T034 [US6] Verify: `npx vitest run --run src/layout/PageTransition.test.tsx src/components/board/CleanUpSummary.test.tsx` passes

**Checkpoint**: Scroll behavior has test coverage — regressions in scroll-to-top and scroll-lock will be caught by CI

---

## Phase 9: User Story 7 — Frontend Board Component Coverage (Priority: P3)

**Goal**: Add tests for board components — target board coverage 42% → 55%+

**Independent Test**: Run `npx vitest run --coverage` — board directory coverage rises above 55%; all CI thresholds pass

### Implementation for User Story 7

#### High Priority

- [x] T035 [P] [US7] Create `solune/frontend/src/components/board/CleanUpButton.test.tsx` — test cleanup workflow orchestration: idle → loading → confirming → executing → summary state transitions
- [x] T036 [P] [US7] Create `solune/frontend/src/components/board/PipelineStagesSection.test.tsx` — test pipeline stage rendering, agent dropdown display, pipeline selection interaction

#### Medium Priority

- [x] T037 [P] [US7] Create `solune/frontend/src/components/board/AddAgentPopover.test.tsx` — test Radix Popover trigger, async agent option loading, search filter, duplicate agent detection

#### Low Priority (Smoke + A11y Only)

- [x] T038 [P] [US7] Create `solune/frontend/src/components/board/AgentDragOverlay.test.tsx` — smoke render test and accessible markup validation
- [x] T039 [P] [US7] Create `solune/frontend/src/components/board/BoardDragOverlay.test.tsx` — smoke render test and accessible markup validation
- [x] T040 [P] [US7] Create `solune/frontend/src/components/board/AgentColumnCell.test.tsx` — smoke render test and accessible markup validation
- [x] T041 [P] [US7] Create `solune/frontend/src/components/board/AgentConfigRow.test.tsx` — smoke render test and accessible markup validation
- [x] T042 [P] [US7] Create `solune/frontend/src/components/board/AgentPresetSelector.test.tsx` — smoke render test and accessible markup validation
- [x] T043 [US7] Verify: `npx vitest run --coverage` — board coverage 42% → 55%+; all CI thresholds pass (statements ≥ 50%, branches ≥ 44%, functions ≥ 41%, lines ≥ 50%)

**Checkpoint**: Board component coverage target met — all interactive components have baseline test coverage

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all stories, type checking, and lint compliance

- [x] T044 [P] Run backend type check: `cd solune/backend && uv run pyright src` — no new type errors
- [x] T045 [P] Run frontend type check: `cd solune/frontend && npx tsc --noEmit` — no new type errors
- [x] T046 [P] Run backend lint: `cd solune/backend && uv run ruff check src tests` — no lint errors
- [x] T047 [P] Run frontend lint: `cd solune/frontend && npm run lint` — no lint errors
- [x] T048 Run full backend test suite: `cd solune/backend && uv run pytest tests/unit/ -v --cov=src --cov-report=term-missing` — coverage 79% → 81%+
- [x] T049 Run full frontend test suite: `cd solune/frontend && npx vitest run --coverage` — all thresholds pass
- [x] T050 Verify deprecated patches removed: `grep -rn "poll_for_copilot_completion\|get_project_repository" solune/backend/tests/unit/test_api_projects.py` — no matches
- [x] T051 Run concurrency test suite: `cd solune/backend && uv run pytest tests/concurrency/ -v` — both formerly-xfail tests pass
- [x] T052 Run quickstart.md full verification sequence from `specs/001-test-coverage-bugfixes/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — adds lock primitives to state.py — BLOCKS all user stories
- **US-1 (Phase 3)**: Depends on Foundational — uses `_polling_state_lock` from state.py
- **US-2 (Phase 4)**: Depends on Foundational — uses `_polling_startup_lock` from state.py — can run in parallel with US-1
- **US-3 (Phase 5)**: Depends on Foundational — refactors test mocks — can run in parallel with US-1 and US-2
- **US-4 (Phase 6)**: Depends on US-1/US-2/US-3 completion (Phase 1 of plan complete) — can run in parallel with US-5, US-6, US-7
- **US-5 (Phase 7)**: Depends on US-1/US-2/US-3 completion — can run in parallel with US-4, US-6, US-7
- **US-6 (Phase 8)**: Depends on US-1/US-2/US-3 completion — can run in parallel with US-4, US-5, US-7
- **US-7 (Phase 9)**: Depends on US-1/US-2/US-3 completion — can run in parallel with US-4, US-5, US-6
- **Polish (Phase 10)**: Depends on ALL user stories being complete

### User Story Dependencies

- **US-1 (P1)**: Depends on Foundational locks — no cross-story dependencies
- **US-2 (P1)**: Depends on Foundational locks — no cross-story dependencies (can parallel with US-1)
- **US-3 (P1)**: No cross-story dependencies (can parallel with US-1, US-2)
- **US-4 (P2)**: Independent — no dependencies on other stories (only on Phase 1 completion)
- **US-5 (P2)**: Independent — no dependencies on other stories (only on Phase 1 completion)
- **US-6 (P3)**: Independent — no dependencies on other stories (only on Phase 1 completion)
- **US-7 (P3)**: Independent — no dependencies on other stories (only on Phase 1 completion)

### Within Each User Story

- Source code changes before test marker removal
- Lock imports before lock usage
- Mock updates before assertion updates
- Test file creation before coverage verification
- Component tests can run in parallel (different files)

### Parallel Opportunities

- **Phase 2**: T004 and T005 modify the same file (state.py) — MUST be sequential
- **Phase 3 + 4 + 5**: US-1, US-2, US-3 can run in parallel (different files except shared state.py dependency)
- **Phase 6 + 7 + 8 + 9**: US-4, US-5, US-6, US-7 are fully independent — all can run in parallel
- **Phase 7 (US-5)**: All test file tasks (T023-T028) are [P] — different test files
- **Phase 8 (US-6)**: T030, T031, T032 are [P] — different test files
- **Phase 9 (US-7)**: All test file tasks (T035-T042) are [P] — different test files
- **Phase 10**: T044-T047 are [P] — different check tools

---

## Parallel Example: User Story 5 (Backend MCP Coverage)

```bash
# Launch all MCP test tasks in parallel (different files):
Task T023: "Enhance test_middleware.py — header parsing, context cleanup, error paths"
Task T024: "Create test_tools_chores.py — CRUD operations, error dicts"
Task T025: "Create test_tools_chat.py — send_chat_message, get_metadata"
Task T026: "Create test_tools_activity.py — get_activity limits, update_item_status"
Task T027: "Enhance test_resources.py — resource type branches, prompt selection"
Task T028: "Enhance test_api_templates.py — category filtering, 404, pagination"
```

## Parallel Example: User Story 7 (Frontend Board Coverage)

```bash
# Launch high-priority board tests in parallel:
Task T035: "Create CleanUpButton.test.tsx — cleanup workflow orchestration"
Task T036: "Create PipelineStagesSection.test.tsx — pipeline stages + agent dropdown"

# Then medium-priority:
Task T037: "Create AddAgentPopover.test.tsx — Radix Popover + async fetch"

# Then low-priority smoke tests (all parallel):
Task T038: "Create AgentDragOverlay.test.tsx — smoke + a11y"
Task T039: "Create BoardDragOverlay.test.tsx — smoke + a11y"
Task T040: "Create AgentColumnCell.test.tsx — smoke + a11y"
Task T041: "Create AgentConfigRow.test.tsx — smoke + a11y"
Task T042: "Create AgentPresetSelector.test.tsx — smoke + a11y"
```

---

## Implementation Strategy

### MVP First (User Stories 1-3 — Concurrency Fixes)

1. Complete Phase 1: Setup verification
2. Complete Phase 2: Foundational lock infrastructure (CRITICAL — blocks all stories)
3. Complete Phase 3: US-1 — Fix polling state race condition
4. Complete Phase 4: US-2 — Fix duplicate polling tasks
5. Complete Phase 5: US-3 — Update stale test mocks
6. **STOP and VALIDATE**: `pytest tests/concurrency/ -v` — both tests pass; `grep` for deprecated mocks returns nothing
7. All blocking bugs are fixed — safe to proceed with coverage expansion

### Incremental Delivery

1. Complete Setup + Foundational → Lock infrastructure ready
2. Add US-1 + US-2 + US-3 → Concurrency bugs fixed, test mocks updated (MVP!)
3. Add US-4 → Agent preview regression guard validated
4. Add US-5 → Backend MCP coverage 79% → 81%+
5. Add US-6 → Frontend scroll behavior covered
6. Add US-7 → Frontend board coverage 42% → 55%+
7. Each story adds coverage value without breaking previous stories

### Parallel Team Strategy

With multiple developers after Phase 2 (Foundational) completes:

1. **Developer A**: US-1 (polling_loop.py + pipeline.py locks) + US-2 (startup lock)
2. **Developer B**: US-3 (stale mocks) + US-4 (agent preview regression test)
3. After P1 stories complete:
   - **Developer A**: US-5 (backend MCP coverage)
   - **Developer B**: US-6 (frontend scroll) + US-7 (frontend board)
4. Stories integrate independently — no merge conflicts expected

---

## Summary

| Metric | Value |
|--------|-------|
| **Total Tasks** | 52 |
| **US-1 Tasks** | 6 (T006-T011) |
| **US-2 Tasks** | 4 (T012-T015) |
| **US-3 Tasks** | 5 (T016-T020) |
| **US-4 Tasks** | 2 (T021-T022) |
| **US-5 Tasks** | 7 (T023-T029) |
| **US-6 Tasks** | 5 (T030-T034) |
| **US-7 Tasks** | 9 (T035-T043) |
| **Setup Tasks** | 3 (T001-T003) |
| **Foundational Tasks** | 2 (T004-T005) |
| **Polish Tasks** | 9 (T044-T052) |
| **Parallel Opportunities** | 28 tasks marked [P] |
| **Suggested MVP Scope** | US-1 + US-2 + US-3 (Phases 3-5, 15 tasks) |
| **Backend Coverage Target** | 79% → 81%+ |
| **Frontend Board Coverage Target** | 42% → 55%+ |

### Format Validation

✅ ALL 52 tasks follow the checklist format: `- [ ] [TaskID] [P?] [Story?] Description with file path`
✅ Setup phase tasks (T001-T003): No story label
✅ Foundational phase tasks (T004-T005): No story label
✅ User story phase tasks (T006-T043): All have [US#] story labels
✅ Polish phase tasks (T044-T052): No story label
✅ All [P] markers indicate genuinely parallelizable tasks (different files, no dependencies)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Concurrency approach: `asyncio.Lock` — simplest correct fix for low-contention single-event-loop paths
- MCP tests: Unit-only with mocked services (integration deferred to Phase 6 feature)
- Frontend drag overlays (T038-T042): Smoke + a11y only — deep DnD interaction testing deferred
- Excluded: `otel_setup.py` (infrastructure-only, marginal test value)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
