"""Agent function tools for the Microsoft Agent Framework.

Each tool is a standalone async function decorated with ``@tool``.
Runtime context (project_id, github_token, session_id) is injected via
``AgentSession.state`` — never exposed to the LLM schema.

Tool registration is designed to accommodate future MCP tool integration (v0.4.0).
"""

from __future__ import annotations

import json
from typing import Any, TypedDict

import aiosqlite
from agent_framework import FunctionInvocationContext, tool

from src.config import get_settings
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


# ── Constants ────────────────────────────────────────────────────────────

DIFFICULTY_PRESET_MAP: dict[str, str] = {
    "XS": "github-copilot",
    "S": "easy",
    "M": "medium",
    "L": "hard",
    "XL": "expert",
}


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

    # Enforce length limits (aligned with docstring contract)
    if len(title) > 100:
        title = title[:97] + "..."
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

    # Retrieve available tasks from session state
    available_tasks = context.session.state.get("available_tasks", []) if context.session else []

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
    state = context.session.state if context.session else {}
    project_name = state.get("project_name", "Unknown Project")
    project_id = state.get("project_id", "")

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
    available_statuses = (
        context.session.state.get("available_statuses", []) if context.session else []
    )
    statuses_str = ", ".join(available_statuses) if available_statuses else "No statuses configured"

    return ToolResult(
        content=f"**Available Status Columns**: {statuses_str}",
        action_type=None,
        action_data=None,
    )


@tool
async def assess_difficulty(
    context: FunctionInvocationContext,
    difficulty: str,
    reasoning: str,
) -> ToolResult:
    """Assess the complexity of a project idea and record the difficulty rating.

    Use this when the user describes a project they want to build. Rate the
    complexity before selecting a pipeline preset or creating the project.

    Args:
        context: Framework-injected invocation context.
        difficulty: Complexity rating — one of XS, S, M, L, XL.
        reasoning: Brief explanation of why this difficulty level was chosen.
    """
    logger.info("Tool assess_difficulty called: difficulty=%s", difficulty)

    difficulty_upper = difficulty.upper().strip()
    preset_id = DIFFICULTY_PRESET_MAP.get(difficulty_upper, "medium")

    if context.session:
        context.session.state["assessed_difficulty"] = difficulty_upper

    return ToolResult(
        content=(
            f"**Difficulty Assessment**: {difficulty_upper}\n\n"
            f"**Reasoning**: {reasoning}\n\n"
            f"**Recommended Preset**: `{preset_id}`"
        ),
        action_type=None,
        action_data=None,
    )


@tool
async def select_pipeline_preset(
    context: FunctionInvocationContext,
    difficulty: str,
    project_name: str,
) -> ToolResult:
    """Select the appropriate pipeline preset based on difficulty assessment.

    Use this after assessing difficulty to configure the pipeline that will
    be used for project execution.

    Args:
        context: Framework-injected invocation context.
        difficulty: Complexity rating — one of XS, S, M, L, XL.
        project_name: Name of the project being configured.
    """
    from src.services.pipelines.service import _PRESET_DEFINITIONS

    logger.info(
        "Tool select_pipeline_preset called: difficulty=%s, project=%s",
        difficulty,
        project_name[:80],
    )

    difficulty_upper = difficulty.upper().strip()
    preset_id = DIFFICULTY_PRESET_MAP.get(difficulty_upper, "medium")

    # Look up preset details from definitions
    preset = next((p for p in _PRESET_DEFINITIONS if p["preset_id"] == preset_id), None)

    if preset is None:
        # Fallback to medium if somehow the preset isn't found
        preset_id = "medium"
        preset = next((p for p in _PRESET_DEFINITIONS if p["preset_id"] == preset_id), None)

    if context.session:
        context.session.state["selected_preset_id"] = preset_id

    if preset:
        stages = [stage["name"] for stage in preset.get("stages", [])]
        agents: list[str] = []
        for stage in preset.get("stages", []):
            for agent in stage.get("agents", []):
                display = agent.get("agent_display_name", agent.get("agent_slug", ""))
                if display and display not in agents:
                    agents.append(display)

        stages_str = " → ".join(stages) if stages else "No stages"
        agents_str = ", ".join(agents) if agents else "No agents"

        return ToolResult(
            content=(
                f"**Pipeline Preset Selected**: {preset['name']} (`{preset_id}`)\n\n"
                f"**Project**: {project_name}\n"
                f"**Stages**: {stages_str}\n"
                f"**Agents**: {agents_str}\n\n"
                f"{preset.get('description', '')}"
            ),
            action_type=None,
            action_data=None,
        )

    return ToolResult(
        content=f"Selected pipeline preset `{preset_id}` for **{project_name}**.",
        action_type=None,
        action_data=None,
    )


