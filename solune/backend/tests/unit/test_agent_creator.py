"""Unit tests for the agent creator service.

Covers pure functions (parse_command, fuzzy_match_status,
generate_config_files, _format_preview, _format_pipeline_report),
the admin check (is_admin_user), and top-level handle_agent_command routing.
"""

from __future__ import annotations

from typing import ClassVar
from unittest.mock import AsyncMock, patch

import aiosqlite
import pytest

from src.models.agent_creator import (
    AgentCreationState,
    AgentPreview,
    CreationStep,
    PipelineStepResult,
)
from src.services.agent_creator import (
    _format_pipeline_report,
    _format_preview,
    clear_session,
    fuzzy_match_status,
    generate_config_files,
    get_active_session,
    handle_agent_command,
    is_admin_user,
    parse_command,
)

# ═══════════════════════════════════════════════════════════════════════
# parse_command
# ═══════════════════════════════════════════════════════════════════════


class TestParseCommand:
    """Tests for the #agent command parser."""

    def test_simple_description(self):
        desc, status = parse_command("#agent Reviews PRs for security")
        assert desc == "Reviews PRs for security"
        assert status is None

    def test_description_with_status(self):
        desc, status = parse_command("#agent Reviews PRs for security #in-review")
        assert desc == "Reviews PRs for security"
        assert status == "in-review"

    def test_status_with_spaces(self):
        desc, status = parse_command("#agent Auto-assigns issues #Code Review")
        assert desc == "Auto-assigns issues"
        assert status == "Code Review"

    def test_case_insensitive_prefix(self):
        desc, status = parse_command("#AGENT some description")
        assert desc == "some description"
        assert status is None

    def test_empty_description_raises(self):
        with pytest.raises(ValueError, match="empty description"):
            parse_command("#agent")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="empty description"):
            parse_command("#agent   ")

    def test_hash_only_status_no_description(self):
        """#agent #done — description is empty before the hash."""
        with pytest.raises(ValueError, match="empty description"):
            parse_command("#agent #done")

    def test_multiple_hash_takes_last(self):
        desc, status = parse_command("#agent Handles #bug triage flow #backlog")
        assert desc == "Handles #bug triage flow"
        assert status == "backlog"

    def test_strips_whitespace(self):
        desc, status = parse_command("  #agent   Review PRs   #in-review  ")
        assert desc == "Review PRs"
        assert status == "in-review"


# ═══════════════════════════════════════════════════════════════════════
# fuzzy_match_status
# ═══════════════════════════════════════════════════════════════════════


class TestFuzzyMatchStatus:
    """Tests for status column fuzzy matching."""

    COLUMNS: ClassVar[list[str]] = ["Todo", "In Progress", "In Review", "Code Review", "Done"]

    def test_exact_match(self):
        resolved, ambiguous, matches = fuzzy_match_status("Done", self.COLUMNS)
        assert resolved == "Done"
        assert ambiguous is False
        assert matches == ["Done"]

    def test_normalized_exact_match(self):
        """in-review normalises to the same as 'In Review'."""
        resolved, ambiguous, _matches = fuzzy_match_status("in-review", self.COLUMNS)
        assert resolved == "In Review"
        assert ambiguous is False

    def test_case_insensitive_match(self):
        resolved, ambiguous, _matches = fuzzy_match_status("TODO", self.COLUMNS)
        assert resolved == "Todo"
        assert ambiguous is False

    def test_ambiguous_contains_match(self):
        """'review' matches both 'In Review' and 'Code Review'."""
        resolved, ambiguous, matches = fuzzy_match_status("review", self.COLUMNS)
        assert resolved is None
        assert ambiguous is True
        assert set(matches) == {"In Review", "Code Review"}

    def test_unique_contains_match(self):
        """'progress' uniquely matches 'In Progress'."""
        resolved, ambiguous, _matches = fuzzy_match_status("progress", self.COLUMNS)
        assert resolved == "In Progress"
        assert ambiguous is False

    def test_no_match(self):
        resolved, ambiguous, matches = fuzzy_match_status("nonexistent", self.COLUMNS)
        assert resolved is None
        assert ambiguous is False
        assert matches == []

    def test_empty_columns(self):
        resolved, ambiguous, matches = fuzzy_match_status("anything", [])
        assert resolved is None
        assert ambiguous is False
        assert matches == []

    def test_empty_input(self):
        _resolved, ambiguous, _matches = fuzzy_match_status("", self.COLUMNS)
        # Empty string matches everything via contains — expect ambiguous
        assert ambiguous is True


# ═══════════════════════════════════════════════════════════════════════
# generate_config_files
# ═══════════════════════════════════════════════════════════════════════


class TestGenerateConfigFiles:
    """Tests for config file generation (GitHub Custom Agent .agent.md format)."""

    @pytest.fixture
    def preview(self) -> AgentPreview:
        return AgentPreview(
            name="SecurityReviewer",
            slug="security-reviewer",
            description="Reviews PRs for security vulnerabilities",
            system_prompt="You are a security reviewer...",
            status_column="In Review",
            tools=["search_code", "create_issue"],
        )

    def test_returns_two_files(self, preview: AgentPreview):
        files = generate_config_files(preview)
        assert len(files) == 2

    def test_agent_file_path(self, preview: AgentPreview):
        files = generate_config_files(preview)
        assert files[0]["path"] == ".github/agents/security-reviewer.agent.md"

    def test_prompt_file_path(self, preview: AgentPreview):
        files = generate_config_files(preview)
        assert files[1]["path"] == ".github/prompts/security-reviewer.prompt.md"

    def test_agent_file_has_yaml_frontmatter(self, preview: AgentPreview):
        files = generate_config_files(preview)
        content = files[0]["content"]
        assert content.startswith("---\n")
        assert "\n---\n" in content

    def test_agent_file_has_frontmatter(self, preview: AgentPreview):
        files = generate_config_files(preview)
        content = files[0]["content"]
        assert "description: Reviews PRs for security vulnerabilities" in content

    def test_agent_file_omits_tools_from_frontmatter(self, preview: AgentPreview):
        files = generate_config_files(preview)
        content = files[0]["content"]
        assert "tools:" not in content

    def test_agent_file_has_system_prompt_body(self, preview: AgentPreview):
        files = generate_config_files(preview)
        content = files[0]["content"]
        assert "You are a security reviewer..." in content

    def test_prompt_file_has_prompt_fence(self, preview: AgentPreview):
        files = generate_config_files(preview)
        content = files[1]["content"]
        assert content.startswith("```prompt\n")
        assert "agent: security-reviewer" in content

    def test_no_tools_omits_tools_key(self):
        preview = AgentPreview(
            name="SimpleAgent",
            slug="simple-agent",
            description="A simple agent",
            system_prompt="Do things",
            status_column="Todo",
            tools=[],
        )
        files = generate_config_files(preview)
        assert "tools:" not in files[0]["content"]

    def test_agent_file_includes_mcp_servers_and_metadata(self):
        preview = AgentPreview(
            name="McpReviewer",
            slug="mcp-reviewer",
            description="Uses uploaded MCP servers",
            system_prompt="Review with MCP assistance",
            status_column="Todo",
            tools=["Context7"],
            tool_ids=["tool-123"],
            mcp_servers={
                "context7": {
                    "type": "http",
                    "url": "https://example.com/mcp",
                    "tools": ["*"],
                }
            },
        )

        files = generate_config_files(preview)
        content = files[0]["content"]

        assert "mcp-servers:" in content
        assert "context7:" in content
        assert "url: https://example.com/mcp" in content
        assert "solune-tool-ids: tool-123" in content
        assert "\nmetadata:\n" in content


# ═══════════════════════════════════════════════════════════════════════
# _format_preview
# ═══════════════════════════════════════════════════════════════════════


class TestFormatPreview:
    """Tests for the preview markdown formatter."""

    @pytest.fixture
    def preview(self) -> AgentPreview:
        return AgentPreview(
            name="BugTriager",
            slug="bug-triager",
            description="Triages bug reports",
            system_prompt="You triage bugs " + "x" * 600,  # > 500 chars
            status_column="Triage",
            tools=["list_projects"],
        )

    def test_contains_name(self, preview: AgentPreview):
        result = _format_preview(preview, is_new_column=False)
        assert "## Agent Preview: BugTriager" in result

    def test_contains_slug(self, preview: AgentPreview):
        result = _format_preview(preview, is_new_column=False)
        assert "`bug-triager`" in result

    def test_contains_description(self, preview: AgentPreview):
        result = _format_preview(preview, is_new_column=False)
        assert "Triages bug reports" in result

    def test_contains_tools_display(self, preview: AgentPreview):
        result = _format_preview(preview, is_new_column=False)
        assert "`list_projects`" in result

    def test_contains_file_paths(self, preview: AgentPreview):
        result = _format_preview(preview, is_new_column=False)
        assert ".github/agents/bug-triager.agent.md" in result
        assert ".github/prompts/bug-triager.prompt.md" in result

    def test_new_column_note(self, preview: AgentPreview):
        result = _format_preview(preview, is_new_column=True)
        assert "*(new column)*" in result

    def test_no_new_column_note_when_false(self, preview: AgentPreview):
        result = _format_preview(preview, is_new_column=False)
        assert "*(new column)*" not in result

    def test_long_prompt_truncated(self, preview: AgentPreview):
        result = _format_preview(preview, is_new_column=False)
        assert "..." in result


