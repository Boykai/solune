"""Startup step: start Signal WebSocket listener."""

from __future__ import annotations

import dataclasses

from src.startup.protocol import StartupContext


@dataclasses.dataclass(frozen=True)
class SignalWsListenerStep:
    """Start the Signal WebSocket listener for inbound messages.

    Registers a shutdown hook to stop the listener on teardown.
    """

    name: str = "signal_ws_listener"
    fatal: bool = False

    async def run(self, ctx: StartupContext) -> None:
        from src.services.signal_bridge import start_signal_ws_listener, stop_signal_ws_listener

        await start_signal_ws_listener()
        ctx.add_shutdown_hook(stop_signal_ws_listener)
