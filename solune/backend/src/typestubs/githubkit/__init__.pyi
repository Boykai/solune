from typing import Any

class Response[T]:
    """Typed githubkit Response enabling attribute access on parsed_data."""
    parsed_data: T
    status_code: int
    headers: dict[str, str]
    url: str
    content: bytes

class GitHub:
    """GitHub API client."""
    def __init__(self, auth: Any = ..., **kwargs: Any) -> None: ...
    @property
    def rest(self) -> Any: ...
    @property
    def graphql(self) -> Any: ...
    def __getattr__(self, name: str) -> Any: ...

class TokenAuthStrategy:
    """Token-based authentication strategy."""
    def __init__(self, token: str) -> None: ...
