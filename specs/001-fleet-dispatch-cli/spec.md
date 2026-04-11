# Feature Specification: Fleet-Dispatch Agent Pipelines via GitHub CLI

**Feature Branch**: `001-fleet-dispatch-cli`  
**Created**: 2026-04-11  
**Status**: Draft  
**Input**: User description: "Fleet-Dispatch Agent Pipelines via GitHub CLI"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Dispatch a Full Agent Pipeline from the Command Line (Priority: P1)

A pipeline operator wants to dispatch a complete agent pipeline (multiple agents across sequential and parallel groups) from the command line without relying on the Python backend. They invoke a single shell command, point it at a pipeline configuration file, and the script creates the required sub-issues in the target repository, assigns each agent via the appropriate dispatch mechanism, and respects group execution order — running parallel groups concurrently and serial groups one agent at a time.

**Why this priority**: This is the core value of the feature. Without the ability to dispatch agents from the CLI, none of the other stories (monitoring, config extraction) deliver value. A working dispatch script is the minimum viable product.

**Independent Test**: Can be fully tested by invoking the script with a sample pipeline config against a test repository and verifying that sub-issues are created with the correct labels, agents are assigned, and parallel groups launch concurrently.

**Acceptance Scenarios**:

1. **Given** a valid pipeline config file with three groups (G1 serial: architect; G2 parallel: tester, quality-assurance, designer; G3 parallel: judge, linter), **When** the operator invokes the dispatch script with the config and a target repository, **Then** the script creates one sub-issue per agent, assigns agents in group order, and dispatches all G2 agents concurrently after G1 completes.
2. **Given** a pipeline config and the `--dry-run` flag, **When** the operator invokes the dispatch script, **Then** the script prints the planned sub-issues and agent assignments without making any changes to the repository.
3. **Given** a pipeline config referencing an agent that does not exist in the repository, **When** the script attempts dispatch, **Then** the script reports a clear error identifying the invalid agent and skips that assignment without failing the entire pipeline.

---

### User Story 2 — Extract Pipeline Configuration to a Standalone File (Priority: P2)

A pipeline operator or contributor wants the pipeline group and agent definitions to live in a standalone configuration file that both the shell dispatch script and the Python backend can consume. Today the pipeline definitions are embedded inside Python code. By extracting them to a shared format, changes to pipeline structure can be made in one place and used by both dispatch paths.

**Why this priority**: The dispatch script (P1) needs a config file to consume. Extracting the config also reduces duplication between the shell and Python dispatch paths, preventing drift. This is a prerequisite for reliable fleet dispatch.

**Independent Test**: Can be tested by extracting the config, then verifying that both the shell script and the existing Python orchestrator produce identical agent assignments when given the same input.

**Acceptance Scenarios**:

1. **Given** the current pipeline definitions in the Python backend, **When** a contributor runs the extraction process, **Then** a standalone config file is produced that lists all groups, their execution mode (sequential or parallel), and the ordered list of agents per group.
2. **Given** a standalone config file, **When** the shell dispatch script reads it, **Then** the script correctly interprets group ordering, execution modes, and agent assignments without requiring any Python runtime.
3. **Given** a standalone config file, **When** the Python backend loads it, **Then** the backend produces the same pipeline behavior as the current embedded definitions.

---

### User Story 3 — Template Custom Instructions for Shell-Based Dispatch (Priority: P3)

A pipeline operator wants custom instructions (the context prompt sent to each agent) to be generated from reusable templates that the shell script can populate without the Python backend. Currently, custom instructions are built by Python functions that combine issue context, PR context, and agent-specific output instructions. Templates must be readable and fillable by standard shell tools so the dispatch script can produce equivalent instructions.

**Why this priority**: Custom instructions are critical for agent quality — agents without proper context produce poor results. However, the dispatch script (P1) can initially use a simplified instruction format and still deliver value. Full template parity is an enhancement.

**Independent Test**: Can be tested by generating custom instructions from the template for a sample issue/agent and comparing the output to what the Python backend would produce for the same inputs.

**Acceptance Scenarios**:

1. **Given** an issue number, agent name, and optional PR branch, **When** the shell script generates custom instructions from the template, **Then** the output includes the issue title, body, comments, agent-specific output instructions, and PR context (if provided).
2. **Given** a template file and an agent name of "speckit.specify", **When** instructions are generated, **Then** the output includes the directive to commit to `spec.md`.
3. **Given** an issue with no comments, **When** instructions are generated, **Then** the comments section is omitted gracefully rather than showing empty placeholders.

---

### User Story 4 — Monitor Agent Completion and Pipeline Progress (Priority: P4)

A pipeline operator wants to monitor the progress of a dispatched fleet — seeing which agents have completed, which are still running, and whether any have failed. The monitoring uses available CLI commands to poll agent status and report aggregate pipeline health.

**Why this priority**: Monitoring is essential for production use but is not needed for the initial dispatch to work. Operators can manually check issue status in GitHub as a workaround until monitoring is built.

**Independent Test**: Can be tested by dispatching a small pipeline, waiting for at least one agent to complete, and verifying the monitoring output reflects the correct status for each agent.

**Acceptance Scenarios**:

1. **Given** a running pipeline with a unique run ID, **When** the operator invokes the monitoring command, **Then** the output shows each agent's current status (pending, running, completed, failed) grouped by pipeline group.
2. **Given** a parallel group where 2 of 3 agents have completed, **When** the operator checks status, **Then** the output shows the group as "in progress" with per-agent completion detail.
3. **Given** a completed pipeline, **When** the operator checks status, **Then** the output shows an overall "completed" status with a summary of agent results.

---

### Edge Cases

