# Tasks: Solune MCP Server

**Input**: Design documents from `/specs/001-mcp-server/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included — the plan (Phase 9) and spec explicitly request unit tests for auth and core tools, plus integration tests for MCP client↔server lifecycle.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/src/`, `solune/backend/tests/`
- Source package: `solune/backend/src/services/mcp_server/`
- Tool modules: `solune/backend/src/services/mcp_server/tools/`
- Tests: `solune/backend/tests/unit/test_mcp_server/`, `solune/backend/tests/integration/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the MCP SDK dependency and feature flag configuration

- [ ] T001 Add `mcp>=1.26.0,<2` dependency to `solune/backend/pyproject.toml` under `[project.dependencies]`
- [ ] T002 [P] Add `mcp_server_enabled: bool = False` and `mcp_server_name: str = "solune"` settings to `solune/backend/src/config.py` following the existing pydantic-settings pattern (env vars: `MCP_SERVER_ENABLED`, `MCP_SERVER_NAME`)
- [ ] T003 [P] Create `solune/backend/src/services/mcp_server/` package directory with `__init__.py` that exports `create_mcp_server()` and `get_mcp_app()`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core MCP server infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create `solune/backend/src/services/mcp_server/context.py` — define `McpContext` dataclass with fields: `github_token: str`, `github_user_id: int`, `github_login: str` per data-model.md. Include validation (non-empty token, positive user ID, non-empty login)
- [ ] T005 [P] Create `solune/backend/src/services/mcp_server/auth.py` — implement `GitHubTokenVerifier` class with `verify_token(token: str) -> AccessToken | None` method. Calls `GET https://api.github.com/user` via httpx with the provided PAT. Returns `AccessToken(token=token, client_id=str(github_user_id), scopes=[])`. Implements SHA-256 token hashing for cache keys, 60-second TTL cache (`dict[str, TokenCacheEntry]`), and rate limiting (max 10 attempts per 60s sliding window per token hash using `collections.deque`). Defines `TokenCacheEntry` and `RateLimitEntry` per data-model.md
- [ ] T006 Create `solune/backend/src/services/mcp_server/server.py` — implement `create_mcp_server()` function that instantiates `FastMCP("solune", stateless_http=True, json_response=True)` with a lifespan that initializes DB connection. Pass `token_verifier=GitHubTokenVerifier()` for auth. Set `instructions` parameter with Solune server description. Implement `get_mcp_app()` that returns `mcp.streamable_http_app()`. Register all tool, resource, and prompt modules
- [ ] T007 Create `solune/backend/src/services/mcp_server/tools/__init__.py` — empty package init for tool modules
- [ ] T008 Mount MCP server into FastAPI app — modify `solune/backend/src/main.py`: if `settings.mcp_server_enabled`, import and call `create_mcp_server()`, mount its `streamable_http_app()` at `/api/v1/mcp`, add `mcp.session_manager.run()` to the lifespan context manager. Log `"MCP server mounted at /api/v1/mcp"` on startup
- [ ] T009 [P] Create `solune/backend/tests/unit/test_mcp_server/__init__.py` — empty package init for MCP server unit tests

**Checkpoint**: Foundation ready — MCP server mounts, authenticates tokens, and is ready for tool registration

---

## Phase 3: User Story 1 — External Agent Discovers and Calls Solune Tools (Priority: P1) 🎯 MVP

**Goal**: An external MCP client connects, authenticates with a GitHub PAT, lists available tools, and calls read-only project/board tools via Streamable HTTP transport.

**Independent Test**: Connect any MCP client to `/api/v1/mcp` with a valid GitHub PAT → list tools → call `list_projects` → verify structured project data is returned.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T010 [P] [US1] Create `solune/backend/tests/unit/test_mcp_server/test_auth.py` — test `GitHubTokenVerifier`: valid token returns `AccessToken`, invalid token returns `None`, expired cache entry triggers re-verification, rate limiting blocks after 10 attempts in 60s, cache hit avoids GitHub API call, revoked token invalidates cache. Mock httpx calls to GitHub API
- [ ] T011 [P] [US1] Create `solune/backend/tests/unit/test_mcp_server/test_tools_projects.py` — test `list_projects`, `get_project`, `get_board`, `get_project_tasks` tools: mock `GitHubProjectsService` methods, verify correct service delegation and structured return data. Test project access validation rejects unauthorized users

### Implementation for User Story 1

