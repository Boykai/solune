from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from starlette.requests import Request

_F = TypeVar("_F", bound=Callable[..., Any])
_AF = TypeVar("_AF", bound=Callable[..., Awaitable[Any]])

class Limiter:
    enabled: bool
    def __init__(
        self,
        key_func: Callable[[Request], str],
        default_limits: list[str] | None = ...,
        application_limits: list[str] | None = ...,
        headers_enabled: bool = ...,
        strategy: str | None = ...,
        storage_uri: str | None = ...,
        storage_options: dict[str, Any] | None = ...,
        auto_check: bool = ...,
        swallow_errors: bool = ...,
        in_memory_fallback: list[str] | None = ...,
        in_memory_fallback_enabled: bool = ...,
        retry_after: str | None = ...,
        key_prefix: str = ...,
        enabled: bool = ...,
        config_filename: str | None = ...,
        key_style: str = ...,
    ) -> None: ...
    def limit(
        self,
        limit_value: str | Callable[..., str],
        key_func: Callable[..., str] | None = ...,
        per_method: bool = ...,
        methods: list[str] | None = ...,
        error_message: str | None = ...,
        exempt_when: Callable[..., bool] | None = ...,
        cost: int | Callable[..., int] = ...,
        override_defaults: bool = ...,
    ) -> Callable[[_F], _F]: ...
    def shared_limit(
        self,
        limit_value: str | Callable[..., str],
        scope: str | Callable[..., str],
        key_func: Callable[..., str] | None = ...,
        error_message: str | None = ...,
        exempt_when: Callable[..., bool] | None = ...,
        cost: int | Callable[..., int] = ...,
    ) -> Callable[[_F], _F]: ...
    def exempt(self, obj: _F) -> _F: ...
    def reset(self) -> None: ...
