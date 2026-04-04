# Tasks: Update Testing Coverage

**Input**: Design documents from `/specs/002-update-testing-coverage/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests ARE the deliverable for this feature. All tasks involve writing, improving, or removing tests.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `solune/backend/src/`, `solune/backend/tests/`
- **Frontend**: `solune/frontend/src/`, `solune/frontend/e2e/`
- **Config**: `solune/backend/pyproject.toml`, `solune/frontend/vitest.config.ts`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish baseline coverage metrics and prepare test infrastructure

- [ ] T001 Run backend coverage baseline and save report with `cd solune/backend && uv run pytest --cov=src --cov-report=json --cov-report=term-missing --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency`
- [ ] T002 Run frontend coverage baseline with `cd solune/frontend && npm run test:coverage` and record current thresholds
- [ ] T003 [P] Audit existing backend test fixtures in solune/backend/tests/conftest.py for reusability and identify shared helpers needed for new tests
- [ ] T004 [P] Audit existing frontend test utilities in solune/frontend/src/test/ for reusability and identify shared helpers needed for new tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Ensure shared test helpers and fixtures are ready before writing per-file tests

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Review and update shared async fixtures in solune/backend/tests/conftest.py to ensure AsyncClient, mock database session, and mock service factories are available for new test files
- [ ] T006 [P] Review and update shared frontend test wrapper providers in solune/frontend/src/test/ to ensure QueryClient, Router, and Theme wrappers are available for new hook and component tests
- [ ] T007 [P] Verify backend test configuration in solune/backend/pyproject.toml — confirm branch=true, asyncio_mode=auto, and coverage source paths are correct
- [ ] T008 [P] Verify frontend test configuration in solune/frontend/vitest.config.ts — confirm v8 coverage provider and current threshold values match expected baseline (50/44/41/50)

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 — Increase Backend Unit and Branch Coverage (Priority: P1) 🎯 MVP

**Goal**: Raise backend line coverage from 79% to ≥85% and branch coverage from 70% to ≥78% by targeting the top 15 files by missing lines

**Independent Test**: Run `cd solune/backend && uv run pytest --cov=src --cov-report=term-missing --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency` and verify overall line coverage ≥85%, branch coverage ≥78%

### Tier 1 — Top 5 Files (Highest Impact, ~1261 missing lines)

- [ ] T009 [P] [US1] Add unit tests for pipeline state transitions, error recovery paths, and async processing edge cases in solune/backend/tests/unit/test_copilot_polling_pipeline.py targeting solune/backend/src/services/copilot_polling/pipeline.py (65.7% → 82%, 310 missing lines)
- [ ] T010 [P] [US1] Add unit tests for agent CRUD operations, validation failures, and agent configuration edge cases in solune/backend/tests/unit/test_agents_service.py targeting solune/backend/src/services/agents/service.py (47.4% → 72%, 281 missing lines)
- [ ] T011 [P] [US1] Add API route tests using AsyncClient for error responses, SSE streaming edge cases, and message handling in solune/backend/tests/unit/test_api_chat.py targeting solune/backend/src/api/chat.py (59.6% → 78%, 275 missing lines)
- [ ] T012 [P] [US1] Add unit tests for creation workflows, template processing, and validation rules in solune/backend/tests/unit/test_agent_creator.py targeting solune/backend/src/services/agent_creator.py (39.4% → 65%, 240 missing lines)
- [ ] T013 [P] [US1] Add route tests for project CRUD, authorization checks, and pagination in solune/backend/tests/unit/test_api_projects.py targeting solune/backend/src/api/projects.py (37.7% → 65%, 155 missing lines)

### Tier 2 — Next 5 Files (Important, ~685 missing lines)

- [ ] T014 [P] [US1] Add unit tests for chore scheduling, execution, and error handling in solune/backend/tests/unit/test_chores_service.py targeting solune/backend/src/services/chores/service.py (51.3% → 72%, 154 missing lines)
- [ ] T015 [P] [US1] Add unit tests for recovery strategies, retry logic, and failure modes in solune/backend/tests/unit/test_copilot_polling_recovery.py targeting solune/backend/src/services/copilot_polling/recovery.py (64.3% → 80%, 138 missing lines)
- [ ] T016 [P] [US1] Add unit tests for complex orchestration flows and state transitions in solune/backend/tests/unit/test_workflow_orchestrator.py targeting solune/backend/src/services/workflow_orchestrator/orchestrator.py (79.8% → 88%, 136 missing lines)
- [ ] T017 [P] [US1] Add unit tests for app lifecycle, installation, and update logic in solune/backend/tests/unit/test_app_service.py targeting solune/backend/src/services/app_service.py (61.6% → 78%, 130 missing lines)
- [ ] T018 [P] [US1] Add unit tests for bridge communication and webhook dispatch in solune/backend/tests/unit/test_signal_bridge.py targeting solune/backend/src/services/signal_bridge.py (60.9% → 78%, 127 missing lines)

### Tier 3 — Final 5 Files + Branch Coverage (Secondary, ~446 missing lines)

- [ ] T019 [P] [US1] Add route tests for pipeline CRUD and query operations in solune/backend/tests/unit/test_api_pipelines.py targeting solune/backend/src/api/pipelines.py (62.2% → 78%, 101 missing lines)
- [ ] T020 [P] [US1] Add unit tests for board operations, column management, and card movement in solune/backend/tests/unit/test_github_projects_board.py targeting solune/backend/src/services/github_projects/board.py (63.0% → 78%, 91 missing lines)
- [ ] T021 [P] [US1] Add unit tests for application startup, shutdown, middleware registration, and CORS configuration in solune/backend/tests/unit/test_main.py targeting solune/backend/src/main.py (68.2% → 80%, 89 missing lines)
- [ ] T022 [P] [US1] Add route tests for board endpoints, authorization, and error handling in solune/backend/tests/unit/test_api_board.py targeting solune/backend/src/api/board.py (64.5% → 78%, 85 missing lines)
- [ ] T023 [P] [US1] Add unit tests for agent output parsing, formatting, and error handling in solune/backend/tests/unit/test_copilot_polling_agent_output.py targeting solune/backend/src/services/copilot_polling/agent_output.py (73.0% → 83%, 80 missing lines)

### Branch Coverage Hardening

- [ ] T024 [US1] Review branch coverage report for all 15 targeted files and add parametrized tests for untested conditional branches, focusing on error paths and None/empty checks across solune/backend/tests/unit/
- [ ] T025 [US1] Raise backend coverage fail_under threshold from 75 to 80 in solune/backend/pyproject.toml (only after T009-T024 verify ≥85% line and ≥78% branch coverage)

**Checkpoint**: Backend coverage meets ≥85% line / ≥78% branch targets. Each new test file validates independently.

---

## Phase 4: User Story 2 — Increase Frontend Unit and Component Coverage (Priority: P1)

**Goal**: Raise frontend vitest coverage thresholds from 50/44/41/50 to 60/55/52/60 by targeting hooks, services, and components with lowest coverage

**Independent Test**: Run `cd solune/frontend && npm run test:coverage` and verify new thresholds pass (60/55/52/60)

### Hooks Coverage (Highest Impact — 60+ hooks)

- [ ] T026 [P] [US2] Identify the 10 hooks with lowest coverage by running vitest with per-file reporting and create a prioritized list in solune/frontend/src/hooks/
- [ ] T027 [P] [US2] Add renderHook tests for state transitions, error cases, and edge cases for the 5 lowest-coverage hooks in solune/frontend/src/hooks/ (create or update corresponding .test.ts files)
- [ ] T028 [P] [US2] Add renderHook tests for state transitions, error cases, and edge cases for hooks 6-10 in solune/frontend/src/hooks/ (create or update corresponding .test.ts files)

### Service Layer Coverage

- [ ] T029 [P] [US2] Add tests for API client functions, request/response handling, and error cases in solune/frontend/src/services/ (create or update corresponding .test.ts files)
- [ ] T030 [P] [US2] Add tests for schema validation edge cases, type guards, and transformation functions in solune/frontend/src/services/ (create or update corresponding .test.ts files)

### Component Coverage (Complex Components)

- [ ] T031 [P] [US2] Add user-centric Testing Library tests for chat component rendering, message display, streaming states, and user interaction in solune/frontend/src/components/chat/ test files
- [ ] T032 [P] [US2] Add user-centric Testing Library tests for pipeline component rendering, state management, and drag-drop interaction in solune/frontend/src/components/pipeline/ test files
- [ ] T033 [P] [US2] Add user-centric Testing Library tests for board component rendering, column/card display, and real-time sync behavior in solune/frontend/src/components/board/ test files

### Threshold Enforcement

- [ ] T034 [US2] Raise frontend coverage thresholds from 50/44/41/50 to 60/55/52/60 in solune/frontend/vitest.config.ts (only after T026-T033 verify coverage meets new thresholds)

**Checkpoint**: Frontend coverage meets new thresholds (60/55/52/60). All vitest tests pass.

---

## Phase 5: User Story 3 — Meaningful E2E Tests for Core UX Flows (Priority: P2)

**Goal**: Audit all existing Playwright specs and ensure core UX flows (auth, chat, board, pipeline, agent creation, settings) are thoroughly validated end-to-end

**Independent Test**: Run `cd solune/frontend && npm run test:e2e` and verify all spec files pass in both chromium and firefox projects

### E2E Audit

- [ ] T035 [US3] Audit all existing Playwright spec files in solune/frontend/e2e/ — catalog each spec, classify as current/stale/broken, and identify missing core flow coverage
- [ ] T036 [US3] Remove or update stale and broken e2e spec files identified in T035 from solune/frontend/e2e/

### Core Flow E2E Tests

- [ ] T037 [P] [US3] Ensure authentication e2e test covers the complete login/logout flow with session persistence using storageState in solune/frontend/e2e/
- [ ] T038 [P] [US3] Ensure chat interaction e2e test covers message sending, streaming response display, and error recovery in solune/frontend/e2e/
- [ ] T039 [P] [US3] Ensure board navigation e2e test covers board loading, column display, card interaction, and real-time updates in solune/frontend/e2e/
- [ ] T040 [P] [US3] Ensure pipeline monitoring e2e test covers pipeline list view, status display, and detail navigation in solune/frontend/e2e/
- [ ] T041 [P] [US3] Ensure agent creation e2e test covers the full agent creation wizard, configuration options, and validation in solune/frontend/e2e/
- [ ] T042 [P] [US3] Ensure settings management e2e test covers settings navigation, configuration changes, and save/cancel behavior in solune/frontend/e2e/

### E2E Quality Improvements

- [ ] T043 [P] [US3] Add accessibility assertions using @axe-core/playwright to at least 3 core e2e flows (auth, board, chat) in solune/frontend/e2e/
- [ ] T044 [US3] Verify all e2e tests pass in both chromium and firefox projects using the Playwright configuration in solune/frontend/playwright.config.ts

**Checkpoint**: All e2e specs pass across both browser projects. Core UX flows are validated end-to-end.

---

## Phase 6: User Story 4 — Remove Stale, Outdated, and Low-Quality Tests (Priority: P2)

**Goal**: Identify and remove at least 10 stale or low-quality tests from both backend and frontend without regressing overall coverage by more than 2%

**Independent Test**: Run full test suites before and after removal; verify CI passes and coverage delta is ≤2% regression

### Backend Test Audit

- [ ] T045 [P] [US4] Scan solune/backend/tests/ for tests with no assertions (no assert, expect, or pytest.raises calls) and catalog candidates for removal
- [ ] T046 [P] [US4] Scan solune/backend/tests/ for tests importing non-existent modules or testing removed features and catalog candidates for removal
- [ ] T047 [P] [US4] Scan solune/backend/tests/ for over-mocked tests where every dependency is mocked and the test only verifies mock wiring, not behavior
- [ ] T048 [US4] Remove or consolidate identified stale backend tests from solune/backend/tests/ with documented reasons in commit messages

### Frontend Test Audit

- [ ] T049 [P] [US4] Scan solune/frontend/src/ test files for tests with no assertions, empty test bodies, or snapshot-only tests without behavioral assertions
- [ ] T050 [P] [US4] Scan solune/frontend/src/ test files for tests covering removed features or deprecated component APIs
- [ ] T051 [US4] Remove or consolidate identified stale frontend tests from solune/frontend/src/ with documented reasons in commit messages

### Duplicate Test Consolidation

- [ ] T052 [US4] Identify and consolidate duplicate tests that exercise the exact same code paths across solune/backend/tests/ and solune/frontend/src/ test files
- [ ] T053 [US4] Verify that test removal does not regress overall coverage by more than 2% by running coverage before and after removals

**Checkpoint**: At least 10 stale tests removed. CI passes. Coverage regression ≤2%.

---

## Phase 7: User Story 5 — Discover and Fix Bugs During Coverage Increase (Priority: P3)

**Goal**: Document and fix bugs discovered while writing new tests throughout Phases 3-6, with each fix accompanied by the test that exposed it

**Independent Test**: Each bug fix verified by writing a test that initially fails, applying the fix, and confirming the test passes plus all other tests continue to pass

- [ ] T054 [US5] During Phases 3-6, when a new test reveals unexpected behavior in a backend module under solune/backend/src/, document the bug, write a failing test, apply the fix, and verify the test passes
- [ ] T055 [US5] During Phases 3-6, when a new test reveals unexpected behavior in a frontend module under solune/frontend/src/, document the bug, write a failing test, apply the fix, and verify the test passes
- [ ] T056 [US5] For any discovered bug that requires changes outside the scope of testing (architectural changes, external API changes), create a TODO comment in the test file with a description and skip the test with `@pytest.mark.skip(reason="...")` or `it.skip(...)` pending a separate issue
- [ ] T057 [US5] Review all bug fixes applied during Phases 3-6 and ensure each fix commit message follows the format: `fix: {description} (discovered during coverage improvement)` with the affected module documented

**Checkpoint**: All discovered bugs are either fixed (with accompanying tests) or documented as TODO/skip for separate resolution.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, threshold enforcement, and documentation

- [ ] T058 [P] Run full backend test suite with coverage enforcement at the new threshold: `cd solune/backend && uv run pytest --cov=src --cov-fail-under=80 --cov-report=term-missing --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency`
- [ ] T059 [P] Run full frontend test suite with new thresholds: `cd solune/frontend && npm run test:coverage`
- [ ] T060 [P] Run full e2e test suite: `cd solune/frontend && npm run test:e2e`
- [ ] T061 Run backend linting and type checking: `cd solune/backend && uv run ruff check src tests && uv run pyright src`
- [ ] T062 Run frontend linting and type checking: `cd solune/frontend && npm run lint && npx tsc --noEmit -p tsconfig.test.json`
- [ ] T063 Verify total test suite execution time remains ≤10 minutes on CI by checking `--durations=20` output from backend test run
- [ ] T064 Generate final coverage reports (JSON + HTML) for both backend and frontend and compare against baseline from T001-T002
- [ ] T065 Run quickstart.md validation — execute all commands from specs/002-update-testing-coverage/quickstart.md and verify each succeeds

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 Backend Coverage (Phase 3)**: Depends on Phase 2 — highest priority
- **US2 Frontend Coverage (Phase 4)**: Depends on Phase 2 — can run in parallel with Phase 3
- **US3 E2E Tests (Phase 5)**: Depends on Phase 2 — can run in parallel with Phases 3-4
- **US4 Stale Test Removal (Phase 6)**: Depends on Phases 3-5 (need coverage data to identify truly stale tests)
- **US5 Bug Discovery (Phase 7)**: Runs concurrently with Phases 3-6 (bugs found during those phases)
- **Polish (Phase 8)**: Depends on all prior phases (final validation)

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 2 — no dependencies on other stories
- **User Story 2 (P1)**: Can start after Phase 2 — independent of US1
- **User Story 3 (P2)**: Can start after Phase 2 — independent of US1/US2
- **User Story 4 (P2)**: Depends on US1-US3 completion (needs coverage data before removal decisions)
- **User Story 5 (P3)**: Runs throughout US1-US4 (bugs discovered inline)

### Within Each User Story

- Analyze coverage gaps before writing tests
- Write tests targeting uncovered lines and branches
- Verify file-level coverage improvement after each test file
- Only raise thresholds after sufficient tests are in place
- Complete all tasks in a story before declaring checkpoint met

### Parallel Opportunities

- **Phase 2**: T005-T008 can all run in parallel (different config files)
- **Phase 3 Tier 1**: T009-T013 can all run in parallel (different source files)
- **Phase 3 Tier 2**: T014-T018 can all run in parallel (different source files)
- **Phase 3 Tier 3**: T019-T023 can all run in parallel (different source files)
- **Phase 4**: T026-T033 can mostly run in parallel (different frontend modules)
- **Phase 5**: T037-T043 can run in parallel (different e2e spec files)
- **Phase 6**: T045-T047 and T049-T050 can run in parallel (audit tasks)
- **Phases 3-5**: Can run in parallel across team members (backend/frontend/e2e)

---

## Parallel Example: User Story 1 Tier 1

```bash
# Launch all 5 Tier 1 backend test files in parallel (different source targets):
Task T009: "Add tests for pipeline.py in tests/unit/test_copilot_polling_pipeline.py"
Task T010: "Add tests for agents/service.py in tests/unit/test_agents_service.py"
Task T011: "Add tests for api/chat.py in tests/unit/test_api_chat.py"
Task T012: "Add tests for agent_creator.py in tests/unit/test_agent_creator.py"
Task T013: "Add tests for api/projects.py in tests/unit/test_api_projects.py"
```

## Parallel Example: User Story 2 Components

```bash
# Launch all 3 complex component test tasks in parallel (different component dirs):
Task T031: "Add tests for chat components in src/components/chat/"
Task T032: "Add tests for pipeline components in src/components/pipeline/"
Task T033: "Add tests for board components in src/components/board/"
```

## Parallel Example: Cross-Story Parallelism

```bash
# After Phase 2 completes, launch all 3 independent user stories in parallel:
Developer A: Phase 3 (US1 — Backend Coverage)
Developer B: Phase 4 (US2 — Frontend Coverage)
Developer C: Phase 5 (US3 — E2E Tests)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (baseline coverage metrics)
2. Complete Phase 2: Foundational (test infrastructure verification)
3. Complete Phase 3: User Story 1 — Backend Coverage (Tier 1 first, then Tier 2, then Tier 3)
4. **STOP and VALIDATE**: Run `uv run pytest --cov=src --cov-fail-under=80` — verify backend meets new threshold
5. Raise `fail_under` to 80 in pyproject.toml
6. Deploy/demo if ready — backend coverage improvement is independently valuable