# ═══════════════════════════════════════════════════════════════════════
# _format_pipeline_report
# ═══════════════════════════════════════════════════════════════════════


class TestFormatPipelineReport:
    """Tests for the pipeline report formatter."""

    @pytest.fixture
    def preview(self) -> AgentPreview:
        return AgentPreview(
            name="TestAgent",
            slug="test-agent",
            description="A test agent",
            system_prompt="prompt",
            status_column="Done",
            tools=[],
        )

    def test_all_success(self, preview: AgentPreview):
        results = [
            PipelineStepResult(step_name="Step A", success=True, detail="OK"),
            PipelineStepResult(step_name="Step B", success=True, detail="OK"),
        ]
        report = _format_pipeline_report(preview, results)
        assert "✅ **Step A** — OK" in report
        assert "✅ **Step B** — OK" in report
        assert "2/2 steps completed" in report

    def test_some_failures(self, preview: AgentPreview):
        results = [
            PipelineStepResult(step_name="Step A", success=True, detail="OK"),
            PipelineStepResult(step_name="Step B", success=False, error="Connection timeout"),
        ]
        report = _format_pipeline_report(preview, results)
        assert "✅ **Step A**" in report
        assert "❌ **Step B**" in report
        assert "Connection timeout" in report
        assert "1/2 steps completed" in report

    def test_empty_results(self, preview: AgentPreview):
        report = _format_pipeline_report(preview, [])
        assert "0/0 steps completed" in report


# ═══════════════════════════════════════════════════════════════════════
# AgentPreview.name_to_slug
# ═══════════════════════════════════════════════════════════════════════


class TestNameToSlug:
    """Tests for slug derivation."""

    def test_simple(self):
        assert AgentPreview.name_to_slug("SecurityReviewer") == "securityreviewer"

    def test_spaces(self):
        assert AgentPreview.name_to_slug("Bug Triager") == "bug-triager"

    def test_special_chars(self):
        assert AgentPreview.name_to_slug("PR Review (Auto)") == "pr-review-auto"

    def test_consecutive_special(self):
        assert AgentPreview.name_to_slug("a--b__c  d") == "a-b-c-d"

    def test_leading_trailing_stripped(self):
        assert AgentPreview.name_to_slug("---test---") == "test"

    def test_empty_string(self):
        assert AgentPreview.name_to_slug("") == ""


# ═══════════════════════════════════════════════════════════════════════
# is_admin_user
# ═══════════════════════════════════════════════════════════════════════


class TestIsAdminUser:
    """Tests for the admin check helper."""

    @pytest.fixture
    async def seeded_db(self, mock_db: aiosqlite.Connection):
        """Seed global_settings row (migrations create the table but don't insert)."""
        await mock_db.execute(
            "INSERT OR IGNORE INTO global_settings (id, updated_at) VALUES (1, '2026-01-01T00:00:00')",
        )
        await mock_db.commit()
        return mock_db

    @pytest.fixture
    async def admin_db(self, seeded_db: aiosqlite.Connection):
        """Set admin_github_user_id in global_settings."""
        await seeded_db.execute(
            "UPDATE global_settings SET admin_github_user_id = ? WHERE id = 1",
            ("12345",),
        )
        await seeded_db.commit()
        return seeded_db

    async def test_admin_user_returns_true(self, admin_db: aiosqlite.Connection):
        assert await is_admin_user(admin_db, "12345") is True

    async def test_non_admin_returns_false(self, admin_db: aiosqlite.Connection):
        assert await is_admin_user(admin_db, "99999") is False

    async def test_no_admin_set_auto_promotes(self, seeded_db: aiosqlite.Connection):
        """When no admin is set in debug mode, the first caller is auto-promoted."""
        mock_settings = AsyncMock()
        mock_settings.debug = True
        mock_settings.admin_github_user_id = None
        with patch("src.config.get_settings", return_value=mock_settings):
            assert await is_admin_user(seeded_db, "12345") is True
        # Verify the admin was persisted.
        cursor = await seeded_db.execute(
            "SELECT admin_github_user_id FROM global_settings WHERE id = 1"
        )
        row = await cursor.fetchone()
        admin_id = row["admin_github_user_id"] if isinstance(row, dict) else row[0]
        assert str(admin_id) == "12345"

    async def test_no_admin_set_second_user_denied(self, seeded_db: aiosqlite.Connection):
        """After auto-promotion, a different user is denied."""
        mock_settings = AsyncMock()
        mock_settings.debug = True
        mock_settings.admin_github_user_id = None
        with patch("src.config.get_settings", return_value=mock_settings):
            assert await is_admin_user(seeded_db, "first-user") is True
            assert await is_admin_user(seeded_db, "second-user") is False

    async def test_no_admin_set_production_denies(self, seeded_db: aiosqlite.Connection):
        """In production mode, missing admin config denies access."""
        mock_settings = AsyncMock()
        mock_settings.debug = False
        mock_settings.admin_github_user_id = None
        with patch("src.config.get_settings", return_value=mock_settings):
            assert await is_admin_user(seeded_db, "12345") is False

    async def test_production_configured_admin_allowed(self, seeded_db: aiosqlite.Connection):
        """In production with ADMIN_GITHUB_USER_ID set, configured admin is allowed and DB seeded."""
        mock_settings = AsyncMock()
        mock_settings.debug = False
        mock_settings.admin_github_user_id = 12345
        with patch("src.config.get_settings", return_value=mock_settings):
            assert await is_admin_user(seeded_db, "12345") is True
        # Verify admin was persisted in DB
        cursor = await seeded_db.execute(
            "SELECT admin_github_user_id FROM global_settings WHERE id = 1"
        )
        row = await cursor.fetchone()
        admin_id = row["admin_github_user_id"] if isinstance(row, dict) else row[0]
        assert str(admin_id) == "12345"

    async def test_production_configured_admin_denies_other(self, seeded_db: aiosqlite.Connection):
        """In production with ADMIN_GITHUB_USER_ID set, non-admin user is denied."""
        mock_settings = AsyncMock()
        mock_settings.debug = False
        mock_settings.admin_github_user_id = 12345
        with patch("src.config.get_settings", return_value=mock_settings):
            assert await is_admin_user(seeded_db, "99999") is False

    async def test_db_error_returns_false(self):
        """If the DB query fails, default to denying access."""
        db = AsyncMock()
        db.execute.side_effect = Exception("DB unavailable")
        assert await is_admin_user(db, "12345") is False


# ═══════════════════════════════════════════════════════════════════════
# handle_agent_command — admin gate
# ═══════════════════════════════════════════════════════════════════════


class TestHandleAgentCommandAdminGate:
    """Tests that handle_agent_command enforces admin-only access."""

    @pytest.fixture
    async def seeded_db(self, mock_db: aiosqlite.Connection):
        """Seed global_settings row."""
        await mock_db.execute(
            "INSERT OR IGNORE INTO global_settings (id, updated_at) VALUES (1, '2026-01-01T00:00:00')",
        )
        await mock_db.commit()
        return mock_db

    async def test_non_admin_denied(self, seeded_db: aiosqlite.Connection):
        """Non-admin user should receive an auth error without any state change."""
        # Pre-set an admin so "not-an-admin" is genuinely non-admin.
        await seeded_db.execute(
            "UPDATE global_settings SET admin_github_user_id = ? WHERE id = 1",
            ("real-admin",),
        )
        await seeded_db.commit()

        result = await handle_agent_command(
            message="#agent Create a test agent",
            session_key="test-session-key",
            project_id="PVT_123",
            owner="testowner",
            repo="testrepo",
            github_user_id="not-an-admin",
            access_token="token",
            db=seeded_db,
            project_columns=["Todo", "Done"],
        )
        assert "restricted to admin" in result
        assert get_active_session("test-session-key") is None

    async def test_admin_proceeds(self, seeded_db: aiosqlite.Connection):
        """Admin user should pass the gate and reach command parsing."""
        # Set up admin
        await seeded_db.execute(
            "UPDATE global_settings SET admin_github_user_id = ? WHERE id = 1",
            ("admin-user",),
        )
        await seeded_db.commit()

        with patch("src.services.agent_creator.get_ai_agent_service") as mock_ai:
            mock_service = AsyncMock()
            mock_service.generate_agent_config.return_value = {
                "name": "TestAgent",
                "description": "A test agent",
                "system_prompt": "You are a test agent.",
                "tools": ["search_code"],
            }
            mock_ai.return_value = mock_service

            result = await handle_agent_command(
                message="#agent Create a test agent #Done",
                session_key="admin-session",
                project_id="PVT_123",
                owner="testowner",
                repo="testrepo",
                github_user_id="admin-user",
                access_token="token",
                db=seeded_db,
                project_columns=["Todo", "Done"],
            )
            # Should proceed to preview (not blocked)
            assert "Agent Preview" in result or "Error" in result
            # Clean up
            clear_session("admin-session")


# ═══════════════════════════════════════════════════════════════════════
# Session management
# ═══════════════════════════════════════════════════════════════════════


class TestSessionManagement:
    """Tests for get_active_session and clear_session."""

    def test_no_session_returns_none(self):
        assert get_active_session("nonexistent-key") is None

    def test_clear_nonexistent_is_noop(self):
        """clear_session on a missing key should not raise."""
        clear_session("nonexistent-key")  # should not raise


