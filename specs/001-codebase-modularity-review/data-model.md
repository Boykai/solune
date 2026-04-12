# Data Model: Codebase Modularity Review

**Feature**: Codebase Modularity Review | **Date**: 2026-04-12 | **Status**: Complete

> This refactoring introduces no new persistent data or database schema changes. The data model below describes the **extracted classes and their relationships** — the internal architecture of the new modules.

## Entity: ChatStateManager

A consolidated state container for the chat subsystem's in-memory cache layer, replacing 4 module-level global dicts and their accessor functions.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `_messages` | `dict[str, list[ChatMessage]]` | Private, keyed by session_id | In-memory message cache (read-through from SQLite) |
| `_proposals` | `dict[str, AITaskProposal]` | Private, keyed by proposal_id | In-memory proposal cache |
| `_recommendations` | `dict[str, IssueRecommendation]` | Private, keyed by recommendation_id | In-memory recommendation cache |
| `_locks` | `dict[str, asyncio.Lock]` | Private, keyed by arbitrary key | Per-key async locks for concurrency control |
| `_db` | `aiosqlite.Connection` | Required, injected | Database connection for persistence |
| `_chat_store` | `ChatStore` | Required, injected | SQLite persistence layer for chat data |
| `_persist_max_retries` | `int` | Default: 3 | Max retry attempts for transient SQLite errors |
| `_persist_base_delay` | `float` | Default: 0.1 | Base delay (seconds) for exponential backoff |

### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_lock` | `(key: str) → asyncio.Lock` | Lazy-create and return per-key lock |
| `get_messages` | `async (session_id: str) → list[ChatMessage]` | Read-through: cache → SQLite fallback |
| `add_message` | `async (session_id: str, message: ChatMessage) → None` | Write-through: persist → cache |
| `clear_messages` | `async (session_id: str) → None` | Clear both cache and database |
| `get_proposal` | `async (proposal_id: str) → AITaskProposal | None` | Read-through: cache → SQLite fallback |
| `store_proposal` | `async (proposal_id: str, proposal: AITaskProposal) → None` | Write-through: persist → cache |
| `get_recommendation` | `async (rec_id: str) → IssueRecommendation | None` | Read-through: cache → SQLite fallback |
| `store_recommendation` | `async (rec_id: str, rec: IssueRecommendation) → None` | Write-through: persist → cache |

### State Transitions

```
Empty → Populated: First read triggers SQLite load into cache
Populated → Updated: Write-through on add/store operations
Populated → Cleared: Explicit clear removes both cache and DB entries
Any → Locked: get_lock() creates lock on first access per key
```

### Relationships

- **Used by**: `api/chat/messages.py`, `api/chat/proposals.py`, `api/chat/conversations.py`, `api/chat/streaming.py`
- **Depends on**: `ChatStore` (SQLite persistence), `aiosqlite.Connection`
- **Injected via**: `dependencies.get_chat_state_manager()` → reads from `request.app.state.chat_state_manager`

---

## Entity: ProposalOrchestrator

A service class encapsulating the 7-phase proposal confirmation workflow, extracted from the monolithic `confirm_proposal()` function.

### Dependencies (Constructor-Injected)

| Dependency | Type | Description |
|------------|------|-------------|
| `github_service` | `GitHubProjectsService` | GitHub API operations (issue creation, project management) |
| `connection_manager` | `ConnectionManager` | WebSocket broadcasting |
| `chat_state_manager` | `ChatStateManager` | Proposal/message state access |
| `chat_store` | `ChatStore` | Direct SQLite persistence for status updates |
| `workflow_orchestrator` | Module | Workflow configuration and agent assignment |
| `copilot_polling` | Module | Copilot polling lifecycle |
| `settings_store` | Module | User/project settings |

### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `confirm` | `async (proposal_id, request, session) → AITaskProposal` | Full 7-phase orchestration |
| `_validate_proposal` | `async (proposal_id, session) → AITaskProposal` | Phase 1: Verify ownership, expiry, status |
| `_apply_user_edits` | `(proposal, request) → AITaskProposal` | Phase 2: Apply edited title/description |
| `_resolve_repository` | `async (proposal, session) → tuple[str, str, str]` | Phase 3: Get owner, repo, project_id |
| `_create_github_issue` | `async (proposal, owner, repo, project_id) → IssueResult` | Phase 4: Create issue + add to project |
| `_broadcast_confirmation` | `async (proposal, session, issue_result) → None` | Phase 5: Status update + WebSocket + chat message |
| `_configure_workflow` | `async (proposal, session, issue_result) → WorkflowConfig` | Phase 6: Load/create workflow config + pipeline mapping |
| `_assign_agent_and_start` | `async (proposal, session, workflow_config) → None` | Phase 7: Agent assignment + pipeline init + polling |

