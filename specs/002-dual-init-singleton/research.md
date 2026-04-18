# Phase 0 Research: Eliminate the "Dual-Init" Singleton Pattern

**Feature**: 002-dual-init-singleton
**Date**: 2026-04-18

This document resolves the open questions and validates the assumptions in `spec.md` and `plan.md` Technical Context. All `NEEDS CLARIFICATION` markers have been resolved through codebase investigation.

---

## R1 — Complete singleton inventory and current initialisation patterns

**Decision**: Eight service singletons require migration. The inventory is exhaustive based on `grep` evidence across the entire `solune/backend/src/` tree.

| # | Service | Module | Global Variable | Current Accessor | On `app.state`? | Fallback? |
|---|---------|--------|----------------|-----------------|-----------------|-----------|
| 1 | GitHubProjectsService | `services/github_projects/service.py` | `github_projects_service` (module-level instance) | `get_github_service(request)` in `dependencies.py:33` | ✅ `app.state.github_service` | ✅ Falls back to module global (line 39) |
| 2 | ConnectionManager | `services/websocket.py` | `connection_manager` (module-level instance) | `get_connection_manager(request)` in `dependencies.py:44` | ✅ `app.state.connection_manager` | ✅ Falls back to module global (line 49) |
| 3 | ChatAgentService | `services/chat_agent.py` | `_chat_agent_service` (line 957, `None`) | `get_chat_agent_service()` (line 960, lazy-init) | ❌ | N/A — always-global |
| 4 | PipelineRunService | `api/pipelines.py` | `_run_service_instance` (line 732, `None`) | `_get_run_service()` (line 735, lazy-init) | ❌ | N/A — always-global |
| 5 | GitHubAuthService | `services/github_auth.py` | `github_auth_service` (module-level instance) | None (direct import) | ❌ | N/A — always-global |
| 6 | AlertDispatcher | `services/alert_dispatcher.py` | `_dispatcher` (line 19, `None`) | `get_dispatcher()` (line 31) + `set_dispatcher()` (line 25) | ✅ `app.state.alert_dispatcher` | Dual: both `app.state` and module setter |
| 7 | Database connection | `services/database.py` | `_connection` | `get_db()` in `database.py` + `get_database(request)` in `dependencies.py:54` | ✅ `app.state.db` | ✅ Falls back to `get_db()` (line 59) |
| 8 | OTel tracer/meter | `services/otel_setup.py` | N/A (returned from `init_otel()`) | None | ✅ `app.state.otel_tracer` / `app.state.otel_meter` | N/A — already app.state only |

**Rationale**: The spec's inventory (FR-001) lists six named services. The database connection and OTel are already partially migrated but follow the same dual-init pattern (database) or are already clean (OTel). The database accessor in `dependencies.py` has the same fallback pattern and should be migrated alongside the others for consistency.

**Alternatives considered**: Migrating only the six named services. Rejected — the database accessor is the most heavily patched service in tests (175+ `get_db` patches) and follows the identical dual-init pattern.

---

## R2 — Direct import sites that must be migrated to `Depends()`

**Decision**: Every API module that imports a service singleton directly must be refactored to receive it via `Depends()` in the route handler signature.

### GitHubProjectsService (7 API modules, 1 utility module)

| Module | Import Style | Usage Count |
|--------|-------------|-------------|
| `api/board.py` | Top-level `from src.services.github_projects import github_projects_service` | Multiple |
| `api/projects.py` | Top-level import | Multiple |
| `api/tasks.py` | Top-level import | Multiple |
| `api/workflow.py` | Top-level import | Multiple |
| `api/chores.py` | Top-level import | Multiple |
| `api/pipelines.py` | Top-level import | Multiple |
| `api/webhooks.py` | Top-level import | Multiple |
| `api/chat.py` | Local import inside functions (lines 429, 540) | 2 |
| `api/metadata.py` | Local import inside functions (lines 26, 40) | 2 |
| `api/agents.py` | Local import inside functions (lines 545, 568) | 2 |
| `api/tools.py` | Local import inside function (line 44) | 1 |

### ConnectionManager (4 API modules)

| Module | Import Style |
|--------|-------------|
| `api/projects.py` | Top-level `from src.services.websocket import connection_manager` |
| `api/tasks.py` | Top-level import |
| `api/workflow.py` | Top-level import |
| `api/apps.py` | Local import inside function (line 555) |

### GitHubAuthService (2 API modules)

| Module | Import Style |
|--------|-------------|
| `api/auth.py` | Top-level `from src.services.github_auth import github_auth_service` |
| `api/projects.py` | Top-level import |

### ChatAgentService (1 API module)

| Module | Import Style |
|--------|-------------|
| `api/chat.py` | Top-level `from src.services.chat_agent import get_chat_agent_service` — called 5 times (lines 1180, 1542, 2135, 2212, 2519) |