# ═══════════════════════════════════════════════════════════════════════
# AgentCreationState model
# ═══════════════════════════════════════════════════════════════════════


class TestAgentCreationState:
    """Tests for the AgentCreationState model."""

    def test_default_step_is_parse(self):
        state = AgentCreationState(session_id="s1")
        assert state.step == CreationStep.PARSE

    def test_github_user_id_stored(self):
        state = AgentCreationState(session_id="s1", github_user_id="12345")
        assert state.github_user_id == "12345"

    def test_github_user_id_defaults_empty(self):
        state = AgentCreationState(session_id="s1")
        assert state.github_user_id == ""

    def test_available_projects_default_empty(self):
        state = AgentCreationState(session_id="s1")
        assert state.available_projects == []


# ---------------------------------------------------------------------------
# T029 - Exception paths
# ---------------------------------------------------------------------------


class TestExceptionPaths:
    """Tests for GitHub API error handling in agent creation pipeline."""

    async def test_db_error_in_admin_check_returns_false(self):
        """Database failures in is_admin_user gracefully deny access."""
        db = AsyncMock()
        db.execute.side_effect = Exception("DB connection lost")
        result = await is_admin_user(db, "12345")
        assert result is False

    async def test_handle_command_with_db_error_returns_error_message(self, mock_db):
        """handle_agent_command returns error string when DB is broken for admin check."""
        broken_db = AsyncMock()
        broken_db.execute.side_effect = Exception("DB unavailable")

        result = await handle_agent_command(
            message="#agent Create a security reviewer",
            session_key="err-session",
            project_id="PVT_1",
            owner="testowner",
            repo="testrepo",
            github_user_id="12345",
            access_token="token",
            db=broken_db,
            project_columns=["Todo", "Done"],
        )
        # Should return an error or denied message, not crash
        assert isinstance(result, str)

    async def test_ai_service_network_error_surfaces_gracefully(self, mock_db):
        """Network errors from AI service are caught during preview generation."""
        await mock_db.execute(
            "INSERT OR IGNORE INTO global_settings (id, updated_at) VALUES (1, '2026-01-01T00:00:00')",
        )
        await mock_db.execute(
            "UPDATE global_settings SET admin_github_user_id = ? WHERE id = 1",
            ("admin-user",),
        )
        await mock_db.commit()

        with patch("src.services.agent_creator.get_ai_agent_service") as mock_ai:
            mock_service = AsyncMock()
            mock_service.generate_agent_config.side_effect = ConnectionError("Network unreachable")
            mock_ai.return_value = mock_service

            result = await handle_agent_command(
                message="#agent Create a reviewer #Done",
                session_key="net-err-session",
                project_id="PVT_1",
                owner="testowner",
                repo="testrepo",
                github_user_id="admin-user",
                access_token="token",
                db=mock_db,
                project_columns=["Todo", "Done"],
            )
            assert isinstance(result, str)
            clear_session("net-err-session")


# ---------------------------------------------------------------------------
# T030 - Config parsing
# ---------------------------------------------------------------------------


class TestConfigParsing:
    """Tests for malformed/missing config scenarios in agent creation."""

    def test_parse_command_empty_raises(self):
        """Empty description after prefix raises ValueError."""
        with pytest.raises(ValueError, match="empty description"):
            parse_command("#agent")

    def test_parse_command_whitespace_only_raises(self):
        """Whitespace-only description raises ValueError."""
        with pytest.raises(ValueError, match="empty description"):
            parse_command("#agent   ")

    def test_parse_command_extracts_status_after_hash(self):
        """Status is extracted from the last # in the command."""
        desc, status = parse_command("#agent Build a linter #In Review")
        assert desc == "Build a linter"
        assert status is not None
        assert "review" in status.lower()

    def test_fuzzy_match_empty_columns_returns_none(self):
        """Fuzzy match with no columns returns (None, False, [])."""
        resolved, ambiguous, matches = fuzzy_match_status("Done", [])
        assert resolved is None
        assert ambiguous is False
        assert matches == []

    def test_fuzzy_match_empty_input_returns_none(self):
        """Fuzzy match with empty input returns no match."""
        resolved, _ambiguous, _matches = fuzzy_match_status("", ["Todo", "Done"])
        assert resolved is None

    async def test_ai_returns_tools_as_non_list(self, mock_db):
        """When AI returns tools as a non-list, it should be handled gracefully."""
        await mock_db.execute(
            "INSERT OR IGNORE INTO global_settings (id, updated_at) VALUES (1, '2026-01-01T00:00:00')",
        )
        await mock_db.execute(
            "UPDATE global_settings SET admin_github_user_id = ? WHERE id = 1",
            ("admin-user",),
        )
        await mock_db.commit()

        with patch("src.services.agent_creator.get_ai_agent_service") as mock_ai:
            mock_service = AsyncMock()
            mock_service.generate_agent_config.return_value = {
                "name": "BadTools",
                "description": "Agent with bad tools",
                "system_prompt": "You are a test.",
                "tools": "not-a-list",
            }
            mock_ai.return_value = mock_service

            result = await handle_agent_command(
                message="#agent Create agent #Done",
                session_key="bad-tools-session",
                project_id="PVT_1",
                owner="testowner",
                repo="testrepo",
                github_user_id="admin-user",
                access_token="token",
                db=mock_db,
                project_columns=["Todo", "Done"],
            )
            assert isinstance(result, str)
            clear_session("bad-tools-session")


# ---------------------------------------------------------------------------
# T031 - Tool assignment
# ---------------------------------------------------------------------------


class TestToolAssignment:
    """Tests for tool assignment logic in config file generation."""

    @pytest.fixture
    def preview_with_tools(self) -> AgentPreview:
        return AgentPreview(
            name="ToolAgent",
            slug="tool-agent",
            description="Agent with tools",
            system_prompt="You use tools.",
            status_column="Done",
            tools=["search_code", "create_issue"],
        )

    @pytest.fixture
    def preview_no_tools(self) -> AgentPreview:
        return AgentPreview(
            name="NoToolAgent",
            slug="no-tool-agent",
            description="Agent without extras",
            system_prompt="You do things.",
            status_column="Done",
            tools=[],
        )

    def test_tools_appear_in_preview_format(self, preview_with_tools):
        """Tools list is included in the formatted preview."""
        from src.services.agent_creator import _format_preview

        text = _format_preview(preview_with_tools, is_new_column=False)
        assert "search_code" in text
        assert "create_issue" in text

    def test_no_tools_omits_tools_section_in_config(self, preview_no_tools):
        """Config files with no tools should not include a tools key in frontmatter."""
        files = generate_config_files(preview_no_tools)
        agent_file = files[0]
        assert "tools" not in agent_file["content"].split("---")[1]

    def test_tools_with_mcp_servers_in_frontmatter(self):
        """MCP servers appear in agent file frontmatter when specified."""
        preview = AgentPreview(
            name="McpAgent",
            slug="mcp-agent",
            description="Agent with MCP",
            system_prompt="You use MCP.",
            status_column="Done",
            tools=["tool1"],
            tool_ids=["tid-1"],
            mcp_servers={"my-server": {"url": "https://example.com"}},
        )
        files = generate_config_files(preview)
        agent_content = files[0]["content"]
        assert "mcp-servers" in agent_content or "mcp_servers" in agent_content

    def test_config_files_count_is_two(self, preview_with_tools):
        """generate_config_files always returns exactly 2 files."""
        files = generate_config_files(preview_with_tools)
        assert len(files) == 2

    def test_agent_file_path_matches_slug(self, preview_with_tools):
        """Agent file path contains the slug."""
        files = generate_config_files(preview_with_tools)
        assert "tool-agent" in files[0]["path"]

    def test_prompt_file_path_matches_slug(self, preview_with_tools):
        """Prompt file path contains the slug."""
        files = generate_config_files(preview_with_tools)
        assert "tool-agent" in files[1]["path"]


# ═══════════════════════════════════════════════════════════════════════
# Status resolution — _resolve_status_step / _handle_status_selection
# ═══════════════════════════════════════════════════════════════════════


