"""Agent provider factory — creates Agent instances for different AI backends.

Replaces the old ``CompletionProvider`` + ``create_completion_provider`` pattern
with a Microsoft Agent Framework Agent.

Also hosts the shared :class:`CopilotClientPool` (previously in the removed
``completion_providers`` module) and a lightweight :func:`call_completion`
helper for direct LLM completions outside the agent-framework flow.

Supported providers:
- ``copilot``: Uses ``GitHubCopilotAgent`` (per-user OAuth token).
- ``azure_openai``: Uses ``Agent`` with ``AzureAIClient``.
"""

from __future__ import annotations

import asyncio
import hashlib
from typing import TYPE_CHECKING, Any, cast

from src.config import get_settings
from src.logging_utils import get_logger
from src.utils import BoundedDict

logger = get_logger(__name__)

if TYPE_CHECKING:
    from azure.ai.inference.models import ChatRequestMessage
    from openai.types.chat import ChatCompletionMessageParam

# ── CopilotClientPool (relocated from completion_providers.py) ───────

_copilot_client_pool: CopilotClientPool | None = None


class CopilotClientPool:
    """Shared, bounded cache of CopilotClient instances keyed by token hash.

    Used by both the agent provider and the model fetcher to avoid
    duplicate client creation. Each unique GitHub token maps to exactly one
    CopilotClient, regardless of which service requests it.

    Thread-safe via asyncio.Lock for concurrent get_or_create calls.
    Memory-safe via BoundedDict with FIFO eviction when capacity is reached.
    """

    def __init__(self, maxlen: int = 50) -> None:
        self._clients: BoundedDict[str, Any] = BoundedDict(maxlen=maxlen)
        self._lock: asyncio.Lock | None = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    @staticmethod
    def _token_key(github_token: str) -> str:
        """Return a stable hash of the token for use as a cache key.

        Avoids keeping raw tokens as dict keys where they could be
        exposed by debug tooling or log dumps.
        """
        return hashlib.sha256(github_token.encode()).hexdigest()[:16]

    async def get_or_create(self, github_token: str) -> Any:
        """Get cached or create new CopilotClient for a given token."""
        key = self._token_key(github_token)
        if key in self._clients:
            return self._clients[key]

        async with self._get_lock():
            # Double-check after acquiring lock
            if key in self._clients:
                return self._clients[key]

            from copilot import CopilotClient
            from copilot.types import CopilotClientOptions

            options = CopilotClientOptions(github_token=github_token, auto_start=False)
            client = CopilotClient(options=options)
            await client.start()
            self._clients[key] = client
            logger.info(
                "Created new CopilotClient (pool size: %d/%d)",
                len(self._clients),
                self._clients._maxlen,
            )
            return client

    async def cleanup(self) -> None:
        """Stop all cached CopilotClient instances. Call on app shutdown."""
        for _token_hash, client in list(self._clients.items()):
            try:
                await client.stop()
            except Exception as e:
                logger.warning("Error stopping CopilotClient: %s", e)
        self._clients.clear()
        logger.info("Cleaned up all CopilotClient instances")

    async def remove(self, github_token: str) -> None:
        """Stop and remove a single client by token."""
        key = self._token_key(github_token)
        client = self._clients.pop(key, None)
        if client:
            try:
                await client.stop()
            except Exception as e:
                logger.warning("Error stopping CopilotClient: %s", e)


def get_copilot_client_pool() -> CopilotClientPool:
    """Return the shared Copilot client pool, creating it on first use."""
    global _copilot_client_pool
    if _copilot_client_pool is None:
        _copilot_client_pool = CopilotClientPool()
    return _copilot_client_pool


# ── Lightweight completion helper ────────────────────────────────────


async def call_completion(
    *,
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 1000,
    github_token: str | None = None,
) -> str:
    """Execute a direct LLM completion outside the agent-framework flow.

    Selects the configured AI provider (``copilot`` or ``azure_openai``)
    and returns the assistant's response content.

    Args:
        messages: Chat messages ``[{"role": "system"|"user", "content": "..."}]``.
        temperature: Sampling temperature.
        max_tokens: Maximum response tokens.
        github_token: GitHub OAuth token (required for Copilot provider).

    Returns:
        The assistant's response content.
    """
    settings = get_settings()
    provider = settings.ai_provider

    if provider == "copilot":
        return await _copilot_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            github_token=github_token,
        )
    elif provider == "azure_openai":
        return await _azure_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    else:
        raise ValueError(f"Unknown AI_PROVIDER {provider!r}. Supported: 'copilot', 'azure_openai'.")


