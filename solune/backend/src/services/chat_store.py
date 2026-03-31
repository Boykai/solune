"""Chat persistence — SQLite-backed message, proposal, and recommendation storage.

Replaces the in-memory dict storage in ``api/chat.py`` with durable SQLite
persistence using the tables created by ``023_consolidated_schema.sql``.

All write operations use ``BEGIN IMMEDIATE`` transactions to prevent
concurrent writers from causing inconsistent state.
"""

from __future__ import annotations

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
) -> None:
    """Persist a chat message to SQLite."""
    async with transaction(db):
        await db.execute(
            """INSERT OR REPLACE INTO chat_messages
               (message_id, session_id, sender_type, content, action_type, action_data)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (message_id, session_id, sender_type, content, action_type, action_data),
        )


async def get_messages(
    db: aiosqlite.Connection,
    session_id: str,
    *,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    """Retrieve messages for a session, ordered by timestamp.

    When *limit* is provided, only *limit* rows starting at *offset* are
    returned (SQL-level pagination).  Otherwise all rows are fetched.
    """
    if limit is not None:
        cursor = await db.execute(
            """SELECT message_id, session_id, sender_type, content,
                      action_type, action_data, timestamp
               FROM chat_messages WHERE session_id = ? ORDER BY timestamp
               LIMIT ? OFFSET ?""",
            (session_id, limit, offset),
        )
    else:
        cursor = await db.execute(
            """SELECT message_id, session_id, sender_type, content,
                      action_type, action_data, timestamp
               FROM chat_messages WHERE session_id = ? ORDER BY timestamp""",
            (session_id,),
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
                }
            )
        else:
            result.append(dict(row))
    return result


async def count_messages(
    db: aiosqlite.Connection,
    session_id: str,
) -> int:
    """Return the total number of messages for a session."""
    cursor = await db.execute(
        "SELECT COUNT(*) FROM chat_messages WHERE session_id = ?",
        (session_id,),
    )
    row = await cursor.fetchone()
    return row[0] if row else 0


async def clear_messages(
    db: aiosqlite.Connection,
    session_id: str,
) -> None:
    """Delete all messages for a session."""
    async with transaction(db):
        await db.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))


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
    async with transaction(db):
        await db.execute(
            """INSERT OR REPLACE INTO chat_plans
               (plan_id, session_id, title, summary, status,
                project_id, project_name, repo_owner, repo_name,
                parent_issue_number, parent_issue_url,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                plan.plan_id,
                plan.session_id,
                plan.title,
                plan.summary,
                plan.status.value if hasattr(plan.status, "value") else plan.status,
                plan.project_id,
                plan.project_name,
                plan.repo_owner,
                plan.repo_name,
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
            await db.execute(
                """INSERT INTO chat_plan_steps
                   (step_id, plan_id, position, title, description,
                    dependencies, issue_number, issue_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    step.step_id,
                    plan.plan_id,
                    step.position,
                    step.title,
                    step.description,
                    json.dumps(step.dependencies),
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
        """SELECT plan_id, session_id, title, summary, status,
                  project_id, project_name, repo_owner, repo_name,
                  parent_issue_number, parent_issue_url,
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
            "project_id": row[5],
            "project_name": row[6],
            "repo_owner": row[7],
            "repo_name": row[8],
            "parent_issue_number": row[9],
            "parent_issue_url": row[10],
            "created_at": row[11],
            "updated_at": row[12],
        }
    else:
        plan_dict = dict(row)

    # Fetch steps
    step_cursor = await db.execute(
        """SELECT step_id, plan_id, position, title, description,
                  dependencies, issue_number, issue_url
           FROM chat_plan_steps WHERE plan_id = ?
           ORDER BY position ASC""",
        (plan_id,),
    )
    step_rows = await step_cursor.fetchall()
    steps = []
    for s in step_rows:
        if isinstance(s, tuple):
            steps.append({
                "step_id": s[0],
                "plan_id": s[1],
                "position": s[2],
                "title": s[3],
                "description": s[4],
                "dependencies": json.loads(s[5]) if s[5] else [],
                "issue_number": s[6],
                "issue_url": s[7],
            })
        else:
            d = dict(s)
            raw_deps = d.get("dependencies")
            d["dependencies"] = json.loads(raw_deps) if raw_deps else []
            steps.append(d)

    plan_dict["steps"] = steps
    return plan_dict


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
            f"UPDATE chat_plans SET {', '.join(sets)} WHERE plan_id = ?",
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
