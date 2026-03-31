# Feature Specification: Solune MCP Server

**Feature Branch**: `001-mcp-server`  
**Created**: 2026-03-31  
**Status**: Draft  
**Input**: User description: "Plan: v0.4.0 — Solune MCP Server"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - External Agent Discovers and Calls Solune Tools (Priority: P1)

An external AI agent (e.g., VS Code Copilot, Claude Desktop, or a custom MCP client) connects to the Solune MCP server, authenticates with a GitHub Personal Access Token, browses the list of available tools, and calls a tool to retrieve project data. The agent uses the standard MCP protocol over Streamable HTTP transport without needing any Solune-specific client code.

**Why this priority**: This is the foundational use case — without tool discovery and invocation, the MCP server provides no value. Every subsequent story depends on external agents being able to connect, authenticate, and call tools.

**Independent Test**: Can be fully tested by connecting any MCP-compatible client to the server endpoint, listing available tools, and invoking `list_projects` with a valid GitHub PAT. Delivers immediate value by enabling external agents to query Solune project data.

**Acceptance Scenarios**:

1. **Given** the MCP server is enabled and running, **When** an external agent connects to the MCP endpoint with a valid GitHub PAT, **Then** the connection is established and the agent receives a list of all available tools with their descriptions and parameter schemas.
2. **Given** an authenticated MCP connection, **When** the agent calls `list_projects`, **Then** the server returns the user's GitHub projects with names, IDs, and URLs in structured data.
3. **Given** an authenticated MCP connection, **When** the agent calls `get_board(project_id)` for a project the user has access to, **Then** the server returns the full kanban board state including columns and items.
4. **Given** an external agent attempts to connect without a token, **When** the connection request is made, **Then** the server rejects the request with an authentication error.

---

### User Story 2 - External Agent Creates Tasks and Launches Pipelines (Priority: P2)

An external AI agent uses the MCP server to create new tasks, issues, and launch development pipelines within a Solune project. The agent can describe work to be done, and Solune handles issue creation, sub-issue breakdown, and agent assignment — all through MCP tool calls.

**Why this priority**: Write operations (creating tasks, launching pipelines) are the highest-value actions for external agents. This transforms Solune from a read-only data source into a fully interactive project management partner that agents can orchestrate.

**Independent Test**: Can be fully tested by calling `create_task` with a project ID, title, and description, then verifying the task appears on the project board. Pipeline launch can be tested by calling `launch_pipeline` and verifying the pipeline state transitions.

**Acceptance Scenarios**:

1. **Given** an authenticated MCP connection with a project the user owns, **When** the agent calls `create_task(project_id, title, description)`, **Then** a new issue is created on GitHub, added to the project board, and sub-issues are generated as configured.
2. **Given** an authenticated MCP connection, **When** the agent calls `launch_pipeline(project_id, pipeline_id, issue_description)`, **Then** a parent issue is created, sub-issues are generated, and agents are assigned to begin work.
3. **Given** an authenticated MCP connection, **When** the agent calls `create_issue(project_id, title, body, labels)`, **Then** a new issue is created with the specified labels and added to the project.
4. **Given** a pipeline that has a failed agent assignment, **When** the agent calls `retry_pipeline(project_id, issue_number)`, **Then** the failed assignment is retried and the pipeline state is updated.

---

### User Story 3 - Authentication and Project Access Scoping (Priority: P2)

The MCP server authenticates every connection using a GitHub Personal Access Token and enforces project-level access control. Users can only access projects they have permissions for on GitHub, ensuring the MCP server inherits the same security model as the existing application.

**Why this priority**: Security is co-equal with write operations. Without proper auth and access scoping, the MCP server cannot be safely exposed. This must ship alongside or before any write tools.

**Independent Test**: Can be tested by connecting with tokens of varying permission levels and verifying that project access is correctly scoped — a user without access to a project receives an authorization error when trying to call tools on that project.

**Acceptance Scenarios**:

1. **Given** a valid GitHub PAT, **When** the MCP server verifies the token, **Then** the user's GitHub identity (login, user ID) is resolved and cached for the session.
2. **Given** an authenticated user, **When** the user calls a tool referencing a project they do not have access to, **Then** the server returns an authorization error without executing the tool.
3. **Given** an invalid or expired GitHub PAT, **When** the MCP server attempts to verify the token, **Then** the connection is rejected with a clear authentication error.
4. **Given** multiple rapid authentication attempts from the same source, **When** the rate limit is exceeded, **Then** further verification attempts are temporarily blocked.

