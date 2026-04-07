from typing import Any

class RequestFailed(Exception):
    """Exception raised when a GitHub API request fails."""

    response: Any
    def __init__(self, response: Any = ...) -> None: ...

class PrimaryRateLimitExceeded(RequestFailed):
    """Exception raised when primary rate limit is exceeded."""

    retry_after: int | None
