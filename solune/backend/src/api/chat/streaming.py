"""SSE streaming endpoints for chat and plan modes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.api.auth import get_session_dep
from src.dependencies import require_selected_project
from src.logging_utils import get_logger
from src.middleware.rate_limit import limiter
from src.models.chat import ChatMessage, ChatMessageRequest, SenderType
from src.models.user import UserSession
from src.services.cache import cache, get_project_items_cache_key, get_user_projects_cache_key
from src.services.chat_agent import get_chat_agent_service
from src.services.database import get_db

from .dispatch import _extract_transcript_content, _post_process_agent_response
from .helpers import _resolve_repository, _trigger_signal_delivery, add_message

logger = get_logger(__name__)
router = APIRouter()


@router.post("/messages/stream")
@limiter.limit("10/minute")
async def send_message_stream(
    request: Request,
    chat_request: ChatMessageRequest,
    session: Annotated[UserSession, Depends(get_session_dep)],
):
    """Send a chat message and stream the AI response via SSE.

    Returns Server-Sent Events with progressive token delivery.
    Event types: token, tool_call, tool_result, done, error.
    """
    from sse_starlette.sse import EventSourceResponse

    from src.config import get_settings as _get_settings

    selected_project_id = require_selected_project(session)

    if chat_request.content.strip().lower().startswith("/plan"):
        return await send_plan_message_stream(request, chat_request, session)

    # Streaming requires the agent — reject unsupported options early.
    if not getattr(chat_request, "ai_enhance", True):
        return JSONResponse(
            status_code=400,
            content={
                "detail": "ai_enhance=False is not supported for streaming. "
                "Use /messages endpoint instead."
            },
        )

    try:
        chat_agent_svc = get_chat_agent_service()
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"detail": "Streaming not available. Use /messages endpoint instead."},
        )

    settings = _get_settings()
    if not settings.agent_streaming_enabled:
        return JSONResponse(
            status_code=503,
            content={"detail": "Streaming is disabled. Use /messages endpoint instead."},
        )

    # Create user message
    user_message = ChatMessage(
        session_id=session.session_id,
        sender_type=SenderType.USER,
        content=chat_request.content,
        conversation_id=chat_request.conversation_id,
    )
    await add_message(session.session_id, user_message)

    # Get project details
    project_name = "Unknown Project"
    project_columns: list[str] = []
    cache_key = get_user_projects_cache_key(session.github_user_id)
    cached_projects = cache.get(cache_key)
    if cached_projects:
        for p in cached_projects:
            if p.project_id == selected_project_id:
                project_name = p.name
                project_columns = [col.name for col in p.status_columns]
                break

    tasks_cache_key = get_project_items_cache_key(selected_project_id)
    current_tasks = cache.get(tasks_cache_key) or []

    # Extract transcript content from uploaded files (mirrors non-streaming path)
    stream_message = chat_request.content
    if chat_request.file_urls:
        transcript_content = await _extract_transcript_content(chat_request.file_urls)
        if transcript_content:
            stream_message = f"[Uploaded transcript file]\n\n{transcript_content}"

    async def event_generator():
        async for event in chat_agent_svc.run_stream(
            message=stream_message,
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
        ):
            if event.get("event") == "done":
                try:
                    assistant_message = ChatMessage.model_validate_json(event["data"])
                    assistant_message.conversation_id = chat_request.conversation_id
                    assistant_message = await _post_process_agent_response(
                        session=session,
                        message=assistant_message,
                        project_name=project_name,
                        pipeline_id=chat_request.pipeline_id,
                        file_urls=chat_request.file_urls,
                        cached_projects=cached_projects,
                        selected_project_id=selected_project_id,
                        user_content=chat_request.content,
                    )
                    await add_message(session.session_id, assistant_message)
                    _trigger_signal_delivery(session, assistant_message, project_name)
                    yield {
                        "event": "done",
                        "data": assistant_message.model_dump_json(),
                    }
                except Exception:
                    logger.error(
                        "Failed to persist or post-process streamed agent response",
                        exc_info=True,
                    )
                    yield event
                continue
            yield event

    return EventSourceResponse(event_generator())


@router.post("/messages/plan/stream")
@limiter.limit("10/minute")
async def send_plan_message_stream(
    request: Request,
    chat_request: ChatMessageRequest,
    session: Annotated[UserSession, Depends(get_session_dep)],
):
    """Enter plan mode with SSE streaming and thinking events."""
    from sse_starlette.sse import EventSourceResponse

    selected_project_id = require_selected_project(session)

    content = chat_request.content.strip()
    if content.lower().startswith("/plan"):
        content = content[5:].strip()
    if not content:
        return JSONResponse(
            status_code=400,
            content={"detail": "Please provide a feature description after /plan."},
        )

    try:
        owner, repo = await _resolve_repository(session)
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"detail": "No repository linked to the selected project."},
        )

    # Get project details
    project_name = "Unknown Project"
    project_columns: list[str] = []
    cache_key = get_user_projects_cache_key(session.github_user_id)
    cached_projects = cache.get(cache_key)
    if cached_projects:
        for p in cached_projects:
            if p.project_id == selected_project_id:
                project_name = p.name
                project_columns = [col.name for col in p.status_columns]
                break

    try:
        chat_agent_svc = get_chat_agent_service()
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"detail": "Plan mode not available."},
        )

    # Create user message only after plan mode is confirmed available.
    user_message = ChatMessage(
        session_id=session.session_id,
        sender_type=SenderType.USER,
        content=chat_request.content,
        conversation_id=chat_request.conversation_id,
    )
    await add_message(session.session_id, user_message)

    async def event_generator():
        async for event in chat_agent_svc.run_plan_stream(
            message=content,
            session_id=session.session_id,
            github_token=session.access_token,
            project_name=project_name,
            project_id=selected_project_id,
            available_statuses=project_columns,
            repo_owner=owner,
            repo_name=repo,
            selected_pipeline_id=chat_request.pipeline_id,
            db=get_db(),
        ):
            if event.get("event") == "done":
                try:
                    assistant_message = ChatMessage.model_validate_json(event["data"])
                    assistant_message.conversation_id = chat_request.conversation_id
                    await add_message(session.session_id, assistant_message)
                    yield {
                        "event": "done",
                        "data": assistant_message.model_dump_json(),
                    }
                except Exception:
                    logger.error(
                        "Failed to persist plan streamed response",
                        exc_info=True,
                    )
                    yield event
                continue
            yield event

    return EventSourceResponse(event_generator())
