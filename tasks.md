# Tasks: Increase Test Coverage with Meaningful Tests Using Modern Best Practices

**Input**: Design documents from `/specs/001-increase-test-coverage/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Tests ARE the primary deliverable for this feature. All tasks generate test files or fix the bounded-locks bug.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/src/`, `solune/backend/tests/`, `solune/frontend/src/`
- Backend tests: `solune/backend/tests/unit/test_<module>.py`
- Frontend tests: colocated `<Component>.test.tsx` or `__tests__/<Component>.test.tsx`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify existing test infrastructure is ready; no new tooling needed

- [ ] T001 Verify backend test suite passes with `cd solune/backend && python -m pytest tests/ --cov=src --cov-fail-under=75 -q`
- [ ] T002 Verify frontend test suite passes with `cd solune/frontend && npm run test`
- [ ] T003 [P] Verify backend linting passes with `cd solune/backend && ruff check src/ tests/ && ruff format --check src/ tests/`
- [ ] T004 [P] Verify frontend linting and type-check passes with `cd solune/frontend && npm run lint && npm run type-check`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational infrastructure changes are needed. The existing test infrastructure (pytest-asyncio auto mode, Vitest + happy-dom, jest-axe, @fast-check/vitest) is already modern and correct. Phase 2 is a no-op checkpoint.

**⚠️ CRITICAL**: Confirm all Phase 1 verification tasks pass before proceeding to user stories.

**Checkpoint**: Foundation verified — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 — Close Critical Frontend Test Gaps (Priority: P1) 🎯 MVP

**Goal**: Add meaningful tests for all untested frontend chores components, tools components, agents components, settings components, UI primitives, and remaining pipeline/chat gaps. Every new test must exercise rendering, user interaction, and core behavior — not just import verification.

**Independent Test**: Run `cd solune/frontend && npx vitest run --coverage` and verify chores, tools, agents, settings, and UI directories show meaningful coverage improvements. All new tests must pass.

### Implementation for User Story 1

#### Chores Components (6 untested)

- [ ] T005 [P] [US1] Create test for ChoreChatFlow in `solune/frontend/src/components/chores/__tests__/ChoreChatFlow.test.tsx` — render with mock props, verify chat flow UI renders, test user message submission
- [ ] T006 [P] [US1] Create test for ChoreInlineEditor in `solune/frontend/src/components/chores/__tests__/ChoreInlineEditor.test.tsx` — render in edit mode, verify input fields, test save/cancel interactions
- [ ] T007 [P] [US1] Create test for ChoresSaveAllBar in `solune/frontend/src/components/chores/__tests__/ChoresSaveAllBar.test.tsx` — render with pending changes, verify save-all button, test click handler
- [ ] T008 [P] [US1] Create test for ChoresSpotlight in `solune/frontend/src/components/chores/__tests__/ChoresSpotlight.test.tsx` — render spotlight view, verify featured chore display, test navigation
- [ ] T009 [P] [US1] Create test for ChoresToolbar in `solune/frontend/src/components/chores/__tests__/ChoresToolbar.test.tsx` — render toolbar, verify filter/sort controls, test toolbar actions
- [ ] T010 [P] [US1] Create test for PipelineSelector in `solune/frontend/src/components/chores/__tests__/PipelineSelector.test.tsx` — render with pipeline options, verify selection behavior, test change handler

#### Tools Components (8 untested)

