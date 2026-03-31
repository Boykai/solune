# Research: Solune MCP Server

**Feature**: 001-mcp-server | **Date**: 2026-03-31
**Input**: [plan.md](./plan.md) Technical Context

## Research Tasks

### R-001: MCP Python SDK (`mcp` package) — FastMCP Integration

**Context**: The spec requires mounting an MCP server into the existing FastAPI app using `FastMCP` with Streamable HTTP transport.

**Decision**: Use `mcp>=1.26.0,<2` Python SDK with `FastMCP` class for server creation.

**Rationale**:
- `FastMCP` is the high-level API recommended by the MCP SDK for Python servers.
- It supports `stateless_http=True` for Streamable HTTP transport (the MCP-recommended production transport, replacing deprecated SSE transport).
- `json_response=True` ensures structured JSON responses for tool calls.
- The SDK auto-generates JSON Schema from Python type hints and docstrings — no manual schema maintenance.
- `FastMCP.streamable_http_app()` returns a Starlette ASGI app that can be directly mounted into FastAPI.

**Alternatives Considered**:
- **Low-level `mcp.server.Server`**: More control but requires manual transport setup, schema generation, and session management. Rejected — unnecessary complexity.
- **Separate MCP process**: Would require IPC or HTTP proxy. Rejected — violates FR-003 (shared process) and adds deployment complexity.
- **SSE transport**: Deprecated in MCP spec. Rejected — Streamable HTTP is the recommended replacement.

**Key Findings**:
- `FastMCP` constructor: `FastMCP(name, stateless_http=True, json_response=True, instructions=..., lifespan=...)`
- Tool registration: `@mcp.tool()` decorator on async functions. Context via `ctx: Context` parameter.
- Resource registration: `@mcp.resource("uri://template/{param}")` decorator.
- Prompt registration: `@mcp.prompt("name")` decorator.
- Auth: `FastMCP` accepts `token_verifier` parameter for custom token verification.
- Mount: `app.mount("/api/v1/mcp", mcp.streamable_http_app())` — standard Starlette ASGI mount.
- Lifespan: `FastMCP` lifespan context is accessible in tools via `ctx.request_context.lifespan_context`.
- Session manager: Must add `mcp.session_manager.run()` to the FastAPI lifespan for proper cleanup.

---

### R-002: Authentication — GitHub PAT Token Verification via MCP SDK

**Context**: MCP connections must be authenticated using GitHub PATs. The MCP SDK supports a `TokenVerifier` protocol.

**Decision**: Implement `GitHubTokenVerifier` class that implements the MCP SDK's `TokenVerifier` protocol. Verify tokens by calling `GET https://api.github.com/user` with the provided PAT. Cache verified results in a dict with 60-second TTL.

**Rationale**:
- The MCP SDK's `token_verifier` parameter accepts any object with a `verify_token(token) -> AccessToken | None` method.
- GitHub's `GET /user` endpoint is the standard way to validate a PAT and resolve the user identity. Returns login, id, and avatar_url.
- 60-second cache TTL (FR-007) balances performance with security — avoids per-request GitHub API calls while detecting revoked tokens within a minute.
- Token hash (SHA-256) used as cache key to avoid storing raw tokens in memory.

**Alternatives Considered**:
- **GitHub App installation tokens**: Would require GitHub App setup. Rejected — PATs are simpler and MCP clients typically provide tokens directly.
- **OAuth flow**: MCP clients don't have browser context for OAuth. Rejected — not practical for CLI/agent use cases.
- **JWT verification**: GitHub PATs are not JWTs. Rejected — not applicable.
- **No caching**: Would cause GitHub API rate limiting with high tool call volume. Rejected — unacceptable performance impact.

**Key Findings**:
- `TokenVerifier` protocol: `async def verify_token(self, token: str) -> AccessToken | None`
- `AccessToken` fields: `token: str`, `client_id: str`, `scopes: list[str]`
- Cache structure: `dict[str, tuple[AccessToken, float]]` where key is SHA-256 hash, value is (access_token, expiry_timestamp).
- Rate limiting: Simple counter per token hash with exponential backoff. Use `collections.defaultdict` for counters.
- Existing pattern: `verify_project_access()` in `dependencies.py` calls `svc.list_user_projects()` — reuse this pattern for per-tool project scoping.

---

### R-003: Starlette ASGI Mount — FastMCP into FastAPI

**Context**: The MCP server must be mounted into the existing FastAPI application at `/api/v1/mcp`.

**Decision**: Use `app.mount("/api/v1/mcp", mcp.streamable_http_app())` in `main.py`, guarded by the `mcp_server_enabled` feature flag. Add `mcp.session_manager.run()` to the lifespan.

