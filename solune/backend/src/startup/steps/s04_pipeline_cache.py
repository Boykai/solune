"""Step 4: Load persisted pipeline state into L1 cache."""

from src.startup.protocol import StartupContext


class PipelineCacheStep:
    name = "pipeline_state_cache"
    fatal = True

    async def run(self, ctx: StartupContext) -> None:
        from src.services.pipeline_state_store import init_pipeline_state_store

        if ctx.db is None:
            raise RuntimeError("database step must run before pipeline_state_cache")
        await init_pipeline_state_store(ctx.db)
