# Tasks: Remove Fleet Dispatch & Copilot CLI Code

**Input**: Design documents from `specs/002-remove-fleet-dispatch/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: No new tests requested. Existing fleet tests are deleted; non-fleet test files are modified to remove fleet assertions.

**Organization**: Tasks are grouped by dependency phase. Each task is tagged with the primary user story it serves. Because this is a removal feature, the natural execution order follows the dependency graph (leaf nodes first, then dependents).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `solune/backend/src/`, `solune/backend/tests/`
- **Frontend**: `solune/frontend/src/`
- **Scripts**: `solune/scripts/`
- **CLI Plugin**: `solune/cli-plugin/`
- **Docs**: `solune/docs/`

---

## Phase 1: Setup

**Purpose**: Verify baseline — all tests pass before any changes

- [x] T001 Run backend unit tests to establish green baseline: `cd solune/backend && python -m pytest tests/unit/ -x -q`
- [x] T002 [P] Run frontend type check and tests to establish green baseline: `cd solune/frontend && npx tsc --noEmit && npx vitest run`

**Checkpoint**: Baseline is green — proceed with removal

---

## Phase 2: Delete Standalone Fleet & CLI Artifacts (no dependencies, all parallel)

**Purpose**: Remove files that have no downstream importers — safe to delete without breaking anything

- [x] T003 [P] [US2] Delete fleet dispatch shell script at solune/scripts/fleet-dispatch.sh
- [x] T004 [P] [US2] Delete fleet dispatch common library at solune/scripts/lib/fleet_dispatch_common.sh
- [x] T005 [P] [US2] Delete entire pipeline config/templates directory at solune/scripts/pipelines/ (fleet-dispatch.json, pipeline-config.schema.json, templates/ with 12 template files)
- [x] T006 [P] [US2] Delete entire CLI plugin directory at solune/cli-plugin/ (plugin.json, .mcp.json, agents/, hooks/, skills/)
- [x] T007 [P] [US2] Delete fleet dispatch backend service module at solune/backend/src/services/fleet_dispatch.py (~360 lines)
- [x] T008 [P] [US2] Delete fleet test harness at solune/backend/tests/fleet_dispatch_harness.py
- [x] T009 [P] [US2] Delete fleet unit test files: solune/backend/tests/unit/test_fleet_dispatch_service.py, solune/backend/tests/unit/test_fleet_dispatch_templates.py, solune/backend/tests/unit/test_fleet_dispatch_cli.py, solune/backend/tests/unit/test_fleet_parity.py
- [x] T010 [P] [US2] Delete fleet integration test files: solune/backend/tests/integration/test_fleet_app_dispatch.py, solune/backend/tests/integration/test_fleet_dispatch_smoke.py

**Checkpoint**: All standalone fleet files deleted — ~25 files removed

---

## Phase 3: Remove Fleet Models & Config Functions (depends on Phase 2)

**Purpose**: Remove FleetDispatch model classes and fleet configuration functions that were imported by the now-deleted fleet service

- [x] T011 [US2] Remove 9 FleetDispatch* model classes (FleetDispatchModel, FleetDispatchRepository, FleetDispatchDefaults, FleetDispatchSubIssue, FleetDispatchAgent, FleetDispatchExecutionGroup, FleetDispatchConfig, FleetDispatchStatus, FleetDispatchRecord) from solune/backend/src/models/pipeline.py — preserve all non-fleet models (PipelineAgentNode, ExecutionGroup, PipelineStage, PipelineConfig, etc.)
- [x] T012 [P] [US2] Remove fleet config functions (_DEFAULT_FLEET_DISPATCH_CONFIG, get_default_fleet_dispatch_config_path(), load_fleet_dispatch_config(), build_pipeline_stages_from_fleet_config()) and FleetDispatchConfig import from solune/backend/src/services/workflow_orchestrator/config.py — preserve get_workflow_config(), set_workflow_config(), resolve_project_pipeline_mappings(), load_user_agent_mappings()

**Checkpoint**: Fleet data layer fully removed — no FleetDispatch* types exist in codebase

---

## Phase 4: Clean Core Orchestration — US1 (depends on Phase 3)

**Purpose**: Remove fleet branching from orchestrators, making classic dispatch the sole code path

- [x] T013 [US1] Clean solune/backend/src/services/workflow_orchestrator/orchestrator.py: remove FleetDispatchService import and instantiation, delete _find_reusable_fleet_sub_issue() method, remove all is_fleet_eligible() branch sites (keep classic/else path as sole code), remove build_fleet_sub_issue_labels() calls, remove agent_task_ids from state writes, remove fleet logging — preserve format_issue_context_as_prompt() and assign_copilot_to_issue() usage
- [x] T014 [P] [US1] Simplify solune/backend/src/services/pipeline_orchestrator.py: remove fleet imports (build_pipeline_stages_from_fleet_config, load_fleet_dispatch_config), replace _default_pipeline_stages() function with a module-level PIPELINE_STAGES constant containing the hardcoded 11 legacy stages
- [x] T015 [P] [US1] Clean solune/backend/src/services/github_projects/copilot.py: delete _AGENT_TASK_HEADERS, _AGENT_TASK_ENDPOINT_CANDIDATES, _discover_agent_task_endpoint(), list_agent_tasks(), get_agent_task(), and self._agent_task_endpoint_cache — preserve assign_copilot_to_issue()
- [x] T016 [P] [US1] Clean solune/backend/src/services/copilot_polling/helpers.py: delete _get_agent_task_id() and _check_agent_task_status() functions
- [x] T017 [P] [US1] Clean solune/backend/src/services/copilot_polling/__init__.py: remove _check_agent_task_status from imports and exports
- [x] T018 [P] [US1] Clean solune/backend/src/services/copilot_polling/pipeline.py: remove "Fleet task failed" log messages and any fleet-related conditionals

**Checkpoint**: Classic dispatch is the sole code path — orchestrator has zero fleet references

---

## Phase 5: API & Frontend Cleanup — US4 (parallel with Phase 4)

**Purpose**: Remove fleet-specific fields from API responses and frontend type definitions

- [x] T019 [P] [US4] Clean solune/backend/src/api/workflow.py: remove agent_task_ids and dispatch_backend from response dict, delete _infer_dispatch_backend() function, remove FleetDispatchService import if present, remove conditional agent_task_ids pops
- [x] T020 [P] [US4] Remove dispatch_backend and agent_task_ids from PipelineStateInfo interface in solune/frontend/src/types/index.ts
- [x] T021 [P] [US4] Remove dispatch_backend and agent_task_ids fields from Zod schema in solune/frontend/src/services/schemas/pipeline.ts

**Checkpoint**: API responses and frontend types are fleet-free

---

## Phase 6: Test File Cleanup — US3 (depends on Phases 4 & 5)

**Purpose**: Remove fleet-specific assertions and fixtures from non-fleet test files while preserving all non-fleet test coverage

- [x] T022 [P] [US3] Remove fleet config schema validation tests from solune/backend/tests/unit/test_pipeline_config_schema.py
- [x] T023 [P] [US3] Remove fleet dispatch mocks, is_fleet_eligible assertions, and fleet-related fixtures from solune/backend/tests/unit/test_workflow_orchestrator.py
- [x] T024 [P] [US3] Remove dispatch_backend and agent_task_ids from response assertions in solune/backend/tests/unit/test_api_workflow.py
- [x] T025 [P] [US3] Remove fleet label assertions from solune/backend/tests/unit/test_issues.py
- [x] T026 [P] [US3] Remove _get_agent_task_id and _check_agent_task_status tests from solune/backend/tests/unit/test_helpers_polling.py
- [x] T027 [P] [US3] Remove agent_task_ids from state fixtures in solune/backend/tests/unit/test_pipeline_state_store.py
- [x] T028 [P] [US3] Remove fleet metadata Zod parsing test and agent_task_ids/dispatch_backend from test fixtures in solune/frontend/src/services/schemas/pipeline.test.ts

**Checkpoint**: All remaining tests are fleet-free and pass

---

## Phase 7: Documentation — US5 (parallel with Phases 4–6)

**Purpose**: Update architecture diagrams and documentation to reflect simplified system

- [x] T029 [P] [US5] Remove Fleet Dispatch node from Mermaid diagram in solune/docs/architectures/backend-components.mmd
- [x] T030 [P] [US5] Remove fleet-dispatch-pipelines references from plan.md (root-level)

**Checkpoint**: Documentation reflects the simplified architecture

---

## Phase 8: Polish & Verification

**Purpose**: Final validation — verify zero fleet references and all tests pass

- [x] T031 Run backend unit tests: `cd solune/backend && python -m pytest tests/unit/ -x -q` — verify all pass with no import errors
- [x] T032 [P] Run backend integration tests: `cd solune/backend && python -m pytest tests/integration/ -x -q` — verify no broken imports
- [x] T033 [P] Run frontend type check: `cd solune/frontend && npx tsc --noEmit` — verify zero type errors
- [x] T034 [P] Run frontend tests: `cd solune/frontend && npx vitest run` — verify schema tests pass
- [x] T035 Run codebase-wide fleet reference search: `grep -rn "fleet\|FleetDispatch\|fleet_dispatch\|fleet-dispatch\|agent_task_ids\|dispatch_backend" solune/ --exclude-dir=__pycache__ --exclude="CHANGELOG.md"` — verify zero matches (excluding specs/)
- [x] T036 Verify assign_copilot_to_issue() callers are intact: confirm solune/backend/src/services/app_plan_orchestrator.py and solune/backend/src/services/copilot_polling/auto_merge.py still import and call it
- [x] T037 Verify pipeline_orchestrator.py PIPELINE_STAGES constant returns hardcoded 11 legacy stages with no fleet dependency

**Checkpoint**: All verification gates pass — feature complete

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — establish baseline
- **Phase 2 (Delete Standalone)**: Depends on Phase 1 — all tasks in Phase 2 are parallel with each other
- **Phase 3 (Models/Config)**: Depends on Phase 2 — fleet service must be deleted before removing models it imported
- **Phase 4 (Orchestration)**: Depends on Phase 3 — fleet models must be removed before cleaning orchestrator imports
- **Phase 5 (API/Frontend)**: Can run in parallel with Phase 4 — no shared dependencies
- **Phase 6 (Tests)**: Depends on Phases 4 & 5 — source changes must be complete before fixing test expectations
- **Phase 7 (Docs)**: Can run in parallel with Phases 4, 5, and 6 — documentation is independent
- **Phase 8 (Verification)**: Depends on ALL prior phases — final validation

### User Story Mapping

- **US1 (Classic Path)**: T013, T014, T015, T016, T017, T018 — Phase 4
- **US2 (Dead Code Removal)**: T003–T012 — Phases 2 & 3
- **US3 (No Regression)**: T022–T028 — Phase 6, verified by T031–T037
- **US4 (API Cleanup)**: T019–T021 — Phase 5
- **US5 (Documentation)**: T029–T030 — Phase 7

### Parallel Opportunities

**Phase 2** (8 tasks): All T003–T010 are fully parallel — different files, zero dependencies.

**Phase 3** (2 tasks): T011 and T012 are parallel — different files (pipeline.py vs config.py).

**Phase 4** (6 tasks): T014–T018 are parallel with each other (different files). T013 is the largest task (orchestrator.py) and can also run in parallel since it touches a different file.

**Phase 5** (3 tasks): All T019–T021 are parallel — different files (workflow.py, index.ts, pipeline.ts). Phase 5 is also parallel with Phase 4.

**Phase 6** (7 tasks): All T022–T028 are parallel — different test files.

**Phase 7** (2 tasks): T029 and T030 are parallel. Phase 7 is parallel with Phases 4–6.

---

## Parallel Example: Maximum Concurrency at Phase 4–7

```
# These 4 phases can overlap:

