"""Chat agent service — wraps Microsoft Agent Framework for Solune chat.

Manages the Agent lifecycle, AgentSession ↔ Solune session_id mapping,
and converts AgentResponse messages into ChatMessage instances.

Key design decisions:
- SQLite remains the canonical store for conversation history.
- AgentSession holds a lightweight summary for multi-turn context.
- Sessions are evicted after configurable inactivity (TTL).
- The Agent is created per invocation; provider-specific caching may be
  introduced as an optimization if needed.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from agent_framework import AgentResponse, AgentSession

from src.config import get_settings
from src.logging_utils import get_logger
from src.models.chat import ActionType, ChatMessage, SenderType
from src.prompts.agent_instructions import build_system_instructions
from src.prompts.plan_instructions import build_plan_instructions
from src.services.agent_provider import create_agent
from src.services.agent_tools import (
    extract_embedded_action_payload,
    load_mcp_tools,
    register_plan_tools,
    register_tools,
)
from src.services.plan_agent_provider import on_post_tool_use_hook, on_pre_tool_use_hook
from src.utils import utcnow

logger = get_logger(__name__)

PLAN_CREATE_DRAFT_MESSAGE = (
    "Plan drafted. Review the Plan Preview and approve it to create GitHub issues."
)


def _extract_text(value: Any) -> str:
    """Extract text content from framework messages/updates or test doubles."""
    text = getattr(value, "text", None)
    if isinstance(text, str):
        cleaned_text, _, _ = extract_embedded_action_payload(text)
        return cleaned_text or ""

    content = getattr(value, "content", None)
    if isinstance(content, str):
        cleaned_content, _, _ = extract_embedded_action_payload(content)
        return cleaned_content or ""
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str):
                parts.append(part_text)
        joined = "".join(parts)
        cleaned_joined, _, _ = extract_embedded_action_payload(joined)
        return cleaned_joined or ""

    return ""


def _extract_action_payload(value: Any) -> tuple[str | None, dict[str, Any] | None]:
    """Extract action payloads from compatible message/update shapes."""
    tool_result = getattr(value, "tool_result", None)
    if isinstance(tool_result, dict) and "action_type" in tool_result:
        return tool_result["action_type"], tool_result.get("action_data")

    additional = getattr(value, "additional_properties", None)
    if isinstance(additional, dict):
        payload = additional.get("tool_result")
        if isinstance(payload, dict) and "action_type" in payload:
            return payload["action_type"], payload.get("action_data")

    annotations = getattr(value, "annotations", None)
    if annotations:
        for annotation in annotations:
            data = getattr(annotation, "data", None)
            if isinstance(data, dict) and "action_type" in data:
                return data["action_type"], data.get("action_data")

    text = getattr(value, "text", None)
    if isinstance(text, str):
        _, embedded_action_type, embedded_action_data = extract_embedded_action_payload(text)
        if embedded_action_type:
            return embedded_action_type, embedded_action_data

    content = getattr(value, "content", None)
    if isinstance(content, str):
        _, embedded_action_type, embedded_action_data = extract_embedded_action_payload(content)
        if embedded_action_type:
            return embedded_action_type, embedded_action_data
    elif isinstance(content, list):
        parts: list[str] = []
        for part in content:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str):
                parts.append(part_text)
        if parts:
            _, embedded_action_type, embedded_action_data = extract_embedded_action_payload(
                "".join(parts)
            )
            if embedded_action_type:
                return embedded_action_type, embedded_action_data

    # Check Message.contents for function_result Content items.
    # The Agent Framework stores tool return values as Content objects
    # of type "function_result" whose ``result`` field is a JSON string.
    contents = getattr(value, "contents", None)
    if contents:
        for item in contents:
            if getattr(item, "type", None) != "function_result":
                continue
            raw = getattr(item, "result", None)
            if raw is None:
                continue
            parsed = raw
            if isinstance(raw, str):
                try:
                    parsed = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    _, embedded_action_type, embedded_action_data = extract_embedded_action_payload(
                        raw
                    )
                    if embedded_action_type:
                        return embedded_action_type, embedded_action_data
                    continue
            if isinstance(parsed, dict) and "action_type" in parsed:
                return parsed["action_type"], parsed.get("action_data")

    return None, None


def _normalize_assistant_content(content: str, action_type: Any) -> str:
    """Replace misleading tool narration for plan drafts with stable UI copy."""
    if action_type in {ActionType.PLAN_CREATE, ActionType.PLAN_CREATE.value, "plan_create"}:
        return PLAN_CREATE_DRAFT_MESSAGE
    return content


def _consume_session_tool_action(
    agent_session: AgentSession,
) -> tuple[str | None, dict[str, Any] | None]:
    """Read and clear the last tool action captured in session state."""
    payload = agent_session.state.pop("_last_tool_action", None)
    if not isinstance(payload, dict):
        return None, None

    action_type = payload.get("action_type")
    action_data = payload.get("action_data")
    if not isinstance(action_type, str):
        return None, None
    if action_data is not None and not isinstance(action_data, dict):
        action_data = None
    return action_type, action_data


def _build_plan_action_data(plan_record: dict[str, Any]) -> dict[str, Any]:
    """Normalize persisted plan records into the plan_create action payload shape."""
    step_summaries = [
        {
            "step_id": step["step_id"],
            "position": step["position"],
            "title": step["title"],
            "description": step["description"],
            "dependencies": step.get("dependencies", []),
        }
        for step in plan_record.get("steps", [])
    ]

    return {
        "plan_id": plan_record["plan_id"],
        "title": plan_record["title"],
        "summary": plan_record["summary"],
        "status": plan_record["status"],
        "project_id": plan_record["project_id"],
        "project_name": plan_record["project_name"],
        "repo_owner": plan_record["repo_owner"],
        "repo_name": plan_record["repo_name"],
        "steps": step_summaries,
    }


async def _recover_saved_plan_action(
    db: Any | None,
    session_id: UUID,
    *,
    updated_after: str,
) -> tuple[str | None, dict[str, Any] | None]:
    """Recover plan_create from the persisted draft when transport metadata is lost."""
    if db is None:
        return None, None

    from src.services import chat_store

    plan_record = await chat_store.get_latest_plan_for_session(
        db,
        str(session_id),
        updated_after=updated_after,
    )
    if not isinstance(plan_record, dict):
        return None, None

    return "plan_create", _build_plan_action_data(plan_record)


# ── Session mapping ──────────────────────────────────────────────────────


class _SessionEntry:
    """Internal wrapper tracking an AgentSession and its last access time."""

    __slots__ = ("agent_session", "last_accessed")

    def __init__(self, agent_session: AgentSession) -> None:
        self.agent_session = agent_session
        self.last_accessed = time.monotonic()

    def touch(self) -> None:
        self.last_accessed = time.monotonic()


class AgentSessionMapping:
    """Maps Solune session IDs to AgentSession instances.

    Features:
    - Create-on-first-message: sessions are lazily created.
    - TTL-based eviction: sessions expire after configurable inactivity.
    - Max concurrent sessions: bounded to prevent memory exhaustion.
    """

    def __init__(
        self,
        ttl_seconds: int = 3600,
        max_sessions: int = 100,
    ) -> None:
        self._sessions: dict[str, _SessionEntry] = {}
        self._ttl_seconds = ttl_seconds
        self._max_sessions = max_sessions
        self._lock = asyncio.Lock()

    async def get_or_create(self, session_id: str) -> AgentSession:
        """Get an existing session or create a new one.

        Triggers eviction of expired sessions before creating new ones.
        """
        async with self._lock:
            self._evict_expired()

            entry = self._sessions.get(session_id)
            if entry is not None:
                entry.touch()
                return entry.agent_session

            # Enforce max sessions — evict oldest if at capacity
            if len(self._sessions) >= self._max_sessions:
                self._evict_oldest()

            agent_session = AgentSession()
            self._sessions[session_id] = _SessionEntry(agent_session)
            logger.debug(
                "Created AgentSession for session_id=%s (total: %d)",
                session_id[:8],
                len(self._sessions),
            )
            return agent_session

    def _evict_expired(self) -> None:
        """Remove sessions that have exceeded the TTL."""
        now = time.monotonic()
        expired = [
            sid
            for sid, entry in self._sessions.items()
            if (now - entry.last_accessed) > self._ttl_seconds
        ]
        for sid in expired:
            del self._sessions[sid]
            logger.debug("Evicted expired AgentSession: %s", sid[:8])

    def _evict_oldest(self) -> None:
        """Evict the least recently accessed session."""
        if not self._sessions:
            return
        oldest_sid = min(self._sessions, key=lambda s: self._sessions[s].last_accessed)
        del self._sessions[oldest_sid]
        logger.debug("Evicted oldest AgentSession: %s", oldest_sid[:8])

    async def invalidate(self, session_id: str) -> None:
        """Remove a session, e.g. after an error leaves it in a bad state."""
        async with self._lock:
            if self._sessions.pop(session_id, None) is not None:
                logger.debug("Invalidated AgentSession: %s", session_id[:8])

    @property
    def session_count(self) -> int:
        """Number of active sessions."""
        return len(self._sessions)


# ── ChatAgentService ─────────────────────────────────────────────────────


class ChatAgentService:
    """High-level service wrapping the Agent Framework for Solune chat.

    Exposes ``run()`` and ``run_stream()`` methods that accept Solune-domain
    inputs and return ``ChatMessage`` instances.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._session_mapping = AgentSessionMapping(
            ttl_seconds=settings.agent_session_ttl_seconds,
            max_sessions=settings.agent_max_concurrent_sessions,
        )
        self._tools = register_tools()
        self._plan_tools = register_plan_tools()
        logger.info("ChatAgentService initialized with %d tools", len(self._tools))

    async def run(
        self,
        *,
        message: str,
        session_id: UUID,
        github_token: str | None = None,
        project_name: str = "Unknown Project",
        project_id: str = "",
        available_tasks: list[Any] | None = None,
        available_statuses: list[str] | None = None,
        pipeline_id: str | None = None,
        file_urls: list[str] | None = None,
        db: Any | None = None,
    ) -> ChatMessage:
        """Run the agent with a user message and return a ChatMessage.

        Args:
            message: The user's chat message content.
            session_id: Solune session UUID.
            github_token: GitHub OAuth token (required for Copilot provider).
            project_name: Name of the selected project for context.
            project_id: Project ID for context injection.
            available_tasks: List of task objects for status-change matching.
            available_statuses: Valid status column names.
            pipeline_id: Optional pipeline configuration ID.
            file_urls: URLs of uploaded files.
            db: Optional aiosqlite connection for MCP tool loading.

        Returns:
            ChatMessage with the agent's response, including action_type and
            action_data when the agent invoked an action tool.
        """
        agent_session = await self._session_mapping.get_or_create(str(session_id))

        # Inject runtime context into session state for tool access
        agent_session.state.update(
            {
                "project_name": project_name,
                "project_id": project_id,
                "available_tasks": available_tasks or [],
                "available_statuses": available_statuses or [],
                "github_token": github_token,
                "session_id": str(session_id),
                "pipeline_id": pipeline_id,
                "file_urls": file_urls or [],
            }
        )

        # Auto-delegate to plan mode if the session is in plan mode
        if agent_session.state.get("is_plan_mode"):
            return await self.run_plan(
                message=message,
                session_id=session_id,
                github_token=github_token,
                project_name=project_name,
                project_id=project_id,
                available_statuses=available_statuses,
                repo_owner=agent_session.state.get("repo_owner", ""),
                repo_name=agent_session.state.get("repo_name", ""),
                db=db,
            )

        instructions = build_system_instructions(
            project_name=project_name,
            available_statuses=available_statuses,
        )

        # Load MCP tools if a database connection and project_id are available
        mcp_servers = None
        if db and project_id:
            mcp_servers = await load_mcp_tools(project_id, db) or None

        agent = await create_agent(
            instructions=instructions,
            tools=self._tools,
            github_token=github_token,
            mcp_servers=mcp_servers,
            tool_runtime_state=agent_session.state,
        )

        sid = str(session_id)
        try:
            response: AgentResponse = await agent.run(
                message,
                session=agent_session,
            )
            result = self._convert_response(response, session_id)
            session_action_type, session_action_data = _consume_session_tool_action(agent_session)
            if result.action_type is None and session_action_type:
                result.action_type = ActionType(session_action_type)
                result.action_data = session_action_data
                result.content = _normalize_assistant_content(result.content, session_action_type)
            return result
        except Exception as e:
            logger.error("Agent run failed: %s", e, exc_info=True)
            # Invalidate the session so the next attempt gets a fresh one
            # instead of resuming a potentially stuck Copilot session.
            await self._session_mapping.invalidate(sid)
            return ChatMessage(
                session_id=session_id,
                sender_type=SenderType.ASSISTANT,
                content=f"I encountered an error processing your request ({type(e).__name__}). Please try again.",
            )

    async def run_stream(
        self,
        *,
        message: str,
        session_id: UUID,
        github_token: str | None = None,
        project_name: str = "Unknown Project",
        project_id: str = "",
        available_tasks: list[Any] | None = None,
        available_statuses: list[str] | None = None,
        db: Any | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Run the agent in streaming mode, yielding SSE-compatible events.

        Event types:
        - ``token``: Partial text content.
        - ``tool_call``: Agent is invoking a tool.
        - ``tool_result``: Tool invocation completed.
        - ``done``: Stream complete with final ChatMessage.
        - ``error``: An error occurred.

        Yields:
            Dicts with ``event`` and ``data`` keys for SSE serialization.
        """
        agent_session = await self._session_mapping.get_or_create(str(session_id))

        # Inject runtime context into session state for tool access
        agent_session.state.update(
            {
                "project_name": project_name,
                "project_id": project_id,
                "available_tasks": available_tasks or [],
                "available_statuses": available_statuses or [],
                "github_token": github_token,
                "session_id": str(session_id),
            }
        )

        # Auto-delegate to plan mode if the session is in plan mode
        if agent_session.state.get("is_plan_mode"):
            async for event in self.run_plan_stream(
                message=message,
                session_id=session_id,
                github_token=github_token,
                project_name=project_name,
                project_id=project_id,
                available_statuses=available_statuses,
                repo_owner=agent_session.state.get("repo_owner", ""),
                repo_name=agent_session.state.get("repo_name", ""),
                db=db,
            ):
                yield event
            return

        instructions = build_system_instructions(
            project_name=project_name,
            available_statuses=available_statuses,
        )

        mcp_servers = None
        if db and project_id:
            mcp_servers = await load_mcp_tools(project_id, db) or None

        agent = await create_agent(
            instructions=instructions,
            tools=self._tools,
            github_token=github_token,
            mcp_servers=mcp_servers,
            tool_runtime_state=agent_session.state,
        )

        try:
            accumulated_text = ""
            action_type = None
            action_data = None
            final_response: AgentResponse | None = None

            stream = agent.run(
                message,
                stream=True,
                session=agent_session,
            )
            async for update in stream:
                update_text = _extract_text(update)
                if update_text:
                    accumulated_text += update_text
                    yield {"event": "token", "data": json.dumps({"content": update_text})}

                current_action_type, current_action_data = _extract_action_payload(update)
                if current_action_type:
                    action_type = current_action_type
                    action_data = current_action_data
                    yield {
                        "event": "tool_result",
                        "data": json.dumps(
                            {
                                "action_type": action_type,
                                "action_data": action_data,
                            }
                        ),
                    }

            if hasattr(stream, "get_final_response"):
                final_response = await stream.get_final_response()
                if final_response is not None and not accumulated_text:
                    accumulated_text = final_response.text

            if final_response is not None and action_type is None:
                final_message = self._convert_response(final_response, session_id)
                if final_message.action_type is not None:
                    action_type = final_message.action_type.value
                    action_data = final_message.action_data
                    if not accumulated_text:
                        accumulated_text = final_message.content

            session_action_type, session_action_data = _consume_session_tool_action(agent_session)
            if action_type is None and session_action_type:
                action_type = session_action_type
                action_data = session_action_data

            # Fallback: try to extract tool result from accumulated text (JSON)
            if action_type is None and accumulated_text:
                try:
                    parsed = json.loads(accumulated_text)
                    if isinstance(parsed, dict) and "action_type" in parsed:
                        action_type = parsed["action_type"]
                        action_data = parsed.get("action_data")
                        accumulated_text = parsed.get("content", accumulated_text)
                except (json.JSONDecodeError, TypeError):
                    pass

            # Build final message
            final_msg = ChatMessage(
                session_id=session_id,
                sender_type=SenderType.ASSISTANT,
                content=accumulated_text or "I processed your request.",
                action_type=ActionType(action_type) if action_type else None,
                action_data=action_data,
            )
            yield {
                "event": "done",
                "data": final_msg.model_dump_json(),
            }

        except Exception as e:
            logger.error("Agent stream failed: %s", e, exc_info=True)
            await self._session_mapping.invalidate(str(session_id))
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }

    # ── Plan mode methods ────────────────────────────────────────────────

    async def run_plan(
        self,
        *,
        message: str,
        session_id: UUID,
        github_token: str | None = None,
        project_name: str = "Unknown Project",
        project_id: str = "",
        available_statuses: list[str] | None = None,
        repo_owner: str = "",
        repo_name: str = "",
        selected_pipeline_id: str | None = None,
        db: Any | None = None,
    ) -> ChatMessage:
        """Run the plan-mode agent (non-streaming).

        Sets ``is_plan_mode=True`` and ``repo_owner``/``repo_name`` in
        session state so follow-up messages auto-delegate.
        """
        agent_session = await self._session_mapping.get_or_create(str(session_id))
        effective_pipeline_id = selected_pipeline_id or agent_session.state.get(
            "selected_pipeline_id"
        )

        # Auto-resolve the project's assigned pipeline when none was
        # explicitly selected (e.g. no @mention).  This ensures the plan
        # references the existing saved pipeline instead of leaving the
        # field empty and resolving a potentially different pipeline at
        # approval time.
        if not effective_pipeline_id and project_id:
            from src.services.workflow_orchestrator.config import resolve_assigned_pipeline_id

            effective_pipeline_id = await resolve_assigned_pipeline_id(project_id)

        # Inject plan-mode context
        agent_session.state.update(
            {
                "project_name": project_name,
                "project_id": project_id,
                "available_statuses": available_statuses or [],
                "github_token": github_token,
                "session_id": str(session_id),
                "is_plan_mode": True,
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "selected_pipeline_id": effective_pipeline_id,
                "db": db,
            }
        )

        instructions = build_plan_instructions(
            project_name=project_name,
            project_id=project_id,
            repo_owner=repo_owner,
            repo_name=repo_name,
            available_statuses=available_statuses,
        )

        agent = await create_agent(
            instructions=instructions,
            tools=self._plan_tools,
            github_token=github_token,
            tool_runtime_state=agent_session.state,
        )

        sid = str(session_id)
        plan_request_started_at = utcnow().isoformat()
        try:
            response: AgentResponse = await agent.run(
                message,
                session=agent_session,
            )
            result = self._convert_response(response, session_id)
            session_action_type, session_action_data = _consume_session_tool_action(agent_session)
            if result.action_type is None and session_action_type:
                result.action_type = ActionType(session_action_type)
                result.action_data = session_action_data
                result.content = _normalize_assistant_content(result.content, session_action_type)
            if result.action_type is None:
                recovered_action_type, recovered_action_data = await _recover_saved_plan_action(
                    db,
                    session_id,
                    updated_after=plan_request_started_at,
                )
                if recovered_action_type:
                    result.action_type = ActionType(recovered_action_type)
                    result.action_data = recovered_action_data
                    result.content = _normalize_assistant_content(
                        result.content,
                        recovered_action_type,
                    )
            return result
        except Exception as e:
            logger.error("Plan agent run failed: %s", e, exc_info=True)
            await self._session_mapping.invalidate(sid)
            return ChatMessage(
                session_id=session_id,
                sender_type=SenderType.ASSISTANT,
                content=f"I encountered an error in plan mode ({type(e).__name__}). Please try again.",
            )

    async def run_plan_stream(
        self,
        *,
        message: str,
        session_id: UUID,
        github_token: str | None = None,
        project_name: str = "Unknown Project",
        project_id: str = "",
        available_statuses: list[str] | None = None,
        repo_owner: str = "",
        repo_name: str = "",
        selected_pipeline_id: str | None = None,
        db: Any | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Run the plan-mode agent in streaming mode with thinking events.

        Yields SSE events including ``thinking`` events for phase-aware UI.
        """
        agent_session = await self._session_mapping.get_or_create(str(session_id))

        # Determine thinking phase based on whether we are refining
        is_refining = agent_session.state.get("active_plan_id") is not None
        effective_pipeline_id = selected_pipeline_id or agent_session.state.get(
            "selected_pipeline_id"
        )

        # Auto-resolve the project's assigned pipeline when none was
        # explicitly selected (e.g. no @mention).
        if not effective_pipeline_id and project_id:
            from src.services.workflow_orchestrator.config import resolve_assigned_pipeline_id

            effective_pipeline_id = await resolve_assigned_pipeline_id(project_id)

        # Inject plan-mode context
        agent_session.state.update(
            {
                "project_name": project_name,
                "project_id": project_id,
                "available_statuses": available_statuses or [],
                "github_token": github_token,
                "session_id": str(session_id),
                "is_plan_mode": True,
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "selected_pipeline_id": effective_pipeline_id,
                "db": db,
            }
        )

        instructions = build_plan_instructions(
            project_name=project_name,
            project_id=project_id,
            repo_owner=repo_owner,
            repo_name=repo_name,
            available_statuses=available_statuses,
        )

        agent = await create_agent(
            instructions=instructions,
            tools=self._plan_tools,
            github_token=github_token,
            tool_runtime_state=agent_session.state,
        )

        try:
            # Emit initial thinking event
            if is_refining:
                yield {
                    "event": "thinking",
                    "data": json.dumps(
                        {
                            "phase": "refining",
                            "detail": "Incorporating your feedback…",
                        }
                    ),
                }
            else:
                yield {
                    "event": "thinking",
                    "data": json.dumps(
                        {
                            "phase": "researching",
                            "detail": "Analyzing project context…",
                        }
                    ),
                }

            accumulated_text = ""
            action_type = None
            action_data = None
            planning_event_emitted = False
            final_response: AgentResponse | None = None
            plan_request_started_at = utcnow().isoformat()

            stream = agent.run(
                message,
                stream=True,
                session=agent_session,
            )
            async for update in stream:
                update_text = _extract_text(update)
                if update_text:
                    # Emit planning phase on first text output
                    if not planning_event_emitted and not is_refining:
                        yield {
                            "event": "thinking",
                            "data": json.dumps(
                                {
                                    "phase": "planning",
                                    "detail": "Drafting implementation plan…",
                                }
                            ),
                        }
                        planning_event_emitted = True
                    accumulated_text += update_text
                    yield {"event": "token", "data": json.dumps({"content": update_text})}

                current_action_type, current_action_data = _extract_action_payload(update)
                if current_action_type:
                    # Fire pre-save hook for automatic versioning
                    if current_action_type == "plan_create":
                        await on_pre_tool_use_hook(
                            "save_plan",
                            current_action_data or {},
                            agent_session.state,
                        )
                    action_type = current_action_type
                    action_data = current_action_data
                    yield {
                        "event": "tool_result",
                        "data": json.dumps(
                            {
                                "action_type": action_type,
                                "action_data": action_data,
                            }
                        ),
                    }
                    # Fire post-save hook for plan_diff SSE event
                    if current_action_type == "plan_create":
                        diff_event = await on_post_tool_use_hook(
                            "save_plan",
                            action_data,
                            agent_session.state,
                        )
                        if diff_event:
                            yield diff_event

            if hasattr(stream, "get_final_response"):
                final_response = await stream.get_final_response()
                if final_response is not None and not accumulated_text:
                    accumulated_text = final_response.text

            if final_response is not None and action_type is None:
                final_message = self._convert_response(final_response, session_id)
                if final_message.action_type is not None:
                    action_type = final_message.action_type.value
                    action_data = final_message.action_data
                    if not accumulated_text:
                        accumulated_text = final_message.content

            session_action_type, session_action_data = _consume_session_tool_action(agent_session)
            if action_type is None and session_action_type:
                action_type = session_action_type
                action_data = session_action_data

            if action_type is None:
                recovered_action_type, recovered_action_data = await _recover_saved_plan_action(
                    db,
                    session_id,
                    updated_after=plan_request_started_at,
                )
                if recovered_action_type:
                    action_type = recovered_action_type
                    action_data = recovered_action_data

            # Fallback: extract tool result from accumulated text
            if action_type is None and accumulated_text:
                try:
                    parsed = json.loads(accumulated_text)
                    if isinstance(parsed, dict) and "action_type" in parsed:
                        action_type = parsed["action_type"]
                        action_data = parsed.get("action_data")
                        accumulated_text = parsed.get("content", accumulated_text)
                except (json.JSONDecodeError, TypeError):
                    pass

            final_msg = ChatMessage(
                session_id=session_id,
                sender_type=SenderType.ASSISTANT,
                content=_normalize_assistant_content(
                    accumulated_text or "I processed your plan request.",
                    action_type,
                ),
                action_type=ActionType(action_type) if action_type else None,
                action_data=action_data,
            )
            yield {
                "event": "done",
                "data": final_msg.model_dump_json(),
            }

        except Exception as e:
            logger.error("Plan agent stream failed: %s", e, exc_info=True)
            await self._session_mapping.invalidate(str(session_id))
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }

    async def exit_plan_mode(self, session_id: UUID) -> None:
        """Clear plan-mode state from the agent session."""
        agent_session = await self._session_mapping.get_or_create(str(session_id))
        agent_session.state.pop("is_plan_mode", None)
        agent_session.state.pop("active_plan_id", None)

    def _convert_response(self, response: AgentResponse, session_id: UUID) -> ChatMessage:
        """Convert an AgentResponse into a ChatMessage.

        Extracts action_type and action_data from tool results embedded
        in the response messages.
        """
        content_parts: list[str] = []
        action_type: str | None = None
        action_data: dict[str, Any] | None = None

        for msg in response.messages:
            msg_text = _extract_text(msg)
            if msg_text:
                content_parts.append(msg_text)

            current_action_type, current_action_data = _extract_action_payload(msg)
            if current_action_type:
                action_type = current_action_type
                action_data = current_action_data

        # If no content was extracted from messages, use a default
        content = "\n".join(content_parts) if content_parts else "I processed your request."

        # Try to extract tool result from the last message's metadata
        if action_type is None and response.messages:
            last_msg = response.messages[-1]
            # Check if the content itself is a structured tool result
            last_msg_text = _extract_text(last_msg)
            if last_msg_text:
                try:
                    parsed = json.loads(last_msg_text)
                    if isinstance(parsed, dict) and "action_type" in parsed:
                        action_type = parsed["action_type"]
                        action_data = parsed.get("action_data")
                        content = parsed.get("content", content)
                except (json.JSONDecodeError, TypeError):
                    pass

        return ChatMessage(
            session_id=session_id,
            sender_type=SenderType.ASSISTANT,
            content=_normalize_assistant_content(content, action_type),
            action_type=ActionType(action_type) if action_type else None,
            action_data=action_data,
            timestamp=utcnow(),
        )


# ── Module-level singleton ───────────────────────────────────────────────

_chat_agent_service: ChatAgentService | None = None


def get_chat_agent_service() -> ChatAgentService:
    """Return the module-level ChatAgentService singleton.

    Creates the instance on first call.
    """
    global _chat_agent_service
    if _chat_agent_service is None:
        _chat_agent_service = ChatAgentService()
    return _chat_agent_service
