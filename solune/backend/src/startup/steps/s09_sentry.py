"""Step 9: Initialize Sentry SDK (skipped if no DSN configured)."""

from src.logging_utils import get_logger
from src.startup.protocol import StartupContext

logger = get_logger(__name__)


class SentryStep:
    name = "sentry"
    fatal = False

    def skip_if(self, ctx: StartupContext) -> bool:
        return not ctx.settings.sentry_dsn

    async def run(self, ctx: StartupContext) -> None:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=ctx.settings.sentry_dsn,
            traces_sample_rate=0,
            integrations=[FastApiIntegration()],
        )
        logger.info("Sentry SDK initialised")