### State Transitions (Proposal)

```
PENDING → EDITED: User edits applied (Phase 2)
EDITED → CONFIRMED: GitHub issue created successfully (Phase 5)
CONFIRMED → ASSIGNED: Agent assigned to workflow (Phase 7)
Any → ERROR: Validation failure or GitHub API error (returns HTTP error)
```

### Relationships

- **Used by**: `api/chat/proposals.py` (single call site)
- **Depends on**: `ChatStateManager`, `GitHubProjectsService`, `ConnectionManager`, `ChatStore`, workflow/polling modules
- **Injected via**: `dependencies.get_proposal_orchestrator()` using FastAPI `Depends()`

---

## Entity: Chat Package Module Map

Describes the decomposition of `api/chat.py` (2930 lines) into domain-scoped modules.

### Module: conversations.py

| Routes | Method | Path | Description |
|--------|--------|------|-------------|
| 4 | POST/GET/PATCH/DELETE | `/conversations/*` | Conversation CRUD |

**Depends on**: `ChatStateManager`, `ChatStore`, auth dependencies

### Module: messages.py

| Routes | Method | Path | Description |
|--------|--------|------|-------------|
| 3 | GET/DELETE/POST | `/messages/*` | Message listing, deletion, send |

**Depends on**: `ChatStateManager`, `ChatStore`, AI service, auth dependencies

### Module: proposals.py

| Routes | Method | Path | Description |
|--------|--------|------|-------------|
| 2 | POST/DELETE | `/proposals/*` | Confirm and cancel proposals |

**Depends on**: `ProposalOrchestrator`, `ChatStateManager`, auth dependencies

### Module: plans.py

| Routes | Method | Path | Description |
|--------|--------|------|-------------|
| 12 | CRUD | `/plans/*`, `/steps/*` | Plan management + step approval workflow |

**Depends on**: `ChatStore`, plan service, auth dependencies

### Module: streaming.py

| Routes | Method | Path | Description |
|--------|--------|------|-------------|
| 2 | POST | `/stream/*`, `/plan-stream/*` | SSE streaming for chat and plan generation |

**Depends on**: `ChatStateManager`, AI service, SSE helpers

---

## Entity: Webhooks Package Module Map

Describes the decomposition of `api/webhooks.py` (1033 lines) into domain-scoped modules.

### Module: handlers.py

| Functions | Description |
|-----------|-------------|
| `github_webhook()` | Main POST /github route — event dispatcher |
| `verify_webhook_signature()` | HMAC-SHA256 signature verification |
| `_processed_delivery_ids` | BoundedSet for deduplication (1000 entries) |
| `classify_pull_request_activity()` | PR event classification helper |
| `extract_issue_number_from_pr()` | Issue number extraction from PR body |

### Module: pull_requests.py

| Functions | Description |
|-----------|-------------|
| `handle_pull_request_event()` | PR opened/closed/ready_for_review handling |
| `handle_copilot_pr_ready()` | Copilot PR auto-review trigger |
| `update_issue_status_for_copilot_pr()` | Board status update for Copilot PRs |

### Module: ci.py

| Functions | Description |
|-----------|-------------|
| `handle_check_run_event()` | CI check run completed handler |
| `handle_check_suite_event()` | CI check suite pass/fail handler |
| `_get_auto_merge_pipeline()` | 3-tier cache lookup for auto-merge pipeline config |

---

## Entity: Frontend API Client Module Map

Describes the decomposition of `services/api.ts` (1876 lines) into domain-scoped modules.

### Module: client.ts (shared infrastructure)

| Export | Type | Description |
|--------|------|-------------|
| `request<T>()` | Function | Generic typed fetch wrapper with CSRF, auth, error handling |
| `ApiError` | Class | Custom error class for API failures |
| `onAuthExpired` | Function | Auth expiration listener pattern |
| `API_BASE_URL` | Constant | Base URL from env or `/api/v1` |
| `getCsrfToken()` | Function | CSRF token from document.cookie |
| `normalizeApiError()` | Function | Error response normalization |

### Domain Modules (16 files)

