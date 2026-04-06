"""Minimal type stubs for copilot.types."""

from typing import Any, TypedDict

class PermissionHandler:
    @staticmethod
    def approve_all(*args: Any, **kwargs: Any) -> Any: ...

class _SystemMessage(TypedDict, total=False):
    mode: str
    content: str

class SessionConfig(TypedDict, total=False):
    session_id: str
    client_name: str
    model: str
    reasoning_effort: str
    tools: list[Any]
    system_message: _SystemMessage
    available_tools: list[Any]
    excluded_tools: list[Any]
    on_permission_request: Any
    on_user_input_request: Any
    hooks: Any
    working_directory: str
    provider: str
    streaming: bool
    mcp_servers: Any
    custom_agents: Any
    config_dir: str
    skill_directories: list[str]
    disabled_skills: list[str]
    infinite_sessions: bool

class CopilotClientOptions(TypedDict, total=False):
    cli_path: str
    cli_args: list[str]
    cwd: str
    port: int
    use_stdio: bool
    cli_url: str
    log_level: str
    auto_start: bool
    auto_restart: bool
    env: dict[str, str]
    github_token: str
    use_logged_in_user: bool
