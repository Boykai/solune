"""Chat API package — split from the monolithic chat.py module.

All symbols that external code previously imported from ``src.api.chat``
are re-exported here so that ``from src.api.chat import router`` (and
every other external import) continues to work unchanged.
"""

from __future__ import annotations

from fastapi import APIRouter

# ── Sub-module routers ───────────────────────────────────────────────────
from .conversations import router as conversations_router
from .messages import router as messages_router
from .plans import router as plans_router
from .proposals import router as proposals_router
from .streaming import router as streaming_router

router = APIRouter()
router.include_router(messages_router)
router.include_router(proposals_router)
router.include_router(plans_router)
router.include_router(conversations_router)
router.include_router(streaming_router)

# ── Backward-compatible re-exports ───────────────────────────────────────
# Every symbol that external code imports from `src.api.chat` must appear
# here so the barrel import keeps working.

from pathlib import Path as Path  # noqa: E402

from src.services.cache import cache as cache  # noqa: E402
from src.services.database import get_db as get_db  # noqa: E402

from .dispatch import (  # noqa: E402
    _extract_transcript_content,
    _handle_transcript_upload,
    _post_process_agent_response,
)
from .helpers import (  # noqa: E402
    _resolve_repository,
    _retry_persist,
    _safe_validation_detail,
    _trigger_signal_delivery,
    add_message,
    get_proposal,
    get_recommendation,
    get_session_messages,
    store_proposal,
    store_recommendation,
)
from .models import FileUploadResponse  # noqa: E402
from .proposals import upload_file  # noqa: E402
from .state import (  # noqa: E402
    _PERSIST_BASE_DELAY,
    _PERSIST_MAX_RETRIES,
    _locks,
    _messages,
    _proposals,
    _recommendations,
)

__all__ = [
    "_PERSIST_BASE_DELAY",
    "_PERSIST_MAX_RETRIES",
    "FileUploadResponse",
    "Path",
    "_extract_transcript_content",
    "_handle_transcript_upload",
    "_locks",
    "_messages",
    "_post_process_agent_response",
    "_proposals",
    "_recommendations",
    "_resolve_repository",
    "_retry_persist",
    "_safe_validation_detail",
    "_trigger_signal_delivery",
    "add_message",
    "cache",
    "get_db",
    "get_proposal",
    "get_recommendation",
    "get_session_messages",
    "router",
    "store_proposal",
    "store_recommendation",
    "upload_file",
]