class TestStatusResolution:
    """Tests for the status resolution flow via handle_agent_command."""

    @pytest.fixture
    async def seeded_db(self, mock_db: aiosqlite.Connection):
        await mock_db.execute(
            "INSERT OR IGNORE INTO global_settings (id, updated_at) VALUES (1, '2024-01-01T00:00:00Z')",
        )
        await mock_db.commit()
        return mock_db

    @pytest.fixture
    async def admin_db(self, seeded_db: aiosqlite.Connection):
        await seeded_db.execute(
            "UPDATE global_settings SET admin_github_user_id = ? WHERE id = 1",
            ("12345",),
        )
        await seeded_db.commit()
        return seeded_db

    @pytest.fixture(autouse=True)
    def _clear_sessions(self):
        from src.services.agent_creator import _agent_sessions

        _agent_sessions.clear()
        yield
        _agent_sessions.clear()

    # T024
    async def test_empty_status_prompts_for_column(self, admin_db: aiosqlite.Connection):
        """When no status is provided, user is asked to choose a column."""
        result = await handle_agent_command(
            message="#agent Reviews PRs",
            session_key="sess-t024",
            project_id="PVT_1",
            owner="o",
            repo="r",
            github_user_id="12345",
            access_token="tok",
            db=admin_db,
            project_columns=["Todo", "In Progress", "Done"],
        )
        assert "Which status column" in result
        assert "1. Todo" in result
        state = get_active_session("sess-t024")
        assert state is not None
        assert state.step == CreationStep.RESOLVE_STATUS

    # T025
    async def test_case_insensitive_match_resolves(self, admin_db: aiosqlite.Connection):
        """Status provided as 'in-progress' matches 'In Progress' column."""
        with patch("src.services.agent_creator.get_ai_agent_service") as mock_ai:
            svc = AsyncMock()
            svc.generate_agent_config.return_value = {
                "name": "Reviewer",
                "description": "Reviews code",
                "system_prompt": "You review code.",
                "tools": [],
            }
            mock_ai.return_value = svc

            result = await handle_agent_command(
                message="#agent Reviews code #in-progress",
                session_key="sess-t025",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "In Progress", "Done"],
            )
        assert "Agent Preview" in result
        state = get_active_session("sess-t025")
        assert state is not None
        assert state.resolved_status == "In Progress"
        assert state.is_new_column is False

    # T026
    async def test_out_of_range_selection_returns_error(self, admin_db: aiosqlite.Connection):
        """Typing an out-of-range number returns a helpful error."""
        # First trigger the ambiguous prompt by providing a status that matches
        # two columns.

        result = await handle_agent_command(
            message="#agent My agent #review",
            session_key="sess-t026",
            project_id="PVT_1",
            owner="o",
            repo="r",
            github_user_id="12345",
            access_token="tok",
            db=admin_db,
            project_columns=["In Review", "Code Review"],
        )
        assert "Multiple columns" in result

        # Now respond with invalid number
        result2 = await handle_agent_command(
            message="99",
            session_key="sess-t026",
            project_id="PVT_1",
            owner="o",
            repo="r",
            github_user_id="12345",
            access_token="tok",
            db=admin_db,
            project_columns=["In Review", "Code Review"],
        )
        assert "between 1 and" in result2

    # T027
    async def test_no_match_proposes_new_column(self, admin_db: aiosqlite.Connection):
        """Unrecognized status results in a new column proposal."""
        with patch("src.services.agent_creator.get_ai_agent_service") as mock_ai:
            svc = AsyncMock()
            svc.generate_agent_config.return_value = {
                "name": "Triager",
                "description": "Triages issues",
                "system_prompt": "You triage issues.",
                "tools": [],
            }
            mock_ai.return_value = svc

            result = await handle_agent_command(
                message="#agent Triages issues #brand-new-status",
                session_key="sess-t027",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "Done"],
            )
        assert "Agent Preview" in result
        state = get_active_session("sess-t027")
        assert state is not None
        assert state.is_new_column is True
        assert state.resolved_status == "Brand New Status"


# ═══════════════════════════════════════════════════════════════════════
# Creation pipeline — _execute_creation_pipeline
# ═══════════════════════════════════════════════════════════════════════