- What happens when the GitHub CLI authentication token is expired or missing? The script must detect the authentication failure on the first dispatch attempt and exit with a clear error message before creating any sub-issues.
- What happens when a parallel group dispatch partially fails (e.g., 2 of 3 agents assigned successfully, 1 fails)? The script must report which agents succeeded and which failed, and continue monitoring the successful agents rather than aborting the entire pipeline.
- What happens when the target repository does not have Copilot agent access enabled? The dispatch must fail gracefully with an actionable error message.
- What happens when the pipeline config file is malformed or references unknown groups? The script must validate the config before creating any sub-issues and report all validation errors at once.
- What happens when the network drops mid-dispatch during a parallel group? Agents already dispatched must continue; the script must track which agents were successfully dispatched and allow retry of only the failed ones.
- What happens when two fleet dispatches target the same parent issue concurrently? The script must use unique run IDs to prevent sub-issue and label collisions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a shell script (`fleet-dispatch.sh`) that accepts a pipeline config file path and a target repository identifier to dispatch a complete agent pipeline.
- **FR-002**: System MUST create one sub-issue per agent in the target repository, with appropriate labels linking each sub-issue to the parent issue and pipeline run.
- **FR-003**: System MUST dispatch agents using the full-featured assignment mechanism that supports custom agent name, model selection, custom instructions, and base branch reference.
- **FR-004**: System MUST execute parallel groups by dispatching all agents in the group concurrently and waiting for all to complete before advancing to the next group.
- **FR-005**: System MUST execute sequential groups by dispatching agents one at a time, polling for completion before dispatching the next agent.
- **FR-006**: System MUST support a `--dry-run` mode that prints the planned actions without making any changes.
- **FR-007**: System MUST validate the pipeline configuration file before beginning dispatch and report all errors before creating any sub-issues.
- **FR-008**: System MUST produce a standalone pipeline configuration file that defines groups, execution modes, and agent assignments in a format consumable by both the shell script and the Python backend.
- **FR-009**: System MUST generate custom instructions for each agent from reusable templates that can be populated with issue context, PR context, and agent-specific directives using standard shell tools.
- **FR-010**: System MUST provide a monitoring command that reports per-agent and per-group status for a given pipeline run.
- **FR-011**: System MUST assign a unique run ID to each pipeline dispatch to prevent collisions when multiple dispatches target the same repository.
- **FR-012**: System MUST handle partial failures in parallel groups by continuing to monitor successfully dispatched agents and reporting failures for the rest.
- **FR-013**: System MUST exit with a clear, actionable error message when authentication, permissions, or repository access prerequisites are not met.
- **FR-014**: System MUST support specifying a base branch for all agent PRs in the pipeline via a `--base-ref` flag.
- **FR-015**: System MUST support specifying a model override for all agents in the pipeline via a `--model` flag, with per-agent overrides in the config taking precedence.
- **FR-016**: System MUST log all dispatch actions (sub-issue creation, agent assignment, completion events) to a state file for auditability and retry support.

### Key Entities

- **Pipeline Configuration**: Defines the ordered list of groups, each group's execution mode (sequential or parallel), and the agents within each group. Each agent entry includes agent name, optional model override, and optional custom instruction template reference.
- **Pipeline Run**: A single execution of a pipeline configuration against a target repository and parent issue. Identified by a unique run ID. Tracks the status of every agent in every group.
- **Agent Assignment**: Represents one agent being dispatched to one sub-issue. Carries the agent name, model, custom instructions, base branch, and resulting sub-issue number.
- **Fleet State**: The aggregate status of a pipeline run, including per-agent statuses (pending, running, completed, failed), per-group progress, and overall pipeline health.
- **Custom Instruction Template**: A reusable text template with placeholders for issue context, PR context, and agent-specific output directives. Populated at dispatch time by the shell script.

## Assumptions

- The GitHub CLI (`gh`) version 2.80 or later is installed and authenticated on the machine running the dispatch script.
- The target repository has GitHub Copilot agent access enabled and the dispatching user has appropriate permissions.
- The `gh api graphql` command is used for dispatch because it is the only CLI entry point that exposes the full `agentAssignment` input fields (customAgent, model, customInstructions, baseRef).
- Pipeline configurations use a JSON format as it is natively parseable by `jq`, which is a standard CLI tool available in most CI/CD environments.
- Custom instruction templates use `envsubst`-style variable substitution (e.g., `${ISSUE_TITLE}`, `${AGENT_NAME}`) for shell compatibility.
- The polling interval for completion monitoring defaults to 30 seconds, matching the existing Python backend polling behavior.
- Standard POSIX shell features (background processes, `wait`, `trap`) are sufficient for parallel dispatch without requiring additional dependencies.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can dispatch a full pipeline (5+ agents across 3+ groups) in under 2 minutes of wall-clock time from a single command invocation.
- **SC-002**: Parallel groups of 3 or more agents dispatch concurrently, with all agents starting within 10 seconds of each other.
- **SC-003**: The dispatch script produces identical sub-issue structure and agent assignments as the current Python backend for the same pipeline configuration.
- **SC-004**: The standalone pipeline configuration file is the single source of truth — changes made to it are reflected in both the shell and Python dispatch paths without additional synchronization.
- **SC-005**: An operator can determine the status of every agent in a running pipeline within 30 seconds by invoking the monitoring command.
- **SC-006**: Partial failures in parallel groups do not block monitoring or completion detection of successfully dispatched agents — the pipeline reports per-agent results.
- **SC-007**: The dispatch script can be run from any CI/CD environment with `gh` and `jq` installed, with no Python runtime dependency.
- **SC-008**: 100% of dispatch actions (sub-issue creation, agent assignment, status changes) are logged to the state file for post-run audit.
