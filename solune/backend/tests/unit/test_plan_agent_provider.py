"""Unit tests for plan_agent_provider — agent profiles, session hooks, SDK factory."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.plan_agent_provider import (
    PLAN_AGENT_PROFILE,
    SPECKIT_AGENT_PROFILES,
    create_plan_session,
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
        assert "create_project_issue" in PLAN_AGENT_PROFILE["tool_whitelist"]
        assert "launch_pipeline" in PLAN_AGENT_PROFILE["tool_whitelist"]
        assert "iterate_on_app" in PLAN_AGENT_PROFILE["tool_whitelist"]
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

    def test_analyze_profile_tool_whitelist_excludes_save_plan(self):
        """Analyze agent must NOT have save_plan — it is read-only."""
        profile = SPECKIT_AGENT_PROFILES["solune-analyze"]
        assert "save_plan" not in profile["tool_whitelist"]

    def test_analyze_profile_has_only_get_project_context(self):
        """Analyze agent should have minimal tool access."""
        profile = SPECKIT_AGENT_PROFILES["solune-analyze"]
        assert profile["tool_whitelist"] == ["get_project_context"]

    def test_analyze_profile_name_and_description(self):
        """Analyze profile metadata should be correct."""
        profile = SPECKIT_AGENT_PROFILES["solune-analyze"]
        assert profile["name"] == "solune-analyze"
        assert profile["description"] == (
            "Analysis agent — performs cross-artifact consistency and quality analysis."
        )

    def test_all_profiles_have_required_keys(self):
        """Every profile must have name, description, tool_whitelist, permission."""
        required_keys = {"name", "description", "tool_whitelist", "permission"}
        for profile_name, profile in SPECKIT_AGENT_PROFILES.items():
            missing = required_keys - set(profile.keys())
            assert not missing, f"Profile {profile_name!r} missing keys: {missing}"

    def test_read_only_profiles_have_explicit_tool_whitelist(self):
        """Read-only profiles should have an explicit (non-None) tool whitelist."""
        for profile_name, profile in SPECKIT_AGENT_PROFILES.items():
            if profile["permission"] == "read_only":
                assert profile["tool_whitelist"] is not None, (
                    f"Read-only profile {profile_name!r} must have an explicit tool_whitelist"
                )


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

    @pytest.mark.anyio
    async def test_swallows_snapshot_exception(self):
        """Snapshot failure must not propagate — it logs and returns silently."""
        mock_db = MagicMock()
        context = {"db": mock_db, "active_plan_id": "plan-1"}

        with patch(
            "src.services.chat_store.snapshot_plan_version",
            new_callable=AsyncMock,
            side_effect=RuntimeError("db down"),
        ):
            # Should NOT raise
            await on_pre_tool_use_hook("save_plan", {}, context)

    @pytest.mark.anyio
    async def test_snapshot_returns_none_still_succeeds(self):
        """When snapshot_plan_version returns None, hook should still complete without error."""
        mock_db = MagicMock()
        context = {"db": mock_db, "active_plan_id": "plan-1"}

        with patch(
            "src.services.chat_store.snapshot_plan_version",
            new_callable=AsyncMock,
            return_value=None,
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

    @pytest.mark.anyio
    async def test_reads_version_from_db(self):
        """When db and plan exist, version numbers should come from the plan."""
        import json

        mock_db = MagicMock()
        context = {"active_plan_id": "plan-2", "db": mock_db}

        with patch(
            "src.services.chat_store.get_plan",
            new_callable=AsyncMock,
            return_value={"version": 5},
        ):
            result = await on_post_tool_use_hook("save_plan", None, context)

        assert result is not None
        data = json.loads(result["data"])
        assert data["to_version"] == 5
        assert data["from_version"] == 4

    @pytest.mark.anyio
    async def test_version_defaults_on_db_exception(self):
        """If db read fails, version defaults to 1."""
        import json

        mock_db = MagicMock()
        context = {"active_plan_id": "plan-3", "db": mock_db}

        with patch(
            "src.services.chat_store.get_plan",
            new_callable=AsyncMock,
            side_effect=RuntimeError("db error"),
        ):
            result = await on_post_tool_use_hook("save_plan", None, context)

        assert result is not None
        data = json.loads(result["data"])
        assert data["from_version"] == 1
        assert data["to_version"] == 1

    @pytest.mark.anyio
    async def test_version_defaults_when_plan_is_none(self):
        """If get_plan returns None, version defaults to 1."""
        import json

        mock_db = MagicMock()
        context = {"active_plan_id": "plan-4", "db": mock_db}

        with patch(
            "src.services.chat_store.get_plan",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await on_post_tool_use_hook("save_plan", None, context)

        assert result is not None
        data = json.loads(result["data"])
        assert data["from_version"] == 1
        assert data["to_version"] == 1

    @pytest.mark.anyio
    async def test_from_version_never_below_one(self):
        """from_version should be at least 1, even when to_version is 1."""
        import json

        mock_db = MagicMock()
        context = {"active_plan_id": "plan-5", "db": mock_db}

        with patch(
            "src.services.chat_store.get_plan",
            new_callable=AsyncMock,
            return_value={"version": 1},
        ):
            result = await on_post_tool_use_hook("save_plan", None, context)

        data = json.loads(result["data"])
        assert data["from_version"] == 1
        assert data["to_version"] == 1


# =============================================================================
# Session Factory
# =============================================================================


class TestCreatePlanSession:
    """Tests for create_plan_session SDK session factory."""

    @pytest.mark.anyio
    async def test_analyze_profile_uses_read_only_config(self):
        """Analyze profile should produce a session without save_plan tools."""
        mock_session = MagicMock()
        mock_client = AsyncMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)

        mock_pool = MagicMock()
        mock_pool.get_or_create = AsyncMock(return_value=mock_client)

        with patch(
            "src.services.completion_providers.get_copilot_client_pool",
            return_value=mock_pool,
        ):
            session = await create_plan_session(
                github_token="ghp_test",
                agent_profile="solune-analyze",
            )

        assert session is mock_session
        mock_client.create_session.assert_awaited_once()

    @pytest.mark.anyio
    async def test_unknown_profile_falls_back_to_plan(self):
        """Unknown agent_profile should fall back to PLAN_AGENT_PROFILE."""
        mock_session = MagicMock()
        mock_client = AsyncMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)

        mock_pool = MagicMock()
        mock_pool.get_or_create = AsyncMock(return_value=mock_client)

        with patch(
            "src.services.completion_providers.get_copilot_client_pool",
            return_value=mock_pool,
        ):
            session = await create_plan_session(
                github_token="ghp_test",
                agent_profile="nonexistent-profile",
            )

        assert session is mock_session

    @pytest.mark.anyio
    async def test_custom_instructions_override_profile_prompt(self):
        """Custom instructions should override profile system_prompt."""
        mock_session = MagicMock()
        mock_client = AsyncMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)

        mock_pool = MagicMock()
        mock_pool.get_or_create = AsyncMock(return_value=mock_client)

        with patch(
            "src.services.completion_providers.get_copilot_client_pool",
            return_value=mock_pool,
        ):
            await create_plan_session(
                github_token="ghp_test",
                instructions="Custom analyze instructions",
                agent_profile="solune-analyze",
            )

        call_args = mock_client.create_session.call_args[0][0]
        assert call_args["system_message"]["content"] == "Custom analyze instructions"

    @pytest.mark.anyio
    async def test_reasoning_effort_passed_to_config(self):
        """reasoning_effort should be included in the session config when set."""
        mock_session = MagicMock()
        mock_client = AsyncMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)

        mock_pool = MagicMock()
        mock_pool.get_or_create = AsyncMock(return_value=mock_client)

        with patch(
            "src.services.completion_providers.get_copilot_client_pool",
            return_value=mock_pool,
        ):
            await create_plan_session(
                github_token="ghp_test",
                reasoning_effort="high",
                agent_profile="solune-analyze",
            )

        call_args = mock_client.create_session.call_args[0][0]
        assert call_args["reasoning_effort"] == "high"
