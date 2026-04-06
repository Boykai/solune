from typing import Any, Generic, TypeVar
from typing_extensions import TypedDict

class GitHubCopilotOptions(TypedDict, total=False):
    """GitHub Copilot-specific options."""
    system_message: dict[str, str]
    cli_path: str
    model: str
    timeout: float
    log_level: str
    on_permission_request: Any
    mcp_servers: dict[str, Any]
    reasoning_effort: str

OptionsT = TypeVar("OptionsT", default=GitHubCopilotOptions)

class GitHubCopilotAgent(Generic[OptionsT]):
    """GitHub Copilot agent."""
    def __init__(
        self,
        *,
        name: str = ...,
        instructions: str = ...,
        tools: list[Any] = ...,
        default_options: OptionsT = ...,
        client: Any = ...,
        **kwargs: Any,
    ) -> None: ...
