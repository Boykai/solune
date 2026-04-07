"""Agent provider factory — creates Agent instances for different AI backends.

Replaces the old ``CompletionProvider`` + ``create_completion_provider`` pattern
with a Microsoft Agent Framework Agent.

Supported providers:
- ``copilot``: Uses ``GitHubCopilotAgent`` (per-user OAuth token).
- ``azure_openai``: Uses ``Agent`` with ``AzureAIClient``.
"""

from __future__ import annotations

from typing import Any

from src.config import get_settings
from src.logging_utils import get_logger

logger = get_logger(__name__)


async def create_agent(
    *,
    instructions: str,
    tools: list | None = None,
    github_token: str | None = None,
    mcp_servers: dict[str, Any] | None = None,
    reasoning_effort: str = "",
) -> Any:
    """Create an Agent instance for the configured AI provider.

    Args:
        instructions: System instructions for the agent.
        tools: List of ``@tool``-decorated functions to register.
        github_token: GitHub OAuth token (required for ``copilot`` provider).
        mcp_servers: Optional MCP server configs loaded from the project.
        reasoning_effort: Optional reasoning effort level (e.g. "low", "medium", "high", "xhigh").

    Returns:
        A configured ``Agent`` instance.

    Raises:
        ValueError: If the provider is unknown or required credentials are missing.
    """
    settings = get_settings()
    provider = settings.ai_provider

    if provider == "copilot":
        return await _create_copilot_agent(
            instructions=instructions,
            tools=tools,
            github_token=github_token,
            mcp_servers=mcp_servers,
            reasoning_effort=reasoning_effort,
        )
    elif provider == "azure_openai":
        return _create_azure_agent(
            instructions=instructions,
            tools=tools,
        )
    else:
        raise ValueError(f"Unknown AI_PROVIDER {provider!r}. Supported: 'copilot', 'azure_openai'.")


async def _create_copilot_agent(
    *,
    instructions: str,
    tools: list | None = None,
    github_token: str | None = None,
    mcp_servers: dict[str, Any] | None = None,
    reasoning_effort: str = "",
) -> Any:
    """Create an Agent using the GitHub Copilot provider.

    Uses ``agent-framework-github-copilot`` which wraps the Copilot SDK
    as a MAF-compatible provider. Reuses the shared CopilotClientPool so
    only one CLI server process exists per GitHub token.
    """
    from agent_framework_github_copilot import GitHubCopilotAgent, GitHubCopilotOptions
    from copilot import PermissionHandler

    from src.services.completion_providers import get_copilot_client_pool

    if not github_token:
        raise ValueError(
            "GitHub OAuth token required for Copilot agent provider. "
            "Ensure user is authenticated via GitHub OAuth."
        )

    settings = get_settings()

    options: GitHubCopilotOptions = {
        "model": settings.copilot_model,
        "on_permission_request": PermissionHandler.approve_all,
        "timeout": float(settings.agent_copilot_timeout_seconds),
    }

    if mcp_servers:
        options["mcp_servers"] = mcp_servers

    if reasoning_effort:
        options["reasoning_effort"] = reasoning_effort  # type: ignore[typeddict-item]

    client = await get_copilot_client_pool().get_or_create(github_token)

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
    """Create an Agent using Azure AI as the backend.

    Uses ``AzureAIClient`` from ``agent-framework-azure-ai`` with
    ``DefaultAzureCredential`` for authentication (supports managed identity,
    environment variables, and ``az login``).
    """
    settings = get_settings()

    if not settings.azure_openai_endpoint:
        raise ValueError("Azure OpenAI endpoint not configured. Set AZURE_OPENAI_ENDPOINT in .env")

    from agent_framework import Agent
    from agent_framework_azure_ai import AzureAIClient
    from azure.identity import DefaultAzureCredential

    client = AzureAIClient(
        project_endpoint=settings.azure_openai_endpoint,
        model_deployment_name=settings.azure_openai_deployment,
        credential=DefaultAzureCredential(),
    )

    agent = Agent(
        name="solune-agent",
        instructions=instructions,
        client=client,
        tools=tools or [],
    )
    logger.info("Created Azure AI Agent (deployment: %s)", settings.azure_openai_deployment)
    return agent
