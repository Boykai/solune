---

description: "Task list for implementing meaningful backend and frontend test coverage improvements"
---

# Tasks: Increase Test Coverage with Meaningful Tests

**Input**: Design documents from `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/`  
**Prerequisites**: `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/plan.md`, `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/spec.md`, `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/research.md`, `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/data-model.md`, `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/contracts/test-coverage-surfaces.openapi.yaml`, `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/quickstart.md`

**Tests**: Tests are required by the specification and are the primary deliverable for every user story.

**Organization**: Tasks are grouped by user story so each story can be implemented and verified independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Task can run in parallel with other `[P]` tasks because it touches different files and has no unmet dependency
- **[Story]**: User story label for traceability (`[US1]`, `[US2]`, `[US3]`, `[US4]`)
- Every task below includes exact file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the baseline and gather the shared test utilities that later phases will reuse.

- [ ] T001 Run the baseline targeted commands from `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/quickstart.md` against `/home/runner/work/solune/solune/solune/backend/tests/unit` and `/home/runner/work/solune/solune/solune/frontend/src` to confirm a clean starting point
- [X] T002 Audit reusable test helpers in `/home/runner/work/solune/solune/solune/backend/tests/conftest.py`, `/home/runner/work/solune/solune/solune/frontend/src/test/setup.ts`, and `/home/runner/work/solune/solune/solune/frontend/src/test/test-utils.tsx` before adding new suites

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extend the shared fixtures and UI test harnesses needed across multiple stories.

**⚠️ CRITICAL**: Complete this phase before starting story work.

- [ ] T003 Extend shared backend fixtures and mocks in `/home/runner/work/solune/solune/solune/backend/tests/conftest.py` for chat, board, apps, settings, onboarding, templates, and backend service regression scenarios
- [ ] T004 [P] Extend shared frontend render and provider helpers in `/home/runner/work/solune/solune/solune/frontend/src/test/test-utils.tsx` for Agents and Pipeline component coverage
- [ ] T005 [P] Extend frontend test-environment setup in `/home/runner/work/solune/solune/solune/frontend/src/test/setup.ts` for async loading, error, timer, and observer behaviors used by the new component suites

**Checkpoint**: Shared backend and frontend test infrastructure is ready for story implementation.

---

## Phase 3: User Story 1 - Backend API Error Path Testing and Bug Fixes (Priority: P1) 🎯 MVP

**Goal**: Add regression tests for the highest-risk backend modules and fix the exposed chat, board, and apps bugs inline.

**Independent Test**: Run the targeted backend coverage workflow from `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/quickstart.md` for `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_chat.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_board.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_apps.py`, and `/home/runner/work/solune/solune/solune/backend/tests/unit/test_utils.py`; verify chat ≥80%, board ≥85%, apps branch ≥75%, utils ≥85%, and confirm each exposed bug is covered by a regression test.

### Tests for User Story 1

> Write these tests before the corresponding fixes in `/home/runner/work/solune/solune/solune/backend/src/api`.

- [ ] T006 [P] [US1] Expand `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_chat.py` to cover proposal expiry boundaries, `_retry_persist` transient vs permanent failures, transcript path traversal rejection, upload size and type validation, unrecognized action types, and streaming failures documented by `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/contracts/test-coverage-surfaces.openapi.yaml`
- [ ] T007 [P] [US1] Expand `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_board.py` to cover auth-vs-rate-limit classification, `_retry_after_seconds()` edge cases, stale cache fallback, manual refresh cache deletion, and deterministic hash behavior
- [ ] T008 [P] [US1] Expand `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_apps.py` to cover empty-after-strip name normalization, pipeline launch warning paths, duplicate normalized repository imports, and force-delete partial failures documented by `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/contracts/test-coverage-surfaces.openapi.yaml`
- [ ] T009 [P] [US1] Expand `/home/runner/work/solune/solune/solune/backend/tests/unit/test_utils.py` to cover `BoundedDict` eviction and move-to-end behavior, repository URL parsing edge cases, `resolve_repository()` fallback order, malformed REST URL extraction, and `cached_fetch(refresh=True)`

### Implementation for User Story 1

