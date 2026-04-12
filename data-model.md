# Data Model: Codebase Modularity Review

**Feature**: Codebase Modularity Review | **Date**: 2026-04-11 | **Status**: Complete

> This refactoring does not introduce new data entities. It restructures existing modules to improve maintainability. The "data model" describes the target module topology, interface contracts between newly-split modules, and the dependency graph after refactoring.

## Module: `api/chat/` Package (from `api/chat.py`)

The monolithic `api/chat.py` (2930 lines) is decomposed into focused sub-modules inside an `api/chat/` package.

### Target Module Structure

| Module | Responsibility | Approximate Lines | Key Exports |
|--------|---------------|-------------------|-------------|
| `__init__.py` | Package init, router aggregation | ~30 | `router` (combined APIRouter) |
| `messages.py` | Message CRUD, persistence helpers, session messages | ~350 | `get_messages`, `add_message`, `clear_messages`, `get_session_messages`, `_persist_message` |
| `proposals.py` | Proposal/recommendation storage, retrieval, confirmation, cancellation | ~400 | `store_proposal`, `get_proposal`, `confirm_proposal`, `cancel_proposal`, `store_recommendation`, `get_recommendation` |
| `plans.py` | Plan mode endpoints (14 functions) | ~650 | `send_plan_message`, `get_plan_endpoint`, `update_plan_endpoint`, `approve_plan_endpoint`, `exit_plan_mode_endpoint`, plan step CRUD |
| `conversations.py` | Conversation CRUD endpoints | ~100 | `create_conversation`, `list_conversations`, `update_conversation`, `delete_conversation` |
| `streaming.py` | SSE streaming variants, response formatting | ~300 | `send_message_stream`, `send_plan_message_stream` |
| `state.py` | `ChatStateManager` class wrapping `_messages`, `_proposals`, `_recommendations`, `_locks` | ~150 | `ChatStateManager` |
| `helpers.py` | Shared utilities: `_get_lock`, `_retry_persist`, `_default_expires_at`, `_resolve_repository`, `_safe_validation_detail`, `_trigger_signal_delivery` | ~200 | (internal helpers) |
| `dispatch.py` | Message processing: `_handle_agent_command`, `_handle_transcript_upload`, `_handle_feature_request`, `_handle_status_change`, `_handle_task_generation`, `_post_process_agent_response` | ~450 | (internal dispatch handlers) |
| `models.py` | Module-local models: `FileUploadResponse` | ~20 | `FileUploadResponse` |

### Dependencies Between Sub-Modules

```text
messages.py ──► helpers.py, state.py
proposals.py ──► helpers.py, state.py
plans.py ──► helpers.py, state.py, dispatch.py
conversations.py ──► (standalone, uses chat_store directly)
streaming.py ──► helpers.py, state.py, dispatch.py
dispatch.py ──► helpers.py, state.py
state.py ──► (standalone, no internal deps)
helpers.py ──► (standalone, no internal deps)
models.py ──► (standalone)
```

### Migration Path

1. Create `api/chat/` directory with `__init__.py`
2. Move `ChatStateManager` (new) into `state.py`
3. Move helper functions into `helpers.py`
4. Move dispatch handlers into `dispatch.py`
5. Move message endpoints into `messages.py`
6. Move proposal/recommendation functions into `proposals.py`
7. Move conversation endpoints into `conversations.py`
8. Move plan endpoints into `plans.py`
9. Move streaming endpoints into `streaming.py`
10. Move `FileUploadResponse` into `models.py`
11. Wire all sub-routers in `__init__.py`
12. Delete original `api/chat.py`
13. Update all imports across the codebase

---

## Module: `services/proposal_orchestrator.py` (from `confirm_proposal()`)

### Class: `ProposalOrchestrator`

