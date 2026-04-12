# Tasks: Fleet-Dispatch Agent Pipelines via GitHub CLI

**Input**: Design documents from `plan.md`, `spec.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/`
**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `research.md`, `data-model.md`, `contracts/`

**Tests**: Tests are explicitly included — `bats` for shell scripts (per plan.md Phase 1) and `pytest` for the Python extraction script (per plan.md Phase 2). The constitution check (Section IV) confirms test inclusion for this critical infrastructure component.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Shell scripts**: `solune/scripts/`
- **Shell script tests**: `solune/scripts/tests/`
- **Pipeline config**: `solune/config/`
- **Instruction templates**: `solune/config/templates/`
- **Backend services**: `solune/backend/src/services/pipelines/`
- **Backend agent code**: `solune/backend/src/services/github_projects/agents.py`
- **Backend tests**: `solune/backend/tests/unit/`
- **Frontend presets**: `solune/frontend/src/data/preset-pipelines.ts`
- **Contracts/schemas**: `contracts/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the directory structure, install test tooling, and verify prerequisites before writing any implementation code.

- [ ] T001 Create directory structure per implementation plan: `solune/config/`, `solune/config/templates/`, `solune/scripts/tests/`
- [ ] T002 [P] Add `bats` test framework as a dev dependency — create `solune/scripts/tests/bats-setup.sh` with install instructions and test helper bootstrap
- [ ] T003 [P] Copy JSON Schema from `contracts/pipeline-config-schema.json` into `solune/config/pipeline-config-schema.json` for runtime validation by the dispatch script

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core shell utilities and shared functions that ALL user stories depend on. These are extracted into a library file sourced by the main dispatch script.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T004 Create shell library `solune/scripts/lib/fleet-common.sh` — shared functions: `log_info()`, `log_error()`, `log_verbose()`, `die()`, `require_cmd()` (validates `gh`, `jq`, `envsubst` exist), `check_gh_auth()` (runs `gh auth status`), `json_escape()` (escapes strings for JSON embedding)
- [ ] T005 [P] Create shell library `solune/scripts/lib/fleet-state.sh` — state file management functions: `init_state_file()` (creates `fleet-state.json` with run_id UUID, repo, parent_issue, base_ref, pipeline_preset, started_at, status=running, agents=[]), `update_agent_state()` (updates a single agent record by slug), `finalize_state()` (sets completed_at and derives overall status from agent statuses), `atomic_write()` (write to temp file then `mv` for atomicity)
- [ ] T006 [P] Create shell library `solune/scripts/lib/fleet-graphql.sh` — GraphQL functions: `resolve_repo_node_id()` (queries GitHub for the repository node ID), `resolve_copilot_bot_id()` (queries for the Copilot bot user node ID), `resolve_issue_node_id()` (queries for an issue's node ID given its number), `dispatch_agent()` (constructs and sends the `addAssigneesToAssignable` mutation with full `agentAssignment` payload and `GraphQL-Features` header)
- [ ] T007 Create script skeleton `solune/scripts/fleet-dispatch.sh` — argument parsing (`--repo`, `--parent-issue`, `--config`, `--preset`, `--base-ref`, `--model`, `--state-dir`, `--dry-run`, `--verbose`), sources `lib/fleet-common.sh`, `lib/fleet-state.sh`, `lib/fleet-graphql.sh`; validates all required args and prerequisites; exits with code 2 on invalid args

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 — CLI Fleet Dispatch with Parallel Agent Groups (Priority: P1) 🎯 MVP

**Goal**: A platform operator can run `fleet-dispatch.sh` to dispatch a full agent pipeline — sub-issues are created, agents are dispatched via GraphQL, parallel groups run concurrently, serial groups run sequentially, and a state file tracks progress.

**Independent Test**: Run `fleet-dispatch.sh --dry-run` with a test pipeline config and verify it produces the correct dispatch plan (sub-issue creation order, parallel/serial group handling) without making API calls.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T008 [P] [US1] Create bats test file `solune/scripts/tests/fleet-dispatch.bats` — test argument validation: exits code 2 when `--repo` missing, exits code 2 when `--parent-issue` missing, exits code 2 when `--config` points to nonexistent file, exits code 2 when `--preset` not found in config
- [ ] T009 [P] [US1] Add bats tests for prerequisite validation in `solune/scripts/tests/fleet-dispatch.bats` — test `require_cmd` exits when `gh` not found, test `check_gh_auth` exits when not authenticated (mock `gh auth status` failure)
- [ ] T010 [P] [US1] Create bats test file `solune/scripts/tests/fleet-common.bats` — unit tests for `log_info`, `log_error`, `log_verbose`, `die`, `require_cmd`, `json_escape` functions in `solune/scripts/lib/fleet-common.sh`
- [ ] T011 [P] [US1] Create bats test file `solune/scripts/tests/fleet-state.bats` — unit tests for `init_state_file` (verify JSON structure matches FleetState schema from `data-model.md`), `update_agent_state`, `finalize_state` (verify status derivation: all completed → completed, some failed → partial_failure, all failed → failed), `atomic_write` (verify temp file then mv)
- [ ] T012 [P] [US1] Create bats test file `solune/scripts/tests/fleet-graphql.bats` — unit tests for `dispatch_agent` (verify GraphQL mutation structure, verify `GraphQL-Features` header is set, verify `agentAssignment` includes customAgent/customInstructions/model/baseRef)
- [ ] T013 [P] [US1] Add bats dry-run integration tests in `solune/scripts/tests/fleet-dispatch.bats` — test `--dry-run` with a sample pipeline config: verify no API calls made, verify dispatch plan output lists correct agents in correct group order, verify parallel groups are annotated as parallel, verify serial groups are annotated as serial

### Implementation for User Story 1

- [ ] T014 [US1] Implement config loading in `solune/scripts/fleet-dispatch.sh` — `load_pipeline_config()` reads `--config` JSON file, extracts preset by `--preset` ID using `jq`, validates preset has stages with agents, stores stages/groups/agents in shell variables for iteration
- [ ] T015 [US1] Implement sub-issue creation loop in `solune/scripts/fleet-dispatch.sh` — `create_sub_issues()` iterates all agents across all stages/groups, calls `gh issue create --repo "$REPO" --title "[${agent_slug}] ${parent_title}" --body "$(tailor_body)" --label "agent:${agent_slug}"` for each, parses returned issue URL for number, calls `resolve_issue_node_id` for GraphQL node ID, updates state file via `update_agent_state`
- [ ] T016 [US1] Implement retry logic in `solune/scripts/lib/fleet-graphql.sh` — `dispatch_with_retry()` wraps `dispatch_agent` with 3 attempts and exponential backoff (sleep 3s, 6s, 12s); on exhaustion marks agent as `"failed"` in state file and logs error; returns exit code 0 on success, 1 on failure
- [ ] T017 [US1] Implement parallel group dispatch in `solune/scripts/fleet-dispatch.sh` — `dispatch_parallel_group()` iterates agents in a group where `execution_mode == "parallel"`, launches `dispatch_with_retry "$agent_slug" &` for each, collects PIDs, calls `wait` for all PIDs, captures per-PID exit codes, updates state file for each agent
- [ ] T018 [US1] Implement serial group dispatch in `solune/scripts/fleet-dispatch.sh` — `dispatch_serial_group()` iterates agents in a group where `execution_mode == "sequential"`, dispatches one at a time via `dispatch_with_retry`, updates state file after each dispatch
- [ ] T019 [US1] Implement main dispatch orchestration in `solune/scripts/fleet-dispatch.sh` — `run_dispatch()` iterates stages in order, then groups within each stage in order, calls `dispatch_parallel_group` or `dispatch_serial_group` based on `execution_mode`, calls `finalize_state` when all stages complete
- [ ] T020 [US1] Implement `--dry-run` mode in `solune/scripts/fleet-dispatch.sh` — when `--dry-run` flag is set, `run_dispatch()` prints the full dispatch plan to stdout (stages, groups, agents, execution modes, labels) without calling `gh issue create` or `gh api graphql`; exits with code 0
- [ ] T021 [US1] Implement duplicate sub-issue detection in `solune/scripts/fleet-dispatch.sh` — `detect_existing_sub_issues()` queries `gh issue list --repo "$REPO" --label "agent:${agent_slug}" --search "parent:#${parent_issue}"` to find already-created sub-issues; skips creation for existing issues and uses their numbers/node IDs instead

**Checkpoint**: At this point, `fleet-dispatch.sh` can dispatch a full pipeline with parallel/serial groups. Verify with `--dry-run` flag and a sample config.

---

## Phase 4: User Story 2 — Pipeline Config Extraction to Standalone JSON (Priority: P1)

**Goal**: A developer can run `extract-pipeline-config.py` to produce a standalone `pipeline-config.json` from the Python backend's `_PRESET_DEFINITIONS`, validated against the JSON Schema, and consumable by both the shell script and Python backend.

**Independent Test**: Run `extract-pipeline-config.py` against `pipelines/service.py` and validate the output JSON against `contracts/pipeline-config-schema.json`. Verify it matches the existing `_PRESET_DEFINITIONS` structure.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T022 [P] [US2] Create pytest test file `solune/backend/tests/unit/test_extract_pipeline_config.py` — test extraction produces valid JSON, test output passes JSON Schema validation against `contracts/pipeline-config-schema.json`, test each preset has required fields (preset_id, name, stages), test stage order is contiguous from 0, test agent_slug values match known agents from `AgentsMixin.BUILTIN_AGENTS`
- [ ] T023 [P] [US2] Add pytest tests for round-trip fidelity in `solune/backend/tests/unit/test_extract_pipeline_config.py` — test that loading the extracted JSON back into Pydantic `PipelineConfig` models succeeds, test the loaded models match the original `_PRESET_DEFINITIONS` structure field-by-field
- [ ] T024 [P] [US2] Add bats test for `jq` consumption in `solune/scripts/tests/fleet-config.bats` — test that `jq` can parse the extracted JSON, test extracting preset by ID, test extracting agent slugs from a specific group, test extracting execution_mode for groups

### Implementation for User Story 2

- [ ] T025 [US2] Create extraction script `solune/scripts/extract-pipeline-config.py` — imports `_PRESET_DEFINITIONS` from `solune/backend/src/services/pipelines/service.py`, serializes to JSON array matching `contracts/pipeline-config-schema.json` schema, writes to `--output` path (default `solune/config/pipeline-config.json`), validates output against schema using `jsonschema` library, accepts `--source` (path to service.py) and `--output` (path to JSON) arguments
- [ ] T026 [US2] Generate initial `solune/config/pipeline-config.json` by running `python solune/scripts/extract-pipeline-config.py --output solune/config/pipeline-config.json` — commit the generated JSON as a versioned artifact
- [ ] T027 [US2] Update `PipelineService.seed_presets()` in `solune/backend/src/services/pipelines/service.py` — add `_load_preset_definitions()` function that reads from `solune/config/pipeline-config.json` if the file exists, falling back to the inline `_PRESET_DEFINITIONS` dict; replace `for preset in _PRESET_DEFINITIONS` with `for preset in _load_preset_definitions()`
- [ ] T028 [US2] Update `select_pipeline_preset()` and `launch_pipeline()` in `solune/backend/src/services/agent_tools.py` — replace `from src.services.pipelines.service import _PRESET_DEFINITIONS` with the new `_load_preset_definitions()` accessor
- [ ] T029 [P] [US2] Create sync script or Makefile target to regenerate `solune/frontend/src/data/preset-pipelines.ts` from `solune/config/pipeline-config.json` — script reads JSON, maps to TypeScript `PresetPipelineDefinition[]` format, writes to `preset-pipelines.ts` with header comment noting it is auto-generated

**Checkpoint**: At this point, pipeline config is extracted to JSON and consumed by both backend and dispatch script. Run `python -m pytest tests/unit/test_extract_pipeline_config.py -v` and verify JSON Schema validation passes.

---

## Phase 5: User Story 3 — Custom Instruction Templating for Shell Dispatch (Priority: P2)

**Goal**: The fleet-dispatch script generates agent-specific custom instructions using `envsubst`-compatible template files, matching the behavior of the Python `format_issue_context_as_prompt()` and `tailor_body_for_agent()` functions.

**Independent Test**: Set template variables as environment variables, run `envsubst` on a template file, and verify the output matches the expected instruction format for each agent type.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T030 [P] [US3] Create bats test file `solune/scripts/tests/fleet-templates.bats` — test `envsubst` expansion of `agent-instructions.tpl` with populated variables (`ISSUE_TITLE`, `ISSUE_BODY`, `AGENT_NAME`, `PARENT_ISSUE_NUMBER`, `BASE_REF`, `REPO_OWNER`, `REPO_NAME`), verify output contains all variable values
- [ ] T031 [P] [US3] Add bats tests for agent-specific templates in `solune/scripts/tests/fleet-templates.bats` — test `speckit-specify.tpl` output includes `spec.md` file reference, test `speckit-plan.tpl` output includes `plan.md` file reference, test `speckit-tasks.tpl` output includes `tasks.md` file reference, test `copilot-review.tpl` output includes PR review tracking note
- [ ] T032 [P] [US3] Add bats test for unknown agent fallback in `solune/scripts/tests/fleet-templates.bats` — test that when no agent-specific template exists, the base `agent-instructions.tpl` is used with generic task description

### Implementation for User Story 3

- [ ] T033 [P] [US3] Create base instruction template `solune/config/templates/agent-instructions.tpl` — port the structure from `format_issue_context_as_prompt()` in `solune/backend/src/services/github_projects/agents.py:106–205`: include `${ISSUE_TITLE}`, `${ISSUE_BODY}`, `${AGENT_NAME}`, `${AGENT_DESCRIPTION}`, `${PARENT_ISSUE_NUMBER}`, `${BASE_REF}` placeholders with issue context sections and output instructions
- [ ] T034 [P] [US3] Create agent-specific template `solune/config/templates/speckit-specify.tpl` — extends base template with spec.md output file instructions per `agent_files` map in `agents.py:169–175`
- [ ] T035 [P] [US3] Create agent-specific template `solune/config/templates/speckit-plan.tpl` — extends base template with plan.md output file instructions
- [ ] T036 [P] [US3] Create agent-specific template `solune/config/templates/speckit-tasks.tpl` — extends base template with tasks.md output file instructions
- [ ] T037 [P] [US3] Create agent-specific template `solune/config/templates/speckit-implement.tpl` — extends base template with implementation-specific instructions (no specific .md output files)
- [ ] T038 [P] [US3] Create agent-specific template `solune/config/templates/copilot-review.tpl` — extends base template with PR review tracking note per the `copilot-review` entry in the `agent_descriptions` mapping in `solune/backend/src/services/github_projects/agents.py`
- [ ] T039 [US3] Implement template expansion function in `solune/scripts/lib/fleet-templates.sh` — `expand_instructions()` accepts agent_slug, sets template variables as environment variables from CLI args and issue data, selects the agent-specific template if it exists (falling back to `agent-instructions.tpl`), runs `envsubst` on the selected template, returns the expanded instructions string
- [ ] T040 [US3] Integrate template expansion into sub-issue creation in `solune/scripts/fleet-dispatch.sh` — update `create_sub_issues()` to call `expand_instructions "$agent_slug"` for each agent and pass the result as `customInstructions` in the GraphQL dispatch mutation
- [ ] T041 [US3] Implement issue context fetching in `solune/scripts/lib/fleet-templates.sh` — `fetch_issue_context()` calls `gh issue view "$PARENT_ISSUE" --repo "$REPO" --json title,body,comments` to populate `ISSUE_TITLE`, `ISSUE_BODY`, and comment variables for template expansion

**Checkpoint**: At this point, the dispatch script generates full custom instructions for each agent type. Verify with `--dry-run --verbose` to inspect generated instructions.

---

## Phase 6: User Story 4 — Completion Monitoring and Pipeline Advancement (Priority: P2)

**Goal**: After dispatching agents, the script monitors completion by polling sub-issue state via `gh api graphql`. Serial groups advance to the next agent only after the current one completes. A summary report is printed at the end.

**Independent Test**: Mock a sub-issue state transition from open to closed and verify the polling loop detects completion and advances to the next agent.

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T042 [P] [US4] Create bats test file `solune/scripts/tests/fleet-polling.bats` — test `poll_issue_completion` detects closed issue status, test exponential backoff intervals (30s, 60s, 120s, 240s, 300s cap), test timeout detection after configurable duration
- [ ] T043 [P] [US4] Add bats tests for PR detection in `solune/scripts/tests/fleet-polling.bats` — test `detect_agent_pr` finds a PR matching the agent branch pattern, test `check_pr_merged` detects merged status
- [ ] T044 [P] [US4] Add bats tests for summary report in `solune/scripts/tests/fleet-polling.bats` — test `print_summary` outputs table with agent slug, status, duration, issue number, and PR link columns

### Implementation for User Story 4

- [ ] T045 [US4] Create shell library `solune/scripts/lib/fleet-polling.sh` — `poll_issue_completion()` queries sub-issue state via `gh api graphql` (issue state: OPEN/CLOSED), implements exponential backoff polling (30s base, 2x multiplier, 300s cap), accepts `--timeout` (default 3600s = 60 min), returns 0 on completion, 1 on timeout; updates agent state to `"completed"` or `"timed_out"`
- [ ] T046 [US4] Implement PR detection in `solune/scripts/lib/fleet-polling.sh` — `detect_agent_pr()` queries `gh pr list --repo "$REPO" --head "copilot/${agent_slug}" --json number,merged,url`, updates agent state with `pr_number` and `pr_merged` fields
- [ ] T047 [US4] Integrate polling into serial group dispatch in `solune/scripts/fleet-dispatch.sh` — update `dispatch_serial_group()` to call `poll_issue_completion` after each agent dispatch, only proceed to next agent when current one completes or times out
- [ ] T048 [US4] Implement parallel group completion wait in `solune/scripts/fleet-dispatch.sh` — update `dispatch_parallel_group()` to optionally poll for all agents in the group to complete (when `--wait` flag is set), using concurrent polling loops
- [ ] T049 [US4] Implement summary report in `solune/scripts/fleet-dispatch.sh` — `print_summary()` reads final `fleet-state.json`, prints a formatted table with columns: Agent | Status | Duration | Issue | PR, computes total duration, reports success/failure/timeout counts, exits with code 0 if all succeeded, code 1 if any failed

**Checkpoint**: At this point, `fleet-dispatch.sh` fully monitors agent completion and advances serial groups. Verify by dispatching a test pipeline and checking the summary report.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories.

- [ ] T050 [P] Add `--help` flag and usage documentation to `solune/scripts/fleet-dispatch.sh` — print comprehensive usage with all flags, examples from `quickstart.md`, and exit code descriptions
- [ ] T051 [P] Add `--help` flag and usage documentation to `solune/scripts/extract-pipeline-config.py` — print usage with `--source` and `--output` args
- [ ] T052 [P] Update `solune/scripts/validate-contracts.sh` — add Step 4: validate `solune/config/pipeline-config.json` against `contracts/pipeline-config-schema.json` using `jq` or `python -m jsonschema`
- [ ] T053 [P] Add shellcheck compliance to `solune/scripts/fleet-dispatch.sh` and all `solune/scripts/lib/*.sh` — run `shellcheck` and fix warnings
- [ ] T054 Code cleanup — ensure all shell functions have doc comments, remove any debugging `echo` statements, verify `set -euo pipefail` is set in all scripts
- [ ] T055 [P] Update `quickstart.md` with verified usage examples — run each example from the Development & Testing section and fix any discrepancies
- [ ] T056 Run full bats test suite `bats solune/scripts/tests/` and verify all tests pass
- [ ] T057 Run existing backend tests `cd solune/backend && python -m pytest tests/unit/ -q --timeout=120` to verify no regressions from config extraction changes
- [ ] T058 Run existing frontend tests `cd solune/frontend && npm test` to verify no regressions if `preset-pipelines.ts` was regenerated

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) — core dispatch functionality
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) — can run in PARALLEL with US1
- **User Story 3 (Phase 5)**: Depends on US1 dispatch skeleton (T007, T015) for integration — can start templates (T033–T038) in parallel with US1
- **User Story 4 (Phase 6)**: Depends on US1 dispatch (Phase 3) — serial group advancement needs dispatch working
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) — Independent of US1; both are P1 and can be worked in parallel
- **User Story 3 (P2)**: Template files (T033–T038) can be created in parallel with US1/US2; integration (T039–T041) depends on US1 dispatch skeleton
- **User Story 4 (P2)**: Depends on US1 completion — polling integrates into the dispatch loop

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Library functions before script integration
- Core implementation before integration tasks
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1**: All Setup tasks (T001–T003) can run in parallel
- **Phase 2**: T005, T006 can run in parallel (different files); T007 depends on T004
- **Phase 3 (US1)**: All test tasks (T008–T013) can run in parallel; T017/T018 depend on T016; T020/T021 can run in parallel with T019
- **Phase 4 (US2)**: All test tasks (T022–T024) can run in parallel; T025 before T026–T029; T029 independent of T027–T028
- **Phase 5 (US3)**: All test tasks (T030–T032) can run in parallel; all template files (T033–T038) can run in parallel; T039 before T040
- **Phase 6 (US4)**: All test tasks (T042–T044) can run in parallel; T045 before T047; T046 independent of T045
- **Phase 7**: Most polish tasks can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together (different files):
Task: T008 — "bats tests for argument validation in solune/scripts/tests/fleet-dispatch.bats"
Task: T010 — "bats tests for common functions in solune/scripts/tests/fleet-common.bats"
Task: T011 — "bats tests for state management in solune/scripts/tests/fleet-state.bats"
Task: T012 — "bats tests for GraphQL functions in solune/scripts/tests/fleet-graphql.bats"

# Then implement library functions in parallel (different files):
Task: T014 — "Config loading in fleet-dispatch.sh"
Task: T016 — "Retry logic in lib/fleet-graphql.sh"

# Then serial integration:
Task: T015 — "Sub-issue creation loop"
Task: T017 — "Parallel group dispatch"
Task: T018 — "Serial group dispatch"
Task: T019 — "Main dispatch orchestration"
```

## Parallel Example: User Story 2

```bash
# Launch all US2 tests together (different files):
Task: T022 — "pytest extraction tests in test_extract_pipeline_config.py"
Task: T023 — "pytest round-trip fidelity tests"
Task: T024 — "bats jq consumption tests in fleet-config.bats"

# Then implement extraction (serial — each step depends on previous):
Task: T025 — "Create extract-pipeline-config.py"
Task: T026 — "Generate initial pipeline-config.json"
Task: T027 — "Update PipelineService.seed_presets()"
Task: T028 — "Update agent_tools.py"
Task: T029 — "Create frontend sync script" (parallel with T027/T028)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 — CLI Fleet Dispatch
4. **STOP and VALIDATE**: Test with `--dry-run` flag against sample config
5. Deploy/demo — fire-and-forget dispatch works

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test with `--dry-run` → Deploy/Demo (MVP!)
3. Add User Story 2 → Test with JSON Schema validation → Config extraction works
4. Add User Story 3 → Test with `envsubst` expansion → Full custom instructions
5. Add User Story 4 → Test with polling → Full pipeline automation
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (CLI Dispatch)
   - Developer B: User Story 2 (Config Extraction) — fully independent of US1
3. After US1 dispatch skeleton is ready:
   - Developer C: User Story 3 (Templates) — depends on US1 skeleton for integration
   - Developer D: User Story 4 (Monitoring) — depends on US1 completion
4. Stories complete and integrate independently

---

## Summary

| Metric | Value |
|--------|-------|
| **Total tasks** | 58 |
| **Phase 1 (Setup)** | 3 tasks |
| **Phase 2 (Foundational)** | 4 tasks |
| **Phase 3 (US1 — Dispatch)** | 14 tasks (6 test + 8 impl) |
| **Phase 4 (US2 — Config Extraction)** | 8 tasks (3 test + 5 impl) |
| **Phase 5 (US3 — Templates)** | 12 tasks (3 test + 9 impl) |
| **Phase 6 (US4 — Monitoring)** | 8 tasks (3 test + 5 impl) |
| **Phase 7 (Polish)** | 9 tasks |
| **Parallel opportunities** | 34 tasks marked [P] |
| **Suggested MVP scope** | Phases 1–3 (User Story 1 only) — 21 tasks |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All shell scripts use `set -euo pipefail` and pass `shellcheck`
- `gh api graphql` requires header: `GraphQL-Features: issues_copilot_assignment_api_support,coding_agent_model_selection`