- [ ] T012 [P] [US1] Create `solune/backend/src/services/mcp_server/tools/projects.py` — implement `list_projects` tool: `@mcp.tool()` async function, extract `McpContext` from `ctx.request_context.lifespan_context`, instantiate `GitHubProjectsService` with user's token, call `list_user_projects()`, return structured `{projects: [{project_id, name, url}]}`. (FR-011)
- [ ] T013 [US1] Add `get_project(project_id: str)` tool to `solune/backend/src/services/mcp_server/tools/projects.py` — validate project access via `verify_project_access()` pattern, call `GitHubProjectsService.get_project()`, return project details with status columns. (FR-012)
- [ ] T014 [US1] Add `get_board(project_id: str)` tool to `solune/backend/src/services/mcp_server/tools/projects.py` — validate project access, call `GitHubProjectsService.get_board_data()`, return full kanban state (columns + items). (FR-013)
- [ ] T015 [US1] Add `get_project_tasks(project_id: str)` tool to `solune/backend/src/services/mcp_server/tools/projects.py` — validate project access, call `GitHubProjectsService.get_board_data()`, return all items/issues with status, type, and labels. (FR-014)
- [ ] T016 [US1] Register project tools in `solune/backend/src/services/mcp_server/server.py` — import `tools/projects.py` and register all four tool functions on the FastMCP instance

**Checkpoint**: User Story 1 complete — external agents can connect, authenticate, discover tools, and query project/board data

---

## Phase 4: User Story 2 — External Agent Creates Tasks and Launches Pipelines (Priority: P2)

**Goal**: An external MCP client creates tasks, issues, and launches development pipelines through MCP tool calls. Write operations delegate to the same service layer as the REST API.

**Independent Test**: Call `create_task(project_id, title, description)` → verify issue created on GitHub and added to board. Call `launch_pipeline(project_id, pipeline_id, description)` → verify parent issue, sub-issues, and pipeline state.

### Tests for User Story 2

- [ ] T017 [P] [US2] Create `solune/backend/tests/unit/test_mcp_server/test_tools_pipelines.py` — test `list_pipelines`, `launch_pipeline`, `get_pipeline_states`, `retry_pipeline` tools: mock pipeline services, verify correct delegation to `execute_pipeline_launch()` and pipeline state store. Test project access validation

### Implementation for User Story 2

- [ ] T018 [P] [US2] Create `solune/backend/src/services/mcp_server/tools/tasks.py` — implement `create_task(project_id, title, description)` tool: validate project access, delegate to the same task creation logic as `POST /tasks` endpoint (create issue + add to project + generate sub-issues). Implement `create_issue(project_id, title, body, labels?)` tool: validate project access, call `GitHubProjectsService.create_issue()` + `add_issue_to_project()`. (FR-015, FR-016)
- [ ] T019 [P] [US2] Create `solune/backend/src/services/mcp_server/tools/pipelines.py` — implement `list_pipelines(project_id)` tool: validate project access, query pipeline configurations. (FR-017)
- [ ] T020 [US2] Add `launch_pipeline(project_id, pipeline_id, issue_description)` to `solune/backend/src/services/mcp_server/tools/pipelines.py` — validate project access, delegate to `execute_pipeline_launch()`, return parent issue, sub-issues, and pipeline state. (FR-018)
- [ ] T021 [US2] Add `get_pipeline_states(project_id)` to `solune/backend/src/services/mcp_server/tools/pipelines.py` — validate project access, query pipeline state store, return all active states with stage progress. (FR-019)
- [ ] T022 [US2] Add `retry_pipeline(project_id, issue_number)` to `solune/backend/src/services/mcp_server/tools/pipelines.py` — validate project access, delegate to pipeline retry logic, return success status and updated state. (FR-020)
- [ ] T023 [P] [US2] Create `solune/backend/src/services/mcp_server/tools/activity.py` — implement `get_activity(project_id, limit=20)` tool: validate project access, return paginated activity feed. Implement `update_item_status(project_id, item_id, status)` tool: validate project access, call `GitHubProjectsService.update_item_status()`, return new status. (FR-021, FR-022)
- [ ] T024 [US2] Register task, pipeline, and activity tools in `solune/backend/src/services/mcp_server/server.py` — import `tools/tasks.py`, `tools/pipelines.py`, `tools/activity.py` and register all tool functions on the FastMCP instance

**Checkpoint**: User Stories 1 AND 2 complete — external agents can read project data AND create tasks, launch/manage pipelines

---

## Phase 5: User Story 3 — Authentication and Project Access Scoping (Priority: P2)

**Goal**: Harden authentication with full token verification, caching, rate limiting, and per-tool project access validation. Ensure every tool enforces access control.

**Independent Test**: Connect with tokens of varying permission levels → verify user without access to a project gets authorization error. Verify rate limiting blocks after 10 rapid attempts.

