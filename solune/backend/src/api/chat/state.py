"""In-memory state dicts for chat messages, proposals, and recommendations."""

from __future__ import annotations

import asyncio

from src.models.chat import ChatMessage
from src.models.recommendation import AITaskProposal, IssueRecommendation

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
