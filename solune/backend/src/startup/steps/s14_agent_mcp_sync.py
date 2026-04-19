"""Step 14: Agent MCP sync — fire-and-forget via TaskRegistry."""

from src.logging_utils import get_logger
from src.startup.protocol import StartupContext

logger = get_logger(__name__)


class AgentMcpSyncStep:
    name = "agent_mcp_sync"
    fatal = False

    async def run(self, ctx: StartupContext) -> None:
        """Fire-and-forget agent MCP sync via TaskRegistry."""
        assert ctx.db is not None, "database step must run before agent_mcp_sync"
        db = ctx.db

        async def _run_background() -> None:
            from src.services.agents.agent_mcp_sync import sync_agent_mcps
            from src.services.session_store import get_session
            from src.utils import resolve_repository

            try:
                cursor = await db.execute(
                    """
                    SELECT session_id FROM user_sessions
                    WHERE selected_project_id IS NOT NULL
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                )
                row = await cursor.fetchone()
                if row is None:
                    logger.debug("No user session found — skipping startup agent MCP sync")
                    return

                session = await get_session(db, row["session_id"])
                if not session or not session.selected_project_id:
                    return

                try:
                    owner, repo = await resolve_repository(
                        session.access_token, session.selected_project_id
                    )
                except Exception as e:
                    logger.debug("Could not resolve repo for startup MCP sync: %s", e)
                    return

                await sync_agent_mcps(
                    owner=owner,
                    repo=repo,
                    project_id=session.selected_project_id,
                    access_token=session.access_token,
                    trigger="startup",
                    db=db,
                )
                logger.info(
                    "Startup agent MCP sync completed for %s/%s",
                    owner,
                    repo,
                )
            except Exception as e:
                logger.warning("Startup agent MCP sync failed (non-fatal): %s", e)

        ctx.task_registry.create_task(_run_background(), name="startup-mcp-sync")
