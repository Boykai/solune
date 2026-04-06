# Tasks: Multi-Phase App Creation with Auto-Merge Pipeline Orchestration

**Input**: Design documents from `/specs/001-multi-phase-app-creation/` and `/specs/002-auto-merge-pipeline-orchestration/`
**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, contracts/ ✅, research.md ✅, quickstart.md ✅

**Tests**: Explicitly requested in Phase 4 of the parent issue and plan.md — included below.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/src/`, `solune/frontend/src/`
- **Tests**: `solune/backend/tests/unit/`, `solune/frontend/src/**/*.test.*`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Database migration and shared data models needed by all user stories

- [ ] T001 Create database migration for orchestration tracking table in solune/backend/src/migrations/042_app_plan_orchestrations.sql
- [ ] T002 Add `prerequisite_issues: list[int]` field to PipelineState dataclass in solune/backend/src/services/workflow_orchestrator/models.py
- [ ] T003 [P] Serialize `prerequisite_issues` in `_pipeline_state_to_row()` metadata JSON in solune/backend/src/services/pipeline_state_store.py
- [ ] T004 [P] Deserialize `prerequisite_issues` in `_row_to_pipeline_state()` with default `[]` in solune/backend/src/services/pipeline_state_store.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core parser service and orchestrator skeleton that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Create PlanPhase dataclass (index, title, description, steps, depends_on_phases, execution_mode) in solune/backend/src/services/plan_parser.py
- [ ] T006 Implement `parse_plan(plan_md_content: str) -> list[PlanPhase]` — extract `## Implementation Phases` section, parse `### Phase N — Title` blocks via regex `r"### Phase (\d+)\s*[—–-]\s*(.+)"`, extract description, steps, dependency markers, and execution mode in solune/backend/src/services/plan_parser.py
- [ ] T007 Implement `group_into_waves(phases: list[PlanPhase]) -> list[list[PlanPhase]]` — Wave 1: no deps, Wave N: deps all in prior waves in solune/backend/src/services/plan_parser.py
- [ ] T008 Add circular dependency detection in `parse_plan()` that raises ValueError when cycles are found in solune/backend/src/services/plan_parser.py
- [ ] T009 Create AppPlanOrchestrator class skeleton with `__init__`, `_update_status()`, and status state machine constants in solune/backend/src/services/app_plan_orchestrator.py

**Checkpoint**: Foundation ready — parser and orchestrator skeleton available for all user stories

---

## Phase 3: User Story 1 — Plan-Driven App Creation (Priority: P1) 🎯 MVP

**Goal**: User submits an app description → system generates a plan, parses phases, creates GitHub issues per phase, and launches Phase 1 pipeline — all without further user input.

**Independent Test**: Submit an app description via `POST /apps/create-with-plan`; verify (a) plan.md is generated, (b) phases are parsed into PlanPhase objects, (c) corresponding parent issues appear on the project board, (d) first wave of pipelines launches.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T010 [P] [US1] Unit tests for `parse_plan()` — valid plan.md → correct PlanPhase objects, dependency detection, parallel detection, edge cases (single phase, no phases error) in solune/backend/tests/unit/test_plan_parser.py
- [ ] T011 [P] [US1] Unit tests for `group_into_waves()` — correct wave grouping by dependency depth, single wave when no deps in solune/backend/tests/unit/test_plan_parser.py
- [ ] T012 [P] [US1] Unit test for circular dependency detection — raises ValueError with cycle info in solune/backend/tests/unit/test_plan_parser.py
- [ ] T013 [P] [US1] Unit tests for `orchestrate_app_creation()` happy path with mocked services — verifies status transitions: planning → speckit_running → parsing_phases → creating_issues → launching_pipelines → active in solune/backend/tests/unit/test_app_plan_orchestrator.py
- [ ] T014 [P] [US1] Unit tests for error handling in orchestration — speckit.plan timeout, plan.md fetch failure, parse failure (zero phases) in solune/backend/tests/unit/test_app_plan_orchestrator.py
- [ ] T015 [P] [US1] Unit tests for phase issue creation — correct titles (Phase N/M: Title — AppName), correct body content, tracking table appended, added to project board in solune/backend/tests/unit/test_app_plan_orchestrator.py

### Implementation for User Story 1

