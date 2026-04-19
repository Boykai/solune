"""Startup step: agent MCP sync (fire-and-forget via TaskRegistry)."""
# pyright: basic
# reason: Extracted from main.py; imports private helpers.

from __future__ import annotations

import dataclasses

from src.logging_utils import get_logger
from src.startup.protocol import StartupContext

logger = get_logger(__name__)


@dataclasses.dataclass(frozen=True)
class AgentMcpSyncStep:
    """Run agent MCP sync on startup via TaskRegistry (fire-and-forget)."""

    name: str = "agent_mcp_sync"
    fatal: bool = False

    async def run(self, ctx: StartupContext) -> None:
        from src.main import _startup_agent_mcp_sync

        assert ctx.db is not None, "DatabaseStep must run before AgentMcpSyncStep"
        db = ctx.db

        async def _run_background() -> None:
            try:
                await _startup_agent_mcp_sync(db)
            except Exception as exc:
                logger.warning("Startup agent MCP sync failed (non-fatal): %s", exc)

        ctx.task_registry.create_task(_run_background(), name="startup-mcp-sync")
