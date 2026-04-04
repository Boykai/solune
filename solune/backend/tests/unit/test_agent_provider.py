"""Tests for agent provider factory — create_agent() paths.

T018: All paths in src/services/agent_provider.py
- Copilot provider: success, missing token
- Azure OpenAI provider: success, missing credentials
- Unknown provider error
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_settings(**overrides):
    """Build a minimal Settings-like namespace for provider tests."""
    defaults = {
        "ai_provider": "copilot",
        "copilot_model": "gpt-4o",
        "agent_copilot_timeout_seconds": 60,
        "azure_openai_endpoint": None,
        "azure_openai_key": None,
        "azure_openai_deployment": "gpt-4",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestCreateAgentCopilot:
    @pytest.mark.asyncio
    @patch("src.services.agent_provider.get_settings")
    async def test_creates_copilot_agent_with_valid_token(self, mock_settings):
        """create_agent() succeeds for copilot provider with github_token."""
        mock_settings.return_value = _make_settings(ai_provider="copilot")

        mock_copilot_agent = MagicMock()
        mock_client = MagicMock()
        mock_permission_handler = MagicMock()
        mock_permission_handler.approve_all = MagicMock()
        mock_pool = MagicMock()
        mock_pool.get_or_create = AsyncMock(return_value=mock_client)

        with (
            patch.dict(
                "sys.modules",
                {
                    "agent_framework_github_copilot": MagicMock(
                        GitHubCopilotAgent=mock_copilot_agent,
                        GitHubCopilotOptions=dict,
                    ),
                    "copilot": MagicMock(
                        CopilotClient=MagicMock(return_value=mock_client),
                        PermissionHandler=mock_permission_handler,
                    ),
                },
            ),
            patch(
                "src.services.completion_providers.get_copilot_client_pool",
                return_value=mock_pool,
            ),
        ):
            from src.services.agent_provider import create_agent

            await create_agent(
                instructions="test instructions",
                github_token="gho_test_token",
            )

        mock_copilot_agent.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.agent_provider.get_settings")
    async def test_raises_when_github_token_missing(self, mock_settings):
        """create_agent() raises ValueError for copilot without token."""
        mock_settings.return_value = _make_settings(ai_provider="copilot")

        from src.services.agent_provider import create_agent

        with pytest.raises(ValueError, match="GitHub OAuth token required"):
            await create_agent(instructions="test", github_token=None)

    @pytest.mark.asyncio
    @patch("src.services.agent_provider.get_settings")
    async def test_raises_when_github_token_empty(self, mock_settings):
        """create_agent() raises ValueError for copilot with empty token."""
        mock_settings.return_value = _make_settings(ai_provider="copilot")

        from src.services.agent_provider import create_agent

        with pytest.raises(ValueError, match="GitHub OAuth token required"):
            await create_agent(instructions="test", github_token="")


class TestCreateAgentAzure:
    @pytest.mark.asyncio
    @patch("src.services.agent_provider.get_settings")
    async def test_creates_azure_agent_with_valid_credentials(self, mock_settings):
        """create_agent() succeeds for azure_openai with full credentials."""
        mock_settings.return_value = _make_settings(
            ai_provider="azure_openai",
            azure_openai_endpoint="https://test.openai.azure.com",
            azure_openai_key="test-key",
            azure_openai_deployment="gpt-4",
        )

        mock_agent_cls = MagicMock()
        mock_client_cls = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "agent_framework": MagicMock(Agent=mock_agent_cls),
                "agent_framework_azure_ai": MagicMock(AzureOpenAIChatClient=mock_client_cls),
            },
        ):
            from src.services.agent_provider import create_agent

            await create_agent(instructions="test instructions")

        mock_agent_cls.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.agent_provider.get_settings")
    async def test_raises_when_azure_credentials_missing(self, mock_settings):
        """create_agent() raises ValueError when Azure credentials missing."""
        mock_settings.return_value = _make_settings(
            ai_provider="azure_openai",
            azure_openai_endpoint=None,
            azure_openai_key=None,
        )

        from src.services.agent_provider import create_agent

        with pytest.raises(ValueError, match="Azure OpenAI credentials not configured"):
            await create_agent(instructions="test")

    @pytest.mark.asyncio
    @patch("src.services.agent_provider.get_settings")
    async def test_raises_when_azure_endpoint_only(self, mock_settings):
        """create_agent() raises when only endpoint is set but key is missing."""
        mock_settings.return_value = _make_settings(
            ai_provider="azure_openai",
            azure_openai_endpoint="https://test.openai.azure.com",
            azure_openai_key=None,
        )

        from src.services.agent_provider import create_agent

        with pytest.raises(ValueError, match="Azure OpenAI credentials not configured"):
            await create_agent(instructions="test")


class TestCreateAgentUnknown:
    @pytest.mark.asyncio
    @patch("src.services.agent_provider.get_settings")
    async def test_raises_for_unknown_provider(self, mock_settings):
        """create_agent() raises ValueError for unrecognized AI_PROVIDER."""
        mock_settings.return_value = _make_settings(ai_provider="unknown_provider")

        from src.services.agent_provider import create_agent

        with pytest.raises(ValueError, match="Unknown AI_PROVIDER 'unknown_provider'"):
            await create_agent(instructions="test")


class TestCreateAgentToolsAndInstructions:
    @pytest.mark.asyncio
    @patch("src.services.agent_provider.get_settings")
    async def test_passes_tools_to_copilot_agent(self, mock_settings):
        """create_agent() passes tool list to the provider."""
        mock_settings.return_value = _make_settings(ai_provider="copilot")

        tool_fn = MagicMock()
        mock_copilot_agent = MagicMock()
        mock_permission_handler = MagicMock()
        mock_permission_handler.approve_all = MagicMock()
        mock_pool = MagicMock()
        mock_pool.get_or_create = AsyncMock(return_value=MagicMock())

        with (
            patch.dict(
                "sys.modules",
                {
                    "agent_framework_github_copilot": MagicMock(
                        GitHubCopilotAgent=mock_copilot_agent,
                        GitHubCopilotOptions=dict,
                    ),
                    "copilot": MagicMock(
                        CopilotClient=MagicMock(return_value=MagicMock()),
                        PermissionHandler=mock_permission_handler,
                    ),
                },
            ),
            patch(
                "src.services.completion_providers.get_copilot_client_pool",
                return_value=mock_pool,
            ),
        ):
            from src.services.agent_provider import create_agent

            await create_agent(
                instructions="test",
                tools=[tool_fn],
                github_token="gho_token",
            )

        call_kwargs = mock_copilot_agent.call_args
        assert tool_fn in call_kwargs.kwargs.get("tools", call_kwargs[1].get("tools", []))

    @pytest.mark.asyncio
    @patch("src.services.agent_provider.get_settings")
    async def test_default_tools_is_empty_list(self, mock_settings):
        """When tools is None, an empty list is passed to the agent."""
        mock_settings.return_value = _make_settings(ai_provider="copilot")

        mock_copilot_agent = MagicMock()
        mock_permission_handler = MagicMock()
        mock_permission_handler.approve_all = MagicMock()
        mock_pool = MagicMock()
        mock_pool.get_or_create = AsyncMock(return_value=MagicMock())

        with (
            patch.dict(
                "sys.modules",
                {
                    "agent_framework_github_copilot": MagicMock(
                        GitHubCopilotAgent=mock_copilot_agent,
                        GitHubCopilotOptions=dict,
                    ),
                    "copilot": MagicMock(
                        CopilotClient=MagicMock(return_value=MagicMock()),
                        PermissionHandler=mock_permission_handler,
                    ),
                },
            ),
            patch(
                "src.services.completion_providers.get_copilot_client_pool",
                return_value=mock_pool,
            ),
        ):
            from src.services.agent_provider import create_agent

            await create_agent(
                instructions="test",
                tools=None,
                github_token="gho_token",
            )

        call_kwargs = mock_copilot_agent.call_args
        tools_arg = call_kwargs.kwargs.get("tools", call_kwargs[1].get("tools"))
        assert tools_arg == []
