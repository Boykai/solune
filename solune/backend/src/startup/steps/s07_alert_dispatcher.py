"""Startup step: initialise alert dispatcher."""

from __future__ import annotations

import dataclasses

from src.startup.protocol import StartupContext


@dataclasses.dataclass(frozen=True)
class AlertDispatcherStep:
    """Create and register the AlertDispatcher for observability alerts."""

    name: str = "alert_dispatcher"
    fatal: bool = False

    async def run(self, ctx: StartupContext) -> None:
        from src.services.alert_dispatcher import AlertDispatcher, set_dispatcher

        dispatcher = AlertDispatcher(
            webhook_url=ctx.settings.alert_webhook_url,
            cooldown_minutes=ctx.settings.alert_cooldown_minutes,
        )
        ctx.app.state.alert_dispatcher = dispatcher
        set_dispatcher(dispatcher)
