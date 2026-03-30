"""Agent function tools for the Microsoft Agent Framework.

Each tool is a standalone async function decorated with ``@tool``.
Runtime context (project_id, github_token, session_id) is injected via
``FunctionInvocationContext.kwargs`` — never exposed to the LLM schema.

Tool registration is designed to accommodate future MCP tool integration (v0.4.0).
"""

from __future__ import annotations

from typing import Any, TypedDict

from agent_framework import FunctionInvocationContext, tool

from src.logging_utils import get_logger

logger = get_logger(__name__)


# ── Result types ─────────────────────────────────────────────────────────


class ToolResult(TypedDict, total=False):
    """Structured result returned by all agent tools.

    - ``content``: Human-readable text for the agent's response.
    - ``action_type``: Maps to ``ActionType`` enum (or ``None`` for informational).
    - ``action_data``: Structured payload for confirm/reject flows.
    """

    content: str
    action_type: str | None
    action_data: dict[str, Any] | None


# ── Tool functions ───────────────────────────────────────────────────────


@tool
async def create_task_proposal(
    context: FunctionInvocationContext,
    title: str,
    description: str,
) -> ToolResult:
    """Create a task proposal from a title and description.

    Use this when the user describes a specific work item, bug fix, or
    technical task they want to create.

    Args:
        context: Framework-injected invocation context.
        title: Short, action-oriented task title (max 100 characters).
        description: Detailed description with acceptance criteria.
    """
    logger.info("Tool create_task_proposal called: title=%s", title[:80])

    # Enforce length limits
    if len(title) > 256:
        title = title[:253] + "..."
    if len(description) > 65535:
        description = description[:65532] + "..."

    return ToolResult(
        content=f"I've created a task proposal:\n\n**{title}**\n\n{description[:200]}{'...' if len(description) > 200 else ''}\n\nClick confirm to create this task.",
        action_type="task_create",
        action_data={
            "proposed_title": title,
            "proposed_description": description,
        },
    )


@tool
async def create_issue_recommendation(
    context: FunctionInvocationContext,
    title: str,
    user_story: str,
    ui_ux_description: str,
    functional_requirements: list[str],
    technical_notes: str = "",
) -> ToolResult:
    """Create a structured GitHub issue recommendation from a feature request.

    Use this when the user describes a new feature, enhancement, or product idea
    that should become a GitHub issue with full specification.

    Args:
        context: Framework-injected invocation context.
        title: Clear, concise issue title (max 256 characters).
        user_story: User story in "As a [user], I want [goal] so that [benefit]" format.
        ui_ux_description: Guidance for designers/developers on how the feature should look.
        functional_requirements: List of specific, testable requirements.
        technical_notes: Implementation hints and architecture considerations.
    """
    logger.info("Tool create_issue_recommendation called: title=%s", title[:80])

    if len(title) > 256:
        title = title[:253] + "..."

    requirements_preview = "\n".join(f"- {req}" for req in functional_requirements)
    technical_preview = ""
    if technical_notes:
        technical_preview = f"\n\n**Technical Notes:**\n{technical_notes[:300]}{'...' if len(technical_notes) > 300 else ''}"

    return ToolResult(
        content=(
            f"I've generated a GitHub issue recommendation:\n\n"
            f"**{title}**\n\n"
            f"**User Story:**\n{user_story}\n\n"
            f"**UI/UX Description:**\n{ui_ux_description}\n\n"
            f"**Functional Requirements:**\n{requirements_preview}"
            f"{technical_preview}\n\n"
            f"Click **Confirm** to create this issue in GitHub, or **Reject** to discard."
        ),
        action_type="issue_create",
        action_data={
            "proposed_title": title,
            "user_story": user_story,
            "ui_ux_description": ui_ux_description,
            "functional_requirements": functional_requirements,
            "technical_notes": technical_notes,
        },
    )


@tool
async def update_task_status(
    context: FunctionInvocationContext,
    task_reference: str,
    target_status: str,
) -> ToolResult:
    """Update a task's status in the project board.

    Use this when the user asks to move a task to a different status column
    (e.g., "move X to Done", "mark Y as in progress").

    Args:
        context: Framework-injected invocation context.
        task_reference: The task title, number, or description the user mentioned.
        target_status: The target status column name (e.g., "Done", "In Progress").
    """
    logger.info(
        "Tool update_task_status called: ref=%s, target=%s",
        task_reference[:80],
        target_status,
    )

    # Retrieve available tasks from runtime kwargs
    available_tasks = context.kwargs.get("available_tasks", [])

    target_task = _identify_target_task(task_reference, available_tasks)

    if not target_task:
        return ToolResult(
            content=f"I couldn't find a task matching '{task_reference}'. Please try again with a more specific task name.",
            action_type=None,
            action_data=None,
        )

    return ToolResult(
        content=f"I'll update the status of **{target_task.title}** from **{target_task.status}** to **{target_status}**.\n\nClick confirm to apply this change.",
        action_type="status_update",
        action_data={
            "task_id": target_task.github_item_id,
            "task_title": target_task.title,
            "current_status": target_task.status,
            "target_status": target_status,
        },
    )