```python
class ProposalOrchestrator:
    """Orchestrates proposal confirmation: validation → GitHub → persistence → broadcast."""

    def __init__(self, chat_state: ChatStateManager, chat_store: ChatStore):
        self._state = chat_state
        self._store = chat_store

    async def confirm(
        self,
        proposal_id: str,
        request: ProposalConfirmRequest | None,
        session: UserSession,
        github_service: GitHubProjectsService,
        connection_manager: ConnectionManager,
    ) -> AITaskProposal: ...

    # Private methods
    async def _validate_proposal(self, proposal_id: str, session: UserSession) -> AITaskProposal: ...
    def _apply_edits(self, proposal: AITaskProposal, request: ProposalConfirmRequest | None) -> AITaskProposal: ...
    async def _create_github_issue(self, proposal: AITaskProposal, session: UserSession, github_service: GitHubProjectsService) -> tuple[str, int]: ...
    async def _add_to_project(self, issue_number: int, session: UserSession, github_service: GitHubProjectsService) -> None: ...
    async def _persist_status(self, proposal: AITaskProposal) -> None: ...
    async def _broadcast_update(self, proposal: AITaskProposal, session: UserSession, connection_manager: ConnectionManager) -> None: ...
```

### State Transitions

```text
proposal.status: "pending" ──[validate]──► "pending" (no change)
                           ──[apply_edits]──► "pending" (title/desc updated)
                           ──[create_github_issue]──► "confirmed" (issue_url set)
                           ──[error at any step]──► "error" (error_message set)
```

---

## Module: `api/webhooks/` Package (from `api/webhooks.py`)

### Target Module Structure

| Module | Responsibility | Approximate Lines |
|--------|---------------|-------------------|
| `__init__.py` | Router aggregation, webhook entry point | ~40 |
| `common.py` | Signature verification, payload parsing, shared types | ~100 |
| `pull_requests.py` | PR opened/closed/synchronize handlers | ~300 |
| `check_runs.py` | CI check completed/created handlers | ~200 |
| `issues.py` | Issue opened/edited/labeled handlers | ~150 |
| `handlers.py` | Dispatch registry mapping event→handler | ~100 |

---

## Module: `services/bootstrap.py` (from `main.py`)

### Responsibilities Extracted

| Function | Purpose | Called From |
|----------|---------|-------------|
| `async def initialize_services(app: FastAPI)` | Create and attach services to `app.state` | Lifespan startup |
| `async def run_migrations(app: FastAPI)` | Execute pending database migrations | Lifespan startup |
| `async def start_background_tasks(app: FastAPI)` | Start polling loops, agent sync, cleanup | Lifespan startup |
| `async def shutdown_services(app: FastAPI)` | Gracefully stop background tasks, close connections | Lifespan shutdown |

### `main.py` After Extraction (~120 lines)

```python
app = FastAPI(lifespan=lifespan)

# Middleware
app.add_middleware(...)

# Routers
app.include_router(...)
```

**DOM nodes**: ~8–12 elements (content only, no decorative)

---

## Module: `services/api/` Package (from `services/api.ts`)

### Target Module Structure (Frontend)

| Module | Namespace Exports | Approximate Lines |
|--------|------------------|-------------------|
| `client.ts` | `apiClient`, `handleApiError`, request helpers | ~200 |
| `auth.ts` | `authApi` | ~40 |
| `chat.ts` | `chatApi`, `conversationApi` | ~250 |
| `board.ts` | `boardApi` | ~80 |
| `tasks.ts` | `tasksApi` | ~50 |
| `projects.ts` | `projectsApi` | ~50 |
| `settings.ts` | `settingsApi` | ~80 |
| `workflow.ts` | `workflowApi` | ~60 |
| `metadata.ts` | `metadataApi`, `signalApi` | ~80 |
| `agents.ts` | `agentsApi`, `agentToolsApi` | ~200 |
| `pipelines.ts` | `pipelinesApi` | ~120 |
| `chores.ts` | `choresApi` | ~100 |
| `tools.ts` | `toolsApi` | ~80 |
| `apps.ts` | `appsApi` | ~80 |
| `activity.ts` | `activityApi` | ~50 |
| `cleanup.ts` | `cleanupApi` | ~40 |
| `models.ts` | `modelsApi` | ~30 |
| `mcp.ts` | `mcpApi` | ~40 |
| `index.ts` | Barrel re-export of all namespaces | ~30 |

