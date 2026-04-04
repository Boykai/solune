"""Tests for src.services.activity_logger — fire-and-forget event logging."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from src.services.activity_logger import log_event


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    return db


class TestLogEvent:
    @pytest.mark.asyncio
    async def test_inserts_row_with_required_fields(self, mock_db: AsyncMock) -> None:
        await log_event(
            mock_db,
            event_type="task_status_change",
            entity_type="issue",
            entity_id="ISSUE-1",
            project_id="PROJ-1",
            action="moved",
            summary="Moved issue to Done",
        )
        mock_db.execute.assert_awaited_once()
        args = mock_db.execute.call_args
        sql = args[0][0]
        params = args[0][1]
        assert "INSERT INTO activity_events" in sql
        assert params[1] == "task_status_change"
        assert params[2] == "issue"
        assert params[3] == "ISSUE-1"
        assert params[4] == "PROJ-1"
        assert params[5] == "system"  # default actor
        assert params[6] == "moved"
        assert params[7] == "Moved issue to Done"
        assert params[8] is None  # no detail
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_serializes_detail_dict_as_json(self, mock_db: AsyncMock) -> None:
        detail = {"old_status": "In Progress", "new_status": "Done"}
        await log_event(
            mock_db,
            event_type="task_status_change",
            entity_type="issue",
            entity_id="ISSUE-1",
            project_id="PROJ-1",
            action="moved",
            summary="Moved",
            detail=detail,
        )
        params = mock_db.execute.call_args[0][1]
        assert params[8] == json.dumps(detail)

    @pytest.mark.asyncio
    async def test_custom_actor_passed_through(self, mock_db: AsyncMock) -> None:
        await log_event(
            mock_db,
            event_type="agent_run",
            entity_type="pipeline",
            entity_id="P-1",
            project_id="PROJ-1",
            actor="copilot-bot",
            action="started",
            summary="Pipeline started",
        )
        params = mock_db.execute.call_args[0][1]
        assert params[5] == "copilot-bot"

    @pytest.mark.asyncio
    async def test_generates_uuid_event_id(self, mock_db: AsyncMock) -> None:
        await log_event(
            mock_db,
            event_type="task_status_change",
            entity_type="issue",
            entity_id="ISSUE-1",
            project_id="PROJ-1",
            action="moved",
            summary="Moved",
        )
        params = mock_db.execute.call_args[0][1]
        event_id = params[0]
        # UUID format: 8-4-4-4-12 hex chars
        assert len(event_id) == 36
        parts = event_id.split("-")
        assert len(parts) == 5

    @pytest.mark.asyncio
    async def test_never_raises_on_db_error(self, mock_db: AsyncMock) -> None:
        """log_event must swallow exceptions — it's fire-and-forget."""
        mock_db.execute.side_effect = RuntimeError("DB connection lost")
        # Should not raise
        await log_event(
            mock_db,
            event_type="task_status_change",
            entity_type="issue",
            entity_id="ISSUE-1",
            project_id="PROJ-1",
            action="moved",
            summary="Moved",
        )

    @pytest.mark.asyncio
    async def test_never_raises_on_commit_error(self, mock_db: AsyncMock) -> None:
        mock_db.commit.side_effect = RuntimeError("Commit failed")
        await log_event(
            mock_db,
            event_type="task_status_change",
            entity_type="issue",
            entity_id="ISSUE-1",
            project_id="PROJ-1",
            action="moved",
            summary="Moved",
        )

    @pytest.mark.asyncio
    async def test_none_detail_stored_as_null(self, mock_db: AsyncMock) -> None:
        await log_event(
            mock_db,
            event_type="test",
            entity_type="issue",
            entity_id="1",
            project_id="P",
            action="test",
            summary="test",
            detail=None,
        )
        params = mock_db.execute.call_args[0][1]
        assert params[8] is None