@tool
async def create_project_issue(
    context: FunctionInvocationContext,
    title: str,
    body: str,
    labels: list[str] | None = None,
) -> ToolResult:
    """Create a GitHub issue for a new project.

    Use this after assessing difficulty and selecting a pipeline preset.

    Args:
        context: Framework-injected invocation context.
        title: Issue title for the new project.
        body: Issue body with project description and requirements.
        labels: Optional explicit labels. If omitted, labels are auto-generated.
    """
    logger.info("Tool create_project_issue called: title=%s", title[:80])

    settings = get_settings()
    state = context.session.state if context.session else {}
    github_token = state.get("github_token")
    project_name = state.get("project_name", "Unknown Project")
    preset_id = state.get("selected_preset_id", "medium")

    if not github_token:
        return ToolResult(
            content="Cannot create issue: GitHub authentication is required.",
            action_type=None,
            action_data=None,
        )

    try:
        from src.services.github_projects.service import GitHubProjectsService

        service = GitHubProjectsService()
        owner = settings.default_repo_owner
        repo = settings.default_repo_name

        if not owner or not repo:
            return ToolResult(
                content="Cannot create issue: default repository is not configured.",
                action_type=None,
                action_data=None,
            )

        if labels is not None:
            from src.services.label_classifier import validate_labels

            issue_labels = validate_labels(labels)
        else:
            from src.services.label_classifier import classify_labels

            issue_labels = await classify_labels(
                title=title,
                description=body,
                github_token=github_token,
            )

        issue = await service.create_issue(
            access_token=github_token,
            owner=owner,
            repo=repo,
            title=title,
            body=body,
            labels=issue_labels,
        )

        return ToolResult(
            content=(
                f"**Issue Created**: #{issue['number']}\n\n"
                f"**URL**: {issue['html_url']}\n"
                f"**Pipeline Preset**: `{preset_id}`\n"
                f"**Project**: {project_name}"
            ),
            action_type="issue_create",
            action_data={
                "issue_number": issue["number"],
                "issue_url": issue["html_url"],
                "preset_id": preset_id,
                "project_name": project_name,
            },
        )
    except Exception as e:
        logger.error("Failed to create project issue: %s", e, exc_info=True)
        return ToolResult(
            content=(
                "Failed to create issue due to an internal error. "
                "Please try again later or create the issue manually."
            ),
            action_type=None,
            action_data=None,
        )


