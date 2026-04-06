# MCP HTTP Auth Contract

Feature scope: secure the protected MCP transport mounted by `/home/runner/work/solune/solune/solune/backend/src/main.py` and align MCP resource authorization with the existing tool authorization model.

## 1. HTTP transport contract

### Protected transport

| Item | Contract |
|---|---|
| Mount path | `/api/v1/mcp` |
| Implementation entrypoint | `/home/runner/work/solune/solune/solune/backend/src/services/mcp_server/server.py` via `streamable_http_app()` |
| Middleware | `/home/runner/work/solune/solune/solune/backend/src/services/mcp_server/middleware.py` |
| Auth mechanism | `Authorization: Bearer <GitHub PAT>` |
| Success precondition | `GitHubTokenVerifier.verify_token(token)` returns a valid access token and cached `McpContext` |

### Required HTTP behavior

| Condition | Expected result |
|---|---|
| Missing `Authorization` header | `401 Unauthorized`; request must not reach tool/resource handler |
| Malformed header (not `Bearer <token>`) | `401 Unauthorized` |
| Empty bearer token | `401 Unauthorized` |
| Invalid / expired token | `401 Unauthorized` |
| Token verification raises an exception or external auth call fails | `401 Unauthorized` |
| Valid token on protected MCP HTTP request | Request proceeds with request-scoped `McpContext` set |
| Non-HTTP scope (for example lifespan/websocket scope passed to the middleware) | Pass through without MCP HTTP auth enforcement |

## 2. Resource authorization contract

All MCP project resources must follow the same authorization pattern as existing tool handlers in `/home/runner/work/solune/solune/solune/backend/src/services/mcp_server/tools/__init__.py`:

1. Resolve the authenticated `McpContext`.
2. Verify project access for the requested `project_id`.
3. Only then load or serialize the resource payload.

### Protected MCP resource URIs

| Resource URI | Implementation file | Authorization expectation | Success payload |
|---|---|---|---|
| `solune://projects/{project_id}/pipelines` | `/home/runner/work/solune/solune/solune/backend/src/services/mcp_server/resources.py` | Require authenticated context and project access before filtering pipeline state | JSON string containing `project_id` and `pipeline_states` |
| `solune://projects/{project_id}/board` | same | Require authenticated context and project access even if the current payload is a placeholder note | JSON string containing `project_id` and board/access note |
| `solune://projects/{project_id}/activity` | same | Require authenticated context and project access before querying activity events | JSON string containing `project_id` and recent event data |

### Authorization outcomes

| Condition | Expected result |
|---|---|
| No authenticated MCP context | Authentication/authorization failure; caller receives unauthorized error behavior |
| Authenticated user lacks access to `project_id` | Forbidden/unauthorized project-access error |
| Authenticated user has access to `project_id` | Resource data returns successfully |
| Authenticated user is valid but project does not exist | Not-found/service error after auth succeeds |

## 3. Test contract

The implementation is complete only when tests prove the contract:

- Backend middleware coverage validates valid token flow, missing header, malformed bearer, empty token, exception path, non-HTTP pass-through, and 401 on failed auth.
- Backend resource coverage validates valid access, unauthorized project access, invalid project identifiers or missing projects, service exceptions, and JSON serialization behavior.
- Contract-adjacent auth tests validate exact cache bounds, stale rate-limit cleanup, timeout handling, and API error responses.
