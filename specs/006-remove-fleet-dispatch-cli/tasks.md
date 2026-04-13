# Tasks: Remove Fleet Dispatch & Copilot CLI Code

**Feature**: `006-remove-fleet-dispatch-cli` | **Branch**: `006-remove-fleet-dispatch-cli`
**Input**: Design documents from `/home/runner/work/solune/solune/specs/006-remove-fleet-dispatch-cli/` plus `/home/runner/work/solune/solune/spec.md`
**Prerequisites**: `/home/runner/work/solune/solune/plan.md` ✅, `/home/runner/work/solune/solune/spec.md` ✅, `/home/runner/work/solune/solune/specs/006-remove-fleet-dispatch-cli/research.md` ✅, `/home/runner/work/solune/solune/specs/006-remove-fleet-dispatch-cli/data-model.md` ✅, `/home/runner/work/solune/solune/specs/006-remove-fleet-dispatch-cli/quickstart.md` ✅, `/home/runner/work/solune/solune/specs/006-remove-fleet-dispatch-cli/contracts/removal-contract.yaml` ✅

**Tests**: Included — spec.md success criteria SC-002 through SC-005 require backend/unit/integration regression runs, frontend schema/type validation, and final zero-reference verification.

**Organization**: Tasks are grouped by user story in spec.md priority order (P1 → P2 → P3). Setup and Foundational phases contain shared prerequisites; every user story phase carries a `[US#]` label and ends with an independent validation task.

## Format: `- [ ] T### [P?] [US#?] Description with file path`