@tool
async def launch_pipeline(
    context: FunctionInvocationContext,
    pipeline_id: str = "",
) -> ToolResult:
    """Launch a pipeline for the current project.

    Use this after creating a project issue to start the configured
    pipeline execution.

    Args:
        context: Framework-injected invocation context.
        pipeline_id: Optional pipeline configuration ID override.
    """
    state = context.session.state if context.session else {}
    preset_id = state.get("selected_preset_id", "medium")
    project_id = state.get("project_id", "")
    effective_pipeline_id = pipeline_id or state.get("pipeline_id", "")

    logger.info(
        "Tool launch_pipeline called: preset=%s, project_id=%s, pipeline_id=%s",
        preset_id,
        project_id[:20] if project_id else "",
        effective_pipeline_id[:20] if effective_pipeline_id else "",
    )

    from src.services.pipelines.service import _PRESET_DEFINITIONS

    preset = next((p for p in _PRESET_DEFINITIONS if p["preset_id"] == preset_id), None)
    stages: list[str] = []
    if preset:
        stages = [stage["name"] for stage in preset.get("stages", [])]

    return ToolResult(
        content=(
            f"**Pipeline Launched**\n\n"
            f"**Preset**: `{preset_id}`\n"
            f"**Stages**: {' → '.join(stages) if stages else 'Default'}\n"
            f"**Project ID**: {project_id or 'Not set'}\n\n"
            f"The pipeline configuration has been prepared. "
            f"The orchestration layer will handle execution."
        ),
        action_type="pipeline_launch",
        action_data={
            "pipeline_id": effective_pipeline_id,
            "preset": preset_id,
            "stages": stages,
        },
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
        assess_difficulty,
        select_pipeline_preset,
        create_project_issue,
        launch_pipeline,
        list_app_templates,
        get_app_template,
        import_github_repo,
        build_app,
        iterate_on_app,
        generate_app_questions,
    ]


# ── Plan-mode tools ─────────────────────────────────────────────────────


