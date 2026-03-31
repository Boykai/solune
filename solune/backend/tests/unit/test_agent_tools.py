"""Tests for agent function tools (src/services/agent_tools.py).

Covers all @tool-decorated functions with mocked FunctionInvocationContext.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.agent_tools import (
    DIFFICULTY_PRESET_MAP,
    ToolResult,
    _identify_target_task,
    analyze_transcript,
    ask_clarifying_question,
    assess_difficulty,
    create_issue_recommendation,
    create_project_issue,
    create_task_proposal,
    get_pipeline_list,
    get_project_context,
    launch_pipeline,
    load_mcp_tools,
    register_tools,
    select_pipeline_preset,
    update_task_status,
)


def _make_context(**kwargs) -> MagicMock:
    """Create a mock FunctionInvocationContext with session state."""
    ctx = MagicMock()
    ctx.session.state = dict(kwargs)
    return ctx


# ── create_task_proposal ────────────────────────────────────────────────


class TestCreateTaskProposal:
    async def test_returns_task_create_action(self):
        ctx = _make_context()
        result: ToolResult = await create_task_proposal(
            ctx, title="Fix login bug", description="Fix the login flow"
        )
        assert result["action_type"] == "task_create"
        assert result["action_data"]["proposed_title"] == "Fix login bug"
        assert result["action_data"]["proposed_description"] == "Fix the login flow"
        assert "confirm" in result["content"].lower()

    async def test_truncates_long_title(self):
        ctx = _make_context()
        long_title = "A" * 300
        result = await create_task_proposal(ctx, title=long_title, description="desc")
        assert len(result["action_data"]["proposed_title"]) == 100

    async def test_truncates_long_description(self):
        ctx = _make_context()
        long_desc = "B" * 70000
        result = await create_task_proposal(ctx, title="T", description=long_desc)
        assert len(result["action_data"]["proposed_description"]) <= 65535


# ── create_issue_recommendation ─────────────────────────────────────────


class TestCreateIssueRecommendation:
    async def test_returns_issue_create_action(self):
        ctx = _make_context()
        result = await create_issue_recommendation(
            ctx,
            title="Add dark mode",
            user_story="As a user I want dark mode so I can reduce eye strain",
            ui_ux_description="Toggle in settings",
            functional_requirements=["Must toggle theme", "Must persist preference"],
            technical_notes="Use CSS custom properties",
        )
        assert result["action_type"] == "issue_create"
        assert result["action_data"]["proposed_title"] == "Add dark mode"
        assert result["action_data"]["user_story"].startswith("As a user")
        assert len(result["action_data"]["functional_requirements"]) == 2
        assert "Confirm" in result["content"]

    async def test_truncates_long_title(self):
        ctx = _make_context()
        result = await create_issue_recommendation(
            ctx,
            title="X" * 300,
            user_story="story",
            ui_ux_description="desc",
            functional_requirements=["req"],
        )
        assert len(result["action_data"]["proposed_title"]) <= 256

    async def test_optional_technical_notes(self):
        ctx = _make_context()
        result = await create_issue_recommendation(
            ctx,
            title="Title",
            user_story="story",
            ui_ux_description="desc",
            functional_requirements=["req"],
        )
        assert result["action_data"]["technical_notes"] == ""


# ── update_task_status ──────────────────────────────────────────────────


class TestUpdateTaskStatus:
    async def test_found_task_returns_status_update(self):
        task = MagicMock()
        task.title = "Fix login bug"
        task.status = "In Progress"
        task.github_item_id = "PVTI_1"

        ctx = _make_context(available_tasks=[task])
        result = await update_task_status(ctx, task_reference="Fix login bug", target_status="Done")
        assert result["action_type"] == "status_update"
        assert result["action_data"]["task_title"] == "Fix login bug"
        assert result["action_data"]["target_status"] == "Done"

    async def test_task_not_found_returns_none_action(self):
        ctx = _make_context(available_tasks=[])
        result = await update_task_status(ctx, task_reference="nonexistent", target_status="Done")
        assert result["action_type"] is None
        assert "couldn't find" in result["content"].lower()


# ── analyze_transcript ──────────────────────────────────────────────────


class TestAnalyzeTranscript:
    async def test_returns_issue_create_action(self):
        ctx = _make_context()
        result = await analyze_transcript(
            ctx, transcript_content="Speaker 1: We need a login feature\nSpeaker 2: Agreed"
        )
        assert result["action_type"] == "issue_create"
        assert "transcript" in result["action_data"]["source"]

    async def test_truncates_long_transcript_in_data(self):
        ctx = _make_context()
        long_transcript = "X" * 1000
        result = await analyze_transcript(ctx, transcript_content=long_transcript)
        assert len(result["action_data"]["transcript_content"]) <= 500


# ── ask_clarifying_question ─────────────────────────────────────────────


class TestAskClarifyingQuestion:
    async def test_returns_question_with_no_action(self):
        ctx = _make_context()
        result = await ask_clarifying_question(ctx, question="What specific feature do you want?")
        assert result["action_type"] is None
        assert result["action_data"] is None
        assert "What specific feature" in result["content"]


# ── get_project_context ─────────────────────────────────────────────────


class TestGetProjectContext:
    async def test_returns_project_info(self):
        ctx = _make_context(project_name="My Project", project_id="PVT_123")
        result = await get_project_context(ctx)
        assert result["action_type"] is None
        assert "My Project" in result["content"]


# ── get_pipeline_list ───────────────────────────────────────────────────


class TestGetPipelineList:
    async def test_returns_statuses(self):
        ctx = _make_context(available_statuses=["Todo", "In Progress", "Done"])
        result = await get_pipeline_list(ctx)
        assert result["action_type"] is None
        assert "Todo" in result["content"]
        assert "In Progress" in result["content"]

    async def test_empty_statuses(self):
        ctx = _make_context(available_statuses=[])
        result = await get_pipeline_list(ctx)
        assert "No statuses" in result["content"]


# ── _identify_target_task ────────────────────────────────────────────────


class TestIdentifyTargetTask:
    def _make_task(self, title: str, **kwargs) -> MagicMock:
        task = MagicMock()
        task.title = title
        for k, v in kwargs.items():
            setattr(task, k, v)
        return task

    def test_exact_match(self):
        task = self._make_task("Fix login bug")
        result = _identify_target_task("Fix login bug", [task])
        assert result is task

    def test_exact_match_case_insensitive(self):
        task = self._make_task("Fix Login Bug")
        result = _identify_target_task("fix login bug", [task])
        assert result is task

    def test_partial_match(self):
        task = self._make_task("Fix login bug in auth module")
        result = _identify_target_task("login bug", [task])
        assert result is task

    def test_fuzzy_match_by_word_overlap(self):
        task1 = self._make_task("Update CI pipeline config")
        task2 = self._make_task("Fix login authentication")
        result = _identify_target_task("login auth fix", [task1, task2])
        assert result is task2

    def test_returns_none_for_empty_reference(self):
        task = self._make_task("Fix bug")
        assert _identify_target_task("", [task]) is None

    def test_returns_none_for_empty_tasks(self):
        assert _identify_target_task("Fix bug", []) is None

    def test_returns_none_for_no_match(self):
        task = self._make_task("Unrelated task")
        result = _identify_target_task("xyz123abc", [task])
        assert result is None


# ── register_tools ──────────────────────────────────────────────────────


class TestRegisterTools:
    def test_returns_all_tools(self):
        tools = register_tools()
        assert len(tools) == 11
        # Verify all expected tools are present (FunctionTool objects)
        tool_names = [t.name for t in tools]
        assert "create_task_proposal" in tool_names
        assert "create_issue_recommendation" in tool_names
        assert "update_task_status" in tool_names
        assert "analyze_transcript" in tool_names
        assert "ask_clarifying_question" in tool_names
        assert "get_project_context" in tool_names
        assert "get_pipeline_list" in tool_names
        assert "assess_difficulty" in tool_names
        assert "select_pipeline_preset" in tool_names
        assert "create_project_issue" in tool_names
        assert "launch_pipeline" in tool_names


# ── assess_difficulty ───────────────────────────────────────────────────


class TestAssessDifficulty:
    async def test_returns_valid_tool_result_with_no_action(self):
        ctx = _make_context()
        result: ToolResult = await assess_difficulty(
            ctx, difficulty="M", reasoning="Multi-file changes needed"
        )
        assert result["action_type"] is None
        assert result["action_data"] is None
        assert "M" in result["content"]
        assert "medium" in result["content"]

    async def test_sets_session_state(self):
        ctx = _make_context()
        await assess_difficulty(ctx, difficulty="L", reasoning="Complex refactoring")
        assert ctx.session.state["assessed_difficulty"] == "L"

    @pytest.mark.parametrize(
        "difficulty,expected_preset",
        [
            ("XS", "github-copilot"),
            ("S", "easy"),
            ("M", "medium"),
            ("L", "hard"),
            ("XL", "expert"),
        ],
    )
    async def test_all_difficulty_levels(self, difficulty, expected_preset):
        ctx = _make_context()
        result = await assess_difficulty(ctx, difficulty=difficulty, reasoning="test")
        assert ctx.session.state["assessed_difficulty"] == difficulty
        assert expected_preset in result["content"]

    async def test_case_insensitive_difficulty(self):
        ctx = _make_context()
        result = await assess_difficulty(ctx, difficulty="xl", reasoning="test")
        assert ctx.session.state["assessed_difficulty"] == "XL"
        assert "expert" in result["content"]

    async def test_unknown_difficulty_falls_back_to_medium(self):
        ctx = _make_context()
        result = await assess_difficulty(ctx, difficulty="UNKNOWN", reasoning="test")
        assert "medium" in result["content"]


# ── select_pipeline_preset ──────────────────────────────────────────────


class TestSelectPipelinePreset:
    async def test_correct_preset_selected_for_each_difficulty(self):
        for difficulty, expected_id in DIFFICULTY_PRESET_MAP.items():
            ctx = _make_context()
            result = await select_pipeline_preset(
                ctx, difficulty=difficulty, project_name="Test Project"
            )
            assert ctx.session.state["selected_preset_id"] == expected_id
            assert expected_id in result["content"]

    async def test_unknown_difficulty_falls_back_to_medium(self):
        ctx = _make_context()
        result = await select_pipeline_preset(
            ctx, difficulty="UNKNOWN", project_name="Test Project"
        )
        assert ctx.session.state["selected_preset_id"] == "medium"
        assert "medium" in result["content"].lower()

    async def test_preset_details_in_result_content(self):
        ctx = _make_context()
        result = await select_pipeline_preset(ctx, difficulty="M", project_name="My App")
        # Should contain stages and agents info
        assert "My App" in result["content"]
        assert "medium" in result["content"].lower()

    async def test_sets_selected_preset_id_in_session(self):
        ctx = _make_context()
        await select_pipeline_preset(ctx, difficulty="XL", project_name="Big Project")
        assert ctx.session.state["selected_preset_id"] == "expert"


# ── create_project_issue ────────────────────────────────────────────────


class TestCreateProjectIssue:
    @patch("src.services.agent_tools.get_settings")
    async def test_auto_create_disabled_returns_proposal(self, mock_settings):
        mock_settings.return_value = MagicMock(chat_auto_create_enabled=False)
        ctx = _make_context(selected_preset_id="medium")
        result = await create_project_issue(
            ctx, title="Stock Tracker", body="Build a stock tracking app"
        )
        assert result["action_type"] is None
        assert "proposal" in result["content"].lower()
        assert "CHAT_AUTO_CREATE_ENABLED" in result["content"]

    @patch("src.services.agent_tools.get_settings")
    async def test_auto_create_enabled_calls_github_api(self, mock_settings):
        mock_settings.return_value = MagicMock(
            chat_auto_create_enabled=True,
            default_repo_owner="testowner",
            default_repo_name="testrepo",
        )
        mock_service = AsyncMock()
        mock_service.create_issue.return_value = {
            "number": 42,
            "html_url": "https://github.com/testowner/testrepo/issues/42",
        }

        ctx = _make_context(
            github_token="test-token",
            project_name="My Project",
            selected_preset_id="easy",
        )

        with patch(
            "src.services.github_projects.service.GitHubProjectsService",
            return_value=mock_service,
        ), patch(
            "src.services.agent_tools.classify_labels",
            new_callable=AsyncMock,
            return_value=["ai-generated", "feature", "backend"],
        ):
            result = await create_project_issue(
                ctx, title="Stock Tracker", body="Build a stock tracking app"
            )

        assert result["action_type"] == "issue_create"
        assert result["action_data"]["issue_number"] == 42
        assert result["action_data"]["preset_id"] == "easy"
        _, kwargs = mock_service.create_issue.await_args
        assert kwargs["labels"] == ["ai-generated", "feature", "backend"]

    @patch("src.services.agent_tools.get_settings")
    async def test_explicit_labels_skip_auto_classification(self, mock_settings):
        mock_settings.return_value = MagicMock(
            chat_auto_create_enabled=True,
            default_repo_owner="testowner",
            default_repo_name="testrepo",
        )
        mock_service = AsyncMock()
        mock_service.create_issue.return_value = {
            "number": 42,
            "html_url": "https://github.com/testowner/testrepo/issues/42",
        }
        ctx = _make_context(github_token="test-token")

        with patch(
            "src.services.github_projects.service.GitHubProjectsService",
            return_value=mock_service,
        ), patch("src.services.agent_tools.classify_labels", new_callable=AsyncMock) as mock_classify:
            await create_project_issue(
                ctx,
                title="Stock Tracker",
                body="Build a stock tracking app",
                labels=["bug", "frontend"],
            )

        mock_classify.assert_not_awaited()
        _, kwargs = mock_service.create_issue.await_args
        assert kwargs["labels"] == ["bug", "frontend"]

    @patch("src.services.agent_tools.get_settings")
    async def test_auto_create_no_token_returns_error(self, mock_settings):
        mock_settings.return_value = MagicMock(
            chat_auto_create_enabled=True,
            default_repo_owner="owner",
            default_repo_name="repo",
        )
        ctx = _make_context(github_token=None)
        result = await create_project_issue(ctx, title="Test", body="Test body")
        assert result["action_type"] is None
        assert "authentication" in result["content"].lower()

    @patch("src.services.agent_tools.get_settings")
    async def test_auto_create_no_repo_returns_error(self, mock_settings):
        mock_settings.return_value = MagicMock(
            chat_auto_create_enabled=True,
            default_repo_owner=None,
            default_repo_name=None,
        )
        ctx = _make_context(github_token="test-token")
        result = await create_project_issue(ctx, title="Test", body="Test body")
        assert result["action_type"] is None
        assert "repository" in result["content"].lower()

    @patch("src.services.agent_tools.get_settings")
    async def test_handles_github_api_error_gracefully(self, mock_settings):
        mock_settings.return_value = MagicMock(
            chat_auto_create_enabled=True,
            default_repo_owner="owner",
            default_repo_name="repo",
        )
        ctx = _make_context(github_token="test-token", project_name="Proj")

        with patch(
            "src.services.github_projects.service.GitHubProjectsService",
        ) as mock_cls:
            mock_service = AsyncMock()
            mock_service.create_issue.side_effect = RuntimeError("API down")
            mock_cls.return_value = mock_service

            result = await create_project_issue(ctx, title="Test", body="Test body")

        assert result["action_type"] is None
        assert "failed" in result["content"].lower()


# ── launch_pipeline ─────────────────────────────────────────────────────


class TestLaunchPipeline:
    async def test_returns_pipeline_launch_action(self):
        ctx = _make_context(
            selected_preset_id="medium",
            project_id="PVT_123",
        )
        result = await launch_pipeline(ctx)
        assert result["action_type"] == "pipeline_launch"
        assert result["action_data"]["preset"] == "medium"
        assert isinstance(result["action_data"]["stages"], list)

    async def test_reads_preset_from_session_state(self):
        ctx = _make_context(
            selected_preset_id="expert",
            project_id="PVT_456",
        )
        result = await launch_pipeline(ctx)
        assert result["action_data"]["preset"] == "expert"

    async def test_uses_pipeline_id_from_argument(self):
        ctx = _make_context(selected_preset_id="easy", project_id="PVT_1")
        result = await launch_pipeline(ctx, pipeline_id="custom-pipeline-123")
        assert result["action_data"]["pipeline_id"] == "custom-pipeline-123"

    async def test_falls_back_to_session_pipeline_id(self):
        ctx = _make_context(
            selected_preset_id="easy",
            project_id="PVT_1",
            pipeline_id="session-pipeline",
        )
        result = await launch_pipeline(ctx)
        assert result["action_data"]["pipeline_id"] == "session-pipeline"


# ── load_mcp_tools ──────────────────────────────────────────────────────


class TestLoadMcpTools:
    def _mock_db_with_cursor(self, cursor):
        """Create a mock db where execute() returns an async context manager wrapping cursor.

        aiosqlite's Connection.execute() returns a _ContextManager that is both
        awaitable *and* an async-context-manager.  We replicate that by making
        execute a *non*-async callable that returns an object supporting
        ``__aenter__``/``__aexit__``.
        """
        mock_db = AsyncMock()
        ctx = AsyncMock()
        ctx.__aenter__.return_value = cursor
        ctx.__aexit__.return_value = False
        mock_db.execute = MagicMock(return_value=ctx)
        return mock_db

    async def test_returns_valid_config_dicts(self):
        mock_cursor = AsyncMock()
        mock_cursor.fetchall.return_value = [
            ("mcp-server-1", "https://example.com/mcp1", '{"key": "value"}'),
            ("mcp-server-2", "https://example.com/mcp2", "{}"),
        ]
        mock_db = self._mock_db_with_cursor(mock_cursor)

        result = await load_mcp_tools("PVT_123", mock_db)

        assert len(result) == 2
        assert "mcp-server-1" in result
        assert result["mcp-server-1"]["endpoint_url"] == "https://example.com/mcp1"
        assert result["mcp-server-1"]["config"] == {"key": "value"}
        assert "mcp-server-2" in result

    async def test_returns_empty_dict_when_no_tools_configured(self):
        mock_cursor = AsyncMock()
        mock_cursor.fetchall.return_value = []
        mock_db = self._mock_db_with_cursor(mock_cursor)

        result = await load_mcp_tools("PVT_123", mock_db)
        assert result == {}

    async def test_returns_empty_dict_on_database_error(self):
        mock_db = AsyncMock()
        mock_db.execute.side_effect = RuntimeError("DB connection lost")

        result = await load_mcp_tools("PVT_123", mock_db)
        assert result == {}

    async def test_returns_empty_dict_for_empty_project_id(self):
        mock_db = AsyncMock()
        result = await load_mcp_tools("", mock_db)
        assert result == {}

    async def test_handles_invalid_json_config(self):
        mock_cursor = AsyncMock()
        mock_cursor.fetchall.return_value = [
            ("mcp-server", "https://example.com/mcp", "not-valid-json"),
        ]
        mock_db = self._mock_db_with_cursor(mock_cursor)

        result = await load_mcp_tools("PVT_123", mock_db)
        assert len(result) == 1
        assert result["mcp-server"]["config"] == {}
