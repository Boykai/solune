# Tasks: Remove Fleet Dispatch & Copilot CLI Code

**Input**: Design documents from `/specs/006-remove-fleet-dispatch-cli/`
**Prerequisites**: plan.md (required), spec.md (from `specs/001-remove-fleet-dispatch/`), research.md, data-model.md, quickstart.md, contracts/

**Tests**: No new tests are mandated. Fleet-specific test files are deleted and fleet assertions in shared test files are removed. Existing non-fleet tests serve as regression gates.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. This is a deletion-focused refactor — no new files or features are created.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/src/`, `solune/frontend/src/`
- **Scripts**: `solune/scripts/`
- **CLI Plugin**: `solune/cli-plugin/`
- **Docs**: `solune/docs/`
- **Tests**: `solune/backend/tests/`, `solune/frontend/src/services/schemas/`

## Phase 1: Setup (Delete Standalone Fleet & CLI Artifacts)

**Purpose**: Delete all standalone fleet dispatch and CLI plugin files that have no code dependents. These deletions are safe to perform in any order.

- [ ] T001 Delete fleet dispatch shell scripts: solune/scripts/fleet-dispatch.sh and solune/scripts/lib/fleet_dispatch_common.sh
- [ ] T002 [P] Delete pipeline config and templates: solune/scripts/pipelines/fleet-dispatch.json, solune/scripts/pipelines/pipeline-config.schema.json, and solune/scripts/pipelines/templates/ (all 12 template files)
- [ ] T003 [P] Delete entire CLI plugin directory: solune/cli-plugin/ (plugin.json, .mcp.json, agents/, hooks/, skills/)
- [ ] T004 [P] Delete fleet backend service module: solune/backend/src/services/fleet_dispatch.py (~356 lines, FleetDispatchService class)
- [ ] T005 Delete empty directories: remove solune/scripts/pipelines/ if empty after template/config removal; remove solune/scripts/lib/ if empty after common script removal

---

## Phase 2: Foundational (Remove Fleet Models & Config Functions)

**Purpose**: Remove fleet-specific Pydantic models and configuration functions that are imported by core orchestration modules. MUST complete before any user story phase can begin.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete — removing these models and config functions breaks fleet import paths that Phase 3+ tasks rely on cleaning up.

- [ ] T006 Remove 9 FleetDispatch* model classes from solune/backend/src/models/pipeline.py: delete FleetDispatchModel, FleetDispatchRepository, FleetDispatchDefaults, FleetDispatchSubIssue, FleetDispatchAgent, FleetDispatchExecutionGroup, FleetDispatchConfig, FleetDispatchStatus (enum), FleetDispatchRecord. Preserve all non-fleet models: PipelineAgentNode, ExecutionGroup, PipelineStage, PipelineConfig, etc.
- [ ] T007 [P] Remove fleet config functions and imports from solune/backend/src/services/workflow_orchestrator/config.py: delete _DEFAULT_FLEET_DISPATCH_CONFIG, get_default_fleet_dispatch_config_path(), load_fleet_dispatch_config(), build_pipeline_stages_from_fleet_config(). Remove FleetDispatchConfig import. Preserve: get_workflow_config(), set_workflow_config(), resolve_project_pipeline_mappings(), load_user_agent_mappings(), and all other non-fleet functions.
- [ ] T008 [P] Remove agent_task_ids field (dict[str, str]) from PipelineState dataclass in solune/backend/src/services/workflow_orchestrator/models.py

**Checkpoint**: Fleet models and config functions removed — orchestration cleanup can now begin.

---

## Phase 3: User Story 1 — Issue Dispatch Continues via Classic Path (Priority: P1) 🎯 MVP

**Goal**: The classic dispatch path (format_issue_context_as_prompt + standard Copilot assignment) becomes the sole execution path. All fleet dispatch branching, state tracking, and polling is removed from the orchestrator.

**Independent Test**: Trigger a pipeline dispatch for any issue and verify the agent is assigned via standard Copilot assignment, issue context is formatted as a prompt, the pipeline progresses through all stages, and no fleet-related fields (agent_task_ids, dispatch_backend) appear in state or responses.

### Implementation for User Story 1

- [ ] T009 [US1] Clean orchestrator: remove FleetDispatchService import and self.fleet_dispatch instantiation, remove 3 is_fleet_eligible() branch sites (keep the else/"classic" path as sole code path using format_issue_context_as_prompt()), remove _find_reusable_fleet_sub_issue(), build_fleet_sub_issue_labels() calls, fleet logging, and agent_task_ids from state writes in solune/backend/src/services/workflow_orchestrator/orchestrator.py
- [ ] T010 [P] [US1] Remove fleet task helpers: delete _get_agent_task_id(), _check_agent_task_status(), and remove FleetDispatchService.normalize_task_state() import from solune/backend/src/services/copilot_polling/helpers.py
- [ ] T011 [P] [US1] Remove "Fleet task failed" log messages and any fleet-specific status handling from solune/backend/src/services/copilot_polling/pipeline.py
- [ ] T012 [P] [US1] Remove agent_task_ids from serialization and deserialization logic in solune/backend/src/services/pipeline_state_store.py (existing SQLite rows with agent_task_ids in JSON will be safely ignored)

**Checkpoint**: Classic dispatch path is the sole execution path. Fleet branching fully removed from orchestrator and polling.

---

## Phase 4: User Story 2 — Codebase Is Free of Fleet Dispatch Artifacts (Priority: P1)

**Goal**: Zero fleet-related references remain in source code, configuration, or type definitions (excluding CHANGELOG.md and historical documentation).

**Independent Test**: Run `grep -rn "fleet\|FleetDispatch\|fleet_dispatch\|fleet-dispatch\|agent_task_ids\|dispatch_backend" solune/ --exclude-dir=node_modules --exclude=CHANGELOG.md` and verify zero matches.

### Implementation for User Story 2

- [ ] T013 [US2] Scan entire codebase for remaining fleet-related references (fleet, FleetDispatch, fleet_dispatch, fleet-dispatch, agent_task_ids, dispatch_backend) and clean up any residual occurrences missed by other phases in solune/

**Checkpoint**: Comprehensive grep across codebase returns zero fleet matches (excluding CHANGELOG.md).

---

## Phase 5: User Story 3 — All Existing Tests Pass After Removal (Priority: P1)

**Goal**: All backend and frontend test suites pass with zero errors, zero import failures, and zero type errors after fleet test deletion and assertion cleanup.

**Independent Test**: Run `cd solune/backend && uv run pytest tests/unit/ -x -q`, `cd solune/backend && uv run pytest tests/integration/ -x -q`, `cd solune/frontend && npx tsc --noEmit`, and `cd solune/frontend && npx vitest run` — all must pass.

### Implementation for User Story 3

- [ ] T014 [P] [US3] Delete fleet test harness: solune/backend/tests/fleet_dispatch_harness.py
- [ ] T015 [P] [US3] Delete fleet CLI test: solune/backend/tests/unit/test_fleet_dispatch_cli.py
- [ ] T016 [P] [US3] Delete fleet service test: solune/backend/tests/unit/test_fleet_dispatch_service.py
- [ ] T017 [P] [US3] Delete fleet templates test: solune/backend/tests/unit/test_fleet_dispatch_templates.py
- [ ] T018 [P] [US3] Delete fleet parity test: solune/backend/tests/unit/test_fleet_parity.py
- [ ] T019 [P] [US3] Delete fleet smoke test: solune/backend/tests/integration/test_fleet_dispatch_smoke.py
- [ ] T020 [P] [US3] Delete fleet app dispatch test: solune/backend/tests/integration/test_fleet_app_dispatch.py
- [ ] T021 [US3] Remove fleet-specific assertions and fixtures from backend test files: solune/backend/tests/unit/test_pipeline_config_schema.py (fleet config schema tests), solune/backend/tests/unit/test_workflow_orchestrator.py (fleet branch assertions), solune/backend/tests/unit/test_api_workflow.py (dispatch_backend/agent_task_ids assertions), solune/backend/tests/unit/test_issues.py (fleet label/issue assertions), solune/backend/tests/unit/test_helpers_polling.py (fleet polling assertions), solune/backend/tests/unit/test_pipeline_state_store.py (agent_task_ids assertions)
- [ ] T022 [US3] Remove fleet metadata field test from frontend schema test: solune/frontend/src/services/schemas/pipeline.test.ts

**Checkpoint**: All 7 fleet test files deleted, fleet assertions removed from 7 shared test files. Test suites ready for verification.

---

## Phase 6: User Story 4 — Pipeline Orchestration Uses Hardcoded Legacy Stages (Priority: P2)

**Goal**: The pipeline orchestrator uses hardcoded legacy stages directly as the primary and sole stage source, with no dependency on fleet dispatch configuration files or fleet-specific stage builders.

**Independent Test**: Launch a pipeline and verify the stages returned match the hardcoded legacy stages (11 stages across 4 groups), with no fleet config file loading or fleet stage building.

### Implementation for User Story 4

- [ ] T023 [US4] Simplify pipeline orchestrator: remove fleet imports (load_fleet_dispatch_config, build_pipeline_stages_from_fleet_config), replace _default_pipeline_stages() with the hardcoded legacy stages directly (the current fallback/except path becomes the sole definition) in solune/backend/src/services/pipeline_orchestrator.py

**Checkpoint**: Pipeline stages are deterministic and hardcoded — no fleet configuration dependency.

---

## Phase 7: User Story 5 — Shared Functions Remain Available to Non-Fleet Callers (Priority: P2)

**Goal**: Fleet-exclusive Copilot functions are removed while the shared assign_copilot_to_issue() function remains available for its existing callers (app_plan_orchestrator.py, auto_merge.py).

**Independent Test**: Verify assign_copilot_to_issue() is importable and callable from app_plan_orchestrator.py and auto_merge.py. Verify list_agent_tasks(), get_agent_task(), and _discover_agent_task_endpoint() no longer exist.

### Implementation for User Story 5

- [ ] T024 [US5] Clean copilot service: delete list_agent_tasks(), get_agent_task(), _discover_agent_task_endpoint() (all fleet-exclusive, completely unused even pre-removal). Preserve assign_copilot_to_issue() — used by app_plan_orchestrator.py and auto_merge.py in solune/backend/src/services/github_projects/copilot.py

**Checkpoint**: Shared Copilot assignment function preserved; fleet-only methods removed.

---

## Phase 8: User Story 6 — API Responses No Longer Contain Fleet Fields (Priority: P2)

**Goal**: Workflow API responses no longer contain fleet-specific fields (dispatch_backend, agent_task_ids). Frontend type definitions and Zod schemas are updated to match.

**Independent Test**: Call the workflow API endpoint and inspect the response payload — verify dispatch_backend and agent_task_ids are absent. Run frontend type check and schema tests.

### Implementation for User Story 6

- [ ] T025 [US6] Clean API layer: remove _infer_dispatch_backend() helper, FleetDispatchService import, and dispatch_backend/agent_task_ids fields from response dict in solune/backend/src/api/workflow.py
- [ ] T026 [P] [US6] Remove fleet fields from frontend types: delete agent_task_ids (Record<string, string>) and dispatch_backend ('fleet' | 'classic') from PipelineStateInfo interface in solune/frontend/src/types/index.ts
- [ ] T027 [P] [US6] Remove fleet fields from frontend Zod schema: delete agent_task_ids (z.record) and dispatch_backend (z.enum) from pipeline state schema in solune/frontend/src/services/schemas/pipeline.ts

**Checkpoint**: API responses are clean; frontend types and schemas match backend response shape.

---

## Phase 9: User Story 7 — Documentation Reflects Simplified Architecture (Priority: P3)

**Goal**: Architecture diagrams and planning documents accurately reflect the system without fleet dispatch components.

**Independent Test**: Review backend-components.mmd and verify Fleet Dispatch is not present as a component. Review plan.md and verify no fleet-dispatch-pipelines references exist.

### Implementation for User Story 7

- [ ] T028 [US7] Remove Fleet Dispatch entry (SVC_23["Fleet Dispatch"] or equivalent) from architecture diagram in solune/docs/architectures/backend-components.mmd and renumber subsequent entries if needed
- [ ] T029 [US7] Regenerate architecture diagrams by running solune/scripts/generate-diagrams.sh (CI checks diagrams with --check flag)
- [ ] T030 [US7] Remove fleet-dispatch-pipelines references from root plan.md

**Checkpoint**: Documentation accurately reflects the simplified architecture.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final verification across all user stories and cross-cutting quality checks.

- [ ] T031 Run backend unit tests: cd solune/backend && uv run pytest tests/unit/ -x -q — verify all pass with no import errors
- [ ] T032 [P] Run backend integration tests: cd solune/backend && uv run pytest tests/integration/ -x -q — verify no broken imports
- [ ] T033 [P] Run backend linting and type checking: cd solune/backend && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run pyright src/
- [ ] T034 [P] Run frontend type check and tests: cd solune/frontend && npx tsc --noEmit && npx vitest run
- [ ] T035 Final verification: grep -rn for zero fleet references (excluding CHANGELOG.md, node_modules), verify assign_copilot_to_issue() callers (app_plan_orchestrator.py, auto_merge.py) are unaffected, verify _default_pipeline_stages() returns hardcoded stages with no fleet dependency

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately. All tasks are file deletions with no code dependents.
- **Foundational (Phase 2)**: No strict dependency on Phase 1 — Phase 1 deletes standalone files (scripts, CLI plugin, fleet_dispatch.py) that are not imported by the model/config files modified in Phase 2. However, completing Phase 1 first provides a cleaner working tree.
- **US1 (Phase 3)**: Depends on Phase 2 — fleet models and config must be removed before cleaning orchestrator imports.
- **US2 (Phase 4)**: Depends on Phases 3, 5–9 — codebase-wide sweep should run after all modifications are complete.
- **US3 (Phase 5)**: Can start after Phase 2 (delete fleet test files immediately); test file modifications depend on corresponding source changes in Phases 3, 6–8.
- **US4 (Phase 6)**: Depends on Phase 2 — fleet config functions must be removed before simplifying pipeline orchestrator.
- **US5 (Phase 7)**: Depends on Phase 2 — fleet models must be removed. Can run in parallel with US1, US4, US6.
- **US6 (Phase 8)**: Depends on Phase 2 — fleet models must be removed. Can run in parallel with US1, US4, US5.
- **US7 (Phase 9)**: No code dependencies — can run in parallel with Phases 3–8.
- **Polish (Phase 10)**: Depends on ALL previous phases completing.

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational (Phase 2). No dependencies on other user stories. This is the MVP.
- **US2 (P1)**: Cross-cutting — verified once all other user stories are complete.
- **US3 (P1)**: Test deletions can start after Phase 2. Test modifications depend on corresponding source changes.
- **US4 (P2)**: Depends on Foundational only. Independent of US1, US5, US6.
- **US5 (P2)**: Depends on Foundational only. Independent of US1, US4, US6.
- **US6 (P2)**: Depends on Foundational only. Independent of US1, US4, US5.
- **US7 (P3)**: No code dependencies — fully independent.

### Within Each User Story

- File deletions before code modifications
- Import removal before logic changes
- Backend before frontend (API fields drive type definitions)
- Code changes before test *modifications* (test file *deletions* can happen early since they remove entire files)

### Parallel Opportunities

- **Phase 1**: T002, T003, T004 can all run in parallel (independent file deletions)
- **Phase 2**: T007, T008 can run in parallel (different files)
- **Phase 3**: T010, T011, T012 can run in parallel with each other (different files); T009 is the critical path
- **Phase 5**: T014–T020 can ALL run in parallel (independent file deletions)
- **Phase 6–8**: US4, US5, US6 can all run in parallel (different files, no cross-dependencies)
- **Phase 8**: T026, T027 can run in parallel (different frontend files)
- **Phase 9**: Can run entirely in parallel with Phases 3–8
- **Phase 10**: T032, T033, T034 can run in parallel (independent verification commands)

---

## Parallel Example: Phase 1 (Setup)

```bash
# Launch all independent deletions together:
Task T002: "Delete pipeline config/templates from solune/scripts/pipelines/"
Task T003: "Delete CLI plugin directory solune/cli-plugin/"
Task T004: "Delete fleet backend service solune/backend/src/services/fleet_dispatch.py"
```

## Parallel Example: User Story 3 (Test Cleanup)

```bash
# Launch all fleet test file deletions together:
Task T014: "Delete solune/backend/tests/fleet_dispatch_harness.py"
Task T015: "Delete solune/backend/tests/unit/test_fleet_dispatch_cli.py"
Task T016: "Delete solune/backend/tests/unit/test_fleet_dispatch_service.py"
Task T017: "Delete solune/backend/tests/unit/test_fleet_dispatch_templates.py"
Task T018: "Delete solune/backend/tests/unit/test_fleet_parity.py"
Task T019: "Delete solune/backend/tests/integration/test_fleet_dispatch_smoke.py"
Task T020: "Delete solune/backend/tests/integration/test_fleet_app_dispatch.py"
```

## Parallel Example: P2 User Stories (US4 + US5 + US6)

```bash
# Launch all P2 user stories in parallel (different files, no cross-dependencies):
Task T023 [US4]: "Simplify pipeline_orchestrator.py with hardcoded legacy stages"
Task T024 [US5]: "Clean copilot.py — remove fleet-only methods"
Task T025 [US6]: "Clean workflow.py — remove fleet inference and fields"
Task T026 [US6]: "Remove fleet fields from frontend types/index.ts"
Task T027 [US6]: "Remove fleet fields from frontend schemas/pipeline.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (delete standalone artifacts)
2. Complete Phase 2: Foundational (remove fleet models & config)
3. Complete Phase 3: User Story 1 (clean orchestrator for classic-only dispatch)
4. **STOP and VALIDATE**: Verify classic dispatch path works, no fleet branching remains in orchestrator
5. Run backend tests to confirm no import errors

