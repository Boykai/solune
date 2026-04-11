# Data Model: Codebase Modularity Review

**Feature**: Codebase Modularity Review | **Date**: 2026-04-11 | **Status**: Complete

> **Note**: This refactor introduces no new database entities or schema changes. The data model below describes the **module dependency structure** — the relationships between the new and existing modules after the refactoring is complete.

## Module: `api/chat/` Package

The monolithic `api/chat.py` (2,930 lines) is decomposed into a Python package with the following module dependency graph:

### Internal Module Dependencies

```text
api/chat/__init__.py
    └── imports router from → api/chat/router.py

api/chat/router.py
    ├── imports router from → api/chat/conversations.py
    ├── imports router from → api/chat/messages.py
    ├── imports router from → api/chat/proposals.py
    ├── imports router from → api/chat/plans.py
    └── imports router from → api/chat/streaming.py

api/chat/state.py                         (NO internal dependencies)
    └── uses: BoundedDict, ChatMessage, AITaskProposal

api/chat/conversations.py
    └── imports from → api/chat/state.py  (ChatStateManager via Depends)

api/chat/messages.py
    ├── imports from → api/chat/state.py  (ChatStateManager via Depends)
    └── defines: _persist_message(), _retry_persist(), _resolve_repository()

api/chat/proposals.py
    ├── imports from → api/chat/state.py  (ChatStateManager via Depends)
    └── imports from → services/proposal_orchestrator.py

api/chat/plans.py
    └── imports from → api/chat/state.py  (ChatStateManager via Depends)

api/chat/streaming.py
    ├── imports from → api/chat/state.py  (ChatStateManager via Depends)
    └── imports from → api/chat/messages.py (_persist_message, _post_process_agent_response)
```

### External Dependencies (unchanged)

Each endpoint module depends on the same external services they currently use:

| Module | External Dependencies |
|--------|----------------------|
| `conversations.py` | `chat_store`, `auth` (session dependency) |
| `messages.py` | `chat_store`, `chat_agent`, `auth`, `github_projects_service`, `connection_manager` |
| `proposals.py` | `ProposalOrchestrator`, `auth` |
| `plans.py` | `chat_store`, `plan_agent_provider`, `auth` |
| `streaming.py` | `chat_agent`, `plan_agent_provider`, `auth`, `connection_manager` |

---

## Module: `services/proposal_orchestrator.py`

### Class: ProposalOrchestrator

| Attribute | Type | Source |
|-----------|------|--------|
| `_github` | `GitHubProjectsService` | Injected via constructor |
| `_ws` | `ConnectionManager` | Injected via constructor |
| `_poller` | `CopilotPollingService` | Injected via constructor |

### Method Dependencies

```text
confirm()
    ├── validate_proposal()      → reads proposal status, expiration
    ├── setup_github_workflow()   → calls _github.create_branch(), .commit_files(), .create_pr()
    ├── assign_agent()            → calls _github.assign_copilot_to_pr()
    ├── start_polling()           → calls _poller.start_polling()
    └── broadcast_result()        → calls _ws.broadcast()
```

### Dependency Injection

```text
get_proposal_orchestrator(request: Request) → ProposalOrchestrator
    ├── get_github_service(request)        → GitHubProjectsService
    ├── get_connection_manager(request)    → ConnectionManager
    └── request.app.state.copilot_poller   → CopilotPollingService
```

---

## Module: `api/webhooks/` Package

### Internal Module Dependencies

```text
api/webhooks/__init__.py
    └── imports router from → api/webhooks/router.py

api/webhooks/router.py
    ├── imports from → api/webhooks/helpers.py     (verify_webhook_signature)
    ├── imports from → api/webhooks/pull_requests.py
    └── imports from → api/webhooks/check_runs.py

api/webhooks/helpers.py                            (NO internal dependencies)
    └── defines: verify_webhook_signature(), extract_issue_number_from_pr(),
                 classify_pull_request_activity(), _resolve_issue_for_pr()

api/webhooks/pull_requests.py
    └── imports from → api/webhooks/helpers.py     (extract_issue_number_from_pr, classify)

api/webhooks/check_runs.py
    └── imports from → api/webhooks/helpers.py     (extract_issue_number_from_pr)
```

---

