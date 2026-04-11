# Research: Codebase Modularity Review

**Feature**: Codebase Modularity Review | **Date**: 2026-04-11 | **Status**: Complete

## R1: Chat Module Split Strategy — Package vs. Flat Files

**Decision**: Convert `api/chat.py` into a Python package (`api/chat/` directory with `__init__.py`) rather than splitting into sibling files at the `api/` level.

**Rationale**: A package approach provides several advantages over flat sibling files:

1. **Encapsulation**: Internal helpers (e.g., `_persist_message()`, `_retry_persist()`) stay private to the package — they aren't visible at the `api/` level alongside `board.py`, `tasks.py`, etc.
2. **Import compatibility**: `from src.api.chat import router` resolves to `api/chat/__init__.py`, which re-exports `router`. No external import paths change.
3. **Namespace isolation**: Each sub-module defines its own `router = APIRouter()` with a clear scope. The package `router.py` combines them via `include_router()`.
4. **State sharing**: The `ChatStateManager` lives in `api/chat/state.py` and is imported by sibling modules within the package. This is cleaner than a separate top-level `api/chat_state.py`.

The current codebase already uses package-style organization for services (`services/copilot_polling/`, `services/github_projects/`, `services/workflow_orchestrator/`, `services/mcp_server/`) — each with `__init__.py` and multiple internal modules. Following the same pattern for API routes is consistent.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Flat sibling files (`api/chat_messages.py`, `api/chat_proposals.py`) | Pollutes the `api/` namespace with 5+ chat-prefixed files; no encapsulation of internal helpers; inconsistent with existing `services/` package pattern |
| Single file with better organization (regions/comments) | Doesn't solve the core problem — 2,930 lines is too large for effective code review, test isolation, and merge conflict avoidance |
| Move all logic to services, keep `api/chat.py` thin | Over-extraction — the endpoint functions contain routing logic (request parsing, response formatting, SSE setup) that belongs in the API layer, not services |

---

## R2: ProposalOrchestrator Extraction — Service Class vs. Module Functions

**Decision**: Extract `confirm_proposal()` body into a `ProposalOrchestrator` class (in `services/proposal_orchestrator.py`) rather than a set of standalone module-level functions.

**Rationale**: The current `confirm_proposal()` function (345 lines, starting at line 1607 of `api/chat.py`) performs five distinct sequential steps:

1. **Validate** — Check proposal status, expiration, permissions
2. **GitHub workflow** — Create branch, commit files, open PR via GitHub API
3. **Agent assignment** — Assign a Copilot agent to the PR
4. **Polling** — Start copilot polling for the new workflow
5. **Broadcast** — WebSocket notification to connected clients

A class provides:
- **Dependency injection**: Constructor accepts `GitHubProjectsService`, `ConnectionManager`, `CopilotPollingService` — all testable via mocks
- **Step isolation**: Each method can be unit-tested independently
- **Error recovery**: Class can maintain transient state for rollback (e.g., if step 4 fails, step 2's PR still exists but polling isn't started)
- **Consistency**: Follows the existing `services/` pattern where complex workflows are encapsulated in service classes (e.g., `AgentCreatorService`, `MetadataService`)

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Module-level functions in `services/proposal_orchestrator.py` | Loses the ability to inject dependencies via constructor; each function would need all dependencies as parameters, creating long parameter lists |
| Keep in `api/chat/proposals.py` but refactor into smaller nested functions | Still a single endpoint function; doesn't improve testability; nested functions can't be imported or tested individually |
| Extract to `services/github_projects/` (extend existing service) | `confirm_proposal` spans multiple services (GitHub, WebSocket, polling); adding it to `github_projects` would increase that service's coupling |

---

## R3: Webhooks Split — Event-Type Grouping

**Decision**: Split `api/webhooks.py` by GitHub event type: `pull_requests.py` for PR events, `check_runs.py` for check run/suite events, and `helpers.py` for shared utilities.

**Rationale**: The webhook dispatcher (`github_webhook()` at line 348) already routes by event type header:

```python
event_type = request.headers.get("X-GitHub-Event")
if event_type == "pull_request":
    return await handle_pull_request_event(payload)
elif event_type == "check_run":
    return await handle_check_run_event(payload)
elif event_type == "check_suite":
    return await handle_check_suite_event(payload)
```

This natural routing boundary maps directly to file boundaries. Each handler file contains the event-specific logic plus any sub-handlers (e.g., `handle_pull_request_event()` calls `update_issue_status_for_copilot_pr()` and `handle_copilot_pr_ready()` — all PR-related).

Helper functions (`verify_webhook_signature()`, `extract_issue_number_from_pr()`, `classify_pull_request_activity()`, `_resolve_issue_for_pr()`) are used across event types and belong in a shared `helpers.py`.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Split by action (opened, closed, completed) | Too granular; many actions share context and would require excessive cross-file imports |
| Keep as single file with better organization | 1,033 lines is manageable but still large for focused reviews; event-type split is a natural boundary |
| Move all logic to a `WebhookService` class | Over-abstraction — webhook handlers are inherently procedural (receive event, process, respond); a class adds ceremony without benefit |

---

## R4: Frontend API Client Split — Per-Domain Files

**Decision**: Replace the monolithic `services/api.ts` (1,876 lines) with a `services/api/` directory containing one TypeScript file per API domain, plus a shared `client.ts` and a barrel `index.ts`.