### Incremental Delivery

1. Complete Setup + Foundational → Fleet artifacts deleted, models removed
2. Add US1 → Classic dispatch is sole path → Verify orchestrator (MVP!)
3. Add US4 + US5 + US6 in parallel → Pipeline stages hardcoded, copilot.py clean, API clean
4. Add US3 → Test suite fully cleaned → All tests pass
5. Add US7 → Documentation updated
6. Polish → Full verification across all stories
7. Each story adds cleanup value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (sequential dependency)
2. Once Foundational is done:
   - Developer A: US1 (orchestrator cleanup) → US2 (final sweep)
   - Developer B: US4 (pipeline stages) + US5 (copilot.py) + US6 (API + frontend)
   - Developer C: US3 (test cleanup) + US7 (documentation)
3. All stories complete independently; Polish phase verifies everything

---

## Summary

| Metric | Count |
|--------|-------|
| **Total tasks** | 35 |
| **Setup tasks** | 5 (T001–T005) |
| **Foundational tasks** | 3 (T006–T008) |
| **US1 tasks** | 4 (T009–T012) |
| **US2 tasks** | 1 (T013) |
| **US3 tasks** | 9 (T014–T022) |
| **US4 tasks** | 1 (T023) |
| **US5 tasks** | 1 (T024) |
| **US6 tasks** | 3 (T025–T027) |
| **US7 tasks** | 3 (T028–T030) |
| **Polish tasks** | 5 (T031–T035) |
| **Parallelizable tasks** | 22 (marked with [P]) |
| **Files to delete** | ~30 |
| **Files to modify** | ~15 |
| **Suggested MVP scope** | US1 (Phases 1–3: Setup + Foundational + Classic Path) |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks in the same phase
- [Story] label maps task to specific user story for traceability
- No new tests are mandated — fleet test files are deleted, fleet assertions in shared tests are removed
- Existing non-fleet tests serve as regression gates
- No database migration needed — removed fields safely ignored on deserialization of existing SQLite rows
- CHANGELOG.md may contain historical fleet references — these are acceptable and should not be removed
- .github/agents/*.agent.md files are preserved unchanged — fleet eligibility was runtime, not encoded in agent definitions
- guard-config.yml is unchanged — no fleet-specific entries exist
