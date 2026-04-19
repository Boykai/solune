"""Chat API endpoints."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Annotated, Any, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, File, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from src.api.auth import get_session_dep
from src.constants import (
    DEFAULT_STATUS_COLUMNS,
    GITHUB_ISSUE_BODY_MAX_LENGTH,
)
from src.dependencies import get_connection_manager, get_github_service, require_selected_project
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
    ProposalConfirmRequest,
    ProposalStatus,
    RecommendationStatus,
)
from src.models.user import UserSession
from src.models.workflow import WorkflowConfiguration
from src.services import ai_utilities
from src.services import chat_store as _chat_store_module
from src.services.cache import (
    cache,
    get_project_items_cache_key,
    get_user_projects_cache_key,
)
from src.services.chat_agent import get_chat_agent_service
from src.services.database import get_db
from src.services.github_projects.service import GitHubProjectsService
from src.services.pipeline_launcher import start_pipeline
from src.services.settings_store import get_effective_user_settings
from src.services.websocket import ConnectionManager
from src.services.workflow_orchestrator import (
    WorkflowContext,
    get_agent_slugs,
    get_workflow_config,
    get_workflow_orchestrator,
    set_workflow_config,
)
from src.utils import resolve_repository, utcnow

logger = get_logger(__name__)
router = APIRouter()

# Several legacy services declare bare ``dict`` in their signatures, which the
# strict floor flags as partially unknown. Re-binding the service objects to
# Any-typed locals lets us call them without method-access errors.
_chat_store_any: Any = _chat_store_module
_ai_utilities_any: Any = ai_utilities

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
#
# Chat messages, proposals, and recommendations are persisted to SQLite
# via _chat_store_any.py (tables from 023_consolidated_schema.sql).  In-memory
# dicts act as a read-through cache backed by SQLite (single source of truth).
# Writes go to SQLite first, then update the cache on success.

_messages: dict[str, list[ChatMessage]] = {}
_proposals: dict[str, AITaskProposal] = {}
_recommendations: dict[str, IssueRecommendation] = {}
_locks: dict[str, asyncio.Lock] = {}

_PERSIST_MAX_RETRIES = 3
_PERSIST_BASE_DELAY = 0.1  # 100ms, 200ms, 400ms


def _get_lock(key: str) -> asyncio.Lock:
    """Return a per-key asyncio lock (lazy-created)."""
    if key not in _locks:
        _locks[key] = asyncio.Lock()
    return _locks[key]


async def _retry_persist(
    fn: Callable[..., Awaitable[None]],
    *args: Any,
    context: str = "",
    **kwargs: Any,
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

    db = get_db()
    await _retry_persist(
        _chat_store_any.save_message,
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


async def _persist_proposal(proposal: AITaskProposal) -> None:
    """Persist a proposal to SQLite with retry."""

    db = get_db()
    await _retry_persist(
        _chat_store_any.save_proposal,
        db,
        session_id=str(proposal.session_id),
        proposal_id=str(proposal.proposal_id),
        original_input=proposal.original_input,
        proposed_title=proposal.proposed_title,
        proposed_description=proposal.proposed_description,
        status=proposal.status.value,
        edited_title=proposal.edited_title,
        edited_description=proposal.edited_description,
        created_at=proposal.created_at.isoformat(),
        expires_at=proposal.expires_at.isoformat(),
        file_urls=proposal.file_urls or None,
        selected_pipeline_id=proposal.selected_pipeline_id,
        context=f"proposal:{proposal.proposal_id}",
    )


async def _persist_recommendation(recommendation: IssueRecommendation) -> None:
    """Persist a recommendation to SQLite with retry."""

    db = get_db()
    await _retry_persist(
        _chat_store_any.save_recommendation,
        db,
        session_id=str(recommendation.session_id),
        recommendation_id=str(recommendation.recommendation_id),
        data=json.dumps(recommendation.model_dump(mode="json")),
        status=recommendation.status.value,
        file_urls=recommendation.file_urls or None,
        context=f"recommendation:{recommendation.recommendation_id}",
    )


async def store_proposal(proposal: AITaskProposal) -> None:
    """Persist a proposal to SQLite, then update cache."""
    await _persist_proposal(proposal)
    _proposals[str(proposal.proposal_id)] = proposal


async def store_recommendation(recommendation: IssueRecommendation) -> None:
    """Persist a recommendation to SQLite, then update cache."""
    await _persist_recommendation(recommendation)
    _recommendations[str(recommendation.recommendation_id)] = recommendation


async def get_proposal(proposal_id: str) -> AITaskProposal | None:
    """Get a proposal by ID from cache or SQLite."""
    # Fast path: in-memory cache
    proposal = _proposals.get(proposal_id)
    if proposal is not None:
        return proposal

    # Slow path: load from SQLite
    try:
        db = get_db()
        row = await _chat_store_any.get_proposal_by_id(db, proposal_id)
        if row is None:
            return None
        from datetime import datetime as _dt

        raw_expires = row["expires_at"] or _default_expires_at(row["created_at"])
        parsed_expires = (
            _dt.fromisoformat(raw_expires) if isinstance(raw_expires, str) else raw_expires
        )

        proposal = AITaskProposal(
            proposal_id=row["proposal_id"],
            session_id=row["session_id"],
            original_input=row["original_input"],
            proposed_title=row["proposed_title"],
            proposed_description=row["proposed_description"],
            status=ProposalStatus(row["status"]),
            edited_title=row.get("edited_title"),
            edited_description=row.get("edited_description"),
            file_urls=row.get("file_urls", []),
            selected_pipeline_id=row.get("selected_pipeline_id"),
            created_at=row["created_at"],
            expires_at=parsed_expires,
        )
        _proposals[proposal_id] = proposal
        return proposal
    except Exception:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
        logger.warning("Failed to load proposal from SQLite", exc_info=True)
        return None


async def get_recommendation(recommendation_id: str) -> IssueRecommendation | None:
    """Get a recommendation by ID from cache or SQLite."""
    # Fast path: in-memory cache
    rec = _recommendations.get(recommendation_id)
    if rec is not None:
        return rec

    # Slow path: load from SQLite
    try:
        db = get_db()
        row = await _chat_store_any.get_recommendation_by_id(db, recommendation_id)
        if row is None:
            return None
        data = json.loads(row["data"]) if isinstance(row["data"], str) else row["data"]
        rec = IssueRecommendation.model_validate(data)
        rec.status = RecommendationStatus(
            _chat_store_any.recommendation_status_from_db(row["status"])
        )
        _recommendations[str(rec.recommendation_id)] = rec
        return rec
    except Exception:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
        logger.warning("Failed to load recommendation from SQLite", exc_info=True)
        return None


def _default_expires_at(created_at_str: str) -> str:
    """Compute a fallback expires_at when the stored value is NULL."""
    from datetime import datetime, timedelta

    try:
        created = datetime.fromisoformat(created_at_str)
        return (created + timedelta(minutes=10)).isoformat()
    except (ValueError, TypeError):
        return created_at_str


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
    except Exception as exc:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
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
        filename = os.path.basename(raw_name)  # noqa: PTH119 — reason: CodeQL-recognised path sanitizer; pathlib.PurePath.name not recognised by CodeQL
        if not filename:
            continue

        # Build the candidate path and normalise it so CodeQL can verify
        # the subsequent prefix check neutralises any traversal attempt.
        candidate = os.path.normpath(os.path.join(str(upload_dir), filename))  # noqa: PTH118 — reason: CodeQL-recognised path normalisation for traversal check
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
        except Exception as exc:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
            logger.warning("Could not read uploaded file %s: %s", filename, exc)
            continue

        # Strip the 8-char UUID prefix added during upload (format: "abcd1234-original.ext")
        original_name = filename[9:] if len(filename) > 9 and filename[8] == "-" else filename
        result = detect_transcript(original_name, content)

        if not result.is_transcript:
            continue

        # Transcript detected — run through the Transcribe agent
        try:
            metadata_context: dict[str, Any] | None = None
            try:
                owner, repo = await _resolve_repository(session)
                from src.services.github_projects import github_projects_service
                from src.services.metadata_service import MetadataService

                metadata_svc = MetadataService(github_service=github_projects_service)
                ctx = await metadata_svc.get_or_fetch(session.access_token, owner, repo)
                metadata_context = ctx.model_dump()
            except Exception as md_err:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
                logger.warning("Metadata fetch for transcript prompt failed: %s", md_err)

            recommendation = await _ai_utilities_any.analyze_transcript(
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
    project_name: str,
    pipeline_id: str | None,
    ai_enhance: bool,
    file_urls: list[str] | None,
) -> ChatMessage | None:
    """Priority 1: Detect feature request intent and generate issue recommendation.

    Returns an assistant ChatMessage if the intent was a feature request, None otherwise.
    """
    try:
        is_feature_request = await _ai_utilities_any.detect_feature_request_intent(
            content, github_token=session.access_token
        )
    except Exception as e:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
        logger.warning("Feature request detection failed: %s", e)
        is_feature_request = False

    if not is_feature_request:
        return None

    try:
        metadata_context: dict[str, Any] | None = None
        try:
            owner, repo = await _resolve_repository(session)
            from src.services.github_projects import github_projects_service
            from src.services.metadata_service import MetadataService

            metadata_svc = MetadataService(github_service=github_projects_service)
            ctx = await metadata_svc.get_or_fetch(session.access_token, owner, repo)
            metadata_context = ctx.model_dump()
        except Exception as md_err:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
            logger.warning("Metadata fetch for prompt injection failed: %s", md_err)

        recommendation = await _ai_utilities_any.generate_issue_recommendation(
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
    current_tasks: list[Any],
    project_columns: list[str],
    cached_projects: list[Any] | None,
    selected_project_id: str,
    project_name: str,
) -> ChatMessage | None:
    """Priority 2: Parse status change request and create proposal.

    Returns an assistant ChatMessage if a status change was detected, None otherwise.
    """
    status_change = await _ai_utilities_any.parse_status_change_request(
        user_input=content,
        available_tasks=[t.title for t in current_tasks],
        available_statuses=(project_columns or DEFAULT_STATUS_COLUMNS),
        github_token=session.access_token,
    )
    if not status_change:
        return None

    target_task = _ai_utilities_any.identify_target_task(
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
    project_name: str,
    ai_enhance: bool,
    pipeline_id: str | None,
) -> ChatMessage:
    """Priority 3: Generate task from description (metadata-only or full AI).

    Always returns a ChatMessage (success or error).
    """
    if not ai_enhance:
        try:
            title = await _ai_utilities_any.generate_title_from_description(
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

    # Full AI pipeline: generate both title and description via AI
    try:
        generated = await _ai_utilities_any.generate_task_from_description(
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
        await add_message(session.session_id, error_message)
        return error_message


async def _resolve_repository(session: UserSession) -> tuple[str, str]:
    """Resolve repository owner and name for issue creation."""
    project_id = require_selected_project(session)
    return await resolve_repository(session.access_token, project_id)


async def get_session_messages(session_id: UUID) -> list[ChatMessage]:
    """Get messages for a session from cache or SQLite."""
    key = str(session_id)
    cached = _messages.get(key)
    if cached is not None:
        return cached

    # Load from SQLite on cache miss
    try:
        db = get_db()
        rows = cast("list[dict[str, Any]]", await _chat_store_any.get_messages(db, key))
        messages: list[ChatMessage] = []
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
    except Exception:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
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
        except Exception as e:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
            logger.debug("Signal delivery trigger failed (non-fatal): %s", e)

    try:
        from src.services.task_registry import task_registry

        task_registry.create_task(_deliver(), name="signal-delivery")
    except RuntimeError:
        pass  # No running event loop — skip silently


# ── Conversation CRUD ────────────────────────────────────────────


@router.post("/conversations", status_code=201)
async def create_conversation(
    session: Annotated[UserSession, Depends(get_session_dep)],
    body: ConversationCreateRequest = Body(default_factory=ConversationCreateRequest),  # noqa: B008 — reason: FastAPI Depends() pattern — evaluated per-request, not at import time
) -> Conversation:
    """Create a new conversation for the current session."""

    db = get_db()
    conv_id = str(uuid4())
    row = await _chat_store_any.save_conversation(
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

    db = get_db()
    rows = await _chat_store_any.get_conversations(db, str(session.session_id))
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

    db = get_db()
    # Verify ownership before updating
    existing = await _chat_store_any.get_conversation_by_id(db, conversation_id)
    if existing is None:
        raise NotFoundError(f"Conversation {conversation_id} not found")
    if existing["session_id"] != str(session.session_id):
        raise NotFoundError(f"Conversation {conversation_id} not found")
    row = await _chat_store_any.update_conversation(db, conversation_id, body.title)
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

    db = get_db()
    # Verify ownership before deleting
    existing = await _chat_store_any.get_conversation_by_id(db, conversation_id)
    if existing is None:
        raise NotFoundError(f"Conversation {conversation_id} not found")
    if existing["session_id"] != str(session.session_id):
        raise NotFoundError(f"Conversation {conversation_id} not found")
    await _chat_store_any.delete_conversation(db, conversation_id)
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

    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    key = str(session.session_id)

    db = get_db()
    total = await _chat_store_any.count_messages(db, key, conversation_id=conversation_id)
    rows = await _chat_store_any.get_messages(
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
        db = get_db()
        await _chat_store_any.clear_messages(db, key, conversation_id=conversation_id)
    except Exception:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
        logger.warning("Failed to clear messages from SQLite", exc_info=True)
    return {"message": "Chat history cleared"}


async def _validate_chat_conversation(
    session: UserSession,
    conversation_id: UUID | None,
) -> None:
    """Ensure the requested conversation exists and belongs to the active session."""
    if conversation_id is None:
        return

    try:
        db = get_db()
        conversation = await _chat_store_any.get_conversation_by_id(db, str(conversation_id))
    except Exception as exc:  # noqa: BLE001 — reason: boundary handler; logs and re-raises as safe AppException
        handle_service_error(exc, "validate conversation")

    if conversation is None or conversation["session_id"] != str(session.session_id):
        raise NotFoundError(f"Conversation {conversation_id} not found")


async def _validate_chat_pipeline(
    session: UserSession,
    project_id: str,
    pipeline_id: str | None,
) -> None:
    """Ensure any selected pipeline still exists and is accessible."""
    if not pipeline_id:
        return

    from src.services.pipelines.service import PipelineService

    try:
        db = get_db()
        pipeline_svc = PipelineService(db)
        pipeline = await pipeline_svc.get_pipeline(
            project_id,
            pipeline_id,
            github_user_id=session.github_user_id,
        )
        if pipeline is None:
            raise ValidationError(f"Pipeline not found: {pipeline_id}")
    except ValidationError:
        raise
    except Exception as exc:  # noqa: BLE001 — reason: boundary handler; logs and re-raises as safe AppException
        handle_service_error(exc, "validate pipeline")


async def _validate_chat_request_context(
    session: UserSession,
    selected_project_id: str,
    chat_request: ChatMessageRequest,
) -> None:
    """Validate request-scoped chat references before persisting any messages."""
    await _validate_chat_conversation(session, chat_request.conversation_id)
    await _validate_chat_pipeline(session, selected_project_id, chat_request.pipeline_id)


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
        return await send_plan_message(request, chat_request, session)

    await _validate_chat_request_context(session, selected_project_id, chat_request)

    # Check that AI provider is configured (utility functions handle completion internally)
    ai_available = False
    try:
        from src.config import get_settings as _get_settings

        _settings = _get_settings()
        if _settings.ai_provider in ("copilot", "azure_openai"):
            ai_available = True
    except Exception:  # noqa: BLE001 — reason: mixed exception surface; operation failure is non-critical
        pass

    # Try to get the new ChatAgentService
    chat_agent_service = None
    try:
        chat_agent_service = get_chat_agent_service()
    except Exception:  # noqa: BLE001 — reason: mixed exception surface; operation failure is non-critical
        pass

    if not ai_available and chat_agent_service is None:
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
    current_tasks: list[Any] = cache.get(tasks_cache_key) or []

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
        if ai_available:
            return await _handle_task_generation(
                session,
                content,
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
    if not ai_available:
        raise RuntimeError("AI service is required for fallback priority dispatch")

    # Priority 0.5: Transcript upload → issue recommendation
    transcript_msg = await _handle_transcript_upload(
        session,
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
        filename = os.path.basename(raw_name)  # noqa: PTH119 — reason: CodeQL-recognised path sanitizer; pathlib.PurePath.name not recognised by CodeQL
        if not filename:
            continue

        candidate = os.path.normpath(os.path.join(str(upload_dir), filename))  # noqa: PTH118 — reason: CodeQL-recognised path normalisation for traversal check
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
        except Exception:  # noqa: BLE001 — reason: mixed exception surface; operation failure is non-critical
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
    cached_projects: list[Any] | None,
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
        await store_proposal(proposal)
        action_data["proposal_id"] = str(proposal.proposal_id)
        action_data["status_option_id"] = status_option_id
        action_data["status_field_id"] = status_field_id
        action_data["status"] = ProposalStatus.PENDING.value
        message.action_data = action_data

    return message


# ── Streaming endpoint (US4) ────────────────────────────────────────────


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

    await _validate_chat_request_context(session, selected_project_id, chat_request)

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
    except Exception:  # noqa: BLE001 — reason: best-effort operation; returns fallback value on failure
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
    current_tasks: list[Any] = cache.get(tasks_cache_key) or []

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


@router.post("/proposals/{proposal_id}/confirm", response_model=AITaskProposal)
async def confirm_proposal(
    proposal_id: str,
    request: ProposalConfirmRequest | None,
    session: Annotated[UserSession, Depends(get_session_dep)],
    github_projects_service: GitHubProjectsService = Depends(get_github_service),  # noqa: B008 — reason: FastAPI Depends() pattern — evaluated per-request, not at import time
    connection_manager: ConnectionManager = Depends(get_connection_manager),  # noqa: B008 — reason: FastAPI Depends() pattern — evaluated per-request, not at import time
) -> AITaskProposal:
    """Confirm an AI task proposal and create the task."""
    proposal = await get_proposal(proposal_id)

    if not proposal:
        raise NotFoundError(f"Proposal not found: {proposal_id}")

    if str(proposal.session_id) != str(session.session_id):
        raise NotFoundError(f"Proposal not found: {proposal_id}")

    if proposal.is_expired:
        proposal.status = ProposalStatus.CANCELLED
        try:
            db = get_db()
            await _chat_store_any.update_proposal_status(
                db, proposal_id, ProposalStatus.CANCELLED.value
            )
        except Exception:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
            logger.warning("Failed to update expired proposal status in SQLite", exc_info=True)
        raise ValidationError("Proposal has expired")

    if proposal.status != ProposalStatus.PENDING:
        raise ValidationError(f"Proposal already {proposal.status.value}")

    # Apply edits if provided
    if request:
        if request.edited_title:
            proposal.edited_title = request.edited_title
            proposal.status = ProposalStatus.EDITED
        if request.edited_description:
            proposal.edited_description = request.edited_description
            if proposal.status != ProposalStatus.EDITED:
                proposal.status = ProposalStatus.EDITED

    # Resolve repository info for issue creation
    owner, repo = await _resolve_repository(session)

    project_id = require_selected_project(session)

    # Validate description does not exceed GitHub API limit before attempting
    # issue creation.  This check lives outside the try/except below so that the
    # structured ValidationError (with body_length/max_length details) is never
    # caught by the broad ``except Exception`` handler and re-wrapped — which
    # would drop the ``details`` payload and return a misleading error message.
    body = proposal.final_description or ""

    # Embed file attachments in issue body
    from src.attachment_formatter import format_attachments_markdown

    body += format_attachments_markdown(proposal.file_urls)

    if len(body) > GITHUB_ISSUE_BODY_MAX_LENGTH:
        raise ValidationError(
            f"Issue body is {len(body)} characters, which exceeds the "
            f"GitHub API limit of {GITHUB_ISSUE_BODY_MAX_LENGTH} characters. "
            "Please shorten the description.",
            details={
                "body_length": len(body),
                "max_length": GITHUB_ISSUE_BODY_MAX_LENGTH,
            },
        )

    # Create the issue in GitHub
    try:
        # Step 1: Create a real GitHub Issue via REST API
        issue = cast(
            "dict[str, Any]",
            await cast(Any, github_projects_service).create_issue(
                access_token=session.access_token,
                owner=owner,
                repo=repo,
                title=proposal.final_title,
                body=body,
                labels=[],
            ),
        )

        issue_number = issue["number"]
        issue_node_id = issue["node_id"]
        issue_url = issue["html_url"]
        issue_database_id = issue["id"]  # Integer database ID for REST API fallback

        # Step 2: Add the issue to the project
        item_id = await cast(Any, github_projects_service).add_issue_to_project(
            access_token=session.access_token,
            project_id=project_id,
            issue_node_id=issue_node_id,
            issue_database_id=issue_database_id,
        )

        proposal.status = ProposalStatus.CONFIRMED
        try:
            db = get_db()
            await _chat_store_any.update_proposal_status(
                db,
                proposal_id,
                ProposalStatus.CONFIRMED.value,
                edited_title=proposal.edited_title,
                edited_description=proposal.edited_description,
            )
        except Exception:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
            logger.warning("Failed to update proposal status in SQLite", exc_info=True)

        # Invalidate cache
        cache.delete(get_project_items_cache_key(project_id))

        # Broadcast WebSocket message to connected clients
        await cast(Any, connection_manager).broadcast_to_project(
            project_id,
            {
                "type": "task_created",
                "task_id": item_id,
                "title": proposal.final_title,
                "issue_number": issue_number,
                "issue_url": issue_url,
            },
        )

        # Add confirmation message
        confirm_message = ChatMessage(
            session_id=session.session_id,
            sender_type=SenderType.SYSTEM,
            content=f"✅ Issue created: **{proposal.final_title}** ([#{issue_number}]({issue_url}))",
            action_type=ActionType.TASK_CREATE,
            action_data={
                "proposal_id": str(proposal.proposal_id),
                "task_id": item_id,
                "issue_number": issue_number,
                "issue_url": issue_url,
                "status": ProposalStatus.CONFIRMED.value,
            },
        )
        await add_message(session.session_id, confirm_message)
        _trigger_signal_delivery(session, confirm_message)

        logger.info(
            "Created issue #%d from proposal %s: %s",
            issue_number,
            proposal_id,
            proposal.final_title,
        )

        # Step 3: Set up workflow config and assign agent for Backlog status
        try:
            from src.config import get_settings

            settings = get_settings()

            config = await get_workflow_config(project_id)
            if not config:
                config = WorkflowConfiguration(
                    project_id=project_id,
                    repository_owner=owner,
                    repository_name=repo,
                    copilot_assignee=settings.default_assignee,
                )
                await set_workflow_config(
                    project_id,
                    config,
                )
            else:
                config.repository_owner = owner
                config.repository_name = repo
                if not config.copilot_assignee:
                    config.copilot_assignee = settings.default_assignee

            # Apply explicitly selected pipeline first, then project/user/default fallback
            from src.services.workflow_orchestrator.config import (
                PipelineResolutionResult,
                load_pipeline_as_agent_mappings,
                resolve_project_pipeline_mappings,
            )

            if proposal.selected_pipeline_id:
                selected_pipeline = await load_pipeline_as_agent_mappings(
                    project_id,
                    proposal.selected_pipeline_id,
                    github_user_id=session.github_user_id,
                )
                if selected_pipeline is not None:
                    (
                        selected_mappings,
                        selected_pipeline_name,
                        selected_exec_modes,
                        selected_grp_mappings,
                    ) = selected_pipeline
                    pipeline_result = PipelineResolutionResult(
                        agent_mappings=selected_mappings,
                        source="pipeline",
                        pipeline_name=selected_pipeline_name,
                        pipeline_id=proposal.selected_pipeline_id,
                        stage_execution_modes=selected_exec_modes,
                        group_mappings=selected_grp_mappings,
                    )
                else:
                    logger.warning(
                        "Selected pipeline %s not found for proposal %s on project %s; falling back",
                        proposal.selected_pipeline_id,
                        proposal_id,
                        project_id,
                    )
                    pipeline_result = await resolve_project_pipeline_mappings(
                        project_id, session.github_user_id
                    )
            else:
                pipeline_result = await resolve_project_pipeline_mappings(
                    project_id, session.github_user_id
                )

            if pipeline_result.agent_mappings:
                logger.info(
                    "Applying %s agent pipeline mappings for project=%s (pipeline=%s)",
                    pipeline_result.source,
                    project_id,
                    pipeline_result.pipeline_name or "N/A",
                )
                config.agent_mappings = pipeline_result.agent_mappings
                await set_workflow_config(project_id, config)

            # Populate pipeline metadata on the proposal response
            proposal.pipeline_name = pipeline_result.pipeline_name
            proposal.pipeline_source = pipeline_result.source

            # Set issue status to Backlog on the project
            backlog_status = config.status_backlog
            await cast(Any, github_projects_service).update_item_status_by_name(
                access_token=session.access_token,
                project_id=project_id,
                item_id=item_id,
                status_name=backlog_status,
            )
            logger.info(
                "Set issue #%d status to '%s' on project",
                issue_number,
                backlog_status,
            )

            # Assign the first Backlog agent
            try:
                effective_user_settings = await get_effective_user_settings(
                    get_db(), session.github_user_id
                )
                user_chat_model = effective_user_settings.ai.model
                user_agent_model = effective_user_settings.ai.agent_model
                user_reasoning_effort = effective_user_settings.ai.reasoning_effort
            except Exception:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
                logger.warning(
                    "Could not load effective user settings for session %s; user_chat_model left empty",
                    session.session_id,
                )
                user_chat_model = ""
                user_agent_model = ""
                user_reasoning_effort = ""

            ctx = WorkflowContext(
                session_id=str(session.session_id),
                project_id=project_id,
                access_token=session.access_token,
                repository_owner=owner,
                repository_name=repo,
                selected_pipeline_id=proposal.selected_pipeline_id,
                config=config,
                user_chat_model=user_chat_model,
                user_agent_model=user_agent_model,
                user_reasoning_effort=user_reasoning_effort,
            )
            ctx.issue_id = issue_node_id
            ctx.issue_number = issue_number
            ctx.project_item_id = item_id

            orchestrator = get_workflow_orchestrator()

            launch_result = await start_pipeline(
                ctx,
                config,
                orchestrator,
                caller="confirm_proposal",
                get_agent_slugs_fn=get_agent_slugs,
            )

            # Send agent_assigned WebSocket notification
            if launch_result.initial_agent and not launch_result.error:
                await cast(Any, connection_manager).broadcast_to_project(
                    project_id,
                    {
                        "type": "agent_assigned",
                        "issue_number": issue_number,
                        "agent_name": launch_result.initial_agent,
                        "status": launch_result.status_name,
                    },
                )

        except Exception as e:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
            logger.warning(
                "Issue #%d created but agent assignment failed: %s",
                issue_number,
                e,
            )

        return proposal

    except ValidationError:
        raise
    except Exception as e:  # noqa: BLE001 — reason: boundary handler; logs and re-raises as safe AppException
        handle_service_error(e, "create issue from proposal", ValidationError)


@router.delete("/proposals/{proposal_id}")
async def cancel_proposal(
    proposal_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
) -> dict[str, Any]:
    """Cancel an AI task proposal."""
    proposal = await get_proposal(proposal_id)

    if not proposal:
        raise NotFoundError(f"Proposal not found: {proposal_id}")

    if str(proposal.session_id) != str(session.session_id):
        raise NotFoundError(f"Proposal not found: {proposal_id}")

    proposal.status = ProposalStatus.CANCELLED
    try:
        db = get_db()
        await _chat_store_any.update_proposal_status(
            db, proposal_id, ProposalStatus.CANCELLED.value
        )
    except Exception:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
        logger.warning("Failed to update proposal status in SQLite", exc_info=True)

    # Add cancellation message
    cancel_message = ChatMessage(
        session_id=session.session_id,
        sender_type=SenderType.SYSTEM,
        content="Task creation cancelled.",
    )
    await add_message(session.session_id, cancel_message)

    return {"message": "Proposal cancelled"}


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),  # noqa: B008 — reason: FastAPI Depends() pattern — evaluated per-request, not at import time
    session: UserSession = Depends(get_session_dep),  # noqa: B008 — reason: FastAPI Depends() pattern — evaluated per-request, not at import time
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

    # Store files in a temporary upload directory and serve via a local URL.
    # This is intentional for self-hosted single-instance deployments where
    # simplicity outweighs cloud storage benefits.  Files reside in the OS
    # temp directory and are cleaned up automatically on system restart.
    # For multi-instance or cloud deployments, migrate to object storage
    # (e.g. S3 / GCS) in a dedicated specification.
    upload_id = str(uuid4())[:8]
    # Sanitise the original filename to prevent path-traversal attacks:
    # strip null bytes first (could confuse Path parsing on some platforms),
    # then strip directory components so e.g. "../../etc/passwd" becomes "passwd".
    cleaned = file.filename.replace("\x00", "")
    basename = Path(cleaned).name
    if not basename:
        basename = "upload"
    safe_filename = f"{upload_id}-{basename}"

    # Store in a temporary directory
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

    # Generate a file URL — in production this would be a GitHub CDN URL
    file_url = f"/api/v1/chat/uploads/{safe_filename}"

    return FileUploadResponse(
        filename=file.filename,
        file_url=file_url,
        file_size=len(content),
        content_type=file.content_type or "application/octet-stream",
    )


# ── Plan mode endpoints ──────────────────────────────────────────────────


@router.post("/messages/plan")
@limiter.limit("10/minute")
async def send_plan_message(
    request: Request,
    chat_request: ChatMessageRequest,
    session: Annotated[UserSession, Depends(get_session_dep)],
):
    """Enter plan mode (non-streaming).

    The user's message is treated as a feature description for the plan agent.
    """
    selected_project_id = require_selected_project(session)

    content = chat_request.content.strip()
    # Strip /plan prefix if present
    if content.lower().startswith("/plan"):
        content = content[5:].strip()
    if not content:
        return JSONResponse(
            status_code=400,
            content={"detail": "Please provide a feature description after /plan."},
        )

    await _validate_chat_request_context(session, selected_project_id, chat_request)

    try:
        owner, repo = await _resolve_repository(session)
    except Exception:  # noqa: BLE001 — reason: best-effort operation; returns fallback value on failure
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
    except Exception:  # noqa: BLE001 — reason: best-effort operation; returns fallback value on failure
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

    result = await chat_agent_svc.run_plan(
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
    )
    result.conversation_id = chat_request.conversation_id
    await add_message(session.session_id, result)
    return result


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

    await _validate_chat_request_context(session, selected_project_id, chat_request)

    try:
        owner, repo = await _resolve_repository(session)
    except Exception:  # noqa: BLE001 — reason: best-effort operation; returns fallback value on failure
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
    except Exception:  # noqa: BLE001 — reason: best-effort operation; returns fallback value on failure
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


@router.get("/plans/{plan_id}")
async def get_plan_endpoint(
    plan_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
):
    """Retrieve a plan with all steps."""
    from src.models.plan import PlanResponse, PlanStepResponse

    db = get_db()
    plan = await _chat_store_any.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    # Verify the plan belongs to this session
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    steps = [
        PlanStepResponse(
            step_id=s["step_id"],
            position=s["position"],
            title=s["title"],
            description=s["description"],
            dependencies=s.get("dependencies", []),
            approval_status=s.get("approval_status", "pending"),
            issue_number=s.get("issue_number"),
            issue_url=s.get("issue_url"),
        )
        for s in plan.get("steps", [])
    ]
    return PlanResponse(
        plan_id=plan["plan_id"],
        session_id=plan["session_id"],
        title=plan["title"],
        summary=plan["summary"],
        status=plan["status"],
        version=plan.get("version", 1),
        project_id=plan["project_id"],
        project_name=plan["project_name"],
        repo_owner=plan["repo_owner"],
        repo_name=plan["repo_name"],
        parent_issue_number=plan.get("parent_issue_number"),
        parent_issue_url=plan.get("parent_issue_url"),
        steps=steps,
        created_at=plan["created_at"],
        updated_at=plan["updated_at"],
    )


@router.patch("/plans/{plan_id}")
async def update_plan_endpoint(
    plan_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
    request: Request,
):
    """Update plan metadata (title and/or summary)."""
    from src.models.plan import PlanResponse, PlanStepResponse, PlanUpdateRequest

    body = await request.json()
    update_req = PlanUpdateRequest(**body)

    db = get_db()
    plan = await _chat_store_any.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["status"] != "draft":
        return JSONResponse(
            status_code=400,
            content={"detail": "Only draft plans can be updated."},
        )

    await _chat_store_any.update_plan(
        db, plan_id, title=update_req.title, summary=update_req.summary
    )
    updated = await _chat_store_any.get_plan(db, plan_id)
    if updated is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found after update."})
    steps = [
        PlanStepResponse(
            step_id=s["step_id"],
            position=s["position"],
            title=s["title"],
            description=s["description"],
            dependencies=s.get("dependencies", []),
            issue_number=s.get("issue_number"),
            issue_url=s.get("issue_url"),
        )
        for s in updated.get("steps", [])
    ]
    return PlanResponse(
        plan_id=updated["plan_id"],
        session_id=updated["session_id"],
        title=updated["title"],
        summary=updated["summary"],
        status=updated["status"],
        project_id=updated["project_id"],
        project_name=updated["project_name"],
        repo_owner=updated["repo_owner"],
        repo_name=updated["repo_name"],
        parent_issue_number=updated.get("parent_issue_number"),
        parent_issue_url=updated.get("parent_issue_url"),
        steps=steps,
        created_at=updated["created_at"],
        updated_at=updated["updated_at"],
    )


@router.post("/plans/{plan_id}/approve")
async def approve_plan_endpoint(
    plan_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
):
    """Approve a plan and launch it through the shared parent-issue pipeline flow."""
    from src.api.pipelines import execute_pipeline_launch
    from src.models.plan import PlanApprovalResponse, PlanStepResponse
    from src.services.plan_issue_service import format_plan_issue_markdown

    db = get_db()
    plan = await _chat_store_any.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["status"] != "draft":
        return JSONResponse(
            status_code=400,
            content={"detail": "Only draft plans can be approved."},
        )
    if not plan.get("steps"):
        return JSONResponse(
            status_code=400,
            content={"detail": "Cannot approve a plan with zero steps."},
        )

    # Set status to approved before creating issues
    await _chat_store_any.update_plan_status(db, plan_id, "approved")

    try:
        workflow_result = await execute_pipeline_launch(
            project_id=plan["project_id"],
            issue_description=format_plan_issue_markdown(plan),
            pipeline_id=plan.get("selected_pipeline_id"),
            session=session,
        )
    except Exception:
        logger.error("Plan issue creation failed", exc_info=True)
        await _chat_store_any.update_plan_status(db, plan_id, "failed")
        return JSONResponse(
            status_code=502,
            content={
                "error": "GitHub issue creation failed",
                "plan_id": plan_id,
                "status": "failed",
                "detail": "An error occurred while creating GitHub issues. Please try again.",
            },
        )

    if workflow_result.issue_number and workflow_result.issue_url:
        await _chat_store_any.update_plan_parent_issue(
            db,
            plan_id,
            workflow_result.issue_number,
            workflow_result.issue_url,
        )

    if not workflow_result.issue_number:
        await _chat_store_any.update_plan_status(db, plan_id, "failed")
        return JSONResponse(
            status_code=502,
            content={
                "error": "GitHub issue creation failed",
                "plan_id": plan_id,
                "status": "failed",
                "detail": workflow_result.message,
            },
        )

    if not workflow_result.success:
        logger.warning(
            "Plan %s created parent issue #%s but pipeline launch returned a warning: %s",
            plan_id,
            workflow_result.issue_number,
            workflow_result.message,
        )

    await _chat_store_any.update_plan_status(db, plan_id, "completed")

    if workflow_result.issue_number and workflow_result.issue_url:
        confirmation_prefix = (
            "✅ GitHub parent issue created for plan"
            if workflow_result.success
            else "⚠️ GitHub parent issue created for plan"
        )
        confirmation_content = (
            f"{confirmation_prefix} **{plan['title']}** "
            f"([#{workflow_result.issue_number}]({workflow_result.issue_url}))"
        )
        if not workflow_result.success and workflow_result.message:
            confirmation_content += f"\n\n{workflow_result.message}"

        confirm_message = ChatMessage(
            session_id=session.session_id,
            sender_type=SenderType.SYSTEM,
            content=confirmation_content,
            action_type=ActionType.PLAN_CREATE,
            action_data={
                "plan_id": plan_id,
                "parent_issue_number": workflow_result.issue_number,
                "parent_issue_url": workflow_result.issue_url,
                "status": "completed",
            },
        )
        await add_message(session.session_id, confirm_message)
        _trigger_signal_delivery(session, confirm_message)

    # Re-fetch for accurate state
    updated_plan = await _chat_store_any.get_plan(db, plan_id)
    steps = [
        PlanStepResponse(
            step_id=s["step_id"],
            position=s["position"],
            title=s["title"],
            description=s["description"],
            dependencies=s.get("dependencies", []),
            issue_number=s.get("issue_number"),
            issue_url=s.get("issue_url"),
        )
        for s in (updated_plan or plan).get("steps", [])
    ]
    return PlanApprovalResponse(
        plan_id=plan_id,
        status="completed",
        parent_issue_number=workflow_result.issue_number,
        parent_issue_url=workflow_result.issue_url,
        steps=steps,
    )


@router.post("/plans/{plan_id}/exit")
async def exit_plan_mode_endpoint(
    plan_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
):
    """Exit plan mode and return to normal chat."""
    from src.models.plan import PlanExitResponse

    db = get_db()
    plan = await _chat_store_any.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    # Clear plan mode from agent session
    try:
        chat_agent_svc = get_chat_agent_service()
        await chat_agent_svc.exit_plan_mode(session.session_id)
    except Exception:  # noqa: BLE001 — reason: best-effort operation; failure logged, execution continues
        logger.warning("Failed to clear plan mode from agent session", exc_info=True)

    return PlanExitResponse(
        message="Plan mode deactivated",
        plan_id=plan_id,
        plan_status=plan["status"],
    )


# ---------------------------------------------------------------------------
# Plan v2 endpoints — history, step CRUD, feedback, approval, reorder, export
# ---------------------------------------------------------------------------


# Known safe ValueError messages mapped to (http_status, client-safe description).
# Returning hardcoded strings (never str(exc)) breaks the CodeQL taint chain.
# Non-draft plan conflicts → 409; validation errors → 400.
_SAFE_ERROR_MESSAGES: dict[str, tuple[int, str]] = {
    "Cannot add steps": (409, "Cannot add steps to a non-draft plan."),
    "Cannot change approval": (409, "Cannot change approval status of steps in a non-draft plan."),
    "Cannot delete steps": (409, "Cannot delete steps from a non-draft plan."),
    "Cannot modify steps": (409, "Cannot modify steps in a non-draft plan."),
    "Cannot reorder steps": (409, "Cannot reorder steps in a non-draft plan."),
    "Cannot update steps": (409, "Cannot update steps of a non-draft plan."),
    "DAG validation failed": (400, "DAG validation failed: invalid step dependencies."),
    "Invalid approval_status": (400, "Invalid approval status value."),
    "step_ids must contain exactly the current step IDs": (
        400,
        "step_ids must contain exactly the current step IDs.",
    ),
}


def _safe_validation_detail(exc: ValueError) -> tuple[int, str]:
    """Return a (status_code, detail) pair for a domain ValueError.

    Returns 409 for non-draft plan conflicts, 400 for validation errors,
    and a generic 400 when the exception doesn't match a known prefix.
    Uses hardcoded messages only (never ``str(exc)``) to avoid leaking internals.
    """
    msg = str(exc)  # Used only for prefix matching; never returned to clients.
    for prefix, response in _SAFE_ERROR_MESSAGES.items():
        if msg.startswith(prefix):
            return response
    return 400, "Invalid request: validation failed."


@router.get("/plans/{plan_id}/history")
async def get_plan_history_endpoint(
    plan_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
):
    """Retrieve version history for a plan, ordered by version descending."""
    from src.models.plan import PlanHistoryResponse, PlanVersionResponse

    db = get_db()
    plan = await _chat_store_any.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    versions = await _chat_store_any.get_plan_versions(db, plan_id)
    return PlanHistoryResponse(
        plan_id=plan_id,
        current_version=plan.get("version", 1),
        versions=[
            PlanVersionResponse(
                version_id=v["version_id"],
                plan_id=v["plan_id"],
                version=v["version"],
                title=v["title"],
                summary=v["summary"],
                steps_json=v["steps_json"],
                created_at=v["created_at"],
            )
            for v in versions
        ],
    )


@router.post("/plans/{plan_id}/steps")
async def add_plan_step_endpoint(
    plan_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
    request: Request,
):
    """Add a new step to a plan."""
    from src.models.plan import PlanStepResponse, StepCreateRequest

    db = get_db()
    plan = await _chat_store_any.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    body = await request.json()
    try:
        req = StepCreateRequest(**body)
    except Exception:  # noqa: BLE001 — reason: best-effort operation; returns fallback value on failure
        return JSONResponse(status_code=422, content={"detail": "Invalid request body."})

    try:
        step = await _chat_store_any.add_plan_step(
            db,
            plan_id,
            title=req.title,
            description=req.description,
            dependencies=req.dependencies,
            position=req.position,
        )
    except ValueError as e:
        status, detail = _safe_validation_detail(e)
        return JSONResponse(status_code=status, content={"detail": detail})

    if step is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    return JSONResponse(
        status_code=201,
        content=PlanStepResponse(
            step_id=step["step_id"],
            position=step["position"],
            title=step["title"],
            description=step["description"],
            dependencies=step.get("dependencies", []),
            approval_status=step.get("approval_status", "pending"),
        ).model_dump(),
    )


@router.patch("/plans/{plan_id}/steps/{step_id}")
async def update_plan_step_endpoint(
    plan_id: str,
    step_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
    request: Request,
):
    """Update an existing plan step."""
    from src.models.plan import PlanStepResponse, StepUpdateRequest

    db = get_db()
    plan = await _chat_store_any.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    body = await request.json()
    try:
        req = StepUpdateRequest(**body)
    except Exception:  # noqa: BLE001 — reason: best-effort operation; returns fallback value on failure
        return JSONResponse(status_code=422, content={"detail": "Invalid request body."})

    try:
        step = await _chat_store_any.update_plan_step(
            db,
            plan_id,
            step_id,
            title=req.title,
            description=req.description,
            dependencies=req.dependencies,
        )
    except ValueError as e:
        status, detail = _safe_validation_detail(e)
        return JSONResponse(status_code=status, content={"detail": detail})

    if step is None:
        return JSONResponse(status_code=404, content={"detail": "Step not found."})

    return PlanStepResponse(
        step_id=step["step_id"],
        position=step["position"],
        title=step["title"],
        description=step["description"],
        dependencies=step.get("dependencies", []),
        approval_status=step.get("approval_status", "pending"),
    )


@router.delete("/plans/{plan_id}/steps/{step_id}")
async def delete_plan_step_endpoint(
    plan_id: str,
    step_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
):
    """Delete a plan step."""

    db = get_db()
    plan = await _chat_store_any.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    try:
        deleted = await _chat_store_any.delete_plan_step(db, plan_id, step_id)
    except ValueError as e:
        status, detail = _safe_validation_detail(e)
        return JSONResponse(status_code=status, content={"detail": detail})

    if not deleted:
        return JSONResponse(status_code=404, content={"detail": "Step not found."})

    return Response(status_code=204)


@router.post("/plans/{plan_id}/steps/reorder")
async def reorder_plan_steps_endpoint(
    plan_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
    request: Request,
):
    """Reorder plan steps with DAG re-validation."""
    from src.models.plan import PlanStepResponse, StepReorderRequest

    db = get_db()
    plan = await _chat_store_any.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    body = await request.json()
    try:
        req = StepReorderRequest(**body)
    except Exception:  # noqa: BLE001 — reason: best-effort operation; returns fallback value on failure
        return JSONResponse(status_code=422, content={"detail": "Invalid request body."})

    try:
        reordered = await _chat_store_any.reorder_plan_steps(db, plan_id, req.step_ids)
    except ValueError as e:
        status, detail = _safe_validation_detail(e)
        return JSONResponse(status_code=status, content={"detail": detail})

    if not reordered:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    # Re-fetch the plan to return the updated steps in new order
    updated_plan = await _chat_store_any.get_plan(db, plan_id)
    if updated_plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    return [
        PlanStepResponse(
            step_id=s["step_id"],
            position=s["position"],
            title=s["title"],
            description=s["description"],
            dependencies=s.get("dependencies", []),
            approval_status=s.get("approval_status", "pending"),
        )
        for s in updated_plan.get("steps", [])
    ]


@router.post("/plans/{plan_id}/steps/{step_id}/approve")
async def approve_plan_step_endpoint(
    plan_id: str,
    step_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
    request: Request,
):
    """Update the approval status of a single plan step."""
    from src.models.plan import PlanStepResponse, StepApprovalRequest

    db = get_db()
    plan = await _chat_store_any.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    body = await request.json()
    try:
        req = StepApprovalRequest(**body)
    except Exception:  # noqa: BLE001 — reason: best-effort operation; returns fallback value on failure
        return JSONResponse(status_code=422, content={"detail": "Invalid request body."})

    try:
        updated = await _chat_store_any.update_step_approval(
            db, plan_id, step_id, req.approval_status.value
        )
    except ValueError as e:
        status, detail = _safe_validation_detail(e)
        return JSONResponse(status_code=status, content={"detail": detail})

    if not updated:
        return JSONResponse(status_code=404, content={"detail": "Step not found."})

    # Re-fetch step to return full response
    updated_plan = await _chat_store_any.get_plan(db, plan_id)
    step_data = None
    if updated_plan:
        for s in updated_plan.get("steps", []):
            if s["step_id"] == step_id:
                step_data = s
                break

    if step_data is None:
        return {"step_id": step_id, "approval_status": req.approval_status.value}

    return PlanStepResponse(
        step_id=step_data["step_id"],
        position=step_data["position"],
        title=step_data["title"],
        description=step_data["description"],
        dependencies=step_data.get("dependencies", []),
        approval_status=step_data.get("approval_status", "pending"),
    )


@router.post("/plans/{plan_id}/steps/{step_id}/feedback")
async def submit_step_feedback_endpoint(
    plan_id: str,
    step_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
    request: Request,
):
    """Submit step-level feedback for plan refinement.

    Stub: validates the plan/step and accepts the feedback with HTTP 202,
    but does not yet persist or route the feedback to the active agent
    session.  Persistence and SDK elicitation will be wired in when the
    Copilot SDK upgrade lands.
    """
    from src.models.plan import StepFeedbackRequest, StepFeedbackResponse

    db = get_db()
    plan = await _chat_store_any.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    # Verify step exists
    step_found = any(s["step_id"] == step_id for s in plan.get("steps", []))
    if not step_found:
        return JSONResponse(status_code=404, content={"detail": "Step not found."})

    body = await request.json()
    try:
        req = StepFeedbackRequest(**body)
    except Exception:  # noqa: BLE001 — reason: best-effort operation; returns fallback value on failure
        return JSONResponse(status_code=422, content={"detail": "Invalid request body."})

    # Feedback is transient — accepted for async agent processing
    return JSONResponse(
        status_code=202,
        content=StepFeedbackResponse(
            step_id=step_id,
            feedback_type=req.feedback_type.value,
            status="accepted",
        ).model_dump(),
    )


@router.get("/plans/{plan_id}/export")
async def export_plan_endpoint(
    plan_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
    format: str = "markdown",
):
    """Export a plan as markdown or GitHub issues format."""

    db = get_db()
    plan = await _chat_store_any.get_plan(db, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})
    if plan["session_id"] != str(session.session_id):
        return JSONResponse(status_code=404, content={"detail": "Plan not found."})

    if format == "markdown":
        lines = [f"# {plan['title']}", "", plan["summary"], "", "## Steps", ""]
        for s in plan.get("steps", []):
            deps = ""
            if s.get("dependencies"):
                deps = f" (depends on: {', '.join(s['dependencies'])})"
            lines.append(f"### {s['position'] + 1}. {s['title']}{deps}")
            lines.append("")
            lines.append(s["description"])
            lines.append("")
        return {"format": "markdown", "content": "\n".join(lines)}
    elif format == "github_issues":
        issues = [
            {
                "title": s["title"],
                "body": s["description"],
                "dependencies": s.get("dependencies", []),
            }
            for s in plan.get("steps", [])
        ]
        return {"format": "github_issues", "plan_title": plan["title"], "issues": issues}
    else:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Unsupported format: {format}. Use 'markdown' or 'github_issues'."},
        )
