# Research: Codebase Modularity Review

**Feature**: Codebase Modularity Review | **Date**: 2026-04-12 | **Status**: Complete

## R1: Python Module-to-Package Conversion Best Practices

**Decision**: Convert monolithic `.py` files to packages (directories with `__init__.py`) using router aggregation in `__init__.py` for FastAPI endpoints.

**Rationale**: FastAPI's `APIRouter` natively supports `include_router()` for composing sub-routers. Converting `api/chat.py` to `api/chat/__init__.py` that imports and includes sub-routers from domain-specific modules (conversations.py, messages.py, etc.) preserves the same URL prefix and all middleware/dependency behavior. The `__init__.py` re-exports public symbols so that existing `from src.api.chat import ...` statements continue to work.

**Alternatives considered**:
- **Blueprint/namespace pattern** — FastAPI doesn't have Django-style blueprints; `include_router()` is the idiomatic equivalent. Rejected: no additional benefit.
- **Keep monolithic file with regions** — Retains the problem; rejected because the 2930-line file is the #1 maintainability issue.
- **Separate top-level modules** (e.g., `api/chat_messages.py`, `api/chat_proposals.py`) — Would pollute the `api/` namespace and break the domain-scoped directory convention. Rejected.

**Key implementation details**:
- `__init__.py` creates a single `router = APIRouter()` and calls `router.include_router(messages.router)`, etc.
- Shared state (ChatStateManager) is injected via FastAPI `Depends()` rather than module-level globals.
- The `generate-diagrams.sh` script (per memory) already handles both `.py` files and package directories with `__init__.py` for API route discovery — no diagram script changes needed.

---

## R2: Service Extraction Pattern for God Functions

**Decision**: Extract `confirm_proposal()` (346 lines, 7 orchestration phases) into a `ProposalOrchestrator` class in `services/proposal_orchestrator.py`, injected via FastAPI `Depends()`.

**Rationale**: The function performs 7 distinct phases: validation → user-edit application → repository resolution → GitHub issue creation → status broadcasting → workflow configuration → agent assignment. Each phase has distinct dependencies (GitHub API, WebSocket manager, workflow orchestrator, copilot polling). A class with individual methods per phase enables unit testing of each step in isolation while the orchestrator method coordinates the sequence.

**Alternatives considered**:
- **Break into standalone functions** — Loses the shared context (proposal, session, services) that threads through all 7 steps. Each function would need 6+ parameters. Rejected: parameter bloat.
- **Event-driven saga** — Overengineered for a synchronous request/response flow. The 7 steps must execute sequentially and any failure must return an HTTP error immediately. Rejected: YAGNI.
- **Keep as-is with smaller helpers** — Doesn't address the testability problem; 450-line functions remain untestable. Rejected.

**Key implementation details**:
- Constructor receives all service dependencies (github_service, connection_manager, settings_store, chat_store, workflow_orchestrator, copilot_polling).
- FastAPI `Depends()` factory function `get_proposal_orchestrator()` in `dependencies.py` wires the services.
- The `proposals.py` endpoint thin-wraps `orchestrator.confirm(proposal_id, request, session)`.

---

## R3: Stateful Module-Global Consolidation (ChatStateManager)

**Decision**: Wrap `_messages`, `_proposals`, `_recommendations`, `_locks` dictionaries plus their accessor functions into a `ChatStateManager` class, instantiated during FastAPI lifespan and stored on `app.state`.

**Rationale**: The 4 module-level dicts in `chat.py` implement a read-through cache over SQLite with per-key async locking. Consolidating into a class provides: (1) explicit lifecycle management (clear on shutdown), (2) future TTL/eviction support, (3) testability via constructor injection, (4) elimination of race condition on `_locks` dict creation.

**Alternatives considered**:
- **Redis cache** — Adds infrastructure dependency for what is currently an in-process cache. The SQLite source-of-truth pattern works well for single-process deployment. Rejected: YAGNI, violates Principle V.
- **Keep globals but add a cleanup function** — Doesn't solve testability (tests can't inject a fresh state instance). Rejected.
- **Singleton pattern** — Module-level singletons are effectively what we have now; a class on `app.state` is cleaner for FastAPI's DI model. Rejected: no improvement.

**Key implementation details**:
- Class methods: `get_messages()`, `add_message()`, `clear_messages()`, `get_proposal()`, `store_proposal()`, `get_recommendation()`, `store_recommendation()`, `get_lock()`.
- Internal retry logic (`_retry_persist()`) and persistence helpers move into the class.
- DI via `get_chat_state_manager()` in `dependencies.py` reads from `request.app.state.chat_state_manager`.

