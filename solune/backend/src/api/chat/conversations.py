"""Conversation CRUD routes."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Body, Depends

from src.api.auth import get_session_dep
from src.exceptions import NotFoundError
from src.models.chat import (
    Conversation,
    ConversationCreateRequest,
    ConversationsListResponse,
    ConversationUpdateRequest,
)
from src.models.user import UserSession
from src.services.database import get_db
from src.utils import utcnow

router = APIRouter()


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
