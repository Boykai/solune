"""Unit tests for build_plan_instructions().

Covers:
- Default instructions always included
- Project context injection (project_name, repo, project_id, statuses)
- Partial context (some fields None)
"""

from src.prompts.plan_instructions import PLAN_SYSTEM_INSTRUCTIONS, build_plan_instructions


class TestBuildPlanInstructions:
    """build_plan_instructions output composition."""

    def test_always_includes_system_instructions(self):
        result = build_plan_instructions()
        assert PLAN_SYSTEM_INSTRUCTIONS in result

    def test_includes_project_name(self):
        result = build_plan_instructions(project_name="My App")
        assert "**Project**: My App" in result

    def test_includes_repository(self):
        result = build_plan_instructions(repo_owner="octocat", repo_name="hello")
        assert "**Repository**: octocat/hello" in result

    def test_includes_project_id(self):
        result = build_plan_instructions(project_id="PVT_abc123")
        assert "**Project ID**: PVT_abc123" in result

    def test_includes_statuses(self):
        result = build_plan_instructions(available_statuses=["Todo", "In Progress", "Done"])
        assert "**Available Statuses**: Todo, In Progress, Done" in result

    def test_no_context_when_all_none(self):
        result = build_plan_instructions()
        assert "**Project**:" not in result
        assert "**Repository**:" not in result
        assert "**Project ID**:" not in result
        assert "**Available Statuses**:" not in result

    def test_partial_context(self):
        result = build_plan_instructions(project_name="App", repo_owner="o", repo_name="r")
        assert "**Project**: App" in result
        assert "**Repository**: o/r" in result
        assert "**Project ID**:" not in result

    def test_repo_requires_both_owner_and_name(self):
        """Repository line should only appear when both owner and name are present."""
        result_owner_only = build_plan_instructions(repo_owner="o")
        result_name_only = build_plan_instructions(repo_name="r")
        assert "**Repository**:" not in result_owner_only
        assert "**Repository**:" not in result_name_only

    def test_full_context(self):
        result = build_plan_instructions(
            project_name="My App",
            project_id="PVT_abc",
            repo_owner="octocat",
            repo_name="hello",
            available_statuses=["Todo", "Done"],
        )
        assert "**Project**: My App" in result
        assert "**Repository**: octocat/hello" in result
        assert "**Project ID**: PVT_abc" in result
        assert "**Available Statuses**: Todo, Done" in result
