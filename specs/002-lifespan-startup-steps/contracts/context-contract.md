# StartupContext Contract

**Feature**: 002-lifespan-startup-steps
**Owners**: `src/startup/protocol.py`
**Consumers**: Every step module in `src/startup/steps/`, `src/startup/runner.py`, `main.py` (lifespan)

This contract specifies the StartupContext dataclass — its fields, initial values, and mutation rules.

---

## C1 — StartupContext definition

```python
from dataclasses import dataclass, field
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any

import aiosqlite
from fastapi import FastAPI

from src.config import Settings
from src.services.task_registry import TaskRegistry

@dataclass
class StartupContext:
    app: FastAPI
    settings: Settings
    task_registry: TaskRegistry
    db: aiosqlite.Connection | None = None
    background: list[Coroutine[Any, Any, None]] = field(default_factory=list)
    shutdown_hooks: list[Callable[[], Awaitable[None]]] = field(default_factory=list)
```

---

## C2 — Field access rules

| Field | Readable by | Writable by | Notes |
|---|---|---|---|
| `app` | All steps | All steps (via `app.state`) | Steps set attributes on `app.state.*`; do not replace `app` itself |
| `settings` | All steps | Nobody | Read-only reference to the application settings singleton |
| `task_registry` | All steps | Nobody (but steps call `.create_task()`) | Reference to the module-level `task_registry` singleton |
| `db` | Steps 4–15 | Step 3 (`s03_database`) only | `None` until step 3 runs; steps must tolerate `None` if ordered before step 3 |
| `background` | Runner (after all steps) | Steps 15 (`s15_background_loops`) | Steps append coroutine objects; runner consumes the list after all steps |
| `shutdown_hooks` | Runner (during shutdown) | Any step | Steps append `async def` callables; runner iterates in LIFO order |

---

## C3 — Creation exemplar (in `lifespan()`)

```python
from src.startup.protocol import StartupContext
from src.config import get_settings
from src.services.task_registry import task_registry

async def lifespan(app: FastAPI):
    settings = get_settings()
    ctx = StartupContext(
        app=app,
        settings=settings,
        task_registry=task_registry,
    )
    outcomes = await run_startup(STARTUP_STEPS, ctx)
    app.state.startup_report = outcomes

    async with asyncio.TaskGroup() as tg:
        for coro in ctx.background:
            tg.create_task(coro)
        yield

    await run_shutdown(ctx)
```

---

## C4 — Testing exemplar (mock context)

```python
from unittest.mock import AsyncMock, MagicMock
from src.startup.protocol import StartupContext

def make_test_ctx(**overrides):
    """Create a minimal StartupContext for unit testing."""
    app = MagicMock(spec=["state"])
    app.state = MagicMock()
    settings = MagicMock()
    task_registry = MagicMock()
    ctx = StartupContext(
        app=overrides.get("app", app),
        settings=overrides.get("settings", settings),
        task_registry=overrides.get("task_registry", task_registry),
        db=overrides.get("db", None),
    )
    return ctx
```

This fixture is shared across all step tests in `tests/unit/startup/conftest.py`.

---

## C5 — Lifecycle invariants

1. **Single creation**: `StartupContext` is instantiated exactly once per application boot, in `lifespan()`.
2. **No persistence**: The context object is not stored on `app.state` or in any module-level variable. Only `app.state.startup_report` (a `list[StepOutcome]`) survives.
3. **No concurrent access**: Steps execute sequentially (the runner is `await`-based, not parallel). No locking is needed on context fields.
4. **Background deferred**: Coroutines in `ctx.background` are not awaited by the runner. They are passed back to `lifespan()` to be started in the TaskGroup.
5. **Shutdown hooks consumed once**: `run_shutdown` iterates `ctx.shutdown_hooks` exactly once. After `run_shutdown` returns, the hooks list is not reused.

---

## C6 — Forbidden states

| State | Why forbidden | Detection |
|---|---|---|
| `ctx.db` set before step 3 | No database connection exists yet | Type check (`db` is `None`) |
| `ctx.background` consumed before all steps | Premature task start breaks the TaskGroup contract | Runner returns the list; only `lifespan()` feeds it to TG |
| `ctx.shutdown_hooks` modified after `run_shutdown` starts | Mutation during iteration is undefined behaviour | `run_shutdown` operates on a snapshot (`list(reversed(...))`) |
| `ctx.app` replaced (not just `app.state` mutated) | All steps share the same app reference | Dataclass is mutable but convention prohibits replacement |