- [ ] T010 [US1] Fix the `expires_at is None` guard, `action_type` whitelist, and transcript-size pre-read validation in `/home/runner/work/solune/solune/solune/backend/src/api/chat.py` to satisfy `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_chat.py`
- [ ] T011 [US1] Fix rate-limit hash ordering in `/home/runner/work/solune/solune/solune/backend/src/api/board.py` to satisfy `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_board.py`
- [ ] T012 [US1] Fix empty normalized-name rejection in `/home/runner/work/solune/solune/solune/backend/src/api/apps.py` to satisfy `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_apps.py`
- [ ] T013 [US1] Run the targeted backend verification from `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/quickstart.md` for `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_chat.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_board.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_apps.py`, and `/home/runner/work/solune/solune/solune/backend/tests/unit/test_utils.py`

**Checkpoint**: User Story 1 is complete when the low-coverage backend regression targets and their inline bug fixes pass independently.

---

## Phase 4: User Story 2 - Backend Untested Endpoint Coverage (Priority: P1)

**Goal**: Establish behavioral coverage for the zero-coverage backend modules and fix the settings no-op logging bug inline.

**Independent Test**: Run the targeted backend coverage workflow from `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/quickstart.md` for `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_settings.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_onboarding.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_templates.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_pipeline_estimate.py`, and `/home/runner/work/solune/solune/solune/backend/tests/unit/test_completion_providers.py`; verify settings ≥80%, onboarding ≥90%, templates ≥90%, pipeline estimate ≥95%, and completion providers ≥75%.

### Tests for User Story 2

> Write these tests before the corresponding bug fix in `/home/runner/work/solune/solune/solune/backend/src/api/settings.py`.

- [ ] T014 [P] [US2] Create or expand `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_settings.py` to cover admin enforcement, empty-update no-op behavior, workflow sync, cache invalidation, and `/api/v1/settings/models/{provider}` missing-token handling from `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/contracts/test-coverage-surfaces.openapi.yaml`
- [ ] T015 [P] [US2] Create or expand `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_onboarding.py` to cover default state, progress persistence, completion timestamps, dismiss-vs-complete behavior, and `step > 13` validation from `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/contracts/test-coverage-surfaces.openapi.yaml`
- [X] T016 [P] [US2] Create `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_templates.py` to cover empty registry, invalid category, summary-vs-detail filtering, and 404 responses from `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/contracts/test-coverage-surfaces.openapi.yaml`
- [ ] T017 [P] [US2] Create or expand `/home/runner/work/solune/solune/solune/backend/tests/unit/test_pipeline_estimate.py` to cover hour-threshold boundaries, invalid agent-count logging, and deterministic date calculation in `/home/runner/work/solune/solune/solune/backend/src/services/pipeline_estimate.py`
- [ ] T018 [P] [US2] Create or expand `/home/runner/work/solune/solune/solune/backend/tests/unit/test_completion_providers.py` to cover concurrent pool access, cleanup on remove, timeout empty-string fallback, Azure configuration validation, and factory dispatch in `/home/runner/work/solune/solune/solune/backend/src/services/completion_providers.py`

### Implementation for User Story 2

- [ ] T019 [US2] Fix no-op activity logging in `/home/runner/work/solune/solune/solune/backend/src/api/settings.py` to satisfy `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_settings.py`
- [X] T020 [US2] Run the targeted backend verification from `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/quickstart.md` for `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_settings.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_onboarding.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_templates.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_pipeline_estimate.py`, and `/home/runner/work/solune/solune/solune/backend/tests/unit/test_completion_providers.py`

**Checkpoint**: User Story 2 is complete when the zero-coverage backend modules pass independently at their required thresholds.

---

## Phase 5: User Story 3 - Frontend Critical Component Testing (Priority: P2)

**Goal**: Add behavior-first tests for the most interactive Agents and Pipeline surfaces.

**Independent Test**: Run the frontend targeted workflow from `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/quickstart.md` for the six new component test files and verify each file passes independently while contributing toward frontend statement coverage ≥63%.

### Tests for User Story 3