@tool
async def analyze_transcript(
    context: FunctionInvocationContext,
    transcript_content: str,
) -> ToolResult:
    """Analyse a meeting transcript and extract actionable requirements.

    Use this when the user provides meeting notes, .vtt/.srt content, or
    conversation logs that should be converted into a GitHub issue.

    Args:
        context: Framework-injected invocation context.
        transcript_content: Raw transcript text content.
    """
    logger.info("Tool analyze_transcript called: content_length=%d", len(transcript_content))

    # Return structured result — the agent will synthesize the analysis
    return ToolResult(
        content=(
            "I've analysed the transcript. Please review the generated issue "
            "recommendation and click **Confirm** to create it in GitHub, "
            "or **Reject** to discard."
        ),
        action_type="issue_create",
        action_data={
            "proposed_title": "Transcript Analysis — Issue Recommendation",
            "transcript_content": transcript_content[:500],
            "source": "transcript",
        },
    )


@tool
async def ask_clarifying_question(
    context: FunctionInvocationContext,
    question: str,
) -> ToolResult:
    """Ask the user a clarifying question before taking action.

    Use this when the user's request is ambiguous or incomplete and you need
    more information to proceed with the correct tool.

    Args:
        context: Framework-injected invocation context.
        question: The clarifying question to ask the user.
    """
    logger.info("Tool ask_clarifying_question called")

    return ToolResult(
        content=question,
        action_type=None,
        action_data=None,
    )


@tool
async def get_project_context(
    context: FunctionInvocationContext,
) -> ToolResult:
    """Get information about the currently selected project.

    Use this when the user asks about project status, available tasks,
    or project configuration.
    """
    project_name = context.kwargs.get("project_name", "Unknown Project")
    project_id = context.kwargs.get("project_id", "")

    return ToolResult(
        content=f"**Current Project**: {project_name} (ID: {project_id})",
        action_type=None,
        action_data=None,
    )


@tool
async def get_pipeline_list(
    context: FunctionInvocationContext,
) -> ToolResult:
    """Get the list of available agent pipelines for the current project.

    Use this when the user asks about available pipelines or workflow
    configurations.
    """
    available_statuses = context.kwargs.get("available_statuses", [])
    statuses_str = ", ".join(available_statuses) if available_statuses else "No statuses configured"

    return ToolResult(
        content=f"**Available Status Columns**: {statuses_str}",
        action_type=None,
        action_data=None,
    )


# ── Helpers ───────────────────────────────────────────────────────────────


def _identify_target_task(task_reference: str, available_tasks: list[Any]) -> Any | None:
    """Find the best matching task for a reference string.

    Standalone extraction of ``AIAgentService.identify_target_task`` so the
    new tool layer does not depend on the deprecated service class.

    Args:
        task_reference: User-provided reference (partial title/description).
        available_tasks: Objects with a ``.title`` attribute.

    Returns:
        Best matching task or ``None``.
    """
    if not task_reference or not available_tasks:
        return None

    reference_lower = task_reference.lower()

    # Exact match
    for task in available_tasks:
        if task.title.lower() == reference_lower:
            return task

    # Partial match
    matches = [
        task
        for task in available_tasks
        if reference_lower in task.title.lower() or task.title.lower() in reference_lower
    ]
    if len(matches) == 1:
        return matches[0]

    # Fuzzy match — highest word overlap wins
    ref_words = set(reference_lower.split())
    best_match = None
    best_score = 0
    for task in available_tasks:
        title_words = set(task.title.lower().split())
        overlap = len(ref_words & title_words)
        if overlap > best_score:
            best_score = overlap
            best_match = task

    return best_match if best_score > 0 else None


# ── Tool registration ────────────────────────────────────────────────────


def register_tools() -> list:
    """Return the list of all agent tools for Agent registration.

    This list is designed to be extended with MCP-sourced tools in v0.4.0.

    Returns:
        List of ``@tool``-decorated functions.
    """
    return [
        create_task_proposal,
        create_issue_recommendation,
        update_task_status,
        analyze_transcript,
        ask_clarifying_question,
        get_project_context,
        get_pipeline_list,
    ]
