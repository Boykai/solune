# Data Model: Solune MCP Server

**Feature**: 001-mcp-server | **Date**: 2026-03-31
**Input**: [spec.md](./spec.md), [research.md](./research.md)

## Entities

### 1. McpContext

**Purpose**: Per-request authentication context passed through `FastMCP` lifespan context to all tool handlers. Holds the resolved GitHub identity from token verification.

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `github_token` | `str` | Raw GitHub PAT from the MCP client's bearer token | Token verifier |
| `github_user_id` | `int` | Numeric GitHub user ID resolved from `GET /user` | GitHub API |
| `github_login` | `str` | GitHub username (login) resolved from `GET /user` | GitHub API |

**Relationships**: Created by `GitHubTokenVerifier` during auth, consumed by all MCP tool handlers.

**Validation Rules**:
- `github_token` must be non-empty
- `github_user_id` must be a positive integer
- `github_login` must be a non-empty string

**Notes**: This is a runtime dataclass, not persisted to the database. Lifetime is scoped to a single MCP request.

---

### 2. TokenCacheEntry

**Purpose**: Cached token verification result to avoid redundant GitHub API calls within the TTL window (FR-007).

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `token_hash` | `str` | SHA-256 hash of the raw token (cache key) | Computed |
| `access_token` | `AccessToken` | MCP SDK `AccessToken` with client_id and scopes | Token verifier |
| `github_token` | `str` | Raw token for service instantiation | MCP client |
| `github_user_id` | `int` | Resolved GitHub user ID | GitHub API |
| `github_login` | `str` | Resolved GitHub username | GitHub API |
| `expires_at` | `float` | Expiration timestamp (`time.monotonic() + TTL`) | Computed |

**Relationships**: Stored in `GitHubTokenVerifier._cache` dict, keyed by `token_hash`.

**Validation Rules**:
- `expires_at` must be in the future at time of use
- Entry is evicted if `time.monotonic() > expires_at`

**State Transitions**:
- **Created**: On first successful token verification
- **Hit**: On subsequent verification within TTL → return cached result
- **Expired**: When `time.monotonic() > expires_at` → evict and re-verify
- **Invalidated**: On verification failure for a previously cached token → evict immediately

**Notes**: In-memory only, not persisted. Lost on server restart (acceptable — tokens are re-verified on next request).

---

### 3. RateLimitEntry

**Purpose**: Tracks token verification attempts for rate limiting (FR-009).

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `token_hash` | `str` | SHA-256 hash of the token being rate-limited | Computed |
| `attempts` | `deque[float]` | Sliding window of attempt timestamps | Computed |

**Relationships**: Stored in `GitHubTokenVerifier._rate_limits` dict, keyed by `token_hash`.

**Validation Rules**:
- Maximum 10 attempts per 60-second sliding window
- Expired entries (older than 60s) are pruned on each access

**State Transitions**:
- **Under limit**: Attempt count < 10 within window → allow verification
- **Rate limited**: Attempt count ≥ 10 within window → reject immediately (return `None`)

**Notes**: In-memory only. Piggyback cleanup — old entries pruned when new attempts arrive.

---

### 4. MCP Server Configuration (Settings)

**Purpose**: Feature flag and server name configuration in `config.py` (FR-002, FR-004).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `mcp_server_enabled` | `bool` | `False` | Whether the MCP server endpoint is mounted |
| `mcp_server_name` | `str` | `"solune"` | Name passed to `FastMCP` constructor |

**Relationships**: Read by `main.py` at startup to decide whether to create and mount the MCP server.

**Validation Rules**:
- `mcp_server_name` must be a non-empty string
- When `mcp_server_enabled` is `False`, no MCP routes are registered

**Notes**: Follows existing settings pattern (pydantic-settings, env var override). Environment variables: `MCP_SERVER_ENABLED`, `MCP_SERVER_NAME`.

---

### 5. MCP Tool (Runtime)

**Purpose**: A callable operation exposed via MCP, registered at server creation time.

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `name` | `str` | Tool identifier (e.g., `list_projects`, `launch_pipeline`) | Decorator |
| `description` | `str` | Human-readable description (auto-extracted from docstring) | Docstring |
| `parameters` | `JSON Schema` | Auto-generated from Python type hints | Type hints |
| `handler` | `async callable` | The tool implementation function | Module |
| `domain` | `str` | Logical grouping (projects, pipelines, tasks, etc.) | Module path |

