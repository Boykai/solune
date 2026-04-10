"""Unit tests for the ``get_github_service()`` lazy singleton accessor.

Verifies the accessor introduced in Harden Phase 3 (task 3.1) behaves
correctly: lazy creation, singleton guarantee, and reset-ability for tests.
"""

from __future__ import annotations

from unittest.mock import patch

import src.services.github_projects as gp_mod
from src.services.github_projects import GitHubProjectsService, get_github_service


class TestGetGithubService:
    """Tests for get_github_service() lazy singleton accessor."""

    def setup_method(self):
        """Clear the module-level singleton before each test."""
        gp_mod._service_instance = None

    def teardown_method(self):
        """Reset the singleton after each test to avoid cross-contamination."""
        gp_mod._service_instance = None

    def test_returns_github_projects_service_instance(self):
        """Should return an instance of GitHubProjectsService."""
        svc = get_github_service()
        assert isinstance(svc, GitHubProjectsService)

    def test_lazy_creation_on_first_call(self):
        """Should create the instance only on first call."""
        assert gp_mod._service_instance is None
        svc = get_github_service()
        assert gp_mod._service_instance is svc

    def test_returns_same_instance_on_subsequent_calls(self):
        """Should return the same singleton across multiple calls."""
        svc1 = get_github_service()
        svc2 = get_github_service()
        assert svc1 is svc2

    def test_respects_pre_set_instance(self):
        """If _service_instance is pre-assigned, the accessor should return it."""
        sentinel = object()
        gp_mod._service_instance = sentinel  # type: ignore[assignment]
        assert get_github_service() is sentinel

    def test_patchable_for_tests(self):
        """Mock.patch should intercept get_github_service() return value."""
        mock_svc = object()
        with patch(
            "src.services.github_projects.get_github_service",
            return_value=mock_svc,
        ):
            assert gp_mod.get_github_service() is mock_svc


class TestModuleExports:
    """Verify __all__ includes the public API surface."""

    def test_all_exports_get_github_service(self):
        assert "get_github_service" in gp_mod.__all__

    def test_all_exports_github_projects_service(self):
        assert "GitHubProjectsService" in gp_mod.__all__

    def test_all_exports_github_client_factory(self):
        assert "GitHubClientFactory" in gp_mod.__all__
