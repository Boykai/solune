# Lifespan Registration Contract

**Feature**: 002-dual-init-singleton
**Owners**: `solune/backend/src/main.py` (lifespan context manager)
**Consumers**: `dependencies.py` accessors, background tasks, tests.

This contract specifies the post-migration state of the lifespan context manager in `main.py` and the invariants for singleton registration on `app.state`.

---

## L1 — Registration block (post-migration)

All service singleton registrations MUST appear in a single contiguous block within `lifespan()`, after database initialisation and before background task creation:

```python
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    # ... logging, database init, migrations, cache init ...

    # ── Register singleton services on app.state (single source of truth) ──
    _app.state.github_service = GitHubProjectsService()
    _app.state.connection_manager = ConnectionManager()
    _app.state.github_auth_service = GitHubAuthService()

    try:
        _app.state.chat_agent_service = ChatAgentService()
    except Exception:
        logger.critical("Failed to initialise ChatAgentService during startup")
        raise

    try:
        _app.state.pipeline_run_service = PipelineRunService(db)
    except Exception:
        logger.critical("Failed to initialise PipelineRunService during startup")
        raise

    _app.state.alert_dispatcher = AlertDispatcher(
        webhook_url=settings.alert_webhook_url,
        cooldown_minutes=settings.alert_cooldown_minutes,
    )

    # OTel (conditional — None when disabled)
    if settings.otel_enabled:
        tracer, meter = init_otel(...)
        _app.state.otel_tracer = tracer
        _app.state.otel_meter = meter
    else:
        _app.state.otel_tracer = None
        _app.state.otel_meter = None

    # ... signal listener, polling, background tasks, yield ...
```

---

## L2 — Fail-fast contract (FR-010)

Every service constructor that could raise an exception MUST be wrapped in a `try/except` block that:

1. Logs a `CRITICAL`-level message identifying the service by name.
2. Re-raises the original exception (no swallowing, no wrapping in a custom exception type).

Services whose constructors are trivial (no I/O, no configuration validation) MAY omit the `try/except` if the constructor is known to be side-effect-free (e.g., `GitHubProjectsService()` which only initialises in-memory state). The decision to wrap or not MUST be documented in the implementation PR.

---

## L3 — Removed dual-registration

The following dual-registration patterns MUST be removed:

| Pattern | Location | Action |
|---|---|---|
| `set_dispatcher(_alert_dispatcher)` | `main.py:713` | Remove — `app.state.alert_dispatcher` is the single source |
| Import `github_projects_service` and assign to `app.state.github_service` | `main.py:699–702` | Replace import with direct constructor call (or keep import if constructor requires no args) |
| Import `connection_manager` and assign to `app.state.connection_manager` | `main.py:700–703` | Same as above |

After migration, no module-level global singleton is imported into `lifespan()` for the purpose of registering it on `app.state`. Singletons are either constructed directly in the lifespan or imported as classes (not instances).

---

## L4 — `app.state` attribute naming convention

| Attribute | Matches existing? | Notes |
|---|---|---|
| `db` | ✅ | Unchanged |
| `github_service` | ✅ | Unchanged |
| `connection_manager` | ✅ | Unchanged |
| `alert_dispatcher` | ✅ | Unchanged |
| `otel_tracer` | ✅ | Unchanged |
| `otel_meter` | ✅ | Unchanged |
| `chat_agent_service` | ❌ **NEW** | Follows `snake_case` convention |
| `pipeline_run_service` | ❌ **NEW** | Follows `snake_case` convention |
| `github_auth_service` | ❌ **NEW** | Follows `snake_case` convention |

All attribute names use `snake_case` matching the service class name (e.g., `ChatAgentService` → `chat_agent_service`). This convention is established by the existing `github_service`, `connection_manager`, and `alert_dispatcher` attributes.

---

## L5 — Ordering constraints

Service registration MUST follow this order within the lifespan:

1. **Database** — many services depend on the database connection.
2. **GitHubProjectsService** — no dependencies beyond configuration.
3. **ConnectionManager** — no dependencies.
4. **GitHubAuthService** — no dependencies.
5. **ChatAgentService** — no dependencies.
6. **PipelineRunService** — depends on database (`db` parameter).
7. **AlertDispatcher** — depends on settings (webhook URL, cooldown).
8. **OTel** — conditional, no dependencies on other services.

This ordering ensures that services depending on the database are registered after `db` is available. The ordering is soft (not enforced by code) but MUST be maintained for readability and correctness.

---

## L6 — Contract acceptance

1. After lifespan startup, `dir(app.state)` includes all nine attributes from L4.
2. None of the removed patterns from L3 exist in `main.py`.
3. `uv run pytest` passes — confirming that test fixtures correctly mock all registered services.
4. Starting the application with `uvicorn` succeeds and all endpoints respond normally.
