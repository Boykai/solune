# Phase 1 Data Model: Eliminate the "Dual-Init" Singleton Pattern

**Feature**: 002-dual-init-singleton
**Date**: 2026-04-18

This feature changes internal wiring, not persistent data. The "entities" below are runtime objects and patterns whose shape, lifecycle, and invariants the implementation must preserve.

---

## E1 — Service Singleton (registered on `app.state`)

**Storage**: In-memory attributes on the FastAPI `app.state` object, set during `lifespan()` in `main.py`.

**Instances** (post-migration, exhaustive):

| `app.state` attribute | Type | Constructor site | Existing? |
|---|---|---|---|
| `github_service` | `GitHubProjectsService` | `lifespan()` — import from `services/github_projects` | ✅ Already registered (line 702) |
| `connection_manager` | `ConnectionManager` | `lifespan()` — import from `services/websocket` | ✅ Already registered (line 703) |
| `alert_dispatcher` | `AlertDispatcher` | `lifespan()` — construct with settings (line 708) | ✅ Already registered (line 712) |
| `db` | `aiosqlite.Connection` | `lifespan()` — `await init_database()` (line 684) | ✅ Already registered (line 686) |
| `otel_tracer` | `Tracer \| None` | `lifespan()` — conditional `init_otel()` (line 719) | ✅ Already registered (line 720) |
| `otel_meter` | `Meter \| None` | `lifespan()` — conditional `init_otel()` (line 721) | ✅ Already registered (line 721) |
| `chat_agent_service` | `ChatAgentService` | `lifespan()` — `ChatAgentService()` | ❌ **NEW** |
| `pipeline_run_service` | `PipelineRunService` | `lifespan()` — `PipelineRunService(db)` | ❌ **NEW** |
| `github_auth_service` | `GitHubAuthService` | `lifespan()` — `GitHubAuthService()` | ❌ **NEW** |

**Validation rules**:

- Every attribute MUST be set before the `yield` in the lifespan context manager. Any `None` value after yield (except `otel_tracer`/`otel_meter` when OTel is disabled) indicates a startup failure.
- Attribute names are permanent — renaming an `app.state` attribute is a breaking change for any code that accesses it via `getattr(request.app.state, "name")`.
- Service constructors MUST NOT perform I/O that could block the event loop synchronously. Async initialisation (e.g., database) uses `await` in the lifespan.

**Lifecycle**:

1. **Created**: During `lifespan()` startup, before `yield`.
2. **Accessed**: Via `Depends(get_X)` in route handlers; via `app.state.X` in background tasks.
3. **Destroyed**: Implicitly when the process exits. No explicit teardown is needed for stateless services. Services with resources (database, alert dispatcher) are shut down in the `finally` block of the lifespan.

---

## E2 — Module-Level Global Sentinel

**Storage**: Module-level variable in the service module file (e.g., `services/chat_agent.py`).

**Post-migration state**:

| Module | Variable | Pre-migration value | Post-migration value |
|---|---|---|---|
| `services/github_projects/service.py` | `github_projects_service` | `GitHubProjectsService()` instance | `None` (or removed) |
| `services/websocket.py` | `connection_manager` | `ConnectionManager()` instance | `None` (or removed) |
| `services/chat_agent.py` | `_chat_agent_service` | `None` (lazy-init) | `None` (stays, but lazy-init function removed) |
| `services/github_auth.py` | `github_auth_service` | `GitHubAuthService()` instance | `None` (or removed) |
| `services/alert_dispatcher.py` | `_dispatcher` | `None` (set via `set_dispatcher()`) | `None` (setter/getter removed) |
| `api/pipelines.py` | `_run_service_instance` | `None` (lazy-init) | `None` (stays, but lazy-init function removed) |

**Validation rules**:

- Post-migration, no production code path MUST read from these variables. They exist only for backward compatibility during the transition (if needed) and are set to `None`.
- The `get_chat_agent_service()` and `_get_run_service()` lazy-init functions are either removed entirely or replaced with stubs that raise `RuntimeError("Use Depends(get_X) instead")` to catch accidental direct calls.
- `set_dispatcher()` and `get_dispatcher()` in `alert_dispatcher.py` are removed. Any remaining import sites are updated to use `app.state.alert_dispatcher` or `Depends(get_alert_dispatcher)`.

---

## E3 — Dependency Accessor Function (in `dependencies.py`)

**Storage**: Python functions in `solune/backend/src/dependencies.py`.

**Post-migration inventory**:

| Function | Signature | Returns from | Existing? |
|---|---|---|---|
| `get_github_service` | `(request: Request) -> GitHubProjectsService` | `request.app.state.github_service` | ✅ Exists (line 33) — remove fallback |
| `get_connection_manager` | `(request: Request) -> ConnectionManager` | `request.app.state.connection_manager` | ✅ Exists (line 44) — remove fallback |
| `get_database` | `(request: Request) -> aiosqlite.Connection` | `request.app.state.db` | ✅ Exists (line 54) — remove fallback |
| `get_chat_agent_service` | `(request: Request) -> ChatAgentService` | `request.app.state.chat_agent_service` | ❌ **NEW** |
| `get_pipeline_run_service` | `(request: Request) -> PipelineRunService` | `request.app.state.pipeline_run_service` | ❌ **NEW** |
| `get_github_auth_service` | `(request: Request) -> GitHubAuthService` | `request.app.state.github_auth_service` | ❌ **NEW** |
| `get_alert_dispatcher` | `(request: Request) -> AlertDispatcher` | `request.app.state.alert_dispatcher` | ❌ **NEW** |

**Contract** (per `contracts/accessor-contract.md`):

