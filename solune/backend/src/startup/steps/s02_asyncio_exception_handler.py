"""Startup step: install global asyncio exception handler."""
# pyright: basic
# reason: Extracted from main.py; asyncio callback typing is imprecise.

from __future__ import annotations

import asyncio
import dataclasses

from src.logging_utils import get_logger
from src.startup.protocol import StartupContext

logger = get_logger(__name__)


@dataclasses.dataclass(frozen=True)
class AsyncioExceptionHandlerStep:
    """Install a global asyncio exception handler for unhandled async errors."""

    name: str = "asyncio_exception_handler"
    fatal: bool = False

    async def run(self, ctx: StartupContext) -> None:
        loop = asyncio.get_running_loop()

        def _handler(_loop: asyncio.AbstractEventLoop, context: dict) -> None:  # type: ignore[type-arg] — reason: asyncio callback dict has untyped values
            exc = context.get("exception")
            msg = context.get("message", "Unhandled async exception")
            logger.error(
                "Async exception: %s — %s",
                msg,
                exc,
                exc_info=(
                    (type(exc), exc, getattr(exc, "__traceback__", None))
                    if exc is not None
                    else None
                ),
            )

        loop.set_exception_handler(_handler)