@tool
async def save_plan(
    context: FunctionInvocationContext,
    title: str,
    summary: str,
    steps: list[dict[str, Any]],
) -> ToolResult:
    """Save or update the current implementation plan.

    Call this when you have drafted a complete plan or incorporated user
    feedback into an existing plan.  Each step becomes a future GitHub issue.

    Args:
        context: Framework-injected invocation context.
        title: Short, action-oriented plan title (max 256 characters).
        summary: Overview of what the plan accomplishes (1-3 paragraphs).
        steps: Ordered list of step dicts, each with keys:
            - title (str): Step title (max 256 chars).
            - description (str): Detailed step description.
            - dependencies (list[str], optional): step_ids this step depends on.
    """
    from uuid import uuid4

    from src.models.plan import Plan, PlanStatus, PlanStep
    from src.services import chat_store

    logger.info("Tool save_plan called: title=%s, steps=%d", title[:80], len(steps))

    state = context.session.state if context.session else {}
    session_id = state.get("session_id", "")
    project_id = state.get("project_id", "")
    project_name = state.get("project_name", "Unknown Project")
    repo_owner = state.get("repo_owner", "")
    repo_name = state.get("repo_name", "")
    db = state.get("db")

    if not session_id or not db:
        return ToolResult(
            content="Cannot save plan: missing session context.",
            action_type=None,
            action_data=None,
        )

    if not steps:
        return ToolResult(
            content="Cannot save plan: at least one step is required.",
            action_type=None,
            action_data=None,
        )

    # Reuse existing plan_id when refining in-place
    active_plan_id = state.get("active_plan_id") or str(uuid4())

    # Reject updates for non-draft plans to prevent status regression
    existing_plan = None
    if state.get("active_plan_id"):
        existing_plan = await chat_store.get_plan(db, active_plan_id)
        if existing_plan and existing_plan.get("status") not in (None, "draft"):
            return ToolResult(
                content="Cannot update plan: only draft plans can be modified.",
                action_type=None,
                action_data=None,
            )

    plan_steps = []
    for i, s in enumerate(steps):
        # Validate and normalize step title (auto-generated if missing; titles
        # are user-facing labels that benefit from a sensible default)
        raw_title = s.get("title")
        if isinstance(raw_title, str) and raw_title.strip():
            title_value = raw_title
        else:
            title_value = f"Step {i + 1}"

        # Validate and normalize step description (required, non-empty)
        raw_description = s.get("description")
        if not isinstance(raw_description, str) or not raw_description.strip():
            return ToolResult(
                content=f"Cannot save plan: step {i + 1} must include a non-empty description.",
                action_type=None,
                action_data=None,
            )

        # Preserve step_id when provided (e.g. during refinement)
        provided_id = s.get("step_id")
        step_id = (
            provided_id if isinstance(provided_id, str) and provided_id.strip() else str(uuid4())
        )

        # Coerce dependencies to a list of strings (agent may provide invalid types)
        raw_deps = s.get("dependencies", [])
        deps = [str(d) for d in raw_deps] if isinstance(raw_deps, list) else []

        plan_steps.append(
            PlanStep(
                step_id=step_id,
                plan_id=active_plan_id,
                position=i,
                title=title_value[:256],
                description=raw_description[:65536],
                dependencies=deps,
            )
        )

    # Preserve created_at from existing plan when refining
    existing_created_at = existing_plan.get("created_at") if existing_plan else None

    try:
        plan = Plan(
            plan_id=active_plan_id,
            session_id=session_id,
            title=title[:256],
            summary=summary[:65536],
            status=PlanStatus.DRAFT,
            project_id=project_id,
            project_name=project_name,
            repo_owner=repo_owner,
            repo_name=repo_name,
            steps=plan_steps,
            created_at=existing_created_at,
        )
    except (ValueError, TypeError) as exc:
        logger.warning("Plan model validation failed: %s", exc)
        return ToolResult(
            content=f"Cannot save plan: invalid data — {exc}",
            action_type=None,
            action_data=None,
        )

    try:
        await chat_store.save_plan(db, plan)
    except Exception as e:
        logger.error("Failed to save plan: %s", e, exc_info=True)
        return ToolResult(
            content="Failed to save plan due to an internal error. Please try again.",
            action_type=None,
            action_data=None,
        )

    # Store active plan id in session state for refinement
    if context.session:
        context.session.state["active_plan_id"] = active_plan_id
        context.session.state["is_plan_mode"] = True

    step_summaries = [
        {
            "step_id": s.step_id,
            "position": s.position,
            "title": s.title,
            "description": s.description,
            "dependencies": s.dependencies,
        }
        for s in plan_steps
    ]

    return ToolResult(
        content=(
            f"Plan saved: **{plan.title}** with {len(plan_steps)} steps.\n\n"
            f"{plan.summary[:300]}{'…' if len(plan.summary) > 300 else ''}"
        ),
        action_type="plan_create",
        action_data={
            "plan_id": plan.plan_id,
            "title": plan.title,
            "summary": plan.summary,
            "status": plan.status.value,
            "project_id": plan.project_id,
            "project_name": plan.project_name,
            "repo_owner": plan.repo_owner,
            "repo_name": plan.repo_name,
            "steps": step_summaries,
        },
    )


def register_plan_tools() -> list:
    """Return the restricted read-only toolset for plan mode plus ``save_plan``.

    Returns:
        List of ``@tool``-decorated functions suitable for plan-mode agents.
    """
    return [
        get_project_context,
        get_pipeline_list,
        save_plan,
    ]


def register_plan_step_tools() -> list:
    """Return step CRUD tools for agent-driven plan mutations.

    These tools allow the agent to add, edit, and delete steps programmatically
    using the same validation logic as the API endpoints.
    """
    return [
        add_step,
        edit_step,
        delete_step,
    ]


# ── Plan Step CRUD tools (v2) ────────────────────────────────────────────


