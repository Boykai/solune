"""Step 6: Register singleton services on app.state."""

from src.startup.protocol import StartupContext


class SingletonServicesStep:
    name = "singleton_services"
    fatal = True

    async def run(self, ctx: StartupContext) -> None:
        from src.services.github_projects import github_projects_service
        from src.services.websocket import connection_manager

        ctx.app.state.github_service = github_projects_service
        ctx.app.state.connection_manager = connection_manager
