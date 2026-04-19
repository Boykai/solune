"""Step 3: Initialize SQLite database and run migrations."""

from src.startup.protocol import StartupContext


class DatabaseStep:
    name = "database"
    fatal = True

    async def run(self, ctx: StartupContext) -> None:
        from src.services.database import init_database, seed_global_settings

        db = await init_database()
        await seed_global_settings(db)
        ctx.db = db
        ctx.app.state.db = db
