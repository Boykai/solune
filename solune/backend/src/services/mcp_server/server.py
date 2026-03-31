"""FastMCP server creation and tool registration.

Creates the ``FastMCP`` instance with all tools, resources, and prompts
registered.  The server is mounted into the FastAPI application by
``main.py`` when the ``mcp_server_enabled`` feature flag is True.

Architecture note: All MCP tools, REST API endpoints, and internal
``@tool`` functions delegate to the same ``GitHubProjectsService``,
``WorkflowOrchestrator``, ``ChatAgentService``, etc.  This ensures a
single source of truth — no business logic duplication (FR-038, FR-039).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from src.config import get_settings
from src.logging_utils import get_logger
from src.services.mcp_server.auth import GitHubTokenVerifier

if TYPE_CHECKING:
    from starlette.applications import Starlette

logger = get_logger(__name__)

# Module-level singleton so main.py can import it for lifespan management
_mcp_server: FastMCP | None = None
_token_verifier: GitHubTokenVerifier | None = None

_INSTRUCTIONS = """\
Solune is an agent-driven development platform that turns feature descriptions
into working code. This MCP server exposes Solune's project management,
pipeline orchestration, and agent tools via the Model Context Protocol.

Available capabilities:
- **Projects & Board**: List projects, view board state, get project tasks
- **Task & Issue Creation**: Create tasks and issues on GitHub Projects
- **Pipelines**: List, launch, monitor, and retry development pipelines
- **Activity & Status**: View activity feeds, update item status
- **Agents**: List and create custom GitHub Copilot agents
- **Apps**: Manage applications (list, status, create)
- **Chores**: List and trigger recurring maintenance chores
- **Chat**: Natural language interaction with Solune's AI agent
- **Metadata**: Repository context (labels, branches, milestones)
- **Cleanup**: Preview stale branches/PRs for cleanup

Authentication: Provide a GitHub Personal Access Token (PAT) as a Bearer
token in the Authorization header. The token is verified against the
GitHub API and used for all GitHub operations.
"""


def create_mcp_server() -> FastMCP:
    """Create and configure the FastMCP server instance.

    Registers all tool functions, resource templates, and prompt templates.
    The server uses Streamable HTTP transport with stateless mode for
    production deployment.
    """
    global _mcp_server, _token_verifier

    settings = get_settings()
    _token_verifier = GitHubTokenVerifier()

    _mcp_server = FastMCP(
        settings.mcp_server_name,
        stateless_http=True,
        json_response=True,
        instructions=_INSTRUCTIONS,
    )

    _register_tools(_mcp_server)
    _register_resources(_mcp_server)
    _register_prompts(_mcp_server)

    logger.info(
        "MCP server '%s' created with tools, resources, and prompts",
        settings.mcp_server_name,
    )
    return _mcp_server


def get_mcp_app() -> Starlette:
    """Return the Starlette ASGI app for the MCP server.

    Must be called after ``create_mcp_server()``.
    """
    if _mcp_server is None:
        raise RuntimeError("MCP server not created. Call create_mcp_server() first.")
    return _mcp_server.streamable_http_app()


def get_token_verifier() -> GitHubTokenVerifier | None:
    """Return the token verifier instance (for auth context resolution)."""
    return _token_verifier


# ------------------------------------------------------------------
# Tool registration
# ------------------------------------------------------------------


def _register_tools(mcp: FastMCP) -> None:
    """Register all MCP tool functions on the server."""
    from src.services.mcp_server.tools.activity import get_activity, update_item_status
    from src.services.mcp_server.tools.agents import create_agent, list_agents
    from src.services.mcp_server.tools.apps import create_app, get_app_status, list_apps
    from src.services.mcp_server.tools.chat import (
        cleanup_preflight,
        get_metadata,
        send_chat_message,
    )
    from src.services.mcp_server.tools.chores import list_chores, trigger_chore
    from src.services.mcp_server.tools.pipelines import (
        get_pipeline_states,
        launch_pipeline,
        list_pipelines,
        retry_pipeline,
    )
    from src.services.mcp_server.tools.projects import (
        get_board,
        get_project,
        get_project_tasks,
        list_projects,
    )
    from src.services.mcp_server.tools.tasks import create_issue, create_task

    # Tier 1 — Projects & Board (US1)
    mcp.tool()(list_projects)
    mcp.tool()(get_project)
    mcp.tool()(get_board)
    mcp.tool()(get_project_tasks)

    # Tier 1 — Task & Issue Creation (US2)
    mcp.tool()(create_task)
    mcp.tool()(create_issue)

    # Tier 1 — Pipelines (US2)
    mcp.tool()(list_pipelines)
    mcp.tool()(launch_pipeline)
    mcp.tool()(get_pipeline_states)
    mcp.tool()(retry_pipeline)

    # Tier 1 — Activity & Status (US2)
    mcp.tool()(get_activity)
    mcp.tool()(update_item_status)

    # Tier 2 — Agents (US4)
    mcp.tool()(list_agents)
    mcp.tool()(create_agent)

    # Tier 2 — Apps (US4)
    mcp.tool()(list_apps)
    mcp.tool()(get_app_status)
    mcp.tool()(create_app)

    # Tier 2 — Chores (US4)
    mcp.tool()(list_chores)
    mcp.tool()(trigger_chore)

    # Tier 2 — Chat, Metadata, Cleanup (US4)
    mcp.tool()(send_chat_message)
    mcp.tool()(get_metadata)
    mcp.tool()(cleanup_preflight)

    logger.info("Registered 22 MCP tools")


def _register_resources(mcp: FastMCP) -> None:
    """Register MCP resource templates."""
    from src.services.mcp_server.resources import register_resources

    register_resources(mcp)
    logger.info("Registered MCP resource templates")


def _register_prompts(mcp: FastMCP) -> None:
    """Register MCP prompt templates."""
    from src.services.mcp_server.prompts import register_prompts

    register_prompts(mcp)
    logger.info("Registered MCP prompt templates")
