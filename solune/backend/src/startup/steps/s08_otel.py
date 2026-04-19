"""Step 8: Initialize OpenTelemetry (skipped if not enabled)."""

from src.startup.protocol import StartupContext


class OtelStep:
    name = "otel"
    fatal = False

    def skip_if(self, ctx: StartupContext) -> bool:
        return not ctx.settings.otel_enabled

    async def run(self, ctx: StartupContext) -> None:
        from src.services.otel_setup import init_otel

        tracer, meter = init_otel(ctx.settings.otel_service_name, ctx.settings.otel_endpoint)
        ctx.app.state.otel_tracer = tracer
        ctx.app.state.otel_meter = meter