class TestCreationPipeline:
    """Tests for the 7-step creation pipeline."""

    @pytest.fixture
    async def seeded_db(self, mock_db: aiosqlite.Connection):
        await mock_db.execute(
            "INSERT OR IGNORE INTO global_settings (id, updated_at) VALUES (1, '2024-01-01T00:00:00Z')",
        )
        await mock_db.commit()
        return mock_db

    @pytest.fixture
    async def admin_db(self, seeded_db: aiosqlite.Connection):
        await seeded_db.execute(
            "UPDATE global_settings SET admin_github_user_id = ? WHERE id = 1",
            ("12345",),
        )
        await seeded_db.commit()
        return seeded_db

    @pytest.fixture(autouse=True)
    def _clear_sessions(self):
        from src.services.agent_creator import _agent_sessions

        _agent_sessions.clear()
        yield
        _agent_sessions.clear()

    def _ai_mock(self, name: str = "TestBot"):
        """Return a patched AI service mock with valid generate_agent_config."""
        patcher = patch("src.services.agent_creator.get_ai_agent_service")
        mock_ai = patcher.start()
        svc = AsyncMock()
        svc.generate_agent_config.return_value = {
            "name": name,
            "description": "A test bot",
            "system_prompt": "You are a test bot.",
            "tools": ["tool1"],
        }
        svc.edit_agent_config.return_value = {
            "name": name,
            "description": "Edited",
            "system_prompt": "Edited prompt.",
        }
        mock_ai.return_value = svc
        return patcher, svc

    def _gps_mock(self):
        """Return a patched github_projects_service mock with all pipeline methods."""
        patcher = patch("src.services.agent_creator.github_projects_service")
        mock_gps = patcher.start()
        mock_gps.create_issue = AsyncMock(
            return_value={
                "number": 42,
                "node_id": "I_42",
                "id": 1,
                "html_url": "https://github.com/o/r/issues/42",
            }
        )
        mock_gps.get_repository_info = AsyncMock(
            return_value={
                "repository_id": "R_1",
                "head_oid": "abc123",
                "default_branch": "main",
            }
        )
        mock_gps.create_branch = AsyncMock(return_value="ref-id-1")
        mock_gps.commit_files = AsyncMock(return_value="commit-oid-1")
        mock_gps.create_pull_request = AsyncMock(
            return_value={"number": 10, "url": "https://github.com/o/r/pull/10"}
        )
        mock_gps.add_issue_to_project = AsyncMock(return_value="item-1")
        mock_gps.update_item_status_by_name = AsyncMock()
        return patcher, mock_gps

    async def _drive_to_preview(
        self,
        admin_db: aiosqlite.Connection,
        session_key: str,
        *,
        name: str = "TestBot",
    ) -> str:
        """Drive the conversation through to the preview step."""
        ai_patcher, _ = self._ai_mock(name)
        try:
            result = await handle_agent_command(
                message=f"#agent Build a {name} #Done",
                session_key=session_key,
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "In Progress", "Done"],
            )
        finally:
            ai_patcher.stop()
        return result

    # T028
    async def test_duplicate_name_halts_pipeline(self, admin_db: aiosqlite.Connection):
        """Pipeline stops when an agent with the same name already exists."""
        # Pre-insert an agent with the same name
        await admin_db.execute(
            """INSERT INTO agent_configs
               (id, name, slug, description, system_prompt, status_column,
                tools, project_id, owner, repo, created_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "existing-id",
                "TestBot",
                "test-bot",
                "Already exists",
                "prompt",
                "Done",
                "[]",
                "PVT_1",
                "o",
                "r",
                "12345",
                "2024-01-01T00:00:00Z",
            ),
        )
        await admin_db.commit()

        preview_result = await self._drive_to_preview(admin_db, "sess-t028")
        assert "Agent Preview" in preview_result

        # Now confirm to trigger pipeline
        gps_patcher, _ = self._gps_mock()
        try:
            result = await handle_agent_command(
                message="create",
                session_key="sess-t028",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "In Progress", "Done"],
            )
        finally:
            gps_patcher.stop()

        assert "already exists" in result
        assert get_active_session("sess-t028") is None

    # T029
    async def test_issue_creation_failure_continues(self, admin_db: aiosqlite.Connection):
        """When issue creation fails, pipeline continues with a warning."""
        preview_result = await self._drive_to_preview(admin_db, "sess-t029", name="IssueBot")
        assert "Agent Preview" in preview_result

        gps_patcher, mock_gps = self._gps_mock()
        mock_gps.create_issue = AsyncMock(side_effect=RuntimeError("GitHub API error"))
        try:
            result = await handle_agent_command(
                message="create",
                session_key="sess-t029",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "In Progress", "Done"],
            )
        finally:
            gps_patcher.stop()

        assert "Agent Created" in result
        assert "Create GitHub Issue" in result
        # Issue step should be marked as failed
        assert "GitHub API error" in result

    # T030
    async def test_pr_creation_failure_logged(self, admin_db: aiosqlite.Connection):
        """When PR creation fails, pipeline continues and reports the error."""
        preview_result = await self._drive_to_preview(admin_db, "sess-t030", name="PrBot")
        assert "Agent Preview" in preview_result

        gps_patcher, mock_gps = self._gps_mock()
        mock_gps.create_pull_request = AsyncMock(side_effect=RuntimeError("PR API error"))
        try:
            result = await handle_agent_command(
                message="create",
                session_key="sess-t030",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "In Progress", "Done"],
            )
        finally:
            gps_patcher.stop()

        assert "Agent Created" in result
        assert "Open Pull Request" in result
        assert "PR API error" in result
        # Issue creation should have succeeded
        assert "Create GitHub Issue" in result


# ═══════════════════════════════════════════════════════════════════════
# AI service failures
# ═══════════════════════════════════════════════════════════════════════


class TestAIServiceFailures:
    """Tests for AI service error handling paths."""

    @pytest.fixture
    async def seeded_db(self, mock_db: aiosqlite.Connection):
        await mock_db.execute(
            "INSERT OR IGNORE INTO global_settings (id, updated_at) VALUES (1, '2024-01-01T00:00:00Z')",
        )
        await mock_db.commit()
        return mock_db

    @pytest.fixture
    async def admin_db(self, seeded_db: aiosqlite.Connection):
        await seeded_db.execute(
            "UPDATE global_settings SET admin_github_user_id = ? WHERE id = 1",
            ("12345",),
        )
        await seeded_db.commit()
        return seeded_db

    @pytest.fixture(autouse=True)
    def _clear_sessions(self):
        from src.services.agent_creator import _agent_sessions

        _agent_sessions.clear()
        yield
        _agent_sessions.clear()

    # T031
    async def test_generate_config_raises_clears_session(self, admin_db: aiosqlite.Connection):
        """When generate_agent_config raises, session is cleared and error returned."""
        with patch("src.services.agent_creator.get_ai_agent_service") as mock_ai:
            svc = AsyncMock()
            svc.generate_agent_config.side_effect = RuntimeError("AI down")
            mock_ai.return_value = svc

            result = await handle_agent_command(
                message="#agent Build a bot #Done",
                session_key="sess-t031",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "Done"],
            )

        assert "Error" in result
        assert "AI down" in result
        assert get_active_session("sess-t031") is None

    # T032
    async def test_edit_config_fails_preserves_preview(self, admin_db: aiosqlite.Connection):
        """When edit_agent_config fails, error returned but preview preserved."""
        # First get to preview
        with patch("src.services.agent_creator.get_ai_agent_service") as mock_ai:
            svc = AsyncMock()
            svc.generate_agent_config.return_value = {
                "name": "EditBot",
                "description": "Test",
                "system_prompt": "Prompt.",
                "tools": [],
            }
            mock_ai.return_value = svc

            await handle_agent_command(
                message="#agent Build a bot #Done",
                session_key="sess-t032",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "Done"],
            )

        state_before = get_active_session("sess-t032")
        assert state_before is not None
        assert state_before.preview is not None
        original_name = state_before.preview.name

        # Now try an edit that fails
        with patch("src.services.agent_creator.get_ai_agent_service") as mock_ai2:
            svc2 = AsyncMock()
            svc2.edit_agent_config.side_effect = RuntimeError("Edit failed")
            mock_ai2.return_value = svc2

            result = await handle_agent_command(
                message="change name to FooBot",
                session_key="sess-t032",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "Done"],
            )

        assert "Error" in result
        assert "Edit failed" in result
        # Preview should still exist
        state_after = get_active_session("sess-t032")
        assert state_after is not None
        assert state_after.preview is not None
        assert state_after.preview.name == original_name

    # T032b
    async def test_edit_can_retry_after_failure(self, admin_db: aiosqlite.Connection):
        """A failed edit keeps the preview so a later retry can still succeed."""
        with patch("src.services.agent_creator.get_ai_agent_service") as mock_ai:
            svc = AsyncMock()
            svc.generate_agent_config.return_value = {
                "name": "RetryBot",
                "description": "Test",
                "system_prompt": "Prompt.",
                "tools": [],
            }
            mock_ai.return_value = svc

            initial_result = await handle_agent_command(
                message="#agent Build a bot #Done",
                session_key="sess-t032b",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "Done"],
            )

        assert "Agent Preview" in initial_result
        assert "RetryBot" in initial_result

        with patch("src.services.agent_creator.get_ai_agent_service") as mock_ai_fail:
            failing_service = AsyncMock()
            failing_service.edit_agent_config.side_effect = RuntimeError("Edit failed")
            mock_ai_fail.return_value = failing_service

            failed_result = await handle_agent_command(
                message="change name to FooBot",
                session_key="sess-t032b",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "Done"],
            )

        assert "Error" in failed_result

        with patch("src.services.agent_creator.get_ai_agent_service") as mock_ai_retry:
            retry_service = AsyncMock()
            retry_service.edit_agent_config.return_value = {
                "name": "RetryBotV2",
                "description": "Updated",
                "system_prompt": "Updated prompt.",
                "tools": [],
            }
            mock_ai_retry.return_value = retry_service

            retry_result = await handle_agent_command(
                message="change name to RetryBotV2",
                session_key="sess-t032b",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "Done"],
            )

        assert "Agent Preview" in retry_result
        assert "RetryBotV2" in retry_result
        state_after_retry = get_active_session("sess-t032b")
        assert state_after_retry is not None
        assert state_after_retry.step == CreationStep.EDIT_LOOP
        assert state_after_retry.preview is not None
        assert state_after_retry.preview.name == "RetryBotV2"

    # T033
    async def test_ai_returns_string_tools_defaults_to_empty(self, admin_db: aiosqlite.Connection):
        """When AI returns a non-list for tools, it defaults to empty list."""
        with patch("src.services.agent_creator.get_ai_agent_service") as mock_ai:
            svc = AsyncMock()
            svc.generate_agent_config.return_value = {
                "name": "ToolBot",
                "description": "A bot",
                "system_prompt": "Prompt.",
                "tools": "not-a-list",
            }
            mock_ai.return_value = svc

            result = await handle_agent_command(
                message="#agent Build a bot #Done",
                session_key="sess-t033",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "Done"],
            )

        assert "Agent Preview" in result
        state = get_active_session("sess-t033")
        assert state is not None
        assert state.preview is not None
        assert state.preview.tools == []


# ═══════════════════════════════════════════════════════════════════════
# Additional coverage — status selection, edit flow, edge cases
# ═══════════════════════════════════════════════════════════════════════


class TestStatusSelectionFlow:
    """Tests for _handle_status_selection via handle_agent_command."""

    @pytest.fixture
    async def seeded_db(self, mock_db: aiosqlite.Connection):
        await mock_db.execute(
            "INSERT OR IGNORE INTO global_settings (id, updated_at) VALUES (1, '2024-01-01T00:00:00Z')",
        )
        await mock_db.commit()
        return mock_db

    @pytest.fixture
    async def admin_db(self, seeded_db: aiosqlite.Connection):
        await seeded_db.execute(
            "UPDATE global_settings SET admin_github_user_id = ? WHERE id = 1",
            ("12345",),
        )
        await seeded_db.commit()
        return seeded_db

    @pytest.fixture(autouse=True)
    def _clear_sessions(self):
        from src.services.agent_creator import _agent_sessions

        _agent_sessions.clear()
        yield
        _agent_sessions.clear()

    async def test_valid_numeric_selection_resolves(self, admin_db: aiosqlite.Connection):
        """Typing a valid number picks that column and generates preview."""
        # Trigger ambiguous status
        result = await handle_agent_command(
            message="#agent My agent #review",
            session_key="sess-sel1",
            project_id="PVT_1",
            owner="o",
            repo="r",
            github_user_id="12345",
            access_token="tok",
            db=admin_db,
            project_columns=["In Review", "Code Review"],
        )
        assert "Multiple columns" in result

        # Respond with valid number
        with patch("src.services.agent_creator.get_ai_agent_service") as mock_ai:
            svc = AsyncMock()
            svc.generate_agent_config.return_value = {
                "name": "Reviewer",
                "description": "Reviews",
                "system_prompt": "You review.",
                "tools": [],
            }
            mock_ai.return_value = svc

            result2 = await handle_agent_command(
                message="1",
                session_key="sess-sel1",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["In Review", "Code Review"],
            )
        assert "Agent Preview" in result2
        state = get_active_session("sess-sel1")
        assert state is not None
        assert state.resolved_status == "In Review"

    async def test_text_selection_creates_new_column(self, admin_db: aiosqlite.Connection):
        """Typing free text during status selection creates a new column."""
        # First prompt for status (no status provided)
        result = await handle_agent_command(
            message="#agent My agent",
            session_key="sess-sel2",
            project_id="PVT_1",
            owner="o",
            repo="r",
            github_user_id="12345",
            access_token="tok",
            db=admin_db,
            project_columns=["Todo", "Done"],
        )
        assert "Which status column" in result

        # Respond with free text
        with patch("src.services.agent_creator.get_ai_agent_service") as mock_ai:
            svc = AsyncMock()
            svc.generate_agent_config.return_value = {
                "name": "Agent",
                "description": "An agent",
                "system_prompt": "You are an agent.",
                "tools": [],
            }
            mock_ai.return_value = svc

            result2 = await handle_agent_command(
                message="custom-status",
                session_key="sess-sel2",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "Done"],
            )
        assert "Agent Preview" in result2
        state = get_active_session("sess-sel2")
        assert state is not None
        assert state.is_new_column is True
        assert state.resolved_status == "Custom Status"


class TestEditFlow:
    """Tests for the _apply_edit path via handle_agent_command."""

    @pytest.fixture
    async def seeded_db(self, mock_db: aiosqlite.Connection):
        await mock_db.execute(
            "INSERT OR IGNORE INTO global_settings (id, updated_at) VALUES (1, '2024-01-01T00:00:00Z')",
        )
        await mock_db.commit()
        return mock_db

    @pytest.fixture
    async def admin_db(self, seeded_db: aiosqlite.Connection):
        await seeded_db.execute(
            "UPDATE global_settings SET admin_github_user_id = ? WHERE id = 1",
            ("12345",),
        )
        await seeded_db.commit()
        return seeded_db

    @pytest.fixture(autouse=True)
    def _clear_sessions(self):
        from src.services.agent_creator import _agent_sessions

        _agent_sessions.clear()
        yield
        _agent_sessions.clear()

    async def test_successful_edit_updates_preview(self, admin_db: aiosqlite.Connection):
        """Successful edit updates the preview and sets step to EDIT_LOOP."""
        # Get to preview
        with patch("src.services.agent_creator.get_ai_agent_service") as mock_ai:
            svc = AsyncMock()
            svc.generate_agent_config.return_value = {
                "name": "OldName",
                "description": "Old desc",
                "system_prompt": "Old prompt.",
                "tools": ["tool1"],
            }
            mock_ai.return_value = svc

            await handle_agent_command(
                message="#agent Build a bot #Done",
                session_key="sess-edit1",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "Done"],
            )

        # Now send an edit
        with patch("src.services.agent_creator.get_ai_agent_service") as mock_ai2:
            svc2 = AsyncMock()
            svc2.edit_agent_config.return_value = {
                "name": "NewName",
                "description": "New desc",
                "system_prompt": "New prompt.",
            }
            mock_ai2.return_value = svc2

            result = await handle_agent_command(
                message="change the name to NewName",
                session_key="sess-edit1",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "Done"],
            )

        assert "Agent Preview" in result
        assert "NewName" in result
        state = get_active_session("sess-edit1")
        assert state is not None
        assert state.step == CreationStep.EDIT_LOOP
        assert state.preview is not None
        assert state.preview.name == "NewName"

    async def test_empty_status_no_columns(self, admin_db: aiosqlite.Connection):
        """When no status and no columns, user gets a free-text prompt."""
        result = await handle_agent_command(
            message="#agent A simple agent",
            session_key="sess-edit2",
            project_id="PVT_1",
            owner="o",
            repo="r",
            github_user_id="12345",
            access_token="tok",
            db=admin_db,
            project_columns=[],
        )
        assert "type a column name" in result

    async def test_missing_context_returns_error(self, admin_db: aiosqlite.Connection):
        """Pipeline with missing project_id returns error."""
        with patch("src.services.agent_creator.get_ai_agent_service") as mock_ai:
            svc = AsyncMock()
            svc.generate_agent_config.return_value = {
                "name": "Bot",
                "description": "A bot",
                "system_prompt": "Prompt.",
                "tools": [],
            }
            mock_ai.return_value = svc

            await handle_agent_command(
                message="#agent Build a bot #Done",
                session_key="sess-edit3",
                project_id=None,
                owner=None,
                repo=None,
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "Done"],
            )

        # Session should be in RESOLVE_PROJECT step (Signal flow)
        state = get_active_session("sess-edit3")
        assert state is not None
        assert state.step == CreationStep.RESOLVE_PROJECT


# ═══════════════════════════════════════════════════════════════════════
# generate_issue_body
# ═══════════════════════════════════════════════════════════════════════


class TestGenerateIssueBody:
    """Tests for generate_issue_body helper."""

    def test_basic_body(self):
        from src.services.agent_creator import generate_issue_body

        preview = AgentPreview(
            name="SecBot",
            slug="sec-bot",
            description="Reviews security",
            system_prompt="You review security.",
            status_column="In Review",
            tools=["search_code"],
        )
        body = generate_issue_body(preview)
        assert "# Agent Configuration: SecBot" in body
        assert "**Description:** Reviews security" in body
        assert "**Status Column:** In Review" in body
        assert "`sec-bot`" in body
        assert "`search_code`" in body
        assert "#agent" in body

    def test_more_than_10_tools_truncated(self):
        from src.services.agent_creator import generate_issue_body

        tools = [f"tool{i}" for i in range(15)]
        preview = AgentPreview(
            name="ManyToolsBot",
            slug="many-tools-bot",
            description="Has many tools",
            system_prompt="Prompt.",
            status_column="Done",
            tools=tools,
        )
        body = generate_issue_body(preview)
        assert "(+5 more)" in body
        # Only first 10 tools shown
        assert "`tool9`" in body
        assert "`tool10`" not in body

    def test_empty_tools(self):
        from src.services.agent_creator import generate_issue_body

        preview = AgentPreview(
            name="NoTool",
            slug="no-tool",
            description="No tools",
            system_prompt="Prompt.",
            status_column="Done",
            tools=[],
        )
        body = generate_issue_body(preview)
        assert "**Tools:** " in body


# ═══════════════════════════════════════════════════════════════════════
# _handle_existing_session — DONE step routing
# ═══════════════════════════════════════════════════════════════════════


class TestExistingSessionDoneStep:
    """Tests for handle_agent_command routing when session step is DONE."""

    @pytest.fixture
    async def admin_db(self, mock_db: aiosqlite.Connection):
        await mock_db.execute(
            "INSERT OR IGNORE INTO global_settings (id, updated_at) VALUES (1, '2024-01-01T00:00:00Z')",
        )
        await mock_db.execute(
            "UPDATE global_settings SET admin_github_user_id = ? WHERE id = 1",
            ("12345",),
        )
        await mock_db.commit()
        return mock_db

    @pytest.fixture(autouse=True)
    def _clear_sessions(self):
        from src.services.agent_creator import _agent_sessions

        _agent_sessions.clear()
        yield
        _agent_sessions.clear()

    async def test_done_session_with_non_agent_message(self, admin_db):
        """After DONE, a non-#agent message returns 'complete' message."""
        from src.services.agent_creator import _agent_sessions

        state = AgentCreationState(
            session_id="sess-done1",
            github_user_id="12345",
            project_id="PVT_1",
            owner="o",
            repo="r",
        )
        state.step = CreationStep.DONE
        _agent_sessions["sess-done1"] = state

        result = await handle_agent_command(
            message="hello",
            session_key="sess-done1",
            project_id="PVT_1",
            owner="o",
            repo="r",
            github_user_id="12345",
            access_token="tok",
            db=admin_db,
        )
        assert "complete" in result.lower() or "start a new one" in result.lower()
        assert get_active_session("sess-done1") is None

    async def test_done_session_with_new_agent_command(self, admin_db):
        """After DONE, a new #agent command starts a fresh session."""
        from src.services.agent_creator import _agent_sessions

        state = AgentCreationState(
            session_id="sess-done2",
            github_user_id="12345",
            project_id="PVT_1",
            owner="o",
            repo="r",
        )
        state.step = CreationStep.DONE
        _agent_sessions["sess-done2"] = state

        with patch("src.services.agent_creator.get_ai_agent_service") as mock_ai:
            svc = AsyncMock()
            svc.generate_agent_config.return_value = {
                "name": "FreshBot",
                "description": "Fresh",
                "system_prompt": "Fresh prompt.",
                "tools": [],
            }
            mock_ai.return_value = svc

            result = await handle_agent_command(
                message="#agent Build a fresh bot #Done",
                session_key="sess-done2",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "Done"],
            )
        assert "Agent Preview" in result or "complete" in result.lower()

    async def test_unexpected_state_returns_start_over(self, admin_db):
        """An unexpected step returns a 'start over' message."""
        from src.services.agent_creator import _agent_sessions

        state = AgentCreationState(
            session_id="sess-unexp",
            github_user_id="12345",
            project_id="PVT_1",
            owner="o",
            repo="r",
        )
        state.step = CreationStep.EXECUTING  # shouldn't receive messages in this state
        _agent_sessions["sess-unexp"] = state

        result = await handle_agent_command(
            message="some message",
            session_key="sess-unexp",
            project_id="PVT_1",
            owner="o",
            repo="r",
            github_user_id="12345",
            access_token="tok",
            db=admin_db,
        )
        assert "start over" in result.lower() or "unexpected" in result.lower()


