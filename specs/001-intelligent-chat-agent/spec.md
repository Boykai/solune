# Feature Specification: Complete v0.2.0 — Intelligent Chat Agent

**Feature Branch**: `001-intelligent-chat-agent`  
**Created**: 2026-03-30  
**Status**: Draft  
**Input**: User description: "Complete v0.2.0 — Intelligent Chat Agent (Microsoft Agent Framework)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Difficulty Assessment & Pipeline Selection (Priority: P1)

As a user chatting with Solune, I want the agent to evaluate the complexity of my project idea and automatically recommend the appropriate pipeline configuration, so I receive the right level of tooling and agents without manually configuring pipelines.

**Why this priority**: This is the core intelligence layer. Without difficulty assessment, the agent cannot make informed decisions about pipeline selection, and every subsequent workflow (autonomous creation, pipeline launch) depends on knowing the project's complexity. This delivers immediate value — users no longer need to understand pipeline presets to get started.

**Independent Test**: Can be fully tested by describing a project idea in chat (e.g., "Build me a stock tracking app with React and Azure") and verifying that the agent responds with a complexity rating and recommended pipeline configuration. Delivers value by giving users actionable guidance on project scope even without autonomous creation.

**Acceptance Scenarios**:

1. **Given** a user describes a simple project idea (e.g., "Create a static landing page"), **When** the agent processes the message, **Then** the agent assesses the difficulty as XS and recommends the "github-copilot" pipeline preset with an explanation of why this level fits.
2. **Given** a user describes a complex project idea (e.g., "Build a multi-tenant SaaS with payment processing and real-time dashboards"), **When** the agent processes the message, **Then** the agent assesses the difficulty as L or XL and recommends the "hard" or "expert" pipeline preset with reasoning.
3. **Given** a user describes a moderately complex project, **When** the agent assesses difficulty, **Then** the agent provides a clear explanation of the assessed complexity level and the pipeline preset it maps to, including what stages and agents are included.
4. **Given** a user provides a vague or ambiguous project description, **When** the agent cannot confidently assess difficulty, **Then** the agent asks clarifying questions before making an assessment, or defaults to a "medium" assessment with a note that more details could refine the recommendation.

---

### User Story 2 - Autonomous Project Creation from Chat (Priority: P2)

As a user, I want the agent to create a GitHub issue and launch the selected pipeline for my project directly from our chat conversation, so I can go from idea to active development pipeline in a single interaction without leaving the chat interface.

**Why this priority**: This is the flagship workflow that differentiates Solune — turning a chat conversation into real project artifacts. It depends on difficulty assessment (P1) and represents the full end-to-end value proposition of the intelligent chat agent. Without this, users must still manually create issues and configure pipelines.

**Independent Test**: Can be tested by enabling autonomous creation, describing a project in chat, confirming when asked, and verifying that a GitHub issue is created and a pipeline is launched. The created issue and pipeline run should be visible in GitHub and the Solune dashboard respectively.

**Acceptance Scenarios**:

1. **Given** a user has described a project and difficulty has been assessed, **When** autonomous creation is enabled, **Then** the agent asks "Shall I proceed?" before creating the GitHub issue, creates the issue upon confirmation, and reports back the issue number and URL.
2. **Given** a user confirms project creation, **When** the issue is created successfully, **Then** the agent launches the selected pipeline preset and reports the pipeline status including which stages and agents will run.
3. **Given** autonomous creation is disabled (default), **When** a user asks the agent to create a project, **Then** the agent presents a detailed proposal with the project name, assessed difficulty, selected preset, and estimated pipeline stages — but does not create any resources. The user can review and manually proceed.
4. **Given** the agent asks "Shall I proceed?" and the user declines, **When** the user says no or requests changes, **Then** the agent does not create any resources and offers to adjust the plan.
5. **Given** a GitHub API error occurs during issue creation, **When** the agent fails to create the issue, **Then** the agent reports the error clearly to the user and suggests next steps (e.g., check permissions, retry).

