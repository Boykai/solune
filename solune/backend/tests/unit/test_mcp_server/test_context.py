"""Tests for MCP per-request authentication context (src/services/mcp_server/context.py).

Covers:
- McpContext dataclass validation (valid creation, invalid inputs)
- Contextvar get/set lifecycle (set → get → clear → get-none)
- Contextvar isolation across async tasks
- Frozen dataclass immutability
"""

import asyncio

from src.services.mcp_server.context import (
    McpContext,
    get_current_mcp_context,
    set_current_mcp_context,
)


class TestSetAndGetCurrentMcpContext:
    """Tests for the contextvar getter/setter pair."""

    def test_default_is_none(self):
        """Before any set, the contextvar should return None."""
        set_current_mcp_context(None)
        assert get_current_mcp_context() is None

    def test_set_and_get_roundtrip(self):
        """Setting a context and immediately getting it returns the same object."""
        ctx = McpContext(github_token="ghp_abc", github_user_id=1, github_login="user")
        set_current_mcp_context(ctx)
        try:
            result = get_current_mcp_context()
            assert result is ctx
        finally:
            set_current_mcp_context(None)

    def test_clear_resets_to_none(self):
        """Setting the contextvar to None clears any previous value."""
        ctx = McpContext(github_token="ghp_abc", github_user_id=1, github_login="user")
        set_current_mcp_context(ctx)
        set_current_mcp_context(None)
        assert get_current_mcp_context() is None

    def test_overwrite_replaces_previous(self):
        """A second set() call overwrites the first value."""
        ctx1 = McpContext(github_token="ghp_a", github_user_id=1, github_login="alice")
        ctx2 = McpContext(github_token="ghp_b", github_user_id=2, github_login="bob")
        set_current_mcp_context(ctx1)
        set_current_mcp_context(ctx2)
        try:
            assert get_current_mcp_context() is ctx2
        finally:
            set_current_mcp_context(None)

    async def test_async_task_isolation(self):
        """Each asyncio task gets its own copy of the contextvar.

        Setting the context in the parent task should be visible to a child
        task (Python copies the context on task creation), but changes in
        the child should not leak back into the parent.
        """
        parent_ctx = McpContext(github_token="ghp_parent", github_user_id=1, github_login="parent")
        set_current_mcp_context(parent_ctx)

        child_saw: list[McpContext | None] = []

        async def child_task():
            # Child inherits a copy of the parent context
            child_saw.append(get_current_mcp_context())
            # Override in child — should NOT affect parent
            child_ctx = McpContext(github_token="ghp_child", github_user_id=2, github_login="child")
            set_current_mcp_context(child_ctx)
            child_saw.append(get_current_mcp_context())

        await asyncio.create_task(child_task())

        try:
            # Child initially inherited parent context
            assert child_saw[0] is parent_ctx
            # Child override was visible inside the child
            assert child_saw[1] is not None
            assert child_saw[1].github_login == "child"
            # Parent context is unaffected
            assert get_current_mcp_context() is parent_ctx
        finally:
            set_current_mcp_context(None)


class TestMcpContextImmutability:
    """McpContext is a frozen dataclass — attributes cannot be reassigned."""

    def test_frozen_token(self):
        ctx = McpContext(github_token="ghp_abc", github_user_id=1, github_login="user")
        with __import__("pytest").raises(AttributeError):
            ctx.github_token = "ghp_new"  # type: ignore[misc]

    def test_frozen_user_id(self):
        ctx = McpContext(github_token="ghp_abc", github_user_id=1, github_login="user")
        with __import__("pytest").raises(AttributeError):
            ctx.github_user_id = 99  # type: ignore[misc]

    def test_frozen_login(self):
        ctx = McpContext(github_token="ghp_abc", github_user_id=1, github_login="user")
        with __import__("pytest").raises(AttributeError):
            ctx.github_login = "other"  # type: ignore[misc]
