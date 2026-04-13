"""Shared constants, config, and in-memory state for the chat sub-package."""

from __future__ import annotations

import asyncio

from pydantic import BaseModel

from src.logging_utils import get_logger
from src.models.chat import ChatMessage
from src.models.recommendation import AITaskProposal, IssueRecommendation

logger = get_logger(__name__)

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
# via chat_store.py (tables from 023_consolidated_schema.sql).  In-memory
# dicts act as a read-through cache backed by SQLite (single source of truth).
# Writes go to SQLite first, then update the cache on success.

_messages: dict[str, list[ChatMessage]] = {}
_proposals: dict[str, AITaskProposal] = {}
_recommendations: dict[str, IssueRecommendation] = {}
_locks: dict[str, asyncio.Lock] = {}

_PERSIST_MAX_RETRIES = 3
_PERSIST_BASE_DELAY = 0.1  # 100ms, 200ms, 400ms
