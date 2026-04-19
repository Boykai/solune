"""Shared fixtures for startup unit tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI

from src.startup.protocol import StartupContext


def make_test_ctx(**overrides: Any) -> StartupContext:
    """Create a minimal StartupContext for testing."""
    app = MagicMock(spec=FastAPI)
    app.state = MagicMock()
    settings = MagicMock()
    settings.debug = False
    settings.otel_enabled = False
    settings.sentry_dsn = ""
    settings.alert_webhook_url = ""
    settings.alert_cooldown_minutes = 60
    task_registry = MagicMock()
    task_registry.create_task = MagicMock()
    task_registry.drain = AsyncMock()
    ctx = StartupContext(
        app=app,
        settings=settings,
        task_registry=task_registry,
    )
    for key, value in overrides.items():
        setattr(ctx, key, value)
    return ctx


class FakeStep:
    """Configurable fake step for runner tests."""

    def __init__(
        self,
        name: str = "fake",
        fatal: bool = False,
        run_side_effect: Exception | None = None,
        skip: bool = False,
        skip_raises: Exception | None = None,
    ) -> None:
        self._name = name
        self._fatal = fatal
        self._run_side_effect = run_side_effect
        self._skip = skip
        self._skip_raises = skip_raises
        self.run_called = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def fatal(self) -> bool:
        return self._fatal

    async def run(self, ctx: StartupContext) -> None:
        self.run_called = True
        if self._run_side_effect is not None:
            raise self._run_side_effect

    def skip_if(self, ctx: StartupContext) -> bool:
        if self._skip_raises is not None:
            raise self._skip_raises
        return self._skip


@pytest.fixture
def ctx() -> StartupContext:
    return make_test_ctx()
