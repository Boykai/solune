"""Step 5: Initialize done-items DB cache."""

from src.startup.protocol import StartupContext


class DoneItemsCacheStep:
    name = "done_items_cache"
    fatal = True

    async def run(self, ctx: StartupContext) -> None:
        from src.services.done_items_store import init_done_items_store

        if ctx.db is None:
            raise RuntimeError("database step must run before done_items_cache")
        await init_done_items_store(ctx.db)
