# Feature Specification: Fleet-Dispatch Agent Pipelines via GitHub CLI

**Feature Branch**: `001-fleet-dispatch-pipelines`  
**Created**: 2026-04-12  
**Status**: Draft  
**Input**: User description: "Fleet-Dispatch Agent Pipelines via GitHub CLI"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dispatch a Full Agent Pipeline from the CLI (Priority: P1)

A pipeline operator launches the fleet-dispatch script, pointing it at a pipeline configuration file and a parent issue. The script reads the config, creates the required sub-issues, and dispatches every agent in each group — running agents within the same parallel group concurrently and waiting for each serial group to complete before advancing to the next.

**Why this priority**: This is the core value proposition. Without the ability to dispatch agents from the CLI, none of the downstream monitoring or config features matter.

**Independent Test**: Can be fully tested by running the fleet-dispatch script against a test repository with a sample pipeline config containing at least one serial group and one parallel group, verifying that sub-issues are created and agents are assigned with the correct parameters (customAgent, model, customInstructions, baseRef).

**Acceptance Scenarios**:

1. **Given** a valid pipeline config file and a parent issue number, **When** the operator runs the fleet-dispatch script with the config, issue number, and repository, **Then** sub-issues are created for every agent in the pipeline, each agent is dispatched via the GraphQL mutation with the full agentAssignment payload, and agents in the same parallel group are dispatched concurrently.
2. **Given** a pipeline config with three groups (G1 serial, G2 parallel, G3 parallel), **When** the script executes, **Then** G1 agents run sequentially, G2 agents are dispatched concurrently after G1 completes, and G3 agents are dispatched concurrently after G2 completes.
3. **Given** the script is run without a valid GitHub authentication token, **When** the dispatch is attempted, **Then** the script exits with a clear authentication error before creating any sub-issues.

---

### User Story 2 - Standalone Pipeline Configuration (Priority: P2)

A pipeline maintainer defines agent groups, execution order, models, and custom instruction templates in a standalone JSON configuration file that is consumed by the fleet-dispatch script. This decouples pipeline definitions from the Python backend, enabling CLI-only workflows.

**Why this priority**: The config file is essential for the dispatch script to know which agents to run and how. Without it, the script has no input. This is a prerequisite for User Story 1 but is lower priority because the config format could initially be hardcoded for testing.

**Independent Test**: Can be fully tested by validating a sample pipeline config against the JSON schema and confirming that the fleet-dispatch script correctly parses it, extracts agent groups, and identifies serial vs. parallel execution modes.

**Acceptance Scenarios**:

1. **Given** a pipeline config JSON file that matches the defined schema, **When** the fleet-dispatch script parses it, **Then** it correctly identifies all agent groups, their execution modes, agent slugs, model selections, and custom instruction templates.
2. **Given** a pipeline config with an invalid or missing required field, **When** the script attempts to parse it, **Then** it exits with a descriptive validation error identifying the missing or invalid field.
3. **Given** the existing Python backend preset definitions (Spec Kit, Medium, Hard, Expert), **When** these are exported to the standalone JSON format, **Then** each exported config passes schema validation and contains equivalent agent groups, ordering, and execution modes.

---

### User Story 3 - Monitor Agent Completion and Pipeline Progress (Priority: P3)

A pipeline operator monitors the progress of a dispatched fleet by polling agent task status. The script reports which agents have completed, which are still running, and whether any have failed — enabling the operator to track pipeline progress without accessing the web UI.

**Why this priority**: Monitoring is valuable for production use but not required for the initial dispatch capability. Operators can manually check issue status in the interim.

**Independent Test**: Can be fully tested by dispatching a known set of agents and polling their completion status, verifying that the script correctly reports completed, in-progress, and failed agents.

**Acceptance Scenarios**:

1. **Given** a fleet has been dispatched, **When** the operator runs a status check command, **Then** the script displays the current status of each agent (pending, active, completed, failed) along with the overall pipeline progress.
2. **Given** all agents in a group have completed successfully, **When** the status is polled, **Then** the group is marked complete and the pipeline advances to the next group if applicable.
3. **Given** an agent has failed (e.g., assignment error or session error), **When** the status is polled, **Then** the failure is reported with the agent name, error context, and the group is marked as having a failure.

---

### User Story 4 - Custom Instruction Templating (Priority: P3)

A pipeline maintainer uses template variables in custom instruction strings within the pipeline config, and the fleet-dispatch script resolves those templates at dispatch time using issue context (title, body, comments) — replicating the behavior of the Python backend's prompt formatting and body tailoring functions.

**Why this priority**: Templates enable richer agent instructions but are not required for basic dispatch. A minimal initial version could pass static instruction strings.

**Independent Test**: Can be fully tested by providing a pipeline config with template variables (e.g., `${ISSUE_TITLE}`, `${ISSUE_BODY}`, `${PARENT_ISSUE_NUMBER}`) and verifying that the script resolves them to the correct values fetched from the GitHub issue.

**Acceptance Scenarios**:

1. **Given** a pipeline config with custom instruction templates containing `${ISSUE_TITLE}` and `${ISSUE_BODY}`, **When** the fleet-dispatch script processes the config for an issue, **Then** the dispatched agents receive custom instructions with the actual issue title and body substituted in.
2. **Given** a template references a variable that cannot be resolved (e.g., issue has no body), **When** the script processes it, **Then** the unresolvable variable is replaced with an empty string and the dispatch proceeds without error.

