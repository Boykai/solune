"""Step 1: Configure structured logging."""

from src.startup.protocol import StartupContext


class LoggingStep:
    name = "logging"
    fatal = True

    async def run(self, ctx: StartupContext) -> None:
        from src.config import setup_logging

        setup_logging(ctx.settings.debug, structured=not ctx.settings.debug)