@tool
async def add_step(
    context: FunctionInvocationContext,
    plan_id: str,
    title: str,
    description: str,
    dependencies: str = "[]",
) -> ToolResult:
    """Add a new step to an existing plan.

    Args:
        context: Agent function invocation context.
        plan_id: The plan to add a step to.
        title: Step title (max 256 chars).
        description: Step description with acceptance criteria.
        dependencies: JSON array of step_id strings this step depends on.
    """
    from src.services import chat_store

    state = context.session.state if context.session else {}
    db: aiosqlite.Connection | None = state.get("db")
    if db is None:
        return ToolResult(content="Error: database connection not available.")

    try:
        deps = json.loads(dependencies) if isinstance(dependencies, str) else dependencies
    except (json.JSONDecodeError, TypeError):
        deps = []

    try:
        step = await chat_store.add_plan_step(
            db,
            plan_id,
            title=title,
            description=description,
            dependencies=deps,
        )
    except ValueError as e:
        return ToolResult(content=f"Error adding step: {e}")

    if step is None:
        return ToolResult(content=f"Error: plan {plan_id!r} not found.")

    return ToolResult(
        content=f"Added step '{title}' at position {step['position']}.",
        action_type="step_add",
        action_data=step,
    )


@tool
async def edit_step(
    context: FunctionInvocationContext,
    plan_id: str,
    step_id: str,
    title: str = "",
    description: str = "",
    dependencies: str = "",
) -> ToolResult:
    """Edit an existing step in a plan.

    Args:
        context: Agent function invocation context.
        plan_id: The plan containing the step.
        step_id: The step to edit.
        title: New title (empty = no change).
        description: New description (empty = no change).
        dependencies: JSON array of step_id strings (empty = no change).
    """
    from src.services import chat_store

    state = context.session.state if context.session else {}
    db: aiosqlite.Connection | None = state.get("db")
    if db is None:
        return ToolResult(content="Error: database connection not available.")

    new_title = title or None
    new_desc = description or None
    new_deps = None
    if dependencies:
        try:
            new_deps = json.loads(dependencies) if isinstance(dependencies, str) else dependencies
        except (json.JSONDecodeError, TypeError):
            pass

    try:
        step = await chat_store.update_plan_step(
            db,
            plan_id,
            step_id,
            title=new_title,
            description=new_desc,
            dependencies=new_deps,
        )
    except ValueError as e:
        return ToolResult(content=f"Error updating step: {e}")

    if step is None:
        return ToolResult(content=f"Error: step {step_id!r} not found in plan {plan_id!r}.")

    return ToolResult(
        content=f"Updated step '{step['title']}'.",
        action_type="step_edit",
        action_data=step,
    )


@tool
async def delete_step(
    context: FunctionInvocationContext,
    plan_id: str,
    step_id: str,
) -> ToolResult:
    """Delete a step from a plan.

    Args:
        context: Agent function invocation context.
        plan_id: The plan containing the step.
        step_id: The step to delete.
    """
    from src.services import chat_store

    state = context.session.state if context.session else {}
    db: aiosqlite.Connection | None = state.get("db")
    if db is None:
        return ToolResult(content="Error: database connection not available.")

    try:
        deleted = await chat_store.delete_plan_step(db, plan_id, step_id)
    except ValueError as e:
        return ToolResult(content=f"Error deleting step: {e}")

    if not deleted:
        return ToolResult(content=f"Error: step {step_id!r} not found in plan {plan_id!r}.")

    return ToolResult(
        content=f"Deleted step {step_id!r}.",
        action_type="step_delete",
        action_data={"step_id": step_id, "plan_id": plan_id},
    )


# ── App Builder tools ───────────────────────────────────────────────────


@tool
async def list_app_templates(
    context: FunctionInvocationContext,
    category: str = "",
) -> ToolResult:
    """List available app templates for building applications.

    Args:
        context: Agent function invocation context.
        category: Optional category filter (saas, api, cli, dashboard). Empty = all.

    Returns:
        ToolResult with template summaries.
    """
    from src.models.app_template import AppCategory
    from src.services.app_templates.registry import list_templates as _list

    cat: AppCategory | None = None
    if category:
        try:
            cat = AppCategory(category)
        except ValueError:
            return ToolResult(
                content=f"Invalid category '{category}'. Valid categories: {', '.join(c.value for c in AppCategory)}",
                action_type=None,
                action_data=None,
            )
    templates = _list(category=cat)
    summaries = [t.to_summary_dict() for t in templates]

    if not summaries:
        return ToolResult(
            content="No templates found matching the criteria.",
            action_type=None,
            action_data=None,
        )

    lines = [f"**{len(summaries)} template(s) available:**\n"]
    lines.extend(
        f"- **{s['name']}** (`{s['id']}`) — {s['category']}, "
        f"difficulty {s['difficulty']}, scaffold: {s['scaffold_type']}"
        for s in summaries
    )

    return ToolResult(
        content="\n".join(lines),
        action_type=None,
        action_data={"templates": summaries},
    )


