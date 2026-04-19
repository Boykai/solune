"""Step 2: Install global asyncio exception handler."""

from __future__ import annotations

import asyncio
from types import TracebackType
from typing import Any

from src.logging_utils import get_logger
from src.startup.protocol import StartupContext

logger = get_logger(__name__)


class AsyncioExcHandlerStep:
    name = "asyncio_exception_handler"
    fatal = False

    async def run(self, ctx: StartupContext) -> None:
        loop = asyncio.get_running_loop()

        def _handler(_loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
            exc: BaseException | None = context.get("exception")
            msg: str = context.get("message", "Unhandled async exception")
            exc_info: tuple[type[BaseException], BaseException, TracebackType | None] | None = (
                (type(exc), exc, exc.__traceback__) if exc is not None else None
            )
            logger.error(
                "Async exception: %s — %s",
                msg,
                exc,
                exc_info=exc_info,
            )

        loop.set_exception_handler(_handler)
