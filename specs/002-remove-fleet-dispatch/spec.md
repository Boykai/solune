# Feature Specification: Remove Fleet Dispatch & Copilot CLI Code

**Feature Branch**: `002-remove-fleet-dispatch`  
**Created**: 2026-04-13  
**Status**: Draft  
**Input**: User description: "Remove all fleet dispatch orchestration and GitHub Copilot CLI plugin code from Solune. Fleet enrichment (custom templates, agent-task tracking, fleet-specific labels) is deleted; the existing 'classic' dispatch path — which uses format_issue_context_as_prompt() and standard Copilot assignment — becomes the sole execution path."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Classic Dispatch Path Remains the Sole Execution Path (Priority: P1)

As a Solune operator, I want the classic dispatch path (format_issue_context_as_prompt + standard Copilot assignment) to be the only execution path so that issues are dispatched simply and predictably without fleet-specific branching logic.

**Why this priority**: This is the core behavioral change. All fleet dispatch was an alternative orchestration layer; removing it makes the classic path the sole code path. If this story fails, the system cannot dispatch work at all.

**Independent Test**: Trigger a dispatch for any issue and verify the system uses format_issue_context_as_prompt() to build instructions and assign_copilot_to_issue() to dispatch — with no fleet eligibility checks, no task ID resolution, and no fleet sub-issue label enrichment.

**Acceptance Scenarios**:

1. **Given** an issue eligible for dispatch, **When** the orchestrator processes it, **Then** it builds instructions via format_issue_context_as_prompt() and dispatches via assign_copilot_to_issue() without any fleet eligibility check.
2. **Given** an issue that previously would have been fleet-eligible, **When** the orchestrator processes it, **Then** it follows the same classic dispatch path as any other issue.
3. **Given** an active dispatch in progress, **When** polling for completion status, **Then** the system does not query agent task IDs or fleet task status endpoints.

---

### User Story 2 - Dead Code and Artifacts Are Fully Removed (Priority: P1)

As a developer maintaining Solune, I want all fleet dispatch code, CLI plugin files, fleet-specific templates, and fleet test files removed so that the codebase is smaller, simpler, and free of dead code paths.

**Why this priority**: Dead code creates confusion, increases maintenance burden, and inflates the test surface. Removing it is essential for long-term codebase health and is the primary deliverable of this feature.

**Independent Test**: Search the codebase for any reference to fleet dispatch identifiers (FleetDispatch, fleet_dispatch, fleet-dispatch, agent_task_ids, dispatch_backend) and confirm zero matches outside of changelog/historical documentation.

**Acceptance Scenarios**:

1. **Given** the completed removal, **When** searching the codebase for fleet dispatch identifiers, **Then** zero matches are found (excluding CHANGELOG.md).
2. **Given** the fleet_dispatch.py service file, **When** checking the file system, **Then** it no longer exists.
3. **Given** the cli-plugin directory, **When** checking the file system, **Then** it no longer exists.
4. **Given** fleet-specific test files (7 files), **When** checking the file system, **Then** none of them exist.
5. **Given** fleet template files (12 files) and fleet pipeline config, **When** checking the file system, **Then** none of them exist.

---

### User Story 3 - Existing Non-Fleet Functionality Is Unaffected (Priority: P1)

As a Solune operator, I want all non-fleet functionality (classic dispatch, pipeline orchestration, API responses, auto-merge, app-plan orchestration) to continue working identically after the removal so there is zero behavioral regression.

**Why this priority**: Any regression in existing functionality would make this removal a net negative. Preserving behavior is as important as removing code.

**Independent Test**: Run the full unit and integration test suites, verify type-checking passes, and confirm that callers of assign_copilot_to_issue() (app_plan_orchestrator.py, auto_merge.py) are unaffected.

**Acceptance Scenarios**:

1. **Given** the removal is complete, **When** running backend unit tests, **Then** all tests pass with no import errors.
2. **Given** the removal is complete, **When** running backend integration tests, **Then** all tests pass with no broken imports.
3. **Given** the removal is complete, **When** running frontend type checking, **Then** no type errors are reported.
4. **Given** the removal is complete, **When** running frontend schema tests, **Then** all tests pass.
5. **Given** assign_copilot_to_issue() is preserved, **When** app_plan_orchestrator.py or auto_merge.py call it, **Then** it functions identically to before.

