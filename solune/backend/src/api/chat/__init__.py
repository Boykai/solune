"""Chat API package – split from the original monolithic chat.py."""

from __future__ import annotations

import asyncio  # noqa: F401 – re-exported for test patches (src.api.chat.asyncio.sleep)

from fastapi import APIRouter

# Re-export shared state so external code (signal_chat, signal_bridge,
# workflow, tests/conftest) can still do `from src.api.chat import X`.
from src.api.chat.messages import (  # noqa: F401
    MAX_FILE_SIZE_BYTES,
    FileUploadResponse,
    _locks,
    _messages,
    _resolve_repository,
    _trigger_signal_delivery,
    add_message,
    get_session_messages,
    upload_file,
)
from src.api.chat.proposals import (  # noqa: F401
    _default_expires_at,
    _persist_proposal,
    _persist_recommendation,
    _proposals,
    _recommendations,
    get_proposal,
    get_recommendation,
    store_proposal,
    store_recommendation,
)

# Re-export names that tests patch at "src.api.chat.<name>" or access via
# ``import src.api.chat as chat_mod; chat_mod.<name>``.
from src.dependencies import require_selected_project  # noqa: F401
from src.models.recommendation import AITaskProposal  # noqa: F401
from src.services.ai_agent import get_ai_agent_service  # noqa: F401
from src.services.cache import cache  # noqa: F401
from src.services.chat_agent import get_chat_agent_service  # noqa: F401
from src.services.database import get_db  # noqa: F401
from src.services.settings_store import get_effective_user_settings  # noqa: F401
from src.services.workflow_orchestrator import (  # noqa: F401
    get_agent_slugs,
    get_workflow_config,
    get_workflow_orchestrator,
    set_workflow_config,
)
from src.utils import resolve_repository  # noqa: F401

# Sub-module routers
from src.api.chat.conversations import router as conversations_router
from src.api.chat.messages import router as messages_router
from src.api.chat.plans import router as plans_router
from src.api.chat.proposals import router as proposals_router
from src.api.chat.streaming import router as streaming_router

router = APIRouter()
router.include_router(conversations_router)
router.include_router(messages_router)
router.include_router(proposals_router)
router.include_router(plans_router)
router.include_router(streaming_router)