**Rationale**:
- FastAPI inherits from Starlette and supports `app.mount()` for sub-applications.
- `FastMCP.streamable_http_app()` returns a standard Starlette ASGI app.
- Mounting at `/api/v1/mcp` keeps the MCP endpoint under the existing API prefix — consistent with the REST API structure.
- The feature flag in `config.py` allows disabling MCP without code changes (FR-002, edge case: flag disabled → 404).
- Session manager integration ensures proper cleanup of MCP sessions on shutdown.

**Alternatives Considered**:
- **Separate uvicorn process**: Would require port allocation and proxy. Rejected — violates FR-003 and complicates deployment.
- **FastAPI router instead of mount**: MCP SDK provides its own routing. Rejected — incompatible with the SDK's transport layer.
- **Mount at root `/mcp`**: Inconsistent with existing `/api/v1/` prefix. Rejected — breaks URL convention.

**Key Findings**:
- Mount order matters: mount MCP app *before* `include_router` for the API router to avoid route conflicts.
- The MCP app handles its own routing internally (POST for tool calls, GET for server info).
- CORS middleware on the parent FastAPI app does NOT propagate to mounted sub-applications — may need separate CORS handling if browser-based MCP clients are used (unlikely for v0.4.0).
- The MCP endpoint bypasses FastAPI's dependency injection — auth is handled by the MCP SDK's token verifier, not FastAPI's `Depends()`.

---

### R-004: Service Layer Reuse — Single Source of Truth Pattern

**Context**: MCP tools must delegate to the same service layer used by the REST API and internal agent tools (FR-038, FR-039).

**Decision**: MCP tools instantiate service classes per-call using the authenticated user's token from `McpContext`. Follow the same pattern as API endpoints: create a `GitHubProjectsService` instance with the user's token, call the appropriate method, and return structured data.

**Rationale**:
- The existing `GitHubProjectsService` (8 mixins) provides all the methods needed for Tier 1 and Tier 2 tools.
- API endpoints use `session.access_token` to create service instances — MCP tools use `ctx.request_context.lifespan_context.github_token` for the same purpose.
- No business logic duplication: MCP tools are thin wrappers that translate MCP parameters to service method calls and format the return values.

**Alternatives Considered**:
- **Shared singleton service**: Would require multi-tenant token management. Rejected — per-call instances are simpler and match the existing pattern.
- **Direct GitHub API calls from tools**: Would duplicate logic already in services. Rejected — violates FR-039.
- **Internal MCP client (agent calling itself)**: Adds HTTP round-trip latency. Rejected — deferred to future iteration per Phase 7 recommendation.

**Key Findings**:
- `GitHubProjectsService` mixins: `IssuesMixin`, `BoardMixin`, `BranchesMixin`, `ProjectsMixin`, `AgentsMixin`, `CopilotMixin`, `PRsMixin`, `RepositoryMixin`.
- Pipeline operations: `execute_pipeline_launch()` in `pipelines.py` handles the full pipeline lifecycle.
- Agent operations: `AgentsService` in `services/agents/service.py` handles agent CRUD.
- Chat operations: `ChatAgentService` in `services/chat_agent.py` handles chat messaging.
- Activity: Available via existing API modules — `activity.py`, `board.py`.
- Database: MCP tools need access to `aiosqlite.Connection` for pipeline state queries and MCP config reads.

---

### R-005: MCP Resources — Real-Time Subscriptions

**Context**: Expose pipeline states, board, and activity as subscribable MCP resources (FR-031–FR-033).

**Decision**: Register MCP resource templates using `@mcp.resource()` decorators with URI patterns like `solune://projects/{project_id}/pipelines`. Integrate with the existing `ConnectionManager.broadcast_to_project()` pattern to notify MCP subscribers when data changes.

**Rationale**:
- MCP resources are the standard way to expose subscribable data in the MCP protocol.
- URI templates allow parameterization by project_id — matching the existing WebSocket broadcast scope.
- The existing `ConnectionManager` already maintains per-project connections; MCP resource subscriptions follow the same pattern.
- `ctx.session.send_resource_updated(uri)` is the SDK method to notify subscribers.

**Alternatives Considered**:
- **Polling from clients**: Would increase server load and latency. Rejected — MCP resources provide push-based updates.
- **WebSocket passthrough**: MCP clients don't use raw WebSocket. Rejected — MCP resources are the standard mechanism.
- **Event sourcing**: Over-engineered for this use case. Rejected — simple notification-on-change is sufficient.

**Key Findings**:
- Resource registration: `@mcp.resource("solune://projects/{project_id}/pipelines")`
- Resource handler returns current state; subscriptions deliver deltas.
- Integration point: In `websocket.py` or a new notification hook, call MCP resource notification alongside WebSocket broadcast.
- Must handle case where MCP server is disabled (feature flag) — notification hook should be a no-op.

---

### R-006: Dynamic Tool Registration — Pipeline Templates

**Context**: Pipeline presets should be registered as convenience tools at server initialization (FR-029, FR-030).

