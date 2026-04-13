# Feature Specification: Remove Fleet Dispatch & Copilot CLI Code

**Feature Branch**: `001-remove-fleet-dispatch`  
**Created**: 2026-04-13  
**Status**: Draft  
**Input**: User description: "Remove all fleet dispatch orchestration and GitHub Copilot CLI plugin code from Solune. Fleet enrichment (custom templates, agent-task tracking, fleet-specific labels) is deleted; the existing 'classic' dispatch path — which uses format_issue_context_as_prompt() and standard Copilot assignment — becomes the sole execution path. ~30 files deleted, ~15 files modified."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Issue Dispatch Continues via Classic Path (Priority: P1)

A maintainer triggers a workflow pipeline for a repository issue. The system dispatches work to a Copilot agent using the classic path — formatting issue context as a prompt and assigning the Copilot agent to the issue. The maintainer observes the same behavior they would have seen previously when fleet dispatch was not eligible: the issue is assigned, the agent receives instructions, and the pipeline progresses through its stages. No fleet-specific enrichment (custom templates, fleet labels, agent-task tracking) is applied because that capability has been fully removed.

**Why this priority**: This is the core user-facing behavior that must remain intact. If the classic dispatch path breaks, no issues can be dispatched to agents at all — the entire pipeline stops working. Every other story depends on this path functioning correctly.

**Independent Test**: Trigger a pipeline dispatch for any issue and verify that the agent is assigned via the standard Copilot assignment, the issue context is formatted as a prompt, the pipeline progresses through all stages, and no fleet-related fields (agent_task_ids, dispatch_backend) appear in state or responses.

**Acceptance Scenarios**:

1. **Given** a repository issue eligible for pipeline dispatch, **When** the orchestrator processes the issue, **Then** the system formats issue context as a prompt using the classic path and assigns a Copilot agent to the issue.
2. **Given** the fleet dispatch code has been removed, **When** any issue is dispatched, **Then** no fleet eligibility check occurs, no fleet sub-issue labels are generated, and no agent task IDs are tracked.
3. **Given** a pipeline is running, **When** the pipeline state is written, **Then** the state contains no dispatch_backend or agent_task_ids fields.

---

### User Story 2 - Codebase Is Free of Fleet Dispatch Artifacts (Priority: P1)

A developer working on the Solune codebase searches for fleet-related code, configuration files, templates, shell scripts, or CLI plugin artifacts. They find zero results. All standalone fleet dispatch files (~30 files) have been deleted, and all fleet references in modified files (~15 files) have been cleaned up. The developer can confidently work on the codebase without encountering dead code paths, unused imports, or orphaned configuration.

**Why this priority**: Dead code creates confusion, increases maintenance burden, and risks accidental re-activation. Removing all fleet artifacts is the primary deliverable of this feature and a prerequisite for all other stories.

**Independent Test**: Run a comprehensive text search across the entire codebase for fleet-related terms (fleet, FleetDispatch, fleet_dispatch, fleet-dispatch, agent_task_ids, dispatch_backend) and verify zero matches outside of changelog or historical documentation.

**Acceptance Scenarios**:

1. **Given** the removal is complete, **When** a developer searches the codebase for "FleetDispatch", "fleet_dispatch", "fleet-dispatch", or "fleet", **Then** zero matches are found (excluding CHANGELOG.md).
2. **Given** the removal is complete, **When** a developer searches for "agent_task_ids" or "dispatch_backend", **Then** zero matches are found in source code, configuration, or type definitions.
3. **Given** all fleet shell scripts, templates, and CLI plugin files have been deleted, **When** a developer lists the project's file tree, **Then** none of the deleted files exist on disk.

---

### User Story 3 - All Existing Tests Pass After Removal (Priority: P1)

A developer runs the full backend and frontend test suites after the fleet dispatch removal. All unit tests, integration tests, type checks, and schema validations pass without errors. No test failures are introduced by the removal. Fleet-specific test files have been deleted, and fleet assertions in shared test files have been cleaned up.

**Why this priority**: Test suite health is a critical gate for any code removal. Broken tests block CI/CD and prevent other work from merging. This story verifies that the removal is surgically clean — nothing was accidentally broken.

**Independent Test**: Run all backend unit tests, backend integration tests, frontend type checking, and frontend test suite. All must pass with zero errors and zero import failures.

**Acceptance Scenarios**:

1. **Given** fleet-specific test files have been deleted, **When** the backend unit test suite runs, **Then** all tests pass with no import errors.
2. **Given** fleet assertions have been removed from shared test files, **When** the backend integration test suite runs, **Then** all tests pass.
3. **Given** fleet type definitions have been removed from frontend schemas, **When** the frontend type checker runs, **Then** no type errors are reported.
4. **Given** fleet fields have been removed from Zod schemas, **When** the frontend test suite runs, **Then** all schema tests pass.

---

### User Story 4 - Pipeline Orchestration Uses Hardcoded Legacy Stages (Priority: P2)

A pipeline is launched and the system determines which stages to execute. Previously, stages could be derived from fleet dispatch configuration. After removal, the pipeline orchestrator uses the hardcoded legacy stages directly as the primary and sole stage source. The behavior is identical to the previous fallback path, which now becomes the only path.

