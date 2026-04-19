"""Step 10: Start Signal WebSocket listener."""

from src.startup.protocol import StartupContext


class SignalWsStep:
    name = "signal_ws_listener"
    fatal = False

    async def run(self, ctx: StartupContext) -> None:
        from src.services.signal_bridge import start_signal_ws_listener, stop_signal_ws_listener

        await start_signal_ws_listener()
        ctx.shutdown_hooks.append(stop_signal_ws_listener)