- [ ] T011 [P] [US1] Create test for ToolCard in `solune/frontend/src/components/tools/__tests__/ToolCard.test.tsx` — render with tool data, verify name/description display, test click interaction
- [ ] T012 [P] [US1] Create test for ToolsPanel in `solune/frontend/src/components/tools/__tests__/ToolsPanel.test.tsx` — render panel with mock tools list, verify tool cards render, test add/remove flow
- [ ] T013 [P] [US1] Create test for ToolChips in `solune/frontend/src/components/tools/__tests__/ToolChips.test.tsx` — render chips with tool names, verify chip display, test removal interaction
- [ ] T014 [P] [US1] Create test for McpPresetsGallery in `solune/frontend/src/components/tools/__tests__/McpPresetsGallery.test.tsx` — render gallery with presets, verify preset cards, test selection
- [ ] T015 [P] [US1] Create test for RepoConfigPanel in `solune/frontend/src/components/tools/__tests__/RepoConfigPanel.test.tsx` — render config panel, verify form fields, test configuration changes
- [ ] T016 [P] [US1] Create test for EditRepoMcpModal in `solune/frontend/src/components/tools/__tests__/EditRepoMcpModal.test.tsx` — render modal open state, verify form inputs, test save/cancel
- [ ] T017 [P] [US1] Create test for UploadMcpModal in `solune/frontend/src/components/tools/__tests__/UploadMcpModal.test.tsx` — render upload modal, verify file input area, test upload flow
- [ ] T018 [P] [US1] Create test for GitHubMcpConfigGenerator in `solune/frontend/src/components/tools/__tests__/GitHubMcpConfigGenerator.test.tsx` — render config generator, verify output preview, test generate action

#### Agents Components (5 untested)

- [ ] T019 [P] [US1] Create test for AgentCard in `solune/frontend/src/components/agents/__tests__/AgentCard.test.tsx` — render with agent data, verify name/avatar/status display, test click handler
- [ ] T020 [P] [US1] Create test for AgentInlineEditor in `solune/frontend/src/components/agents/__tests__/AgentInlineEditor.test.tsx` — render in edit mode, verify form fields, test save/cancel
- [ ] T021 [P] [US1] Create test for AgentIconCatalog in `solune/frontend/src/components/agents/__tests__/AgentIconCatalog.test.tsx` — render icon catalog, verify icon grid display, test icon selection
- [ ] T022 [P] [US1] Create test for AgentIconPickerModal in `solune/frontend/src/components/agents/__tests__/AgentIconPickerModal.test.tsx` — render picker modal, verify search/filter, test icon pick
- [ ] T023 [P] [US1] Create test for BulkModelUpdateDialog in `solune/frontend/src/components/agents/__tests__/BulkModelUpdateDialog.test.tsx` — render dialog with agents, verify model selection, test confirm/cancel

#### Settings Components (4 untested)

- [ ] T024 [P] [US1] Create test for ProjectSettings in `solune/frontend/src/components/settings/__tests__/ProjectSettings.test.tsx` — render settings form, verify input fields, test save interaction
- [ ] T025 [P] [US1] Create test for AIPreferences in `solune/frontend/src/components/settings/__tests__/AIPreferences.test.tsx` — render preferences panel, verify toggle/select controls, test preference changes
- [ ] T026 [P] [US1] Create test for PrimarySettings in `solune/frontend/src/components/settings/__tests__/PrimarySettings.test.tsx` — render primary settings, verify key settings display, test edit flow
- [ ] T027 [P] [US1] Create test for SignalConnection in `solune/frontend/src/components/settings/__tests__/SignalConnection.test.tsx` — render connection status, verify indicator display, test reconnect action

#### UI Primitives (6 untested — non-trivial ones only)

- [ ] T028 [P] [US1] Create test for copy-button in `solune/frontend/src/components/ui/__tests__/copy-button.test.tsx` — render with content, verify clipboard copy on click, test copied-state feedback
- [ ] T029 [P] [US1] Create test for character-counter in `solune/frontend/src/components/ui/__tests__/character-counter.test.tsx` — render with limits, verify count display, test near-limit and over-limit styling
- [ ] T030 [P] [US1] Create test for keyboard-shortcut-modal in `solune/frontend/src/components/ui/__tests__/keyboard-shortcut-modal.test.tsx` — render modal, verify shortcut list display, test close interaction

#### Remaining Component Gaps (Pipeline, Chat — lower priority within P1)