### Implementation for User Story 3

> Note: Core auth was built in Phase 2 (T005). This phase adds hardening, edge case handling, and integration wiring.

- [ ] T025 [US3] Enhance `solune/backend/src/services/mcp_server/auth.py` — add error handling for GitHub API unreachability (return `None`, do NOT cache failures), add cache invalidation on verification failure for previously cached tokens, add `AuthSettings` configuration and wire into `FastMCP` constructor. Handle edge case: multiple simultaneous clients with different tokens (per-connection auth context isolation)
- [ ] T026 [US3] Create shared access validation helper in `solune/backend/src/services/mcp_server/tools/__init__.py` or a `solune/backend/src/services/mcp_server/access.py` module — implement `verify_mcp_project_access(ctx, project_id)` that extracts `McpContext` from the MCP context, instantiates `GitHubProjectsService`, and calls the `verify_project_access()` pattern from `dependencies.py`. Raise a descriptive error for access denied vs. project not found
- [ ] T027 [US3] Audit and ensure all project-scoped tools in `tools/projects.py`, `tools/tasks.py`, `tools/pipelines.py`, and `tools/activity.py` call `verify_mcp_project_access()` before executing. Add clear error messages for access denied, project not found, and authentication failures
- [ ] T028 [P] [US3] Add additional test cases to `solune/backend/tests/unit/test_mcp_server/test_auth.py` — test GitHub API unreachability handling, cache invalidation on token revocation, concurrent clients with different tokens, edge case for expired cache during long-running tool call

**Checkpoint**: User Stories 1, 2, AND 3 complete — full auth, access scoping, and rate limiting in place

---

## Phase 6: User Story 4 — Agent and App Management via MCP (Priority: P3)

**Goal**: Extend the MCP server with Tier 2 management tools for agents, apps, chores, metadata, cleanup, and chat.

**Independent Test**: Call `list_agents(project_id)` → verify agent definitions returned. Call `get_app_status(app_name)` → verify health check. Call `send_chat_message(project_id, message)` → verify AI agent response.

### Implementation for User Story 4

- [ ] T029 [P] [US4] Create `solune/backend/src/services/mcp_server/tools/agents.py` — implement `list_agents(project_id)` tool: validate project access, delegate to `AgentsService.list_agents()`, return agent list. Implement `create_agent(project_id, name, instructions, model?)` tool: validate project access, delegate to `AgentsService.create_agent()`, return agent ID and PR URL. (FR-023)
- [ ] T030 [P] [US4] Create `solune/backend/src/services/mcp_server/tools/apps.py` — implement `list_apps()` tool: return all managed apps with status. Implement `get_app_status(app_name)` tool: return health check. Implement `create_app(name, owner, template?, pipeline_id?)` tool: scaffold app with optional pipeline launch. (FR-024)
- [ ] T031 [P] [US4] Create `solune/backend/src/services/mcp_server/tools/chores.py` — implement `list_chores(project_id)` tool: validate project access, return chore list. Implement `trigger_chore(project_id, chore_id)` tool: validate project access, execute chore, return result. (FR-025)
- [ ] T032 [P] [US4] Create `solune/backend/src/services/mcp_server/tools/chat.py` — implement `send_chat_message(project_id, message)` tool: validate project access, delegate to `ChatAgentService.run()`, return AI response. Implement `get_metadata(owner, repo)` tool: delegate to `GitHubProjectsService` (RepositoryMixin), return labels, branches, milestones, collaborators. Implement `cleanup_preflight(project_id)` tool: validate project access, return stale branches/PRs preview. (FR-026, FR-027, FR-028)
- [ ] T033 [US4] Register all Tier 2 tools in `solune/backend/src/services/mcp_server/server.py` — import `tools/agents.py`, `tools/apps.py`, `tools/chores.py`, `tools/chat.py` and register all tool functions on the FastMCP instance

**Checkpoint**: User Story 4 complete — full platform administration via MCP (22 tools total)

---

## Phase 7: User Story 5 — Real-Time Status Subscriptions (Priority: P3)

**Goal**: Expose pipeline states, board state, and activity as subscribable MCP resources. Notify subscribed clients when data changes.

**Independent Test**: Subscribe to `solune://projects/{project_id}/pipelines` → trigger a pipeline state change → verify client receives a `resource-updated` notification.

### Implementation for User Story 5