## Module: `ChatStateManager` (api/chat/state.py)

### State Structure

| Field | Type | Description |
|-------|------|-------------|
| `_messages` | `dict[str, list[ChatMessage]]` | In-memory message cache keyed by session ID |
| `_proposals` | `dict[str, AITaskProposal]` | In-memory proposal cache keyed by proposal ID |
| `_locks` | `BoundedDict[str, asyncio.Lock]` | Per-project concurrency locks with LRU eviction |

### Lifecycle

```text
App Startup (lifespan):
    ChatStateManager(lock_capacity=10_000) → app.state.chat_state

Request Handling (Depends):
    get_chat_state(request) → request.app.state.chat_state

App Shutdown (lifespan):
    app.state.chat_state.clear() → empties all dicts
```

### Access Patterns

| Operation | Method | Thread Safety |
|-----------|--------|---------------|
| Get/create lock | `get_lock(key)` | GIL-safe dict access; lock itself is async |
| Read messages | `get_messages(session_id)` | Returns list reference (caller must not mutate) |
| Write messages | `set_messages(session_id, msgs)` | Replaces list reference atomically |
| Append message | `append_message(session_id, msg)` | Appends to existing list |
| Get proposal | `get_proposal(proposal_id)` | Returns `None` if not found |
| Set proposal | `set_proposal(proposal_id, p)` | Overwrites existing |
| Remove proposal | `remove_proposal(proposal_id)` | No-op if not found |
| Cleanup | `clear()` | Clears all three dicts |

---

## Module: `services/api/` Directory (Frontend)

### Module Dependency Graph

```text
services/api/index.ts                      (barrel re-export only)

services/api/client.ts                     (NO internal dependencies)
    └── defines: ApiError, onAuthExpired(), fetchApi(), handleResponse()

services/api/auth.ts
    └── imports from → client.ts           (fetchApi, handleResponse)

services/api/chat.ts
    └── imports from → client.ts

services/api/board.ts
    └── imports from → client.ts

services/api/projects.ts
    └── imports from → client.ts

services/api/tasks.ts
    └── imports from → client.ts

services/api/settings.ts
    └── imports from → client.ts

services/api/workflow.ts
    └── imports from → client.ts

services/api/agents.ts
    └── imports from → client.ts

services/api/signal.ts
    └── imports from → client.ts

services/api/metadata.ts
    └── imports from → client.ts
```

**Key property**: All domain API modules depend only on `client.ts` — no cross-domain API dependencies. This ensures clean code-splitting boundaries.

---

## Module: `types/` Directory (Frontend)

### Type Dependency Graph

```text
types/index.ts                              (barrel re-export only)

types/common.ts                             (NO dependencies)
    └── defines: SenderType, ActionType, User, AuthResponse, Project, ProjectListResponse,
                 ProposalStatus, RecommendationStatus

types/tasks.ts
    └── imports from → common.ts            (Project)

types/chat.ts
    ├── imports from → common.ts            (SenderType, ActionType, ProposalStatus)
    └── imports from → tasks.ts             (Task — for action data)

types/board.ts
    └── imports from → common.ts            (Project)

types/pipeline.ts
    └── imports from → common.ts            (Project)

types/plans.ts
    └── imports from → common.ts            (ActionType)

types/agents.ts
    └── imports from → common.ts            (Project)

types/settings.ts                           (NO dependencies)
```

**Key property**: The dependency graph is a DAG (directed acyclic graph) rooted at `common.ts`. No circular dependencies exist.

---

## Impact Summary

| Category | Before | After |
|----------|--------|-------|
| Largest backend API file | 2,930 lines (`chat.py`) | ~500 lines (`streaming.py`) |
| Largest frontend service file | 1,876 lines (`api.ts`) | ~450 lines (`chat.ts`) |
| Largest frontend types file | 1,525 lines (`index.ts`) | ~300 lines (`plans.ts`) |
| Module-level global state | 3 unmanaged dicts | 1 `ChatStateManager` class |
| God function | `confirm_proposal()` 345 lines | 5 methods, ~70 lines each |
| Backend files in `api/` | 2 monolithic (chat + webhooks) | 2 packages (13 focused modules) |
| Database schema changes | — | None |
| API contract changes | — | None |