**Rationale**: The current file contains 13 namespace objects (`authApi`, `projectsApi`, `tasksApi`, `conversationApi`, `chatApi`, `boardApi`, `settingsApi`, `workflowApi`, `metadataApi`, `signalApi`, `mcpApi`, `cleanupApi`, `choresApi`) plus 15+ agent/MCP type definitions and utility functions. This creates several problems:

1. **Code review scope**: Any API change requires reviewing 1,876 lines of context
2. **Merge conflicts**: Multiple developers adding endpoints to different domains conflict on the same file
3. **Code splitting**: Vite cannot tree-shake unused API namespaces because they're all in one module
4. **Test isolation**: Mocking a single API namespace requires importing the entire file

Per-domain files solve all four issues while maintaining backward compatibility via barrel re-exports.

**Import compatibility**: The barrel `services/api/index.ts` re-exports all namespaces:
```typescript
export { ApiError, onAuthExpired } from './client';
export { authApi } from './auth';
export { chatApi, conversationApi } from './chat';
// ... etc
```

Existing imports like `import { chatApi } from '../services/api'` resolve to the barrel and continue to work. TypeScript path resolution treats a directory with `index.ts` the same as a file.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Keep as single file, use `// #region` comments | Doesn't solve code-splitting, merge conflicts, or test isolation |
| One file per endpoint (e.g., `api/createTask.ts`) | Too granular; 50+ files for individual endpoints reduces discoverability |
| Use a code-generated API client (OpenAPI → TypeScript) | Architectural change; out of scope for a modularity refactor; would require backend OpenAPI spec generation |

---

## R5: Frontend Types Split — Domain Scoping

**Decision**: Split `types/index.ts` (1,525 lines) into domain-scoped files with a barrel re-export.

**Rationale**: The current file defines 40+ types, interfaces, and enums for all domains (chat, board, pipeline, tasks, agents, plans, settings, common). Analysis of the type dependency graph shows:

- **Common types** (`SenderType`, `ActionType`, `User`, `Project`): Referenced by 3+ other domains → extract to `common.ts`
- **Chat types** (`ChatMessage`, `AITaskProposal`, etc.): Self-contained with imports from `common.ts` → extract to `chat.ts`
- **Plan types** (`Plan`, `PlanStep`, `ThinkingEvent`, etc.): Self-contained → extract to `plans.ts`
- **Board types**: Import `Task` from tasks → extract to `board.ts`
- **No circular dependencies**: The type graph is acyclic when `common.ts` holds shared base types

The barrel `index.ts` re-exports everything, preserving `import type { ChatMessage } from '@/types'` and `import type { ChatMessage } from '../types'` paths.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Keep monolithic with better comments/sections | Doesn't solve IDE navigation issues or cognitive load |
| Type-per-file (one file per interface) | Too granular for 40+ types; 40 files in `types/` reduces discoverability |
| Co-locate types with components (e.g., `components/chat/types.ts`) | Breaks the existing convention of centralized types; makes cross-domain type sharing harder |

---

## R6: Global State Consolidation — ChatStateManager

**Decision**: Replace the three module-level dicts in `api/chat.py` with a `ChatStateManager` class, instantiated during app lifespan and registered on `app.state`.

**Rationale**: The current global state pattern has three issues:

1. **No lifecycle management**: Dicts are never cleared. The `_locks` dict accumulates one `asyncio.Lock` per unique project ID indefinitely — a memory leak identified in issue #1355's parent.
2. **Race conditions**: Module-level dicts are accessible from any coroutine without synchronization. While Python's GIL prevents data corruption, logical races (read-modify-write on `_messages`) are possible.
3. **Test isolation**: Tests that modify global state must manually reset it in teardown fixtures. A class-based approach allows creating fresh instances per test.

The `ChatStateManager` class:
- Uses `BoundedDict` (already in codebase) for `_locks` with a configurable capacity (default 10,000)
- Provides explicit `clear()` for shutdown cleanup
- Is injected via `Depends()` from `app.state.chat_state`, consistent with other singletons (`github_projects_service`, `connection_manager`, etc.)

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Keep dicts but add `WeakValueDictionary` for locks | `asyncio.Lock` instances are referenced by in-progress operations; weak refs would GC active locks |
| Move state to Redis/external store | Over-engineered for in-memory cache; adds infrastructure dependency for a modularity refactor |
| Use FastAPI `app.state` directly without wrapper class | Loses encapsulation; state access scattered across codebase without validation |

---

## R7: Import Path Migration — Test Patch Targets

**Decision**: After splitting modules, systematically update all test `patch()` targets that reference the old monolithic file paths.

**Rationale**: The backend test suite contains 5,200+ tests. Many use `unittest.mock.patch()` or `pytest.monkeypatch` with string targets like:
- `src.api.chat._messages`
- `src.api.chat._proposals`
- `src.api.chat._get_lock`
- `src.api.webhooks.handle_pull_request_event`

After the split, these targets change to:
- `src.api.chat.state.ChatStateManager` (or the injected instance)
- `src.api.chat.messages._persist_message`
- `src.api.webhooks.pull_requests.handle_pull_request_event`

A systematic `grep -r "patch.*src.api.chat" tests/` followed by targeted updates ensures no test breaks from import path changes.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Keep old import paths via re-exports in `__init__.py` | Leaking internal implementation through `__init__.py` defeats the purpose of the split; creates a maintenance burden |
| Use `importlib` indirection in tests | Overly clever; harder to read than direct import paths |