### PipelineRunService (1 API module)

| Module | Import Style |
|--------|-------------|
| `api/pipelines.py` | Module-private `_get_run_service()` lazy-init — called 7 times |

### AlertDispatcher (2 service modules, 0 API modules)

| Module | Import Style |
|--------|-------------|
| `services/copilot_polling/recovery.py` | `from src.services.alert_dispatcher import get_dispatcher` — 2 call sites |
| `services/copilot_polling/polling_loop.py` | `from src.services.alert_dispatcher import get_dispatcher` — 1 call site |

**Rationale**: Top-level route-handler imports are the primary migration target — they become `Depends()` parameters. Local (inside-function) imports in service modules (not route handlers) that are called from background tasks (not HTTP requests) cannot use `Depends()` because there is no `Request` object. These retain the `app.state` accessor pattern by receiving the `app` reference from the lifespan-scoped task context.

**Alternatives considered**: Making background task functions also use `Depends()`. Rejected — `Depends()` is a FastAPI/Starlette mechanism that only works within the request lifecycle. Background tasks access `app.state` directly via the `app` reference passed at task creation.

---

## R3 — AlertDispatcher migration strategy

**Decision**: Remove `set_dispatcher()` and `get_dispatcher()` module-level functions. Move all reads to either `Depends(get_alert_dispatcher)` (for route handlers) or direct `app.state.alert_dispatcher` access (for background tasks in `copilot_polling/`).

**Rationale**: The AlertDispatcher is the only service with a true dual-registration path — it is both set on `app.state.alert_dispatcher` (line 712 of `main.py`) and registered via `set_dispatcher()` (line 713). The three call sites (`recovery.py:237`, `recovery.py:1065`, `polling_loop.py:456`) are all in background task code, not route handlers. These should access the dispatcher via the `app` reference already available in the polling context (passed through the polling state or via module-level `_app` reference set during lifespan).

**Alternatives considered**:

- Keep `get_dispatcher()` as a convenience function that reads from `app.state` internally. Rejected — this perpetuates the dual-init pattern (the module function hides the real source of truth).
- Pass dispatcher as a parameter to every polling function. Rejected — too invasive; the polling functions already have access to the app reference.

---

## R4 — PipelineRunService migration strategy

**Decision**: Move `PipelineRunService` instantiation into the lifespan (alongside other singletons) and register it on `app.state.pipeline_run_service`. Create a new `get_pipeline_run_service(request)` accessor in `dependencies.py`. Replace all `_get_run_service()` calls in `api/pipelines.py` with `Depends(get_pipeline_run_service)`.

**Rationale**: `_get_run_service()` in `api/pipelines.py` (line 735) is a lazy-init function that creates a `PipelineRunService(get_db())` on first call. This couples the service instantiation to the database connection at call time. Moving instantiation to the lifespan ensures the database connection is fully initialised before the service is created, and aligns with the pattern established for other singletons.

**Alternatives considered**: Keep `PipelineRunService` lazy-initialised but register on `app.state` at first access. Rejected — lazy registration on `app.state` introduces a race condition window where `app.state.pipeline_run_service` is `None` during early requests.

---

## R5 — Resettable state registry design

**Decision**: Implement the registry as a simple module-level list of `(name, reset_fn)` tuples in a new `src/services/resettable_state.py` module. The `@resettable_state` decorator or `register_resettable()` function appends entries. The autouse fixture calls `reset_all()` which iterates the list, calling each `reset_fn()` and logging (not raising) any exceptions.

**Rationale**: The simplest possible design that satisfies FR-004 through FR-006. A list of callables is ~30 lines of code with zero runtime overhead (the list is only iterated by the test fixture). The decorator form is syntactic sugar — the core API is `register_resettable(name, reset_fn)`.

**Design**:

```python
# src/services/resettable_state.py
from __future__ import annotations
import logging
from typing import Callable

logger = logging.getLogger(__name__)

_registry: list[tuple[str, Callable[[], None]]] = []


def register_resettable(name: str, reset_fn: Callable[[], None]) -> None:
    """Register a piece of mutable state for automatic test cleanup."""
    _registry.append((name, reset_fn))


def reset_all() -> None:
    """Reset all registered state. Logs errors but does not raise."""
    for name, reset_fn in _registry:
        try:
            reset_fn()
        except Exception:
            logger.exception("Failed to reset state: %s", name)
```

**Alternatives considered**:

- `@resettable_state` class decorator that wraps module globals. Rejected — over-engineered for the use case; most globals are plain dicts or `None` sentinels, not class instances.
- `ContextVar`-based approach. Rejected — `ContextVar` is designed for per-task state in async code, not for module-level singletons. It would add complexity without solving the core problem.
- Full DI container (`dependency-injector` library). Rejected — out of scope per spec.