- [ ] T031 [P] [US1] Create test for ModelSelector in `solune/frontend/src/components/pipeline/__tests__/ModelSelector.test.tsx` — render with model options, verify dropdown, test selection change
- [ ] T032 [P] [US1] Create test for PipelineStagesOverview in `solune/frontend/src/components/pipeline/__tests__/PipelineStagesOverview.test.tsx` — render with stages data, verify stage cards, test stage navigation
- [ ] T033 [P] [US1] Create test for ParallelStageGroup in `solune/frontend/src/components/pipeline/__tests__/ParallelStageGroup.test.tsx` — render with parallel stages, verify group layout, test expand/collapse
- [ ] T034 [P] [US1] Create test for MentionAutocomplete in `solune/frontend/src/components/chat/__tests__/MentionAutocomplete.test.tsx` — render with suggestions, verify dropdown display, test selection
- [ ] T035 [P] [US1] Create test for PlanDependencyGraph in `solune/frontend/src/components/chat/__tests__/PlanDependencyGraph.test.tsx` — render with graph data, verify node rendering, test node interaction
- [ ] T036 [P] [US1] Create test for PipelineIndicator in `solune/frontend/src/components/chat/__tests__/PipelineIndicator.test.tsx` — render with status, verify indicator display, test status changes
- [ ] T037 [P] [US1] Create test for ChatMessageSkeleton in `solune/frontend/src/components/chat/__tests__/ChatMessageSkeleton.test.tsx` — render skeleton, verify placeholder structure

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Run `cd solune/frontend && npx vitest run` to confirm all new + existing tests pass.

---

## Phase 4: User Story 2 — Close Backend Test Gaps (Priority: P2)

**Goal**: Add meaningful tests for untested backend prompt modules and the `otel_setup.py` service. Each test must verify actual behavior — output structure, variable substitution, edge cases.

**Independent Test**: Run `cd solune/backend && python -m pytest tests/ --cov=src --cov-fail-under=75 -q` and verify newly tested modules appear in the coverage report.

### Implementation for User Story 2

#### Prompt Module Tests (3 untested)

- [ ] T038 [P] [US2] Create test for agent_instructions prompt in `solune/backend/tests/unit/test_agent_instructions_prompt.py` — verify output structure contains required sections, test variable substitution with real project data, test edge cases (empty inputs, special characters, long inputs)
- [ ] T039 [P] [US2] Create test for issue_generation prompt in `solune/backend/tests/unit/test_issue_generation_prompt.py` — verify output structure contains required issue fields, test variable substitution, test edge cases (empty title, missing context, special characters)
- [ ] T040 [P] [US2] Create test for task_generation prompt in `solune/backend/tests/unit/test_task_generation_prompt.py` — verify output structure contains task list format, test variable substitution, test edge cases (empty plan, no user stories)

#### Observability Service Test (1 untested)

- [ ] T041 [P] [US2] Create test for otel_setup service in `solune/backend/tests/unit/test_otel_setup.py` — verify setup initialization creates expected providers, test no-op fallback behavior when OTel is disabled, test cleanup/shutdown sequence

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Run backend tests to confirm.

---

## Phase 5: User Story 3 — Fix Discovered Bugs (Priority: P2)

**Goal**: Fix the unbounded `_project_launch_locks` dictionary in `pipeline_state_store.py` by replacing it with a bounded data structure (using the existing `BoundedDict` from `solune/backend/src/utils.py`). Add regression test to prevent recurrence.

**Independent Test**: Write a unit test that creates locks for more entries than the maximum capacity and verifies the dictionary does not grow beyond its bound.

### Implementation for User Story 3

- [ ] T042 [US3] Fix unbounded `_project_launch_locks` in `solune/backend/src/services/pipeline_state_store.py` — replace `dict[str, asyncio.Lock]` with `BoundedDict[str, asyncio.Lock]` using a sensible max size, import `BoundedDict` from `src.utils`
- [ ] T043 [US3] Add bounded-locks regression test in `solune/backend/tests/unit/test_pipeline_state_store.py` — verify lock count stays bounded after accessing more than max unique project IDs, verify existing locks work correctly, verify eviction of oldest entries
- [ ] T044 [US3] Update conftest cleanup if needed in `solune/backend/tests/conftest.py` — verify existing `_project_launch_locks.clear()` cleanup still works with `BoundedDict`, adjust if the clear API differs

**Checkpoint**: All existing `pipeline_state_store` tests still pass, plus the new bounded-locks regression test passes. Run `cd solune/backend && python -m pytest tests/unit/test_pipeline_state_store.py -v`.

