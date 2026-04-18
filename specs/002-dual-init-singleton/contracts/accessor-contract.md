# Accessor Contract

**Feature**: 002-dual-init-singleton
**Owners**: `solune/backend/src/dependencies.py`
**Consumers**: Every API route handler that uses `Depends(get_X)`.

This contract specifies the shape, behaviour, and invariants of dependency accessor functions in `dependencies.py`.

---

## A1 — Function signature

Every service accessor MUST follow this exact pattern:

```python
def get_X(request: Request) -> ServiceType:
    """Return the singleton ServiceType from app.state."""
    return request.app.state.attribute_name
```

Where:

- `request: Request` is the only parameter (FastAPI injects it via `Depends()`).
- `ServiceType` is the concrete return type (not `Optional`).
- `attribute_name` matches the `app.state` attribute set during lifespan startup.

---

## A2 — No fallback logic

The function body MUST be a single `return` statement (plus an optional lazy import for the type). There MUST NOT be any fallback-to-global logic:

```python
# ❌ FORBIDDEN — dual-init pattern
def get_X(request: Request) -> ServiceType:
    svc = getattr(request.app.state, "attr", None)
    if svc is not None:
        return svc
    from src.services.module import global_instance
    return global_instance

# ✅ REQUIRED — single source of truth
def get_X(request: Request) -> ServiceType:
    return request.app.state.attr
```

---

## A3 — Lazy imports for circular import avoidance (FR-011)

When the return type is defined in a service module that could create a circular import, the type annotation uses `TYPE_CHECKING` and the return type is not validated at runtime:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.chat_agent import ChatAgentService

def get_chat_agent_service(request: Request) -> ChatAgentService:
    """Return the singleton ChatAgentService from app.state."""
    return request.app.state.chat_agent_service
```

The lazy import is for the *type* only. The *value* (`request.app.state.X`) is a direct attribute access with no import needed.

---

## A4 — Complete accessor inventory (post-migration)

| Function | `app.state` attribute | Return type |
|---|---|---|
| `get_github_service` | `github_service` | `GitHubProjectsService` |
| `get_connection_manager` | `connection_manager` | `ConnectionManager` |
| `get_database` | `db` | `aiosqlite.Connection` |
| `get_chat_agent_service` | `chat_agent_service` | `ChatAgentService` |
| `get_pipeline_run_service` | `pipeline_run_service` | `PipelineRunService` |
| `get_github_auth_service` | `github_auth_service` | `GitHubAuthService` |
| `get_alert_dispatcher` | `alert_dispatcher` | `AlertDispatcher` |

---

## A5 — Usage in route handlers

Route handlers receive the service via `Depends()`:

```python
from src.dependencies import get_github_service

@router.post("/projects/{project_id}/tasks")
async def create_task(
    project_id: str,
    body: CreateTaskBody,
    github_service: GitHubProjectsService = Depends(get_github_service),
    session: UserSession = Depends(require_session),
) -> TaskResponse:
    # Use github_service directly — no import of the module-level global
    result = await github_service.create_task(...)
    return result
```

---

## A6 — Contract acceptance

For every accessor `get_X`:

1. `get_X` appears in `dependencies.py` with exactly one `return` statement.
2. `grep -n 'getattr.*app.state' dependencies.py` returns zero matches (no fallback logic).
3. Every route handler that previously imported the module-level global now uses `Depends(get_X)`.
4. `app.dependency_overrides[get_X] = lambda: mock` in tests replaces all `patch()` calls for that service.
