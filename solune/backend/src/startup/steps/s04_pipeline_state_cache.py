"""Startup step: load persisted pipeline state into L1 cache."""

from __future__ import annotations

import dataclasses

from src.startup.protocol import StartupContext


@dataclasses.dataclass(frozen=True)
class PipelineStateCacheStep:
    """Load persisted pipeline state from SQLite into in-memory L1 caches."""

    name: str = "pipeline_state_cache"
    fatal: bool = True

    async def run(self, ctx: StartupContext) -> None:
        from src.services.pipeline_state_store import init_pipeline_state_store

        assert ctx.db is not None, "DatabaseStep must run before PipelineStateCacheStep"
        await init_pipeline_state_store(ctx.db)