---

## Phase 6: User Story 4 — Raise Coverage Thresholds (Priority: P3)

**Goal**: After all new tests are in place, raise CI coverage thresholds to prevent future regressions. The new thresholds codify the coverage gains from US1–US3.

**Independent Test**: Temporarily lower a coverage value below the new threshold and verify that the CI job fails with a clear error message.

### Implementation for User Story 4

- [ ] T045 [US4] Measure new frontend coverage baseline by running `cd solune/frontend && npx vitest run --coverage` and recording statements/branches/functions/lines percentages
- [ ] T046 [US4] Raise frontend coverage thresholds in `solune/frontend/vitest.config.ts` — update `coverage.thresholds` to new baseline (target: ≥65% lines, ≥55% branches, ≥55% functions, ≥65% statements), set values 2–3% below measured to allow normal fluctuation
- [ ] T047 [US4] Measure new backend coverage baseline by running `cd solune/backend && python -m pytest tests/ --cov=src -q` and recording overall percentage
- [ ] T048 [US4] Raise backend coverage threshold if warranted in `solune/backend/pyproject.toml` — if overall coverage now exceeds 80%, raise `fail_under` from 75 to match new baseline minus 2–3%

**Checkpoint**: Both test suites pass with the raised thresholds. Verify by running full suites with coverage enforcement.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all user stories

- [ ] T049 Run full backend validation: `cd solune/backend && ruff check src/ tests/ && ruff format --check src/ tests/ && pyright src/ && python -m pytest tests/ --cov=src --cov-fail-under=75 -q`
- [ ] T050 Run full frontend validation: `cd solune/frontend && npm run lint && npm run type-check && npm run test && npm run build`
- [ ] T051 Verify zero pre-existing test failures introduced — compare test counts before and after
- [ ] T052 Verify all new test files follow repository naming conventions (`test_<module>.py` for backend, `<Component>.test.tsx` or `__tests__/<Component>.test.tsx` for frontend)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup passing — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 verification — frontend tests only
- **User Story 2 (Phase 4)**: Depends on Phase 2 verification — backend tests only
- **User Story 3 (Phase 5)**: Depends on Phase 2 verification — backend bug fix
- **User Story 4 (Phase 6)**: Depends on Phases 3, 4, and 5 completion (needs all new tests in place before raising thresholds)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 2 — independent of backend work
- **User Story 2 (P2)**: Can start after Phase 2 — independent of frontend work. Can run in parallel with US1
- **User Story 3 (P2)**: Can start after Phase 2 — independent of US1/US2. Can run in parallel with US1 and US2
- **User Story 4 (P3)**: MUST wait for US1, US2, and US3 to complete — thresholds depend on actual coverage gains

### Within Each User Story

- All tasks marked [P] within a story can run in parallel (different files, no dependencies)
- US3 tasks are sequential: fix (T042) → test (T043) → cleanup (T044)
- US4 tasks are sequential: measure (T045) → raise (T046) → measure (T047) → raise (T048)

### Parallel Opportunities

- **Phase 3 (US1)**: All 33 frontend component test tasks (T005–T037) can run in parallel — each creates a separate test file
- **Phase 4 (US2)**: All 4 backend test tasks (T038–T041) can run in parallel — each creates a separate test file
- **Phase 5 (US3)**: T042 must complete before T043; T043 before T044 (sequential)
- **US1, US2, US3**: Can all run in parallel (frontend, backend tests, backend fix are independent)

---

## Parallel Example: User Story 1