```python
def get_X(request: Request) -> ServiceType:
    """Return the singleton ServiceType from app.state."""
    return request.app.state.attribute_name
```

**Validation rules**:

- No fallback-to-global logic. The function body is a single `return` statement (or a lazy import + return for type safety).
- Lazy imports inside the function body are used only for TYPE_CHECKING avoidance and circular import prevention (FR-011). The imported symbol is the type, not the instance.
- Each function is usable as `Depends(get_X)` in route handler signatures.

---

## E4 — Resettable State Entry

**Storage**: Entries in a module-level list in `src/services/resettable_state.py`.

**Structure**:

```python
# Each entry is a (name, reset_fn) tuple
_registry: list[tuple[str, Callable[[], None]]] = []
```

**Post-migration registry contents** (from `_clear_test_caches()` analysis):

| Category | Registered entries | Reset action |
|---|---|---|
| General caches | `cache` (LRU), `settings_cache` | `.clear()`, `clear_settings_cache()` |
| `api/chat.py` | `_messages`, `_proposals`, `_recommendations`, `_locks` | `.clear()` each |
| `pipeline_state_store.py` | `_pipeline_states`, `_issue_main_branches`, `_issue_sub_issue_map`, `_agent_trigger_inflight`, `_project_launch_locks`, `_store_lock`, `_db` | `.clear()` or `= None` |
| `workflow_orchestrator/` | `_transitions`, `_workflow_configs`, `_tracking_table_cache`, `_orchestrator_instance` | `.clear()` or `= None` |
| `copilot_polling/state.py` | 17 collections + scalars + locks (lines 312–349 of `conftest.py`) | `.clear()`, `= None`, or `= asyncio.Lock()` |
| `websocket.py` | `_ws_lock` | `= None` |
| `settings_store.py` | `_queue_mode_cache`, `_auto_merge_cache` | `.clear()` |
| `signal_chat.py` | `_signal_pending` | `.clear()` |
| `github_auth.py` | `_oauth_states` | `.clear()` |
| `agent_creator.py` | `_agent_sessions` | `.clear()` |
| `agents/service.py` | `_chat_sessions`, `_chat_session_timestamps` | `.clear()` |
| `chores/chat.py` | `_conversations` | `.clear()` |
| `template_files.py` | `_cached_files`, `_cached_warnings` | `= None` |
| `app_templates/registry.py` | `_cache` | `= None` |
| `done_items_store.py` | `_db` | `= None` |
| `session_store.py` | `_encryption_service` | `= None` |

**Validation rules**:

- Registration is at module load time (top-level `register_resettable()` call or `@resettable_state` decorator). No runtime overhead on hot paths.
- `reset_all()` MUST catch exceptions per entry and log them (FR-006). It MUST NOT short-circuit on the first error.
- The registry list itself is never cleared — it is append-only across the application's lifetime.

---

## E5 — Autouse Fixture (in `conftest.py`)

**Storage**: Python function in `solune/backend/tests/conftest.py`.

**Post-migration shape**:

```python
@pytest.fixture(autouse=True)
def _clear_test_caches():
    """Reset all registered mutable state and dependency overrides between tests."""
    from src.services.resettable_state import reset_all

    reset_all()
    yield
    reset_all()
    # Clear dependency overrides to prevent bleed (FR-008)
    from src.main import create_app
    # app instance is created per-test in the client fixture;
    # overrides are cleared when the client fixture tears down.
```

**Validation rules**:

- The fixture is `autouse=True` and function-scoped (default).
- `reset_all()` is called both before and after the test body.
- `app.dependency_overrides` is cleared in the `client` fixture teardown (the `async with AsyncClient(...)` block already creates a fresh app per test). The autouse fixture handles non-client tests that may still mutate module-level state.

---

## E6 — Dependency Override (test-time only)

**Storage**: Entries in `app.dependency_overrides` dict, set in test fixtures.

**Post-migration pattern** (replaces multi-path `patch()` calls):

```python
# In conftest.py client fixture
app.dependency_overrides[get_github_service] = lambda: mock_github_service
app.dependency_overrides[get_connection_manager] = lambda: mock_websocket_manager
app.dependency_overrides[get_database] = lambda: mock_db
app.dependency_overrides[get_chat_agent_service] = lambda: mock_chat_agent_service
app.dependency_overrides[get_pipeline_run_service] = lambda: mock_pipeline_run_service
app.dependency_overrides[get_github_auth_service] = lambda: mock_github_auth_service
app.dependency_overrides[get_alert_dispatcher] = lambda: mock_alert_dispatcher
```

**Validation rules**:

- Each override key is the accessor function object (not a string path).
- The override value is a zero-argument callable that returns the mock.
- Overrides are automatically scoped to the `client` fixture's `app` instance; they do not bleed to other tests because each test gets a fresh `app` from `create_app()`.

---

## Cross-entity invariants

1. **Single source of truth**: For every entry in E1, the corresponding E2 sentinel is `None` and the E3 accessor reads exclusively from `app.state`. No production code reads from E2.
2. **Registry completeness**: Every variable currently reset in `_clear_test_caches()` (E5 pre-migration) has a corresponding entry in E4 post-migration. `reset_all()` covers at least the same set.
3. **Override sufficiency**: Every `patch()` call in `conftest.py` that targets a service singleton import path (E2) is removed post-migration. The equivalent mocking is achieved via E6 entries only.
4. **Fail-fast**: Every E1 constructor that could raise is wrapped in a `try/except` that logs the service name and re-raises (E1 validation rule, FR-010).
5. **No runtime overhead**: E4 registry is append-only at module load time and iterated only by E5 during tests. Production code never calls `reset_all()`.