---

### Edge Cases

- What happens when an agent dispatch fails mid-group in a parallel execution? The script should report the failure for that agent but allow other agents in the same parallel group to complete, then report the group as partially failed.
- What happens when the GitHub API rate limit is hit during fleet dispatch? The script should detect the rate-limit response, pause with an appropriate backoff, and retry the dispatch.
- What happens when a sub-issue already exists for an agent in the pipeline? The script should detect the existing sub-issue (by label or title match) and re-dispatch to the existing issue rather than creating a duplicate.
- How does the system handle very large pipelines (10+ agents)? The script should cap concurrent dispatches to a configurable limit to avoid overwhelming the API.
- What happens when the pipeline config references an agent that does not exist in the repository? The script should emit a warning and skip that agent, continuing with the rest of the pipeline.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a CLI script that accepts a pipeline configuration file, a parent issue number, and a repository identifier, and dispatches agents according to the configuration.
- **FR-002**: System MUST dispatch agents using the GitHub GraphQL mutation with the full agentAssignment payload (customAgent, model, customInstructions, baseRef), including the required feature flags header.
- **FR-003**: System MUST execute agents within the same parallel group concurrently and execute groups sequentially (each group completes before the next begins).
- **FR-004**: System MUST pre-create sub-issues for each agent with appropriate labels, title, and body before dispatching the agent assignment.
- **FR-005**: System MUST support a standalone JSON pipeline configuration file that defines agent groups, execution order (serial/parallel), agent slugs, model selections, and custom instruction templates.
- **FR-006**: System MUST validate the pipeline configuration file against a defined schema before attempting any dispatch, and exit with a descriptive error if validation fails.
- **FR-007**: System MUST resolve template variables in custom instruction strings (e.g., `${ISSUE_TITLE}`, `${ISSUE_BODY}`, `${PARENT_ISSUE_NUMBER}`) by fetching the parent issue context from GitHub before dispatch.
- **FR-008**: System MUST provide a completion-monitoring capability that polls agent task status and reports per-agent and per-group progress (pending, active, completed, failed).
- **FR-009**: System MUST handle authentication by using the existing CLI authentication context and exit with a clear error if not authenticated.
- **FR-010**: System MUST support a configurable concurrency limit for parallel dispatches to avoid overwhelming the API.
- **FR-011**: System MUST detect and handle API rate-limit responses with appropriate backoff and retry behavior.
- **FR-012**: System MUST detect existing sub-issues for an agent (by label or title match) and re-dispatch to the existing issue rather than creating duplicates.
- **FR-013**: System MUST produce the standalone JSON pipeline config by exporting or mirroring the existing backend preset pipeline definitions so that the CLI script consumes the same agent group topology.

### Key Entities

- **Pipeline Configuration**: A JSON file defining the ordered sequence of execution groups, where each group contains one or more agents with their dispatch parameters (slug, model, instruction template, execution mode).
- **Execution Group**: A logical grouping of agents within a pipeline that share an execution mode (serial or parallel) and an order index determining when the group runs relative to other groups.
- **Agent Dispatch**: A single unit of work representing one agent assignment: the sub-issue creation, mutation dispatch, and subsequent status tracking.
- **Fleet Run**: A single invocation of the fleet-dispatch script for a given parent issue, encompassing all sub-issue creations, agent dispatches, and completion monitoring for the full pipeline.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A pipeline operator can dispatch a full multi-agent pipeline (5+ agents across 3+ groups) from a single CLI command in under 60 seconds of script execution time (excluding agent processing time).
- **SC-002**: Agents within a parallel group are dispatched concurrently — total dispatch time for a parallel group of N agents is comparable to the time for a single dispatch (within 2× overhead), not N× sequential time.
- **SC-003**: The standalone pipeline configuration JSON file passes schema validation and contains equivalent agent groups to the existing backend presets with no information loss.
- **SC-004**: The fleet-dispatch script successfully dispatches agents using only the CLI tool and standard shell utilities — no Python runtime dependency is required.
- **SC-005**: Pipeline monitoring correctly reports the status of all dispatched agents within 30 seconds of a status change occurring.
- **SC-006**: 95% of dispatch attempts succeed on the first try under normal conditions (no rate limits, valid auth, network available).
- **SC-007**: Custom instruction templates are resolved correctly for all template variables, producing agent instructions equivalent to those generated by the existing backend prompt formatting functions.

## Assumptions

- The GitHub CLI (version 2.80+) is available and authenticated in the environment where the fleet-dispatch script runs.
- The GitHub GraphQL API continues to support the `addAssigneesToAssignable` mutation with the `agentAssignment` input and the required feature flags header.
- Standard POSIX shell utilities (bash, jq, wait, envsubst) are available on the dispatch machine.
- The parent issue and repository already exist before the fleet-dispatch script is invoked.
- Agent slugs in the pipeline config correspond to valid custom agents installed in the target repository.
- The existing backend preset definitions are the source of truth for agent group topology.
- Rate limits are the standard GitHub API limits; no special enterprise rate limits are assumed.