- [ ] T034 [US5] Create `solune/backend/src/services/mcp_server/resources.py` — register three MCP resource templates using `@mcp.resource()`: `solune://projects/{project_id}/pipelines` (returns pipeline states JSON), `solune://projects/{project_id}/board` (returns board state JSON), `solune://projects/{project_id}/activity` (returns recent activity JSON). Each handler validates project access and delegates to existing services. (FR-031)
- [ ] T035 [US5] Add resource change notification hooks — integrate with the existing `ConnectionManager.broadcast_to_project()` in `solune/backend/src/services/websocket.py`: when a board update or pipeline state change is broadcast via WebSocket, also call `ctx.session.send_resource_updated(uri)` for MCP subscribers. Guard with feature flag check (`if settings.mcp_server_enabled`). (FR-032, FR-033)
- [ ] T036 [US5] Register resource templates in `solune/backend/src/services/mcp_server/server.py` — import `resources.py` and register all resource handlers on the FastMCP instance
- [ ] T037 [US5] Add dynamic pipeline template tool registration to `solune/backend/src/services/mcp_server/server.py` — during server creation, query pipeline configurations from DB (`DIFFICULTY_PRESET_MAP` pattern from `agent_tools.py`). For each preset, dynamically register a convenience tool (e.g., `launch_easy_pipeline(project_id, description)`) using closures and `mcp.tool()` API. Each delegates to `launch_pipeline` with the preset's pipeline ID. (FR-029, FR-030)

**Checkpoint**: User Story 5 complete — real-time subscriptions and pipeline template tools active

---

## Phase 8: User Story 6 — Self-Documentation and Guided Workflows (Priority: P3)

**Goal**: Provide rich server instructions, prompt templates for common workflows, and a configuration discovery endpoint.

**Independent Test**: Connect MCP client → browse server instructions and prompts → invoke `daily-standup` prompt → verify structured activity summary. Call `GET /api/v1/mcp/config` → verify connection configuration response.

### Implementation for User Story 6

- [ ] T038 [US6] Create `solune/backend/src/services/mcp_server/prompts.py` — register three MCP prompt templates using `@mcp.prompt()`: `create-project` (guided project creation flow with optional `project_name` arg), `pipeline-status` (check running pipelines with optional `project_id` arg), `daily-standup` (summarize recent activity with optional `days` arg). Each returns structured messages per the MCP prompt protocol. (FR-036)
- [ ] T039 [US6] Register prompt templates in `solune/backend/src/services/mcp_server/server.py` — import `prompts.py` and register all prompt handlers on the FastMCP instance. Verify `instructions` parameter is set on `FastMCP` with a rich description of Solune's capabilities. (FR-034, FR-035)
- [ ] T040 [US6] Add MCP configuration endpoint — create `GET /api/v1/mcp/config` route (in `solune/backend/src/main.py` or a new `solune/backend/src/api/mcp_config.py`). Returns JSON: `{server_name, url, transport: "streamable-http", auth: {type: "bearer", description: "..."}}`. No authentication required. (FR-037)
- [ ] T041 [P] [US6] Create or update `.vscode/mcp.json` in the repository root — add Solune MCP server entry: `{servers: {solune: {type: "http", url: "http://localhost:8000/api/v1/mcp", headers: {Authorization: "Bearer ${input:github_pat}"}}}}` for local development

**Checkpoint**: User Story 6 complete — full self-documentation, prompt workflows, and configuration discovery

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Integration testing, documentation, and validation across all stories

