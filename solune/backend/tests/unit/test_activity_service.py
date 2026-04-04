"""Tests for src.services.activity_service — activity event queries."""

from __future__ import annotations

import base64
import json
from unittest.mock import AsyncMock

import pytest

from src.services.activity_service import (
    decode_cursor,
    encode_cursor,
    get_activity_stats,
    query_events,
)


class TestEncodeCursor:
    def test_roundtrip(self) -> None:
        ts = "2025-01-15T12:00:00Z"
        eid = "abc-123"
        encoded = encode_cursor(ts, eid)
        decoded_ts, decoded_id = decode_cursor(encoded)
        assert decoded_ts == ts
        assert decoded_id == eid

    def test_produces_base64_string(self) -> None:
        encoded = encode_cursor("2025-01-01T00:00:00Z", "id-1")
        # Should be valid base64
        raw = base64.urlsafe_b64decode(encoded.encode()).decode()
        parsed = json.loads(raw)
        assert isinstance(parsed, list)
        assert len(parsed) == 2


class TestDecodeCursor:
    def test_valid_cursor(self) -> None:
        raw = json.dumps(["2025-01-15T12:00:00Z", "event-1"])
        encoded = base64.urlsafe_b64encode(raw.encode()).decode()
        ts, eid = decode_cursor(encoded)
        assert ts == "2025-01-15T12:00:00Z"
        assert eid == "event-1"

    def test_invalid_base64_raises(self) -> None:
        with pytest.raises(Exception):
            decode_cursor("not-valid-base64!!!")

    def test_invalid_json_raises(self) -> None:
        encoded = base64.urlsafe_b64encode(b"not json").decode()
        with pytest.raises(json.JSONDecodeError):
            decode_cursor(encoded)


def _make_mock_db(rows: list[tuple], count: int = 0) -> AsyncMock:
    """Create a mock db connection returning given rows."""
    db = AsyncMock()
    cursor = AsyncMock()
    cursor.fetchall = AsyncMock(return_value=rows)
    cursor.fetchone = AsyncMock(return_value=(count,))
    db.execute = AsyncMock(return_value=cursor)
    return db


class TestQueryEvents:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_rows(self) -> None:
        db = _make_mock_db([], count=0)
        result = await query_events(db, project_id="P1")
        assert result["items"] == []
        assert result["has_more"] is False
        assert result["next_cursor"] is None

    @pytest.mark.asyncio
    async def test_returns_items_from_rows(self) -> None:
        row = (
            "evt-1",
            "task_status_change",
            "issue",
            "ISSUE-1",
            "PROJ-1",
            "system",
            "moved",
            "Moved to Done",
            None,
            "2025-01-15T12:00:00Z",
        )
        db = _make_mock_db([row], count=1)
        result = await query_events(db, project_id="PROJ-1", limit=50)
        assert len(result["items"]) == 1
        item = result["items"][0]
        assert item["id"] == "evt-1"
        assert item["event_type"] == "task_status_change"
        assert item["entity_type"] == "issue"

    @pytest.mark.asyncio
    async def test_has_more_when_extra_row(self) -> None:
        rows = [
            (f"evt-{i}", "test", "issue", f"I-{i}", "P1", "system", "a", "s", None, f"2025-01-{i:02d}T00:00:00Z")
            for i in range(3)
        ]
        db = _make_mock_db(rows, count=3)
        result = await query_events(db, project_id="P1", limit=2)
        assert result["has_more"] is True
        assert result["next_cursor"] is not None

    @pytest.mark.asyncio
    async def test_filters_by_entity_type(self) -> None:
        db = _make_mock_db([], count=0)
        await query_events(db, entity_type="pipeline")
        sql = db.execute.call_args_list[0][0][0]
        assert "entity_type = ?" in sql

    @pytest.mark.asyncio
    async def test_filters_by_event_type(self) -> None:
        db = _make_mock_db([], count=0)
        await query_events(db, event_type_filter="task_status_change,agent_run")
        sql = db.execute.call_args_list[0][0][0]
        assert "event_type IN" in sql

    @pytest.mark.asyncio
    async def test_invalid_cursor_ignored(self) -> None:
        db = _make_mock_db([], count=0)
        # Use valid base64 but invalid JSON to hit the warning path
        import base64

        bad_cursor = base64.urlsafe_b64encode(b"not json").decode()
        result = await query_events(db, project_id="P1", cursor=bad_cursor)
        assert result["items"] == []

    @pytest.mark.asyncio
    async def test_detail_json_parsed(self) -> None:
        detail = json.dumps({"key": "value"})
        row = ("evt-1", "test", "issue", "I-1", "P1", "system", "a", "s", detail, "2025-01-01T00:00:00Z")
        db = _make_mock_db([row], count=1)
        result = await query_events(db, project_id="P1")
        assert result["items"][0]["detail"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_malformed_detail_json_returns_none(self) -> None:
        row = ("evt-1", "test", "issue", "I-1", "P1", "system", "a", "s", "not-json", "2025-01-01T00:00:00Z")
        db = _make_mock_db([row], count=1)
        result = await query_events(db, project_id="P1")
        assert result["items"][0]["detail"] is None

    @pytest.mark.asyncio
    async def test_total_count_returned_on_first_page(self) -> None:
        db = _make_mock_db([], count=42)
        result = await query_events(db, project_id="P1")
        assert result["total_count"] == 42

    @pytest.mark.asyncio
    async def test_total_count_none_when_cursor_provided(self) -> None:
        cursor = encode_cursor("2025-01-15T12:00:00Z", "evt-1")
        db = _make_mock_db([], count=0)
        result = await query_events(db, project_id="P1", cursor=cursor)
        assert result["total_count"] is None


class TestGetActivityStats:
    @pytest.mark.asyncio
    async def test_returns_stats_dict(self) -> None:
        db = AsyncMock()
        # First call: total_count + last_event_at
        total_cursor = AsyncMock()
        total_cursor.fetchone = AsyncMock(return_value=(10, "2025-01-15T12:00:00Z"))
        # Second call: today_count
        today_cursor = AsyncMock()
        today_cursor.fetchone = AsyncMock(return_value=(3,))
        # Third call: by_type
        by_type_cursor = AsyncMock()
        by_type_cursor.fetchall = AsyncMock(return_value=[("task_status_change", 5), ("agent_run", 2)])

        db.execute = AsyncMock(side_effect=[total_cursor, today_cursor, by_type_cursor])

        result = await get_activity_stats(db, project_id="P1")
        assert result["total_count"] == 10
        assert result["today_count"] == 3
        assert result["by_type"] == {"task_status_change": 5, "agent_run": 2}
        assert result["last_event_at"] == "2025-01-15T12:00:00Z"

    @pytest.mark.asyncio
    async def test_handles_no_events(self) -> None:
        db = AsyncMock()
        total_cursor = AsyncMock()
        total_cursor.fetchone = AsyncMock(return_value=(0, None))
        today_cursor = AsyncMock()
        today_cursor.fetchone = AsyncMock(return_value=(0,))
        by_type_cursor = AsyncMock()
        by_type_cursor.fetchall = AsyncMock(return_value=[])

        db.execute = AsyncMock(side_effect=[total_cursor, today_cursor, by_type_cursor])

        result = await get_activity_stats(db, project_id="P1")
        assert result["total_count"] == 0
        assert result["today_count"] == 0
        assert result["by_type"] == {}
        assert result["last_event_at"] is None