---

### User Story 4 - API Responses Exclude Fleet-Specific Fields (Priority: P2)

As a consumer of the Solune API, I want fleet-specific fields (dispatch_backend, agent_task_ids) removed from workflow API responses so the API surface is clean and only exposes actively-used data.

**Why this priority**: These fields were never rendered by any UI component. Removing them simplifies the API contract and prevents confusion, but has no user-facing impact.

**Independent Test**: Call the workflow API endpoint and verify the response schema no longer contains dispatch_backend or agent_task_ids fields.

**Acceptance Scenarios**:

1. **Given** a workflow API response, **When** inspecting the response body, **Then** it does not contain dispatch_backend or agent_task_ids fields.
2. **Given** the frontend type definitions, **When** inspecting PipelineStateInfo and the Zod schema, **Then** they do not reference dispatch_backend or agent_task_ids.

---

### User Story 5 - Documentation Reflects the Simplified Architecture (Priority: P3)

As a developer onboarding to Solune, I want documentation and architecture diagrams to reflect the simplified system without fleet dispatch so that I can understand the current architecture accurately.

**Why this priority**: Documentation accuracy supports maintainability but is lower urgency than code correctness.

**Independent Test**: Review the architecture diagram and plan document to confirm no fleet dispatch references remain.

**Acceptance Scenarios**:

1. **Given** the backend components diagram, **When** reviewing it, **Then** Fleet Dispatch is not present.
2. **Given** the plan document, **When** reviewing it, **Then** fleet-dispatch-pipelines references are removed.

---

### Edge Cases

