"""Agent provider factory — creates Agent instances for different AI backends.

Replaces the old ``CompletionProvider`` + ``create_completion_provider`` pattern
with a Microsoft Agent Framework Agent.

Supported providers:
- ``copilot``: Uses ``GitHubCopilotAgent`` (per-user OAuth token).
- ``azure_openai``: Uses ``Agent`` with ``AzureOpenAIChatClient``.
"""

from __future__ import annotations

from typing import Any

from src.config import get_settings
from src.logging_utils import get_logger

logger = get_logger(__name__)


def create_agent(
    *,
    instructions: str,
    tools: list | None = None,
    github_token: str | None = None,
) -> Any:
    """Create an Agent instance for the configured AI provider.

    Args:
        instructions: System instructions for the agent.
        tools: List of ``@tool``-decorated functions to register.
        github_token: GitHub OAuth token (required for ``copilot`` provider).

    Returns:
        A configured ``Agent`` instance.

    Raises:
        ValueError: If the provider is unknown or required credentials are missing.
    """
    settings = get_settings()
    provider = settings.ai_provider

    if provider == "copilot":
        return _create_copilot_agent(
            instructions=instructions,
            tools=tools,
            github_token=github_token,
        )
    elif provider == "azure_openai":
        return _create_azure_agent(
            instructions=instructions,
            tools=tools,
        )
    else:
        raise ValueError(f"Unknown AI_PROVIDER {provider!r}. Supported: 'copilot', 'azure_openai'.")


def _create_copilot_agent(
    *,
    instructions: str,
    tools: list | None = None,
    github_token: str | None = None,
) -> Any:
    """Create an Agent using the GitHub Copilot provider.

    Uses ``agent-framework-github-copilot`` which wraps the Copilot SDK
    as a MAF-compatible provider. A pre-configured CopilotClient with
    the user's OAuth token is injected so each user authenticates with
    their own GitHub identity.
    """
    from copilot import CopilotClient, PermissionHandler  # type: ignore[reportMissingImports]

    from agent_framework_github_copilot import GitHubCopilotAgent, GitHubCopilotOptions

    if not github_token:
        raise ValueError(
            "GitHub OAuth token required for Copilot agent provider. "
            "Ensure user is authenticated via GitHub OAuth."
        )

    settings = get_settings()

    options: GitHubCopilotOptions = {
        "model": settings.copilot_model,
        "on_permission_request": PermissionHandler.approve_all,
    }

    client = CopilotClient({"github_token": github_token})

    agent = GitHubCopilotAgent(
        name="solune-agent",
        instructions=instructions,
        tools=tools or [],
        default_options=options,
        client=client,
    )
    logger.info("Created GitHubCopilotAgent (model: %s)", settings.copilot_model)
    return agent


def _create_azure_agent(
    *,
    instructions: str,
    tools: list | None = None,
) -> Any:
    """Create an Agent using Azure OpenAI as the backend.

    Uses ``AzureOpenAIChatClient`` from ``agent-framework-azure-ai``.
    """
    from agent_framework import Agent
    from agent_framework.azure import AzureOpenAIChatClient

    settings = get_settings()

    if not settings.azure_openai_endpoint or not settings.azure_openai_key:
        raise ValueError(
            "Azure OpenAI credentials not configured. "
            "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY in .env"
        )

    client = AzureOpenAIChatClient(
        endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_key,
        deployment_name=settings.azure_openai_deployment,
    )

    agent = Agent(
        name="solune-agent",
        instructions=instructions,
        client=client,
        tools=tools or [],
    )
    logger.info("Created Azure OpenAI Agent (deployment: %s)", settings.azure_openai_deployment)
    return agent