**Why this priority**: This ensures the pipeline stage resolution is simplified and deterministic. While lower priority than core dispatch (Story 1), incorrect stage resolution would cause pipelines to stall or skip steps.

**Independent Test**: Launch a pipeline and verify that the stages returned match the hardcoded legacy stages, with no dependency on fleet dispatch configuration files or fleet-specific stage builders.

**Acceptance Scenarios**:

1. **Given** fleet dispatch configuration has been removed, **When** the pipeline orchestrator determines execution stages, **Then** it returns the hardcoded legacy stages directly.
2. **Given** no fleet configuration loader exists, **When** the system starts up, **Then** no fleet config file is searched for or loaded.

---

### User Story 5 - Shared Functions Remain Available to Non-Fleet Callers (Priority: P2)

Other parts of the system that shared functions with fleet dispatch continue to work. Specifically, the Copilot assignment function (used by the app plan orchestrator and auto-merge) remains available and functional. Only fleet-exclusive functions are removed; shared functions are preserved.

**Why this priority**: Removing shared functions would break unrelated features. This story explicitly verifies that the removal scope is correct — only fleet-exclusive code is deleted.

**Independent Test**: Verify that the Copilot assignment function is still importable and callable from its existing call sites (app plan orchestrator, auto-merge). Verify that fleet-exclusive functions (agent task listing, agent task fetching, agent task endpoint discovery) are no longer present.

**Acceptance Scenarios**:

1. **Given** the Copilot assignment function is shared between fleet and non-fleet callers, **When** the app plan orchestrator or auto-merge module imports it, **Then** the import succeeds and the function is callable.
2. **Given** fleet-exclusive Copilot functions have been removed, **When** a developer attempts to import agent task listing or fetching functions, **Then** the import fails because the functions no longer exist.

---

### User Story 6 - API Responses No Longer Contain Fleet Fields (Priority: P2)

A client consuming the workflow API receives responses that no longer contain fleet-specific fields (dispatch_backend, agent_task_ids). The API response shape is cleaner and only contains fields relevant to the classic dispatch path. Since no frontend component ever rendered these fields, there is no user-visible change in the UI.

**Why this priority**: Clean API contracts prevent confusion for API consumers and reduce payload size. Since frontend never rendered these fields, the risk of user-facing breakage is zero.

**Independent Test**: Call the workflow API endpoint and inspect the response payload. Verify that dispatch_backend and agent_task_ids fields are absent from the response.

**Acceptance Scenarios**:

1. **Given** fleet fields have been removed from the API layer, **When** a client requests pipeline state, **Then** the response does not contain dispatch_backend or agent_task_ids fields.
2. **Given** fleet fields have been removed from frontend type definitions, **When** the frontend receives an API response, **Then** it parses successfully without expecting fleet fields.

---

### User Story 7 - Documentation Reflects Simplified Architecture (Priority: P3)

A developer reviewing architecture documentation sees an accurate representation of the system without fleet dispatch components. The architecture diagram no longer shows Fleet Dispatch as a component, and planning documents no longer reference fleet-dispatch-pipelines.

**Why this priority**: Documentation accuracy is important for onboarding and system understanding, but is lower priority than functional correctness.

**Independent Test**: Review the architecture diagram and planning documents. Verify that Fleet Dispatch is not mentioned in the diagram and fleet-dispatch-pipelines references are removed from the plan.

**Acceptance Scenarios**:

1. **Given** fleet dispatch has been removed, **When** a developer views the backend architecture diagram, **Then** Fleet Dispatch does not appear as a component.
2. **Given** fleet dispatch has been removed, **When** a developer reads the plan document, **Then** no references to fleet-dispatch-pipelines exist.

---

### Edge Cases

