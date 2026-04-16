"""Chat persistence — SQLite-backed message, proposal, and recommendation storage.

Replaces the in-memory dict storage in ``api/chat.py`` with durable SQLite
persistence using the tables created by ``023_consolidated_schema.sql``.

All write operations use ``BEGIN IMMEDIATE`` transactions to prevent
concurrent writers from causing inconsistent state.
"""

from __future__ import annotations

import collections
import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import aiosqlite

from src.logging_utils import get_logger

if TYPE_CHECKING:
    from src.models.plan import Plan

logger = get_logger(__name__)


@asynccontextmanager
async def transaction(db: aiosqlite.Connection) -> AsyncGenerator[aiosqlite.Connection]:
    """Context manager for an ``IMMEDIATE`` transaction.

    Commits on success, rolls back on exception.
    """
    await db.execute("BEGIN IMMEDIATE")
    try:
        yield db
        await db.execute("COMMIT")
    except Exception:
        await db.execute("ROLLBACK")
        raise


# ── Messages ─────────────────────────────────────────────────────


async def save_message(
    db: aiosqlite.Connection,
    session_id: str,
    message_id: str,
    sender_type: str,
    content: str,
    action_type: str | None = None,
    action_data: str | None = None,
    conversation_id: str | None = None,
) -> None:
    """Persist a chat message to SQLite."""
    async with transaction(db):
        await db.execute(
            """INSERT OR REPLACE INTO chat_messages
               (message_id, session_id, sender_type, content, action_type, action_data, conversation_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                message_id,
                session_id,
                sender_type,
                content,
                action_type,
                action_data,
                conversation_id,
            ),
        )
        if conversation_id is not None:
            await db.execute(
                """UPDATE conversations
                   SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                   WHERE conversation_id = ?""",
                (conversation_id,),
            )


async def get_messages(
    db: aiosqlite.Connection,
    session_id: str,
    *,
    limit: int | None = None,
    offset: int = 0,
    conversation_id: str | None = None,
) -> list[dict]:
    """Retrieve messages for a session, ordered by timestamp.

    When *limit* is provided, only *limit* rows starting at *offset* are
    returned (SQL-level pagination).  Otherwise all rows are fetched.

    When *conversation_id* is provided, only messages belonging to that
    conversation are returned.  When omitted, only global (non-conversation)
    messages are returned — i.e. ``conversation_id IS NULL``.
    """
    where = "WHERE session_id = ?"
    params: list[str | int] = [session_id]
    if conversation_id is not None:
        where += " AND conversation_id = ?"
        params.append(conversation_id)
    else:
        where += " AND conversation_id IS NULL"

    if limit is not None:
        cursor = await db.execute(
            f"""SELECT message_id, session_id, sender_type, content,
                      action_type, action_data, timestamp, conversation_id
               FROM chat_messages {where} ORDER BY timestamp
               LIMIT ? OFFSET ?""",  # nosec B608 — reason: WHERE clause built from validated column names; all values are parameterised
            (*params, limit, offset),
        )
    else:
        cursor = await db.execute(
            f"""SELECT message_id, session_id, sender_type, content,
                      action_type, action_data, timestamp, conversation_id
               FROM chat_messages {where} ORDER BY timestamp""",  # nosec B608 — reason: WHERE clause built from validated column names; all values are parameterised
            tuple(params),
        )
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        if isinstance(row, tuple):
            result.append(
                {
                    "message_id": row[0],
                    "session_id": row[1],
                    "sender_type": row[2],
                    "content": row[3],
                    "action_type": row[4],
                    "action_data": row[5],
                    "timestamp": row[6],
                    "conversation_id": row[7],
                }
            )
        else:
            result.append(dict(row))
    return result


async def count_messages(
    db: aiosqlite.Connection,
    session_id: str,
    conversation_id: str | None = None,
) -> int:
    """Return the total number of messages for a session."""
    where = "WHERE session_id = ?"
    params: list[str] = [session_id]
    if conversation_id is not None:
        where += " AND conversation_id = ?"
        params.append(conversation_id)
    else:
        where += " AND conversation_id IS NULL"
    cursor = await db.execute(
        f"SELECT COUNT(*) FROM chat_messages {where}",  # nosec B608 — reason: WHERE clause built from validated column names; all values are parameterised
        tuple(params),
    )
    row = await cursor.fetchone()
    return row[0] if row else 0


async def clear_messages(
    db: aiosqlite.Connection,
    session_id: str,
    conversation_id: str | None = None,
) -> None:
    """Delete messages for a session.

    When *conversation_id* is provided, only that conversation's messages are
    deleted.  When omitted, only global (non-conversation) messages — i.e.
    rows where ``conversation_id IS NULL`` — are removed.
    """
    async with transaction(db):
        if conversation_id is not None:
            await db.execute(
                "DELETE FROM chat_messages WHERE session_id = ? AND conversation_id = ?",
                (session_id, conversation_id),
            )
        else:
            await db.execute(
                "DELETE FROM chat_messages WHERE session_id = ? AND conversation_id IS NULL",
                (session_id,),
            )


# ── Conversations ────────────────────────────────────────────────


async def save_conversation(
    db: aiosqlite.Connection,
    session_id: str,
    conversation_id: str,
    title: str = "New Chat",
) -> dict:
    """Create or update a conversation and return it as a dict."""
    async with transaction(db):
        await db.execute(
            """INSERT INTO conversations (conversation_id, session_id, title)
               VALUES (?, ?, ?)
               ON CONFLICT(conversation_id) DO UPDATE SET
                   title = excluded.title,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')""",
            (conversation_id, session_id, title),
        )
    cursor = await db.execute(
        """SELECT conversation_id, session_id, title, created_at, updated_at
           FROM conversations WHERE conversation_id = ?""",
        (conversation_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return {
            "conversation_id": conversation_id,
            "session_id": session_id,
            "title": title,
        }
    if isinstance(row, tuple):
        return {
            "conversation_id": row[0],
            "session_id": row[1],
            "title": row[2],
            "created_at": row[3],
            "updated_at": row[4],
        }
    return dict(row)


async def get_conversations(
    db: aiosqlite.Connection,
    session_id: str,
) -> list[dict]:
    """Return all conversations for a session, ordered by updated_at DESC."""
    cursor = await db.execute(
        """SELECT conversation_id, session_id, title, created_at, updated_at
           FROM conversations WHERE session_id = ? ORDER BY updated_at DESC""",
        (session_id,),
    )
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        if isinstance(row, tuple):
            result.append(
                {
                    "conversation_id": row[0],
                    "session_id": row[1],
                    "title": row[2],
                    "created_at": row[3],
                    "updated_at": row[4],
                }
            )
        else:
            result.append(dict(row))
    return result


async def get_conversation_by_id(
    db: aiosqlite.Connection,
    conversation_id: str,
) -> dict | None:
    """Return a single conversation by ID, or None if not found."""
    cursor = await db.execute(
        """SELECT conversation_id, session_id, title, created_at, updated_at
           FROM conversations WHERE conversation_id = ?""",
        (conversation_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    if isinstance(row, tuple):
        return {
            "conversation_id": row[0],
            "session_id": row[1],
            "title": row[2],
            "created_at": row[3],
            "updated_at": row[4],
        }
    return dict(row)


async def update_conversation(
    db: aiosqlite.Connection,
    conversation_id: str,
    title: str,
) -> dict | None:
    """Update a conversation title and return the updated record, or None if not found."""
    async with transaction(db):
        await db.execute(
            """UPDATE conversations
               SET title = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
               WHERE conversation_id = ?""",
            (title, conversation_id),
        )
    return await get_conversation_by_id(db, conversation_id)


async def delete_conversation(
    db: aiosqlite.Connection,
    conversation_id: str,
) -> bool:
    """Delete a conversation. Returns True if deleted, False if not found."""
    existing = await get_conversation_by_id(db, conversation_id)
    if existing is None:
        return False
    async with transaction(db):
        await db.execute(
            "DELETE FROM conversations WHERE conversation_id = ?",
            (conversation_id,),
        )
    return True


# ── Proposals ────────────────────────────────────────────────────


async def save_proposal(
    db: aiosqlite.Connection,
    session_id: str,
    proposal_id: str,
    original_input: str,
    proposed_title: str,
    proposed_description: str,
    status: str = "pending",
    edited_title: str | None = None,
    edited_description: str | None = None,
    created_at: str | None = None,
    expires_at: str | None = None,
    file_urls: list[str] | None = None,
    selected_pipeline_id: str | None = None,
) -> None:
    """Persist a chat proposal to SQLite."""
    from src.utils import utcnow

    file_urls_json = json.dumps(file_urls) if file_urls else None
    if created_at is None:
        created_at = utcnow().isoformat()
    if expires_at is None:
        from datetime import timedelta

        expires_at = (utcnow() + timedelta(minutes=10)).isoformat()
    async with transaction(db):
        await db.execute(
            """INSERT OR REPLACE INTO chat_proposals
               (proposal_id, session_id, original_input, proposed_title,
                proposed_description, status, edited_title, edited_description,
                created_at, expires_at, file_urls, selected_pipeline_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                proposal_id,
                session_id,
                original_input,
                proposed_title,
                proposed_description,
                status,
                edited_title,
                edited_description,
                created_at,
                expires_at,
                file_urls_json,
                selected_pipeline_id,
            ),
        )


async def get_proposals(
    db: aiosqlite.Connection,
    session_id: str,
) -> list[dict]:
    """Retrieve all proposals for a session, ordered by creation time."""
    cursor = await db.execute(
        """SELECT proposal_id, session_id, original_input, proposed_title,
                  proposed_description, status, edited_title, edited_description,
                  created_at, expires_at, file_urls
           FROM chat_proposals WHERE session_id = ? ORDER BY created_at""",
        (session_id,),
    )
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        if isinstance(row, tuple):
            raw_file_urls = row[10]
            file_urls = json.loads(raw_file_urls) if raw_file_urls else []
            result.append(
                {
                    "proposal_id": row[0],
                    "session_id": row[1],
                    "original_input": row[2],
                    "proposed_title": row[3],
                    "proposed_description": row[4],
                    "status": row[5],
                    "edited_title": row[6],
                    "edited_description": row[7],
                    "created_at": row[8],
                    "expires_at": row[9],
                    "file_urls": file_urls,
                }
            )
        else:
            d = dict(row)
            raw = d.get("file_urls")
            d["file_urls"] = json.loads(raw) if raw else []
            result.append(d)
    return result


async def update_proposal_status(
    db: aiosqlite.Connection,
    proposal_id: str,
    status: str,
    edited_title: str | None = None,
    edited_description: str | None = None,
) -> None:
    """Update a proposal's status and optional edited fields."""
    async with transaction(db):
        if edited_title is not None or edited_description is not None:
            await db.execute(
                """UPDATE chat_proposals
                   SET status = ?, edited_title = ?, edited_description = ?
                   WHERE proposal_id = ?""",
                (status, edited_title, edited_description, proposal_id),
            )
        else:
            await db.execute(
                "UPDATE chat_proposals SET status = ? WHERE proposal_id = ?",
                (status, proposal_id),
            )


async def get_proposal_by_id(
    db: aiosqlite.Connection,
    proposal_id: str,
) -> dict | None:
    """Retrieve a single proposal by its ID."""
    cursor = await db.execute(
        """SELECT proposal_id, session_id, original_input, proposed_title,
                  proposed_description, status, edited_title, edited_description,
                  created_at, expires_at, file_urls, selected_pipeline_id
           FROM chat_proposals WHERE proposal_id = ?""",
        (proposal_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    if isinstance(row, tuple):
        raw_file_urls = row[10]
        return {
            "proposal_id": row[0],
            "session_id": row[1],
            "original_input": row[2],
            "proposed_title": row[3],
            "proposed_description": row[4],
            "status": row[5],
            "edited_title": row[6],
            "edited_description": row[7],
            "created_at": row[8],
            "expires_at": row[9],
            "file_urls": json.loads(raw_file_urls) if raw_file_urls else [],
            "selected_pipeline_id": row[11],
        }
    d = dict(row)
    raw = d.get("file_urls")
    d["file_urls"] = json.loads(raw) if raw else []
    return d


# ── Recommendations ──────────────────────────────────────────────


async def save_recommendation(
    db: aiosqlite.Connection,
    session_id: str,
    recommendation_id: str,
    data: str,
    status: str = "pending",
    file_urls: list[str] | None = None,
) -> None:
    """Persist a chat recommendation to SQLite."""
    file_urls_json = json.dumps(file_urls) if file_urls else None
    async with transaction(db):
        await db.execute(
            """INSERT OR REPLACE INTO chat_recommendations
               (recommendation_id, session_id, data, status, file_urls)
               VALUES (?, ?, ?, ?, ?)""",
            (
                recommendation_id,
                session_id,
                data,
                _recommendation_status_to_db(status),
                file_urls_json,
            ),
        )


async def get_recommendations(
    db: aiosqlite.Connection,
    session_id: str,
) -> list[dict]:
    """Retrieve all recommendations for a session."""
    cursor = await db.execute(
        """SELECT recommendation_id, session_id, data, status, created_at, file_urls
           FROM chat_recommendations WHERE session_id = ? ORDER BY created_at""",
        (session_id,),
    )
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        if isinstance(row, tuple):
            raw_file_urls = row[5]
            file_urls = json.loads(raw_file_urls) if raw_file_urls else []
            result.append(
                {
                    "recommendation_id": row[0],
                    "session_id": row[1],
                    "data": row[2],
                    "status": row[3],
                    "created_at": row[4],
                    "file_urls": file_urls,
                }
            )
        else:
            d = dict(row)
            raw = d.get("file_urls")
            d["file_urls"] = json.loads(raw) if raw else []
            result.append(d)
    return result


async def update_recommendation_status(
    db: aiosqlite.Connection,
    recommendation_id: str,
    status: str,
    data: str | None = None,
) -> None:
    """Update a recommendation's status."""
    db_status = _recommendation_status_to_db(status)
    async with transaction(db):
        if data is not None:
            await db.execute(
                "UPDATE chat_recommendations SET status = ?, data = ? WHERE recommendation_id = ?",
                (db_status, data, recommendation_id),
            )
        else:
            await db.execute(
                "UPDATE chat_recommendations SET status = ? WHERE recommendation_id = ?",
                (db_status, recommendation_id),
            )


async def get_recommendation_by_id(
    db: aiosqlite.Connection,
    recommendation_id: str,
) -> dict | None:
    """Retrieve a single recommendation by its ID."""
    cursor = await db.execute(
        """SELECT recommendation_id, session_id, data, status, created_at, file_urls
           FROM chat_recommendations WHERE recommendation_id = ?""",
        (recommendation_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    if isinstance(row, tuple):
        raw_file_urls = row[5]
        return {
            "recommendation_id": row[0],
            "session_id": row[1],
            "data": row[2],
            "status": row[3],
            "created_at": row[4],
            "file_urls": json.loads(raw_file_urls) if raw_file_urls else [],
        }
    d = dict(row)
    raw = d.get("file_urls")
    d["file_urls"] = json.loads(raw) if raw else []
    return d


def recommendation_status_from_db(status: str) -> str:
    """Normalize stored recommendation status values to model enum values."""
    return "confirmed" if status == "accepted" else status


def _recommendation_status_to_db(status: str) -> str:
    """Map model enum values to the legacy SQLite status constraint."""
    return "accepted" if status == "confirmed" else status


# ============================================================================
# Plan CRUD
# ============================================================================


async def save_plan(
    db: aiosqlite.Connection,
    plan: Plan,
) -> None:
    """Persist a plan and its steps to SQLite (insert or replace).

    Uses a transaction to atomically write the plan header and all steps.
    """
    from src.utils import utcnow

    now = utcnow().isoformat()
    status_val = plan.status.value if hasattr(plan.status, "value") else plan.status
    async with transaction(db):
        # Preserve created_at and derive version server-side for existing rows
        # via UPSERT. On conflict the DB-side version is kept (never reset to 1).
        await db.execute(
            """INSERT INTO chat_plans
               (plan_id, session_id, title, summary, status, version,
                project_id, project_name, repo_owner, repo_name,
                                selected_pipeline_id,
                parent_issue_number, parent_issue_url,
                created_at, updated_at)
                             VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(plan_id) DO UPDATE SET
                 session_id = excluded.session_id,
                 title = excluded.title,
                 summary = excluded.summary,
                 status = excluded.status,
                 project_id = excluded.project_id,
                 project_name = excluded.project_name,
                 repo_owner = excluded.repo_owner,
                 repo_name = excluded.repo_name,
                                 selected_pipeline_id = excluded.selected_pipeline_id,
                 parent_issue_number = excluded.parent_issue_number,
                 parent_issue_url = excluded.parent_issue_url,
                 updated_at = excluded.updated_at""",
            (
                plan.plan_id,
                plan.session_id,
                plan.title,
                plan.summary,
                status_val,
                plan.project_id,
                plan.project_name,
                plan.repo_owner,
                plan.repo_name,
                plan.selected_pipeline_id,
                plan.parent_issue_number,
                plan.parent_issue_url,
                plan.created_at or now,
                now,
            ),
        )
        # Replace all steps: delete old ones, insert new ones
        await db.execute(
            "DELETE FROM chat_plan_steps WHERE plan_id = ?",
            (plan.plan_id,),
        )
        for step in plan.steps:
            approval_raw = getattr(step, "approval_status", "pending")
            approval: str = getattr(approval_raw, "value", approval_raw)
            await db.execute(
                """INSERT INTO chat_plan_steps
                   (step_id, plan_id, position, title, description,
                    dependencies, approval_status, issue_number, issue_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    step.step_id,
                    plan.plan_id,
                    step.position,
                    step.title,
                    step.description,
                    json.dumps(step.dependencies),
                    approval,
                    step.issue_number,
                    step.issue_url,
                ),
            )


async def get_plan(
    db: aiosqlite.Connection,
    plan_id: str,
) -> dict | None:
    """Retrieve a plan with all its steps joined."""
    cursor = await db.execute(
        """SELECT plan_id, session_id, title, summary, status, version,
                  project_id, project_name, repo_owner, repo_name,
                  selected_pipeline_id, parent_issue_number, parent_issue_url,
                  created_at, updated_at
           FROM chat_plans WHERE plan_id = ?""",
        (plan_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    if isinstance(row, tuple):
        plan_dict = {
            "plan_id": row[0],
            "session_id": row[1],
            "title": row[2],
            "summary": row[3],
            "status": row[4],
            "version": row[5],
            "project_id": row[6],
            "project_name": row[7],
            "repo_owner": row[8],
            "repo_name": row[9],
            "selected_pipeline_id": row[10],
            "parent_issue_number": row[11],
            "parent_issue_url": row[12],
            "created_at": row[13],
            "updated_at": row[14],
        }
    else:
        plan_dict = dict(row)

    # Fetch steps
    step_cursor = await db.execute(
        """SELECT step_id, plan_id, position, title, description,
                  dependencies, approval_status, issue_number, issue_url
           FROM chat_plan_steps WHERE plan_id = ?
           ORDER BY position ASC""",
        (plan_id,),
    )
    step_rows = await step_cursor.fetchall()
    steps = []
    for s in step_rows:
        if isinstance(s, tuple):
            steps.append(
                {
                    "step_id": s[0],
                    "plan_id": s[1],
                    "position": s[2],
                    "title": s[3],
                    "description": s[4],
                    "dependencies": json.loads(s[5]) if s[5] else [],
                    "approval_status": s[6] or "pending",
                    "issue_number": s[7],
                    "issue_url": s[8],
                }
            )
        else:
            d = dict(s)
            raw_deps = d.get("dependencies")
            d["dependencies"] = json.loads(raw_deps) if raw_deps else []
            if "approval_status" not in d or d["approval_status"] is None:
                d["approval_status"] = "pending"
            steps.append(d)

    plan_dict["steps"] = steps
    return plan_dict


async def get_latest_plan_for_session(
    db: aiosqlite.Connection,
    session_id: str,
    *,
    updated_after: str | None = None,
) -> dict | None:
    """Return the most recently updated plan for a session."""
    if updated_after is not None:
        cursor = await db.execute(
            """SELECT plan_id
               FROM chat_plans
               WHERE session_id = ? AND updated_at >= ?
               ORDER BY updated_at DESC
               LIMIT 1""",
            (session_id, updated_after),
        )
    else:
        cursor = await db.execute(
            """SELECT plan_id
               FROM chat_plans
               WHERE session_id = ?
               ORDER BY updated_at DESC
               LIMIT 1""",
            (session_id,),
        )

    row = await cursor.fetchone()
    if row is None:
        return None

    plan_id = row[0] if isinstance(row, tuple) else row["plan_id"]
    return await get_plan(db, plan_id)


async def update_plan(
    db: aiosqlite.Connection,
    plan_id: str,
    title: str | None = None,
    summary: str | None = None,
) -> bool:
    """Update plan metadata (title and/or summary). Returns True if updated."""
    from src.utils import utcnow

    sets: list[str] = []
    params: list[str] = []
    if title is not None:
        sets.append("title = ?")
        params.append(title)
    if summary is not None:
        sets.append("summary = ?")
        params.append(summary)
    if not sets:
        return False

    sets.append("updated_at = ?")
    params.append(utcnow().isoformat())
    params.append(plan_id)

    async with transaction(db):
        cursor = await db.execute(
            f"UPDATE chat_plans SET {', '.join(sets)} WHERE plan_id = ?",  # nosec B608 — reason: SET clause built from hardcoded column names; all values are parameterised
            tuple(params),
        )
    return (cursor.rowcount or 0) > 0


async def update_plan_status(
    db: aiosqlite.Connection,
    plan_id: str,
    status: str,
) -> bool:
    """Transition a plan to a new lifecycle status. Returns True if updated."""
    from src.utils import utcnow

    async with transaction(db):
        cursor = await db.execute(
            "UPDATE chat_plans SET status = ?, updated_at = ? WHERE plan_id = ?",
            (status, utcnow().isoformat(), plan_id),
        )
    return (cursor.rowcount or 0) > 0


async def update_plan_step_issue(
    db: aiosqlite.Connection,
    step_id: str,
    issue_number: int,
    issue_url: str,
) -> bool:
    """Update a step with its GitHub issue number and URL after creation."""
    async with transaction(db):
        cursor = await db.execute(
            "UPDATE chat_plan_steps SET issue_number = ?, issue_url = ? WHERE step_id = ?",
            (issue_number, issue_url, step_id),
        )
    return (cursor.rowcount or 0) > 0


async def update_plan_parent_issue(
    db: aiosqlite.Connection,
    plan_id: str,
    parent_issue_number: int,
    parent_issue_url: str,
) -> bool:
    """Update a plan with its parent GitHub issue number and URL."""
    from src.utils import utcnow

    async with transaction(db):
        cursor = await db.execute(
            """UPDATE chat_plans
               SET parent_issue_number = ?, parent_issue_url = ?, updated_at = ?
               WHERE plan_id = ?""",
            (parent_issue_number, parent_issue_url, utcnow().isoformat(), plan_id),
        )
    return (cursor.rowcount or 0) > 0


# ---------------------------------------------------------------------------
# Plan versioning
# ---------------------------------------------------------------------------


async def snapshot_plan_version(
    db: aiosqlite.Connection,
    plan_id: str,
) -> str | None:
    """Save a snapshot of the current plan state to chat_plan_versions.

    Returns the version_id of the created snapshot, or None if the plan
    was not found.
    """
    from uuid import uuid4

    from src.utils import utcnow

    plan = await get_plan(db, plan_id)
    if plan is None:
        return None

    version = plan.get("version", 1)
    version_id = str(uuid4())
    steps_json = json.dumps(plan.get("steps", []))
    now = utcnow().isoformat()

    async with transaction(db):
        cursor = await db.execute(
            """INSERT OR IGNORE INTO chat_plan_versions
               (version_id, plan_id, version, title, summary, steps_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                version_id,
                plan_id,
                version,
                plan["title"],
                plan["summary"],
                steps_json,
                now,
            ),
        )
        if (cursor.rowcount or 0) == 0:
            # INSERT was ignored (e.g. concurrent snapshot for the same version).
            # Do not increment the plan version to keep history consistent.
            return None
        # Increment the plan's version
        await db.execute(
            "UPDATE chat_plans SET version = version + 1, updated_at = ? WHERE plan_id = ?",
            (now, plan_id),
        )
    return version_id


async def get_plan_versions(
    db: aiosqlite.Connection,
    plan_id: str,
) -> list[dict]:
    """Query version history for a plan, ordered by version descending."""
    cursor = await db.execute(
        """SELECT version_id, plan_id, version, title, summary, steps_json, created_at
           FROM chat_plan_versions
           WHERE plan_id = ?
           ORDER BY version DESC""",
        (plan_id,),
    )
    rows = await cursor.fetchall()
    versions = []
    for r in rows:
        if isinstance(r, tuple):
            versions.append(
                {
                    "version_id": r[0],
                    "plan_id": r[1],
                    "version": r[2],
                    "title": r[3],
                    "summary": r[4],
                    "steps_json": r[5],
                    "created_at": r[6],
                }
            )
        else:
            versions.append(dict(r))
    return versions


# ---------------------------------------------------------------------------
# DAG validation
# ---------------------------------------------------------------------------


def validate_dag(steps: list[dict]) -> tuple[bool, str]:
    """Validate that step dependencies form a DAG (no circular dependencies).

    Uses Kahn's algorithm for topological sort (O(V+E) cycle detection).

    Returns:
        (is_valid, error_message) — True if no cycles, or False with a
        description of the offending cycle.
    """
    step_ids = {s["step_id"] for s in steps}

    # Check all deps reference existing steps
    for s in steps:
        for dep_id in s.get("dependencies", []):
            if dep_id not in step_ids:
                return False, f"Step {s['step_id']!r} depends on unknown step {dep_id!r}"

    # Build adjacency and in-degree
    in_degree: dict[str, int] = dict.fromkeys(step_ids, 0)
    adjacency: dict[str, list[str]] = {sid: [] for sid in step_ids}

    for s in steps:
        for dep_id in s.get("dependencies", []):
            adjacency[dep_id].append(s["step_id"])
            in_degree[s["step_id"]] += 1

    # Kahn's algorithm
    queue = collections.deque(sid for sid, deg in in_degree.items() if deg == 0)
    visited = 0

    while queue:
        node = queue.popleft()
        visited += 1
        for neighbor in adjacency[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if visited != len(step_ids):
        cycle_nodes = [sid for sid, deg in in_degree.items() if deg > 0]
        return False, f"Circular dependency detected among steps: {cycle_nodes}"

    return True, ""


# ---------------------------------------------------------------------------
# Step CRUD operations
# ---------------------------------------------------------------------------


async def add_plan_step(
    db: aiosqlite.Connection,
    plan_id: str,
    title: str,
    description: str,
    dependencies: list[str] | None = None,
    position: int | None = None,
) -> dict | None:
    """Add a new step to a plan with position auto-assignment and DAG validation.

    Returns the created step dict, or None if the plan is not found.
    Raises ValueError on DAG violation or non-draft plan.
    """
    from uuid import uuid4

    plan = await get_plan(db, plan_id)
    if plan is None:
        return None

    if plan["status"] != "draft":
        raise ValueError("Cannot add steps to a non-draft plan")

    existing_steps = plan.get("steps", [])

    # Auto-assign position if not specified
    if position is None:
        position = len(existing_steps)

    step_id = str(uuid4())
    deps = dependencies or []

    # Build proposed steps list for DAG validation
    new_step = {
        "step_id": step_id,
        "plan_id": plan_id,
        "position": position,
        "title": title,
        "description": description,
        "dependencies": deps,
        "approval_status": "pending",
    }
    proposed = [*existing_steps, new_step]
    is_valid, err = validate_dag(proposed)
    if not is_valid:
        raise ValueError(f"DAG validation failed: {err}")

    async with transaction(db):
        # Shift positions >= target position using a temporary offset so the
        # UNIQUE(plan_id, position) constraint is never violated mid-update.
        cursor = await db.execute(
            """SELECT COALESCE(MAX(position), -1)
               FROM chat_plan_steps
               WHERE plan_id = ?""",
            (plan_id,),
        )
        row = await cursor.fetchone()
        max_position = row[0] if row is not None else -1
        temp_offset = max_position + 1

        await db.execute(
            """UPDATE chat_plan_steps
               SET position = position + ?
               WHERE plan_id = ? AND position >= ?""",
            (temp_offset, plan_id, position),
        )
        await db.execute(
            """UPDATE chat_plan_steps
               SET position = position - ? + 1
               WHERE plan_id = ? AND position >= ?""",
            (temp_offset, plan_id, position + temp_offset),
        )
        await db.execute(
            """INSERT INTO chat_plan_steps
               (step_id, plan_id, position, title, description,
                dependencies, approval_status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                step_id,
                plan_id,
                position,
                title,
                description,
                json.dumps(deps),
                "pending",
            ),
        )
    return new_step


async def update_plan_step(
    db: aiosqlite.Connection,
    plan_id: str,
    step_id: str,
    title: str | None = None,
    description: str | None = None,
    dependencies: list[str] | None = None,
) -> dict | None:
    """Update an existing plan step with DAG re-validation.

    Returns the updated step dict, or None if not found.
    Raises ValueError on DAG violation or non-draft plan.
    """
    plan = await get_plan(db, plan_id)
    if plan is None:
        return None

    if plan["status"] != "draft":
        raise ValueError("Cannot update steps of a non-draft plan")

    # Find the target step
    target_step = None
    for s in plan.get("steps", []):
        if s["step_id"] == step_id:
            target_step = s
            break
    if target_step is None:
        return None

    # Apply updates
    new_title = title if title is not None else target_step["title"]
    new_description = description if description is not None else target_step["description"]
    new_deps = dependencies if dependencies is not None else target_step.get("dependencies", [])

    # DAG validation with updated step
    proposed = []
    for s in plan["steps"]:
        if s["step_id"] == step_id:
            proposed.append(
                {**s, "title": new_title, "description": new_description, "dependencies": new_deps}
            )
        else:
            proposed.append(s)

    is_valid, err = validate_dag(proposed)
    if not is_valid:
        raise ValueError(f"DAG validation failed: {err}")

    from src.utils import utcnow

    async with transaction(db):
        sets: list[str] = []
        params: list[str | int] = []
        if title is not None:
            sets.append("title = ?")
            params.append(title)
        if description is not None:
            sets.append("description = ?")
            params.append(description)
        if dependencies is not None:
            sets.append("dependencies = ?")
            params.append(json.dumps(dependencies))
        if not sets:
            return target_step

        params.extend([step_id, plan_id])
        await db.execute(
            f"UPDATE chat_plan_steps SET {', '.join(sets)} WHERE step_id = ? AND plan_id = ?",  # nosec B608 — reason: SET clause built from hardcoded column names; all values are parameterised
            tuple(params),
        )
        await db.execute(
            "UPDATE chat_plans SET updated_at = ? WHERE plan_id = ?",
            (utcnow().isoformat(), plan_id),
        )

    updated = {
        **target_step,
        "title": new_title,
        "description": new_description,
        "dependencies": new_deps,
    }
    return updated


async def delete_plan_step(
    db: aiosqlite.Connection,
    plan_id: str,
    step_id: str,
) -> bool:
    """Delete a step with cascade removal from other steps' dependency lists.

    Re-indexes positions after deletion. Returns True if deleted.
    Raises ValueError if plan is non-draft.
    """
    plan = await get_plan(db, plan_id)
    if plan is None:
        return False

    if plan["status"] != "draft":
        raise ValueError("Cannot delete steps from a non-draft plan")

    target = None
    for s in plan.get("steps", []):
        if s["step_id"] == step_id:
            target = s
            break
    if target is None:
        return False

    from src.utils import utcnow

    async with transaction(db):
        # Delete the step
        await db.execute(
            "DELETE FROM chat_plan_steps WHERE step_id = ? AND plan_id = ?",
            (step_id, plan_id),
        )
        # Remove from other steps' dependency lists
        step_cursor = await db.execute(
            "SELECT step_id, dependencies FROM chat_plan_steps WHERE plan_id = ?",
            (plan_id,),
        )
        rows = await step_cursor.fetchall()
        for row in rows:
            sid = row[0] if isinstance(row, tuple) else row["step_id"]
            deps_raw = row[1] if isinstance(row, tuple) else row["dependencies"]
            deps = json.loads(deps_raw) if deps_raw else []
            if step_id in deps:
                deps.remove(step_id)
                await db.execute(
                    "UPDATE chat_plan_steps SET dependencies = ? WHERE step_id = ?",
                    (json.dumps(deps), sid),
                )
        # Re-index positions
        remaining = await db.execute(
            "SELECT step_id FROM chat_plan_steps WHERE plan_id = ? ORDER BY position ASC",
            (plan_id,),
        )
        remaining_rows = await remaining.fetchall()
        for idx, r in enumerate(remaining_rows):
            sid = r[0] if isinstance(r, tuple) else r["step_id"]
            await db.execute(
                "UPDATE chat_plan_steps SET position = ? WHERE step_id = ?",
                (idx, sid),
            )
        await db.execute(
            "UPDATE chat_plans SET updated_at = ? WHERE plan_id = ?",
            (utcnow().isoformat(), plan_id),
        )
    return True


async def reorder_plan_steps(
    db: aiosqlite.Connection,
    plan_id: str,
    step_ids: list[str],
) -> bool:
    """Reorder plan steps with DAG re-validation.

    Args:
        step_ids: Ordered list of step_ids defining new positions.

    Returns True if reordered. Raises ValueError on DAG violation or non-draft plan.
    """
    plan = await get_plan(db, plan_id)
    if plan is None:
        return False

    if plan["status"] != "draft":
        raise ValueError("Cannot reorder steps of a non-draft plan")

    existing_ids = {s["step_id"] for s in plan.get("steps", [])}
    if set(step_ids) != existing_ids:
        raise ValueError("step_ids must contain exactly the current step IDs")

    # Build reordered steps
    step_map = {s["step_id"]: s for s in plan["steps"]}
    reordered = []
    for i, sid in enumerate(step_ids):
        s = {**step_map[sid], "position": i}
        reordered.append(s)

    is_valid, err = validate_dag(reordered)
    if not is_valid:
        raise ValueError(f"DAG validation failed: {err}")

    from src.utils import utcnow

    async with transaction(db):
        # Use temporary high positions to avoid UNIQUE constraint conflicts
        offset = 10000
        for i, sid in enumerate(step_ids):
            await db.execute(
                "UPDATE chat_plan_steps SET position = ? WHERE step_id = ? AND plan_id = ?",
                (offset + i, sid, plan_id),
            )
        # Set final positions
        for i, sid in enumerate(step_ids):
            await db.execute(
                "UPDATE chat_plan_steps SET position = ? WHERE step_id = ? AND plan_id = ?",
                (i, sid, plan_id),
            )
        await db.execute(
            "UPDATE chat_plans SET updated_at = ? WHERE plan_id = ?",
            (utcnow().isoformat(), plan_id),
        )
    return True


async def update_step_approval(
    db: aiosqlite.Connection,
    plan_id: str,
    step_id: str,
    approval_status: str,
) -> bool:
    """Update the approval status of a single step.

    Returns True if the step was updated.
    Raises ValueError if plan is not draft or approval_status is invalid.
    """
    from src.models.plan import StepApprovalStatus

    # Validate the approval status value
    valid_statuses = {s.value for s in StepApprovalStatus}
    if approval_status not in valid_statuses:
        raise ValueError(
            f"Invalid approval_status {approval_status!r}; must be one of {sorted(valid_statuses)}"
        )

    plan = await get_plan(db, plan_id)
    if plan is None:
        return False

    if plan["status"] != "draft":
        raise ValueError("Cannot change approval status of steps in a non-draft plan")

    from src.utils import utcnow

    now = utcnow().isoformat()

    async with transaction(db):
        cursor = await db.execute(
            "UPDATE chat_plan_steps SET approval_status = ? WHERE step_id = ? AND plan_id = ?",
            (approval_status, step_id, plan_id),
        )
        if (cursor.rowcount or 0) > 0:
            await db.execute(
                "UPDATE chat_plans SET updated_at = ? WHERE plan_id = ?",
                (now, plan_id),
            )
    return (cursor.rowcount or 0) > 0
