# Feature Specification: Fleet-Dispatch Agent Pipelines via GitHub CLI

**Feature Branch**: `001-fleet-dispatch-pipelines`  
**Created**: 2026-04-12  
**Status**: Draft  
**Input**: User description: "Fleet-Dispatch Agent Pipelines via GitHub CLI"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dispatch All Pipeline Agents via CLI Script (Priority: P1)

A pipeline operator wants to dispatch the full agent pipeline for a parent issue using a single shell command instead of relying on the Python backend. They run the fleet dispatch script with a pipeline configuration file and a parent issue number. The script pre-creates sub-issues for each agent, then dispatches agents group by group — serial groups run one agent at a time with completion polling, while parallel groups fire all agents concurrently and wait for all to finish before advancing to the next group.

**Why this priority**: This is the core capability — without it, fleet dispatch does not exist. It decouples agent orchestration from the Python backend and enables CLI-driven automation for any environment with `gh` installed.

**Independent Test**: Can be fully tested by running the script against a test repository with a sample pipeline config and verifying that sub-issues are created and agents are assigned via GraphQL mutations in the correct group order.

**Acceptance Scenarios**:

1. **Given** a valid pipeline config and a parent issue number, **When** the operator runs the fleet dispatch script, **Then** sub-issues are created for every agent defined in the config, labeled and linked to the parent issue.
2. **Given** a pipeline config with serial agents in Group 1, **When** the script dispatches Group 1, **Then** each agent is dispatched sequentially — the next agent starts only after the previous one completes.
3. **Given** a pipeline config with parallel agents in Group 2, **When** the script dispatches Group 2, **Then** all agents in the group are dispatched concurrently and the script waits for all to complete before proceeding.
4. **Given** the dispatch script is running, **When** a dispatched agent fails or times out, **Then** the script reports the failure with the agent name and sub-issue number, and continues with the remaining pipeline according to a configurable error strategy (fail-fast or continue).

---

### User Story 2 - Standalone Pipeline Configuration (Priority: P1)

A pipeline maintainer wants to define agent groups, execution modes, and agent metadata in a standalone configuration file (outside the Python backend) so that both the shell script and the backend can consume the same source of truth. They create or update a JSON config file that describes each group's agents, execution order, custom agent identifiers, models, and instruction template references.

**Why this priority**: The dispatch script cannot function without a consumable config. Decoupling the config from the Python backend ensures consistency and enables non-Python tooling to participate in orchestration.

**Independent Test**: Can be fully tested by validating a sample config against its schema and confirming the shell script reads and interprets every field correctly.

**Acceptance Scenarios**:

1. **Given** the existing pipeline stages defined in the Python backend, **When** the maintainer extracts them to a standalone JSON config, **Then** the config faithfully represents all groups, agents, execution modes, and ordering from the backend definition.
2. **Given** a standalone pipeline config file, **When** the shell script reads it, **Then** it correctly identifies each group's agents, their execution mode (serial or parallel), and the dispatch order.
3. **Given** the standalone config, **When** the Python backend loads it, **Then** it produces the same pipeline behavior as the current hardcoded definition.

---

### User Story 3 - Templated Custom Instructions (Priority: P2)

A pipeline maintainer wants to define agent-specific custom instructions as templates so the shell script can generate the same tailored prompts that the Python backend currently produces. They create template files with placeholders for issue context (title, body, comments, parent issue number) and the script substitutes values at dispatch time.

**Why this priority**: Custom instructions are essential for each agent to perform its specialized task. Without templates, the CLI dispatch would send agents generic or empty instructions, drastically reducing quality.

**Independent Test**: Can be fully tested by rendering a template for a known agent with sample issue context and comparing the output against the equivalent Python-generated prompt.

**Acceptance Scenarios**:

1. **Given** a set of instruction templates (one per agent role), **When** the dispatch script prepares a dispatch for a specific agent, **Then** it loads the correct template and substitutes all placeholders with actual issue context.
2. **Given** a template with placeholders for issue title, body, comments, and parent issue number, **When** the script renders it for a real issue, **Then** the resulting instructions are equivalent in content to what the Python backend's `format_issue_context_as_prompt()` and `tailor_body_for_agent()` produce.
3. **Given** a new custom agent is added to the pipeline config, **When** it has no dedicated template, **Then** the script falls back to a generic instruction template and logs a warning.

