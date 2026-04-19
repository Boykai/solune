"""Startup step: register singleton services on app.state."""

from __future__ import annotations

import dataclasses

from src.startup.protocol import StartupContext


@dataclasses.dataclass(frozen=True)
class SingletonServicesStep:
    """Register singleton services on ``app.state`` for DI (see dependencies.py)."""

    name: str = "singleton_services"
    fatal: bool = True

    async def run(self, ctx: StartupContext) -> None:
        from src.services.github_projects import github_projects_service
        from src.services.websocket import connection_manager

        ctx.app.state.github_service = github_projects_service
        ctx.app.state.connection_manager = connection_manager
