# Data Model — Increase Test Coverage & Fix Discovered Bugs

This feature does not add a new persistent schema. It tightens behavior around existing backend auth/telemetry models and frontend UI state.

## Backend domain entities

### 1. MCP HTTP request

| Field | Type | Source | Validation / Rules |
|---|---|---|---|
| `scope.type` | `str` | Starlette ASGI scope | Authenticate only when scope type is HTTP MCP transport; preserve non-HTTP pass-through behavior. |
| `headers.authorization` | `Bearer <token>` | HTTP header | Required for protected MCP HTTP requests; missing, malformed, empty, invalid, or exception-throwing verification results in 401. |
| `path` | `"/api/v1/mcp"` | FastAPI mount path | Protected transport path mounted from `/home/runner/work/solune/solune/solune/backend/src/main.py`. |

**Relationships**: Feeds token verification in `GitHubTokenVerifier` and sets request-scoped `McpContext` for tool/resource handlers.

### 2. `McpContext`

| Field | Type | Source | Validation / Rules |
|---|---|---|---|
| `github_token` | `str` | Verified PAT | Present only after successful token verification. |
| `github_user_id` | `int` | GitHub `/user` response | Required to build MCP auth context. |
| `github_login` | `str` | GitHub `/user` response | Required for project-access lookup. |

**Relationships**: Consumed by `verify_mcp_project_access()` before any project-scoped resource/tool response is returned.

### 3. `TokenCacheEntry`

| Field | Type | Validation / Rules |
|---|---|---|
| `access_token` | `AccessToken` | Cached only after successful verification. |
| `mcp_context` | `McpContext` | Must correspond to the same token hash. |
| `expires_at` | `float` monotonic timestamp | Entry is expired when `expires_at <= now`. |

**State transitions**: `cache miss -> verified -> cached -> expired/evicted`.  
**Invariant**: Cache size must remain `<= max_cache_size` after insertion and eviction.

### 4. `RateLimitEntry`

| Field | Type | Validation / Rules |
|---|---|---|
| `attempts` | `deque[float]` | Only timestamps inside the sliding window count toward rate limiting. |

**State transitions**: `empty -> active attempts -> stale/pruned`.  
**Invariant**: Stale entries should be removable without breaking active rate limits.

### 5. Protected MCP resource request

| Field | Type | Validation / Rules |
|---|---|---|
| `resource_uri` | `str` | One of `solune://projects/{project_id}/pipelines`, `solune://projects/{project_id}/board`, `solune://projects/{project_id}/activity`. |
| `project_id` | `str` | Must match a project visible to the authenticated GitHub user. |
| `response_payload` | JSON string | Returned only after auth and authorization succeed. |

**Relationships**: Resource handlers depend on `McpContext` and the GitHub project-access check before reading pipeline state, board placeholder data, or activity events.

### 6. OTel initialization outcome

| Field | Type | Validation / Rules |
|---|---|---|
| `otel_enabled` | `bool` | Comes from settings. |
| `tracer` | `Tracer \| None` | Set on success; left unset on graceful fallback. |
| `meter` | `Meter \| None` | Set on success; left unset on graceful fallback. |
| `warning_logged` | `bool` | Required when startup falls back because the exporter endpoint is unreachable. |

**State transitions**: `disabled -> no-op`, `enabled -> initialized`, `enabled -> startup failure -> graceful fallback`.

## Frontend UI state entities

### 7. AddAgentModal form state

| Field | Type | Validation / Rules |
|---|---|---|
| `selectedToolIds` | `string[]` | Drives tool selection. |
| `toolsError` | `string \| null` | Must clear from an effect or event, never during render. |
| `editAgent` | `AgentConfig \| undefined` | Determines create vs. edit flow. |

### 8. AddChoreModal interaction state

| Field | Type | Validation / Rules |
|---|---|---|
| `isOpen` | `boolean` | Escape handling must stay reliable across re-renders. |
| `onClose/resetAndClose` | callback / ref | Listener cleanup must not depend on a stale closure. |
| `template_content` | `string` | Validation errors should persist correctly until user correction. |

### 9. ChoreCard animation state

| Field | Type | Validation / Rules |
|---|---|---|
| `animationFrameId` | `number \| null` | Any pending frame must be cancelled during unmount. |
| `menu state` | local UI state | Must not update after unmount. |

### 10. ToolSelectorModal state

| Field | Type | Validation / Rules |
|---|---|---|
| `searchQuery` | `string` | Must persist across re-renders while the modal remains open. |
| `selectedTools` | `string[]` | Initialization/sync may run in effects, not during render. |

### 11. CommandPalette focus state

| Field | Type | Validation / Rules |
|---|---|---|
| `focusableElements` | `HTMLElement[]` | Tab handling must always prevent default when the palette is open. |
| `selectedIndex` | `number` | Existing keyboard navigation semantics should remain intact. |

## Coverage-oriented test entities

| Test Area | Existing on branch | Planned additions |
|---|---|---|
| Backend MCP auth | `test_auth.py`, MCP tool/server tests | Add middleware/resource-focused suites; extend auth edge cases. |
| Backend observability | none specific to graceful startup | Add OTel graceful-degradation tests. |
| Frontend modal/component tests | `AddAgentModal`, `AddChoreModal`, `InstallConfirmDialog`, `ChoreScheduleConfig` | Expand existing tests plus add missing suites for the scoped components. |
| Frontend hooks | many hooks already covered, but not `useCountdown` or `useFirstErrorFocus` | Add focused hook tests to close feature-specific gaps. |