---

### User Story 4 - Agent and App Management via MCP (Priority: P3)

An external agent uses the MCP server to manage custom GitHub agents, applications, and recurring maintenance tasks. This includes listing agents, creating new agents, checking app health, and triggering chores — extending the MCP server beyond project/issue management into full platform administration.

**Why this priority**: Management tools provide breadth to the MCP server's capabilities but are not essential for the core workflow of project management and pipeline orchestration. They add significant value for power users and automated workflows.

**Independent Test**: Can be tested by calling `list_agents(project_id)` and verifying the response contains agent definitions, or by calling `get_app_status(app_name)` and verifying health check results.

**Acceptance Scenarios**:

1. **Given** an authenticated MCP connection, **When** the agent calls `list_agents(project_id)`, **Then** the server returns all custom GitHub agents configured for the project.
2. **Given** an authenticated MCP connection, **When** the agent calls `list_apps()`, **Then** the server returns all managed applications with their current status.
3. **Given** an authenticated MCP connection, **When** the agent calls `trigger_chore(project_id, chore_id)`, **Then** the specified maintenance chore is executed and the result is returned.
4. **Given** an authenticated MCP connection, **When** the agent calls `send_chat_message(project_id, message)`, **Then** the message is processed by Solune's AI agent and a response is returned.

---

### User Story 5 - Real-Time Status Subscriptions (Priority: P3)

An external agent subscribes to Solune resources (pipeline states, board updates, activity feeds) and receives real-time notifications when data changes. When a pipeline stage completes or a board item moves, subscribed agents are automatically notified without polling.

**Why this priority**: Real-time subscriptions enhance the developer experience significantly but require the core tool infrastructure to be in place first. This is an advanced capability that differentiates Solune from simpler MCP servers.

**Independent Test**: Can be tested by subscribing to a project's pipeline resource, triggering a pipeline state change, and verifying the client receives a resource-updated notification.

**Acceptance Scenarios**:

1. **Given** an authenticated MCP connection, **When** the agent subscribes to `solune://projects/{project_id}/pipelines`, **Then** the agent receives the current pipeline state and is registered for future updates.
2. **Given** an active resource subscription, **When** a pipeline stage completes or an agent is assigned, **Then** the subscribed client receives a resource-updated notification with the new state.
3. **Given** an active board resource subscription, **When** an item is moved on the board (via MCP, REST API, or UI), **Then** the subscribed client receives a notification with the updated board state.

---

### User Story 6 - Self-Documentation and Guided Workflows (Priority: P3)

The MCP server provides rich self-documentation through tool descriptions, parameter schemas, and prompt templates. External agents can use built-in prompts for common workflows like project creation, pipeline status checks, and daily standups — reducing the learning curve for new integrations.

**Why this priority**: Discovery and documentation are important for adoption but do not block core functionality. Prompt templates add convenience on top of the existing tool infrastructure.

**Independent Test**: Can be tested by connecting an MCP client, browsing the server's instructions and prompts, and invoking the `daily-standup` prompt to verify it generates a structured activity summary.

**Acceptance Scenarios**:

1. **Given** an MCP client connects to the server, **When** the client requests server information, **Then** it receives a description of Solune's capabilities and a full catalog of tools with descriptions and parameter schemas.
2. **Given** an authenticated MCP connection, **When** the agent invokes the `daily-standup` prompt, **Then** it receives a structured summary of recent activity across the user's projects.
3. **Given** an external agent, **When** it requests the MCP connection configuration endpoint, **Then** it receives the server URL, transport type, and authentication requirements needed to connect.

---

### Edge Cases