```text
# Launch all chores tests together (all [P]):
Task T005: "Create test for ChoreChatFlow in solune/frontend/src/components/chores/__tests__/ChoreChatFlow.test.tsx"
Task T006: "Create test for ChoreInlineEditor in solune/frontend/src/components/chores/__tests__/ChoreInlineEditor.test.tsx"
Task T007: "Create test for ChoresSaveAllBar in solune/frontend/src/components/chores/__tests__/ChoresSaveAllBar.test.tsx"
Task T008: "Create test for ChoresSpotlight in solune/frontend/src/components/chores/__tests__/ChoresSpotlight.test.tsx"
Task T009: "Create test for ChoresToolbar in solune/frontend/src/components/chores/__tests__/ChoresToolbar.test.tsx"
Task T010: "Create test for PipelineSelector in solune/frontend/src/components/chores/__tests__/PipelineSelector.test.tsx"

# Launch all tools tests together (all [P]):
Task T011: "Create test for ToolCard in solune/frontend/src/components/tools/__tests__/ToolCard.test.tsx"
Task T012: "Create test for ToolsPanel in solune/frontend/src/components/tools/__tests__/ToolsPanel.test.tsx"
Task T013: "Create test for ToolChips in solune/frontend/src/components/tools/__tests__/ToolChips.test.tsx"
Task T014: "Create test for McpPresetsGallery in solune/frontend/src/components/tools/__tests__/McpPresetsGallery.test.tsx"
Task T015: "Create test for RepoConfigPanel in solune/frontend/src/components/tools/__tests__/RepoConfigPanel.test.tsx"
Task T016: "Create test for EditRepoMcpModal in solune/frontend/src/components/tools/__tests__/EditRepoMcpModal.test.tsx"
Task T017: "Create test for UploadMcpModal in solune/frontend/src/components/tools/__tests__/UploadMcpModal.test.tsx"
Task T018: "Create test for GitHubMcpConfigGenerator in solune/frontend/src/components/tools/__tests__/GitHubMcpConfigGenerator.test.tsx"
```

## Parallel Example: User Story 2

```text
# Launch all backend prompt tests together (all [P]):
Task T038: "Create test for agent_instructions prompt in solune/backend/tests/unit/test_agent_instructions_prompt.py"
Task T039: "Create test for issue_generation prompt in solune/backend/tests/unit/test_issue_generation_prompt.py"
Task T040: "Create test for task_generation prompt in solune/backend/tests/unit/test_task_generation_prompt.py"
Task T041: "Create test for otel_setup service in solune/backend/tests/unit/test_otel_setup.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Verify test infrastructure
2. Complete Phase 2: Confirm foundation (no-op for this feature)
3. Complete Phase 3: User Story 1 — Frontend test gaps
4. **STOP and VALIDATE**: Run `cd solune/frontend && npx vitest run --coverage` — all new tests pass, coverage improves
5. Deploy/demo if ready — frontend has regression detection for chores, tools, agents, settings, UI

### Incremental Delivery

1. Complete Setup + Foundation → Infrastructure verified
2. Add US1 (Frontend tests) → Test independently → ~33 new test files (MVP!)
3. Add US2 (Backend tests) → Test independently → ~4 new test files
4. Add US3 (Bug fix) → Test independently → 1 fix + 1 regression test
5. Add US4 (Thresholds) → Test independently → Config changes only
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundation verification together
2. Once Foundation is verified:
   - Developer A: User Story 1 (Frontend tests — largest scope)
   - Developer B: User Story 2 (Backend prompt/otel tests)
   - Developer C: User Story 3 (Bug fix — smallest scope, highest risk)
3. All three stories complete independently
4. Team raises thresholds together (US4) after US1–US3 merge

---

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 52 (T001–T052) |
| Phase 1 (Setup) | 4 tasks |
| Phase 2 (Foundation) | 0 tasks (verification only) |
| Phase 3 (US1 — Frontend) | 33 tasks |
| Phase 4 (US2 — Backend) | 4 tasks |
| Phase 5 (US3 — Bug fix) | 3 tasks |
| Phase 6 (US4 — Thresholds) | 4 tasks |
| Phase 7 (Polish) | 4 tasks |
| Parallel opportunities | 37 of 52 tasks are parallelizable |
| Suggested MVP scope | User Story 1 (Phase 3) |
| Independent test criteria | Each story validates with its own test runner command |

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All new tests must be meaningful — test actual behavior, not just imports or trivial renders
- Use existing test patterns: `vi.mock()` + `vi.hoisted()` for frontend mocks, `unittest.mock.patch` for backend mocks
- Use accessible queries (`getByRole`, `getByText`, `getByLabelText`) for frontend tests
- Use `async def test_*` directly for backend async tests (asyncio_mode = "auto")
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