- What happens if a future contributor re-introduces a fleet-related import? The test suite and type checker should catch undefined references immediately since all fleet modules are deleted.
- What happens to in-flight dispatches that were started under fleet mode before this change is deployed? This removal assumes a clean cutover — no in-flight fleet dispatches exist at deployment time (fleet was runtime-gated, not persisted to durable state).
- What if the scripts/pipelines/ directory becomes empty after template removal? It should be deleted if empty; if other non-fleet files remain, they are preserved.
- What about .github/agents/*.agent.md files that reference fleet? Fleet eligibility was a runtime check, not encoded in agent definitions — these files are preserved unchanged.
- What about guard-config.yml? It contains no fleet-specific entries and is left unchanged.

## Requirements *(mandatory)*

### Functional Requirements

#### Deletion Requirements

- **FR-001**: System MUST delete the fleet dispatch shell scripts (fleet-dispatch.sh, fleet_dispatch_common.sh).
- **FR-002**: System MUST delete the fleet pipeline configuration file (fleet-dispatch.json) and its schema (pipeline-config.schema.json).
- **FR-003**: System MUST delete all 12 fleet dispatch template files.
- **FR-004**: System MUST delete the entire CLI plugin directory (plugin.json, .mcp.json, agents/, hooks/, skills/).
- **FR-005**: System MUST delete the fleet dispatch backend service module (~350 lines, FleetDispatchService class).
- **FR-006**: System MUST delete 7 fleet-specific test files.

#### Model & Configuration Removal Requirements

- **FR-007**: System MUST remove all 9 FleetDispatch model classes (FleetDispatchModel, FleetDispatchRepository, FleetDispatchDefaults, FleetDispatchSubIssue, FleetDispatchAgent, FleetDispatchExecutionGroup, FleetDispatchConfig, FleetDispatchStatus, FleetDispatchRecord) from the pipeline models module.
- **FR-008**: System MUST preserve all non-fleet models (PipelineAgentNode, ExecutionGroup, PipelineStage, PipelineConfig, etc.) in the pipeline models module.
- **FR-009**: System MUST remove fleet configuration functions (_DEFAULT_FLEET_DISPATCH_CONFIG, get_default_fleet_dispatch_config_path(), load_fleet_dispatch_config(), build_pipeline_stages_from_fleet_config()) from the config module.
- **FR-010**: System MUST preserve all non-fleet configuration functions (get_workflow_config(), set_workflow_config(), resolve_project_pipeline_mappings(), load_user_agent_mappings(), etc.).

#### Orchestration Simplification Requirements

- **FR-011**: System MUST remove all fleet eligibility branching (is_fleet_eligible checks) from the orchestrator, making the classic dispatch path the sole code path.
- **FR-012**: System MUST retain format_issue_context_as_prompt() as the instruction-building method for dispatches.
- **FR-013**: System MUST retain assign_copilot_to_issue() as the dispatch method, preserving its callers (app_plan_orchestrator.py, auto_merge.py).
- **FR-014**: System MUST remove fleet sub-issue label building (build_fleet_sub_issue_labels), reusable fleet sub-issue lookup (_find_reusable_fleet_sub_issue), fleet logging, and agent_task_ids from state writes in the orchestrator.
- **FR-015**: System MUST replace the pipeline orchestrator's _default_pipeline_stages() with hardcoded legacy stages directly (current fallback becomes primary).
- **FR-016**: System MUST delete unused Copilot functions (list_agent_tasks(), get_agent_task(), _discover_agent_task_endpoint()) from the Copilot module.
- **FR-017**: System MUST remove fleet task polling helpers (_get_agent_task_id(), _check_agent_task_status(), FleetDispatchService.normalize_task_state() import) from the helpers module.
- **FR-018**: System MUST remove "Fleet task failed" log messages from the pipeline module.

#### API & Frontend Requirements

- **FR-019**: System MUST remove dispatch_backend and agent_task_ids fields from the workflow API response.
- **FR-020**: System MUST remove agent_task_ids and dispatch_backend from the frontend PipelineStateInfo type definition.
- **FR-021**: System MUST remove agent_task_ids and dispatch_backend from the frontend Zod validation schema.

#### Test Modification Requirements

- **FR-022**: System MUST update 5 remaining test files to remove fleet-specific assertions while preserving all non-fleet test coverage.

#### Documentation Requirements

- **FR-023**: System MUST remove Fleet Dispatch from the backend components architecture diagram.
- **FR-024**: System MUST remove fleet-dispatch-pipelines references from the plan document.

#### Cleanup Requirements

- **FR-025**: System MUST delete the scripts/pipelines/ directory if it is empty after template and config removal.

### Assumptions

- Fleet dispatch was a runtime-gated feature; no durable fleet-specific state exists that needs migration or cleanup in external systems.
- The 12 fleet template files, fleet-dispatch.json, and pipeline-config.schema.json are all located within the scripts/pipelines/ or templates directory structure.
- The .github/agents/*.agent.md files do not encode fleet-specific logic and require no changes.
- guard-config.yml contains no fleet-specific entries.
- CHANGELOG.md is excluded from the "zero fleet references" verification — historical entries are preserved.
- No external consumers depend on the dispatch_backend or agent_task_ids API fields (validated by zero UI references).
- A clean cutover is assumed — no in-flight fleet dispatches exist at deployment time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A codebase-wide search for fleet dispatch identifiers (FleetDispatch, fleet_dispatch, fleet-dispatch, agent_task_ids, dispatch_backend) returns zero matches outside of CHANGELOG.md.
- **SC-002**: ~30 files are deleted and ~15 files are modified, resulting in a net reduction of codebase size.
- **SC-003**: All backend unit tests pass with no import errors after removal.
- **SC-004**: All backend integration tests pass with no broken imports after removal.
- **SC-005**: Frontend type checking completes with zero errors after removal.
- **SC-006**: Frontend schema tests pass after removal.
- **SC-007**: The dispatch flow for any issue completes successfully using only the classic path (format_issue_context_as_prompt + assign_copilot_to_issue).
- **SC-008**: Callers of assign_copilot_to_issue() (app_plan_orchestrator.py, auto_merge.py) function identically to before.
- **SC-009**: The pipeline orchestrator returns hardcoded legacy stages with no fleet dependency.
