"""Proposal/recommendation endpoints and file upload."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse

from src.api.auth import get_session_dep
from src.dependencies import get_connection_manager, get_github_service
from src.exceptions import NotFoundError, ValidationError
from src.logging_utils import get_logger
from src.models.chat import ChatMessage, SenderType
from src.models.recommendation import AITaskProposal, ProposalConfirmRequest, ProposalStatus
from src.models.user import UserSession
from src.services.database import get_db
from src.services.proposal_orchestrator import ProposalOrchestrator

from .helpers import (
    add_message,
    get_proposal,
)
from .models import (
    ALLOWED_TYPES,
    BLOCKED_TYPES,
    MAX_FILE_SIZE_BYTES,
    FileUploadResponse,
)

logger = get_logger(__name__)
router = APIRouter()


@router.post("/proposals/{proposal_id}/confirm", response_model=AITaskProposal)
async def confirm_proposal(
    proposal_id: str,
    request: ProposalConfirmRequest | None,
    session: Annotated[UserSession, Depends(get_session_dep)],
    github_projects_service=Depends(get_github_service),  # noqa: B008
    connection_manager=Depends(get_connection_manager),  # noqa: B008
) -> AITaskProposal:
    """Confirm an AI task proposal and create the task."""
    from src.services import chat_store

    orchestrator = ProposalOrchestrator(
        chat_state_manager=None,
        chat_store_module=chat_store,
    )
    return await orchestrator.confirm(
        proposal_id=proposal_id,
        request=request,
        session=session,
        github_service=github_projects_service,
        connection_manager=connection_manager,
    )


@router.delete("/proposals/{proposal_id}")
async def cancel_proposal(
    proposal_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
) -> dict:
    """Cancel an AI task proposal."""
    proposal = await get_proposal(proposal_id)

    if not proposal:
        raise NotFoundError(f"Proposal not found: {proposal_id}")

    if str(proposal.session_id) != str(session.session_id):
        raise NotFoundError(f"Proposal not found: {proposal_id}")

    proposal.status = ProposalStatus.CANCELLED
    try:
        from src.services import chat_store

        db = get_db()
        await chat_store.update_proposal_status(db, proposal_id, ProposalStatus.CANCELLED.value)
    except Exception:
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
