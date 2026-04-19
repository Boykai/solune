"""Startup step: configure logging."""

from __future__ import annotations

import dataclasses

from src.startup.protocol import StartupContext


@dataclasses.dataclass(frozen=True)
class LoggingStep:
    """Configure application logging based on settings."""

    name: str = "logging"
    fatal: bool = True

    async def run(self, ctx: StartupContext) -> None:
        from src.config import setup_logging

        setup_logging(ctx.settings.debug, structured=not ctx.settings.debug)