- [ ] T042 Create `solune/backend/tests/integration/test_mcp_e2e.py` — integration test: MCP client connects to the mounted server, authenticates with a GitHub PAT, lists tools (verify 22+ tools), calls `list_projects`, `get_board`, `launch_pipeline`. Test auth scoping (user without project access gets rejected). Mock GitHub API for token verification
- [ ] T043 [P] Update `solune/backend/src/services/mcp_server/__init__.py` — verify all public exports are correct: `create_mcp_server()`, `get_mcp_app()`. Add module-level docstring documenting the MCP server package purpose and architecture
- [ ] T044 [P] Document shared service layer architecture — add comments or docstring in `solune/backend/src/services/mcp_server/server.py` explicitly documenting that MCP tools, REST API endpoints, and internal `@tool` functions all delegate to the same `GitHubProjectsService`, `WorkflowOrchestrator`, `ChatAgentService`, etc. (FR-038, FR-039, per Phase 7 of plan)
- [ ] T045 Run quickstart.md validation — verify all steps in `specs/001-mcp-server/quickstart.md`: enable feature flag, install dependency, start server, connect MCP client, verify tool discovery and invocation. Fix any discrepancies
- [ ] T046 [P] Security review — verify token hashing uses SHA-256 (not plaintext), cache entries are properly evicted, rate limiting is enforced, no raw tokens are logged, project access is checked on every project-scoped tool
- [ ] T047 Code cleanup — ensure consistent error handling across all tools (descriptive errors for auth failure, access denied, project not found, tool execution failure), verify all tools have rich docstrings for auto-generated JSON Schema

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2)
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2), can run parallel with US1
- **User Story 3 (Phase 5)**: Depends on Foundational (Phase 2), enhances auth from Phase 2 — best done after US1/US2 tools exist
- **User Story 4 (Phase 6)**: Depends on Foundational (Phase 2), can run parallel with US1–US3
- **User Story 5 (Phase 7)**: Depends on User Story 2 (Phase 4) — needs pipeline tools for resource subscriptions
- **User Story 6 (Phase 8)**: Depends on Foundational (Phase 2), can run parallel with US1–US5
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational — **no dependencies on other stories**. Delivers read-only project access (MVP).
- **User Story 2 (P2)**: Can start after Foundational — **no dependencies on US1** (separate tool files). Delivers write operations.
- **User Story 3 (P2)**: Best done after US1 and US2 exist — enhances their auth validation. **Not blocked by them** (auth.py is independent) but testing is more meaningful with tools in place.
- **User Story 4 (P3)**: Can start after Foundational — **no dependencies on US1–US3** (separate tool files). Delivers management breadth.
- **User Story 5 (P3)**: Depends on US2 (pipeline tools) and Foundational — resource subscriptions need pipeline state data.
- **User Story 6 (P3)**: Can start after Foundational — **no dependencies on US1–US5** (prompts and config are independent).

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models/context before services
- Services before endpoints/tools
- Core tool implementation before integration/registration
- Story complete before moving to next priority

### Parallel Opportunities

- T002 and T003 can run in parallel (config.py and package init are independent files)
- T004 and T005 can run in parallel (context.py and auth.py are independent)
- T010 and T011 can run in parallel (different test files)
- T012, T018, T019, T023 can run in parallel (different tool module files)
- T029, T030, T031, T032 can run in parallel (all Tier 2 tool modules are independent files)
- US1, US2, and US4 can all run in parallel after Foundational phase (different tool files)
- US6 can run in parallel with all other user stories

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task T010: "Test auth in tests/unit/test_mcp_server/test_auth.py"
Task T011: "Test project tools in tests/unit/test_mcp_server/test_tools_projects.py"

# Launch all project tools in parallel (same file, but independent functions):
Task T012: "Implement list_projects in tools/projects.py"
Task T013: "Implement get_project in tools/projects.py" (after T012 creates the file)
Task T014: "Implement get_board in tools/projects.py"
Task T015: "Implement get_project_tasks in tools/projects.py"
```

## Parallel Example: User Story 4

```bash
# All Tier 2 tool modules are independent files — launch in parallel:
Task T029: "Create tools/agents.py"
Task T030: "Create tools/apps.py"
Task T031: "Create tools/chores.py"
Task T032: "Create tools/chat.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T009) — CRITICAL, blocks all stories
3. Complete Phase 3: User Story 1 (T010–T016)
4. **STOP and VALIDATE**: Connect MCP client → authenticate → list tools → call `list_projects` → verify response
5. Deploy/demo if ready — external agents can already query Solune project data

### Incremental Delivery

1. Setup + Foundational → MCP server mounts and authenticates (T001–T009)
2. Add User Story 1 → Read-only project access → **MVP!** (T010–T016)
3. Add User Story 2 → Task creation + pipeline launch (T017–T024)
4. Add User Story 3 → Hardened auth + access scoping (T025–T028)
5. Add User Story 4 → Full management tools (T029–T033)
6. Add User Story 5 → Real-time subscriptions (T034–T037)
7. Add User Story 6 → Self-documentation + prompts (T038–T041)
8. Polish → Integration tests + security review (T042–T047)
9. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (Phase 1–2)
2. Once Foundational is done:
   - Developer A: User Story 1 (read-only tools) — T010–T016
   - Developer B: User Story 2 (write tools) — T017–T024
   - Developer C: User Story 4 (management tools) — T029–T033
3. After US1+US2: Developer A takes User Story 3 (auth hardening) — T025–T028
4. After US2: Developer B takes User Story 5 (subscriptions) — T034–T037
5. Developer C takes User Story 6 (prompts/docs) — T038–T041
6. All converge for Polish — T042–T047

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- 22 tools total: 12 Tier 1 (US1 + US2) + 10 Tier 2 (US4), plus 3 resources (US5) + 3 prompts (US6)
- All MCP tools delegate to existing services — no business logic duplication (FR-038, FR-039)
- Token verification caches for 60s (FR-007), rate limits at 10/60s per token hash (FR-009)
