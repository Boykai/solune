"""Regression tests for GraphQL error sanitization (SC-019)."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.services.github_projects import GitHubProjectsService


@pytest.fixture
def service():
    return GitHubProjectsService()


class TestGraphQLErrorSanitization:
    """GraphQL errors should be logged internally without leaking to callers."""

    @pytest.mark.asyncio
    async def test_graphql_error_raises_generic_message(self, service):
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

        assert raw_error not in str(exc_info.value)
        assert "secret-repo" not in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_graphql_error_is_logged_internally(self, service):
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

        mock_logger.error.assert_called_once()
        logged_args = mock_logger.error.call_args.args
        assert logged_args[0] == "GraphQL error: %s"
        assert raw_error in logged_args[1]