---

### User Story 4 - Monitor Pipeline Progress and Completion (Priority: P2)

A pipeline operator wants to monitor the progress of dispatched agents in near real-time and receive a summary when all groups complete. After launching the fleet dispatch, they can poll for agent task status and see which agents are in progress, completed, or failed.

**Why this priority**: Monitoring is essential for production use. Without visibility into agent progress, operators cannot diagnose stuck or failed agents and must manually inspect each sub-issue.

**Independent Test**: Can be fully tested by dispatching a small pipeline and verifying that the monitoring output correctly reflects the known states of each agent's sub-issue.

**Acceptance Scenarios**:

1. **Given** a fleet dispatch is in progress, **When** the operator requests a status check, **Then** the system displays each agent's current state (queued, in progress, completed, failed) with timestamps.
2. **Given** all agents in all groups have completed, **When** the final status check runs, **Then** the system displays a summary including total elapsed time, pass/fail counts, and links to each sub-issue.
3. **Given** an agent has been in progress beyond a configurable timeout, **When** the monitoring poll detects it, **Then** it flags the agent as potentially stuck and reports it prominently.

---

### User Story 5 - Dispatch a Single Agent Ad-Hoc (Priority: P3)

A developer or operator wants to re-dispatch a single agent from the pipeline (for example, to retry a failed linter run) without re-running the entire pipeline. They use the dispatch script with a flag specifying the target agent and an existing sub-issue.

**Why this priority**: Retry and selective dispatch reduces cycle time significantly. It is a convenience feature built on top of the core dispatch capability.

**Independent Test**: Can be fully tested by dispatching a single named agent to an existing sub-issue and verifying the GraphQL mutation is sent with the correct parameters.

**Acceptance Scenarios**:

1. **Given** an existing sub-issue for a specific agent, **When** the operator runs the dispatch script targeting only that agent, **Then** the script dispatches only that agent without affecting other sub-issues or groups.
2. **Given** a failed agent's sub-issue, **When** the operator re-dispatches it, **Then** the script unassigns Copilot first, then re-assigns with updated instructions if provided.

---

### Edge Cases

- What happens when the `gh` CLI is not installed or not authenticated? The script validates prerequisites and exits with a clear error message before any dispatch.
- What happens when a sub-issue creation fails mid-pipeline? The script logs the failure and either halts (fail-fast) or skips the affected agent and continues (continue mode), depending on config.
- What happens when the GitHub API rate limit is exceeded during dispatch? The script detects rate-limit responses, waits for the reset window, and retries the request.
- What happens when two operators run the dispatch script against the same parent issue concurrently? The script uses the parent issue as a lock signal — if sub-issues already exist for the pipeline, it warns the operator and offers to resume or abort.
- What happens when the pipeline config file is missing or malformed? The script validates the config against the schema before dispatch and exits with a descriptive error.
- What happens when a parallel group has only one agent? The script dispatches it as if it were serial (no background process overhead) but still follows group boundary logic.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a shell script (`fleet-dispatch.sh`) that accepts a pipeline configuration file and a parent issue identifier, and dispatches all agents defined in the config.
- **FR-002**: System MUST create sub-issues for each agent before dispatching, with labels linking them to the parent issue and the agent role.
- **FR-003**: System MUST dispatch agents using the GraphQL `addAssigneesToAssignable` mutation with full `agentAssignment` payload (customAgent, customInstructions, model, baseRef).
- **FR-004**: System MUST include the required GraphQL feature headers (`issues_copilot_assignment_api_support`, `coding_agent_model_selection`) with every dispatch request.
- **FR-005**: System MUST execute serial groups by dispatching agents one at a time, polling for completion between each dispatch.
- **FR-006**: System MUST execute parallel groups by dispatching all agents in the group concurrently and waiting for all to complete before advancing.
- **FR-007**: System MUST provide a standalone pipeline configuration file (JSON) that defines agent groups, execution modes, agent identifiers, model selections, and instruction template references.
- **FR-008**: System MUST validate the pipeline configuration against a schema before dispatch and reject invalid configs with descriptive errors.
- **FR-009**: System MUST generate custom instructions from templates by substituting issue context (title, body, comments, parent reference) into agent-specific template files.
- **FR-010**: System MUST fall back to a generic instruction template when an agent-specific template is not available.
- **FR-011**: System MUST poll for agent task completion status and report per-agent progress (queued, in progress, completed, failed).
- **FR-012**: System MUST produce a pipeline summary upon completion that includes elapsed time, per-agent status, and sub-issue references.
- **FR-013**: System MUST support dispatching a single named agent to an existing sub-issue for retry or ad-hoc dispatch scenarios.
- **FR-014**: System MUST validate that the `gh` CLI is installed and authenticated before attempting any dispatch.
- **FR-015**: System MUST handle dispatch failures with a configurable error strategy: "fail-fast" (halt pipeline on first failure) or "continue" (skip failed agent and proceed).