### Incremental Delivery

1. Complete Setup + Foundational → Infrastructure verified
2. Add US1 (Backend Coverage) → Test independently → **MVP delivered** (backend ≥85% line, ≥78% branch)
3. Add US2 (Frontend Coverage) → Test independently → Frontend thresholds raised to 60/55/52/60
4. Add US3 (E2E Tests) → Test independently → All core flows have passing e2e specs
5. Add US4 (Stale Removal) → Test independently → ≥10 stale tests removed
6. Add US5 (Bug Fixes) → Test independently → All discovered bugs documented and resolved
7. Complete Polish → Full validation → CI passes with all new thresholds
8. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Backend Coverage — Tiers 1-3)
   - Developer B: User Story 2 (Frontend Coverage — Hooks, Services, Components)
   - Developer C: User Story 3 (E2E Tests — Audit and Core Flows)
3. After US1-US3 complete:
   - Any developer: User Story 4 (Stale Test Removal)
   - Any developer: User Story 5 (Bug Fix Documentation)
4. Final phase: Everyone runs Polish validation

---

## Notes

- [P] tasks = different files, no dependencies — safe to run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Coverage thresholds are only raised AFTER tests are in place (FR-011)
- All new tests follow existing project conventions (FR-009, FR-010)
- Bug fixes committed alongside their exposing test (FR-008)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Target files and coverage percentages sourced from research.md and data-model.md
- Per-area backend coverage targets sourced from contracts/coverage-targets.yaml
- Test quality standards sourced from contracts/testing-standards.yaml
