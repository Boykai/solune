"""Tests for Chores API routes (src/api/chores.py).

Covers:
- POST   /{project_id}/seed-presets       → seed_presets
- POST   /evaluate-triggers               → evaluate_triggers
- GET    /{project_id}/templates           → list_templates
- GET    /{project_id}/chore-names         → list_chore_names
- GET    /{project_id}                     → list_chores (incl. filtering, sorting, pagination)
- POST   /{project_id}                     → create_chore
- PATCH  /{project_id}/{chore_id}          → update_chore
- DELETE /{project_id}/{chore_id}          → delete_chore
- POST   /{project_id}/{chore_id}/trigger  → trigger_chore
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.chores import Chore, ChoreStatus, ChoreTriggerResult, ScheduleType

_API = "src.api.chores"


def _make_chore(**overrides) -> Chore:
    defaults = {
        "id": "chore-1",
        "project_id": "PVT_123",
        "name": "Update Dependencies",
        "template_path": ".github/ISSUE_TEMPLATE/chore-update-deps.md",
        "template_content": "---\nname: Update Dependencies\n---\nUpdate all deps",
        "status": ChoreStatus.ACTIVE,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    defaults.update(overrides)
    return Chore(**defaults)


# ── POST /seed-presets ────────────────────────────────────────────────────


class TestSeedPresets:
    async def test_seed_presets_success(self, client):
        mock_service = MagicMock()
        mock_service.seed_presets = AsyncMock(return_value=["preset-1", "preset-2"])

        with (
            patch(f"{_API}.resolve_repository", AsyncMock(return_value=("octo", "widgets"))),
            patch(f"{_API}._get_service", return_value=mock_service),
        ):
            resp = await client.post("/api/v1/chores/PVT_123/seed-presets")

        assert resp.status_code == 200
        assert resp.json()["created"] == 2

    async def test_seed_presets_empty(self, client):
        mock_service = MagicMock()
        mock_service.seed_presets = AsyncMock(return_value=[])

        with (
            patch(f"{_API}.resolve_repository", AsyncMock(return_value=("octo", "widgets"))),
            patch(f"{_API}._get_service", return_value=mock_service),
        ):
            resp = await client.post("/api/v1/chores/PVT_123/seed-presets")

        assert resp.status_code == 200
        assert resp.json()["created"] == 0


# ── POST /evaluate-triggers ──────────────────────────────────────────────


class TestEvaluateTriggers:
    async def test_evaluate_triggers_no_project_id(self, client):
        resp = await client.post("/api/v1/chores/evaluate-triggers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["evaluated"] == 0

    async def test_evaluate_triggers_success(self, client, mock_github_service):
        mock_service = MagicMock()
        mock_service.evaluate_triggers = AsyncMock(
            return_value={"evaluated": 3, "triggered": 1, "skipped": 2, "results": []}
        )
        with (
            patch(f"{_API}.resolve_repository", AsyncMock(return_value=("octo", "widgets"))),
            patch(f"{_API}._get_service", return_value=mock_service),
        ):
            resp = await client.post(
                "/api/v1/chores/evaluate-triggers",
                json={"project_id": "PVT_123"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["evaluated"] == 3
        assert data["triggered"] == 1


# ── GET /templates ────────────────────────────────────────────────────────


class TestListTemplates:
    async def test_templates_success(self, client, mock_github_service):
        mock_github_service.get_directory_contents = AsyncMock(
            return_value=[
                {
                    "name": "chore-update-deps.md",
                    "path": ".github/ISSUE_TEMPLATE/chore-update-deps.md",
                },
            ]
        )
        mock_github_service.get_file_content = AsyncMock(
            return_value={
                "content": "---\nname: Update Dependencies\nabout: Update all deps\n---\nBody"
            }
        )
        with patch(f"{_API}.resolve_repository", AsyncMock(return_value=("octo", "widgets"))):
            resp = await client.get("/api/v1/chores/PVT_123/templates")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Update Dependencies"
        assert data[0]["about"] == "Update all deps"

    async def test_templates_resolve_failure_returns_empty(self, client):
        with patch(f"{_API}.resolve_repository", AsyncMock(side_effect=RuntimeError("fail"))):
            resp = await client.get("/api/v1/chores/PVT_123/templates")

        assert resp.status_code == 200
        assert resp.json() == []

    async def test_templates_skips_non_chore_files(self, client, mock_github_service):
        mock_github_service.get_directory_contents = AsyncMock(
            return_value=[
                {"name": "bug_report.md", "path": ".github/ISSUE_TEMPLATE/bug_report.md"},
                {"name": "chore-lint.md", "path": ".github/ISSUE_TEMPLATE/chore-lint.md"},
            ]
        )
        mock_github_service.get_file_content = AsyncMock(
            return_value={"content": "---\nname: Lint\n---\nLint body"}
        )
        with patch(f"{_API}.resolve_repository", AsyncMock(return_value=("octo", "widgets"))):
            resp = await client.get("/api/v1/chores/PVT_123/templates")

        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["name"] == "Lint"

    async def test_templates_skips_null_content(self, client, mock_github_service):
        mock_github_service.get_directory_contents = AsyncMock(
            return_value=[
                {"name": "chore-empty.md", "path": ".github/ISSUE_TEMPLATE/chore-empty.md"},
            ]
        )
        mock_github_service.get_file_content = AsyncMock(return_value=None)
        with patch(f"{_API}.resolve_repository", AsyncMock(return_value=("octo", "widgets"))):
            resp = await client.get("/api/v1/chores/PVT_123/templates")

        assert resp.status_code == 200
        assert resp.json() == []


# ── GET /chore-names ─────────────────────────────────────────────────────


class TestListChoreNames:
    async def test_list_names(self, client):
        chores = [_make_chore(id=f"c-{i}", name=f"Chore {i}") for i in range(3)]
        mock_service = MagicMock()
        mock_service.list_chores = AsyncMock(return_value=chores)

        with (
            patch(f"{_API}.resolve_repository", AsyncMock(return_value=("octo", "widgets"))),
            patch(f"{_API}._get_service", return_value=mock_service),
        ):
            resp = await client.get("/api/v1/chores/PVT_123/chore-names")

        assert resp.status_code == 200
        assert resp.json() == ["Chore 0", "Chore 1", "Chore 2"]


# ── GET /{project_id} (list) ─────────────────────────────────────────────


class TestListChores:
    @pytest.fixture(autouse=True)
    def _patch(self):
        self.mock_service = MagicMock()
        with (
            patch(f"{_API}.resolve_repository", AsyncMock(return_value=("octo", "widgets"))),
            patch(f"{_API}._get_service", return_value=self.mock_service),
        ):
            yield

    async def test_list_all(self, client):
        chores = [_make_chore(id=f"c-{i}", name=f"Chore {i}") for i in range(2)]
        self.mock_service.list_chores = AsyncMock(return_value=chores)
        resp = await client.get("/api/v1/chores/PVT_123")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_filter_by_status(self, client):
        chores = [
            _make_chore(id="c-1", name="Active", status=ChoreStatus.ACTIVE),
            _make_chore(id="c-2", name="Paused", status=ChoreStatus.PAUSED),
        ]
        self.mock_service.list_chores = AsyncMock(return_value=chores)
        resp = await client.get("/api/v1/chores/PVT_123", params={"status": "paused"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Paused"

    async def test_filter_by_schedule_type(self, client):
        chores = [
            _make_chore(
                id="c-1", name="Scheduled", schedule_type=ScheduleType.TIME, schedule_value=7
            ),
            _make_chore(id="c-2", name="Unscheduled"),
        ]
        self.mock_service.list_chores = AsyncMock(return_value=chores)
        resp = await client.get("/api/v1/chores/PVT_123", params={"schedule_type": "unscheduled"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Unscheduled"

    async def test_filter_by_schedule_type_time(self, client):
        chores = [
            _make_chore(id="c-1", name="Timed", schedule_type=ScheduleType.TIME, schedule_value=7),
            _make_chore(
                id="c-2", name="Counted", schedule_type=ScheduleType.COUNT, schedule_value=10
            ),
        ]
        self.mock_service.list_chores = AsyncMock(return_value=chores)
        resp = await client.get("/api/v1/chores/PVT_123", params={"schedule_type": "time"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Timed"

    async def test_search_filter(self, client):
        chores = [
            _make_chore(id="c-1", name="Update Deps", template_path="chore-update-deps.md"),
            _make_chore(id="c-2", name="Lint Code", template_path="chore-lint.md"),
        ]
        self.mock_service.list_chores = AsyncMock(return_value=chores)
        resp = await client.get("/api/v1/chores/PVT_123", params={"search": "lint"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_sort_by_name(self, client):
        chores = [
            _make_chore(id="c-1", name="Bravo"),
            _make_chore(id="c-2", name="Alpha"),
        ]
        self.mock_service.list_chores = AsyncMock(return_value=chores)
        resp = await client.get("/api/v1/chores/PVT_123", params={"sort": "name", "order": "asc"})
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["name"] == "Alpha"
        assert data[1]["name"] == "Bravo"

    async def test_pagination(self, client):
        chores = [_make_chore(id=f"c-{i}", name=f"Chore {i}") for i in range(5)]
        self.mock_service.list_chores = AsyncMock(return_value=chores)
        resp = await client.get("/api/v1/chores/PVT_123", params={"limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["has_more"] is True


# ── PATCH /{project_id}/{chore_id} (update) ──────────────────────────────


class TestUpdateChore:
    async def test_update_success(self, client):
        existing = _make_chore()
        updated = _make_chore(status=ChoreStatus.PAUSED)
        mock_service = MagicMock()
        mock_service.get_chore = AsyncMock(return_value=existing)
        mock_service.update_chore = AsyncMock(return_value=updated)

        with (
            patch(f"{_API}._get_service", return_value=mock_service),
            patch(f"{_API}.log_event", new_callable=AsyncMock),
        ):
            resp = await client.patch(
                "/api/v1/chores/PVT_123/chore-1",
                json={"status": "paused"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

    async def test_update_not_found(self, client):
        mock_service = MagicMock()
        mock_service.get_chore = AsyncMock(return_value=None)

        with patch(f"{_API}._get_service", return_value=mock_service):
            resp = await client.patch(
                "/api/v1/chores/PVT_123/chore-1",
                json={"status": "paused"},
            )
        assert resp.status_code == 404

    async def test_update_wrong_project(self, client):
        existing = _make_chore(project_id="OTHER_PROJECT")
        mock_service = MagicMock()
        mock_service.get_chore = AsyncMock(return_value=existing)

        with patch(f"{_API}._get_service", return_value=mock_service):
            resp = await client.patch(
                "/api/v1/chores/PVT_123/chore-1",
                json={"status": "paused"},
            )
        assert resp.status_code == 404

    async def test_update_invalid_returns_422(self, client):
        existing = _make_chore()
        mock_service = MagicMock()
        mock_service.get_chore = AsyncMock(return_value=existing)
        mock_service.update_chore = AsyncMock(side_effect=ValueError("bad input"))

        with patch(f"{_API}._get_service", return_value=mock_service):
            resp = await client.patch(
                "/api/v1/chores/PVT_123/chore-1",
                json={"status": "paused"},
            )
        assert resp.status_code == 422


# ── DELETE /{project_id}/{chore_id} ──────────────────────────────────────


class TestDeleteChore:
    async def test_delete_success_no_issue(self, client):
        existing = _make_chore(current_issue_number=None)
        mock_service = MagicMock()
        mock_service.get_chore = AsyncMock(return_value=existing)
        mock_service.delete_chore = AsyncMock()

        with (
            patch(f"{_API}._get_service", return_value=mock_service),
            patch(f"{_API}.log_event", new_callable=AsyncMock),
        ):
            resp = await client.delete("/api/v1/chores/PVT_123/chore-1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] is True
        assert data["closed_issue_number"] is None

    async def test_delete_closes_open_issue(self, client, mock_github_service):
        existing = _make_chore(current_issue_number=42)
        mock_service = MagicMock()
        mock_service.get_chore = AsyncMock(return_value=existing)
        mock_service.delete_chore = AsyncMock()
        mock_github_service.update_issue_state = AsyncMock()

        with (
            patch(f"{_API}._get_service", return_value=mock_service),
            patch(f"{_API}.resolve_repository", AsyncMock(return_value=("octo", "widgets"))),
            patch(f"{_API}.log_event", new_callable=AsyncMock),
        ):
            resp = await client.delete("/api/v1/chores/PVT_123/chore-1")
        assert resp.status_code == 200
        assert resp.json()["closed_issue_number"] == 42

    async def test_delete_not_found(self, client):
        mock_service = MagicMock()
        mock_service.get_chore = AsyncMock(return_value=None)

        with patch(f"{_API}._get_service", return_value=mock_service):
            resp = await client.delete("/api/v1/chores/PVT_123/chore-1")
        assert resp.status_code == 404

    async def test_delete_issue_close_failure_nonfatal(self, client, mock_github_service):
        """Issue close failure is logged but does not block deletion."""
        existing = _make_chore(current_issue_number=42)
        mock_service = MagicMock()
        mock_service.get_chore = AsyncMock(return_value=existing)
        mock_service.delete_chore = AsyncMock()
        mock_github_service.update_issue_state = AsyncMock(side_effect=RuntimeError("fail"))

        with (
            patch(f"{_API}._get_service", return_value=mock_service),
            patch(f"{_API}.resolve_repository", AsyncMock(return_value=("octo", "widgets"))),
            patch(f"{_API}.log_event", new_callable=AsyncMock),
        ):
            resp = await client.delete("/api/v1/chores/PVT_123/chore-1")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True
        # Issue close failed, so closed_issue_number should be None
        assert resp.json()["closed_issue_number"] is None


# ── POST /{project_id}/{chore_id}/trigger ────────────────────────────────


class TestTriggerChore:
    async def test_trigger_success(self, client, mock_github_service):
        chore = _make_chore()
        result = ChoreTriggerResult(
            chore_id="chore-1",
            chore_name="Update Dependencies",
            triggered=True,
            issue_number=99,
        )
        mock_service = MagicMock()
        mock_service.get_chore = AsyncMock(return_value=chore)
        mock_service.trigger_chore = AsyncMock(return_value=result)

        with (
            patch(f"{_API}._get_service", return_value=mock_service),
            patch(f"{_API}.resolve_repository", AsyncMock(return_value=("octo", "widgets"))),
            patch(f"{_API}.log_event", new_callable=AsyncMock),
        ):
            resp = await client.post("/api/v1/chores/PVT_123/chore-1/trigger")
        assert resp.status_code == 200
        assert resp.json()["triggered"] is True

    async def test_trigger_skipped_returns_409(self, client, mock_github_service):
        chore = _make_chore()
        result = ChoreTriggerResult(
            chore_id="chore-1",
            chore_name="Update Dependencies",
            triggered=False,
            skip_reason="Recently triggered",
        )
        mock_service = MagicMock()
        mock_service.get_chore = AsyncMock(return_value=chore)
        mock_service.trigger_chore = AsyncMock(return_value=result)

        with (
            patch(f"{_API}._get_service", return_value=mock_service),
            patch(f"{_API}.resolve_repository", AsyncMock(return_value=("octo", "widgets"))),
        ):
            resp = await client.post("/api/v1/chores/PVT_123/chore-1/trigger")
        assert resp.status_code == 409

    async def test_trigger_not_found(self, client):
        mock_service = MagicMock()
        mock_service.get_chore = AsyncMock(return_value=None)

        with patch(f"{_API}._get_service", return_value=mock_service):
            resp = await client.post("/api/v1/chores/PVT_123/chore-1/trigger")
        assert resp.status_code == 404
