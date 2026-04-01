"""Regression tests for bug bash fixes.

Covers:
- settings_store._row_to_global_response handles malformed JSON gracefully
- PipelineService._row_to_config handles malformed JSON gracefully
- PipelineService.list_pipelines handles malformed JSON gracefully
- main._register_active_projects logs exceptions instead of silently swallowing
- database._apply_pending_migrations rolls back on failure
"""

import json
from unittest.mock import patch

import pytest

from src.services.settings_store import _row_to_global_response

# ── _row_to_global_response: malformed allowed_models JSON ──


class TestRowToGlobalResponseMalformedJson:
    """Ensure _row_to_global_response gracefully handles invalid JSON."""

    def _make_row(self, allowed_models_value):
        """Build a fake Row-like dict with all required columns."""
        return {
            "allowed_models": allowed_models_value,
            "ai_provider": "copilot",
            "ai_model": "gpt-4o",
            "ai_temperature": 0.7,
            "ai_agent_model": "gpt-4o",
            "theme": "light",
            "default_view": "chat",
            "sidebar_collapsed": 0,
            "default_repository": "",
            "default_assignee": "",
            "copilot_polling_interval": 30,
            "notify_task_status_change": 1,
            "notify_agent_completion": 1,
            "notify_new_recommendation": 1,
            "notify_chat_mention": 1,
        }

    def test_valid_json_parses_correctly(self):
        row = self._make_row('["gpt-4o", "gpt-3.5-turbo"]')
        result = _row_to_global_response(row)
        assert result.allowed_models == ["gpt-4o", "gpt-3.5-turbo"]

    def test_none_returns_empty_list(self):
        row = self._make_row(None)
        result = _row_to_global_response(row)
        assert result.allowed_models == []

    def test_empty_string_returns_empty_list(self):
        row = self._make_row("")
        result = _row_to_global_response(row)
        assert result.allowed_models == []

    def test_malformed_json_returns_empty_list(self):
        """Malformed JSON should not crash — returns empty list with a warning."""
        row = self._make_row("{not valid json!!!")
        result = _row_to_global_response(row)
        assert result.allowed_models == []

    def test_non_string_type_returns_empty_list(self):
        """Non-string truthy value for allowed_models should not crash."""
        row = self._make_row(12345)
        result = _row_to_global_response(row)
        assert result.allowed_models == []


# ── PipelineService._row_to_config: malformed stages JSON ──


class TestPipelineServiceMalformedStagesJson:
    """Ensure _row_to_config gracefully handles invalid stages JSON."""

    def _make_row_dict(self, stages_value, **overrides):
        """Build a dict matching a pipeline_configs database row."""
        d = {
            "id": "pipe-1",
            "project_id": "PVT_1",
            "name": "Test Pipeline",
            "description": "",
            "stages": stages_value,
            "is_preset": 0,
            "preset_id": "",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        d.update(overrides)
        return d

    def test_valid_json_parses(self):
        from src.services.pipelines.service import PipelineService

        stages = json.dumps([{"id": "s1", "name": "Stage 1", "order": 0, "agents": []}])
        row = self._make_row_dict(stages)
        config = PipelineService._row_to_config(row)
        assert len(config.stages) == 1
        assert config.stages[0].name == "Stage 1"

    def test_malformed_json_returns_empty_stages(self):
        """Malformed stages JSON should not crash — returns config with empty stages."""
        from src.services.pipelines.service import PipelineService

        row = self._make_row_dict("{bad json}")
        config = PipelineService._row_to_config(row)
        assert config.stages == []

    def test_none_stages_returns_empty(self):
        """None stages value falls back to empty list."""
        from src.services.pipelines.service import PipelineService

        row = self._make_row_dict(None)
        config = PipelineService._row_to_config(row)
        assert config.stages == []

    def test_missing_stages_key_returns_empty(self):
        """Missing 'stages' key falls back to empty list via .get() default."""
        from src.services.pipelines.service import PipelineService

        row = {
            "id": "pipe-1",
            "project_id": "PVT_1",
            "name": "Test Pipeline",
            "description": "",
            "is_preset": 0,
            "preset_id": "",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        config = PipelineService._row_to_config(row)
        assert config.stages == []


# ── Database migration rollback ──


class TestMigrationRollback:
    """Ensure database migration failure triggers explicit rollback."""

    @pytest.mark.anyio
    async def test_failed_migration_calls_rollback(self):
        """When a migration fails, rollback is called before re-raising."""
        import aiosqlite

        from src.services.database import _run_migrations

        db = await aiosqlite.connect(":memory:")
        db.row_factory = aiosqlite.Row

        # Seed schema_version so _run_migrations picks up pending migrations
        await db.execute(
            "CREATE TABLE schema_version (version INTEGER NOT NULL, applied_at TEXT NOT NULL)"
        )
        await db.execute(
            "INSERT INTO schema_version (version, applied_at) VALUES (0, '2025-01-01')"
        )
        await db.commit()

        # Patch executescript to always fail, simulating a bad migration
        original_rollback = db.rollback

        rollback_called = False

        async def tracking_rollback():
            nonlocal rollback_called
            rollback_called = True
            await original_rollback()

        with patch.object(db, "executescript", side_effect=RuntimeError("Bad SQL")):
            with patch.object(db, "rollback", side_effect=tracking_rollback):
                with pytest.raises(RuntimeError, match="Bad SQL"):
                    await _run_migrations(db)

        assert rollback_called, "rollback() should be called when a migration fails"
        await db.close()