- **[P]**: Can run in parallel (different files or independent validation commands)
- **[US#]**: Required on user story phase tasks only
- **No [US#]**: Setup, Foundational, and Polish phases only
- Every task below includes an exact absolute repository path or an executable validation command

## Path Conventions

- **Repository root**: `/home/runner/work/solune/solune`
- **Backend root**: `/home/runner/work/solune/solune/solune/backend`
- **Frontend root**: `/home/runner/work/solune/solune/solune/frontend`
- **Docs root**: `/home/runner/work/solune/solune/solune/docs`
- **Feature docs**: `/home/runner/work/solune/solune/specs/006-remove-fleet-dispatch-cli`

---

## Phase 1: Setup (Environment and Scope Audit)

**Purpose**: Prepare the backend/frontend workspaces and confirm the exact removal surface from the approved design documents before touching code.

- [ ] T001 Sync backend development dependencies in `/home/runner/work/solune/solune/solune/backend` with `cd /home/runner/work/solune/solune/solune/backend && uv sync --locked --extra dev`
- [ ] T002 [P] Install frontend dependencies in `/home/runner/work/solune/solune/solune/frontend` with `cd /home/runner/work/solune/solune/solune/frontend && npm ci`
- [ ] T003 [P] Audit `/home/runner/work/solune/solune/plan.md`, `/home/runner/work/solune/solune/spec.md`, and `/home/runner/work/solune/solune/specs/006-remove-fleet-dispatch-cli/{research.md,data-model.md,quickstart.md,contracts/removal-contract.yaml}` to confirm the delete/modify inventory before implementation

**Checkpoint**: Tooling is ready and the exact backend, frontend, docs, scripts, and test paths are confirmed.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Remove the shared fleet artifacts and shared state/config primitives that block every user story.

**⚠️ CRITICAL**: No user story work should start until this phase is complete because all later edits assume fleet assets, models, and state fields are already gone.

- [ ] T004 Delete the standalone fleet artifacts at `/home/runner/work/solune/solune/solune/scripts/fleet-dispatch.sh`, `/home/runner/work/solune/solune/solune/scripts/lib/fleet_dispatch_common.sh`, `/home/runner/work/solune/solune/solune/scripts/pipelines/fleet-dispatch.json`, `/home/runner/work/solune/solune/solune/scripts/pipelines/pipeline-config.schema.json`, `/home/runner/work/solune/solune/solune/scripts/pipelines/templates/`, `/home/runner/work/solune/solune/solune/cli-plugin/`, and `/home/runner/work/solune/solune/solune/backend/src/services/fleet_dispatch.py`, then remove `/home/runner/work/solune/solune/solune/scripts/pipelines/` if it is empty
- [ ] T005 Remove all `FleetDispatch*` classes from `/home/runner/work/solune/solune/solune/backend/src/models/pipeline.py` while preserving `PipelineAgentNode`, `ExecutionGroup`, `PipelineStage`, `PipelineConfig`, and every non-fleet model in the file
- [ ] T006 Remove `_DEFAULT_FLEET_DISPATCH_CONFIG`, `get_default_fleet_dispatch_config_path()`, `load_fleet_dispatch_config()`, and `build_pipeline_stages_from_fleet_config()` from `/home/runner/work/solune/solune/solune/backend/src/services/workflow_orchestrator/config.py`
- [ ] T007 Remove the fleet-only `agent_task_ids` field from `/home/runner/work/solune/solune/solune/backend/src/services/workflow_orchestrator/models.py` and `/home/runner/work/solune/solune/solune/backend/src/services/pipeline_state_store.py` so later orchestration, API, and frontend work no longer depend on fleet state

**Checkpoint**: The repository no longer depends on fleet files, fleet config loaders, FleetDispatch models, or fleet-specific pipeline state.

---

## Phase 3: User Story 1 - Issue Dispatch Continues via Classic Path (Priority: P1) 🎯 MVP

**Goal**: Make the classic dispatch path the only orchestration path so issue assignment, prompt formatting, and pipeline progression continue to work without fleet checks or task tracking.

**Independent Test**: Trigger or simulate a pipeline dispatch and confirm the classic prompt formatting path runs, standard Copilot assignment remains intact, and no `agent_task_ids` or fleet branch behavior appears in state or logs.

- [ ] T008 [US1] Simplify `/home/runner/work/solune/solune/solune/backend/src/services/workflow_orchestrator/orchestrator.py` to remove `FleetDispatchService`, all `is_fleet_eligible()` branches, fleet sub-issue reuse/label logic, fleet logging, and task-ID state writes while keeping `format_issue_context_as_prompt()` plus classic Copilot assignment as the sole dispatch flow
- [ ] T009 [P] [US1] Remove fleet task polling helpers, imports, and fleet-task failure logging from `/home/runner/work/solune/solune/solune/backend/src/services/copilot_polling/helpers.py` and `/home/runner/work/solune/solune/solune/backend/src/services/copilot_polling/pipeline.py`
- [ ] T010 [P] [US1] Update classic-path regression coverage in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_workflow_orchestrator.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_helpers_polling.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_issues.py`, and `/home/runner/work/solune/solune/solune/backend/tests/unit/test_pipeline_state_store.py` so assertions cover classic-only dispatch and the absence of fleet task tracking
- [ ] T011 [US1] Run targeted classic-path regression validation with `cd /home/runner/work/solune/solune/solune/backend && uv run pytest tests/unit/test_workflow_orchestrator.py tests/unit/test_helpers_polling.py tests/unit/test_issues.py tests/unit/test_pipeline_state_store.py -q`

**Checkpoint**: Classic dispatch is the only remaining orchestration path and is independently regression-tested.

---

## Phase 4: User Story 2 - Codebase Is Free of Fleet Dispatch Artifacts (Priority: P1)

**Goal**: Delete the remaining fleet-only test assets and scrub repository paths that should no longer exist after the shared cleanup.

**Independent Test**: Search the repository for `fleet`, `FleetDispatch`, `fleet_dispatch`, `fleet-dispatch`, `agent_task_ids`, and `dispatch_backend` and confirm zero matches outside explicitly allowed historical files such as `CHANGELOG.md`.

- [ ] T012 [P] [US2] Delete the fleet-specific test assets at `/home/runner/work/solune/solune/solune/backend/tests/fleet_dispatch_harness.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_fleet_dispatch_cli.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_fleet_dispatch_service.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_fleet_dispatch_templates.py`, `/home/runner/work/solune/solune/solune/backend/tests/unit/test_fleet_parity.py`, `/home/runner/work/solune/solune/solune/backend/tests/integration/test_fleet_dispatch_smoke.py`, and `/home/runner/work/solune/solune/solune/backend/tests/integration/test_fleet_app_dispatch.py`
- [ ] T013 [P] [US2] Remove fleet-specific schema/assertion coverage from `/home/runner/work/solune/solune/solune/backend/tests/unit/test_pipeline_config_schema.py` so shared tests no longer expect deleted fleet config, schema, or template files
- [ ] T014 [US2] Remove any now-empty directories left by T004 and T012 (especially `/home/runner/work/solune/solune/solune/scripts/pipelines/`) and run `grep -rn "fleet\|FleetDispatch\|fleet_dispatch\|fleet-dispatch\|agent_task_ids\|dispatch_backend" /home/runner/work/solune/solune/solune --exclude-dir=node_modules --exclude=CHANGELOG.md` to confirm the codebase is fleet-free

**Checkpoint**: The repository tree and search index are clear of fleet artifacts.

---

## Phase 5: User Story 3 - All Existing Tests Pass After Removal (Priority: P1)

**Goal**: Align shared tests with the fleet-free implementation and prove that backend + frontend validation still passes after the deletion-heavy refactor.

**Independent Test**: Run backend unit tests, backend integration tests, frontend type checking, and frontend schema tests with zero import errors or regressions.

- [ ] T015 [P] [US3] Update fleet-sensitive shared assertions in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_workflow.py` and `/home/runner/work/solune/solune/solune/frontend/src/services/schemas/pipeline.test.ts` so they validate the fleet-free API/state contract instead of removed fields
- [ ] T016 [US3] Run the backend unit regression suite with `cd /home/runner/work/solune/solune/solune/backend && uv run pytest tests/unit/ -x -q`
- [ ] T017 [US3] Run the backend integration regression suite with `cd /home/runner/work/solune/solune/solune/backend && uv run pytest tests/integration/ -x -q`
- [ ] T018 [US3] Run frontend validation with `cd /home/runner/work/solune/solune/solune/frontend && npx tsc --noEmit && npx vitest run`

**Checkpoint**: The full required regression matrix from the spec passes after fleet removal.

---

## Phase 6: User Story 4 - Pipeline Orchestration Uses Hardcoded Legacy Stages (Priority: P2)

**Goal**: Make the hardcoded legacy stages the only stage-resolution path so pipeline launches no longer depend on fleet configuration files.

**Independent Test**: Inspect or execute pipeline stage resolution and confirm `_default_pipeline_stages()` returns the hardcoded legacy stages directly without loading any fleet config file.

- [ ] T019 [US4] Simplify `/home/runner/work/solune/solune/solune/backend/src/services/pipeline_orchestrator.py` so `_default_pipeline_stages()` returns the hardcoded legacy stage list directly and no fleet config imports remain
- [ ] T020 [P] [US4] Update stage-resolution regression coverage in `/home/runner/work/solune/solune/solune/backend/tests/unit/test_pipeline_config_schema.py` and `/home/runner/work/solune/solune/solune/backend/tests/unit/test_workflow_orchestrator.py` so the tests assert a fleet-free, hardcoded stage source
- [ ] T021 [US4] Run targeted stage validation with `cd /home/runner/work/solune/solune/solune/backend && uv run pytest tests/unit/test_pipeline_config_schema.py tests/unit/test_workflow_orchestrator.py -q`

**Checkpoint**: Stage resolution is deterministic and fleet-config-independent.

---

## Phase 7: User Story 5 - Shared Functions Remain Available to Non-Fleet Callers (Priority: P2)

**Goal**: Remove fleet-exclusive Copilot helpers without breaking `assign_copilot_to_issue()` for the app-plan and auto-merge flows.

**Independent Test**: Verify `assign_copilot_to_issue()` remains importable from its existing call sites and the removed agent-task helper methods are no longer present.

- [ ] T022 [US5] Remove `list_agent_tasks()`, `get_agent_task()`, and `_discover_agent_task_endpoint()` from `/home/runner/work/solune/solune/solune/backend/src/services/github_projects/copilot.py` while preserving `assign_copilot_to_issue()`
- [ ] T023 [P] [US5] Verify `/home/runner/work/solune/solune/solune/backend/src/services/app_plan_orchestrator.py` and `/home/runner/work/solune/solune/solune/backend/src/services/auto_merge.py` still import or call only `assign_copilot_to_issue()` after T022, adjusting those files only if stale fleet-only references remain
- [ ] T024 [US5] Run backend type validation for the preserved Copilot callers with `cd /home/runner/work/solune/solune/solune/backend && uv run pyright src/`

**Checkpoint**: Shared Copilot assignment behavior is preserved and fleet-only helper APIs are gone.

---

## Phase 8: User Story 6 - API Responses No Longer Contain Fleet Fields (Priority: P2)

**Goal**: Remove fleet-only API/state fields from the backend response contract and keep frontend parsing aligned with the simplified payload.

**Independent Test**: Request workflow state and verify `dispatch_backend` and `agent_task_ids` are absent from the response and from the frontend schema/types that parse it.

- [ ] T025 [US6] Remove `FleetDispatchService`, `_infer_dispatch_backend()`, `dispatch_backend`, and `agent_task_ids` handling from `/home/runner/work/solune/solune/solune/backend/src/api/workflow.py`
- [ ] T026 [P] [US6] Remove `agent_task_ids` and `dispatch_backend` from `/home/runner/work/solune/solune/solune/frontend/src/types/index.ts` and `/home/runner/work/solune/solune/solune/frontend/src/services/schemas/pipeline.ts`
- [ ] T027 [P] [US6] Update `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_workflow.py` and `/home/runner/work/solune/solune/solune/frontend/src/services/schemas/pipeline.test.ts` to match `/home/runner/work/solune/solune/specs/006-remove-fleet-dispatch-cli/contracts/removal-contract.yaml`
- [ ] T028 [US6] Run API/schema regression validation with `cd /home/runner/work/solune/solune/solune/backend && uv run pytest tests/unit/test_api_workflow.py -q && cd /home/runner/work/solune/solune/solune/frontend && npx vitest run src/services/schemas/pipeline.test.ts`

**Checkpoint**: The workflow API contract and frontend schema/types no longer expose fleet metadata.

---

## Phase 9: User Story 7 - Documentation Reflects Simplified Architecture (Priority: P3)

**Goal**: Update architecture and planning docs so they no longer describe Fleet Dispatch as a current component or reference obsolete fleet-dispatch-pipelines content.

**Independent Test**: Review the updated diagram and plan text and confirm Fleet Dispatch and fleet-dispatch-pipelines references are gone from the targeted docs.

- [ ] T029 [US7] Update `/home/runner/work/solune/solune/solune/docs/architectures/backend-components.mmd` to remove the Fleet Dispatch component and regenerate diagrams with `cd /home/runner/work/solune/solune/solune && ./scripts/generate-diagrams.sh`
- [ ] T030 [P] [US7] Update `/home/runner/work/solune/solune/plan.md` and `/home/runner/work/solune/solune/specs/006-remove-fleet-dispatch-cli/plan.md` to remove any remaining `fleet-dispatch-pipelines` references while preserving the rest of the plan narrative
- [ ] T031 [US7] Validate documentation cleanup with `grep -n "Fleet Dispatch\|fleet-dispatch-pipelines" /home/runner/work/solune/solune/solune/docs/architectures/backend-components.mmd /home/runner/work/solune/solune/plan.md /home/runner/work/solune/solune/specs/006-remove-fleet-dispatch-cli/plan.md`

**Checkpoint**: The docs describe only the simplified, fleet-free architecture.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Run the final validation bundle that spans every user story and confirms all success criteria before merge.

- [ ] T032 Run backend lint and format validation with `cd /home/runner/work/solune/solune/solune/backend && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/`
- [ ] T033 [P] Run the final backend validation bundle with `cd /home/runner/work/solune/solune/solune/backend && uv run pytest tests/unit/ -x -q && uv run pytest tests/integration/ -x -q && uv run pyright src/`
- [ ] T034 [P] Run the final frontend validation bundle with `cd /home/runner/work/solune/solune/solune/frontend && npx tsc --noEmit && npx vitest run`
- [ ] T035 [P] Verify the preserved-caller and stage invariants with `grep -n "assign_copilot_to_issue" /home/runner/work/solune/solune/solune/backend/src/services/app_plan_orchestrator.py /home/runner/work/solune/solune/solune/backend/src/services/auto_merge.py` and by inspecting `/home/runner/work/solune/solune/solune/backend/src/services/pipeline_orchestrator.py` for the hardcoded `_default_pipeline_stages()` definition
- [ ] T036 [P] Run the final zero-reference sweep with `grep -rn "fleet\|FleetDispatch\|fleet_dispatch\|fleet-dispatch\|agent_task_ids\|dispatch_backend" /home/runner/work/solune/solune/solune --exclude-dir=node_modules --exclude=CHANGELOG.md`

**Checkpoint**: All success criteria and regression gates have been satisfied across backend, frontend, docs, and repository cleanup.

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 (Setup)
  -> Phase 2 (Foundational / blocking cleanup)
      -> Phase 3 (US1 classic dispatch MVP)
          -> Phase 4 (US2 zero-artifact cleanup)
              -> Phase 5 (US3 regression matrix)
                  -> Phase 6 (US4 hardcoded stages)
                      -> Phase 7 (US5 preserved Copilot assignment)
                          -> Phase 8 (US6 fleet-free API contract)
                              -> Phase 9 (US7 docs cleanup)
                                  -> Final Phase (cross-cutting validation)
```

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2; establishes the classic-only orchestration MVP.
- **US2 (P1)**: Starts after Phase 2 and should complete before the final zero-reference sweep.
- **US3 (P1)**: Depends on US1, US2, and US6 so shared tests match the final backend/frontend contracts.
- **US4 (P2)**: Starts after Phase 2; should complete before final stage-invariant validation.
- **US5 (P2)**: Starts after Phase 2; should complete before final pyright and caller verification.
- **US6 (P2)**: Depends on Phase 2 and should finish before US3’s full regression run.
- **US7 (P3)**: Can start after US2/US4/US6 because the docs should describe the final fleet-free system.

### Within Each User Story

- Shared deletions/models/config/state cleanup happen first in Phase 2.
- Source edits precede test updates in every story.
- Validation commands close each user story before the next dependent story begins.
- Final Phase reruns the combined validation matrix after all story work is complete.

### Parallel Opportunities

- T002 and T003 can run in parallel during setup.
- T009 and T010 can run in parallel once T008’s orchestration scope is understood.
- T012 and T013 can run in parallel because they touch different files.
- T015 can run in parallel with T016/T017/T018 preparation, but the full test matrix should execute after all shared assertions are updated.
- T020, T023, T026, T027, and T030 each touch separate files and can be split across different implementers.
- T033 through T036 are independent final validation tasks and can run in parallel on separate workers.

---

## Parallel Execution Examples Per Story

### US1 Parallel Example

```bash
Task: "T009 Remove fleet polling helpers in /home/runner/work/solune/solune/solune/backend/src/services/copilot_polling/helpers.py and /home/runner/work/solune/solune/solune/backend/src/services/copilot_polling/pipeline.py"
Task: "T010 Update classic-path regression coverage in /home/runner/work/solune/solune/solune/backend/tests/unit/test_workflow_orchestrator.py, /home/runner/work/solune/solune/solune/backend/tests/unit/test_helpers_polling.py, /home/runner/work/solune/solune/solune/backend/tests/unit/test_issues.py, and /home/runner/work/solune/solune/solune/backend/tests/unit/test_pipeline_state_store.py"
```

### US2 Parallel Example

```bash
Task: "T012 Delete fleet-specific backend test files under /home/runner/work/solune/solune/solune/backend/tests/"
Task: "T013 Remove fleet expectations from /home/runner/work/solune/solune/solune/backend/tests/unit/test_pipeline_config_schema.py"
```

### US3 Parallel Example

```bash
Task: "T016 Run backend unit regression in /home/runner/work/solune/solune/solune/backend"
Task: "T018 Run frontend type/schema validation in /home/runner/work/solune/solune/solune/frontend"
```

### US4 Parallel Example

```bash
Task: "T019 Simplify /home/runner/work/solune/solune/solune/backend/src/services/pipeline_orchestrator.py"
Task: "T020 Update stage regression coverage in /home/runner/work/solune/solune/solune/backend/tests/unit/test_pipeline_config_schema.py and /home/runner/work/solune/solune/solune/backend/tests/unit/test_workflow_orchestrator.py"
```

### US5 Parallel Example

```bash
Task: "T022 Remove fleet-only helper methods from /home/runner/work/solune/solune/solune/backend/src/services/github_projects/copilot.py"
Task: "T023 Verify preserved assign_copilot_to_issue() callers in /home/runner/work/solune/solune/solune/backend/src/services/app_plan_orchestrator.py and /home/runner/work/solune/solune/solune/backend/src/services/auto_merge.py"
```

### US6 Parallel Example

```bash
Task: "T026 Remove fleet fields from /home/runner/work/solune/solune/solune/frontend/src/types/index.ts and /home/runner/work/solune/solune/solune/frontend/src/services/schemas/pipeline.ts"
Task: "T027 Update API/schema contract tests in /home/runner/work/solune/solune/solune/backend/tests/unit/test_api_workflow.py and /home/runner/work/solune/solune/solune/frontend/src/services/schemas/pipeline.test.ts"
```

### US7 Parallel Example

```bash
Task: "T029 Update /home/runner/work/solune/solune/solune/docs/architectures/backend-components.mmd and regenerate diagrams"
Task: "T030 Remove fleet-dispatch-pipelines references from /home/runner/work/solune/solune/plan.md and /home/runner/work/solune/solune/specs/006-remove-fleet-dispatch-cli/plan.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup).
2. Complete Phase 2 (Foundational).
3. Complete Phase 3 (US1 classic-only orchestration).
4. Validate T011 before starting broader cleanup.
5. Demo or merge the classic-path-preservation MVP once dispatch is proven stable.

### Incremental Delivery

1. Finish Setup + Foundational to remove shared blockers.
2. Deliver US1 to lock in classic dispatch behavior.
3. Deliver US2 to eliminate remaining fleet artifacts and zero-reference drift.
4. Deliver US6 before US3 so API/schema tests reflect the final contract.
5. Deliver US3, US4, US5, and US7, then run the Final Phase validation bundle.

### Parallel Team Strategy

1. Engineer A: US1 + US5 backend orchestration/Copilot cleanup.
2. Engineer B: US2 + US4 repository cleanup and stage simplification.
3. Engineer C: US6 + US7 API/frontend/docs cleanup.
4. Once those converge, any engineer can execute US3 and the Final Phase validation bundle.

---

## Notes

- [P] tasks touch different files or run independent validation commands.
- Every user story phase maps directly to the user stories in `/home/runner/work/solune/solune/spec.md`.
- The contract file `/home/runner/work/solune/solune/specs/006-remove-fleet-dispatch-cli/contracts/removal-contract.yaml` maps specifically to US6.
- The removed model inventory in `/home/runner/work/solune/solune/specs/006-remove-fleet-dispatch-cli/data-model.md` is implemented primarily in Phase 2.
- The quickstart verification commands in `/home/runner/work/solune/solune/specs/006-remove-fleet-dispatch-cli/quickstart.md` are preserved as executable regression tasks in US3 and the Final Phase.