- What happens when the GitHub API is unreachable during token verification? The server should return a clear error indicating the authentication service is temporarily unavailable, without caching the failure.
- What happens when a user's GitHub PAT is revoked mid-session? Subsequent tool calls should fail with an authentication error, and the cached token should be invalidated.
- What happens when a tool call references a project ID that does not exist? The server should return a clear "project not found" error, distinguishable from an access-denied error.
- What happens when the MCP server feature flag is disabled? The MCP endpoint should not be mounted, and requests to the MCP path should return a standard 404 response.
- What happens when multiple MCP clients connect simultaneously with different tokens? Each connection should maintain its own authentication context without cross-contamination.
- What happens when a pipeline launch fails due to missing configuration? The tool should return a descriptive error with the specific configuration issue, not a generic server error.
- What happens when the token verification cache expires during a long-running tool call? The tool call should complete with the originally verified credentials; re-verification occurs on the next call.
- How does the system handle very large board states (hundreds of items)? Responses should be paginated or bounded to prevent excessive response sizes.

## Requirements *(mandatory)*

### Functional Requirements

**Server Foundation**

- **FR-001**: System MUST expose an MCP-compatible server endpoint that accepts connections from any standard MCP client using Streamable HTTP transport.
- **FR-002**: System MUST allow the MCP server to be enabled or disabled via a configuration flag, defaulting to disabled.
- **FR-003**: System MUST serve the MCP endpoint as part of the existing application process, sharing the same database connections and service layer — not as a separate server.
- **FR-004**: System MUST provide a configurable server name for the MCP instance, defaulting to "solune".

**Authentication & Authorization**

- **FR-005**: System MUST authenticate all MCP connections using a GitHub Personal Access Token provided as a bearer token.
- **FR-006**: System MUST verify tokens by resolving the associated GitHub user identity (login, user ID) from the GitHub API.
- **FR-007**: System MUST cache verified token results for a short duration (60 seconds) to reduce external API calls, while still ensuring revoked tokens are detected within a reasonable window.
- **FR-008**: System MUST enforce project-level access scoping — every tool that accepts a project ID MUST validate the authenticated user has access to that project before executing.
- **FR-009**: System MUST rate-limit token verification attempts to prevent abuse.
- **FR-010**: System MUST reject connections with invalid, expired, or missing tokens with clear error messages.

**Tier 1 Tools — Projects & Board**

- **FR-011**: System MUST provide a `list_projects` tool that returns the authenticated user's GitHub projects with names, IDs, and URLs.
- **FR-012**: System MUST provide a `get_project` tool that returns detailed information about a specific project including status columns.
- **FR-013**: System MUST provide a `get_board` tool that returns the full kanban board state (columns and items) for a project.
- **FR-014**: System MUST provide a `get_project_tasks` tool that returns all items and issues in a project.

**Tier 1 Tools — Issue & Task Creation**

- **FR-015**: System MUST provide a `create_task` tool that creates a new issue, adds it to the project board, and generates sub-issues as configured.
- **FR-016**: System MUST provide a `create_issue` tool that creates a new issue with optional labels and adds it to a project.

**Tier 1 Tools — Pipelines**

- **FR-017**: System MUST provide a `list_pipelines` tool that returns available pipeline configurations for a project.
- **FR-018**: System MUST provide a `launch_pipeline` tool that creates a parent issue, generates sub-issues, and starts agent assignments.
- **FR-019**: System MUST provide a `get_pipeline_states` tool that returns all active pipeline states with stage progress.
- **FR-020**: System MUST provide a `retry_pipeline` tool that retries failed agent assignments for a given pipeline.

**Tier 1 Tools — Activity & Status**

- **FR-021**: System MUST provide a `get_activity` tool that returns a paginated activity feed for a project.
- **FR-022**: System MUST provide an `update_item_status` tool that moves an item to a different status column on the board.

**Tier 2 Tools — Management**

- **FR-023**: System MUST provide tools for agent management: `list_agents`, `create_agent`.
- **FR-024**: System MUST provide tools for app management: `list_apps`, `get_app_status`, `create_app`.
- **FR-025**: System MUST provide tools for maintenance: `list_chores`, `trigger_chore`.
- **FR-026**: System MUST provide a `get_metadata` tool for retrieving repository context (labels, branches, milestones, collaborators).
- **FR-027**: System MUST provide a `cleanup_preflight` tool for previewing stale branches and pull requests.
- **FR-028**: System MUST provide a `send_chat_message` tool for natural language interaction with Solune's AI agent.

**Pipeline Templates**

- **FR-029**: System MUST dynamically register convenience tools for each pipeline preset (e.g., `launch_easy_pipeline`, `launch_medium_pipeline`) at server initialization time.
- **FR-030**: Each pipeline template tool MUST delegate to the base `launch_pipeline` tool with the appropriate preset configuration.

