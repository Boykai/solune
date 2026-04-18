from collections.abc import Awaitable

from slowapi.errors import RateLimitExceeded
from slowapi.extension import Limiter as Limiter
from starlette.requests import Request
from starlette.responses import Response

def _rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> Response | Awaitable[Response]: ...

__all__ = ["Limiter", "_rate_limit_exceeded_handler"]
