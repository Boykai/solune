"""Tests for settings API routes (src/api/settings.py).

Covers:
- GET  /api/v1/settings/user                → get_user_settings
- PUT  /api/v1/settings/user                → update_user_settings
- GET  /api/v1/settings/global              → get_global_settings
- PUT  /api/v1/settings/global              → update_global_settings
- GET  /api/v1/settings/project/{id}        → get_project_settings
- PUT  /api/v1/settings/project/{id}        → update_project_settings

NOTE: Settings routes call ``get_db()`` directly (not via Depends).
The conftest patches ``src.api.settings.get_db`` → returns mock_db.
The mock_db needs global_settings seeded to avoid empty-row lookups.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.services.database import seed_global_settings

# ── Helpers ─────────────────────────────────────────────────────────────────


@pytest.fixture
async def seeded_client(client, mock_db):
    """Client fixture with global_settings row seeded (required by settings_store)."""
    await seed_global_settings(mock_db)
    return client


# ── GET /settings/user ──────────────────────────────────────────────────────


class TestUserSettings:
    async def test_get_user_settings_defaults(self, seeded_client):
        resp = await seeded_client.get("/api/v1/settings/user")
        assert resp.status_code == 200
        data = resp.json()
        # Should return fully resolved (global defaults)
        assert "ai" in data
        assert "display" in data
        assert data["ai"]["provider"] == "copilot"
        assert data["display"]["theme"] == "light"

    async def test_update_user_settings(self, seeded_client):
        with patch("src.api.settings.log_event", new_callable=AsyncMock) as mock_log_event:
            resp = await seeded_client.put(
                "/api/v1/settings/user",
                json={"display": {"theme": "dark"}},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["display"]["theme"] == "dark"
        mock_log_event.assert_awaited_once()
        assert mock_log_event.await_args.kwargs["event_type"] == "settings"
        assert mock_log_event.await_args.kwargs["detail"] == {
            "scope": "user",
            "changed_fields": ["theme"],
        }

    async def test_update_user_settings_noop(self, seeded_client):
        """Empty update body returns current settings without changes."""
        resp = await seeded_client.put("/api/v1/settings/user", json={})
        assert resp.status_code == 200
        assert "ai" in resp.json()


# ── GET/PUT /settings/global ───────────────────────────────────────────────


class TestGlobalSettings:
    async def test_get_global_settings(self, seeded_client):
        resp = await seeded_client.get("/api/v1/settings/global")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ai"]["provider"] == "copilot"
        assert data["ai"]["model"] == "gpt-4o"
        assert "allowed_models" in data

    async def test_update_global_settings(self, seeded_client):
        with patch("src.api.settings.log_event", new_callable=AsyncMock) as mock_log_event:
            resp = await seeded_client.put(
                "/api/v1/settings/global",
                json={"ai": {"temperature": 0.5}},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ai"]["temperature"] == 0.5
        mock_log_event.assert_awaited_once()
        assert mock_log_event.await_args.kwargs["detail"] == {
            "scope": "global",
            "changed_fields": ["ai_temperature"],
        }

    async def test_update_global_noop(self, seeded_client):
        resp = await seeded_client.put("/api/v1/settings/global", json={})
        assert resp.status_code == 200


# ── GET/PUT /settings/project/{id} ─────────────────────────────────────────


class TestProjectSettings:
    async def test_get_project_settings_default(self, seeded_client):
        resp = await seeded_client.get("/api/v1/settings/project/PVT_123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["project"]["project_id"] == "PVT_123"
        # Should inherit global + user defaults
        assert "ai" in data
        assert "display" in data

    async def test_update_project_settings(self, seeded_client):
        with patch("src.api.settings.log_event", new_callable=AsyncMock) as mock_log_event:
            resp = await seeded_client.put(
                "/api/v1/settings/project/PVT_123",
                json={
                    "board_display_config": {
                        "column_order": ["Todo", "In Progress", "Done"],
                        "collapsed_columns": [],
                        "show_estimates": True,
                    }
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["project"]["board_display_config"]["show_estimates"] is True
        mock_log_event.assert_awaited_once()
        assert mock_log_event.await_args.kwargs["entity_id"] == "PVT_123"
        assert mock_log_event.await_args.kwargs["detail"] == {
            "scope": "project",
            "changed_fields": ["board_display_config"],
        }

    async def test_update_project_settings_queue_and_auto_merge(self, seeded_client):
        with patch("src.api.settings.log_event", new_callable=AsyncMock) as mock_log:
            resp = await seeded_client.put(
                "/api/v1/settings/project/PVT_123",
                json={"queue_mode": True, "auto_merge": True},
            )

        assert resp.status_code == 200
        mock_log.assert_awaited_once()
        assert mock_log.await_args.kwargs["event_type"] == "settings"
        assert mock_log.await_args.kwargs["entity_id"] == "PVT_123"
        assert mock_log.await_args.kwargs["detail"] == {
            "scope": "project",
            "changed_fields": ["auto_merge", "queue_mode"],
        }

    async def test_update_project_agent_mappings(self, seeded_client):
        resp = await seeded_client.put(
            "/api/v1/settings/project/PVT_123",
            json={
                "agent_pipeline_mappings": {
                    "Backlog": [{"slug": "copilot-swe-agent", "display_name": "Copilot"}]
                }
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        mappings = data["project"]["agent_pipeline_mappings"]
        assert "Backlog" in mappings
