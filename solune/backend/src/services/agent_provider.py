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


def _wrap_copilot_tools_with_runtime_state(
    tools: list | None,
    tool_runtime_state: dict[str, Any] | None,
) -> list:
    """Wrap FunctionTools so Copilot tool calls retain Solune runtime session state."""
    if not tools:
        return []
    if tool_runtime_state is None:
        return tools

    from agent_framework import AgentSession, FunctionInvocationContext, FunctionTool

    try:
        import importlib

        copilot_session = importlib.import_module("copilot.session")
    except ImportError:
        CopilotTool = None
    else:
        CopilotTool = getattr(copilot_session, "Tool", None)

    wrapped_tools: list[Any] = []
    wrapped_count = 0

    for tool_def in tools:
        if not isinstance(tool_def, FunctionTool):
            wrapped_tools.append(tool_def)
            continue

        async def handler(invocation: Any, ai_func: FunctionTool = tool_def) -> dict[str, Any]:
            args: dict[str, Any] = invocation.arguments or {}
            tool_call_id = getattr(invocation, "tool_call_id", "") or ""
            provider_session_id = getattr(invocation, "session_id", "") or None

            tool_session = AgentSession(
                session_id=str(tool_runtime_state.get("session_id") or provider_session_id or ""),
                service_session_id=provider_session_id,
            )
            tool_session.state = tool_runtime_state
            try:
                context = FunctionInvocationContext(
                    function=ai_func,
                    arguments=args,
                    session=tool_session,
                    kwargs={"tool_call_id": tool_call_id},
                )
            except TypeError:
                context = FunctionInvocationContext(
                    function=ai_func,
                    arguments=args,
                    kwargs={"tool_call_id": tool_call_id},
                )
                context.session = tool_session
                context.kwargs = {"tool_call_id": tool_call_id}

            try:
                if ai_func.input_model:
                    args_instance = ai_func.input_model(**args)
                    result = await ai_func.invoke(
                        arguments=args_instance,
                        context=context,
                        tool_call_id=tool_call_id,
                    )
                else:
                    result = await ai_func.invoke(
                        arguments=args,
                        context=context,
                        tool_call_id=tool_call_id,
                    )

                rich = [item for item in result if item.type in ("data", "uri")]
                if rich:
                    logger.warning(
                        "GitHub Copilot does not support rich tool content; "
                        "dropping %d non-text item(s) from '%s'.",
                        len(rich),
                        ai_func.name,
                    )
                text = "\n".join(item.text for item in result if item.type == "text" and item.text)
                return {
                    "text_result_for_llm": text or str(result),
                    "result_type": "success",
                }
            except Exception as exc:
                return {
                    "text_result_for_llm": f"Error: {exc}",
                    "result_type": "failure",
                    "error": str(exc),
                }

        tool_payload = {
            "name": tool_def.name,
            "description": tool_def.description,
            "handler": handler,
            "parameters": tool_def.parameters(),
        }
        wrapped_tools.append(
            CopilotTool(**tool_payload) if CopilotTool is not None else tool_payload
        )
        wrapped_count += 1

    if wrapped_count:
        logger.info(
            "Wrapped %d Copilot FunctionTool(s) with runtime session state",
            wrapped_count,
        )

    return wrapped_tools


async def create_agent(
    *,
    instructions: str,
    tools: list | None = None,
    github_token: str | None = None,
    mcp_servers: dict[str, Any] | None = None,
    reasoning_effort: str = "",
    tool_runtime_state: dict[str, Any] | None = None,
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
            tool_runtime_state=tool_runtime_state,
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
    tool_runtime_state: dict[str, Any] | None = None,
) -> Any:
    """Create an Agent using the GitHub Copilot provider.

    Uses ``agent-framework-github-copilot`` which wraps the Copilot SDK
    as a MAF-compatible provider. Reuses the shared CopilotClientPool so
    only one CLI server process exists per GitHub token.
    """
    if not github_token:
        raise ValueError(
            "GitHub OAuth token required for Copilot agent provider. "
            "Ensure user is authenticated via GitHub OAuth."
        )

    from agent_framework_github_copilot import GitHubCopilotAgent, GitHubCopilotOptions
    from copilot import PermissionHandler

    from src.services.completion_providers import get_copilot_client_pool

    settings = get_settings()
    effective_tools = _wrap_copilot_tools_with_runtime_state(tools, tool_runtime_state)

    options: GitHubCopilotOptions = {
        "model": settings.copilot_model,
        "on_permission_request": PermissionHandler.approve_all,
        "timeout": float(settings.agent_copilot_timeout_seconds),
    }

    if mcp_servers:
        options["mcp_servers"] = mcp_servers

    if reasoning_effort:
        options["reasoning_effort"] = reasoning_effort  # type: ignore[reportGeneralTypeIssues]

    client = await get_copilot_client_pool().get_or_create(github_token)

    agent = GitHubCopilotAgent(
        name="solune-agent",
        instructions=instructions,
        tools=effective_tools,
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
