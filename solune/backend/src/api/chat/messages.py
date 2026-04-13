"""Message and conversation endpoints for the chat API."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse

from src.api.auth import get_session_dep
from src.constants import DEFAULT_STATUS_COLUMNS
from src.dependencies import require_selected_project
from src.exceptions import NotFoundError, ValidationError
from src.logging_utils import get_logger, handle_service_error
from src.middleware.rate_limit import limiter
from src.models.chat import (
    ActionType,
    ChatMessage,
    ChatMessageRequest,
    ChatMessagesResponse,
    Conversation,
    ConversationCreateRequest,
    ConversationsListResponse,
    ConversationUpdateRequest,
    SenderType,
)
from src.models.recommendation import (
    AITaskProposal,
    IssueRecommendation,
    ProposalStatus,
    RecommendationStatus,
)
from src.models.user import UserSession
from src.services.ai_agent import get_ai_agent_service
from src.services.chat_agent import get_chat_agent_service

if TYPE_CHECKING:
    from src.services.ai_agent import AIAgentService
from src.services.cache import (
    cache,
    get_project_items_cache_key,
    get_user_projects_cache_key,
)
from src.services.database import get_db
from src.utils import resolve_repository, utcnow

from src.api.chat.constants import MAX_FILE_SIZE_BYTES, _messages
from src.api.chat import persistence as _persistence

logger = get_logger(__name__)
router = APIRouter()


# ── Command dispatch helpers (extracted from send_message) ───────────────


async def _handle_agent_command(
    session: UserSession,
    content: str,
    selected_project_id: str,
    project_name: str,
    project_columns: list[str],
    conversation_id: UUID | None = None,
) -> ChatMessage | None:
    """Priority 0: Handle /agent or #agent custom agent creation commands.

    Returns an assistant ChatMessage if the command was handled, None otherwise.
    """
    from src.services.agent_creator import get_active_session, handle_agent_command

    session_key = str(session.session_id)
    is_agent_command = content.strip().lower().startswith(
        "/agent"
    ) or content.strip().lower().startswith("#agent")
    active_agent_session = get_active_session(session_key)

    if not (is_agent_command or active_agent_session):
        return None

    try:
        db = get_db()
        owner, repo = await _resolve_repository(session)
        agent_response_text = await handle_agent_command(
            message=content,
            session_key=session_key,
            project_id=selected_project_id,
            owner=owner,
            repo=repo,
            github_user_id=session.github_user_id,
            access_token=session.access_token,
            db=db,
            project_columns=project_columns,
        )
    except Exception as exc:
        logger.error("#agent command failed: %s", exc)
        agent_response_text = (
            "**Error:** The `#agent` command encountered an unexpected error. Please try again."
        )

    agent_msg = ChatMessage(
        session_id=session.session_id,
        sender_type=SenderType.ASSISTANT,
        content=agent_response_text,
        conversation_id=conversation_id,
    )
    await _persistence.add_message(session.session_id, agent_msg)
    _persistence._trigger_signal_delivery(session, agent_msg, project_name)
    return agent_msg


async def _handle_transcript_upload(
    session: UserSession,
    ai_service: AIAgentService,
    project_name: str,
    pipeline_id: str | None,
    file_urls: list[str] | None,
) -> ChatMessage | None:
    """Priority 0.5: Detect transcript files and generate issue recommendation.

    Checks uploaded files for transcript content. If a transcript is detected,
    analyses it via the Transcribe agent and returns an assistant message with
    an ``IssueRecommendation``.  Returns ``None`` when no transcript is found
    so the next handler in the dispatch chain can run.
    """
    if not file_urls:
        return None

    from src.services.transcript_detector import detect_transcript

    upload_dir = Path(tempfile.gettempdir()) / "chat-uploads"

    for file_url in file_urls:
        # Resolve the local file path from the upload URL.
        # Sanitise with os.path.basename (CodeQL-recognised path sanitizer)
        # to strip all directory components and prevent path-traversal.
        raw_name = file_url.rsplit("/", 1)[-1] if "/" in file_url else file_url
        filename = os.path.basename(raw_name)  # noqa: PTH119 — CodeQL sanitizer
        if not filename:
            continue

        # Build the candidate path and normalise it so CodeQL can verify
        # the subsequent prefix check neutralises any traversal attempt.
        candidate = os.path.normpath(os.path.join(str(upload_dir), filename))  # noqa: PTH118
        safe_prefix = os.path.normpath(str(upload_dir)) + os.sep
        if not candidate.startswith(safe_prefix):
            continue

        file_path = Path(candidate)
        if not file_path.exists():
            continue

        try:
            if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
                logger.warning(
                    "Skipping oversized uploaded file %s during transcript analysis", filename
                )
                continue
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.warning("Could not read uploaded file %s: %s", filename, exc)
            continue

        # Strip the 8-char UUID prefix added during upload (format: "abcd1234-original.ext")
        original_name = filename[9:] if len(filename) > 9 and filename[8] == "-" else filename
        result = detect_transcript(original_name, content)

        if not result.is_transcript:
            continue

        # Transcript detected — run through the Transcribe agent
        try:
            metadata_context: dict | None = None
            try:
                owner, repo = await _resolve_repository(session)
                from src.services.github_projects import github_projects_service
                from src.services.metadata_service import MetadataService

                metadata_svc = MetadataService(github_service=github_projects_service)
                ctx = await metadata_svc.get_or_fetch(session.access_token, owner, repo)
                metadata_context = ctx.model_dump()
            except Exception as md_err:
                logger.warning("Metadata fetch for transcript prompt failed: %s", md_err)

            recommendation = await ai_service.analyze_transcript(
                transcript_content=content,
                project_name=project_name,
                session_id=str(session.session_id),
                github_token=session.access_token,
                metadata_context=metadata_context,
            )

            recommendation.selected_pipeline_id = pipeline_id or None
            recommendation.file_urls = file_urls or []

            await _persistence.store_recommendation(recommendation)

            requirements_preview = "\n".join(
                f"- {req}" for req in recommendation.functional_requirements
            )

            technical_notes_preview = ""
            if recommendation.technical_notes:
                technical_notes_preview = f"\n\n**Technical Notes:**\n{recommendation.technical_notes[:300]}{'...' if len(recommendation.technical_notes) > 300 else ''}"

            assistant_message = ChatMessage(
                session_id=session.session_id,
                sender_type=SenderType.ASSISTANT,
                content=f"""I've analysed the uploaded transcript and generated a GitHub issue recommendation:

**{recommendation.title}**

**User Story:**
{recommendation.user_story}

**UI/UX Description:**
{recommendation.ui_ux_description}

**Functional Requirements:**
{requirements_preview}{technical_notes_preview}

Click **Confirm** to create this issue in GitHub, or **Reject** to discard.""",
                action_type=ActionType.ISSUE_CREATE,
                action_data={
                    "recommendation_id": str(recommendation.recommendation_id),
                    "proposed_title": recommendation.title,
                    "user_story": recommendation.user_story,
                    "original_context": recommendation.original_context,
                    "ui_ux_description": recommendation.ui_ux_description,
                    "functional_requirements": recommendation.functional_requirements,
                    "technical_notes": recommendation.technical_notes,
                    "status": RecommendationStatus.PENDING.value,
                    "file_urls": file_urls,
                    "pipeline_id": pipeline_id,
                },
            )
            await _persistence.add_message(session.session_id, assistant_message)
            _persistence._trigger_signal_delivery(session, assistant_message, project_name)

            logger.info(
                "Generated transcript recommendation %s: %s",
                recommendation.recommendation_id,
                recommendation.title,
            )
            return assistant_message

        except Exception as e:
            logger.error("Failed to analyse transcript: %s", e, exc_info=True)
            error_message = ChatMessage(
                session_id=session.session_id,
                sender_type=SenderType.ASSISTANT,
                content=f"I couldn't extract requirements from the uploaded transcript ({type(e).__name__}). Please try again or paste the transcript content directly.",
            )
            await _persistence.add_message(session.session_id, error_message)
            return error_message

    return None


async def _handle_feature_request(
    session: UserSession,
    content: str,
    ai_service: AIAgentService,
    project_name: str,
    pipeline_id: str | None,
    ai_enhance: bool,
    file_urls: list[str] | None,
) -> ChatMessage | None:
    """Priority 1: Detect feature request intent and generate issue recommendation.

    Returns an assistant ChatMessage if the intent was a feature request, None otherwise.
    """
    try:
        is_feature_request = await ai_service.detect_feature_request_intent(
            content, github_token=session.access_token
        )
    except Exception as e:
        logger.warning("Feature request detection failed: %s", e)
        is_feature_request = False

    if not is_feature_request:
        return None

    try:
        metadata_context: dict | None = None
        try:
            owner, repo = await _resolve_repository(session)
            from src.services.github_projects import github_projects_service
            from src.services.metadata_service import MetadataService

            metadata_svc = MetadataService(github_service=github_projects_service)
            ctx = await metadata_svc.get_or_fetch(session.access_token, owner, repo)
            metadata_context = ctx.model_dump()
        except Exception as md_err:
            logger.warning("Metadata fetch for prompt injection failed: %s", md_err)

        recommendation = await ai_service.generate_issue_recommendation(
            user_input=content,
            project_name=project_name,
            session_id=str(session.session_id),
            github_token=session.access_token,
            metadata_context=metadata_context,
        )

        recommendation.selected_pipeline_id = pipeline_id or None
        recommendation.file_urls = file_urls or []

        await _persistence.store_recommendation(recommendation)

        requirements_preview = "\n".join(
            f"- {req}" for req in recommendation.functional_requirements
        )

        technical_notes_preview = ""
        if recommendation.technical_notes:
            technical_notes_preview = f"\n\n**Technical Notes:**\n{recommendation.technical_notes[:300]}{'...' if len(recommendation.technical_notes) > 300 else ''}"

        assistant_message = ChatMessage(
            session_id=session.session_id,
            sender_type=SenderType.ASSISTANT,
            content=f"""I've generated a GitHub issue recommendation:

**{recommendation.title}**

**User Story:**
{recommendation.user_story}

**UI/UX Description:**
{recommendation.ui_ux_description}

**Functional Requirements:**
{requirements_preview}{technical_notes_preview}

Click **Confirm** to create this issue in GitHub, or **Reject** to discard.""",
            action_type=ActionType.ISSUE_CREATE,
            action_data={
                "recommendation_id": str(recommendation.recommendation_id),
                "proposed_title": recommendation.title,
                "user_story": recommendation.user_story,
                "original_context": recommendation.original_context,
                "ui_ux_description": recommendation.ui_ux_description,
                "functional_requirements": recommendation.functional_requirements,
                "technical_notes": recommendation.technical_notes,
                "status": RecommendationStatus.PENDING.value,
                "ai_enhance": ai_enhance,
                "file_urls": file_urls,
                "pipeline_id": pipeline_id,
            },
        )
        await _persistence.add_message(session.session_id, assistant_message)
        _persistence._trigger_signal_delivery(session, assistant_message, project_name)

        logger.info(
            "Generated issue recommendation %s: %s",
            recommendation.recommendation_id,
            recommendation.title,
        )
        return assistant_message

    except Exception as e:
        logger.error("Failed to generate issue recommendation: %s", e, exc_info=True)
        error_message = ChatMessage(
            session_id=session.session_id,
            sender_type=SenderType.ASSISTANT,
            content="I couldn't generate an issue recommendation from your feature request. Please try again with more detail.",
        )
        await _persistence.add_message(session.session_id, error_message)
        return error_message


async def _handle_status_change(
    session: UserSession,
    content: str,
    ai_service: AIAgentService,
    current_tasks: list,
    project_columns: list[str],
    cached_projects: list | None,
    selected_project_id: str,
    project_name: str,
) -> ChatMessage | None:
    """Priority 2: Parse status change request and create proposal.

    Returns an assistant ChatMessage if a status change was detected, None otherwise.
    """
    status_change = await ai_service.parse_status_change_request(
        user_input=content,
        available_tasks=[t.title for t in current_tasks],
        available_statuses=(project_columns or DEFAULT_STATUS_COLUMNS),
        github_token=session.access_token,
    )
    if not status_change:
        return None

    target_task = ai_service.identify_target_task(
        task_reference=status_change.task_reference,
        available_tasks=current_tasks,
    )

    if not target_task:
        error_message = ChatMessage(
            session_id=session.session_id,
            sender_type=SenderType.ASSISTANT,
            content=f"I couldn't find a task matching '{status_change.task_reference}'. Please try again with a more specific task name.",
        )
        await _persistence.add_message(session.session_id, error_message)
        return error_message

    target_status = status_change.target_status
    status_option_id = ""
    status_field_id = ""
    if cached_projects:
        for p in cached_projects:
            if p.project_id == selected_project_id:
                for col in p.status_columns:
                    if col.name.lower() == target_status.lower():
                        status_option_id = col.option_id
                        status_field_id = col.field_id
                        target_status = col.name
                        break
                break

    proposal = AITaskProposal(
        session_id=session.session_id,
        original_input=content,
        proposed_title=target_task.title,
        proposed_description=f"Move from '{target_task.status}' to '{target_status}'",
    )
    await _persistence.store_proposal(proposal)

    assistant_message = ChatMessage(
        session_id=session.session_id,
        sender_type=SenderType.ASSISTANT,
        content=f"I'll update the status of **{target_task.title}** from **{target_task.status}** to **{target_status}**.\n\nClick confirm to apply this change.",
        action_type=ActionType.STATUS_UPDATE,
        action_data={
            "proposal_id": str(proposal.proposal_id),
            "task_id": target_task.github_item_id,
            "task_title": target_task.title,
            "current_status": target_task.status,
            "target_status": target_status,
            "status_option_id": status_option_id,
            "status_field_id": status_field_id,
            "status": ProposalStatus.PENDING.value,
        },
    )
    await _persistence.add_message(session.session_id, assistant_message)
    _persistence._trigger_signal_delivery(session, assistant_message, project_name)
    return assistant_message


async def _handle_task_generation(
    session: UserSession,
    content: str,
    ai_service: AIAgentService,
    project_name: str,
    ai_enhance: bool,
    pipeline_id: str | None,
) -> ChatMessage:
    """Priority 3: Generate task from description (metadata-only or full AI).

    Always returns a ChatMessage (success or error).
    """
    if not ai_enhance:
        try:
            title = await ai_service.generate_title_from_description(
                user_input=content,
                project_name=project_name,
                github_token=session.access_token,
            )

            proposal = AITaskProposal(
                session_id=session.session_id,
                original_input=content,
                proposed_title=title,
                proposed_description=content,
                selected_pipeline_id=pipeline_id or None,
            )
            await _persistence.store_proposal(proposal)

            description_preview = content[:200]
            if len(content) > 200:
                description_preview += "..."

            assistant_message = ChatMessage(
                session_id=session.session_id,
                sender_type=SenderType.ASSISTANT,
                content=f"I've created a task proposal:\n\n**{title}**\n\n{description_preview}\n\nClick confirm to create this task.",
                action_type=ActionType.TASK_CREATE,
                action_data={
                    "proposal_id": str(proposal.proposal_id),
                    "proposed_title": title,
                    "proposed_description": content,
                    "status": ProposalStatus.PENDING.value,
                },
            )
            await _persistence.add_message(session.session_id, assistant_message)
            _persistence._trigger_signal_delivery(session, assistant_message, project_name)
            return assistant_message

        except Exception as e:
            logger.error("Failed to generate metadata (ai_enhance=off): %s", e, exc_info=True)
            error_message = ChatMessage(
                session_id=session.session_id,
                sender_type=SenderType.ASSISTANT,
                content="I couldn't generate metadata for your request. Your input was preserved — please try again.",
            )
            await _persistence.add_message(session.session_id, error_message)
            return error_message

    # Full AI pipeline: generate both title and description via AI
    try:
        generated = await ai_service.generate_task_from_description(
            user_input=content,
            project_name=project_name,
            github_token=session.access_token,
        )

        proposal = AITaskProposal(
            session_id=session.session_id,
            original_input=content,
            proposed_title=generated.title,
            proposed_description=generated.description,
            selected_pipeline_id=pipeline_id or None,
        )
        await _persistence.store_proposal(proposal)

        assistant_message = ChatMessage(
            session_id=session.session_id,
            sender_type=SenderType.ASSISTANT,
            content=(
                f"I've created a task proposal:\n\n**{generated.title}**\n\n"
                f"{generated.description[:200]}"
                f"{'...' if len(generated.description) > 200 else ''}"
                "\n\nClick confirm to create this task."
            ),
            action_type=ActionType.TASK_CREATE,
            action_data={
                "proposal_id": str(proposal.proposal_id),
                "proposed_title": generated.title,
                "proposed_description": generated.description,
                "status": ProposalStatus.PENDING.value,
            },
        )
        await _persistence.add_message(session.session_id, assistant_message)
        _persistence._trigger_signal_delivery(session, assistant_message, project_name)
        return assistant_message

    except Exception as e:
        logger.error("Failed to generate task: %s", e, exc_info=True)

        # Provide a specific, actionable error message based on failure type
        error_str = str(e)
        if (
            "401" in error_str
            or "Access denied" in error_str
            or "authentication" in error_str.lower()
        ):
            user_hint = (
                "AI provider authentication failed. Please re-authenticate via "
                "GitHub OAuth or check your AI provider credentials in Settings."
            )
        elif (
            "404" in error_str
            or "Resource not found" in error_str
            or "not found" in error_str.lower()
        ):
            user_hint = (
                "The configured AI model could not be found. Please verify your "
                "AI provider and model settings (current model may be unavailable)."
            )
        elif "timed out" in error_str.lower() or isinstance(e, TimeoutError):
            user_hint = (
                "The AI request timed out. The service may be temporarily "
                "unavailable — please try again in a moment."
            )
        elif isinstance(e, (ImportError, ModuleNotFoundError)):
            user_hint = (
                "The AI provider SDK is not available or incompatible. "
                "Please check the server logs and verify the SDK installation."
            )
        else:
            user_hint = (
                "I couldn't generate a task from your description. "
                "Please try again with more detail."
            )

        error_message = ChatMessage(
            session_id=session.session_id,
            sender_type=SenderType.ASSISTANT,
            content=user_hint,
        )
        await _persistence.add_message(session.session_id, error_message)
        return error_message


async def _resolve_repository(session: UserSession) -> tuple[str, str]:
    """Resolve repository owner and name for issue creation."""
    project_id = require_selected_project(session)
    return await resolve_repository(session.access_token, project_id)


# ── Conversation CRUD ────────────────────────────────────────────


@router.post("/conversations", status_code=201)
async def create_conversation(
    session: Annotated[UserSession, Depends(get_session_dep)],
    body: ConversationCreateRequest = Body(default_factory=ConversationCreateRequest),  # noqa: B008
) -> Conversation:
    """Create a new conversation for the current session."""
    from src.services import chat_store

    db = get_db()
    conv_id = str(uuid4())
    row = await chat_store.save_conversation(
        db,
        session_id=str(session.session_id),
        conversation_id=conv_id,
        title=body.title,
    )
    return Conversation(
        conversation_id=row["conversation_id"],
        session_id=row["session_id"],
        title=row["title"],
        created_at=row.get("created_at") or utcnow(),
        updated_at=row.get("updated_at") or utcnow(),
    )


@router.get("/conversations", response_model=ConversationsListResponse)
async def list_conversations(
    session: Annotated[UserSession, Depends(get_session_dep)],
) -> ConversationsListResponse:
    """List conversations for the current session."""
    from src.services import chat_store

    db = get_db()
    rows = await chat_store.get_conversations(db, str(session.session_id))
    conversations = [
        Conversation(
            conversation_id=r["conversation_id"],
            session_id=r["session_id"],
            title=r["title"],
            created_at=r.get("created_at") or utcnow(),
            updated_at=r.get("updated_at") or utcnow(),
        )
        for r in rows
    ]
    return ConversationsListResponse(conversations=conversations)


@router.patch("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    body: ConversationUpdateRequest,
    session: Annotated[UserSession, Depends(get_session_dep)],
) -> Conversation:
    """Update a conversation title."""
    from src.services import chat_store

    db = get_db()
    # Verify ownership before updating
    existing = await chat_store.get_conversation_by_id(db, conversation_id)
    if existing is None:
        raise NotFoundError(f"Conversation {conversation_id} not found")
    if existing["session_id"] != str(session.session_id):
        raise NotFoundError(f"Conversation {conversation_id} not found")
    row = await chat_store.update_conversation(db, conversation_id, body.title)
    if row is None:
        raise NotFoundError(f"Conversation {conversation_id} not found")
    return Conversation(
        conversation_id=row["conversation_id"],
        session_id=row["session_id"],
        title=row["title"],
        created_at=row.get("created_at") or utcnow(),
        updated_at=row.get("updated_at") or utcnow(),
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
) -> dict[str, str]:
    """Delete a conversation."""
    from src.services import chat_store

    db = get_db()
    # Verify ownership before deleting
    existing = await chat_store.get_conversation_by_id(db, conversation_id)
    if existing is None:
        raise NotFoundError(f"Conversation {conversation_id} not found")
    if existing["session_id"] != str(session.session_id):
        raise NotFoundError(f"Conversation {conversation_id} not found")
    await chat_store.delete_conversation(db, conversation_id)
    return {"message": f"Conversation {conversation_id} deleted"}


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
    # Require project selection
    selected_project_id = require_selected_project(session)

    # /plan must use the dedicated plan-mode toolset. Falling through to the
    # generic chat agent strips the slash command but leaves save_plan unavailable.
    if chat_request.content.strip().lower().startswith("/plan"):
        from src.api.chat.plans import send_plan_message

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
        await _persistence.add_message(session.session_id, error_msg)
        return error_msg

    # Create user message
    user_message = ChatMessage(
        session_id=session.session_id,
        sender_type=SenderType.USER,
        content=chat_request.content,
        conversation_id=chat_request.conversation_id,
    )
    await _persistence.add_message(session.session_id, user_message)

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
        await _persistence.add_message(session.session_id, assistant_msg)
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

        await _persistence.add_message(session.session_id, assistant_message)
        _persistence._trigger_signal_delivery(session, assistant_message, project_name)
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


# ── Agent response post-processing helpers ───────────────────────────────


async def _extract_transcript_content(file_urls: list[str]) -> str | None:
    """Extract transcript text from uploaded files, if any.

    Returns the first detected transcript content, or None.
    """
    from src.services.transcript_detector import detect_transcript

    upload_dir = Path(tempfile.gettempdir()) / "chat-uploads"

    for file_url in file_urls:
        raw_name = file_url.rsplit("/", 1)[-1] if "/" in file_url else file_url
        filename = os.path.basename(raw_name)  # noqa: PTH119
        if not filename:
            continue

        candidate = os.path.normpath(os.path.join(str(upload_dir), filename))  # noqa: PTH118
        safe_prefix = os.path.normpath(str(upload_dir)) + os.sep
        if not candidate.startswith(safe_prefix):
            continue

        file_path = Path(candidate)
        if not file_path.exists():
            continue

        try:
            if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
                logger.warning(
                    "Skipping oversized uploaded file %s during transcript extraction", filename
                )
                continue
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        original_name = filename[9:] if len(filename) > 9 and filename[8] == "-" else filename
        result = detect_transcript(original_name, content)
        if result.is_transcript:
            return content

    return None


async def _post_process_agent_response(
    *,
    session: UserSession,
    message: ChatMessage,
    project_name: str,
    pipeline_id: str | None,
    file_urls: list[str] | None,
    cached_projects: list | None,
    selected_project_id: str,
    user_content: str = "",
) -> ChatMessage:
    """Create proposals/recommendations from agent tool results.

    When the agent invokes an action tool, the result needs to be stored
    as a proposal or recommendation so that the confirm/reject flow works.
    """
    if not message.action_data or not message.action_type:
        return message

    action_data = message.action_data

    if message.action_type == ActionType.TASK_CREATE:
        proposed_description = action_data.get("proposed_description")
        if not isinstance(proposed_description, str) or not proposed_description.strip():
            proposed_description = user_content or ""

        proposal = AITaskProposal(
            session_id=session.session_id,
            original_input=user_content or proposed_description,
            proposed_title=action_data.get("proposed_title", "Untitled"),
            proposed_description=proposed_description,
            selected_pipeline_id=pipeline_id or None,
        )
        await _persistence.store_proposal(proposal)
        action_data["proposed_description"] = proposed_description
        action_data["proposal_id"] = str(proposal.proposal_id)
        action_data["status"] = ProposalStatus.PENDING.value
        message.action_data = action_data

    elif message.action_type == ActionType.ISSUE_CREATE:
        recommendation = IssueRecommendation(
            session_id=session.session_id,
            original_input=user_content or action_data.get("proposed_title", ""),
            original_context=user_content or action_data.get("proposed_title", ""),
            title=action_data.get("proposed_title", "Untitled"),
            user_story=action_data.get("user_story", ""),
            ui_ux_description=action_data.get("ui_ux_description", ""),
            functional_requirements=action_data.get("functional_requirements", []),
            technical_notes=action_data.get("technical_notes", ""),
        )
        recommendation.selected_pipeline_id = pipeline_id or None
        recommendation.file_urls = file_urls or []
        await _persistence.store_recommendation(recommendation)
        action_data["recommendation_id"] = str(recommendation.recommendation_id)
        action_data["status"] = RecommendationStatus.PENDING.value
        action_data["file_urls"] = file_urls
        action_data["pipeline_id"] = pipeline_id
        message.action_data = action_data

    elif message.action_type == ActionType.STATUS_UPDATE:
        # Look up status IDs from cached projects
        target_status = action_data.get("target_status", "")
        status_option_id = ""
        status_field_id = ""
        if cached_projects:
            for p in cached_projects:
                if p.project_id == selected_project_id:
                    for col in p.status_columns:
                        if col.name.lower() == target_status.lower():
                            status_option_id = col.option_id
                            status_field_id = col.field_id
                            target_status = col.name
                            break
                    break

        proposal = AITaskProposal(
            session_id=session.session_id,
            original_input=action_data.get("task_title", ""),
            proposed_title=action_data.get("task_title", ""),
            proposed_description=f"Move from '{action_data.get('current_status', '')}' to '{target_status}'",
        )
        await _persistence.store_proposal(proposal)
        action_data["proposal_id"] = str(proposal.proposal_id)
        action_data["status_option_id"] = status_option_id
        action_data["status_field_id"] = status_field_id
        action_data["status"] = ProposalStatus.PENDING.value
        message.action_data = action_data

    return message