async def _copilot_completion(
    *,
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 1000,
    github_token: str | None = None,
) -> str:
    """Run a single completion using the GitHub Copilot SDK."""
    if not github_token:
        raise ValueError(
            "GitHub OAuth token required for Copilot provider. "
            "Ensure user is authenticated via GitHub OAuth."
        )

    settings = get_settings()
    model = settings.copilot_model

    client = await get_copilot_client_pool().get_or_create(github_token)

    from copilot.generated.session_events import SessionEventType
    from copilot.types import PermissionHandler, SessionConfig

    system_content = ""
    user_content = ""
    for msg in messages:
        if msg["role"] == "system":
            system_content = msg["content"]
        elif msg["role"] == "user":
            user_content = msg["content"]

    config: SessionConfig = {
        "model": model,
        "on_permission_request": PermissionHandler.approve_all,
    }
    if system_content:
        config["system_message"] = {"mode": "replace", "content": system_content}

    session = await client.create_session(config)
    done = asyncio.Event()
    result_content: list[str] = []
    error_content: list[str] = []

    def on_event(event: Any) -> None:
        try:
            etype = event.type
            if etype == SessionEventType.ASSISTANT_MESSAGE:
                content = getattr(event.data, "content", None)
                if content:
                    result_content.append(content)
            elif etype == SessionEventType.SESSION_IDLE:
                done.set()
            elif etype == SessionEventType.SESSION_ERROR:
                error_msg = getattr(event.data, "message", str(event.data))
                error_content.append(error_msg)
                done.set()
        except Exception as e:
            logger.warning("Error processing Copilot event: %s", e)
            done.set()

    session.on(on_event)
    await session.send(user_content)

    try:
        await asyncio.wait_for(done.wait(), timeout=120)
    except TimeoutError:
        logger.warning("Copilot completion timed out after 120s")
    finally:
        try:
            await session.destroy()
        except Exception as e:
            logger.warning("Error destroying Copilot session: %s", e)

    if error_content:
        raise ValueError(f"Copilot API error: {error_content[0]}")

    return "".join(result_content) if result_content else ""


async def _azure_completion(
    *,
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 1000,
) -> str:
    """Run a single completion using Azure OpenAI."""
    settings = get_settings()

    if not settings.azure_openai_endpoint or not settings.azure_openai_key:
        raise ValueError(
            "Azure OpenAI credentials not configured. "
            "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY in .env"
        )

    deployment = settings.azure_openai_deployment

    try:
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_key,
            api_version="2024-02-15-preview",
        )
        openai_messages = cast(list[ChatCompletionMessageParam], messages)
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=deployment,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except ImportError:
        from azure.ai.inference import ChatCompletionsClient
        from azure.ai.inference.models import SystemMessage, UserMessage
        from azure.core.credentials import AzureKeyCredential

        assert settings.azure_openai_endpoint is not None
        assert settings.azure_openai_key is not None
        ai_client = ChatCompletionsClient(
            endpoint=settings.azure_openai_endpoint,
            credential=AzureKeyCredential(settings.azure_openai_key),
        )
        inference_messages = cast(
            list[ChatRequestMessage],
            [
                (
                    SystemMessage(content=m["content"])
                    if m["role"] == "system"
                    else UserMessage(content=m["content"])
                )
                for m in messages
            ],
        )
        response = await asyncio.to_thread(
            ai_client.complete,
            model=deployment,
            messages=inference_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    if not response.choices:
        return ""
    return response.choices[0].message.content or ""


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

        copilot_types = importlib.import_module("copilot.types")
    except ImportError:
        CopilotTool = None
    else:
        CopilotTool = getattr(copilot_types, "Tool", None)

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
        options["reasoning_effort"] = reasoning_effort  # type: ignore[reportGeneralTypeIssues] — reason: GitHubCopilotOptions TypedDict doesn't declare reasoning_effort yet; SDK preview field

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
