"""Step Protocol, StepOutcome dataclass, StartupContext dataclass, and StartupError."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, Protocol, runtime_checkable

import aiosqlite
from fastapi import FastAPI

if TYPE_CHECKING:
    from src.config import Settings
    from src.services.task_registry import TaskRegistry


@runtime_checkable
class Step(Protocol):
    """Protocol that every startup step must satisfy."""

    @property
    def name(self) -> str: ...

    @property
    def fatal(self) -> bool: ...

    async def run(self, ctx: StartupContext) -> None: ...


@dataclass(frozen=True, slots=True)
class StepOutcome:
    """Immutable record of a single step execution."""

    name: str
    status: Literal["ok", "failed", "skipped"]
    duration_ms: float
    error: str | None = None


@dataclass
class StartupContext:
    """Mutable context passed to every startup step."""

    app: FastAPI
    settings: Settings
    task_registry: TaskRegistry
    db: aiosqlite.Connection | None = None
    background: list[Coroutine[Any, Any, None]] = field(default_factory=list)
    shutdown_hooks: list[Callable[[], Awaitable[None]]] = field(default_factory=list)


class StartupError(RuntimeError):
    """Raised by run_startup when a fatal step fails."""

    def __init__(self, step_name: str) -> None:
        self.step_name = step_name
        super().__init__(f"Fatal startup step failed: {step_name}")
