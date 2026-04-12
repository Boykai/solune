# Tasks: Fleet-Dispatch Agent Pipelines via GitHub CLI

**Input**: Design documents from `specs/001-fleet-dispatch-pipelines/`
**Prerequisites**: `specs/001-fleet-dispatch-pipelines/plan.md`, `specs/001-fleet-dispatch-pipelines/spec.md`, `specs/001-fleet-dispatch-pipelines/research.md`, `specs/001-fleet-dispatch-pipelines/data-model.md`, `specs/001-fleet-dispatch-pipelines/quickstart.md`, `specs/001-fleet-dispatch-pipelines/contracts/`

**Tests**: Include `pytest` unit/integration coverage plus shell-script smoke coverage because the plan explicitly requires parity, schema validation, and mocked CLI execution checks.

**Organization**: Tasks are grouped by user story so each increment can be implemented and validated independently once its dependencies are complete.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the shared CLI, helper, and fixture scaffolding used by every story.

- [ ] T001 Create the fleet dispatch CLI entrypoint scaffold in `solune/scripts/fleet-dispatch.sh`
- [ ] T002 [P] Create shared GitHub CLI and JSON helper scaffolding in `solune/scripts/lib/fleet_dispatch_common.sh`
- [ ] T003 [P] Create reusable mocked GitHub CLI fixture scaffolding in `solune/backend/tests/fixtures/fleet_dispatch/github_api_graphql_success.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared models, schema, and validation plumbing that block every user story.

**⚠️ CRITICAL**: Complete this phase before starting any user story work.

- [ ] T004 Extend fleet-dispatch configuration and dispatch-record models in `solune/backend/src/models/pipeline.py`
- [ ] T005 Implement typed config loading and parity helpers for fleet dispatch in `solune/backend/src/services/workflow_orchestrator/config.py`
- [ ] T006 [P] Add the runtime fleet-dispatch JSON Schema in `solune/scripts/pipelines/pipeline-config.schema.json`
- [ ] T007 [P] Add foundational schema and model coverage in `solune/backend/tests/unit/test_pipeline_config_schema.py`
- [ ] T008 Implement shared GraphQL headers, retry, and rate-limit helpers in `solune/scripts/lib/fleet_dispatch_common.sh`
- [ ] T009 [P] Add shared mocked `gh agent-task` polling fixtures in `solune/backend/tests/fixtures/fleet_dispatch/agent_task_list.json`

**Checkpoint**: Foundation ready — user story work can begin.

---

## Phase 3: User Story 1 - Dispatch All Pipeline Agents via CLI Script (Priority: P1) 🎯 MVP

**Goal**: Let an operator launch the full fleet-dispatch pipeline for a parent issue from one shell command with correct sub-issue creation, group ordering, and error-strategy handling.

**Independent Test**: Run `solune/scripts/fleet-dispatch.sh` against mocked `gh` responses and verify sub-issues are created, serial groups wait correctly, parallel groups dispatch together, and fail-fast/continue behavior matches the config.

### Tests for User Story 1

- [ ] T010 [P] [US1] Add serial-versus-parallel dispatch ordering coverage in `solune/backend/tests/unit/test_fleet_dispatch_cli.py`
- [ ] T011 [P] [US1] Add shell smoke coverage for sub-issue creation, resume locking, and error strategies in `solune/backend/tests/integration/test_fleet_dispatch_smoke.py`

### Implementation for User Story 1

- [ ] T012 [US1] Implement prerequisite validation, argument parsing, and dispatch bootstrap flow in `solune/scripts/fleet-dispatch.sh`
- [ ] T013 [US1] Implement parent-issue lock detection plus sub-issue create-or-resume flow in `solune/scripts/fleet-dispatch.sh`
- [ ] T014 [US1] Implement serial and parallel execution boundaries for ordered agent groups in `solune/scripts/fleet-dispatch.sh`
- [ ] T015 [US1] Implement GraphQL assignment calls with fail-fast and continue semantics in `solune/scripts/fleet-dispatch.sh`
- [ ] T016 [P] [US1] Implement parent/sub-issue labels and linkage body helpers in `solune/scripts/lib/fleet_dispatch_common.sh`

**Checkpoint**: User Story 1 delivers the MVP CLI dispatch path.

---

## Phase 4: User Story 2 - Standalone Pipeline Configuration (Priority: P1)

**Goal**: Extract the ordered fleet definition into a standalone JSON config that both the shell script and backend can load with matching behavior.

**Independent Test**: Validate the canonical JSON config against the runtime schema and verify backend loading reproduces the current four-group execution order and modes.

### Tests for User Story 2

- [ ] T017 [P] [US2] Add canonical fleet-config schema validation cases in `solune/backend/tests/unit/test_pipeline_config_schema.py`
- [ ] T018 [P] [US2] Add backend parity coverage for JSON-loaded group order and execution modes in `solune/backend/tests/unit/test_pipeline_orchestrator.py`

### Implementation for User Story 2

- [ ] T019 [US2] Extract the canonical four-group fleet definition into `solune/scripts/pipelines/fleet-dispatch.json`
- [ ] T020 [US2] Implement backend loading of the standalone fleet config in `solune/backend/src/services/workflow_orchestrator/config.py`
- [ ] T021 [US2] Align orchestrator fallback groups with the extracted JSON contract in `solune/backend/src/services/pipeline_orchestrator.py`

**Checkpoint**: User Story 2 makes the pipeline definition portable and shared.

---

## Phase 5: User Story 3 - Templated Custom Instructions (Priority: P2)

**Goal**: Render agent-specific custom instructions from file-based templates so CLI dispatch matches backend prompt behavior and falls back safely when a dedicated template is missing.

**Independent Test**: Render templates for known agents with fixture issue context and compare the output with backend prompt helpers plus fallback behavior for an unmapped agent.

### Tests for User Story 3

- [ ] T022 [P] [US3] Add prompt-equivalence coverage for rendered CLI templates versus backend helpers in `solune/backend/tests/unit/test_github_agents.py`
- [ ] T023 [P] [US3] Add template fallback and placeholder substitution coverage in `solune/backend/tests/unit/test_fleet_dispatch_templates.py`

### Implementation for User Story 3

- [ ] T024 [US3] Implement template rendering and missing-template fallback resolution in `solune/scripts/lib/fleet_dispatch_common.sh`
- [ ] T025 [P] [US3] Create fallback and Speckit agent templates in `solune/scripts/pipelines/templates/generic.md`, `solune/scripts/pipelines/templates/speckit.specify.md`, `solune/scripts/pipelines/templates/speckit.plan.md`, `solune/scripts/pipelines/templates/speckit.tasks.md`, `solune/scripts/pipelines/templates/speckit.analyze.md`, and `solune/scripts/pipelines/templates/speckit.implement.md`
- [ ] T026 [P] [US3] Create QA and operations agent templates in `solune/scripts/pipelines/templates/quality-assurance.md`, `solune/scripts/pipelines/templates/tester.md`, `solune/scripts/pipelines/templates/copilot-review.md`, `solune/scripts/pipelines/templates/judge.md`, `solune/scripts/pipelines/templates/linter.md`, and `solune/scripts/pipelines/templates/devops.md`
- [ ] T027 [US3] Wire template references and fallback markers into `solune/scripts/pipelines/fleet-dispatch.json`

**Checkpoint**: User Story 3 restores prompt quality parity for CLI-driven assignments.

---

## Phase 6: User Story 4 - Monitor Pipeline Progress and Completion (Priority: P2)

**Goal**: Provide near-real-time pipeline status, timeout visibility, and a final summary for operators running fleet dispatches.

**Independent Test**: Run a mocked dispatch, poll status through the CLI flow, and confirm queued/in-progress/completed/failed/timed-out states plus final summary output match known fixture transitions.

### Tests for User Story 4

- [ ] T028 [P] [US4] Add status polling and timeout detection coverage in `solune/backend/tests/unit/test_fleet_dispatch_monitoring.py`
- [ ] T029 [P] [US4] Add CLI monitor-mode smoke coverage in `solune/backend/tests/integration/test_fleet_dispatch_monitoring.py`

### Implementation for User Story 4

- [ ] T030 [US4] Implement dispatch-record serialization and status aggregation in `solune/scripts/fleet-dispatch.sh`
- [ ] T031 [US4] Implement monitor output for queued, in-progress, completed, and failed agents in `solune/scripts/fleet-dispatch.sh`
- [ ] T032 [US4] Implement stuck-agent timeout warnings and final elapsed-time summary output in `solune/scripts/fleet-dispatch.sh`

**Checkpoint**: User Story 4 gives operators a usable monitoring loop and completion summary.

---

## Phase 7: User Story 5 - Dispatch a Single Agent Ad-Hoc (Priority: P3)

**Goal**: Re-dispatch one named agent against an existing sub-issue without rerunning the entire fleet.

**Independent Test**: Invoke the CLI with `--agent`, `--sub-issue`, and `--retry` against mocked GitHub responses and verify only the target agent is unassigned/reassigned with the expected payload.

### Tests for User Story 5

- [ ] T033 [P] [US5] Add single-agent retry and reassign coverage in `solune/backend/tests/integration/test_fleet_dispatch_retry.py`
- [ ] T034 [P] [US5] Add retry argument parsing and override option coverage in `solune/backend/tests/unit/test_fleet_dispatch_cli.py`

### Implementation for User Story 5

- [ ] T035 [US5] Implement `--agent`, `--sub-issue`, and `--retry` CLI flow in `solune/scripts/fleet-dispatch.sh`
- [ ] T036 [US5] Implement Copilot unassign-before-retry plus override template/model handling in `solune/scripts/lib/fleet_dispatch_common.sh`
- [ ] T037 [US5] Implement single-agent redispatch status updates and audit output in `solune/scripts/fleet-dispatch.sh`

**Checkpoint**: User Story 5 supports targeted retries and ad-hoc redispatch.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Finish cross-story validation, docs, and hardening.

- [ ] T038 [P] Validate fleet-dispatch contract assets in `solune/scripts/validate-contracts.sh`
- [ ] T039 [P] Document fleet dispatch operator commands and test entrypoints in `solune/README.md` and `solune/docs/testing.md`
- [ ] T040 [P] Refresh runnable monitor and retry examples in `specs/001-fleet-dispatch-pipelines/quickstart.md`
- [ ] T041 Harden help text, exit codes, and troubleshooting output in `solune/scripts/fleet-dispatch.sh`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 → Phase 2**: Setup must complete before foundational modeling and schema work.
- **Phase 2 → Phases 3-7**: Foundational work blocks all user stories because every story relies on shared models, schema validation, shell helpers, and polling fixtures.
- **Phase 8**: Polish starts after all desired user stories are complete.

### User Story Dependencies

- **US1**: Starts after Phase 2 and is the MVP path.
- **US2**: Starts after Phase 2 and can proceed alongside US1, but T020-T021 must land before shared backend parity is considered complete.
- **US3**: Starts after Phase 2; T027 depends on T019 so template references point at the canonical config.
- **US4**: Starts after US1 because monitoring depends on real dispatch records and polling flow from T012-T015.
- **US5**: Starts after US1; T036-T037 also depend on the monitoring/state plumbing from US4 and the template rendering logic from US3.

### Recommended Execution Order

1. Finish **Phase 1: Setup**
2. Finish **Phase 2: Foundational**
3. Deliver **US1** for the CLI MVP
4. Deliver **US2** to make the pipeline definition the shared source of truth
5. Deliver **US3** to restore prompt parity via templates
6. Deliver **US4** to add operator monitoring and summaries
7. Deliver **US5** to support targeted retries
8. Finish **Phase 8: Polish**

---

## Parallel Examples per Story

### User Story 1

```bash
# Write the US1 verification coverage in parallel:
T010 solune/backend/tests/unit/test_fleet_dispatch_cli.py
T011 solune/backend/tests/integration/test_fleet_dispatch_smoke.py

