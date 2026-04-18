# Runner Contract

**Feature**: 002-lifespan-startup-steps
**Owners**: `src/startup/runner.py`
**Consumers**: `main.py` (lifespan function), `tests/unit/startup/test_runner.py`

This contract specifies the exact semantics of `run_startup()` and `run_shutdown()`.

---

## R1 — `run_startup(steps, ctx) -> list[StepOutcome]`

### Signature

```python
async def run_startup(
    steps: Sequence[Step],
    ctx: StartupContext,
) -> list[StepOutcome]:
    ...
```

### Pre-conditions

1. `steps` is a non-empty sequence of objects satisfying the `Step` protocol.
2. All step names in `steps` are unique (validated by the runner; raises `ValueError` if violated).
3. `ctx` is a fully-initialised `StartupContext` (all fields set to their initial values per `data-model.md` § E3).

### Execution semantics (per step, in order)

```text
for step in steps:
    1. token = request_id_var.set(f"startup-{step.name}")
    2. start = time.perf_counter()
    3. try:
         a. if hasattr(step, "skip_if") and step.skip_if(ctx):
              outcome = StepOutcome(name, "skipped", duration, None)
         b. else:
              await step.run(ctx)
              outcome = StepOutcome(name, "ok", duration, None)
       except Exception as exc:
         c. outcome = StepOutcome(name, "failed", duration, str(exc))
            if step.fatal:
              log error, append outcome, re-raise as StartupError
            else:
              log warning with exc_info=True
    4. append outcome to results
    5. log structured line: {"step": name, "status": ..., "duration_ms": ...}
    6. request_id_var.reset(token)
```

### Post-conditions

1. Returns `list[StepOutcome]` with one entry per step that was evaluated (may be fewer than `len(steps)` if a fatal step aborted).
2. On fatal failure: raises `StartupError(step_name)` with `__cause__` set to the original exception. The partial outcome list is stored on `ctx.app.state.startup_report` before raising.
3. On success: all steps evaluated; full outcome list returned and stored on `ctx.app.state.startup_report`.

### Structured log contract

Each step produces exactly one log line via `logger.info(...)` or `logger.warning(...)` with the following `extra` keys:

| Key | Type | Description |
|---|---|---|
| `step` | `str` | Step name |
| `status` | `str` | `"ok"`, `"failed"`, or `"skipped"` |
| `duration_ms` | `float` | Wall-clock milliseconds |

For failed non-fatal steps, the log level is `WARNING` with `exc_info=True`. For fatal failures, the log level is `ERROR` with `exc_info=True`.

---

## R2 — `run_shutdown(ctx, *, shutdown_timeout) -> list[StepOutcome]`

### Signature

```python
async def run_shutdown(
    ctx: StartupContext,
    *,
    shutdown_timeout: float = 30.0,
) -> list[StepOutcome]:
    ...
```

### Execution semantics

```text
1. Iterate ctx.shutdown_hooks in reversed() order.
   For each hook:
     a. try: await asyncio.wait_for(hook(), timeout=shutdown_timeout)
     b. except (Exception, asyncio.TimeoutError): log warning, record "failed"
     c. on success: record "ok"

2. Run built-in trailing hooks (always, even if user hooks failed):
     a. drain task registry: await ctx.task_registry.drain(drain_timeout=shutdown_timeout)
     b. stop Copilot polling (if started)
     c. close database: if ctx.db: await ctx.db.close()
```

### Post-conditions

1. Returns `list[StepOutcome]` for all hooks (user + trailing).
2. Never raises — all exceptions are caught and logged.
3. Database connection is always closed (trailing hook c runs unconditionally).

### Shutdown hook naming

User-registered hooks are named `"shutdown-{registration_order}"` (0-indexed). Trailing hooks are named `"shutdown-drain"`, `"shutdown-stop-polling"`, `"shutdown-close-db"`.

---

## R3 — `StartupError` exception

```python
class StartupError(RuntimeError):
    def __init__(self, step_name: str) -> None:
        self.step_name = step_name
        super().__init__(f"Fatal startup step failed: {step_name}")
```

Raised by `run_startup` when a fatal step fails. Always has `__cause__` set to the original exception via `raise StartupError(name) from exc`.

---

## R4 — Runner acceptance tests (test_runner.py contract)

The following test scenarios MUST be covered:

| # | Scenario | Assertion |
|---|---|---|
| 1 | All steps succeed | Returns `len(steps)` outcomes, all `"ok"`, all `duration_ms >= 0` |
| 2 | Non-fatal step fails | Returns outcomes for all steps; failed step has `status="failed"` and `error != None`; subsequent steps still run |
| 3 | Fatal step fails | Raises `StartupError`; partial outcomes stored on `app.state.startup_report`; subsequent steps NOT run |
| 4 | Step with `skip_if=True` | Outcome has `status="skipped"`, `duration_ms >= 0`, `error=None` |
| 5 | `skip_if` raises | Outcome has `status="failed"`; fatal policy applies |
| 6 | Duplicate step names | Raises `ValueError` before any step runs |
| 7 | Empty step list | Returns empty list (no error) |
| 8 | Structured log output | Each step produces one log line with `step`, `status`, `duration_ms` keys |
| 9 | request_id_var set per step | Verify `request_id_var.get()` inside `run()` equals `"startup-{name}"` |
| 10 | Shutdown LIFO order | Hooks registered A→B→C execute C→B→A |
| 11 | Shutdown hook failure | Failed hook logged; subsequent hooks still run |
| 12 | Trailing hooks run after fatal | Force fatal step, assert `close_db` trailing hook still executes |
| 13 | Shutdown hook timeout | Hook exceeding timeout is cancelled and logged as failed |
