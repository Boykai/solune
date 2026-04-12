# Research: Codebase Modularity Review

**Feature**: Codebase Modularity Review | **Date**: 2026-04-11 | **Status**: Complete

## R1: Backend Monolith Split Strategy — `api/chat.py`

**Decision**: Split `api/chat.py` (2930 lines, 40 functions) into five domain-scoped modules under a new `api/chat/` package: `messages.py`, `proposals.py`, `plans.py`, `conversations.py`, and `streaming.py`. A top-level `api/chat/__init__.py` re-exports the FastAPI router to maintain backward compatibility with existing imports.

**Rationale**: `api/chat.py` is the largest backend file and contains five distinct responsibilities that rarely change together:

1. **Message CRUD** — `get_messages`, `add_message`, `clear_messages`, `get_session_messages`, persistence helpers
2. **Proposal/recommendation handling** — `store_proposal`, `get_proposal`, `confirm_proposal`, `cancel_proposal`
3. **Plan mode endpoints** — 14 functions for plan CRUD, approval, step management, export
4. **Conversation CRUD** — `create_conversation`, `list_conversations`, `update_conversation`, `delete_conversation`
5. **Streaming** — `send_message_stream`, `send_plan_message_stream`, SSE response handling

Splitting by responsibility reduces the cognitive load for reviewers (a plan-mode change no longer requires reviewing 2930 lines), enables independent testing per module, and makes `git blame` more useful. The `__init__.py` re-export pattern ensures that existing `from src.api.chat import router` statements continue to work.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Split by HTTP method (GET/POST/PATCH) | Mixes unrelated domains in each file; doesn't align with how developers think about changes |
| Keep as one file, add region comments | Doesn't help IDE navigation, test isolation, or review scope |
| Split into only 2 files (sync + stream) | Still leaves large monoliths; doesn't address the plan-mode bloat |
| Use APIRouter sub-routers without splitting the file | Organizes routes but doesn't reduce file size or improve testability |

---

## R2: God Function Extraction — `confirm_proposal()`

**Decision**: Extract `confirm_proposal()` (348 lines) into a `ProposalOrchestrator` service class in `services/proposal_orchestrator.py`. The class exposes a single `async def confirm(proposal_id, request, session, github_service, connection_manager)` method that internally delegates to focused private methods: `_validate_proposal()`, `_apply_edits()`, `_create_github_issue()`, `_add_to_project()`, `_persist_status()`, `_broadcast_update()`.

**Rationale**: A 348-line function that touches GitHub API, SQLite persistence, WebSocket broadcasting, and validation is untestable in isolation — every test must mock all four concerns. Extracting to a service class with focused methods enables:

- **Unit testing** each step independently (e.g., test `_validate_proposal()` without mocking GitHub)
- **Mocking** the orchestrator as a single dependency in the API layer
- **Reuse** if proposal confirmation is needed from other entry points (e.g., webhooks, CLI)
- **Error isolation** — a broadcast failure doesn't need to be handled in the same scope as GitHub API errors

The API endpoint becomes a thin wrapper: resolve dependencies, call `orchestrator.confirm()`, return result.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Split into standalone functions (not a class) | Loses shared state (proposal cache, connection references); functions need the same parameters passed repeatedly |
| Keep in `chat.py` but refactor into smaller private functions | Improves readability but doesn't improve testability — private functions share the module's global state |
| Event-driven architecture (publish confirmation event) | Over-engineered for synchronous confirmation flow; adds eventual consistency concerns |

---

## R3: Frontend API Client Split Strategy — `services/api.ts`

**Decision**: Split `services/api.ts` (1876 lines, 20 namespace objects) into domain-scoped files under `services/api/`: `auth.ts`, `chat.ts`, `board.ts`, `tasks.ts`, `projects.ts`, `settings.ts`, `workflow.ts`, `metadata.ts`, `agents.ts`, `pipelines.ts`, `chores.ts`, `tools.ts`, `apps.ts`, `activity.ts`. A barrel `services/api/index.ts` re-exports all namespaces. Shared utilities (`apiClient`, `handleApiError`, type helpers) go in `services/api/client.ts`.

**Rationale**: The monolithic `api.ts` makes every change require reviewing 1876 lines. Splitting by domain:

- Enables **tree-shaking** — unused API domains are excluded from bundles for code-split routes
- Matches the **backend API module structure** (`api/chat.py`, `api/board.py`, etc.)
- Makes **code review** focused — a chat API change only touches `api/chat.ts`
- Keeps **imports stable** via barrel re-exports: `import { chatApi } from '@/services/api'` still works

The shared `client.ts` contains the axios/fetch instance, error handling, and request interceptors — these are genuine cross-cutting concerns that every domain needs.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Keep as one file with better comments/regions | Doesn't help tree-shaking or review scope |
| Split by HTTP method | Mixes unrelated domains; not how developers conceptualize API calls |
| Auto-generate from OpenAPI spec | No OpenAPI spec exists; creating one is a separate initiative |
| Use a code-gen tool (e.g., orval) | Requires backend schema first; too large a scope change for this refactoring |

---

## R4: Domain-Scoped Types Strategy — `types/index.ts`

**Decision**: Split `types/index.ts` (1525 lines) into domain-scoped files: `types/chat.ts`, `types/board.ts`, `types/pipeline.ts`, `types/agents.ts`, `types/tasks.ts`, `types/projects.ts`, `types/settings.ts`, `types/common.ts`. A barrel `types/index.ts` re-exports everything for backward compatibility.

**Rationale**: A single 1525-line type file creates unnecessary merge conflicts when multiple features modify types in different domains. Domain-scoped files:

- Reduce **merge conflicts** — changes to board types don't conflict with chat type changes
- Improve **IDE navigation** — jump-to-definition lands in the relevant domain file, not line 847 of a mega-file
- Enable **co-location** — domain types live next to their API client and hooks
- Maintain **backward compatibility** — the barrel re-export means all existing `import { X } from '@/types'` statements continue working

Shared types (e.g., `PaginatedResponse<T>`, `ApiError`, `UUID`) go in `types/common.ts`.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Co-locate types in each component folder | Scatters types too widely; types are shared across hooks, services, and components |
| Keep one file with region markers | Doesn't reduce merge conflicts or improve navigation |
| Generate types from backend Pydantic models | Requires a type generation pipeline; separate initiative |
| Use TypeScript namespaces for grouping | Namespaces are discouraged in modern TS; don't improve file-level organization |

---

## R5: Backend Global State Consolidation

**Decision**: Wrap the four module-level dicts (`_messages`, `_proposals`, `_recommendations`, `_locks`) in a `ChatStateManager` class instantiated during the FastAPI lifespan. Inject via `Depends()` in the same way as `get_github_service`. The manager exposes typed methods: `get_messages(session_id)`, `store_proposal(proposal)`, `get_lock(key)`, etc.

**Rationale**: Module-level mutable dicts create three problems:

1. **Race conditions** — `_locks` dict is itself unprotected; concurrent requests can create duplicate locks
2. **No lifecycle management** — dicts grow without bound (the `_locks` dict was already identified as a memory leak target in Harden Phase 1)
3. **Testing difficulty** — tests must monkey-patch module globals or import-order-dependent state

A `ChatStateManager` class:

- Can be **instantiated with configuration** (max capacity, TTL) from `app.state`
- Can be **injected and mocked** cleanly in tests
- Can use **BoundedDict** internally for capacity-limited caches
- Has a clear **lifecycle** tied to the FastAPI lifespan (create on startup, cleanup on shutdown)

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Move dicts to `app.state` directly | Same issues (no encapsulation, no capacity limits); just moves the globals |
| Use Redis/external cache | Over-engineered for in-process caching; adds infrastructure dependency |
| Keep globals, add explicit locking | Addresses race conditions but not lifecycle or testing concerns |
| Singleton pattern via module `__init__` | Still module-level global state; just adds indirection |

---

## R6: Backend Webhooks Split Strategy — `api/webhooks.py`

**Decision**: Split `api/webhooks.py` (1033 lines) into an `api/webhooks/` package: `pull_requests.py` (PR event handlers), `check_runs.py` (CI check handlers), `issues.py` (issue event handlers), `common.py` (signature verification, payload parsing), and `__init__.py` (router re-export).

**Rationale**: Webhook handlers are inherently event-type-scoped — a pull request handler never interacts with a check run handler. The current monolithic file forces developers to read past unrelated handlers to find the one they need. Splitting by GitHub event type:

- Mirrors **GitHub's own event taxonomy** (pull_request, check_run, issues, etc.)
- Makes **adding new event handlers** straightforward — create a new file, register the route
- Enables **focused testing** — test PR handlers without loading check run dependencies
- Keeps **shared utilities** (HMAC verification, payload extraction) in a common module

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Split by webhook source (GitHub, Slack, etc.) | Only GitHub webhooks exist today; premature generalization |
| Keep as one file with handler registration pattern | Doesn't reduce file size or improve testability |
| Move to event-driven architecture with pub/sub | Over-engineered for the current webhook volume; adds infrastructure complexity |

---

## R7: Backend `main.py` Bootstrap Extraction

**Decision**: Extract bootstrap logic from `main.py` (859 lines) into `services/bootstrap.py`. The bootstrap module handles: service initialization, migration running, polling loop setup, agent sync scheduling, and cleanup task registration. `main.py` retains only the FastAPI app creation, middleware registration, and router inclusion.

**Rationale**: `main.py` currently mixes two concerns:

1. **App definition** — creating the FastAPI instance, adding middleware, including routers
2. **Lifecycle management** — initializing services, running migrations, starting background tasks

These change for different reasons and at different frequencies. A developer adding a new middleware shouldn't need to navigate past 400 lines of initialization code. The extraction:

- Makes `main.py` a **declarative app definition** (~100-150 lines)
- Makes **startup/shutdown testable** independently
- Follows the **FastAPI lifespan pattern** — bootstrap functions are called from the lifespan context manager

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Move everything to a `create_app()` factory | Still mixes concerns in one function; just moves the code |
| Use FastAPI event handlers (@app.on_event) | Deprecated in favor of lifespan context manager |
| Keep as-is with better comments | Doesn't improve testability or review scope |

---

## R8: Frontend Test Layout Consolidation

**Decision**: Standardize on the `__tests__/` subdirectory pattern for all component domains. Co-located `.test.tsx` files in `layout/` should be moved to `layout/__tests__/`. Utility and constant tests remain co-located (they're single files, not test suites).

**Rationale**: The hybrid pattern (some domains use `__tests__/`, layout uses co-located files) reduces discoverability. When a developer looks for tests, they need to check both patterns. The `__tests__/` subdirectory pattern is already dominant (used by 7 component domains) and has advantages:

- **Clean directory listings** — component files aren't interleaved with test files
- **Glob-friendly** — `**/__tests__/**` reliably finds all tests
- **Consistent expectations** — new contributors always know where to look

Exception: single-file test modules (e.g., `chat-placeholders.test.ts` in `constants/`) can remain co-located since there's no subdirectory to justify a `__tests__/` folder for one file.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Standardize on co-located `.test.tsx` everywhere | Would require moving 100+ test files from `__tests__/` directories; larger disruption |
| Keep hybrid | Continues to cause confusion; inconsistent developer experience |
| Top-level `tests/` mirror of `src/` | Disconnects tests from components; harder to maintain |

---

## R9: Circular Dependency Resolution in `dependencies.py`

**Decision**: Resolve the `auth.py` ↔ `dependencies.py` circular import by moving the session dependency into `dependencies.py` directly (consolidating the lazy import workaround). The `_get_session_dep()` wrapper and lazy `from src.api.auth import get_session_dep` should be replaced with a direct implementation in `dependencies.py` that uses the session store.

**Rationale**: The current lazy import in `_get_session_dep()` is a symptom of the circular dependency between `dependencies.py` (which provides DI functions) and `auth.py` (which provides session validation). This fragile pattern:

- Hides **runtime import failures** (caught only when the dependency is first resolved)
- Makes **import order** matter (tests that import auth before dependencies may see different behavior)
- Adds **indirection** without clear benefit

Consolidating session dependency resolution into `dependencies.py` breaks the cycle cleanly since `auth.py` can then import from `dependencies.py` without dependencies.py needing to import from `auth.py`.

**Alternatives considered**:

| Alternative | Why Rejected |
|-------------|-------------|
| Keep the lazy import | Fragile; hides errors; already identified as a problem |
| Move all DI to `auth.py` | Wrong responsibility — auth should not own non-auth dependencies |
| Create a third module `di.py` | Just moves the problem; adds another file to maintain |