---

### User Story 3 - MCP Tool Extensibility for Projects (Priority: P3)

As a user, I want the chat agent to dynamically load and use MCP (Model Context Protocol) tool servers configured for my project, so the agent has access to project-specific tools and capabilities beyond its built-in toolset.

**Why this priority**: This is a foundation layer for future extensibility. While the full MCP marketplace is planned for a later version, enabling the agent to read and use project-configured MCP servers provides immediate value for power users and lays the groundwork for the tool ecosystem. It does not block the core P1/P2 workflows.

**Independent Test**: Can be tested by configuring an MCP tool server for a project and verifying that the agent loads and includes those tools when initialized for that project. If no MCP tools are configured, the agent should function normally with its built-in tools only.

**Acceptance Scenarios**:

1. **Given** a project has MCP tool servers configured, **When** the agent is initialized for a chat session in that project, **Then** the agent loads and makes available the configured MCP tools alongside its built-in tools.
2. **Given** a project has no MCP tool configurations, **When** the agent is initialized, **Then** the agent functions normally with only its built-in tools and no errors occur.
3. **Given** an MCP tool configuration is invalid or the server is unreachable, **When** the agent attempts to load MCP tools, **Then** the agent logs the error, skips the invalid configuration, and continues with its built-in tools.

---

### Edge Cases

- What happens when difficulty assessment falls on a boundary between two levels (e.g., between S and M)? The agent should select the higher pipeline preset and explain the reasoning to the user.
- How does the system handle a GitHub API failure during issue creation? The agent reports a user-friendly error and does not leave the system in an inconsistent state (no orphaned pipelines without issues).
- What if the pipeline service is unavailable after an issue is successfully created? The agent reports the issue was created successfully and that the pipeline launch will need to be retried, with clear instructions on how.
- What if a user changes their project requirements mid-conversation after difficulty is assessed? The agent should allow re-assessment — the assessed difficulty is not locked and can be updated.
- What happens during the full creation workflow (assess → select → create → launch) if one step fails? Each step should be independently recoverable; the agent should report which step succeeded and which failed.
- What if the user's GitHub session lacks repository write access? The agent reports a clear permission error and suggests the user log out and sign in again to refresh permissions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an automated difficulty assessment that classifies project complexity on a five-level scale (XS, S, M, L, XL) based on the user's project description.
- **FR-002**: System MUST map assessed difficulty levels to pipeline presets using a deterministic one-to-one mapping: XS → "github-copilot", S → "easy", M → "medium", L → "hard", XL → "expert".
- **FR-003**: System MUST explain the assessed difficulty and selected pipeline preset to the user, including what the preset provides (stages, agent roles).
- **FR-004**: System MUST record the assessed difficulty and selected preset in the conversation session state so subsequent tools can reference them.
- **FR-005**: System MUST support creating GitHub issues autonomously from the chat conversation, using the project details gathered during the conversation.
- **FR-006**: System MUST enforce a confirmation step — the agent asks "Shall I proceed?" before creating any external resources (issues, pipelines), regardless of whether autonomous creation is enabled.
- **FR-007**: System MUST provide an opt-in configuration setting for autonomous project creation, defaulting to disabled. When disabled, the agent presents proposals instead of creating resources.
- **FR-008**: System MUST support launching a pipeline after successful issue creation, reporting the pipeline status back to the user.
- **FR-009**: System MUST follow a defined workflow sequence: clarify → assess difficulty → select preset → create issue → launch pipeline → report back.
- **FR-010**: System MUST handle the new pipeline launch action in the agent's response processing, so the chat interface can display pipeline launch results appropriately.
- **FR-011**: System MUST dynamically load MCP tool server configurations for a given project when initializing the chat agent, passing them to the agent runtime.
- **FR-012**: System MUST gracefully handle missing, invalid, or unreachable MCP tool configurations by falling back to built-in tools without errors.
- **FR-013**: System MUST fall back to the "medium" pipeline preset when difficulty assessment returns an unrecognized or ambiguous value.

