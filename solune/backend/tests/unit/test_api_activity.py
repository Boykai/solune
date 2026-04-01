"""Tests for Activity Feed API (src/api/activity.py).

Covers:
- encode_cursor / decode_cursor — round-trip, invalid data
- query_events — filtering, pagination, cursor handling, falsy-branch coverage
- GET /api/v1/activity — get_activity_feed endpoint
- GET /api/v1/activity/{entity_type}/{entity_id} — get_entity_history endpoint
"""

import base64
import json
from unittest.mock import AsyncMock, patch

import pytest

from src.api.activity import ALLOWED_ENTITY_TYPES
from src.services.activity_service import decode_cursor, encode_cursor, get_activity_stats, query_events

ACTIVITY_URL = "/api/v1/activity"


@pytest.fixture(autouse=True)
def _bypass_activity_project_access():
    """Bypass verify_project_access called directly in activity endpoints."""
    with patch("src.api.activity.verify_project_access", new_callable=AsyncMock):
        yield


# ── Cursor helpers ───────────────────────────────────────────────────────


class TestEncodeCursor:
    def test_round_trip(self):
        ts, eid = "2024-01-01T00:00:00Z", "evt-42"
        encoded = encode_cursor(ts, eid)
        decoded_ts, decoded_id = decode_cursor(encoded)
        assert decoded_ts == ts
        assert decoded_id == eid

    def test_returns_base64_string(self):
        encoded = encode_cursor("2024-01-01T00:00:00Z", "id-1")
        # Should be decodable as base64
        raw = base64.urlsafe_b64decode(encoded.encode())
        parts = json.loads(raw)
        assert len(parts) == 2


class TestDecodeCursor:
    def test_valid_cursor(self):
        payload = json.dumps(["2024-06-15T12:00:00Z", "evt-99"])
        cursor = base64.urlsafe_b64encode(payload.encode()).decode()
        ts, eid = decode_cursor(cursor)
        assert ts == "2024-06-15T12:00:00Z"
        assert eid == "evt-99"

    def test_invalid_base64_raises(self):
        with pytest.raises(ValueError):
            decode_cursor("not-valid-base64!!!")

    def test_invalid_json_raises(self):
        bad_json = base64.urlsafe_b64encode(b"not json").decode()
        with pytest.raises(json.JSONDecodeError):
            decode_cursor(bad_json)

    def test_empty_array_raises(self):
        empty = base64.urlsafe_b64encode(json.dumps([]).encode()).decode()
        with pytest.raises(IndexError):
            decode_cursor(empty)


# ── Activity Feed endpoint ───────────────────────────────────────────────