# ═══════════════════════════════════════════════════════════════════════
# _handle_project_selection — Signal flow
# ═══════════════════════════════════════════════════════════════════════


class TestProjectSelection:
    """Tests for project selection in Signal flow."""

    @pytest.fixture
    async def admin_db(self, mock_db: aiosqlite.Connection):
        await mock_db.execute(
            "INSERT OR IGNORE INTO global_settings (id, updated_at) VALUES (1, '2024-01-01T00:00:00Z')",
        )
        await mock_db.execute(
            "UPDATE global_settings SET admin_github_user_id = ? WHERE id = 1",
            ("12345",),
        )
        await mock_db.commit()
        return mock_db

    @pytest.fixture(autouse=True)
    def _clear_sessions(self):
        from src.services.agent_creator import _agent_sessions

        _agent_sessions.clear()
        yield
        _agent_sessions.clear()

    async def test_prompt_project_selection_message(self, admin_db):
        """When no project_id is provided, user is prompted for project."""
        with patch("src.services.agent_creator.get_ai_agent_service") as mock_ai:
            svc = AsyncMock()
            mock_ai.return_value = svc

            result = await handle_agent_command(
                message="#agent A bot for security",
                session_key="sess-proj1",
                project_id=None,
                owner=None,
                repo=None,
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
            )
        assert "Which project" in result
        state = get_active_session("sess-proj1")
        assert state is not None
        assert state.step == CreationStep.RESOLVE_PROJECT

    async def test_project_selection_free_text_fallback(self, admin_db):
        """Free text in project selection returns could-not-resolve message."""
        from src.services.agent_creator import _agent_sessions

        state = AgentCreationState(
            session_id="sess-proj2",
            github_user_id="12345",
            raw_description="A bot",
        )
        state.step = CreationStep.RESOLVE_PROJECT
        state.available_projects = []
        _agent_sessions["sess-proj2"] = state

        result = await handle_agent_command(
            message="my-project",
            session_key="sess-proj2",
            project_id=None,
            owner=None,
            repo=None,
            github_user_id="12345",
            access_token="tok",
            db=admin_db,
        )
        assert "Could not resolve" in result

    async def test_project_selection_numeric_valid(self, admin_db):
        """Numeric selection resolves the project and proceeds to status."""
        from src.services.agent_creator import _agent_sessions

        state = AgentCreationState(
            session_id="sess-proj3",
            github_user_id="12345",
            raw_description="A bot",
        )
        state.step = CreationStep.RESOLVE_PROJECT
        state.available_projects = [
            {"id": "PVT_1", "title": "My Project"},
            {"id": "PVT_2", "title": "Other Project"},
        ]
        _agent_sessions["sess-proj3"] = state

        with patch("src.services.agent_creator._resolve_owner_repo", new_callable=AsyncMock) as mock_resolve:
            mock_resolve.return_value = ("owner", "repo")

            result = await handle_agent_command(
                message="1",
                session_key="sess-proj3",
                project_id=None,
                owner=None,
                repo=None,
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
            )
        assert "Which status column" in result or "type a column name" in result
        state_after = get_active_session("sess-proj3")
        assert state_after is not None
        assert state_after.project_id == "PVT_1"

    async def test_project_selection_numeric_out_of_range(self, admin_db):
        """Out-of-range number returns error message."""
        from src.services.agent_creator import _agent_sessions

        state = AgentCreationState(
            session_id="sess-proj4",
            github_user_id="12345",
            raw_description="A bot",
        )
        state.step = CreationStep.RESOLVE_PROJECT
        state.available_projects = [{"id": "PVT_1", "title": "Proj"}]
        _agent_sessions["sess-proj4"] = state

        result = await handle_agent_command(
            message="99",
            session_key="sess-proj4",
            project_id=None,
            owner=None,
            repo=None,
            github_user_id="12345",
            access_token="tok",
            db=admin_db,
        )
        assert "between 1 and" in result