# After T008, helper work can proceed alongside script flow work:
T016 solune/scripts/lib/fleet_dispatch_common.sh
T012 solune/scripts/fleet-dispatch.sh
```

### User Story 2

```bash
# Validate schema and parity in parallel:
T017 solune/backend/tests/unit/test_pipeline_config_schema.py
T018 solune/backend/tests/unit/test_pipeline_orchestrator.py
```

### User Story 3

```bash
# Build the two template sets in parallel:
T025 solune/scripts/pipelines/templates/
T026 solune/scripts/pipelines/templates/

# Add the two test files in parallel:
T022 solune/backend/tests/unit/test_github_agents.py
T023 solune/backend/tests/unit/test_fleet_dispatch_templates.py
```

### User Story 4

```bash
# Monitoring validation can be split across unit and smoke coverage:
T028 solune/backend/tests/unit/test_fleet_dispatch_monitoring.py
T029 solune/backend/tests/integration/test_fleet_dispatch_monitoring.py
```

### User Story 5

```bash
# Retry coverage can be written in parallel before implementation:
T033 solune/backend/tests/integration/test_fleet_dispatch_retry.py
T034 solune/backend/tests/unit/test_fleet_dispatch_cli.py
```

---

## Implementation Strategy

### MVP First

1. Complete **Phase 1: Setup**
2. Complete **Phase 2: Foundational**
3. Complete **US1**
4. Validate the mocked full-dispatch flow end to end
5. Demo the CLI MVP before expanding into shared-config parity and monitoring

### Incremental Delivery

1. **US1** delivers the first usable CLI dispatch path
2. **US2** removes hard-coded fleet definitions and locks in shared config parity
3. **US3** upgrades dispatch quality with file-based prompt templates
4. **US4** adds production-friendly monitoring and summaries
5. **US5** shortens recovery cycles with targeted agent retries

### Parallel Team Strategy

1. One engineer finishes **Setup + Foundational**
2. Then split by dependency-safe track:
   - Engineer A: **US1**, then **US4**
   - Engineer B: **US2**, then **US3**
   - Engineer C: **Phase 8 documentation/contract updates first**, then **US5** after US3 and US4 complete

---

## Notes

- All task lines follow the required checklist format with sequential IDs, optional `[P]` markers, and `[USx]` labels only inside story phases.
- Every task points to an exact repository path so an implementation agent can act without additional clarification.
- Test tasks are included because the feature plan explicitly calls for `pytest` coverage and shell-script smoke validation.
