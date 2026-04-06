"""Protocol describing the service interface available to domain mixins.

Each mixin module (issues, pull_requests, …) accesses helper methods like
``_rest``, ``_graphql``, ``_rest_response``, etc. that are defined on
``GitHubProjectsService``.  Because Python's type system cannot look
ahead to the final composed class, pyright flags these calls as
``reportAttributeAccessIssue``.

By inheriting from ``_ServiceProtocol`` (under ``TYPE_CHECKING`` only),
each mixin tells pyright that ``self`` will eventually have these methods.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, TypeVar

_T = TypeVar("_T")


class _ServiceProtocol(Protocol):
    """Minimal protocol matching the helpers on ``GitHubProjectsService``.

    Covers internal helpers (``_rest``, ``_graphql``, …) **and** cross-mixin
    methods that one mixin calls on another via the composed service.
    """

    # ── Internal helpers (defined on service.py) ──

    async def _rest(
        self,
        access_token: str,
        method: str,
        path: str,
        *,
        json: dict | list | None = ...,
        params: dict | None = ...,
        headers: dict[str, str] | None = ...,
    ) -> dict | list | str: ...

    async def _rest_response(
        self,
        access_token: str,
        method: str,
        path: str,
        *,
        json: dict | list | None = ...,
        params: dict | None = ...,
        headers: dict[str, str] | None = ...,
    ) -> Any: ...

    async def _graphql(
        self,
        access_token: str,
        query: str,
        variables: dict,
        extra_headers: dict | None = ...,
        graphql_features: list[str] | None = ...,
    ) -> dict: ...

    async def _cycle_cached(self, cache_key: str, fetch_fn: Callable[[], Awaitable[_T]]) -> _T: ...

    def _invalidate_cycle_cache(self, *keys: str) -> None: ...

    _cycle_cache: dict[str, Any]

    async def _with_fallback(self, *args: Any, **kwargs: Any) -> Any: ...

    async def _get_project_rest_info(self, *args: Any, **kwargs: Any) -> Any: ...

    # ── Cross-mixin methods (Issues) ──

    async def get_issue_with_comments(self, *args: Any, **kwargs: Any) -> Any: ...

    async def get_sub_issues(self, *args: Any, **kwargs: Any) -> Any: ...

    async def add_issue_to_project(self, *args: Any, **kwargs: Any) -> Any: ...

    # ── Cross-mixin methods (Pull Requests) ──

    async def get_pull_request(self, *args: Any, **kwargs: Any) -> Any: ...

    async def get_linked_pull_requests(self, *args: Any, **kwargs: Any) -> Any: ...

    async def get_pr_timeline_events(self, *args: Any, **kwargs: Any) -> Any: ...

    # ── Cross-mixin methods (Repository / Branches) ──

    async def get_branch_head_oid(self, *args: Any, **kwargs: Any) -> Any: ...

    # ── Cross-mixin methods (Identities — static/class methods on service) ──

    @staticmethod
    def is_copilot_author(*args: Any, **kwargs: Any) -> bool: ...

    @staticmethod
    def is_copilot_swe_agent(*args: Any, **kwargs: Any) -> bool: ...

    @staticmethod
    def is_copilot_reviewer_bot(*args: Any, **kwargs: Any) -> bool: ...