**Relationships**: Registered on the `FastMCP` instance. Each tool accesses `McpContext` via `ctx.request_context.lifespan_context`.

**Notes**: Not persisted — tools are registered at server startup. The MCP SDK handles schema generation automatically from type hints + docstrings.

---

### 6. MCP Resource Template (Runtime)

**Purpose**: Subscribable data endpoint identified by a URI template (FR-031).

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `uri_template` | `str` | URI pattern (e.g., `solune://projects/{project_id}/pipelines`) | Decorator |
| `description` | `str` | Human-readable description | Docstring |
| `handler` | `async callable` | Returns current state for the resource | Module |
| `mime_type` | `str` | Response content type (always `application/json`) | Static |

**Relationships**: Registered on the `FastMCP` instance. Subscribers notified via `ctx.session.send_resource_updated(uri)`.

**Notes**: Three resource templates planned:
1. `solune://projects/{project_id}/pipelines` — all pipeline states
2. `solune://projects/{project_id}/board` — current board state
3. `solune://projects/{project_id}/activity` — recent activity feed

---

### 7. MCP Prompt Template (Runtime)

**Purpose**: Pre-defined workflow template for guided agent interactions (FR-036).

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `name` | `str` | Prompt identifier (e.g., `create-project`, `daily-standup`) | Decorator |
| `description` | `str` | Human-readable description | Docstring |
| `arguments` | `list[PromptArgument]` | Optional parameters for the prompt | Type hints |
| `handler` | `async callable` | Returns prompt messages | Module |

**Relationships**: Registered on the `FastMCP` instance. Returns structured messages that guide agent behavior.

**Notes**: Three prompts planned:
1. `create-project` — guided project creation flow
2. `pipeline-status` — check all running pipelines
3. `daily-standup` — summarize recent activity across projects

---

## Entity Relationship Diagram

```text
┌─────────────────┐       creates        ┌──────────────┐
│ GitHubTokenVeri- │─────────────────────▶│  McpContext   │
│ fier             │                      │  (per-request)│
│                  │                      └──────┬───────┘
│  _cache:         │                             │
│   TokenCacheEntry│                             │ accessed by
│  _rate_limits:   │                             │
│   RateLimitEntry │                             ▼
└─────────────────┘                      ┌──────────────┐
                                         │  MCP Tools   │
┌─────────────────┐       reads          │  (22 total)  │
│ Settings         │────────────────────▶│              │
│  mcp_server_     │                     └──────┬───────┘
│  enabled/name    │                            │
└─────────────────┘                             │ delegates to
                                                │
┌─────────────────┐       mounts         ┌──────▼───────┐
│ main.py          │────────────────────▶│  FastMCP     │
│  (lifespan)      │                     │  Instance    │
└─────────────────┘                      │              │
                                         │  tools: 22   │
                                         │  resources: 3│
                                         │  prompts: 3  │
                                         └──────────────┘
                                                │
                                                │ calls
                                                ▼
                                         ┌──────────────┐
                                         │ Service Layer │
                                         │ (existing)    │
                                         │               │
                                         │ GitHubProjects│
                                         │ Service       │
                                         │ AgentsService │
                                         │ ChatAgent     │
                                         │ pipelines.py  │
                                         └──────────────┘
```

## Existing Entities Referenced (Not Modified)

These entities are consumed by MCP tools but not modified by this feature:

| Entity | Location | Used By |
|--------|----------|---------|
| `GitHubProjectsService` | `services/github_projects/` | All project/board/issue tools |
| `AgentsService` | `services/agents/service.py` | Agent management tools |
| `ChatAgentService` | `services/chat_agent.py` | `send_chat_message` tool |
| `ConnectionManager` | `services/websocket.py` | Resource change notifications |
| `UserSession` | `models/user.py` | Pattern reference for auth context |
| Pipeline state stores | `services/pipelines/` | Pipeline tools + pipeline resource |
| `mcp_configurations` table | `services/mcp_store.py` | Pattern reference for MCP CRUD |
| `DIFFICULTY_PRESET_MAP` | `services/agent_tools.py` | Dynamic pipeline template tools |

## Database Changes

**No new database tables or migrations required.** All new entities (`McpContext`, `TokenCacheEntry`, `RateLimitEntry`) are in-memory runtime structures. MCP tools read from existing tables (pipeline states, project data, agent configs) via the existing service layer.