- [ ] T021 [P] [US3] Create `/home/runner/work/solune/solune/solune/frontend/src/components/agents/__tests__/AgentsPanel.test.tsx` covering empty state, search filter, sort toggle, modal open-close, delete with undo, infinite scroll, and loading/error states
- [ ] T022 [P] [US3] Create `/home/runner/work/solune/solune/solune/frontend/src/components/agents/__tests__/AddAgentModal.test.tsx` covering name validation, create-vs-edit mode state, prompt length limits, character counter updates, and AI enhance toggling
- [X] T023 [P] [US3] Create `/home/runner/work/solune/solune/solune/frontend/src/components/agents/__tests__/AgentChatFlow.test.tsx` covering initial message auto-send, Enter-vs-Shift+Enter behavior, disabled input while pending, and contextual error display
- [X] T024 [P] [US3] Create `/home/runner/work/solune/solune/solune/frontend/src/components/pipeline/ExecutionGroupCard.test.tsx` covering grouped-agent rendering, execution-mode toggling, and remove-agent behavior
- [X] T025 [P] [US3] Create `/home/runner/work/solune/solune/solune/frontend/src/components/pipeline/PipelineModelDropdown.test.tsx` covering open-close state, model selection, and click-outside dismissal
- [X] T026 [P] [US3] Create `/home/runner/work/solune/solune/solune/frontend/src/components/pipeline/PipelineRunHistory.test.tsx` covering collapse-expand behavior, duration formatting, status badges, and lazy query loading

### Implementation for User Story 3

- [X] T027 [US3] Run the targeted frontend verification from `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/quickstart.md` for `/home/runner/work/solune/solune/solune/frontend/src/components/agents/__tests__/AgentsPanel.test.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/components/agents/__tests__/AddAgentModal.test.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/components/agents/__tests__/AgentChatFlow.test.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/components/pipeline/ExecutionGroupCard.test.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/components/pipeline/PipelineModelDropdown.test.tsx`, and `/home/runner/work/solune/solune/solune/frontend/src/components/pipeline/PipelineRunHistory.test.tsx`

**Checkpoint**: User Story 3 is complete when the critical component suites pass independently with meaningful behavioral coverage.

---

## Phase 6: User Story 4 - Frontend Utility and Context Testing (Priority: P3)

**Goal**: Cover the foundational frontend utility and context logic with deterministic tests.

**Independent Test**: Run the frontend targeted workflow from `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/quickstart.md` for `/home/runner/work/solune/solune/solune/frontend/src/lib/route-suggestions.test.ts`, `/home/runner/work/solune/solune/solune/frontend/src/lib/commands/registry.test.ts`, and `/home/runner/work/solune/solune/solune/frontend/src/context/SyncStatusContext.test.tsx`; verify all tests pass with full branch coverage of the targeted logic.

### Tests for User Story 4

- [X] T028 [P] [US4] Create `/home/runner/work/solune/solune/solune/frontend/src/lib/route-suggestions.test.ts` covering Levenshtein accuracy, threshold filtering, relevance ordering, and empty-input handling
- [ ] T029 [P] [US4] Create `/home/runner/work/solune/solune/solune/frontend/src/lib/commands/registry.test.ts` covering register, unregister, get, filter, and argument parsing behavior
- [X] T030 [P] [US4] Create `/home/runner/work/solune/solune/solune/frontend/src/context/SyncStatusContext.test.tsx` covering provider state management, immediate transition visibility, and equality-based deduplication

### Implementation for User Story 4

- [X] T031 [US4] Run the targeted frontend verification from `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/quickstart.md` for `/home/runner/work/solune/solune/solune/frontend/src/lib/route-suggestions.test.ts`, `/home/runner/work/solune/solune/solune/frontend/src/lib/commands/registry.test.ts`, and `/home/runner/work/solune/solune/solune/frontend/src/context/SyncStatusContext.test.tsx`

**Checkpoint**: User Story 4 is complete when the foundational utility and context tests pass independently.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Run full verification and reconcile any cross-story coverage gaps.