- What happens if a pipeline was started with fleet dispatch before the removal and is still in progress? The system should gracefully handle any in-progress pipelines by falling through to the classic path, since the fleet branch no longer exists in the code.
- What happens if external systems or scripts reference fleet dispatch endpoints or configuration files? They will receive standard errors (file not found, import errors) since those artifacts no longer exist. No special backward-compatibility shim is needed.
- What happens if the scripts/pipelines/ directory becomes empty after template and config removal? The empty directory should be deleted to avoid leaving orphaned directories.
- What happens if agent definition files (.github/agents/*.agent.md) contain fleet-related references? These files are preserved as-is because fleet eligibility was a runtime decision, not encoded in agent definitions.
- What happens if guard-config.yml contains fleet-specific entries? Verified: it does not. No changes needed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST delete all standalone fleet dispatch shell scripts (fleet-dispatch.sh, fleet_dispatch_common.sh)
- **FR-002**: System MUST delete all fleet dispatch pipeline configuration files (fleet-dispatch.json, pipeline-config.schema.json) and all 12 template files
- **FR-003**: System MUST delete the entire CLI plugin directory (plugin.json, .mcp.json, agents/, hooks/, skills/)
- **FR-004**: System MUST delete the fleet dispatch backend service module (~350 lines, FleetDispatchService class)
- **FR-005**: System MUST remove all 9 FleetDispatch model classes from the pipeline models while preserving all non-fleet models (PipelineAgentNode, ExecutionGroup, PipelineStage, PipelineConfig, etc.)
- **FR-006**: System MUST remove fleet-specific configuration functions (_DEFAULT_FLEET_DISPATCH_CONFIG, get_default_fleet_dispatch_config_path, load_fleet_dispatch_config, build_pipeline_stages_from_fleet_config) while preserving all non-fleet configuration functions
- **FR-007**: System MUST remove all fleet dispatch references from the main orchestrator (~29 references), including FleetDispatchService import/instantiation, is_fleet_eligible() branch sites, fleet sub-issue label builders, fleet sub-issue finders, fleet logging, and agent_task_ids from state writes
- **FR-008**: System MUST simplify the pipeline orchestrator so that the hardcoded legacy stages become the primary and sole stage source, with no fleet dependency
- **FR-009**: System MUST remove fleet-exclusive Copilot functions (list_agent_tasks, get_agent_task, _discover_agent_task_endpoint) while preserving the shared assign_copilot_to_issue function
- **FR-010**: System MUST remove fleet-related polling helpers (_get_agent_task_id, _check_agent_task_status, FleetDispatchService.normalize_task_state import) and fleet task failure log messages
- **FR-011**: System MUST remove fleet-specific API layer code (_infer_dispatch_backend, FleetDispatchService import, dispatch_backend/agent_task_ids from response payloads)
- **FR-012**: System MUST remove fleet fields (agent_task_ids, dispatch_backend) from frontend type definitions and schema validations
- **FR-013**: System MUST delete all 7 fleet-specific test files and remove fleet assertions from 5 shared test files
- **FR-014**: System MUST update the backend architecture diagram to remove Fleet Dispatch as a component
- **FR-015**: System MUST update the plan document to remove fleet-dispatch-pipelines references
- **FR-016**: System MUST preserve assign_copilot_to_issue() functionality for its existing non-fleet callers (app_plan_orchestrator, auto_merge)
- **FR-017**: System MUST preserve all agent definition files (.github/agents/*.agent.md) unchanged
- **FR-018**: System MUST preserve guard-config.yml unchanged
- **FR-019**: System MUST delete the scripts/pipelines/ directory if it becomes empty after template and config removal

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero matches when searching the codebase for fleet-related terms (fleet, FleetDispatch, fleet_dispatch, fleet-dispatch, agent_task_ids, dispatch_backend), excluding CHANGELOG.md
- **SC-002**: All backend unit tests pass with no import errors after the removal (~100% pass rate maintained)
- **SC-003**: All backend integration tests pass with no broken imports after the removal
- **SC-004**: Frontend type checking completes with zero type errors after the removal
- **SC-005**: Frontend test suite passes with all schema tests succeeding after the removal
- **SC-006**: ~30 files are deleted from the codebase (shell scripts, templates, config, CLI plugin, fleet service, fleet tests)
- **SC-007**: ~15 files are modified to remove fleet references (orchestrators, models, config, API, helpers, frontend types, shared tests, documentation)
- **SC-008**: The Copilot assignment function remains callable from its 2 existing non-fleet call sites (app_plan_orchestrator, auto_merge)
- **SC-009**: Pipeline dispatch for any issue completes successfully using only the classic path
- **SC-010**: API responses for pipeline state contain no dispatch_backend or agent_task_ids fields

## Assumptions

- Fleet dispatch was a runtime feature toggle (is_fleet_eligible() checks), not a permanent architectural split. Removing it simplifies the codebase without losing any user-facing capability.
- The "classic" dispatch path (format_issue_context_as_prompt + standard Copilot assignment) was always the fallback and has been running in production. It is stable and complete.
- No external consumers depend on fleet-specific API fields (dispatch_backend, agent_task_ids). The frontend never rendered them (verified zero UI references).
- In-progress pipelines that may have been started with fleet dispatch will gracefully degrade to the classic path since fleet branches are removed from conditional logic.
- The specs/001-fleet-dispatch-pipelines/ directory does not exist on disk, so no spec cleanup is needed.
- Agent definition files (.github/agents/*.agent.md) do not encode fleet eligibility and require no changes.
- guard-config.yml contains no fleet-specific entries and requires no changes.
- The CHANGELOG.md may contain historical references to fleet dispatch; these are acceptable and should not be removed.

## Scope & Boundaries

### In Scope

- Deletion of all fleet dispatch standalone artifacts (scripts, templates, config, CLI plugin, backend service)
- Removal of fleet dispatch models, configuration functions, and imports from shared modules
- Simplification of orchestration logic to use only the classic dispatch path
- Cleanup of API response payloads and frontend type definitions
- Deletion of fleet-specific tests and cleanup of fleet assertions in shared tests
- Documentation updates (architecture diagram, plan document)

### Out of Scope

- Changes to the classic dispatch path behavior (it must remain exactly as-is)
- Changes to agent definition files or guard configuration
- Changes to CHANGELOG.md or historical documentation
- Addition of new features or capabilities
- Migration or backward-compatibility shims for removed fleet functionality
- Performance optimization of the classic path