# ═══════════════════════════════════════════════════════════════════════
# Full pipeline success + step 8 + pipeline mappings
# ═══════════════════════════════════════════════════════════════════════


class TestFullPipelineSuccess:
    """Tests for the complete creation pipeline success path."""

    @pytest.fixture
    async def admin_db(self, mock_db: aiosqlite.Connection):
        await mock_db.execute(
            "INSERT OR IGNORE INTO global_settings (id, updated_at) VALUES (1, '2024-01-01T00:00:00Z')",
        )
        await mock_db.execute(
            "UPDATE global_settings SET admin_github_user_id = ? WHERE id = 1",
            ("12345",),
        )
        await mock_db.commit()
        # Insert project_settings row for pipeline mapping tests
        await mock_db.execute(
            "INSERT OR IGNORE INTO project_settings (github_user_id, project_id, updated_at) "
            "VALUES (?, ?, ?)",
            ("12345", "PVT_1", "2024-01-01T00:00:00Z"),
        )
        await mock_db.commit()
        return mock_db

    @pytest.fixture(autouse=True)
    def _clear_sessions(self):
        from src.services.agent_creator import _agent_sessions

        _agent_sessions.clear()
        yield
        _agent_sessions.clear()

    def _ai_mock(self, name="FullBot"):
        patcher = patch("src.services.agent_creator.get_ai_agent_service")
        mock_ai = patcher.start()
        svc = AsyncMock()
        svc.generate_agent_config.return_value = {
            "name": name,
            "description": "A full bot",
            "system_prompt": "You are a full bot.",
            "tools": ["tool1"],
        }
        mock_ai.return_value = svc
        return patcher, svc

    def _gps_mock(self):
        patcher = patch("src.services.agent_creator.github_projects_service")
        mock_gps = patcher.start()
        mock_gps.create_issue = AsyncMock(
            return_value={
                "number": 42,
                "node_id": "I_42",
                "id": 1,
                "html_url": "https://github.com/o/r/issues/42",
            }
        )
        mock_gps.get_repository_info = AsyncMock(
            return_value={
                "repository_id": "R_1",
                "head_oid": "abc123",
                "default_branch": "main",
            }
        )
        mock_gps.create_branch = AsyncMock(return_value="ref-id-1")
        mock_gps.commit_files = AsyncMock(return_value="commit-oid-1")
        mock_gps.create_pull_request = AsyncMock(
            return_value={"number": 10, "url": "https://github.com/o/r/pull/10"}
        )
        mock_gps.add_issue_to_project = AsyncMock(return_value="item-1")
        mock_gps.update_item_status_by_name = AsyncMock()
        return patcher, mock_gps

    async def _drive_to_preview(self, admin_db, session_key, *, name="FullBot"):
        ai_patcher, _ = self._ai_mock(name)
        try:
            result = await handle_agent_command(
                message=f"#agent Build a {name} #Done",
                session_key=session_key,
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "In Progress", "Done"],
            )
        finally:
            ai_patcher.stop()
        return result

    async def test_full_success_pipeline(self, admin_db):
        """Full pipeline: all steps succeed and report is returned."""
        preview_result = await self._drive_to_preview(admin_db, "sess-full1")
        assert "Agent Preview" in preview_result

        gps_patcher, _mock_gps = self._gps_mock()
        try:
            result = await handle_agent_command(
                message="create",
                session_key="sess-full1",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "In Progress", "Done"],
            )
        finally:
            gps_patcher.stop()

        assert "Agent Created" in result
        # All pipeline steps should succeed
        assert "Save agent configuration" in result
        assert "Verify project column" in result
        assert "Create GitHub Issue" in result
        assert "Create branch" in result
        assert "Commit configuration files" in result
        assert "Open Pull Request" in result
        assert "Move issue to In Review" in result
        # Session should be DONE
        state = get_active_session("sess-full1")
        assert state is not None
        assert state.step == CreationStep.DONE

    async def test_branch_failure_skips_commit_and_pr(self, admin_db):
        """When branch creation fails, commit and PR are skipped."""
        preview_result = await self._drive_to_preview(admin_db, "sess-brfail", name="BrBot")
        assert "Agent Preview" in preview_result

        gps_patcher, mock_gps = self._gps_mock()
        mock_gps.create_branch = AsyncMock(return_value=None)
        try:
            result = await handle_agent_command(
                message="create",
                session_key="sess-brfail",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "In Progress", "Done"],
            )
        finally:
            gps_patcher.stop()

        assert "Agent Created" in result
        assert "branch creation failed" in result.lower() or "create_branch returned None" in result

    async def test_commit_failure_skips_pr(self, admin_db):
        """When commit fails, PR step is skipped."""
        preview_result = await self._drive_to_preview(admin_db, "sess-cmfail", name="CmBot")
        assert "Agent Preview" in preview_result

        gps_patcher, mock_gps = self._gps_mock()
        mock_gps.commit_files = AsyncMock(return_value=None)
        try:
            result = await handle_agent_command(
                message="create",
                session_key="sess-cmfail",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "In Progress", "Done"],
            )
        finally:
            gps_patcher.stop()

        assert "Agent Created" in result
        assert "file commit failed" in result.lower() or "commit_files returned None" in result

    async def test_add_issue_to_project_null_item_id(self, admin_db):
        """When add_issue_to_project returns None, step 8 reports failure."""
        preview_result = await self._drive_to_preview(admin_db, "sess-noitem", name="NoItemBot")
        assert "Agent Preview" in preview_result

        gps_patcher, mock_gps = self._gps_mock()
        mock_gps.add_issue_to_project = AsyncMock(return_value=None)
        try:
            result = await handle_agent_command(
                message="create",
                session_key="sess-noitem",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "In Progress", "Done"],
            )
        finally:
            gps_patcher.stop()

        assert "Agent Created" in result
        assert "missing project item id" in result.lower()

    async def test_move_issue_exception(self, admin_db):
        """When move issue to In Review raises, error is reported."""
        preview_result = await self._drive_to_preview(admin_db, "sess-mvfail", name="MvBot")
        assert "Agent Preview" in preview_result

        gps_patcher, mock_gps = self._gps_mock()
        mock_gps.update_item_status_by_name = AsyncMock(side_effect=RuntimeError("Move failed"))
        try:
            result = await handle_agent_command(
                message="create",
                session_key="sess-mvfail",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "In Progress", "Done"],
            )
        finally:
            gps_patcher.stop()

        assert "Agent Created" in result
        assert "Move failed" in result

    async def test_new_column_pipeline(self, admin_db):
        """Pipeline with a new column shows 'Create project column' step."""
        with patch("src.services.agent_creator.get_ai_agent_service") as mock_ai:
            svc = AsyncMock()
            svc.generate_agent_config.return_value = {
                "name": "NewColBot",
                "description": "A bot",
                "system_prompt": "Prompt.",
                "tools": [],
            }
            mock_ai.return_value = svc
            await handle_agent_command(
                message="#agent Build a bot #brand-new-status",
                session_key="sess-newcol",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "Done"],
            )

        state = get_active_session("sess-newcol")
        assert state is not None
        assert state.is_new_column is True

        gps_patcher, _mock_gps = self._gps_mock()
        try:
            result = await handle_agent_command(
                message="create",
                session_key="sess-newcol",
                project_id="PVT_1",
                owner="o",
                repo="r",
                github_user_id="12345",
                access_token="tok",
                db=admin_db,
                project_columns=["Todo", "Done"],
            )
        finally:
            gps_patcher.stop()

        assert "Agent Created" in result
        assert "Create project column" in result

    async def test_missing_context_returns_error(self, admin_db):
        """Pipeline with missing owner/repo returns error."""
        from src.services.agent_creator import _agent_sessions

        state = AgentCreationState(
            session_id="sess-nocontext",
            github_user_id="12345",
            project_id=None,
            owner=None,
            repo=None,
            raw_description="A bot",
        )
        state.step = CreationStep.PREVIEW
        state.preview = AgentPreview(
            name="Bot",
            slug="bot",
            description="A bot",
            system_prompt="Prompt.",
            status_column="Done",
            tools=[],
        )
        _agent_sessions["sess-nocontext"] = state

        result = await handle_agent_command(
            message="create",
            session_key="sess-nocontext",
            project_id=None,
            owner=None,
            repo=None,
            github_user_id="12345",
            access_token="tok",
            db=admin_db,
        )
        assert "Error" in result or "Missing" in result
        assert get_active_session("sess-nocontext") is None


