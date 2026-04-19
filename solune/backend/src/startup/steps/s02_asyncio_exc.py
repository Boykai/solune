"""Step 2: Install global asyncio exception handler."""

import asyncio

from src.logging_utils import get_logger
from src.startup.protocol import StartupContext

logger = get_logger(__name__)


class AsyncioExcHandlerStep:
    name = "asyncio_exception_handler"
    fatal = False

    async def run(self, ctx: StartupContext) -> None:
        loop = asyncio.get_running_loop()

        def _handler(_loop: asyncio.AbstractEventLoop, context: dict) -> None:
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
