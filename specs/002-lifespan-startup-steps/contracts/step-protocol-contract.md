# Step Protocol Contract

**Feature**: 002-lifespan-startup-steps
**Owners**: `src/startup/protocol.py`
**Consumers**: `src/startup/runner.py`, every step module in `src/startup/steps/`, `tests/unit/startup/`

This contract specifies the structural interface every startup step must satisfy and the shape of the outcome record.

---

## P1 — Step Protocol

A step is any object that satisfies the following `typing.Protocol`:

```python
from typing import Protocol, runtime_checkable
from src.startup.protocol import StartupContext

@runtime_checkable
class Step(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def fatal(self) -> bool: ...

    async def run(self, ctx: StartupContext) -> None: ...
```

### Optional extension: skip_if

A step MAY additionally implement:

```python
def skip_if(self, ctx: StartupContext) -> bool: ...
```

If present and returning `True`, the runner skips `run()` and records the step as `"skipped"`. If absent, the step always runs.

### Protocol constraints

- `name` must return a non-empty string that is unique across the step list.
- `fatal` must return a stable boolean (it must not change between calls).
- `run(ctx)` is an async method. It may:
  - Read/write `ctx.app.state` attributes.
  - Call `ctx.task_registry.create_task()` for fire-and-forget work.
  - Append coroutine objects to `ctx.background` for long-running loops.
  - Append callables to `ctx.shutdown_hooks` for cleanup.
  - Read `ctx.settings` and `ctx.db`.
- `run(ctx)` must NOT:
  - Start tasks outside of `ctx.task_registry` or `ctx.background`.
  - Close or replace `ctx.db` (only the database step sets it; the trailing shutdown hook closes it).
  - Call `run_startup` or `run_shutdown` (no recursion).

### Conformance test

```python
from src.startup.protocol import Step

def test_step_conforms(step_instance):
    assert isinstance(step_instance, Step)
    assert step_instance.name
    assert isinstance(step_instance.fatal, bool)
```

---

## P2 — StepOutcome dataclass

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True, slots=True)
class StepOutcome:
    name: str
    status: Literal["ok", "failed", "skipped"]
    duration_ms: float
    error: str | None = None
```

### Field constraints

| Field | Constraint |
|---|---|
| `name` | Non-empty; matches originating step's `name` |
| `status` | One of `"ok"`, `"failed"`, `"skipped"` |
| `duration_ms` | `>= 0.0` |
| `error` | Non-`None` iff `status == "failed"` |

### Serialisation

`StepOutcome` is a frozen dataclass with `slots=True`. It can be serialised to dict via `dataclasses.asdict(outcome)` for JSON responses (future healthcheck endpoint).

---

## P3 — Step class exemplar

A minimal step implementation:

```python
from src.startup.protocol import StartupContext

class DatabaseStep:
    name = "database"
    fatal = True

    async def run(self, ctx: StartupContext) -> None:
        from src.services.database import init_database
        db = await init_database()
        ctx.db = db
        ctx.app.state.db = db
```

A step with `skip_if`:

```python
class OtelStep:
    name = "otel"
    fatal = False

    def skip_if(self, ctx: StartupContext) -> bool:
        return not ctx.settings.otel_enabled

    async def run(self, ctx: StartupContext) -> None:
        from src.services.otel import init_otel
        tracer, meter = init_otel(ctx.settings)
        ctx.app.state.otel_tracer = tracer
        ctx.app.state.otel_meter = meter
```

---

## P4 — Forbidden patterns

The following patterns MUST NOT appear in any step module:

- **Direct `sys.exit()` or `os._exit()`**: Steps signal failure by raising exceptions; the runner decides whether to abort.
- **Bare `except:` or `except Exception:`**: Steps should let exceptions propagate to the runner. Internal retry logic is acceptable if it re-raises on final failure.
- **Importing from other step modules**: Steps are independent; shared logic belongs in `src/services/` or `src/startup/protocol.py`.
- **Storing a reference to `ctx` beyond the `run()` call**: The context is transient; long-lived objects should be stored on `app.state`.
