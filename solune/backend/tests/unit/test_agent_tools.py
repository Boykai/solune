"""Tests for agent function tools (src/services/agent_tools.py).

Covers all @tool-decorated functions with mocked FunctionInvocationContext.
"""

from unittest.mock import MagicMock

from src.services.agent_tools import (
    ToolResult,
    _identify_target_task,
    analyze_transcript,
    ask_clarifying_question,
    create_issue_recommendation,
    create_task_proposal,
    get_pipeline_list,
    get_project_context,
    register_tools,
    update_task_status,
)


def _make_context(**kwargs) -> MagicMock:
    """Create a mock FunctionInvocationContext with given kwargs."""
    ctx = MagicMock()
    ctx.kwargs = kwargs
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
        assert len(result["action_data"]["proposed_title"]) <= 256

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
        assert len(tools) == 7
        # Verify all expected tools are present (FunctionTool objects)
        tool_names = [t.name for t in tools]
        assert "create_task_proposal" in tool_names
        assert "create_issue_recommendation" in tool_names
        assert "update_task_status" in tool_names
        assert "analyze_transcript" in tool_names
        assert "ask_clarifying_question" in tool_names
        assert "get_project_context" in tool_names
        assert "get_pipeline_list" in tool_names
