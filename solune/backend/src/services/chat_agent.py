"""Chat agent service — wraps Microsoft Agent Framework for Solune chat.

Manages the Agent lifecycle, AgentSession ↔ Solune session_id mapping,
and converts AgentResponse messages into ChatMessage instances.

Key design decisions:
- SQLite remains the canonical store for conversation history.
- AgentSession holds a lightweight summary for multi-turn context.
- Sessions are evicted after configurable inactivity (TTL).
- The Agent is created per-invocation for Copilot (token-bound) or as
  a singleton for Azure OpenAI (static credentials).
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from agent_framework import Agent, AgentResponse, AgentSession

from src.config import get_settings
from src.logging_utils import get_logger
from src.models.chat import ActionType, ChatMessage, SenderType
from src.prompts.agent_instructions import build_system_instructions
from src.services.agent_provider import create_agent
from src.services.agent_tools import ToolResult, register_tools
from src.utils import utcnow

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


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

        Returns:
            ChatMessage with the agent's response, including action_type and
            action_data when the agent invoked an action tool.
        """
        instructions = build_system_instructions(
            project_name=project_name,
            available_statuses=available_statuses,
        )

        agent = create_agent(
            instructions=instructions,
            tools=self._tools,
            github_token=github_token,
        )

        agent_session = await self._session_mapping.get_or_create(str(session_id))

        # Build runtime kwargs for tool context injection
        function_kwargs = {
            "project_name": project_name,
            "project_id": project_id,
            "available_tasks": available_tasks or [],
            "available_statuses": available_statuses or [],
            "github_token": github_token,
            "session_id": str(session_id),
            "pipeline_id": pipeline_id,
            "file_urls": file_urls or [],
        }

        try:
            response: AgentResponse = await agent.run(
                input=message,
                session=agent_session,
                function_invocation_kwargs=function_kwargs,
            )
            return self._convert_response(response, session_id)
        except Exception as e:
            logger.error("Agent run failed: %s", e, exc_info=True)
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
        instructions = build_system_instructions(
            project_name=project_name,
            available_statuses=available_statuses,
        )

        agent = create_agent(
            instructions=instructions,
            tools=self._tools,
            github_token=github_token,
        )

        agent_session = await self._session_mapping.get_or_create(str(session_id))

        function_kwargs = {
            "project_name": project_name,
            "project_id": project_id,
            "available_tasks": available_tasks or [],
            "available_statuses": available_statuses or [],
            "github_token": github_token,
            "session_id": str(session_id),
        }

        try:
            accumulated_text = ""
            action_type = None
            action_data = None

            async for update in agent.run_stream(
                input=message,
                session=agent_session,
                function_invocation_kwargs=function_kwargs,
            ):
                # AgentResponseUpdate has .text for partial content
                if hasattr(update, "text") and update.text:
                    accumulated_text += update.text
                    yield {"event": "token", "data": json.dumps({"content": update.text})}

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
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }

    def _convert_response(
        self, response: AgentResponse, session_id: UUID
    ) -> ChatMessage:
        """Convert an AgentResponse into a ChatMessage.

        Extracts action_type and action_data from tool results embedded
        in the response messages.
        """
        content_parts: list[str] = []
        action_type: str | None = None
        action_data: dict[str, Any] | None = None

        for msg in response.messages:
            # Agent messages contain the text content
            if hasattr(msg, "content") and msg.content:
                if isinstance(msg.content, str):
                    content_parts.append(msg.content)
                elif isinstance(msg.content, list):
                    for part in msg.content:
                        if hasattr(part, "text"):
                            content_parts.append(part.text)

            # Check for tool results in annotations or metadata
            if hasattr(msg, "annotations"):
                for annotation in msg.annotations or []:
                    if hasattr(annotation, "data") and isinstance(annotation.data, dict):
                        tool_result = annotation.data
                        if "action_type" in tool_result:
                            action_type = tool_result["action_type"]
                            action_data = tool_result.get("action_data")

        # If no content was extracted from messages, use a default
        content = "\n".join(content_parts) if content_parts else "I processed your request."

        # Try to extract tool result from the last message's metadata
        if action_type is None and response.messages:
            last_msg = response.messages[-1]
            # Check if the content itself is a structured tool result
            if hasattr(last_msg, "content") and isinstance(last_msg.content, str):
                try:
                    parsed = json.loads(last_msg.content)
                    if isinstance(parsed, dict) and "action_type" in parsed:
                        action_type = parsed["action_type"]
                        action_data = parsed.get("action_data")
                        content = parsed.get("content", content)
                except (json.JSONDecodeError, TypeError):
                    pass

        return ChatMessage(
            session_id=session_id,
            sender_type=SenderType.ASSISTANT,
            content=content,
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