class TestGetActivityFeed:
    """Tests for GET /api/v1/activity."""

    async def _seed_events(self, db, project_id="PVT_123", count=5):
        """Insert *count* activity events into the test database."""
        for i in range(count):
            await db.execute(
                """INSERT INTO activity_events
                   (id, event_type, entity_type, entity_id, project_id,
                    actor, action, summary, detail, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"evt-{project_id}-{i}",
                    "pipeline_crud",
                    "pipeline",
                    f"pipe-{i}",
                    project_id,
                    "testuser",
                    "created",
                    f"Pipeline {i} created",
                    json.dumps({"index": i}),
                    f"2024-01-01T00:0{i}:00Z",
                ),
            )
        await db.commit()

    async def test_empty_feed(self, client, mock_db):
        resp = await client.get(ACTIVITY_URL, params={"project_id": "PVT_123"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["has_more"] is False
        assert data["total_count"] == 0

    async def test_returns_items(self, client, mock_db):
        await self._seed_events(mock_db, "PVT_123", count=3)
        resp = await client.get(ACTIVITY_URL, params={"project_id": "PVT_123"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 3
        assert data["total_count"] == 3

    async def test_items_ordered_desc(self, client, mock_db):
        await self._seed_events(mock_db, "PVT_123", count=3)
        resp = await client.get(ACTIVITY_URL, params={"project_id": "PVT_123"})
        items = resp.json()["items"]
        timestamps = [item["created_at"] for item in items]
        assert timestamps == sorted(timestamps, reverse=True)

    async def test_limit_respected(self, client, mock_db):
        await self._seed_events(mock_db, "PVT_123", count=5)
        resp = await client.get(ACTIVITY_URL, params={"project_id": "PVT_123", "limit": 2})
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["has_more"] is True
        assert data["next_cursor"] is not None

    async def test_cursor_pagination(self, client, mock_db):
        await self._seed_events(mock_db, "PVT_123", count=5)
        # First page
        resp1 = await client.get(ACTIVITY_URL, params={"project_id": "PVT_123", "limit": 2})
        page1 = resp1.json()
        cursor = page1["next_cursor"]
        assert cursor is not None

        # Second page
        resp2 = await client.get(
            ACTIVITY_URL,
            params={"project_id": "PVT_123", "limit": 2, "cursor": cursor},
        )
        page2 = resp2.json()
        # Second page should have different items
        ids1 = {item["id"] for item in page1["items"]}
        ids2 = {item["id"] for item in page2["items"]}
        assert ids1.isdisjoint(ids2)

    async def test_cursor_page_omits_total_count(self, client, mock_db):
        await self._seed_events(mock_db, "PVT_123", count=5)
        resp1 = await client.get(ACTIVITY_URL, params={"project_id": "PVT_123", "limit": 2})
        cursor = resp1.json()["next_cursor"]

        resp2 = await client.get(
            ACTIVITY_URL,
            params={"project_id": "PVT_123", "limit": 2, "cursor": cursor},
        )
        assert resp2.json()["total_count"] is None

    async def test_event_type_filter(self, client, mock_db):
        # Seed with different event types
        await mock_db.execute(
            """INSERT INTO activity_events
               (id, event_type, entity_type, entity_id, project_id,
                actor, action, summary, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "e1",
                "pipeline_crud",
                "pipeline",
                "p1",
                "PVT_123",
                "user",
                "created",
                "Pipeline created",
                "2024-01-01T00:00:00Z",
            ),
        )
        await mock_db.execute(
            """INSERT INTO activity_events
               (id, event_type, entity_type, entity_id, project_id,
                actor, action, summary, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "e2",
                "tool_crud",
                "tool",
                "t1",
                "PVT_123",
                "user",
                "created",
                "Tool created",
                "2024-01-01T00:01:00Z",
            ),
        )
        await mock_db.commit()

        resp = await client.get(
            ACTIVITY_URL,
            params={"project_id": "PVT_123", "event_type": "pipeline_crud"},
        )
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["event_type"] == "pipeline_crud"

    async def test_multi_event_type_filter(self, client, mock_db):
        for i, et in enumerate(["pipeline_crud", "tool_crud", "chore_crud"]):
            await mock_db.execute(
                """INSERT INTO activity_events
                   (id, event_type, entity_type, entity_id, project_id,
                    actor, action, summary, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"e{i}",
                    et,
                    "pipeline",
                    f"p{i}",
                    "PVT_123",
                    "user",
                    "created",
                    f"Event {i}",
                    f"2024-01-01T00:0{i}:00Z",
                ),
            )
        await mock_db.commit()

        resp = await client.get(
            ACTIVITY_URL,
            params={"project_id": "PVT_123", "event_type": "pipeline_crud,tool_crud"},
        )
        assert len(resp.json()["items"]) == 2

    async def test_invalid_cursor_ignored(self, client, mock_db):
        """Invalid cursor is logged and ignored (no 4xx error)."""
        await self._seed_events(mock_db, "PVT_123", count=2)
        resp = await client.get(
            ACTIVITY_URL,
            params={"project_id": "PVT_123", "cursor": "not-valid-cursor"},
        )
        assert resp.status_code == 200

    async def test_detail_field_parsed_as_json(self, client, mock_db):
        """The detail column is JSON-parsed into a dict on output."""
        await mock_db.execute(
            """INSERT INTO activity_events
               (id, event_type, entity_type, entity_id, project_id,
                actor, action, summary, detail, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "e1",
                "test",
                "pipeline",
                "p1",
                "PVT_123",
                "user",
                "x",
                "s",
                json.dumps({"key": "value"}),
                "2024-01-01T00:00:00Z",
            ),
        )
        await mock_db.commit()

        resp = await client.get(ACTIVITY_URL, params={"project_id": "PVT_123"})
        items = resp.json()["items"]
        assert items[0]["detail"] == {"key": "value"}

    async def test_null_detail_field(self, client, mock_db):
        """Null detail column renders as None."""
        await mock_db.execute(
            """INSERT INTO activity_events
               (id, event_type, entity_type, entity_id, project_id,
                actor, action, summary, detail, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "e1",
                "test",
                "pipeline",
                "p1",
                "PVT_123",
                "user",
                "x",
                "s",
                None,
                "2024-01-01T00:00:00Z",
            ),
        )
        await mock_db.commit()

        resp = await client.get(ACTIVITY_URL, params={"project_id": "PVT_123"})
        assert resp.json()["items"][0]["detail"] is None

    async def test_unparseable_detail_field(self, client, mock_db):
        """Non-JSON detail column becomes None."""
        await mock_db.execute(
            """INSERT INTO activity_events
               (id, event_type, entity_type, entity_id, project_id,
                actor, action, summary, detail, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "e1",
                "test",
                "pipeline",
                "p1",
                "PVT_123",
                "user",
                "x",
                "s",
                "not-json{{{",
                "2024-01-01T00:00:00Z",
            ),
        )
        await mock_db.commit()

        resp = await client.get(ACTIVITY_URL, params={"project_id": "PVT_123"})
        assert resp.json()["items"][0]["detail"] is None

    async def test_project_scoping(self, client, mock_db):
        """Events for other projects are not returned."""
        await self._seed_events(mock_db, "PVT_123", count=2)
        await self._seed_events(mock_db, "PVT_OTHER", count=3)

        resp = await client.get(ACTIVITY_URL, params={"project_id": "PVT_123"})
        assert resp.json()["total_count"] == 2


# ── Entity History endpoint ──────────────────────────────────────────────


class TestGetEntityHistory:
    """Tests for GET /api/v1/activity/{entity_type}/{entity_id}."""

    async def test_valid_entity_type(self, client, mock_db):
        await mock_db.execute(
            """INSERT INTO activity_events
               (id, event_type, entity_type, entity_id, project_id,
                actor, action, summary, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "e1",
                "pipeline_crud",
                "pipeline",
                "pipe-1",
                "PVT_123",
                "user",
                "created",
                "Pipeline created",
                "2024-01-01T00:00:00Z",
            ),
        )
        await mock_db.commit()

        resp = await client.get(
            f"{ACTIVITY_URL}/pipeline/pipe-1",
            params={"project_id": "PVT_123"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    async def test_invalid_entity_type_returns_422(self, client):
        resp = await client.get(
            f"{ACTIVITY_URL}/invalid_type/some-id",
            params={"project_id": "PVT_123"},
        )
        assert resp.status_code == 422
        assert "invalid_type" in resp.json()["error"].lower() or "Invalid" in resp.json()["error"]

    async def test_all_allowed_entity_types(self, client, mock_db):
        """All documented entity types are accepted."""
        for et in ("pipeline", "chore", "agent", "app", "tool", "issue"):
            resp = await client.get(
                f"{ACTIVITY_URL}/{et}/some-id",
                params={"project_id": "PVT_123"},
            )
            assert resp.status_code == 200, f"entity_type={et} rejected"

    async def test_entity_id_scoping(self, client, mock_db):
        """Only events for the specific entity are returned."""
        for i, eid in enumerate(["pipe-1", "pipe-2"]):
            await mock_db.execute(
                """INSERT INTO activity_events
                   (id, event_type, entity_type, entity_id, project_id,
                    actor, action, summary, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"e{i}",
                    "pipeline_crud",
                    "pipeline",
                    eid,
                    "PVT_123",
                    "user",
                    "created",
                    f"Pipeline {eid}",
                    f"2024-01-01T00:0{i}:00Z",
                ),
            )
        await mock_db.commit()

        resp = await client.get(
            f"{ACTIVITY_URL}/pipeline/pipe-1",
            params={"project_id": "PVT_123"},
        )
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["entity_id"] == "pipe-1"

    async def test_empty_history(self, client, mock_db):
        resp = await client.get(
            f"{ACTIVITY_URL}/pipeline/nonexistent",
            params={"project_id": "PVT_123"},
        )
        assert resp.status_code == 200
        assert resp.json()["items"] == []


# ── Branch coverage for query_events ────────────────────────────────────


class TestQueryEventsBranches:
    """Direct tests for query_events to cover falsy-parameter branches.

    Lines 50, 54, 64, 69: when project_id, entity_type, event_type_filter,
    and cursor are None/empty, the corresponding WHERE conditions are skipped.
    """

    @pytest.mark.asyncio
    async def test_no_project_id_omits_project_condition(self, mock_db):
        """When project_id is None, no project_id = ? condition is added."""
        result = await query_events(mock_db, project_id=None)
        assert isinstance(result, dict)
        assert "items" in result

    @pytest.mark.asyncio
    async def test_no_entity_type_omits_entity_condition(self, mock_db):
        """When entity_type is None, no entity_type = ? condition is added."""
        result = await query_events(mock_db, entity_type=None)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_no_entity_id_omits_entity_id_condition(self, mock_db):
        """When entity_id is None, no entity_id = ? condition is added."""
        result = await query_events(mock_db, entity_id=None)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_empty_event_type_filter_after_strip(self, mock_db):
        """Event type filter with only whitespace/commas produces no types (branch 64)."""
        result = await query_events(mock_db, event_type_filter=", , ,")
        assert isinstance(result, dict)
        assert result["items"] == []

    @pytest.mark.asyncio
    async def test_no_cursor_omits_cursor_condition(self, mock_db):
        """When cursor is None, no cursor condition is added."""
        result = await query_events(mock_db, cursor=None)
        assert isinstance(result, dict)
        # total_count should be present on first page (no cursor)
        assert result["total_count"] is not None

    @pytest.mark.asyncio
    async def test_all_params_none_returns_all_events(self, mock_db):
        """When all optional params are None, WHERE is '1=1' (all rows)."""
        result = await query_events(mock_db)
        assert isinstance(result, dict)
        assert result["items"] == []
        assert result["total_count"] == 0

    @pytest.mark.asyncio
    async def test_invalid_cursor_is_logged_and_ignored(self, mock_db):
        """Invalid cursor value is logged but doesn't prevent the query."""
        # Base64-encoded but invalid JSON — triggers JSONDecodeError in decode_cursor
        bad_cursor = base64.urlsafe_b64encode(b"not-json-data").decode()
        result = await query_events(mock_db, cursor=bad_cursor)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_empty_string_event_type_filter(self, mock_db):
        """Empty string event_type_filter is treated as no filter (branch 62)."""
        result = await query_events(mock_db, event_type_filter="")
        assert isinstance(result, dict)


class TestAllowedEntityTypes:
    """Verify the ALLOWED_ENTITY_TYPES constant is correct."""

    def test_expected_entity_types(self):
        assert ALLOWED_ENTITY_TYPES == {"pipeline", "chore", "agent", "app", "tool", "issue"}


# ── Stats endpoint ──────────────────────────────────────────────────────


STATS_URL = f"{ACTIVITY_URL}/stats"


class TestGetActivityStats:
    """Tests for GET /api/v1/activity/stats."""

    @staticmethod
    async def _seed_varied_events(db, project_id: str):
        """Seed events with different event_types for stats grouping."""
        events = [
            ("e1", "pipeline_crud", "pipeline", "p1", "created", "Pipeline created", "2024-01-01T00:00:00Z"),
            ("e2", "pipeline_crud", "pipeline", "p2", "deleted", "Pipeline deleted", "2024-01-01T00:01:00Z"),
            ("e3", "tool_crud", "tool", "t1", "created", "Tool created", "2024-01-01T00:02:00Z"),
            ("e4", "project", "project", "proj1", "created", "Project created", "2024-01-01T00:03:00Z"),
        ]
        for eid, etype, entity_type, entity_id, action, summary, ts in events:
            await db.execute(
                """INSERT INTO activity_events
                   (id, event_type, entity_type, entity_id, project_id,
                    actor, action, summary, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (eid, etype, entity_type, entity_id, project_id, "user", action, summary, ts),
            )
        await db.commit()

    async def test_stats_with_events(self, client, mock_db):
        await self._seed_varied_events(mock_db, "PVT_123")
        resp = await client.get(STATS_URL, params={"project_id": "PVT_123"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 4
        assert data["by_type"] == {"pipeline_crud": 2, "tool_crud": 1, "project": 1}
        assert data["last_event_at"] == "2024-01-01T00:03:00Z"

    async def test_stats_empty_project(self, client, mock_db):
        resp = await client.get(STATS_URL, params={"project_id": "PVT_NONE"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["today"] == 0
        assert data["by_type"] == {}
        assert data["last_event_at"] is None

    async def test_stats_project_scoping(self, client, mock_db):
        """Stats only count events for the requested project."""
        await self._seed_varied_events(mock_db, "PVT_123")
        # Seed a second project with distinct IDs
        events = [
            ("other1", "pipeline_crud", "pipeline", "p1", "created", "P created", "2024-01-01T00:00:00Z"),
            ("other2", "tool_crud", "tool", "t1", "created", "T created", "2024-01-01T00:01:00Z"),
        ]
        for eid, etype, entity_type, entity_id, action, summary, ts in events:
            await mock_db.execute(
                """INSERT INTO activity_events
                   (id, event_type, entity_type, entity_id, project_id,
                    actor, action, summary, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (eid, etype, entity_type, entity_id, "PVT_OTHER", "user", action, summary, ts),
            )
        await mock_db.commit()

        resp = await client.get(STATS_URL, params={"project_id": "PVT_123"})
        assert resp.json()["total"] == 4


# ── Direct service tests for get_activity_stats ─────────────────────────


class TestGetActivityStatsService:
    """Direct tests for the get_activity_stats service function."""

    @pytest.mark.asyncio
    async def test_returns_correct_shape(self, mock_db):
        result = await get_activity_stats(mock_db, project_id="PVT_123")
        assert set(result.keys()) == {"total", "today", "by_type", "last_event_at"}

    @pytest.mark.asyncio
    async def test_empty_db(self, mock_db):
        result = await get_activity_stats(mock_db, project_id="PVT_123")
        assert result["total"] == 0
        assert result["today"] == 0
        assert result["by_type"] == {}
        assert result["last_event_at"] is None

    @pytest.mark.asyncio
    async def test_counts_and_grouping(self, mock_db):
        for i, etype in enumerate(["pipeline_crud", "pipeline_crud", "tool_crud"]):
            await mock_db.execute(
                """INSERT INTO activity_events
                   (id, event_type, entity_type, entity_id, project_id,
                    actor, action, summary, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (f"e{i}", etype, "pipeline", f"p{i}", "PVT_123", "user", "created", f"Evt {i}", f"2024-01-01T00:0{i}:00Z"),
            )
        await mock_db.commit()

        result = await get_activity_stats(mock_db, project_id="PVT_123")
        assert result["total"] == 3
        assert result["by_type"] == {"pipeline_crud": 2, "tool_crud": 1}
        assert result["last_event_at"] == "2024-01-01T00:02:00Z"

    @pytest.mark.asyncio
    async def test_today_count_boundary(self, mock_db):
        """Events inside/outside the 24h window are counted correctly."""
        from unittest.mock import patch as _patch

        # Fix "now" so the 24h boundary is deterministic
        fixed_now = "2024-06-15T12:00:00Z"
        inside_window = "2024-06-15T00:00:00Z"   # 12 h ago – inside
        outside_window = "2024-06-14T11:59:59Z"  # >24 h ago – outside

        for eid, ts in [("in1", inside_window), ("out1", outside_window)]:
            await mock_db.execute(
                """INSERT INTO activity_events
                   (id, event_type, entity_type, entity_id, project_id,
                    actor, action, summary, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (eid, "pipeline_crud", "pipeline", "p1", "PVT_123",
                 "user", "created", f"Evt {eid}", ts),
            )
        await mock_db.commit()

        # Patch SQLite's now() via a deterministic wrapper
        orig_execute = mock_db.execute

        async def _patched_execute(sql, params=()):
            sql = sql.replace("'now'", f"'{fixed_now}'")
            return await orig_execute(sql, params)

        with _patch.object(mock_db, "execute", side_effect=_patched_execute):
            result = await get_activity_stats(mock_db, project_id="PVT_123")

        assert result["total"] == 2
        assert result["today"] == 1