### Key Entities

- **Difficulty Assessment**: Represents the agent's evaluation of a project's complexity. Attributes include the assessed level (XS/S/M/L/XL), the reasoning behind the assessment, and the timestamp. Stored in the conversation session state.
- **Pipeline Preset**: A predefined pipeline configuration template that maps to a difficulty level. Each preset defines a set of stages and agent roles appropriate for the project's complexity.
- **Project Issue**: A GitHub issue created by the agent representing the user's project. Contains the project title, description, and links to the selected pipeline configuration.
- **Pipeline Launch**: Represents the execution of a pipeline for a project. Contains the pipeline identifier, selected preset, stages to execute, and status.
- **MCP Tool Configuration**: A project-specific configuration that defines external MCP tool servers the agent can use. Includes the server endpoint, configuration content, and sync status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can go from describing a project idea to having a created GitHub issue and running pipeline in a single chat conversation, completing the full workflow in under 5 minutes.
- **SC-002**: The system correctly assesses difficulty and selects an appropriate pipeline preset for at least 80% of project descriptions, as measured by alignment with manual expert assessments.
- **SC-003**: Pipeline preset selection always results in a valid, launchable configuration — 100% of selections map to an existing preset with defined stages and agents.
- **SC-004**: Disabling autonomous creation completely prevents the agent from creating external resources (issues, pipelines) while preserving all other agent capabilities (assessment, selection, proposals).
- **SC-005**: The full multi-step workflow (assess → select → create → launch) completes successfully with streaming status updates visible to the user at each step.
- **SC-006**: MCP tool loading adds no more than 2 seconds to agent initialization time, and failures in MCP loading do not prevent the agent from functioning.
- **SC-007**: All existing chat agent functionality (task creation, issue recommendation, status updates, clarifying questions, transcript analysis) continues to work without regression after the new tools are added.

## Assumptions

- The existing pipeline preset definitions are sufficient for all five difficulty levels. No new presets need to be created as part of this feature.
- The existing GitHub issue creation service handles authentication and permission validation. This feature reuses it without modification.
- The existing pipeline service handles pipeline execution. This feature reuses it without modification.
- The agent framework supports sequential multi-tool calls (4+ tools in sequence) with streaming events.
- The MCP tool configuration model already stores the necessary data to convert into agent-compatible MCP server configurations.
- The agent's confirmation prompt ("Shall I proceed?") is always shown before resource creation, even when autonomous creation is enabled, to maintain predictable user experience.
- Pipeline launch scope is full trigger with a status message (not configure-only).
- Data retention, error handling, and authentication follow existing patterns established in the v0.2.0 agent implementation.

## Dependencies

- Existing chat agent service and agent framework implementation (v0.2.0 foundation).
- Existing pipeline preset definitions and pipeline management service.
- Existing GitHub issue creation service.
- Existing MCP tool configuration data model and project-level MCP tool configurations.
- Agent framework tool registration and session state management capabilities.
- GitHub API access with appropriate repository permissions for issue creation.

## Scope Boundaries

**In Scope**:
- Four new agent tools: difficulty assessment, pipeline preset selection, project issue creation, pipeline launch.
- Configuration setting for opt-in autonomous creation.
- Agent instruction updates for the new workflow sequence.
- Response handling for the new pipeline launch action type.
- Foundation MCP tool loading for project-specific agent capabilities.
- Unit tests for all new tools and response handling.

**Out of Scope**:
- Full MCP marketplace or dynamic MCP tool discovery (deferred to v0.4.0).
- Changes to the pipeline execution engine itself.
- Changes to the GitHub API layer.
- New UI components for pipeline visualization (existing chat UI handles action responses).
- Heuristic-based difficulty assessment — assessment relies on the agent's reasoning, not rule-based logic.
- Multi-user or team-based difficulty consensus.
