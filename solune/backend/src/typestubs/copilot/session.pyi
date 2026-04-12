from typing import Any

from typing_extensions import TypedDict

class SessionConfig(TypedDict, total=False):
    """Options passed to create_session."""

    model: str
    on_permission_request: Any
    system_message: dict[str, str]
    reasoning_effort: str

class PermissionHandler:
    """Permission handler for Copilot agent providers."""
    @staticmethod
    def approve_all(*args: Any, **kwargs: Any) -> Any: ...
    async def check_permission(self, **kwargs: Any) -> bool: ...
