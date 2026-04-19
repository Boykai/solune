"""Startup step: initialise Done-items DB cache."""

from __future__ import annotations

import dataclasses

from src.startup.protocol import StartupContext


@dataclasses.dataclass(frozen=True)
class DoneItemsCacheStep:
    """Initialise Done-items DB cache for cold-start optimisation."""

    name: str = "done_items_cache"
    fatal: bool = True

    async def run(self, ctx: StartupContext) -> None:
        from src.services.done_items_store import init_done_items_store

        assert ctx.db is not None, "DatabaseStep must run before DoneItemsCacheStep"
        await init_done_items_store(ctx.db)
