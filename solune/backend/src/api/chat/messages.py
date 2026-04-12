"""Message state, command dispatch, post-processing, and message/upload routes."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.api.auth import get_session_dep
from src.constants import DEFAULT_STATUS_COLUMNS
from src.dependencies import require_selected_project
from src.logging_utils import get_logger, handle_service_error
from src.middleware.rate_limit import limiter
from src.models.chat import (
    ActionType,
    ChatMessage,
    ChatMessageRequest,
    ChatMessagesResponse,
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
from src.services.cache import (
    cache,
    get_project_items_cache_key,
    get_user_projects_cache_key,
)
from src.services.chat_agent import get_chat_agent_service
from src.services.database import get_db

if TYPE_CHECKING:
    from src.services.ai_agent import AIAgentService

from src.api.chat.proposals import (
    _default_expires_at,
    store_proposal,
    store_recommendation,
)
from src.exceptions import ValidationError
from src.utils import resolve_repository, utcnow

logger = get_logger(__name__)
router = APIRouter()

# ── File upload validation constants ─────────────────────────────────────
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_FILES_PER_MESSAGE = 5
ALLOWED_IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
ALLOWED_DOC_TYPES = {".pdf", ".txt", ".md", ".csv", ".json", ".yaml", ".yml", ".vtt", ".srt"}
ALLOWED_ARCHIVE_TYPES = {".zip"}
BLOCKED_TYPES = {".exe", ".sh", ".bat", ".cmd", ".js", ".py", ".rb"}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_DOC_TYPES | ALLOWED_ARCHIVE_TYPES


class FileUploadResponse(BaseModel):
    """Response from file upload endpoint."""

    filename: str
    file_url: str
    file_size: int
    content_type: str


# ── SQLite-backed chat persistence ───────────────────────────────────────

_messages: dict[str, list[ChatMessage]] = {}
_locks: dict[str, asyncio.Lock] = {}

_PERSIST_MAX_RETRIES = 3
_PERSIST_BASE_DELAY = 0.1  # 100ms, 200ms, 400ms


def _get_lock(key: str) -> asyncio.Lock:
    """Return a per-key asyncio lock (lazy-created)."""
    if key not in _locks:
        _locks[key] = asyncio.Lock()
    return _locks[key]


async def _retry_persist(
    fn,
    *args,
    context: str = "",
    **kwargs,
) -> None:
    """Retry a persistence function with exponential backoff.

    Only *transient* SQLite errors (``OperationalError`` — e.g. database
    locked, busy, I/O) are retried.  Permanent errors (``IntegrityError``,
    ``ProgrammingError``, etc.) are re-raised immediately.

    Raises :class:`PersistenceError` after all retries are exhausted.
    """
    import sqlite3

    from src.exceptions import PersistenceError

    last_exc: Exception | None = None
    for attempt in range(1, _PERSIST_MAX_RETRIES + 1):
        try:
            await fn(*args, **kwargs)
            return
        except sqlite3.OperationalError as exc:
            last_exc = exc
            logger.warning(
                "Persist attempt %d/%d failed (%s): %s",
                attempt,
                _PERSIST_MAX_RETRIES,
                context,
                exc,
            )
            if attempt < _PERSIST_MAX_RETRIES:
                await asyncio.sleep(_PERSIST_BASE_DELAY * (2 ** (attempt - 1)))
        except Exception:
            raise  # Non-transient — fail fast

    raise PersistenceError(
        f"Failed to persist {context} after {_PERSIST_MAX_RETRIES} retries",
        details={"context": context, "last_error": str(last_exc)},
    )


async def _persist_message(session_id: UUID, message: ChatMessage) -> None:
    """Persist a chat message to SQLite with retry."""
    from src.services import chat_store

    db = get_db()
    await _retry_persist(
        chat_store.save_message,
        db,
        session_id=str(session_id),
        message_id=str(message.message_id),
        sender_type=message.sender_type.value,
        content=message.content,
        action_type=message.action_type.value if message.action_type else None,
        action_data=json.dumps(message.action_data) if message.action_data else None,
        conversation_id=str(message.conversation_id) if message.conversation_id else None,
        context=f"message:{message.message_id}",
    )


async def get_session_messages(session_id: UUID) -> list[ChatMessage]:
    """Get messages for a session from cache or SQLite."""
    key = str(session_id)
    cached = _messages.get(key)
    if cached is not None:
        return cached

    # Load from SQLite on cache miss
    try:
        from src.services import chat_store

        db = get_db()
        rows = await chat_store.get_messages(db, key)
        messages = []
        for row in rows:
            action_data = None
            if row.get("action_data"):
                try:
                    action_data = json.loads(row["action_data"])
                except (json.JSONDecodeError, TypeError):
                    action_data = None
            messages.append(
                ChatMessage(
                    message_id=row["message_id"],
                    session_id=row["session_id"],
                    sender_type=SenderType(row["sender_type"]),
                    content=row["content"],
                    action_type=ActionType(row["action_type"]) if row.get("action_type") else None,
                    action_data=action_data,
                )
            )
        _messages[key] = messages
        return messages
    except Exception:
        logger.warning("Failed to load messages from SQLite", exc_info=True)
        return []


async def add_message(session_id: UUID, message: ChatMessage) -> None:
    """Persist a message to SQLite, then update cache."""
    key = str(session_id)
    await _persist_message(session_id, message)
    async with _get_lock(key):
        if key not in _messages:
            _messages[key] = []
        _messages[key].append(message)


def _trigger_signal_delivery(
    session: UserSession,
    message: ChatMessage,
    project_name: str | None = None,
) -> None:
    """Fire-and-forget Signal delivery for assistant/system messages.

    Only delivers for non-user messages when the user has an active Signal connection.
    """
    if message.sender_type == SenderType.USER:
        return

    async def _deliver() -> None:
        try:
            from src.services.signal_delivery import deliver_chat_message_via_signal

            await deliver_chat_message_via_signal(
                github_user_id=session.github_user_id,
                message=message,
                project_name=project_name,
                project_id=session.selected_project_id,
            )
        except Exception as e:
            logger.debug("Signal delivery trigger failed (non-fatal): %s", e)

    try:
        from src.services.task_registry import task_registry

        task_registry.create_task(_deliver(), name="signal-delivery")
    except RuntimeError:
        pass  # No running event loop — skip silently


# ── Command dispatch helpers ─────────────────────────────────────────────


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
    await add_message(session.session_id, agent_msg)
    _trigger_signal_delivery(session, agent_msg, project_name)
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
        raw_name = file_url.rsplit("/", 1)[-1] if "/" in file_url else file_url
        filename = os.path.basename(raw_name)  # noqa: PTH119 — CodeQL sanitizer
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
                    "Skipping oversized uploaded file %s during transcript analysis", filename
                )
                continue
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.warning("Could not read uploaded file %s: %s", filename, exc)
            continue

        original_name = filename[9:] if len(filename) > 9 and filename[8] == "-" else filename
        result = detect_transcript(original_name, content)

        if not result.is_transcript:
            continue

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

            await store_recommendation(recommendation)

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
            await add_message(session.session_id, assistant_message)
            _trigger_signal_delivery(session, assistant_message, project_name)

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
            await add_message(session.session_id, error_message)
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

        await store_recommendation(recommendation)

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
        await add_message(session.session_id, assistant_message)
        _trigger_signal_delivery(session, assistant_message, project_name)

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
        await add_message(session.session_id, error_message)
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
        await add_message(session.session_id, error_message)
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
    await store_proposal(proposal)

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
    await add_message(session.session_id, assistant_message)
    _trigger_signal_delivery(session, assistant_message, project_name)
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
            await store_proposal(proposal)

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
            await add_message(session.session_id, assistant_message)
            _trigger_signal_delivery(session, assistant_message, project_name)
            return assistant_message

        except Exception as e:
            logger.error("Failed to generate metadata (ai_enhance=off): %s", e, exc_info=True)
            error_message = ChatMessage(
                session_id=session.session_id,
                sender_type=SenderType.ASSISTANT,
                content="I couldn't generate metadata for your request. Your input was preserved — please try again.",
            )
            await add_message(session.session_id, error_message)
            return error_message

    # Full AI pipeline
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
        await store_proposal(proposal)

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
        await add_message(session.session_id, assistant_message)
        _trigger_signal_delivery(session, assistant_message, project_name)
        return assistant_message

    except Exception as e:
        logger.error("Failed to generate task: %s", e, exc_info=True)

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
        await add_message(session.session_id, error_message)
        return error_message


async def _resolve_repository(session: UserSession) -> tuple[str, str]:
    """Resolve repository owner and name for issue creation."""
    project_id = require_selected_project(session)
    return await resolve_repository(session.access_token, project_id)


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
        await store_proposal(proposal)
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
        await store_recommendation(recommendation)
        action_data["recommendation_id"] = str(recommendation.recommendation_id)
        action_data["status"] = RecommendationStatus.PENDING.value
        action_data["file_urls"] = file_urls
        action_data["pipeline_id"] = pipeline_id
        message.action_data = action_data

    elif message.action_type == ActionType.STATUS_UPDATE:
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
        await store_proposal(proposal)
        action_data["proposal_id"] = str(proposal.proposal_id)
        action_data["status_option_id"] = status_option_id
        action_data["status_field_id"] = status_field_id
        action_data["status"] = ProposalStatus.PENDING.value
        message.action_data = action_data

    return message


# ── Message routes ───────────────────────────────────────────────────────


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
    selected_project_id = require_selected_project(session)

    # /plan must use the dedicated plan-mode toolset.
    if chat_request.content.strip().lower().startswith("/plan"):
        # Lazy import to avoid circular dependency with plans.py
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

    # Try to get AI service (optional)
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

    # ── Priority 0: #agent command ──────────
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

    # ── ai_enhance=False bypass ────────
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
    if chat_agent_service is not None:
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

    # ── Fallback: old priority dispatch ──
    if ai_service is None:
        raise RuntimeError("AI service is required for fallback priority dispatch")

    transcript_msg = await _handle_transcript_upload(
        session,
        ai_service,
        project_name,
        chat_request.pipeline_id,
        chat_request.file_urls,
    )
    if transcript_msg:
        return transcript_msg

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

    return await _handle_task_generation(
        session,
        content,
        ai_service,
        project_name,
        chat_request.ai_enhance,
        chat_request.pipeline_id,
    )


# ── Upload route ─────────────────────────────────────────────────────────


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),  # noqa: B008
    session: UserSession = Depends(get_session_dep),  # noqa: B008
) -> FileUploadResponse | JSONResponse:
    """Upload a file for attachment to a future GitHub Issue.

    Validates file size and type, then stores the file temporarily.
    The returned URL can be embedded in issue bodies.
    """
    if not file.filename:
        return JSONResponse(
            status_code=400,
            content={"filename": "", "error": "No file provided", "error_code": "no_file"},
        )

    # Validate file type
    ext = Path(file.filename).suffix.lower()
    if ext in BLOCKED_TYPES:
        return JSONResponse(
            status_code=415,
            content={
                "filename": file.filename,
                "error": f"File type {ext} is not supported",
                "error_code": "unsupported_type",
            },
        )
    if ext not in ALLOWED_TYPES:
        return JSONResponse(
            status_code=415,
            content={
                "filename": file.filename,
                "error": f"File type {ext} is not supported",
                "error_code": "unsupported_type",
            },
        )

    # Read file content and validate size
    content = await file.read()
    if len(content) == 0:
        return JSONResponse(
            status_code=400,
            content={
                "filename": file.filename,
                "error": "Empty file - cannot attach a file with no content",
                "error_code": "empty_file",
            },
        )
    if len(content) > MAX_FILE_SIZE_BYTES:
        return JSONResponse(
            status_code=413,
            content={
                "filename": file.filename,
                "error": "File exceeds the 10 MB size limit",
                "error_code": "file_too_large",
            },
        )

    upload_id = str(uuid4())[:8]
    cleaned = file.filename.replace("\x00", "")
    basename = Path(cleaned).name
    if not basename:
        basename = "upload"
    safe_filename = f"{upload_id}-{basename}"

    upload_dir = Path(tempfile.gettempdir()) / "chat-uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / safe_filename

    # Verify resolved path stays inside upload_dir (defense-in-depth)
    if not file_path.resolve().is_relative_to(upload_dir.resolve()):
        return JSONResponse(
            status_code=400,
            content={
                "filename": file.filename,
                "error": "Invalid filename",
                "error_code": "invalid_filename",
            },
        )

    file_path.write_bytes(content)

    file_url = f"/api/v1/chat/uploads/{safe_filename}"

    return FileUploadResponse(
        filename=file.filename,
        file_url=file_url,
        file_size=len(content),
        content_type=file.content_type or "application/octet-stream",
    )