**Decision**: At MCP server creation time, query pipeline configurations from the database. For each preset, dynamically register a tool function using Python closures and `mcp.tool()` API.

**Rationale**:
- Dynamic registration avoids hardcoding preset names — new presets are picked up on server restart.
- Closures capture the preset's pipeline_id, making each convenience tool a thin wrapper around `launch_pipeline`.
- The MCP SDK supports programmatic tool registration (not just decorators).

**Alternatives Considered**:
- **Static tool definitions**: Would require code changes for new presets. Rejected — fragile and doesn't scale.
- **Single `launch_pipeline` with preset parameter**: Already exists as the base tool. Rejected — convenience tools improve discoverability for external agents.
- **Plugin system**: Over-engineered. Rejected — simple closures achieve the same result.

**Key Findings**:
- Programmatic registration: `mcp.tool(name=..., description=...)(handler_function)`.
- Pipeline presets are stored in the database (pipeline configurations table).
- `DIFFICULTY_PRESET_MAP` in `agent_tools.py` maps preset labels to pipeline IDs: `{"XS": "github-copilot", "S": "easy", "M": "medium", "L": "hard", "XL": "expert"}`.
- Server restart required to pick up new presets (per spec assumption).

---

### R-007: MCP Prompt Templates — Guided Workflows

**Context**: Provide prompt templates for common workflows: project creation, pipeline status, daily standup (FR-036).

**Decision**: Register 3 MCP prompts using `@mcp.prompt()` decorator. Each prompt returns structured messages that guide the agent through a multi-step workflow.

**Rationale**:
- MCP prompts are the standard discovery mechanism for common workflows — agents can list prompts and invoke them.
- Prompts return message templates, not tool calls — the agent decides how to proceed based on the prompt content.
- Three prompts cover the primary workflows identified in the spec.

**Alternatives Considered**:
- **More prompts**: Could add prompts for every workflow. Rejected — start with three high-value prompts, expand based on usage.
- **No prompts**: Tools are sufficient for basic use. Rejected — prompts significantly improve discoverability for new integrations.

**Key Findings**:
- `@mcp.prompt("create-project")`: Returns instructions for guided project creation.
- `@mcp.prompt("pipeline-status")`: Returns instructions to check all running pipelines.
- `@mcp.prompt("daily-standup")`: Returns instructions to summarize recent activity.
- Prompt handlers can accept parameters (e.g., project_id) for context-specific guidance.

---

### R-008: Configuration and Feature Flag

**Context**: MCP server must be toggleable via configuration (FR-002, FR-004).

**Decision**: Add two settings to `config.py`: `mcp_server_enabled: bool = False` and `mcp_server_name: str = "solune"`. Check `mcp_server_enabled` in `main.py` before mounting the MCP app.

**Rationale**:
- Defaults to disabled — no impact on existing deployments.
- `mcp_server_name` allows customization without code changes.
- Feature flag pattern is already used in the codebase (e.g., `enable_docs`, `agent_streaming_enabled`).

**Alternatives Considered**:
- **Environment variable only**: Settings class already uses env vars via pydantic-settings. Rejected — no need for a separate mechanism.
- **Runtime toggle**: Would require re-mounting the app. Rejected — restart-based toggle is simpler and sufficient.

**Key Findings**:
- Settings pattern: `mcp_server_enabled: bool = False` with env var `MCP_SERVER_ENABLED`.
- Mount guard: `if settings.mcp_server_enabled: app.mount(...)`.
- When disabled, `/api/v1/mcp` returns 404 (edge case from spec).

---

### R-009: Rate Limiting for Token Verification

**Context**: FR-009 requires rate-limiting token verification attempts to prevent abuse.

**Decision**: Implement a simple in-memory rate limiter in the `GitHubTokenVerifier` class. Track verification attempts per token hash with a sliding window (e.g., max 10 attempts per minute per unique token). Use `time.monotonic()` for timestamps.

**Rationale**:
- Per-token (hashed) rate limiting prevents brute-force token guessing.
- In-memory counter is sufficient for a single-process deployment.
- Sliding window with `collections.deque` provides accurate rate tracking.
- Integrating with `slowapi` (existing rate limiter) is not practical because the MCP endpoint bypasses FastAPI middleware.

**Alternatives Considered**:
- **`slowapi` integration**: MCP mount bypasses FastAPI middleware. Rejected — would require custom ASGI middleware on the MCP app.
- **Redis-backed rate limiting**: Over-engineered for single-process deployment. Rejected — in-memory is sufficient.
- **No rate limiting**: Spec explicitly requires it (FR-009). Rejected — security requirement.

**Key Findings**:
- Rate limit scope: Per token hash, not per IP (more precise).
- Window: 10 attempts per 60 seconds.
- Exceeded: Return `None` from `verify_token()` (authentication failure).
- Cleanup: Expired entries cleaned on each verification attempt (piggyback cleanup).