---

## R4: TypeScript Module Splitting with Barrel Re-exports

**Decision**: Split both `services/api.ts` and `types/index.ts` into domain-scoped files within their respective directories, with barrel `index.ts` files re-exporting all symbols for backward compatibility.

**Rationale**: 63 files import from `@/services/api` and 202 files import from `@/types`. Barrel re-exports (`export * from './chat'`) ensure all existing import paths (`import { ChatMessage } from '@/types'`, `import { chatApi } from '@/services/api'`) continue to work with zero consumer changes. This is the standard TypeScript library splitting pattern used by major frameworks (Material UI, Ant Design, TanStack).

**Alternatives considered**:
- **Update all import paths** — 265+ files would need import changes. Massive PR, high merge conflict risk, no additional benefit. Rejected: violates Principle V (simplicity).
- **Namespace re-architecture** — Changing `chatApi.getMessages()` to `import { getMessages } from '@/services/api/chat'` breaks the namespace pattern used across 63+ consumer files. Rejected: functional change beyond scope.
- **Aliases in tsconfig** — Could map `@/services/api` to a directory, but Vite already resolves `@/services/api` to `@/services/api/index.ts` natively. No tsconfig change needed.

**Key implementation details**:
- `services/api/client.ts` exports: `request()`, `ApiError`, `onAuthExpired`, `API_BASE_URL`, `getCsrfToken()`, `normalizeApiError()`.
- Each domain file imports from `./client` and exports its namespace object.
- `services/api/index.ts` barrel: `export { ApiError, onAuthExpired } from './client'` + `export { chatApi } from './chat'` + etc.
- `types/common.ts` holds enums and shared primitives; domain files import from `./common` as needed.
- `types/index.ts` barrel: `export * from './common'` + `export * from './chat'` + etc.

---

## R5: Bootstrap Extraction from main.py

**Decision**: Extract startup/shutdown helper functions from `main.py` lifespan (161 lines) into `services/bootstrap.py`. The lifespan function remains in `main.py` but delegates to bootstrap functions.

**Rationale**: `main.py` (859 lines) mixes application factory, middleware registration, route mounting, and lifespan logic. Extracting the startup sequence (database init, service registration, observability setup, background tasks) into named functions in `bootstrap.py` improves testability and readability. Each bootstrap function can be tested independently with mocked dependencies.

**Alternatives considered**:
- **Full application factory pattern** — Moving `create_app()` to a separate module is a larger refactoring. The issue specifically calls out bootstrap extraction as the target. Rejected: beyond current scope.
- **Keep in main.py with better comments** — Doesn't improve testability. Rejected.

**Key implementation details**:
- Functions: `bootstrap_database()`, `register_services()`, `setup_observability()`, `start_background_services()`, `shutdown_services()`.
- `main.py` lifespan calls these in sequence: `await bootstrap_database(db)` → `register_services(app, db)` → etc.
- Existing test patches (currently at `src.main.*`) will need to patch at `src.services.bootstrap.*` for direct tests, or remain at `src.main.*` for lifespan integration tests.

---

## R6: Webhook Module Splitting Strategy

**Decision**: Split `api/webhooks.py` (1033 lines) into `api/webhooks/` package with `handlers.py` (main dispatcher + security), `pull_requests.py` (PR event processing), and `ci.py` (check run/suite handlers).

**Rationale**: The webhook handler contains 3 distinct event processing domains (PR, CI, misc) plus shared infrastructure (signature verification, deduplication, event classification). Splitting by event type aligns with how webhook events are dispatched and how developers reason about the code when debugging specific webhook behaviors.

**Alternatives considered**:
- **Split by layer** (security.py, events.py, actions.py) — Cross-cuts event types, making it harder to find "all PR handling code". Rejected.
- **One file per GitHub event type** — Too granular; `issues.py` and `ping.py` would be trivially small. Grouping CI events (check_run + check_suite) is more practical. Rejected.

**Key implementation details**:
- `handlers.py` contains: `github_webhook()` main route, `verify_webhook_signature()`, `_processed_delivery_ids` BoundedSet, event classification helpers.
- `pull_requests.py` contains: `handle_pull_request_event()`, `handle_copilot_pr_ready()`, `update_issue_status_for_copilot_pr()`.
- `ci.py` contains: `handle_check_run_event()`, `handle_check_suite_event()`, `_get_auto_merge_pipeline()`.
- `__init__.py` aggregates the router and re-exports public symbols.