@tool
async def get_app_template(
    context: FunctionInvocationContext,
    template_id: str,
) -> ToolResult:
    """Get detailed information about a specific app template.

    Args:
        context: Agent function invocation context.
        template_id: Template identifier (e.g. 'saas-react-fastapi').

    Returns:
        ToolResult with full template details.
    """
    from src.services.app_templates.registry import get_template as _get

    template = _get(template_id)
    if template is None:
        return ToolResult(
            content=f"Template '{template_id}' not found.",
            action_type=None,
            action_data=None,
        )

    detail = template.to_detail_dict()
    tech_stack = detail.get("tech_stack")
    files = detail.get("files")
    tech_stack_text = (
        ", ".join(str(item) for item in tech_stack) if isinstance(tech_stack, list) else ""
    )
    file_count = len(files) if isinstance(files, list) else 0
    return ToolResult(
        content=(
            f"**{detail['name']}**\n\n"
            f"Category: {detail['category']}, Difficulty: {detail['difficulty']}\n"
            f"Tech stack: {tech_stack_text}\n"
            f"Scaffold type: {detail['scaffold_type']}\n"
            f"IaC target: {detail['iac_target']}\n"
            f"Files: {file_count} template file(s)"
        ),
        action_type=None,
        action_data={"template": detail},
    )


@tool
async def import_github_repo(
    context: FunctionInvocationContext,
    url: str,
    create_project: bool = True,
) -> ToolResult:
    """Import an existing GitHub repository into Solune.

    Args:
        context: Agent function invocation context.
        url: GitHub repository URL (https://github.com/owner/repo).
        create_project: Whether to create a GitHub Project V2 board.

    Returns:
        ToolResult with import status.
    """
    import re

    pattern = re.compile(r"^https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+/?$")
    if not pattern.match(url):
        return ToolResult(
            content=f"Invalid GitHub URL: {url}. Expected format: https://github.com/owner/repo",
            action_type=None,
            action_data=None,
        )

    return ToolResult(
        content=(
            f"Repository import requested for {url}.\n"
            f"Create project board: {create_project}\n"
            "Use the /api/apps/import endpoint to complete the import."
        ),
        action_type="app_import",
        action_data={"url": url, "create_project": create_project},
    )


@tool
async def build_app(
    context: FunctionInvocationContext,
    app_name: str,
    template_id: str,
    description: str = "",
    difficulty_override: str = "",
) -> ToolResult:
    """Build a new application from a template.

    Chains: validate template → create app → configure pipeline → launch.

    Args:
        context: Agent function invocation context.
        app_name: Name for the new application (kebab-case).
        template_id: Template to scaffold from.
        description: App description.
        difficulty_override: Optional difficulty override (S, M, L, XL).

    Returns:
        ToolResult with build status.
    """
    from src.services.app_templates.registry import get_template as _get
    from src.services.pipelines.pipeline_config import configure_pipeline_preset

    template = _get(template_id)
    if template is None:
        return ToolResult(
            content=f"Template '{template_id}' not found. Use list_app_templates() to see available templates.",
            action_type=None,
            action_data=None,
        )

    override = difficulty_override or None
    preset_id, include_architect = configure_pipeline_preset(template, override)

    return ToolResult(
        content=(
            f"🏗️ **Building app '{app_name}'**\n\n"
            f"Template: {template.name}\n"
            f"Pipeline preset: {preset_id}\n"
            f"Include architect agent: {include_architect}\n"
            f"Description: {description or '(none)'}\n\n"
            "App creation initiated. Use the Apps page to monitor progress."
        ),
        action_type="app_build",
        action_data={
            "app_name": app_name,
            "template_id": template_id,
            "description": description,
            "preset_id": preset_id,
            "include_architect": include_architect,
        },
    )


