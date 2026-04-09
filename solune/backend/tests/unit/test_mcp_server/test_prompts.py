"""Tests for MCP prompt templates (src/services/mcp_server/prompts.py).

Covers:
- register_prompts attaches three prompts to a FastMCP instance
- create-project prompt output with and without project_name
- pipeline-status prompt output with and without project_id
- daily-standup prompt output with default and custom days
"""

from unittest.mock import MagicMock

import pytest

from src.services.mcp_server.prompts import register_prompts


@pytest.fixture()
def _registered_prompts():
    """Register prompts on a mock FastMCP and capture decorated functions.

    Returns a dict mapping prompt name → async handler function.
    """
    captured: dict[str, object] = {}
    mock_mcp = MagicMock()

    def fake_prompt(name: str):
        def decorator(fn):
            captured[name] = fn
            return fn

        return decorator

    mock_mcp.prompt = fake_prompt
    register_prompts(mock_mcp)
    return captured


class TestRegisterPrompts:
    """Verify the registration itself."""

    def test_registers_three_prompts(self, _registered_prompts):
        assert set(_registered_prompts.keys()) == {
            "create-project",
            "pipeline-status",
            "daily-standup",
        }


class TestCreateProjectPrompt:
    """Tests for the create-project prompt handler."""

    async def test_without_project_name(self, _registered_prompts):
        handler = _registered_prompts["create-project"]
        result = await handler()
        assert "create a new project" in result
        assert "list_projects" in result

    async def test_with_project_name(self, _registered_prompts):
        handler = _registered_prompts["create-project"]
        result = await handler(project_name="MyApp")
        assert 'named "MyApp"' in result
        assert "list_projects" in result


class TestPipelineStatusPrompt:
    """Tests for the pipeline-status prompt handler."""

    async def test_without_project_id(self, _registered_prompts):
        handler = _registered_prompts["pipeline-status"]
        result = await handler()
        assert "all running pipelines across all my projects" in result
        assert "list_projects" in result

    async def test_with_project_id(self, _registered_prompts):
        handler = _registered_prompts["pipeline-status"]
        result = await handler(project_id="PVT_kwDOABC")
        assert "PVT_kwDOABC" in result
        assert "get_pipeline_states" in result
        assert "list_projects" not in result


class TestDailyStandupPrompt:
    """Tests for the daily-standup prompt handler."""

    async def test_default_one_day(self, _registered_prompts):
        handler = _registered_prompts["daily-standup"]
        result = await handler()
        assert "last 1 day(s)" in result
        assert "get_activity" in result

    async def test_custom_days(self, _registered_prompts):
        handler = _registered_prompts["daily-standup"]
        result = await handler(days=7)
        assert "last 7 day(s)" in result
        assert "get_board" in result
