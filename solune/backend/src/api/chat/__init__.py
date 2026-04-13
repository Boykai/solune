"""Chat API sub-package.

Splits the monolithic chat.py into focused modules:
- messages.py: Conversation and message CRUD endpoints
- streaming.py: SSE streaming endpoint
- proposals.py: Proposal confirmation and cancellation
- plans.py: Plan mode endpoints
- uploads.py: File upload endpoint
- persistence.py: SQLite persistence helpers
- constants.py: Shared types, constants, and config
"""

from fastapi import APIRouter

from src.api.chat.messages import router as messages_router
from src.api.chat.streaming import router as streaming_router
from src.api.chat.proposals import router as proposals_router
from src.api.chat.plans import router as plans_router
from src.api.chat.uploads import router as uploads_router

# Re-export public helpers used by other modules (e.g. chat_agent, workflow, signal)
from src.api.chat.persistence import (  # noqa: F401
    _retry_persist,
    _trigger_signal_delivery,
    add_message,
    get_proposal,
    get_recommendation,
    get_session_messages,
    store_proposal,
    store_recommendation,
)
from src.api.chat.constants import (  # noqa: F401
    _PERSIST_BASE_DELAY,
    _PERSIST_MAX_RETRIES,
    _locks,
    _messages,
    _proposals,
    _recommendations,
    FileUploadResponse,
)
from src.api.chat.messages import (  # noqa: F401
    _extract_transcript_content,
    _handle_transcript_upload,
    _post_process_agent_response,
    _resolve_repository,
)
from src.api.chat.uploads import upload_file  # noqa: F401

router = APIRouter()
router.include_router(messages_router)
router.include_router(streaming_router)
router.include_router(proposals_router)
router.include_router(plans_router)
router.include_router(uploads_router)