- [ ] T016 [US1] Implement `orchestrate_app_creation()` main flow in AppPlanOrchestrator — call `chat_agent_svc.run_plan()`, create planning issue, assign speckit.plan, poll for Done!, fetch plan.md, parse phases, create issues, launch pipelines in solune/backend/src/services/app_plan_orchestrator.py
- [ ] T017 [US1] Implement `_create_phase_issues()` — for each PlanPhase create a GitHub Parent Issue with title `Phase {N}/{M}: {title} — {app_name}`, body with app overview + phase steps + tracking table, add to project board at Backlog status in solune/backend/src/services/app_plan_orchestrator.py
- [ ] T018 [US1] Implement `_launch_phase_pipelines()` — call `group_into_waves()`, launch Wave 1 with `auto_merge=True` and no prerequisites, queue Wave 2+ with prerequisite_issues in solune/backend/src/services/app_plan_orchestrator.py
- [ ] T019 [US1] Implement error handling in `orchestrate_app_creation()` — configurable timeout for speckit.plan (default 20min), catch parse failures, update status to `failed` with error_message, broadcast failure via WebSocket in solune/backend/src/services/app_plan_orchestrator.py
- [ ] T020 [US1] Create `POST /apps/create-with-plan` endpoint — validate request body per OpenAPI contract, create App record, create AppPlanOrchestration record, start orchestration as BackgroundTask, return 202 with orchestration_id in solune/backend/src/api/apps.py
- [ ] T021 [US1] Create `GET /apps/{app_name}/plan-status` endpoint — read AppPlanOrchestration from DB, return status, phase_count, phase_issues array with issue numbers/URLs/pipeline status, error_message in solune/backend/src/api/apps.py

**Checkpoint**: User Story 1 fully functional — plan-driven app creation works end-to-end via API

---

## Phase 4: User Story 2 — Sequential Phase Execution with Auto-Merge (Priority: P2)

**Goal**: After Phase 1's pipeline completes and its PR is merged to main, the system automatically starts Phase 2 from the updated main branch. This continues sequentially until all phases are complete.

**Independent Test**: Simulate two sequential phases; verify Phase 2's pipeline only starts after Phase 1's PR has been merged, and Phase 2 branches from updated main.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T022 [P] [US2] Unit tests for `_dequeue_next_pipeline()` skipping pipelines with unmet prerequisite_issues in solune/backend/tests/unit/test_copilot_polling.py
- [ ] T023 [P] [US2] Unit tests for `_dequeue_next_pipeline()` proceeding when all prerequisite_issues have merged PRs in solune/backend/tests/unit/test_copilot_polling.py
- [ ] T024 [P] [US2] Unit test for backward compatibility — pipeline with empty prerequisite_issues dequeues normally in solune/backend/tests/unit/test_copilot_polling.py
- [ ] T025 [P] [US2] Unit tests for `PipelineState` serialization round-trip — prerequisite_issues survives `_pipeline_state_to_row()` → `_row_to_pipeline_state()` in solune/backend/tests/unit/test_copilot_polling.py

### Implementation for User Story 2

- [ ] T026 [US2] Extend `execute_pipeline_launch()` with `auto_merge: bool = False` and `prerequisite_issues: list[int] | None = None` params — pass both to PipelineState constructor in queue and non-queue branches in solune/backend/src/api/pipelines.py
- [ ] T027 [US2] Extend `_dequeue_next_pipeline()` with prerequisite checking — before dequeuing, verify all prerequisite_issues have merged PRs; skip pipelines with unmet prerequisites and try next queued one in solune/backend/src/services/copilot_polling/pipeline.py
- [ ] T028 [US2] Verify auto-merge → dequeue trigger exists — confirm `_dequeue_next_pipeline()` is called after successful auto-merge (already at ~line 2641 in pipeline.py); add comment documenting the prerequisite-aware flow in solune/backend/src/services/copilot_polling/pipeline.py

**Checkpoint**: Sequential phase execution works — Phase N+1 starts only after Phase N's PR is merged to main

---

## Phase 5: User Story 3 — Real-Time Planning Progress Visibility (Priority: P3)

**Goal**: While the system is planning and orchestrating, the user sees a live progress view showing each stage with links to created issues as they appear.

**Independent Test**: Initiate app creation and verify the progress view updates through each state transition (planning → speckit_running → parsing_phases → creating_issues → launching_pipelines → active) and displays correct links.

### Implementation for User Story 3