@tool
async def iterate_on_app(
    context: FunctionInvocationContext,
    app_name: str,
    change_description: str,
) -> ToolResult:
    """Request a change to an existing application.

    Creates an issue and launches a pipeline to implement the change.

    Args:
        context: Agent function invocation context.
        app_name: Name of the existing application.
        change_description: Natural language description of the desired change.

    Returns:
        ToolResult with iteration status.
    """
    return ToolResult(
        content=(
            f"📝 **Iteration requested for '{app_name}'**\n\n"
            f"Change: {change_description}\n\n"
            "An issue will be created in the app's project board and a pipeline "
            "will be launched to implement the change."
        ),
        action_type="app_iterate",
        action_data={
            "app_name": app_name,
            "change_description": change_description,
        },
    )


@tool
async def generate_app_questions(
    context: FunctionInvocationContext,
    description: str,
) -> ToolResult:
    """Generate 2-3 clarifying questions for app creation.

    Args:
        context: Agent function invocation context.
        description: User's initial app description.

    Returns:
        ToolResult with targeted questions.
    """
    from src.services.app_templates.registry import list_templates as _list

    templates = _list()
    categories = sorted({t.category.value for t in templates})

    questions = [
        f"What type of application do you want? Available categories: {', '.join(categories)}.",
        "What is the primary tech stack or deployment target you prefer?",
    ]
    if len(description.split()) < 10:
        questions.append("Can you provide more details about the key features or functionality?")

    return ToolResult(
        content="Before building your app, I have a few questions:\n\n"
        + "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions)),
        action_type=None,
        action_data={"questions": questions, "user_description": description},
    )


# ── MCP tool loading ────────────────────────────────────────────────────


async def load_mcp_tools(project_id: str, db: aiosqlite.Connection) -> dict[str, Any]:
    """Load active MCP tool configurations for a project.

    Queries the ``mcp_tool_configs`` table for active configs matching
    *project_id* and converts each row into a dict compatible with
    ``GitHubCopilotOptions.mcp_servers``.

    Returns an empty dict (and logs accordingly) when no MCP tools are
    configured or on error.

    Args:
        project_id: The project ID to load MCP tools for.
        db: An open aiosqlite connection.

    Returns:
        Mapping of server name → config dict.
    """
    if not project_id:
        logger.info("load_mcp_tools: no project_id provided, skipping MCP tool loading")
        return {}

    try:
        async with db.execute(
            "SELECT name, endpoint_url, config_content "
            "FROM mcp_tool_configs "
            "WHERE project_id = ? AND is_active = 1",
            (project_id,),
        ) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            logger.info(
                "load_mcp_tools: no active MCP tools configured for project %s",
                project_id[:20],
            )
            return {}

        mcp_servers: dict[str, Any] = {}
        for row in rows:
            name, endpoint_url, config_content = row
            try:
                config = json.loads(config_content) if config_content else {}
            except (json.JSONDecodeError, TypeError) as exc:
                logger.warning(
                    "load_mcp_tools: invalid JSON config for MCP server %r: %s",
                    name,
                    exc,
                )
                config = {}

            mcp_servers[name] = {
                "endpoint_url": endpoint_url,
                "config": config,
            }

        logger.info(
            "load_mcp_tools: loaded %d MCP tool(s) for project %s",
            len(mcp_servers),
            project_id[:20],
        )
        return mcp_servers

    except Exception as e:
        logger.warning(
            "load_mcp_tools: failed to load MCP tools for project %s: %s",
            project_id[:20],
            e,
        )
        return {}