Each file imports `request` from `./client` and exports its namespace object(s):

| File | Exports | ~Lines |
|------|---------|--------|
| `auth.ts` | `authApi` | 30 |
| `projects.ts` | `projectsApi` | 40 |
| `tasks.ts` | `tasksApi` | 30 |
| `chat.ts` | `conversationApi`, `chatApi` | 450 |
| `board.ts` | `boardApi` | 55 |
| `settings.ts` | `settingsApi` | 70 |
| `workflow.ts` | `workflowApi`, `metadataApi` | 50 |
| `signal.ts` | `signalApi` | 70 |
| `mcp.ts` | `mcpApi` | 30 |
| `cleanup.ts` | `cleanupApi` | 35 |
| `chores.ts` | `choresApi` | 295 |
| `agents.ts` | `agentsApi` | 90 |
| `pipelines.ts` | `pipelinesApi`, `modelsApi` | 110 |
| `tools.ts` | `toolsApi`, `agentToolsApi` | 80 |
| `apps.ts` | `appsApi` | 75 |
| `activity.ts` | `activityApi` | 30 |

---

## Entity: Frontend Types Module Map

Describes the decomposition of `types/index.ts` (1525 lines) into domain-scoped modules.

### Module: common.ts (shared enums and primitives)

| Exports | Description |
|---------|-------------|
| `ProjectType`, `SenderType`, `ActionType`, `ProposalStatus`, `RecommendationStatus` | Enums used across multiple domains |
| `APIError` | Shared error interface |
| `FileAttachment`, `FileUploadResponse`, `FileUploadError` | File types used by chat + proposals |

### Domain Modules (17 files)

| File | ~Types | ~Lines | Key Exports |
|------|--------|--------|-------------|
| `auth.ts` | 2 | 15 | `User`, `AuthResponse` |
| `projects.ts` | 3 | 25 | `Project`, `StatusColumn`, `ProjectListResponse` |
| `tasks.ts` | 3 | 25 | `Task`, `TaskCreateRequest`, `TaskListResponse` |
| `chat.ts` | 12 | 100 | `ChatMessage`, `ActionData`, `Conversation`, `Mention*` |
| `proposals.ts` | 8 | 80 | `AITaskProposal`, `IssueRecommendation`, `IssuePriority` |
| `plans.ts` | 18 | 85 | `Plan`, `PlanStep`, `PlanStatus`, approval types |
| `board.ts` | 20+ | 340 | `BoardItem`, `BoardColumn`, `BoardProject`, `LinkedPR` |
| `settings.ts` | 17 | 130 | `EffectiveUserSettings`, `GlobalSettings`, update variants |
| `workflow.ts` | 5 | 55 | `WorkflowResult`, `WorkflowConfiguration`, `PipelineStateInfo` |
| `pipeline.ts` | 13 | 130 | `PipelineConfig`, `PipelineStage`, `PipelineAgentNode` |
| `agents.ts` | 4 | 30 | `AgentSource`, `AgentAssignment`, `AgentPreset` |
| `signal.ts` | 9 | 45 | `SignalConnection`, `SignalPreferences` |
| `mcp.ts` | 11 | 90 | `McpConfiguration`, `McpToolConfig` |
| `cleanup.ts` | 11 | 110 | `BranchInfo`, `CleanupPreflightResponse` |
| `chores.ts` | 17 | 145 | `Chore`, `ChoreTemplate`, `ChoreStatus` |
| `activity.ts` | 2 | 20 | `ActivityEvent`, `ActivityStats` |
| `ui.ts` | 8 | 60 | `NavRoute`, `SidebarState`, `Notification`, `TourStep` |

### Cross-Domain Import Graph

```
common.ts ← chat.ts, proposals.ts, plans.ts (enums: SenderType, ActionType, ProposalStatus)
common.ts ← workflow.ts (APIError)
chat.ts ← (standalone — ActionData union references other action types inline)
proposals.ts ← chat.ts (ActionData includes IssueCreateActionData)
plans.ts ← chat.ts (ActionData includes PlanCreateActionData)
pipeline.ts ← settings.ts (ProjectPipelineAssignment references pipeline types)
agents.ts ← workflow.ts (AgentAssignment used in WorkflowConfiguration)
```

**Resolution**: `common.ts` holds all shared enums. `chat.ts` imports action data types from `proposals.ts` and `plans.ts` to build the `ActionData` union. All other domain files are self-contained.
