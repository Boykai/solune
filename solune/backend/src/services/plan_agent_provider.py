"""Plan agent provider — Copilot SDK custom agent profiles and session factory.

Defines agent profiles for each speckit pipeline stage and provides
``create_plan_session()`` which creates SDK sessions with custom agent
configurations, tool whitelists, and session hooks for automatic plan
versioning.

All SDK calls are wrapped behind this module to absorb breaking changes
in the ``github-copilot-sdk`` public preview.
"""

from __future__ import annotations

import json
from typing import Any

from src.logging_utils import get_logger
from src.prompts.plan_instructions import PLAN_SYSTEM_INSTRUCTIONS

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Agent profiles
# ---------------------------------------------------------------------------

PLAN_AGENT_PROFILE: dict[str, Any] = {
    "name": "solune-plan",
    "description": "Plan mode agent — researches project context and produces structured implementation plans.",
    "system_prompt": PLAN_SYSTEM_INSTRUCTIONS,
    "tool_whitelist": ["get_project_context", "get_pipeline_list", "save_plan"],
    "permission": "read_only",
}

SPECKIT_AGENT_PROFILES: dict[str, dict[str, Any]] = {
    "solune-plan": PLAN_AGENT_PROFILE,
    "solune-specify": {
        "name": "solune-specify",
        "description": "Specification agent — creates feature specifications from natural language descriptions.",
        "tool_whitelist": ["get_project_context", "save_spec"],
        "permission": "read_only",
    },
    "solune-tasks": {
        "name": "solune-tasks",
        "description": "Task generation agent — creates actionable task breakdowns from specifications.",
        "tool_whitelist": ["get_project_context", "save_tasks"],
        "permission": "read_only",
    },
    "solune-analyze": {
        "name": "solune-analyze",
        "description": "Analysis agent — performs cross-artifact consistency and quality analysis.",
        "tool_whitelist": ["get_project_context"],
        "permission": "read_only",
    },
    "solune-implement": {
        "name": "solune-implement",
        "description": "Implementation agent — executes tasks and writes production code.",
        "tool_whitelist": None,  # Full tools
        "permission": "full",
    },
}


# ---------------------------------------------------------------------------
# Session hooks for plan versioning
# ---------------------------------------------------------------------------


async def on_pre_tool_use_hook(
    tool_name: str,
    tool_args: dict[str, Any],
    context: dict[str, Any],
) -> None:
    """Pre-tool-use hook: snapshot plan version before save_plan overwrites.

    When ``toolName == "save_plan"``, calls ``snapshot_plan_version()`` to
    preserve the current plan state before the tool modifies it.
    """
    if tool_name != "save_plan":
        return

    db = context.get("db")
    plan_id = context.get("active_plan_id")
    if db is None or plan_id is None:
        return

    try:
        from src.services.chat_store import snapshot_plan_version

        version_id = await snapshot_plan_version(db, plan_id)
        if version_id:
            logger.info("Pre-save snapshot created: version_id=%s plan_id=%s", version_id, plan_id)
    except Exception:
        logger.exception("Failed to snapshot plan version before save_plan")


async def on_post_tool_use_hook(
    tool_name: str,
    tool_result: Any,
    context: dict[str, Any],
) -> dict[str, Any] | None:
    """Post-tool-use hook: emit plan_diff delta after save_plan completes.

    Returns a dict describing the plan_diff event for SSE emission, or
    None if no event should be emitted.
    """
    if tool_name != "save_plan":
        return None

    plan_id = context.get("active_plan_id")
    if plan_id is None:
        return None

    return {
        "event": "plan_diff",
        "data": json.dumps({"plan_id": plan_id, "action": "saved"}),
    }


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------


async def create_plan_session(
    *,
    github_token: str,
    instructions: str | None = None,
    tools: list | None = None,
    reasoning_effort: str = "",
    agent_profile: str = "solune-plan",
) -> Any:
    """Create a Copilot SDK session configured for plan mode.

    Wraps ``CopilotClient.create_session()`` with the appropriate custom
    agent profile, tool whitelist, and session hooks.

    Args:
        github_token: User's GitHub OAuth token.
        instructions: Override system instructions (defaults to profile's prompt).
        tools: Tool functions to register.
        reasoning_effort: SDK reasoning effort level.
        agent_profile: Profile name from SPECKIT_AGENT_PROFILES.

    Returns:
        Configured agent session.
    """
    from copilot.types import (  # type: ignore[reportMissingImports]
        PermissionHandler,
        SessionConfig,
    )

    from src.services.completion_providers import get_copilot_client_pool

    profile = SPECKIT_AGENT_PROFILES.get(agent_profile, PLAN_AGENT_PROFILE)
    system_prompt = instructions or profile.get("system_prompt", PLAN_SYSTEM_INSTRUCTIONS)

    client = await get_copilot_client_pool().get_or_create(github_token)

    config: SessionConfig = {
        "on_permission_request": PermissionHandler.approve_all,
    }
    if system_prompt:
        config["system_message"] = {"mode": "replace", "content": system_prompt}
    if reasoning_effort:
        config["reasoning_effort"] = reasoning_effort  # type: ignore[typeddict-unknown-key]

    session = await client.create_session(config)
    logger.info(
        "Created plan session (profile: %s, tools: %d)",
        profile.get("name", agent_profile),
        len(tools or []),
    )
    return session
