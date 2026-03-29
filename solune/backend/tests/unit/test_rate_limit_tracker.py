"""Tests for RateLimitTracker (src/services/rate_limit_tracker.py).

Covers:
- _ensure_table — idempotent DDL
- record_snapshot — insert + 24h pruning
- get_history — time-window queries
- get_tracker — module singleton
"""

from unittest.mock import patch

import pytest

from src.services.rate_limit_tracker import RateLimitTracker, get_tracker


@pytest.fixture
async def tracker(mock_db):
    """RateLimitTracker wired to the in-memory test database."""
    t = RateLimitTracker()
    t._table_ready = False
    with patch(
        "src.services.rate_limit_tracker.RateLimitTracker._ensure_table", wraps=t._ensure_table
    ):
        with patch("src.services.database.get_db", return_value=mock_db):
            yield t


class TestEnsureTable:
    async def test_creates_table(self, mock_db):
        t = RateLimitTracker()
        t._table_ready = False
        with patch("src.services.database.get_db", return_value=mock_db):
            await t._ensure_table()
        # Table should exist
        cursor = await mock_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='rate_limit_snapshots'"
        )
        row = await cursor.fetchone()
        assert row is not None

    async def test_idempotent(self, mock_db):
        t = RateLimitTracker()
        t._table_ready = False
        with patch("src.services.database.get_db", return_value=mock_db):
            await t._ensure_table()
            await t._ensure_table()  # second call is a no-op
        assert t._table_ready is True

    async def test_skips_when_already_ready(self, mock_db):
        t = RateLimitTracker()
        t._table_ready = True
        # Should not call get_db at all
        with patch(
            "src.services.database.get_db", side_effect=RuntimeError("should not be called")
        ):
            await t._ensure_table()


class TestRecordSnapshot:
    async def test_inserts_row(self, mock_db):
        t = RateLimitTracker()
        t._table_ready = False
        with patch("src.services.database.get_db", return_value=mock_db):
            await t.record_snapshot(remaining=4500, limit=5000, reset_at=1700000000)
        cursor = await mock_db.execute(
            'SELECT remaining, "limit", reset_at FROM rate_limit_snapshots'
        )
        rows = await cursor.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == 4500
        assert rows[0][1] == 5000
        assert rows[0][2] == 1700000000

    async def test_multiple_inserts(self, mock_db):
        t = RateLimitTracker()
        t._table_ready = False
        with patch("src.services.database.get_db", return_value=mock_db):
            await t.record_snapshot(remaining=4500, limit=5000, reset_at=1700000000)
            await t.record_snapshot(remaining=4499, limit=5000, reset_at=1700000001)
        cursor = await mock_db.execute("SELECT COUNT(*) FROM rate_limit_snapshots")
        row = await cursor.fetchone()
        assert row[0] == 2

    async def test_prunes_old_rows(self, mock_db):
        t = RateLimitTracker()
        t._table_ready = False
        with patch("src.services.database.get_db", return_value=mock_db):
            await t._ensure_table()
        # Manually insert an old row (48 hours ago)
        await mock_db.execute(
            'INSERT INTO rate_limit_snapshots (timestamp, remaining, "limit", reset_at) '
            "VALUES (strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-48 hours'), 100, 5000, 0)"
        )
        await mock_db.commit()

        with patch("src.services.database.get_db", return_value=mock_db):
            await t.record_snapshot(remaining=4500, limit=5000, reset_at=1700000000)

        cursor = await mock_db.execute("SELECT COUNT(*) FROM rate_limit_snapshots")
        row = await cursor.fetchone()
        # Old row should be pruned, only the new one remains
        assert row[0] == 1


class TestGetHistory:
    async def test_returns_empty_when_no_data(self, mock_db):
        t = RateLimitTracker()
        t._table_ready = False
        with patch("src.services.database.get_db", return_value=mock_db):
            result = await t.get_history(hours=24)
        assert result == []

    async def test_returns_recent_snapshots(self, mock_db):
        t = RateLimitTracker()
        t._table_ready = False
        with patch("src.services.database.get_db", return_value=mock_db):
            await t.record_snapshot(remaining=4500, limit=5000, reset_at=1700000000)
            await t.record_snapshot(remaining=4400, limit=5000, reset_at=1700000001)
            result = await t.get_history(hours=24)
        assert len(result) == 2
        assert result[0]["remaining"] == 4500
        assert result[1]["remaining"] == 4400

    async def test_history_has_correct_keys(self, mock_db):
        t = RateLimitTracker()
        t._table_ready = False
        with patch("src.services.database.get_db", return_value=mock_db):
            await t.record_snapshot(remaining=4500, limit=5000, reset_at=1700000000)
            result = await t.get_history(hours=24)
        entry = result[0]
        assert "timestamp" in entry
        assert "remaining" in entry
        assert "limit" in entry
        assert "reset_at" in entry

    async def test_history_ordered_asc(self, mock_db):
        t = RateLimitTracker()
        t._table_ready = False
        with patch("src.services.database.get_db", return_value=mock_db):
            await t.record_snapshot(remaining=4500, limit=5000, reset_at=1700000000)
            await t.record_snapshot(remaining=4400, limit=5000, reset_at=1700000001)
            result = await t.get_history(hours=24)
        timestamps = [r["timestamp"] for r in result]
        assert timestamps == sorted(timestamps)


class TestGetTracker:
    def test_returns_same_instance(self):
        t1 = get_tracker()
        t2 = get_tracker()
        assert t1 is t2

    def test_returns_RateLimitTracker(self):
        t = get_tracker()
        assert isinstance(t, RateLimitTracker)
