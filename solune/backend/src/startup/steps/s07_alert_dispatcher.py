"""Step 7: Initialize AlertDispatcher."""

from src.startup.protocol import StartupContext


class AlertDispatcherStep:
    name = "alert_dispatcher"
    fatal = False

    async def run(self, ctx: StartupContext) -> None:
        from src.services.alert_dispatcher import AlertDispatcher, set_dispatcher

        dispatcher = AlertDispatcher(
            webhook_url=ctx.settings.alert_webhook_url,
            cooldown_minutes=ctx.settings.alert_cooldown_minutes,
        )
        ctx.app.state.alert_dispatcher = dispatcher
        set_dispatcher(dispatcher)
