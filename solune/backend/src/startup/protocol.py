"""Step Protocol, StepOutcome, and StartupContext for the startup package."""
# pyright: basic
# reason: Uses Any for settings/db/task_registry to avoid circular imports.

from __future__ import annotations

import dataclasses
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any, Protocol, runtime_checkable

from fastapi import FastAPI

_BackgroundCoro = Coroutine[object, object, None]
_ShutdownHook = Callable[[], Awaitable[None]]


@runtime_checkable
class Step(Protocol):
    """Contract for a startup/shutdown step.

    Each step is a small object with:
    - ``name``: stable identifier (used in logs/metrics).
    - ``fatal``: whether failure aborts startup.
    - ``run(ctx)``: the body; may mutate ``ctx.app.state``, register tasks, etc.
    - ``skip_if(ctx)`` (optional): predicate to conditionally skip the step.
    """

    @property
    def name(self) -> str: ...

    @property
    def fatal(self) -> bool: ...

    async def run(self, ctx: StartupContext) -> None: ...


@dataclasses.dataclass
class StepOutcome:
    """Recorded outcome of a single startup step execution."""

    name: str
    status: str  # "ok", "skipped", "error"
    duration_ms: float
    error: str | None = None


@dataclasses.dataclass
class StartupContext:
    """Mutable context passed to every startup step.

    Holds references to shared resources that steps may read or mutate.
    """

    app: FastAPI
    settings: Any  # src.config.Settings (avoid circular import)
    db: Any | None = None  # aiosqlite.Connection | None
    task_registry: Any = None  # src.services.task_registry.TaskRegistry
    background: list[_BackgroundCoro] = dataclasses.field(default_factory=list)
    shutdown_hooks: list[_ShutdownHook] = dataclasses.field(default_factory=list)

    def add_background(self, coro: _BackgroundCoro) -> None:
        """Queue a coroutine to be started in the TaskGroup after all steps."""
        self.background.append(coro)

    def add_shutdown_hook(self, hook: _ShutdownHook) -> None:
        """Register a shutdown hook (LIFO execution order)."""
        self.shutdown_hooks.append(hook)