---

## R6 — Circular import avoidance strategy

**Decision**: All accessor functions in `dependencies.py` use lazy imports (inside the function body) to import type classes from service modules. This is the existing pattern for `get_github_service()`, `get_connection_manager()`, and `get_database()`, and is extended to all new accessors.

**Rationale**: `dependencies.py` is imported by all API modules (for `Depends()`). If `dependencies.py` imports from `services/chat_agent.py` at module level, and `chat_agent.py` imports from `api/` or `dependencies.py`, a circular import occurs. Lazy imports inside function bodies break the cycle because by the time the function is called, all modules have finished loading.

**Verification**: The existing three accessors already use this pattern (confirmed by reading `dependencies.py`). Python caches module imports after the first load, so the lazy import adds negligible overhead on subsequent calls.

**Alternatives considered**: Moving accessor functions to a separate `accessors.py` module that is not imported by service modules. Rejected — this splits related DI code across two files without clear benefit; the lazy import pattern is already established in the codebase.

---

## R7 — Test migration strategy for `conftest.py` patches

**Decision**: Migrate in two phases:

1. **Phase A (Story 1)**: Register all singletons on `app.state`, add new `Depends()` accessors, update route handlers to use `Depends()`. Keep the existing `patch()` calls in `conftest.py` temporarily — they become redundant but harmless.
2. **Phase B (Story 3)**: Remove the redundant `patch()` calls and verify that `dependency_overrides` alone provides correct mocking. Reduce `_clear_test_caches()` to delegate to `reset_all()` from the resettable registry.

**Rationale**: A two-phase approach reduces risk. Phase A is a pure refactoring of production code with no test changes (all existing tests continue to pass with both `patch()` and `dependency_overrides` active). Phase B is a pure test refactoring with no production code changes.

**Alternatives considered**: Big-bang migration (production and test changes in one PR). Rejected — too risky; a single failing test blocks the entire PR.

---

## R8 — Background task access to singletons

**Decision**: Background tasks launched during lifespan (e.g., `_session_cleanup_loop()`, `_polling_watchdog_loop()`, copilot polling tasks) continue to access singletons via direct `app.state` attribute access on the `_app` reference captured in the lifespan closure. They do NOT use `Depends()`.

**Rationale**: `Depends()` is a request-scoped mechanism. Background tasks have no `Request` object. The lifespan closure already captures `_app`, making `_app.state.X` the natural access pattern. The AlertDispatcher usage in `copilot_polling/recovery.py` and `polling_loop.py` transitions from `get_dispatcher()` to `app.state.alert_dispatcher` via the app reference already threaded through the polling infrastructure.

**Alternatives considered**: Creating a service locator that wraps `app.state` for non-request contexts. Rejected — adds an abstraction layer with no benefit; `app.state.X` is already clear and explicit.

---

## R9 — Fail-fast behaviour during lifespan startup (FR-010)

**Decision**: Wrap each service singleton constructor call in the lifespan with a `try/except` that logs the service name and re-raises the exception. FastAPI's default behaviour already prevents the app from serving requests if the lifespan raises, so the only addition is a structured log line identifying which service failed.

**Implementation pattern**:

```python
# In lifespan()
try:
    _app.state.chat_agent_service = ChatAgentService()
except Exception:
    logger.critical("Failed to initialise ChatAgentService during startup")
    raise
```

**Rationale**: The existing lifespan does not catch exceptions during service registration (lines 698–724 of `main.py`), so an error in any constructor already prevents startup. The `try/except/raise` pattern adds diagnostic clarity without changing the failure behaviour.

**Alternatives considered**: Collecting all constructor errors and raising an aggregate `StartupError`. Rejected — over-engineered; services initialise sequentially, so the first failure is the actionable one.

---

## R10 — `_clear_test_caches()` migration path

**Decision**: The existing `_clear_test_caches()` fixture (lines 245–389 of `conftest.py`) contains ~100 lines of manual reset code. After the resettable registry is populated, the fixture body is reduced to:

```python
@pytest.fixture(autouse=True)
def _clear_test_caches():
    from src.services.resettable_state import reset_all
    reset_all()
    yield
    reset_all()
```

Any module-level state that is currently cleared manually in `_clear_test_caches()` must register itself with the resettable registry. The migration is verified by removing one manual clearing line at a time and confirming the test suite still passes (the registry-based reset covers it).

**Rationale**: Gradual migration (one module at a time) is safer than replacing the entire fixture body at once. Each step is independently verifiable.

**Alternatives considered**: Keeping `_clear_test_caches()` as a fallback alongside the registry. Rejected — maintaining two cleanup mechanisms defeats the purpose of the registry.

---

## Open questions

None. All Technical Context entries resolved with concrete defaults above. No `NEEDS CLARIFICATION` markers remain.
