from typing import Any

class SubprocessConfig:
    """Config for spawning a local Copilot CLI subprocess."""

    github_token: str | None
    auto_start: bool

    def __init__(
        self,
        cli_path: str | None = None,
        cli_args: list[str] | None = None,
        *,
        cwd: str | None = None,
        use_stdio: bool = True,
        port: int = 0,
        log_level: str = "info",
        env: dict[str, str] | None = None,
        github_token: str | None = None,
        use_logged_in_user: bool | None = None,
        telemetry: Any | None = None,
    ) -> None: ...

class ExternalServerConfig:
    """Config for connecting to an existing Copilot server."""

    url: str

    def __init__(self, url: str) -> None: ...

class CopilotClient:
    """GitHub Copilot SDK client for completions."""

    def __init__(
        self,
        config: SubprocessConfig | ExternalServerConfig | None = None,
        *,
        auto_start: bool = True,
        on_list_models: Any | None = None,
    ) -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def create_session(self, config: Any) -> Any: ...
    async def get_completion(self, **kwargs: Any) -> Any: ...
