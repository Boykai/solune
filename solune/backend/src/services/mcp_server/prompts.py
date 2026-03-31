"""MCP prompt templates for guided workflows.

Provides structured prompts that help external agents discover and follow
common Solune workflows (FR-036):
- ``create-project``: Guided project creation flow
- ``pipeline-status``: Check all running pipelines
- ``daily-standup``: Summarize recent activity across projects
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from src.logging_utils import get_logger

logger = get_logger(__name__)


def register_prompts(mcp: FastMCP) -> None:
    """Register all MCP prompt templates on the server instance."""

    @mcp.prompt("create-project")
    async def create_project_prompt(project_name: str | None = None) -> str:
        """Guided project creation flow.

        Walks you through creating a new GitHub Project, setting up pipelines,
        and configuring agents.

        Args:
            project_name: Optional project name to pre-fill.
        """
        name_hint = f' named "{project_name}"' if project_name else ""
        return (
            f"I'd like to create a new project{name_hint} in Solune. "
            "Please help me with the following steps:\n\n"
            "1. First, call `list_projects` to see my existing projects.\n"
            "2. Then, help me set up a new GitHub Project with appropriate columns.\n"
            "3. Configure a development pipeline (easy/medium/hard/expert).\n"
            "4. Set up any custom agents needed for the project.\n\n"
            "Let's start by listing my current projects."
        )

    @mcp.prompt("pipeline-status")
    async def pipeline_status_prompt(project_id: str | None = None) -> str:
        """Check all running pipelines across projects.

        Args:
            project_id: Optional project ID to scope the status check.
        """
        if project_id:
            return (
                f"Check the status of all pipelines in project `{project_id}`.\n\n"
                "1. Call `get_pipeline_states` to see active pipelines.\n"
                "2. For each running pipeline, summarize:\n"
                "   - Current stage and progress\n"
                "   - Agent assignments and their status\n"
                "   - Any stalled or failed stages\n"
                "3. Suggest actions for any issues found."
            )
        return (
            "Check the status of all running pipelines across all my projects.\n\n"
            "1. First, call `list_projects` to discover all projects.\n"
            "2. For each project, call `get_pipeline_states`.\n"
            "3. Summarize the overall pipeline health:\n"
            "   - Total active pipelines\n"
            "   - Any stalled or failed stages\n"
            "   - Recommended actions"
        )

    @mcp.prompt("daily-standup")
    async def daily_standup_prompt(days: int = 1) -> str:
        """Summarize recent activity across projects for a daily standup.

        Args:
            days: Number of days to look back (default: 1).
        """
        return (
            f"Generate a daily standup summary for the last {days} day(s).\n\n"
            "1. Call `list_projects` to discover all projects.\n"
            "2. For each project:\n"
            "   a. Call `get_activity` to fetch recent events.\n"
            "   b. Call `get_pipeline_states` for pipeline status.\n"
            "   c. Call `get_board` for current board state.\n"
            "3. Produce a standup report with:\n"
            "   - **Completed**: Items moved to Done\n"
            "   - **In Progress**: Active work items\n"
            "   - **Blocked**: Stalled pipelines or issues\n"
            "   - **Next Steps**: Recommended priorities"
        )
