"""Startup step: initialise OpenTelemetry."""

from __future__ import annotations

import dataclasses

from src.logging_utils import get_logger
from src.startup.protocol import StartupContext

logger = get_logger(__name__)


@dataclasses.dataclass(frozen=True)
class OtelStep:
    """Initialise OpenTelemetry tracer and meter when enabled."""

    name: str = "otel"
    fatal: bool = False

    def skip_if(self, ctx: StartupContext) -> bool:
        """Skip when OTel is not enabled in settings."""
        return not ctx.settings.otel_enabled

    async def run(self, ctx: StartupContext) -> None:
        from src.services.otel_setup import init_otel

        tracer, meter = init_otel(ctx.settings.otel_service_name, ctx.settings.otel_endpoint)
        ctx.app.state.otel_tracer = tracer
        ctx.app.state.otel_meter = meter
