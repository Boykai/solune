# Phase 1 Data Model: Refactor main.py Lifespan into src/startup/ Step Package

**Feature**: 002-lifespan-startup-steps
**Date**: 2026-04-18

This feature introduces three core entities (Step, StepOutcome, StartupContext) and a fifteen-entry step inventory. The "data model" here describes runtime types whose shapes the implementation must preserve.

---

## E1 — Step Protocol (`src/startup/protocol.py`)

**Storage**: Runtime Protocol class; no persistence.

**Required members**:

| Member | Type | Description |
|---|---|---|
| `name` | `str` | Stable identifier used in logs, metrics, and the startup report. Must be unique across the step list. |
| `fatal` | `bool` | If `True`, a failure in `run()` aborts startup (runner re-raises). If `False`, failure is logged and startup continues. |
| `run` | `(ctx: StartupContext) -> Awaitable[None]` | Async body of the step. May mutate `ctx.app.state`, register tasks via `ctx.task_registry`, or append coroutines to `ctx.background`. |

**Optional members**:

| Member | Type | Default | Description |
|---|---|---|---|
| `skip_if` | `(ctx: StartupContext) -> bool` | *(absent — step always runs)* | Synchronous predicate. If present and returns `True`, the runner records the step as "skipped" and does not call `run()`. |

**Validation rules**:

- `name` must be non-empty and unique within any step list passed to the runner.
- Steps that implement `skip_if` must handle their own exceptions inside `skip_if` only if they want custom behaviour; otherwise the runner catches exceptions and applies the `fatal` policy (research R10).
- The Protocol is structural (`typing.Protocol`); steps do not inherit from it. Pyright verifies conformance at type-check time.

---

## E2 — StepOutcome dataclass (`src/startup/protocol.py`)

**Storage**: In-memory dataclass; stashed as `list[StepOutcome]` on `app.state.startup_report`.

**Fields**:

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Copy of `step.name`. |
| `status` | `Literal["ok", "failed", "skipped"]` | Final disposition of the step. |
| `duration_ms` | `float` | Wall-clock time in milliseconds (from `time.perf_counter()` delta × 1000). |
| `error` | `str \| None` | `str(exception)` if `status == "failed"`, else `None`. |

**State transitions** (per step execution):

```text
                  ┌─ skip_if returns True ──► skipped (duration ≈ 0)
                  │
[start] ──► evaluate skip_if ──► run() ──► ok (duration > 0)
                  │                   │
                  │                   └─ exception ──► failed (duration > 0)
                  │
                  └─ skip_if raises ──► failed (fatal policy applies)
```

**Validation rules**:

- `duration_ms` is always ≥ 0.
- `error` is non-`None` if and only if `status == "failed"`.
- `name` must match the originating step's `name` exactly.

---

## E3 — StartupContext dataclass (`src/startup/protocol.py`)

**Storage**: In-memory mutable dataclass; created in `lifespan()`, passed to every step, discarded after startup.

**Fields**:

| Field | Type | Initial Value | Mutated By |
|---|---|---|---|
| `app` | `FastAPI` | The application instance from `lifespan(_app)` | Steps set attributes on `app.state` |
| `settings` | `Settings` | `get_settings()` | Read-only (never mutated by steps) |
| `db` | `aiosqlite.Connection \| None` | `None` | `s03_database` sets it to the opened connection |
| `task_registry` | `TaskRegistry` | Module-level `task_registry` singleton | Steps call `task_registry.create_task()` |
| `background` | `list[Coroutine[Any, Any, None]]` | `[]` | `s15_background_loops` appends loop coroutines |
| `shutdown_hooks` | `list[Callable[[], Awaitable[None]]]` | `[]` | Steps append cleanup callables (e.g., `s10_signal_ws` appends `stop_signal_ws_listener`) |

**Lifecycle**:

1. Created in `lifespan()` before calling `run_startup()`.
2. Passed to `run_startup(steps, ctx)` — steps read/write fields.
3. After startup, `ctx.background` is consumed by the TaskGroup (coroutines started).
4. `ctx.shutdown_hooks` is consumed by `run_shutdown(ctx)` during teardown.
5. `ctx` itself is not stored long-term; `app.state.startup_report` (a `list[StepOutcome]`) is the only persistent artefact.

**Validation rules**:

- `db` is `None` until `s03_database` runs. Steps that depend on `db` (steps 4–15) must be ordered after step 3 in the step list. The runner does not enforce this — step ordering is the responsibility of the step list author.
- `background` must not be consumed before all steps complete. The runner returns the list; `lifespan()` feeds it to the TaskGroup.
- `shutdown_hooks` are consumed in LIFO order by `run_shutdown()`.

---

## E4 — Step Inventory (canonical step list)

**Storage**: Declared as `STARTUP_STEPS: list[Step]` in `src/startup/steps/__init__.py`.