- [ ] T029 [US3] Implement WebSocket broadcasts on status transitions in `_update_status()` — emit `plan_status_update`, `plan_phase_created`, `plan_orchestration_complete`, `plan_orchestration_failed` payloads per AsyncAPI contract via `connection_manager.broadcast_to_project()` in solune/backend/src/services/app_plan_orchestrator.py
- [ ] T030 [P] [US3] Add TypeScript interfaces for `AppCreateWithPlanResponse`, `AppPlanStatusResponse`, `PhaseIssueInfo`, and WebSocket event payloads in solune/frontend/src/types/apps.ts
- [ ] T031 [P] [US3] Add `useCreateAppWithPlan()` mutation hook — calls `POST /apps/create-with-plan` in solune/frontend/src/hooks/useApps.ts
- [ ] T032 [P] [US3] Add `useAppPlanStatus(appName)` query hook — polls `GET /apps/{app_name}/plan-status` with fallback when WebSocket is unavailable in solune/frontend/src/hooks/useApps.ts
- [ ] T033 [US3] Extend CreateAppDialog.tsx — after form submission, transition to Planning Progress view with stepper showing stages (Plan Generation → Agent Running → Parsing → Creating Issues → Launching → Active), listen for WebSocket events to update step status, show links to created phase issues, handle error state with retry option in solune/frontend/src/components/apps/CreateAppDialog.tsx

**Checkpoint**: Users see real-time progress of plan orchestration with clickable links to phase issues

---

## Phase 6: User Story 4 — Dependency-Aware Wave Execution (Priority: P3)

**Goal**: Phases are grouped into waves based on dependency relationships. Independent phases execute in parallel within a wave. Dependent phases only start after their specific prerequisites are merged.

**Independent Test**: Create a plan with 3 phases where Phase 1 and Phase 2 are independent (Wave 1) and Phase 3 depends on both. Verify Phases 1 and 2 launch in parallel and Phase 3 starts only after both are merged.

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T034 [P] [US4] Unit test for wave grouping with complex dependency graph — 3+ waves, mixed parallel/sequential phases in solune/backend/tests/unit/test_plan_parser.py
- [ ] T035 [P] [US4] Unit test for `_launch_phase_pipelines()` — Wave 1 phases launched with no prerequisites, Wave 2 phases queued with correct prerequisite_issues in solune/backend/tests/unit/test_app_plan_orchestrator.py
- [ ] T036 [P] [US4] Unit test for partial wave failure — when one phase in a wave fails, only its direct dependents are halted, unrelated phases continue in solune/backend/tests/unit/test_copilot_polling.py

### Implementation for User Story 4

- [ ] T037 [US4] Ensure `_launch_phase_pipelines()` handles multi-wave plans — Wave 1 pipelines launch immediately in parallel, Wave 2+ pipelines are queued with prerequisite_issues pointing to prior wave issue numbers in solune/backend/src/services/app_plan_orchestrator.py
- [ ] T038 [US4] Handle partial wave failure in `_dequeue_next_pipeline()` — when evaluating prerequisites, skip pipelines whose specific prerequisite phases failed while allowing unrelated queued pipelines to proceed in solune/backend/src/services/copilot_polling/pipeline.py

**Checkpoint**: Wave-based parallel execution works — independent phases run simultaneously, dependent phases respect merge gates

---

## Phase 7: Tests — Integration & Cross-Cutting

**Purpose**: End-to-end integration test and additional edge case coverage