- [ ] T032 Run backend aggregate verification from `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/quickstart.md` against `/home/runner/work/solune/solune/solune/backend/tests/unit`, `/home/runner/work/solune/solune/solune/backend/src`, and `/home/runner/work/solune/solune/solune/backend/tests` to confirm SC-001, SC-002, SC-005, SC-006, and SC-008
- [ ] T033 [P] Run frontend aggregate verification from `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/quickstart.md` and `/home/runner/work/solune/solune/solune/frontend/package.json` against `/home/runner/work/solune/solune/solune/frontend/src` to confirm SC-003, SC-005, SC-006, SC-007, and SC-009
- [ ] T034 Reconcile any remaining threshold or behavior gaps in `/home/runner/work/solune/solune/solune/backend/src/api/chat.py`, `/home/runner/work/solune/solune/solune/backend/src/api/board.py`, `/home/runner/work/solune/solune/solune/backend/src/api/apps.py`, `/home/runner/work/solune/solune/solune/backend/src/api/settings.py`, `/home/runner/work/solune/solune/solune/backend/src/api/onboarding.py`, `/home/runner/work/solune/solune/solune/backend/src/api/templates.py`, `/home/runner/work/solune/solune/solune/backend/src/services/pipeline_estimate.py`, `/home/runner/work/solune/solune/solune/backend/src/services/completion_providers.py`, `/home/runner/work/solune/solune/solune/backend/src/utils.py`, and their matching test files before final merge

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 → Phase 2**: Complete baseline verification and helper audit before changing shared fixtures
- **Phase 2 → Phase 3**: Backend and frontend shared harness updates in `/home/runner/work/solune/solune/solune/backend/tests/conftest.py`, `/home/runner/work/solune/solune/solune/frontend/src/test/test-utils.tsx`, and `/home/runner/work/solune/solune/solune/frontend/src/test/setup.ts` block story work
- **Phase 3 → Phase 4**: User Story 2 starts after User Story 1 targeted backend smoke is green, matching `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/plan.md`
- **Phase 4 → Phase 5**: Start frontend critical component work after backend P1 targets are stable
- **Phase 5 ↔ Phase 6**: User Story 4 may begin after Phase 2 and can overlap late User Story 3 stabilization, but this plan keeps it sequenced after User Story 3 for simpler delivery
- **Phase 7**: Final verification depends on all selected user stories being complete

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2; no dependency on later stories
- **US2 (P1)**: Starts after US1 targeted backend smoke passes because it reuses the backend fixture patterns proven in US1
- **US3 (P2)**: Starts after US1 and US2 backend work is stable
- **US4 (P3)**: Starts after Phase 2 and is independently testable from backend changes

### Within Each User Story

- Test-file tasks must be completed before inline bug-fix tasks in the corresponding source files
- Targeted verification task is the completion gate for each story
- No story is considered done until its independent test criteria pass

## Parallel Opportunities

- **Foundational**: T004 and T005 can run together after T003 starts the shared-harness work
- **US1**: T006, T007, T008, and T009 can run in parallel because they touch four separate backend test files
- **US2**: T014, T015, T016, T017, and T018 can run in parallel because they touch separate backend test files
- **US3**: T021 through T026 can run in parallel because each task creates a different frontend test file
- **US4**: T028, T029, and T030 can run in parallel because each task targets a different utility/context file
- **Polish**: T032 and T033 can run in parallel after all stories are complete

## Parallel Example: User Story 1

```text
Run together: T006, T007, T008, T009
Then run: T010, T011, T012
Then run: T013
```

## Parallel Example: User Story 2

```text
Run together: T014, T015, T016, T017, T018
Then run: T019
Then run: T020
```

## Parallel Example: User Story 3

```text
Run together: T021, T022, T023, T024, T025, T026
Then run: T027
```

## Parallel Example: User Story 4

```text
Run together: T028, T029, T030
Then run: T031
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2
2. Complete User Story 1
3. Run T013 and confirm the backend high-risk regression targets and inline fixes pass independently
4. Stop and validate before expanding scope

### Incremental Delivery

1. Finish Setup + Foundational shared harness work
2. Deliver US1 for backend low-coverage regression targets and inline bug fixes
3. Deliver US2 for backend zero-coverage modules
4. Deliver US3 for frontend critical component tests
5. Deliver US4 for frontend utility/context tests
6. Finish with Phase 7 aggregate verification

### Suggested MVP Scope

- **MVP**: Phase 1, Phase 2, and User Story 1 only
- **Next increment**: User Story 2 to finish backend coverage goals
- **Final increments**: User Story 3, User Story 4, then Phase 7 verification

## Notes

- All tasks use the required checklist format
- Story labels appear only in user-story phases
- File paths are absolute to match the feature documents
- The feature stays within unit and behavioral testing only; no e2e, integration, property, or fuzz tests are included
