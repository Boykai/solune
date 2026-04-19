"""Startup step: multi-project discovery and registration."""
# pyright: basic
# reason: Extracted from main.py; imports private helpers.

from __future__ import annotations

import dataclasses

from src.logging_utils import get_logger
from src.startup.protocol import StartupContext

logger = get_logger(__name__)


@dataclasses.dataclass(frozen=True)
class MultiProjectDiscoveryStep:
    """Discover projects with active pipelines and register for monitoring."""

    name: str = "multi_project_discovery"
    fatal: bool = False

    async def run(self, ctx: StartupContext) -> None:
        from src.main import _discover_and_register_active_projects

        await _discover_and_register_active_projects()
