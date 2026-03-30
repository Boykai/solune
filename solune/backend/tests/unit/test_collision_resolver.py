"""Tests for collision detection and resolution strategies.

T019: All resolution strategies in src/services/collision_resolver.py
- detect_collision: no collision (versions match), collision detected
- resolve_collision: user_priority (user beats automation, automation beats user),
                     last_write_wins (newer wins, older wins)
- log_collision_event: successful persist, database error
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from src.models.mcp import CollisionEvent, CollisionOperation
from src.services.collision_resolver import (
    detect_collision,
    log_collision_event,
    resolve_collision,
)


def _make_operation(**overrides) -> CollisionOperation:
    defaults = {
        "operation_id": str(uuid.uuid4()),
        "operation_type": "update",
        "initiated_by": "user",
        "timestamp": datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC),
        "version_expected": 1,
    }
    defaults.update(overrides)
    return CollisionOperation(**defaults)


def _make_collision(op_a=None, op_b=None, **overrides) -> CollisionEvent:
    defaults = {
        "collision_id": str(uuid.uuid4()),
        "target_entity_type": "mcp_config",
        "target_entity_id": "mcp-123",
        "operation_a": op_a or _make_operation(initiated_by="automation"),
        "operation_b": op_b or _make_operation(initiated_by="user"),
        "resolution_strategy": "last_write_wins",
        "resolution_outcome": "",
        "winning_operation": "b",
    }
    defaults.update(overrides)
    return CollisionEvent(**defaults)


class TestDetectCollision:
    def test_no_collision_when_versions_match(self):
        """No collision when incoming version_expected matches current_version."""
        op = _make_operation(version_expected=5)
        result = detect_collision("mcp_config", "mcp-1", op, current_version=5)
        assert result is None

    def test_collision_detected_when_versions_differ(self):
        """Collision returned when version_expected != current_version."""
        op = _make_operation(version_expected=3)
        result = detect_collision("mcp_config", "mcp-1", op, current_version=5)
        assert result is not None
        assert isinstance(result, CollisionEvent)
        assert result.target_entity_type == "mcp_config"
        assert result.target_entity_id == "mcp-1"

    def test_collision_has_incoming_as_operation_b(self):
        """The incoming operation is stored as operation_b in the collision event."""
        op = _make_operation(version_expected=1, initiated_by="user")
        result = detect_collision("mcp_config", "mcp-2", op, current_version=3)
        assert result is not None
        assert result.operation_b is op

    def test_collision_synthetic_operation_a_is_automation(self):
        """The synthetic existing operation is marked as automation."""
        op = _make_operation(version_expected=1)
        result = detect_collision("mcp_config", "mcp-3", op, current_version=2)
        assert result is not None
        assert result.operation_a.initiated_by == "automation"
        assert result.operation_a.version_expected == 2

    def test_collision_is_resolved_before_return(self):
        """detect_collision returns an already-resolved collision event."""
        op = _make_operation(version_expected=1)
        result = detect_collision("mcp_config", "mcp-4", op, current_version=2)
        assert result is not None
        assert result.resolved_at is not None
        assert result.resolution_outcome != ""


class TestResolveCollision:
    def test_user_beats_automation(self):
        """User-initiated operation takes precedence over automation (FR-018)."""
        op_a = _make_operation(initiated_by="automation")
        op_b = _make_operation(initiated_by="user")
        collision = _make_collision(op_a=op_a, op_b=op_b)

        result = resolve_collision(collision)

        assert result.resolution_strategy == "user_priority"
        assert result.winning_operation == "b"
        assert "User-initiated" in result.resolution_outcome
        assert result.resolved_at is not None

    def test_automation_loses_to_user_in_position_a(self):
        """When user is operation_a and automation is operation_b, user (a) wins."""
        op_a = _make_operation(initiated_by="user")
        op_b = _make_operation(initiated_by="automation")
        collision = _make_collision(op_a=op_a, op_b=op_b)

        result = resolve_collision(collision)

        assert result.resolution_strategy == "user_priority"
        assert result.winning_operation == "a"
        assert "User-initiated" in result.resolution_outcome

    def test_last_write_wins_newer_b(self):
        """When both same type, later timestamp (b) wins."""
        t1 = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
        t2 = t1 + timedelta(seconds=30)
        op_a = _make_operation(initiated_by="user", timestamp=t1)
        op_b = _make_operation(initiated_by="user", timestamp=t2)
        collision = _make_collision(op_a=op_a, op_b=op_b)

        result = resolve_collision(collision)

        assert result.resolution_strategy == "last_write_wins"
        assert result.winning_operation == "b"
        assert "Later operation" in result.resolution_outcome

    def test_last_write_wins_older_b(self):
        """When both same type and a is newer, a wins."""
        t1 = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
        t2 = t1 - timedelta(seconds=30)
        op_a = _make_operation(initiated_by="automation", timestamp=t1)
        op_b = _make_operation(initiated_by="automation", timestamp=t2)
        collision = _make_collision(op_a=op_a, op_b=op_b)

        result = resolve_collision(collision)

        assert result.resolution_strategy == "last_write_wins"
        assert result.winning_operation == "a"

    def test_last_write_wins_equal_timestamps(self):
        """Equal timestamps — b wins (tie-breaker)."""
        t = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
        op_a = _make_operation(initiated_by="user", timestamp=t)
        op_b = _make_operation(initiated_by="user", timestamp=t)
        collision = _make_collision(op_a=op_a, op_b=op_b)

        result = resolve_collision(collision)

        assert result.resolution_strategy == "last_write_wins"
        assert result.winning_operation == "b"

    def test_resolved_at_is_set(self):
        """All resolution strategies set resolved_at."""
        collision = _make_collision()
        result = resolve_collision(collision)
        assert result.resolved_at is not None


class TestLogCollisionEvent:
    @pytest.mark.asyncio
    async def test_persists_collision_to_database(self):
        """log_collision_event inserts a row into collision_events table."""
        db = AsyncMock()
        collision = _make_collision()
        collision.resolved_at = datetime(2026, 1, 15, 12, 1, 0, tzinfo=UTC)

        await log_collision_event(db, collision)

        db.execute.assert_awaited_once()
        call_args = db.execute.call_args
        sql = call_args[0][0]
        assert "INSERT INTO collision_events" in sql
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_persists_operation_json(self):
        """Operations are serialized as JSON in the database row."""
        db = AsyncMock()
        collision = _make_collision()
        collision.resolved_at = datetime(2026, 1, 15, 12, 1, 0, tzinfo=UTC)

        await log_collision_event(db, collision)

        params = db.execute.call_args[0][1]
        # op_a_json is the 4th param, op_b_json is the 5th
        op_a_data = json.loads(params[3])
        op_b_data = json.loads(params[4])
        assert "operation_id" in op_a_data
        assert "operation_id" in op_b_data

    @pytest.mark.asyncio
    async def test_handles_none_resolved_at(self):
        """log_collision_event handles collision with no resolved_at."""
        db = AsyncMock()
        collision = _make_collision()
        collision.resolved_at = None

        await log_collision_event(db, collision)

        params = db.execute.call_args[0][1]
        # resolved_at is the last parameter
        assert params[-1] is None

    @pytest.mark.asyncio
    async def test_swallows_database_errors(self):
        """Database errors are logged but don't propagate."""
        db = AsyncMock()
        db.execute.side_effect = RuntimeError("table not found")
        collision = _make_collision()
        collision.resolved_at = datetime(2026, 1, 15, 12, 1, 0, tzinfo=UTC)

        # Should not raise
        await log_collision_event(db, collision)
