"""Unit tests for copilot_polling.state — project registration and MonitoredProject."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.services.copilot_polling.state import (
    MonitoredProject,
    _monitored_projects,
    get_monitored_projects,
    register_project,
    unregister_project,
)


@pytest.fixture(autouse=True)
def _clean_registry():
    """Ensure the global registry is empty before and after each test."""
    _monitored_projects.clear()
    yield
    _monitored_projects.clear()


class TestRegisterProject:
    """Tests for register_project()."""

    def test_new_project_returns_true(self):
        result = register_project("p1", "owner", "repo", "tok")
        assert result is True

    def test_new_project_creates_monitored_project(self):
        register_project("p1", "owner", "repo", "tok")
        assert "p1" in _monitored_projects
        mp = _monitored_projects["p1"]
        assert isinstance(mp, MonitoredProject)
        assert mp.project_id == "p1"
        assert mp.owner == "owner"
        assert mp.repo == "repo"
        assert mp.access_token == "tok"
        assert mp.last_polled is None
        assert mp.registered_at.tzinfo is UTC

    def test_existing_project_returns_false(self):
        register_project("p1", "owner", "repo", "tok")
        result = register_project("p1", "owner2", "repo2", "tok2")
        assert result is False

    def test_existing_project_updates_fields(self):
        register_project("p1", "owner", "repo", "tok")
        register_project("p1", "new_owner", "new_repo", "new_tok")
        mp = _monitored_projects["p1"]
        assert mp.access_token == "new_tok"
        assert mp.owner == "new_owner"
        assert mp.repo == "new_repo"

    def test_multiple_projects(self):
        register_project("p1", "o1", "r1", "t1")
        register_project("p2", "o2", "r2", "t2")
        assert len(_monitored_projects) == 2


class TestUnregisterProject:
    """Tests for unregister_project()."""

    def test_existing_returns_true(self):
        register_project("p1", "owner", "repo", "tok")
        result = unregister_project("p1")
        assert result is True

    def test_existing_removes_from_registry(self):
        register_project("p1", "owner", "repo", "tok")
        unregister_project("p1")
        assert "p1" not in _monitored_projects

    def test_missing_returns_false(self):
        result = unregister_project("nonexistent")
        assert result is False


class TestGetMonitoredProjects:
    """Tests for get_monitored_projects()."""

    def test_empty_registry_returns_empty_list(self):
        result = get_monitored_projects()
        assert result == []

    def test_returns_snapshot_of_registered(self):
        register_project("p1", "o1", "r1", "t1")
        register_project("p2", "o2", "r2", "t2")
        result = get_monitored_projects()
        assert len(result) == 2
        assert all(isinstance(mp, MonitoredProject) for mp in result)

    def test_returns_copy_not_reference(self):
        register_project("p1", "o1", "r1", "t1")
        snapshot = get_monitored_projects()
        snapshot.clear()
        assert len(get_monitored_projects()) == 1


class TestMonitoredProjectDataclass:
    """Tests for MonitoredProject dataclass."""

    def test_fields(self):
        now = datetime.now(UTC)
        mp = MonitoredProject(
            project_id="p1",
            owner="owner",
            repo="repo",
            access_token="tok",
            registered_at=now,
        )
        assert mp.project_id == "p1"
        assert mp.owner == "owner"
        assert mp.repo == "repo"
        assert mp.access_token == "tok"
        assert mp.registered_at == now
        assert mp.last_polled is None

    def test_last_polled_can_be_set(self):
        now = datetime.now(UTC)
        mp = MonitoredProject(
            project_id="p1",
            owner="owner",
            repo="repo",
            access_token="tok",
            registered_at=now,
            last_polled=now,
        )
        assert mp.last_polled == now
