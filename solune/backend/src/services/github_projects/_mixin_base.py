"""TYPE_CHECKING-only base for github_projects domain mixins.

At runtime this is just ``object``.  Under pyright it provides the method
signatures and instance attributes that ``GitHubProjectsService`` defines,
so that each mixin file can reference ``self._rest``, ``self._graphql``,
etc. without disabling ``reportAttributeAccessIssue`` at the file level.
"""
# pyright: basic
# reason: Legacy githubkit response shapes; awaiting upstream typed accessors.

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    _T = TypeVar("_T")

    class _ServiceMixin:
        """Shared interface provided by GitHubProjectsService to all mixins."""

        _cycle_cache: dict[str, object]
        _cycle_cache_hit_count: int

        async def _rest(
            self,
            access_token: str,
            method: str,
            path: str,
            *,
            json: dict | list | None = None,
            params: dict | None = None,
            headers: dict[str, str] | None = None,
        ) -> dict | list | str: ...

        async def _rest_response(
            self,
            access_token: str,
            method: str,
            path: str,
            *,
            json: dict | list | None = None,
            params: dict | None = None,
            headers: dict[str, str] | None = None,
        ) -> Any: ...

        async def _graphql(
            self,
            access_token: str,
            query: str,
            variables: dict[str, Any],
            extra_headers: dict[str, str] | None = None,
            graphql_features: list[str] | None = None,
        ) -> dict[str, Any]: ...

        async def _cycle_cached(
            self, cache_key: str, fetch_fn: Callable[[], Awaitable[_T]]
        ) -> _T: ...

        def _invalidate_cycle_cache(self, *keys: str) -> None: ...

        async def _with_fallback(
            self,
            primary_fn: Callable[[], Awaitable[_T]],
            fallback_fn: Callable[[], Awaitable[_T]],
            operation: str,
            verify_fn: Callable[[], Awaitable[bool]] | None = None,
        ) -> _T | None: ...

        async def _best_effort(
            self,
            fn: Callable[..., Awaitable[_T]],
            *args: Any,
            fallback: _T,
            context: str,
            log_level: int = ...,
            **kwargs: Any,
        ) -> _T: ...

        # Cross-mixin methods called from other mixins
        @staticmethod
        def is_copilot_author(login: str) -> bool: ...
        @staticmethod
        def is_copilot_swe_agent(login: str) -> bool: ...
        @staticmethod
        def is_copilot_reviewer_bot(login: str) -> bool: ...
        async def get_branch_head_oid(
            self, access_token: str, owner: str, repo: str, branch_name: str
        ) -> str | None: ...
        async def add_issue_to_project(
            self,
            access_token: str,
            project_id: str,
            issue_node_id: str,
            issue_database_id: int | None = None,
        ) -> str | None: ...
        async def get_issue_with_comments(
            self, access_token: str, owner: str, repo: str, issue_number: int
        ) -> dict[str, Any]: ...
        async def ensure_labels_exist(
            self, access_token: str, owner: str, repo: str, labels: list[str]
        ) -> None: ...
        async def find_issue_by_labels(
            self,
            access_token: str,
            owner: str,
            repo: str,
            labels: list[str],
            state: str = "all",
        ) -> dict[str, Any] | None: ...
        async def get_sub_issues(
            self, access_token: str, owner: str, repo: str, issue_number: int
        ) -> list[dict[str, Any]]: ...
        async def _get_project_rest_info(
            self, access_token: str, project_id: str
        ) -> tuple[int, str, str] | None: ...
        async def get_linked_pull_requests(
            self, access_token: str, owner: str, repo: str, issue_number: int
        ) -> list[dict[str, Any]]: ...
        async def get_pull_request(
            self, access_token: str, owner: str, repo: str, pr_number: int
        ) -> dict[str, Any] | None: ...
        async def get_pr_timeline_events(
            self, access_token: str, owner: str, repo: str, issue_number: int
        ) -> list[dict[str, Any]]: ...

else:
    _ServiceMixin = object