### Key Entities

- **Pipeline Config**: Defines the ordered groups of agents, each group's execution mode (serial/parallel), and per-agent metadata (agent identifier, model, instruction template reference). This is the portable source of truth shared between CLI and backend.
- **Agent Group**: A logical set of agents executed together. Serial groups dispatch one agent at a time; parallel groups dispatch all agents concurrently. Groups execute in defined order.
- **Sub-Issue**: A GitHub issue created for each agent in the pipeline, linked to the parent issue via labels and body references. Each sub-issue carries the tailored instructions for its assigned agent.
- **Dispatch Record**: The combination of a sub-issue, its assigned agent, and the GraphQL mutation sent. Used for monitoring, retry, and audit purposes.
- **Instruction Template**: A text file with placeholders for issue context values. Rendered at dispatch time to produce the custom instructions sent to each agent via the GraphQL mutation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can dispatch a full pipeline of agents for a parent issue using a single CLI command in under 2 minutes (excluding agent execution time).
- **SC-002**: Parallel groups dispatch all member agents within 10 seconds of each other, achieving true concurrent execution rather than sequential delays.
- **SC-003**: The standalone pipeline configuration produces identical agent dispatch behavior whether consumed by the CLI script or the Python backend.
- **SC-004**: Custom instructions generated by the CLI templates are functionally equivalent to those produced by the Python backend for all built-in agent roles.
- **SC-005**: The monitoring capability reports accurate agent status within 30 seconds of state changes, enabling operators to identify stuck or failed agents promptly.
- **SC-006**: Single-agent retry dispatch succeeds without affecting other agents or groups in the pipeline.
- **SC-007**: The dispatch script handles common failure scenarios (auth failure, rate limiting, invalid config, API errors) gracefully, providing actionable error messages for operators.
- **SC-008**: The entire fleet dispatch feature operates using only the `gh` CLI and standard shell utilities (bash, jq), with no dependency on the Python backend at runtime.

## Assumptions

- The `gh` CLI version 2.80+ is available in the dispatch environment, providing access to `gh api graphql` and `gh agent-task` commands.
- The GitHub repository has Copilot agent assignment enabled and the required GraphQL feature flags are active.
- The dispatch environment has `jq` installed for JSON processing in the shell script.
- Agent completion can be detected by polling `gh agent-task list` or checking sub-issue assignment status via the GitHub API.
- The existing Python backend will continue to function alongside the CLI dispatch — the CLI is an alternative dispatch path, not a replacement.
- Instruction templates use simple variable substitution (e.g., `envsubst` or similar) rather than a complex templating engine.
- The pipeline config schema will be defined as a JSON Schema document and shared between CLI validation and backend validation.

## Scope Boundaries

**In scope**:
- Shell script for fleet dispatch via `gh api graphql`
- Standalone JSON pipeline configuration with schema
- Instruction template system for custom agent prompts
- Completion polling and status monitoring
- Single-agent retry dispatch
- Error handling and prerequisite validation

**Out of scope**:
- Replacing the existing Python backend dispatch — the CLI is an additional dispatch path
- Modifying GitHub's CLI commands or API — the script works within existing capabilities
- Automated pipeline triggering from webhooks — the script is manually invoked
- Dashboard or web UI for monitoring — monitoring is CLI-output only
- Multi-repository fleet dispatch — scoped to a single repository per invocation
