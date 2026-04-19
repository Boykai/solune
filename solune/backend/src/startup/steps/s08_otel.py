"""Step 8: Initialize OpenTelemetry (skipped if not enabled)."""

from src.startup.protocol import StartupContext


class OtelStep:
    name = "otel"
    fatal = False

    def skip_if(self, ctx: StartupContext) -> bool:
        if ctx.settings.otel_enabled:
            return False
        ctx.app.state.otel_tracer = None
        ctx.app.state.otel_meter = None
        return True

    async def run(self, ctx: StartupContext) -> None:
        from src.services.otel_setup import init_otel

        tracer, meter = init_otel(ctx.settings.otel_service_name, ctx.settings.otel_endpoint)
        ctx.app.state.otel_tracer = tracer
        ctx.app.state.otel_meter = meter