| # | Step Class | Module | `name` | `fatal` | `skip_if` | Source (current) |
|---|---|---|---|---|---|---|
| 1 | `LoggingStep` | `s01_logging.py` | `"logging"` | `True` | — | `setup_logging()` in lifespan head |
| 2 | `AsyncioExcHandlerStep` | `s02_asyncio_exc.py` | `"asyncio_exception_handler"` | `False` | — | main.py:663 |
| 3 | `DatabaseStep` | `s03_database.py` | `"database"` | `True` | — | main.py:684 |
| 4 | `PipelineCacheStep` | `s04_pipeline_cache.py` | `"pipeline_state_cache"` | `True` | — | main.py:689 |
| 5 | `DoneItemsCacheStep` | `s05_done_items_cache.py` | `"done_items_cache"` | `True` | — | main.py:694 |
| 6 | `SingletonServicesStep` | `s06_singleton_svcs.py` | `"singleton_services"` | `True` | — | main.py:698 |
| 7 | `AlertDispatcherStep` | `s07_alert_dispatcher.py` | `"alert_dispatcher"` | `False` | — | main.py:706 |
| 8 | `OtelStep` | `s08_otel.py` | `"otel"` | `False` | `not settings.otel_enabled` | main.py:716 |
| 9 | `SentryStep` | `s09_sentry.py` | `"sentry"` | `False` | `not settings.sentry_dsn` | main.py:727 |
| 10 | `SignalWsStep` | `s10_signal_ws.py` | `"signal_ws_listener"` | `False` | — | main.py:739 |
| 11 | `CopilotPollingStep` | `s11_copilot_polling.py` | `"copilot_polling_autostart"` | `False` | — | main.py:743 (wraps `_auto_start_copilot_polling`) |
| 12 | `MultiProjectStep` | `s12_multi_project.py` | `"multi_project_discovery"` | `False` | — | main.py:748 (wraps `_discover_and_register_active_projects`) |
| 13 | `PipelineRestoreStep` | `s13_pipeline_restore.py` | `"app_pipeline_polling_restore"` | `False` | — | main.py:755 (wraps `_restore_app_pipeline_polling`) |
| 14 | `AgentMcpSyncStep` | `s14_agent_mcp_sync.py` | `"agent_mcp_sync"` | `False` | — | main.py:762 (wraps `_startup_agent_mcp_sync` via task_registry) |
| 15 | `BackgroundLoopsStep` | `s15_background_loops.py` | `"background_loops"` | `True` | — | main.py:774 (enqueues `_session_cleanup_loop` + `_polling_watchdog_loop`) |

**Validation rules**:

- The step list order is the execution order. No step may be reordered without verifying dependency chains (E3 lifecycle notes).
- All 15 step names must be unique (runner validates at startup — research R9).
- Steps 1–9 are migrated in PR 2; steps 10–14 in PR 3; step 15 (background loops) in PR 3 or PR 4.

---

## E5 — Startup Report (`app.state.startup_report`)

**Storage**: `list[StepOutcome]` stored on `app.state.startup_report` after `run_startup()` completes.

**Structure**: Ordered list matching the step execution sequence. Contains exactly one `StepOutcome` per step in the input list.

**Consumers**: Currently none (introspection only). A future `GET /api/v1/healthz/startup` endpoint may surface it (out of scope).

**Validation rules**:

- Length of the report equals the number of steps in the input list (even if startup was aborted by a fatal step — the fatal step's outcome is the last entry, and subsequent steps are not recorded).
- The report is set exactly once per application boot. It is not updated after startup.

---

## E6 — StartupError exception (`src/startup/runner.py`)

**Storage**: Runtime exception class; not persisted.

**Fields**:

| Field | Type | Description |
|---|---|---|
| `step_name` | `str` | Name of the fatal step that failed. |
| `__cause__` | `BaseException` | The original exception (set via `raise StartupError(...) from exc`). |

**Lifecycle**: Raised by the runner when a fatal step fails. Propagates through `lifespan()` to FastAPI, which aborts the cold start. The `__cause__` chain preserves the original traceback for debugging.

---

## Cross-entity invariants

1. **Step name uniqueness**: `len(set(s.name for s in STARTUP_STEPS)) == len(STARTUP_STEPS)`.
2. **Report completeness**: `len(app.state.startup_report) <= len(STARTUP_STEPS)` (equals if no fatal failure; less if a fatal step aborted early).
3. **Context lifecycle**: `StartupContext` is created before `run_startup` and is not referenced after the TaskGroup starts (steps should not retain a reference to `ctx`).
4. **Shutdown hook LIFO**: `run_shutdown` iterates `ctx.shutdown_hooks` in `reversed()` order, then appends the three built-in trailing hooks.
5. **Background loop deferred start**: No coroutine in `ctx.background` is awaited until all steps complete and the TaskGroup is entered.
