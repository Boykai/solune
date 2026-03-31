"""MCP resource templates for real-time subscriptions.

Exposes pipeline states, board state, and activity as subscribable MCP
resources (FR-031 - FR-033).  Clients can subscribe to these URIs and
receive ``resource-updated`` notifications when data changes.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from src.logging_utils import get_logger

logger = get_logger(__name__)


def register_resources(mcp: FastMCP) -> None:
    """Register all MCP resource templates on the server instance."""

    @mcp.resource("solune://projects/{project_id}/pipelines")
    async def pipelines_resource(project_id: str) -> str:
        """Current pipeline states for a project.

        Returns JSON with all active pipeline states and their stage progress.
        """
        import json

        from src.services.pipeline_state_store import get_all_pipeline_states

        all_states = get_all_pipeline_states()
        project_states = {
            str(k): v.model_dump() if hasattr(v, "model_dump") else v
            for k, v in all_states.items()
            if getattr(v, "project_id", None) == project_id
        }
        return json.dumps({"project_id": project_id, "pipeline_states": project_states})

    @mcp.resource("solune://projects/{project_id}/board")
    async def board_resource(project_id: str) -> str:
        """Current board state for a project.

        Returns JSON with columns and items from the project board.
        Note: This resource requires a valid GitHub token in the lifespan context.
        """
        import json

        return json.dumps(
            {
                "project_id": project_id,
                "note": "Board data requires authenticated access. Use the get_board tool instead.",
            }
        )

    @mcp.resource("solune://projects/{project_id}/activity")
    async def activity_resource(project_id: str) -> str:
        """Recent activity feed for a project.

        Returns JSON with the latest activity events.
        """
        import json

        from src.services.activity_service import query_events
        from src.services.database import get_db

        db = get_db()
        result = await query_events(db, project_id=project_id, limit=20)
        return json.dumps({"project_id": project_id, **result}, default=str)