**Resource Subscriptions**

- **FR-031**: System MUST expose pipeline states, board state, and activity feeds as subscribable MCP resources using URI templates.
- **FR-032**: System MUST notify subscribed MCP clients when resource data changes (pipeline stage completion, board item movement, new activity).
- **FR-033**: System MUST integrate resource change notifications with the existing real-time broadcast mechanism so that changes from any source (MCP, REST API, UI) trigger notifications.

**Self-Documentation & Discovery**

- **FR-034**: System MUST provide server-level instructions describing Solune's capabilities for connected MCP clients.
- **FR-035**: Every tool MUST have a descriptive name, description, and auto-generated parameter schema derived from its signature.
- **FR-036**: System MUST provide prompt templates for common workflows: guided project creation, pipeline status check, and daily standup summary.
- **FR-037**: System MUST provide an endpoint that returns MCP connection configuration details (URL, transport type, auth requirements) for external agent setup.

**Shared Service Layer**

- **FR-038**: All MCP tools MUST delegate to the same backend service layer used by the REST API and internal agent tools — there MUST be a single source of truth for all business logic.
- **FR-039**: System MUST NOT duplicate business logic between MCP tools, REST API endpoints, and internal agent tools.

### Key Entities

- **MCP Server Instance**: The MCP server runtime including its configuration (name, feature flag state), registered tools, resources, and prompts. Controlled by the feature flag.
- **MCP Connection**: A client session with an authenticated GitHub identity, scoped to the user's accessible projects. Each connection has its own authentication context.
- **Tool**: A callable operation exposed via MCP, with a name, description, parameter schema, and access control rules. Tools are organized by domain (projects, pipelines, tasks, agents, apps, chores, activity, chat).
- **Resource**: A subscribable data endpoint identified by a URI template (e.g., `solune://projects/{id}/board`). Clients receive notifications when the underlying data changes.
- **Prompt Template**: A pre-defined workflow template (e.g., "daily-standup") that guides agents through common multi-step interactions.
- **Token Cache Entry**: A cached GitHub token verification result containing the resolved user identity and an expiration timestamp. Entries are evicted after the TTL or when verification fails.

### Assumptions

- GitHub Personal Access Tokens are the sole authentication mechanism for MCP connections. OAuth flows are not needed because MCP clients typically provide tokens directly.
- The 60-second token cache TTL balances performance (avoiding per-request GitHub API calls) with security (detecting revoked tokens within a reasonable window).
- Pipeline preset configurations are loaded from the database at server initialization. If presets change, the server must be restarted to pick up new convenience tools.
- MCP resource subscriptions use the existing real-time infrastructure. No new message broker or pub/sub system is introduced.
- The MCP server runs in the same process as the main application. Scaling the MCP server independently is not in scope for this version.
- Rate limiting for token verification uses a simple per-source counter. Integration with external rate-limiting infrastructure is deferred.
- All MCP tool responses use JSON format for structured data interchange.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An external MCP client can connect, authenticate, list tools, and call `list_projects` in under 5 seconds end-to-end.
- **SC-002**: All 12 Tier 1 tools are callable and return correct, structured data matching the same results as the corresponding REST API endpoints.
- **SC-003**: All 10 Tier 2 tools (agent, app, chore, metadata, cleanup, chat) are callable and return correct results.
- **SC-004**: Token verification rejects invalid tokens 100% of the time, and cached token lookups avoid redundant external verification calls for at least 95% of repeat requests within the cache window.
- **SC-005**: Project access scoping correctly denies access for 100% of tool calls where the authenticated user lacks permissions on the referenced project.
- **SC-006**: Resource subscriptions deliver change notifications to subscribed clients within 2 seconds of the underlying data change.
- **SC-007**: Pipeline template convenience tools are automatically registered for all configured presets at server startup, and each produces identical results to calling `launch_pipeline` directly.
- **SC-008**: The MCP server endpoint is completely inaccessible (returns 404) when the feature flag is disabled, with no residual routes or handlers.
- **SC-009**: The MCP connection configuration endpoint returns valid, machine-readable connection details that an external agent can use to auto-configure its MCP client.
- **SC-010**: All MCP tools produce results consistent with the REST API and internal agent tools — no data discrepancies across the three interfaces for the same operation.