- [ ] T039 [P] Integration test for full orchestration flow with mocked GitHub API and Copilot SDK — create app → run plan agent → parse phases → create issues → launch pipelines → auto-merge Wave 1 → dequeue Wave 2 in solune/backend/tests/unit/test_app_plan_orchestrator.py
- [ ] T040 [P] Unit test for `POST /apps/create-with-plan` endpoint — validates request body, returns 202, creates records, starts background task in solune/backend/tests/unit/test_app_plan_orchestrator.py
- [ ] T041 [P] Unit test for `GET /apps/{app_name}/plan-status` endpoint — returns correct status response, handles 404 for unknown apps in solune/backend/tests/unit/test_app_plan_orchestrator.py

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T042 [P] Add logging throughout AppPlanOrchestrator — log each status transition, phase issue creation, pipeline launch, and errors in solune/backend/src/services/app_plan_orchestrator.py
- [ ] T043 [P] Add logging for prerequisite checking in `_dequeue_next_pipeline()` — log skip reasons and proceed decisions in solune/backend/src/services/copilot_polling/pipeline.py
- [ ] T044 Run quickstart.md validation — verify all commands from quickstart.md execute successfully against implemented code
- [ ] T045 Run full backend lint and type check — `ruff check src tests && ruff format --check src tests && pyright src` in solune/backend/
- [ ] T046 Run full frontend lint and type check — `npm run lint && npm run type-check && npm run build` in solune/frontend/
- [ ] T047 Run full test suites — `uv run pytest tests/unit/ -v --tb=short` (backend) and `npm run test:coverage` (frontend)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational (Phase 2) — MVP, implement first
- **US2 (Phase 4)**: Depends on Foundational (Phase 2) and US1 (Phase 3) — requires pipeline infrastructure from US1
- **US3 (Phase 5)**: Depends on Foundational (Phase 2) and US1 (Phase 3) — requires API endpoints and WebSocket from US1
- **US4 (Phase 6)**: Depends on US2 (Phase 4) — extends prerequisite checking with wave-aware logic
- **Tests — Integration (Phase 7)**: Depends on US1, US2, US3, US4 — full-flow validation
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — no dependencies on other stories
- **User Story 2 (P2)**: Depends on US1 infrastructure (PipelineState extensions, execute_pipeline_launch params)
- **User Story 3 (P3)**: Depends on US1 API endpoints — adds frontend progress view on top
- **User Story 4 (P3)**: Depends on US2 prerequisite checking — adds wave-aware parallel execution

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models/dataclasses before services
- Services before endpoints/UI
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- **Setup**: T003 and T004 can run in parallel (different functions in same file)
- **US1 Tests**: T010–T015 can all run in parallel (different test files)
- **US2 Tests**: T022–T025 can all run in parallel (same test file, independent test cases)
- **US3 Frontend**: T030, T031, T032 can run in parallel (different files)
- **US4 Tests**: T034–T036 can all run in parallel (different test files)
- **Integration Tests**: T039, T040, T041 can run in parallel (independent test scenarios)
- **Polish**: T042, T043 can run in parallel (different files)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (6 parallel tasks):
Task T010: "Unit tests for parse_plan() in tests/unit/test_plan_parser.py"
Task T011: "Unit tests for group_into_waves() in tests/unit/test_plan_parser.py"
Task T012: "Unit test for circular dependency detection in tests/unit/test_plan_parser.py"
Task T013: "Unit tests for orchestrate_app_creation() in tests/unit/test_app_plan_orchestrator.py"
Task T014: "Unit tests for error handling in tests/unit/test_app_plan_orchestrator.py"
Task T015: "Unit tests for phase issue creation in tests/unit/test_app_plan_orchestrator.py"

# Then implement sequentially within US1:
Task T016: "Implement orchestrate_app_creation() main flow"
Task T017: "Implement _create_phase_issues()"
Task T018: "Implement _launch_phase_pipelines()"
Task T019: "Implement error handling"
Task T020: "Create POST /apps/create-with-plan endpoint"
Task T021: "Create GET /apps/{app_name}/plan-status endpoint"
```

## Parallel Example: User Story 3 (Frontend)

```bash
# Launch all frontend tasks together (3 parallel tasks):
Task T030: "Add TypeScript interfaces in types/apps.ts"
Task T031: "Add useCreateAppWithPlan() hook in hooks/useApps.ts"
Task T032: "Add useAppPlanStatus() hook in hooks/useApps.ts"

# Then implement the dialog (depends on hooks and types):
Task T033: "Extend CreateAppDialog.tsx with progress view"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 2: Foundational (T005–T009)
3. Complete Phase 3: User Story 1 (T010–T021)
4. **STOP and VALIDATE**: Test US1 independently — submit app description, verify phases parsed and issues created
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Sequential execution works
4. Add User Story 3 → Test independently → Users see progress
5. Add User Story 4 → Test independently → Wave-based parallelism optimized
6. Integration tests + Polish → Production-ready

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (P1 — MVP)
3. Once US1 is done:
   - Developer A: User Story 2 (P2 — depends on US1)
   - Developer B: User Story 3 (P3 — depends on US1 API)
4. Once US2 is done:
   - Developer A: User Story 4 (P3 — depends on US2)
5. Integration tests + Polish

---

## Summary

| Metric | Value |
|--------|-------|
| **Total tasks** | 47 |
| **Setup tasks** | 4 (T001–T004) |
| **Foundational tasks** | 5 (T005–T009) |
| **US1 tasks** | 12 (T010–T021) — 6 tests, 6 implementation |
| **US2 tasks** | 7 (T022–T028) — 4 tests, 3 implementation |
| **US3 tasks** | 5 (T029–T033) — 0 tests, 5 implementation |
| **US4 tasks** | 5 (T034–T038) — 3 tests, 2 implementation |
| **Integration test tasks** | 3 (T039–T041) |
| **Polish tasks** | 6 (T042–T047) |
| **Parallel opportunities** | 7 groups identified |
| **Suggested MVP scope** | Setup + Foundational + US1 (21 tasks) |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tests explicitly requested in plan.md Phase 4 — included for US1, US2, US4
- US3 (frontend progress) has no dedicated tests because frontend testing is via existing Vitest coverage
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
