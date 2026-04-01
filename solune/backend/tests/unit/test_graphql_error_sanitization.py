"""Unit tests for GraphQL error sanitization (SC-019).

Ensures that raw GitHub GraphQL error messages are logged internally but
never surfaced to API callers.  The ``_graphql`` method must raise a
generic ``ValueError("GitHub API request failed")`` — not the original
error text — so that query structure, token scope details, or internal
GitHub service state cannot leak through API responses.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.services.github_projects import GitHubProjectsService


@pytest.fixture
def service():
    return GitHubProjectsService()


class TestGraphQLErrorSanitization:
    """GraphQL errors must be logged but not leaked to callers."""

    @pytest.mark.asyncio
    async def test_graphql_error_raises_generic_message(self, service):
        """GraphQL errors should raise a generic ValueError, not the raw error."""
        mock_response = Mock(
            status_code=200,
            headers={},
            json=Mock(
                return_value={
                    "errors": [
                        {
                            "message": "Your token has insufficient scopes: "
                            "repo, project. Required: admin:org"
                        }
                    ]
                }
            ),
        )

        mock_client = AsyncMock()
        mock_client.arequest = AsyncMock(return_value=mock_response)

        service._client_factory = Mock()
        service._client_factory.get_client = AsyncMock(return_value=mock_client)

        with pytest.raises(ValueError, match=r"^GitHub API request failed$"):
            await service._graphql(
                "fake-token",
                "query { viewer { login } }",
                {},
                extra_headers={"X-Custom": "test"},
            )

    @pytest.mark.asyncio
    async def test_graphql_multiple_errors_still_generic(self, service):
        """Multiple GraphQL errors should still produce only the generic message."""
        mock_response = Mock(
            status_code=200,
            headers={},
            json=Mock(
                return_value={
                    "errors": [
                        {"message": "Field 'internalField' doesn't exist on type 'User'"},
                        {"message": "Variable $secret is never used in operation Query"},
                    ]
                }
            ),
        )

        mock_client = AsyncMock()
        mock_client.arequest = AsyncMock(return_value=mock_response)

        service._client_factory = Mock()
        service._client_factory.get_client = AsyncMock(return_value=mock_client)

        with pytest.raises(ValueError, match=r"^GitHub API request failed$"):
            await service._graphql(
                "fake-token",
                "query { viewer { login } }",
                {},
                extra_headers={"X-Custom": "test"},
            )

    @pytest.mark.asyncio
    async def test_graphql_error_does_not_contain_raw_message(self, service):
        """Raised exception must not contain the internal error text."""
        raw_error = "Could not resolve to a Repository with the name 'secret-repo'"
        mock_response = Mock(
            status_code=200,
            headers={},
            json=Mock(return_value={"errors": [{"message": raw_error}]}),
        )

        mock_client = AsyncMock()
        mock_client.arequest = AsyncMock(return_value=mock_response)

        service._client_factory = Mock()
        service._client_factory.get_client = AsyncMock(return_value=mock_client)

        with pytest.raises(ValueError) as exc_info:
            await service._graphql(
                "fake-token",
                "query { viewer { login } }",
                {},
                extra_headers={"X-Custom": "test"},
            )

        # The exception text must not contain the raw GitHub error
        assert raw_error not in str(exc_info.value)
        assert "secret-repo" not in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_graphql_error_is_logged_internally(self, service):
        """The full GraphQL error must be logged for debugging."""
        raw_error = "Token scope 'admin:org' required"
        mock_response = Mock(
            status_code=200,
            headers={},
            json=Mock(return_value={"errors": [{"message": raw_error}]}),
        )

        mock_client = AsyncMock()
        mock_client.arequest = AsyncMock(return_value=mock_response)

        service._client_factory = Mock()
        service._client_factory.get_client = AsyncMock(return_value=mock_client)

        with (
            patch("src.services.github_projects.service.logger") as mock_logger,
            pytest.raises(ValueError),
        ):
            await service._graphql(
                "fake-token",
                "query { viewer { login } }",
                {},
                extra_headers={"X-Custom": "test"},
            )

        # logger.error must have been called with the full error text
        mock_logger.error.assert_called_once()
        logged_msg = str(mock_logger.error.call_args)
        assert raw_error in logged_msg