# ═══════════════════════════════════════════════════════════════════════
# _update_pipeline_mappings
# ═══════════════════════════════════════════════════════════════════════


class TestUpdatePipelineMappings:
    """Tests for the _update_pipeline_mappings helper."""

    @pytest.fixture
    async def admin_db(self, mock_db: aiosqlite.Connection):
        await mock_db.execute(
            "INSERT OR IGNORE INTO global_settings (id, updated_at) VALUES (1, '2024-01-01T00:00:00Z')",
        )
        await mock_db.execute(
            "UPDATE global_settings SET admin_github_user_id = ? WHERE id = 1",
            ("12345",),
        )
        await mock_db.commit()
        return mock_db

    async def test_creates_new_mapping(self, admin_db):
        """Adds a slug to a new status column in pipeline mappings."""
        from src.services.agent_creator import _update_pipeline_mappings

        # Insert project_settings row
        await admin_db.execute(
            "INSERT OR IGNORE INTO project_settings (github_user_id, project_id, updated_at) "
            "VALUES (?, ?, ?)",
            ("12345", "PVT_1", "2024-01-01T00:00:00Z"),
        )
        await admin_db.commit()

        await _update_pipeline_mappings(
            db=admin_db,
            project_id="PVT_1",
            status_column="In Review",
            agent_slug="test-bot",
        )

        import json

        cursor = await admin_db.execute(
            "SELECT agent_pipeline_mappings FROM project_settings WHERE project_id = ?",
            ("PVT_1",),
        )
        row = await cursor.fetchone()
        mappings = json.loads(row[0])
        assert "In Review" in mappings
        assert "test-bot" in mappings["In Review"]

    async def test_appends_to_existing_mapping(self, admin_db):
        """Appends a slug to an existing status column mapping."""
        import json

        from src.services.agent_creator import _update_pipeline_mappings

        await admin_db.execute(
            "INSERT OR IGNORE INTO project_settings (github_user_id, project_id, agent_pipeline_mappings, updated_at) "
            "VALUES (?, ?, ?, ?)",
            ("12345", "PVT_2", json.dumps({"In Review": ["old-bot"]}), "2024-01-01T00:00:00Z"),
        )
        await admin_db.commit()

        await _update_pipeline_mappings(
            db=admin_db,
            project_id="PVT_2",
            status_column="In Review",
            agent_slug="new-bot",
        )

        cursor = await admin_db.execute(
            "SELECT agent_pipeline_mappings FROM project_settings WHERE project_id = ?",
            ("PVT_2",),
        )
        row = await cursor.fetchone()
        mappings = json.loads(row[0])
        assert mappings["In Review"] == ["old-bot", "new-bot"]

    async def test_no_duplicate_slugs(self, admin_db):
        """Adding the same slug twice doesn't create duplicates."""
        import json

        from src.services.agent_creator import _update_pipeline_mappings

        await admin_db.execute(
            "INSERT OR IGNORE INTO project_settings (github_user_id, project_id, agent_pipeline_mappings, updated_at) "
            "VALUES (?, ?, ?, ?)",
            ("12345", "PVT_3", json.dumps({"Done": ["my-bot"]}), "2024-01-01T00:00:00Z"),
        )
        await admin_db.commit()

        await _update_pipeline_mappings(
            db=admin_db,
            project_id="PVT_3",
            status_column="Done",
            agent_slug="my-bot",
        )

        cursor = await admin_db.execute(
            "SELECT agent_pipeline_mappings FROM project_settings WHERE project_id = ?",
            ("PVT_3",),
        )
        row = await cursor.fetchone()
        mappings = json.loads(row[0])
        assert mappings["Done"] == ["my-bot"]

    async def test_no_project_settings_row_does_not_crash(self, admin_db):
        """When no project_settings row exists, function doesn't crash."""
        from src.services.agent_creator import _update_pipeline_mappings

        # Should not raise — logs a warning instead
        await _update_pipeline_mappings(
            db=admin_db,
            project_id="PVT_NONEXISTENT",
            status_column="Done",
            agent_slug="test-bot",
        )


# ═══════════════════════════════════════════════════════════════════════
# _apply_edit — edge case: no preview
# ═══════════════════════════════════════════════════════════════════════


class TestApplyEditNoPreview:
    """Tests for _apply_edit when there's no preview."""

    @pytest.fixture
    async def admin_db(self, mock_db: aiosqlite.Connection):
        await mock_db.execute(
            "INSERT OR IGNORE INTO global_settings (id, updated_at) VALUES (1, '2024-01-01T00:00:00Z')",
        )
        await mock_db.execute(
            "UPDATE global_settings SET admin_github_user_id = ? WHERE id = 1",
            ("12345",),
        )
        await mock_db.commit()
        return mock_db

    @pytest.fixture(autouse=True)
    def _clear_sessions(self):
        from src.services.agent_creator import _agent_sessions

        _agent_sessions.clear()
        yield
        _agent_sessions.clear()

    async def test_edit_without_preview_returns_start_over(self, admin_db):
        """Editing with no preview returns 'start over' message."""
        from src.services.agent_creator import _agent_sessions

        state = AgentCreationState(
            session_id="sess-noprev",
            github_user_id="12345",
            project_id="PVT_1",
            owner="o",
            repo="r",
        )
        state.step = CreationStep.PREVIEW
        state.preview = None  # No preview set
        _agent_sessions["sess-noprev"] = state

        result = await handle_agent_command(
            message="change name to Foo",
            session_key="sess-noprev",
            project_id="PVT_1",
            owner="o",
            repo="r",
            github_user_id="12345",
            access_token="tok",
            db=admin_db,
        )
        assert "start over" in result.lower() or "No preview" in result


# ═══════════════════════════════════════════════════════════════════════
# _resolve_owner_repo
# ═══════════════════════════════════════════════════════════════════════


class TestResolveOwnerRepo:
    """Tests for the _resolve_owner_repo helper."""

    async def test_delegates_to_resolve_repository(self):
        """_resolve_owner_repo calls resolve_repository utility."""
        from src.services.agent_creator import _resolve_owner_repo

        with patch("src.utils.resolve_repository", new_callable=AsyncMock) as mock_rr:
            mock_rr.return_value = ("myowner", "myrepo")
            owner, repo = await _resolve_owner_repo("tok123", "PVT_1")
        assert owner == "myowner"
        assert repo == "myrepo"
        mock_rr.assert_awaited_once_with("tok123", "PVT_1")


# ═══════════════════════════════════════════════════════════════════════
# is_admin_user — no global_settings row
# ═══════════════════════════════════════════════════════════════════════


class TestIsAdminNoRow:
    """Tests for is_admin_user when no global_settings row exists."""

    async def test_no_row_returns_false(self, mock_db: aiosqlite.Connection):
        """When global_settings has no rows, is_admin_user returns False."""
        # Don't seed any global_settings row
        result = await is_admin_user(mock_db, "12345")
        assert result is False


# ═══════════════════════════════════════════════════════════════════════
# _handle_new_command parse error
# ═══════════════════════════════════════════════════════════════════════


class TestHandleNewCommandParseError:
    """Tests for _handle_new_command parse failure path."""

    @pytest.fixture
    async def admin_db(self, mock_db: aiosqlite.Connection):
        await mock_db.execute(
            "INSERT OR IGNORE INTO global_settings (id, updated_at) VALUES (1, '2024-01-01T00:00:00Z')",
        )
        await mock_db.execute(
            "UPDATE global_settings SET admin_github_user_id = ? WHERE id = 1",
            ("12345",),
        )
        await mock_db.commit()
        return mock_db

    async def test_empty_command_returns_usage(self, admin_db):
        """An empty #agent command returns usage instructions."""
        result = await handle_agent_command(
            message="#agent",
            session_key="sess-parse-err",
            project_id="PVT_1",
            owner="o",
            repo="r",
            github_user_id="12345",
            access_token="tok",
            db=admin_db,
        )
        assert "Error" in result
        assert "Usage" in result or "usage" in result.lower()
        assert get_active_session("sess-parse-err") is None


# ═══════════════════════════════════════════════════════════════════════
# _normalize_status
# ═══════════════════════════════════════════════════════════════════════


class TestNormalizeStatus:
    """Tests for the _normalize_status helper."""

    def test_strips_hyphens_underscores_spaces(self):
        from src.services.agent_creator import _normalize_status

        assert _normalize_status("In-Progress") == "inprogress"
        assert _normalize_status("in_review") == "inreview"
        assert _normalize_status("Code Review") == "codereview"

    def test_lowercases(self):
        from src.services.agent_creator import _normalize_status

        assert _normalize_status("TODO") == "todo"

    def test_empty_string(self):
        from src.services.agent_creator import _normalize_status

        assert _normalize_status("") == ""
