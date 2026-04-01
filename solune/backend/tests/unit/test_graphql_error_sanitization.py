"""Tests for GraphQL error sanitization (FR-030 / OWASP A09).

Verifies that internal GitHub GraphQL API error details are logged
internally but never exposed to API consumers.  Only a generic
``ValueError("GitHub API request failed")`` must reach callers.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.github_projects.service import GitHubProjectsService


def _make_service() -> GitHubProjectsService:
    """Create a service with a fully mocked client factory."""
    factory = MagicMock()
    return GitHubProjectsService(client_factory=factory)


def _mock_response(json_body: dict, status_code: int = 200) -> MagicMock:
    """Build a mock HTTP response."""
    resp = MagicMock()
    resp.json.return_value = json_body
    resp.status_code = status_code
    resp.headers = {}
    return resp


class TestGraphQLErrorSanitization:
    """Internal GraphQL error details must not leak to callers."""

    @pytest.fixture
    def service(self) -> GitHubProjectsService:
        return _make_service()

    async def test_single_error_raises_generic_message(self, service: GitHubProjectsService):
        """A single GraphQL error should produce a generic ValueError."""
        error_body = {
            "errors": [{"message": "Field 'login' not found on type 'Actor'"}],
        }
        mock_client = AsyncMock()
        mock_client.arequest.return_value = _mock_response(error_body)
        service._client_factory.get_client = AsyncMock(return_value=mock_client)

        with patch("src.config.get_settings") as mock_settings:
            mock_settings.return_value.api_timeout_seconds = 5
            with pytest.raises(ValueError, match=r"^GitHub API request failed$"):
                await service._graphql(
                    "fake-token",
                    "query { viewer { login } }",
                    {},
                    extra_headers={"X-Custom": "header"},
                )

    async def test_multiple_errors_raises_generic_message(self, service: GitHubProjectsService):
        """Multiple GraphQL errors should still produce only a generic message."""
        error_body = {
            "errors": [
                {"message": "Could not resolve to a Repository with the name 'secret/repo'"},
                {"message": "Token scope 'repo' required for this operation"},
            ],
        }
        mock_client = AsyncMock()
        mock_client.arequest.return_value = _mock_response(error_body)
        service._client_factory.get_client = AsyncMock(return_value=mock_client)

        with patch("src.config.get_settings") as mock_settings:
            mock_settings.return_value.api_timeout_seconds = 5
            with pytest.raises(ValueError, match=r"^GitHub API request failed$"):
                await service._graphql(
                    "fake-token",
                    "query { viewer { login } }",
                    {},
                    extra_headers={"X-Custom": "header"},
                )

    async def test_error_details_logged_internally(
        self, service: GitHubProjectsService, caplog: pytest.LogCaptureFixture
    ):
        """The full error message must appear in server logs for debugging."""
        internal_detail = "Variable $id of type ID! was provided invalid value"
        error_body = {
            "errors": [{"message": internal_detail}],
        }
        mock_client = AsyncMock()
        mock_client.arequest.return_value = _mock_response(error_body)
        service._client_factory.get_client = AsyncMock(return_value=mock_client)

        with patch("src.config.get_settings") as mock_settings:
            mock_settings.return_value.api_timeout_seconds = 5
            with pytest.raises(ValueError):
                await service._graphql(
                    "fake-token",
                    "mutation { x }",
                    {},
                    extra_headers={"X-Custom": "header"},
                )

        # Internal detail should be in log output for debugging
        assert internal_detail in caplog.text

    async def test_raised_error_does_not_contain_internal_detail(
        self, service: GitHubProjectsService
    ):
        """The raised ValueError must not contain the internal error message."""
        sensitive_detail = "Token expired for user 'admin@corp.internal'"
        error_body = {
            "errors": [{"message": sensitive_detail}],
        }
        mock_client = AsyncMock()
        mock_client.arequest.return_value = _mock_response(error_body)
        service._client_factory.get_client = AsyncMock(return_value=mock_client)

        with patch("src.config.get_settings") as mock_settings:
            mock_settings.return_value.api_timeout_seconds = 5
            with pytest.raises(ValueError) as exc_info:
                await service._graphql(
                    "fake-token",
                    "query { viewer { login } }",
                    {},
                    extra_headers={"X-Custom": "header"},
                )

        # The error message reaching the caller must be generic
        assert sensitive_detail not in str(exc_info.value)
        assert str(exc_info.value) == "GitHub API request failed"
