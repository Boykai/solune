"""Startup step: initialise Sentry SDK."""

from __future__ import annotations

import dataclasses

from src.logging_utils import get_logger
from src.startup.protocol import StartupContext

logger = get_logger(__name__)


@dataclasses.dataclass(frozen=True)
class SentryStep:
    """Initialise Sentry SDK when a DSN is configured."""

    name: str = "sentry"
    fatal: bool = False

    def skip_if(self, ctx: StartupContext) -> bool:
        """Skip when no Sentry DSN is configured."""
        return not ctx.settings.sentry_dsn

    async def run(self, ctx: StartupContext) -> None:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=ctx.settings.sentry_dsn,
            traces_sample_rate=0,  # avoid double-tracing when OTel is also active
            integrations=[FastApiIntegration()],
        )
        logger.info("Sentry SDK initialised")