# Phase 4 (all parallel with each other):
T013: Clean orchestrator.py
T014: Simplify pipeline_orchestrator.py
T015: Clean copilot.py
T016: Clean helpers.py
T017: Clean __init__.py
T018: Clean pipeline.py (copilot_polling)

# Phase 5 (parallel with Phase 4, all parallel with each other):
T019: Clean workflow.py
T020: Clean index.ts
T021: Clean pipeline.ts (Zod)

# Phase 7 (parallel with Phases 4 & 5):
T029: Update backend-components.mmd
T030: Update plan.md

# Phase 6 (after Phases 4 & 5, all parallel with each other):
T022–T028: Clean 7 test files
```

---

## Implementation Strategy

### MVP First (Phases 1–4)

1. Complete Phase 1: Establish green baseline
2. Complete Phase 2: Delete ~25 standalone files (all parallel)
3. Complete Phase 3: Remove fleet models and config functions
4. Complete Phase 4: Clean orchestrators — classic dispatch is now sole path
5. **STOP and VALIDATE**: Run `python -m pytest tests/unit/ -x -q` — expect some fleet-reference failures in tests but zero import errors in source
6. This delivers US1 (sole execution path) and US2 (dead code removed)

### Incremental Delivery

1. Phases 1–4 → US1 + US2 delivered (core removal)
2. Phase 5 → US4 delivered (API cleanup)
3. Phase 6 → US3 delivered (test cleanup, full green suite)
4. Phase 7 → US5 delivered (documentation)
5. Phase 8 → Full verification, all success criteria met

---

## Notes

- All Phase 2 deletions are safe to do in any order — they are leaf nodes with no importers
- The orchestrator (T013) is the most complex single task (~20+ fleet references to remove)
- assign_copilot_to_issue() MUST be preserved — verify after T015
- PIPELINE_STAGES constant (T014) should contain exactly 11 stages matching the legacy fallback
- Test cleanup (Phase 6) MUST wait for source changes — otherwise test imports will fail before the code they test is cleaned
