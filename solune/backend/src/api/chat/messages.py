"""Message CRUD endpoints."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.api.auth import get_session_dep
from src.dependencies import require_selected_project
from src.exceptions import ValidationError
from src.logging_utils import get_logger, handle_service_error
from src.middleware.rate_limit import limiter
from src.models.chat import (
    ActionType,
    ChatMessage,
    ChatMessageRequest,
    ChatMessagesResponse,
    SenderType,
)
from src.models.user import UserSession
from src.services.ai_agent import get_ai_agent_service
from src.services.cache import (
    cache,
    get_project_items_cache_key,
    get_user_projects_cache_key,
)
from src.services.chat_agent import get_chat_agent_service
from src.services.database import get_db
from src.utils import utcnow

from .dispatch import (
    _extract_transcript_content,
    _handle_agent_command,
    _handle_feature_request,
    _handle_status_change,
    _handle_task_generation,
    _handle_transcript_upload,
    _post_process_agent_response,
)
from .helpers import (
    _trigger_signal_delivery,
    add_message,
)
from .state import _messages

logger = get_logger(__name__)
router = APIRouter()


@router.get("/messages", response_model=ChatMessagesResponse)
async def get_messages(
    session: Annotated[UserSession, Depends(get_session_dep)],
    limit: int = 50,
    offset: int = 0,
    conversation_id: str | None = None,
) -> ChatMessagesResponse:
    """Get chat messages for current session with pagination.

    Pagination is performed at the database level to avoid loading all
    rows into memory for sessions with large message histories.

    When *conversation_id* is provided, only messages for that conversation
    are returned.
    """
    from src.services import chat_store

    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    key = str(session.session_id)

    db = get_db()
    total = await chat_store.count_messages(db, key, conversation_id=conversation_id)
    rows = await chat_store.get_messages(
        db, key, limit=limit, offset=offset, conversation_id=conversation_id
    )
    paginated: list[ChatMessage] = []
    for row in rows:
        action_data = None
        if row.get("action_data"):
            try:
                action_data = json.loads(row["action_data"])
            except (json.JSONDecodeError, TypeError):
                action_data = None
        paginated.append(
            ChatMessage(
                message_id=row["message_id"],
                session_id=row["session_id"],
                sender_type=SenderType(row["sender_type"]),
                content=row["content"],
                action_type=ActionType(row["action_type"]) if row.get("action_type") else None,
                action_data=action_data,
                timestamp=row["timestamp"] if row.get("timestamp") else utcnow(),
                conversation_id=row.get("conversation_id"),
            )
        )
    return ChatMessagesResponse(
        messages=paginated,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.delete("/messages")
async def clear_messages(
    session: Annotated[UserSession, Depends(get_session_dep)],
    conversation_id: str | None = None,
) -> dict[str, str]:
    """Clear all chat messages for current session, optionally scoped to a conversation."""
    key = str(session.session_id)
    _messages.pop(key, None)
    try:
        from src.services import chat_store

        db = get_db()
        await chat_store.clear_messages(db, key, conversation_id=conversation_id)
    except Exception:
        logger.warning("Failed to clear messages from SQLite", exc_info=True)
    return {"message": "Chat history cleared"}


@router.post("/messages", response_model=ChatMessage)
@limiter.limit("10/minute")
async def send_message(
    request: Request,
    chat_request: ChatMessageRequest,
    session: Annotated[UserSession, Depends(get_session_dep)],
) -> ChatMessage | JSONResponse:
    """Send a chat message and get AI response."""
    from .plans import send_plan_message

    # Require project selection
    selected_project_id = require_selected_project(session)

    # /plan must use the dedicated plan-mode toolset. Falling through to the
    # generic chat agent strips the slash command but leaves save_plan unavailable.
    if chat_request.content.strip().lower().startswith("/plan"):
        return await send_plan_message(request, chat_request, session)

    # Validate pipeline_id if provided
    if chat_request.pipeline_id:
        from src.services.pipelines.service import PipelineService

        try:
            db = get_db()
            pipeline_svc = PipelineService(db)
            pipeline = await pipeline_svc.get_pipeline(
                selected_project_id,
                chat_request.pipeline_id,
                github_user_id=session.github_user_id,
            )
            if pipeline is None:
                raise ValidationError(f"Pipeline not found: {chat_request.pipeline_id}")
        except ValidationError:
            raise
        except Exception as exc:
            handle_service_error(exc, "validate pipeline")

    # Try to get AI service (optional) — used for ai_enhance=False fallback
    ai_service = None
    try:
        ai_service = get_ai_agent_service()
    except ValueError:
        pass

    # Try to get the new ChatAgentService
    chat_agent_service = None
    try:
        chat_agent_service = get_chat_agent_service()
    except Exception:
        pass

    if ai_service is None and chat_agent_service is None:
        # Neither service available — return error
        error_msg = ChatMessage(
            session_id=session.session_id,
            sender_type=SenderType.ASSISTANT,
            content="AI features are not configured. Please set up your AI provider credentials (GitHub Copilot OAuth or Azure OpenAI) to use chat functionality.",
            conversation_id=chat_request.conversation_id,
        )
        await add_message(session.session_id, error_msg)
        return error_msg

    # Create user message
    user_message = ChatMessage(
        session_id=session.session_id,
        sender_type=SenderType.USER,
        content=chat_request.content,
        conversation_id=chat_request.conversation_id,
    )
    await add_message(session.session_id, user_message)

    # Get project details for context
    project_name = "Unknown Project"
    project_columns = []
    cache_key = get_user_projects_cache_key(session.github_user_id)
    cached_projects = cache.get(cache_key)
    if cached_projects:
        for p in cached_projects:
            if p.project_id == selected_project_id:
                project_name = p.name
                project_columns = [col.name for col in p.status_columns]
                break

    # Get current tasks for context
    tasks_cache_key = get_project_items_cache_key(selected_project_id)
    current_tasks = cache.get(tasks_cache_key) or []

    # ── Priority 0: #agent command — custom agent creation ──────────
    agent_msg = await _handle_agent_command(
        session,
        chat_request.content,
        selected_project_id,
        project_name,
        project_columns,
        conversation_id=chat_request.conversation_id,
    )
    if agent_msg:
        return agent_msg

    content = chat_request.content

    # Strip slash-command prefixes so the AI prompt receives clean user input
    import re as _re

    content = _re.sub(r"^/plan\s+", "", content)

    # ── ai_enhance=False bypass — preserves v0.1.x behaviour ────────
    if not chat_request.ai_enhance:
        if ai_service is not None:
            return await _handle_task_generation(
                session,
                content,
                ai_service,
                project_name,
                chat_request.ai_enhance,
                chat_request.pipeline_id,
            )
        # Explicitly avoid routing to the agent when ai_enhance=False.
        assistant_msg = ChatMessage(
            session_id=session.session_id,
            sender_type=SenderType.ASSISTANT,
            content=content,
            action_type=ActionType.TASK_CREATE,
            action_data={
                "proposed_title": content,
                "proposed_description": "",
            },
            conversation_id=chat_request.conversation_id,
        )
        assistant_msg = await _post_process_agent_response(
            session=session,
            message=assistant_msg,
            project_name=project_name,
            pipeline_id=chat_request.pipeline_id,
            file_urls=chat_request.file_urls,
            cached_projects=cached_projects,
            selected_project_id=selected_project_id,
            user_content=content,
        )
        await add_message(session.session_id, assistant_msg)
        return assistant_msg

    # ── Agent-powered dispatch (v0.2.0) ──────────────────────────────
    # The agent decides which tool to invoke based on its reasoning,
    # replacing the old priority cascade.
    if chat_agent_service is not None:
        # Handle transcript uploads by including content in the message
        transcript_content = None
        if chat_request.file_urls:
            transcript_content = await _extract_transcript_content(chat_request.file_urls)

        agent_input = content
        if transcript_content:
            agent_input = f"[Uploaded transcript file]\n\n{transcript_content}"

        assistant_message = await chat_agent_service.run(
            message=agent_input,
            session_id=session.session_id,
            github_token=session.access_token,
            project_name=project_name,
            project_id=selected_project_id,
            available_tasks=current_tasks,
            available_statuses=project_columns,
            pipeline_id=chat_request.pipeline_id,
            file_urls=chat_request.file_urls,
            db=get_db(),
            conversation_id=str(chat_request.conversation_id)
            if chat_request.conversation_id
            else None,
        )
        assistant_message.conversation_id = chat_request.conversation_id

        # Post-process: create proposals/recommendations from action_data
        assistant_message = await _post_process_agent_response(
            session=session,
            message=assistant_message,
            project_name=project_name,
            pipeline_id=chat_request.pipeline_id,
            file_urls=chat_request.file_urls,
            cached_projects=cached_projects,
            selected_project_id=selected_project_id,
            user_content=content,
        )

        await add_message(session.session_id, assistant_message)
        _trigger_signal_delivery(session, assistant_message, project_name)
        return assistant_message

    # ── Fallback: old priority dispatch (when ChatAgentService unavailable) ──
    if ai_service is None:
        raise RuntimeError("AI service is required for fallback priority dispatch")

    # Priority 0.5: Transcript upload → issue recommendation
    transcript_msg = await _handle_transcript_upload(
        session,
        ai_service,
        project_name,
        chat_request.pipeline_id,
        chat_request.file_urls,
    )
    if transcript_msg:
        return transcript_msg

    # Priority 1: Feature request → issue recommendation
    feature_msg = await _handle_feature_request(
        session,
        content,
        ai_service,
        project_name,
        chat_request.pipeline_id,
        chat_request.ai_enhance,
        chat_request.file_urls,
    )
    if feature_msg:
        return feature_msg

    # Priority 2: Status change request
    status_msg = await _handle_status_change(
        session,
        content,
        ai_service,
        current_tasks,
        project_columns,
        cached_projects,
        selected_project_id,
        project_name,
    )
    if status_msg:
        return status_msg

    # Priority 3: Task generation (metadata-only or full AI)
    return await _handle_task_generation(
        session,
        content,
        ai_service,
        project_name,
        chat_request.ai_enhance,
        chat_request.pipeline_id,
    )