---

## Module: `types/` Domain-Scoped Files (from `types/index.ts`)

### Target Structure

| File | Domain | Key Types |
|------|--------|-----------|
| `common.ts` | Shared | `PaginatedResponse`, `ApiError`, `UUID`, `DateString`, `UserSession` |
| `chat.ts` | Chat | `ChatMessage`, `ChatMessageRequest`, `AITaskProposal`, `IssueRecommendation`, `Conversation` |
| `board.ts` | Board | `BoardItem`, `BoardColumn`, `BoardView`, `DragResult` |
| `pipeline.ts` | Pipeline | `Pipeline`, `PipelineStep`, `PipelineRun`, `StepStatus` |
| `agents.ts` | Agents | `Agent`, `AgentConfig`, `AgentPreview`, `LifecycleStatus` |
| `tasks.ts` | Tasks | `Task`, `TaskStatus`, `TaskPriority`, `TaskFilter` |
| `projects.ts` | Projects | `Project`, `ProjectSettings`, `Repository` |
| `settings.ts` | Settings | `UserSettings`, `NotificationPrefs`, `ThemeConfig` |
| `chores.ts` | Chores | `Chore`, `ChoreStatus`, `ChoreFrequency` |
| `workflow.ts` | Workflow | `Workflow`, `WorkflowRun`, `WorkflowStep` |
| `index.ts` | Barrel | Re-exports all domain types for backward compatibility |

---

## Module: `ChatStateManager` (new service class)

### Fields

| Field | Type | Purpose |
|-------|------|---------|
| `_messages` | `BoundedDict[str, list[ChatMessage]]` | Per-session message cache (LRU, capacity-limited) |
| `_proposals` | `BoundedDict[str, AITaskProposal]` | Proposal cache (LRU, capacity-limited) |
| `_recommendations` | `BoundedDict[str, IssueRecommendation]` | Recommendation cache (LRU, capacity-limited) |
| `_locks` | `BoundedDict[str, asyncio.Lock]` | Per-key async locks (LRU, capacity-limited) |
| `_global_lock` | `asyncio.Lock` | Protects `_locks` dict access |

### Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_messages_cache` | 1000 | Maximum cached sessions |
| `max_proposals_cache` | 5000 | Maximum cached proposals |
| `max_recommendations_cache` | 5000 | Maximum cached recommendations |
| `max_locks` | 10000 | Maximum concurrent locks |

### Lifecycle

```text
FastAPI startup ──► ChatStateManager() instantiated ──► attached to app.state
                                                      ──► injected via Depends()
FastAPI shutdown ──► ChatStateManager.cleanup() ──► caches cleared
```

---

## Dependency Graph After Refactoring

```text
api/chat/__init__.py
├── api/chat/messages.py ──► services/chat_store.py, api/chat/state.py
├── api/chat/proposals.py ──► services/proposal_orchestrator.py, api/chat/state.py
├── api/chat/plans.py ──► services/chat_store.py, api/chat/state.py
├── api/chat/conversations.py ──► services/chat_store.py
├── api/chat/streaming.py ──► services/chat_agent.py, api/chat/state.py
└── api/chat/dispatch.py ──► services/* (various)

api/webhooks/__init__.py
├── api/webhooks/pull_requests.py ──► services/github_projects/
├── api/webhooks/check_runs.py ──► services/copilot_polling/
├── api/webhooks/issues.py ──► services/github_projects/
└── api/webhooks/common.py ──► (standalone verification)

services/proposal_orchestrator.py ──► services/chat_store.py, services/github_projects/
services/bootstrap.py ──► services/* (initialization only)

main.py ──► services/bootstrap.py, middleware/*, api/*
```
