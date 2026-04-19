"""Startup step: initialise SQLite database."""

from __future__ import annotations

import dataclasses

from src.logging_utils import get_logger
from src.startup.protocol import StartupContext

logger = get_logger(__name__)


@dataclasses.dataclass(frozen=True)
class DatabaseStep:
    """Initialise the SQLite database, run migrations, and seed global settings."""

    name: str = "database"
    fatal: bool = True

    async def run(self, ctx: StartupContext) -> None:
        from src.services.database import init_database, seed_global_settings

        db = await init_database()
        await seed_global_settings(db)
        ctx.db = db
        ctx.app.state.db = db
