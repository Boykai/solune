"""Unit tests for plan_agent_provider — agent profiles, session hooks, SDK factory."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.plan_agent_provider import (
    PLAN_AGENT_PROFILE,
    SPECKIT_AGENT_PROFILES,
    on_post_tool_use_hook,
    on_pre_tool_use_hook,
)

# =============================================================================
# Agent Profiles
# =============================================================================


class TestAgentProfiles:
    """Verify agent profile definitions."""

    def test_plan_agent_profile_structure(self):
        assert PLAN_AGENT_PROFILE["name"] == "solune-plan"
        assert "save_plan" in PLAN_AGENT_PROFILE["tool_whitelist"]
        assert "get_project_context" in PLAN_AGENT_PROFILE["tool_whitelist"]
        assert "get_pipeline_list" in PLAN_AGENT_PROFILE["tool_whitelist"]
        assert PLAN_AGENT_PROFILE["permission"] == "read_only"

    def test_speckit_profiles_all_defined(self):
        expected = {
            "solune-plan",
            "solune-specify",
            "solune-tasks",
            "solune-analyze",
            "solune-implement",
        }
        assert set(SPECKIT_AGENT_PROFILES.keys()) == expected

    def test_implement_profile_has_full_tools(self):
        profile = SPECKIT_AGENT_PROFILES["solune-implement"]
        assert profile["tool_whitelist"] is None
        assert profile["permission"] == "full"

    def test_analyze_profile_is_read_only(self):
        profile = SPECKIT_AGENT_PROFILES["solune-analyze"]
        assert profile["permission"] == "read_only"


# =============================================================================
# Session Hooks
# =============================================================================


class TestPreToolUseHook:
    """Tests for on_pre_tool_use_hook (plan versioning before save_plan)."""

    @pytest.mark.anyio
    async def test_ignores_non_save_plan_tools(self):
        """Non-save_plan tools should be ignored."""
        context = {"db": MagicMock(), "active_plan_id": "plan-1"}
        # Should not raise or call any store methods
        await on_pre_tool_use_hook("get_project_context", {}, context)

    @pytest.mark.anyio
    async def test_skips_when_no_active_plan(self):
        """Should skip when no active_plan_id in context."""
        context = {"db": MagicMock()}
        await on_pre_tool_use_hook("save_plan", {}, context)

    @pytest.mark.anyio
    async def test_skips_when_no_db(self):
        """Should skip when no db in context."""
        context = {"active_plan_id": "plan-1"}
        await on_pre_tool_use_hook("save_plan", {}, context)

    @pytest.mark.anyio
    async def test_calls_snapshot_on_save_plan(self):
        """Should call snapshot_plan_version when save_plan fires."""
        mock_db = MagicMock()
        context = {"db": mock_db, "active_plan_id": "plan-1"}

        with patch(
            "src.services.chat_store.snapshot_plan_version",
            new_callable=AsyncMock,
            return_value="ver-1",
        ) as mock_snapshot:
            await on_pre_tool_use_hook("save_plan", {}, context)
            mock_snapshot.assert_awaited_once_with(mock_db, "plan-1")


class TestPostToolUseHook:
    """Tests for on_post_tool_use_hook (plan_diff event after save_plan)."""

    @pytest.mark.anyio
    async def test_returns_none_for_non_save_plan(self):
        context = {"active_plan_id": "plan-1"}
        result = await on_post_tool_use_hook("get_project_context", None, context)
        assert result is None

    @pytest.mark.anyio
    async def test_returns_plan_diff_event(self):
        import json

        context = {"active_plan_id": "plan-1"}
        result = await on_post_tool_use_hook("save_plan", None, context)
        assert result is not None
        assert result["event"] == "plan_diff"
        data = json.loads(result["data"])
        assert data["plan_id"] == "plan-1"
        assert "from_version" in data
        assert "to_version" in data

    @pytest.mark.anyio
    async def test_returns_none_without_plan_id(self):
        context = {}
        result = await on_post_tool_use_hook("save_plan", None, context)
        assert result is None
