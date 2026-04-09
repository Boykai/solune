"""Tests for agent_instructions prompt module.

Covers:
- AGENT_SYSTEM_INSTRUCTIONS constant structure
- build_system_instructions() with various inputs
- Edge cases: empty/None inputs, special characters
"""

from __future__ import annotations

from src.prompts.agent_instructions import (
    AGENT_SYSTEM_INSTRUCTIONS,
    build_system_instructions,
)


class TestAgentSystemInstructionsConstant:
    """Verify the AGENT_SYSTEM_INSTRUCTIONS constant has required content."""

    def test_contains_core_capabilities_section(self):
        assert "Core Capabilities" in AGENT_SYSTEM_INSTRUCTIONS

    def test_contains_decision_guidelines(self):
        assert "Decision Guidelines" in AGENT_SYSTEM_INSTRUCTIONS

    def test_contains_tool_references(self):
        """Agent instructions must reference the key tool functions."""
        assert "create_task_proposal" in AGENT_SYSTEM_INSTRUCTIONS
        assert "create_issue_recommendation" in AGENT_SYSTEM_INSTRUCTIONS
        assert "update_task_status" in AGENT_SYSTEM_INSTRUCTIONS

    def test_is_non_empty_string(self):
        assert isinstance(AGENT_SYSTEM_INSTRUCTIONS, str)
        assert len(AGENT_SYSTEM_INSTRUCTIONS) > 100


class TestBuildSystemInstructions:
    """Verify build_system_instructions() composes dynamic prompts correctly."""

    def test_returns_base_instructions_with_no_args(self):
        result = build_system_instructions()
        assert AGENT_SYSTEM_INSTRUCTIONS in result

    def test_includes_project_name_when_provided(self):
        result = build_system_instructions(project_name="My Project")
        assert "My Project" in result
        assert "Current Project Context" in result

    def test_includes_available_statuses_when_provided(self):
        statuses = ["Todo", "In Progress", "Done"]
        result = build_system_instructions(available_statuses=statuses)
        assert "Todo" in result
        assert "In Progress" in result
        assert "Done" in result
        assert "Available Statuses" in result

    def test_includes_both_project_and_statuses(self):
        result = build_system_instructions(
            project_name="Acme",
            available_statuses=["Backlog", "Active"],
        )
        assert "Acme" in result
        assert "Backlog" in result

    def test_none_project_name_omits_section(self):
        result = build_system_instructions(project_name=None)
        assert "Current Project Context" not in result

    def test_empty_statuses_omits_section(self):
        result = build_system_instructions(available_statuses=[])
        assert "Available Statuses" not in result

    def test_special_characters_in_project_name(self):
        result = build_system_instructions(project_name="Proj <script>alert('xss')</script>")
        assert "<script>" in result  # No sanitisation expected — this is a prompt, not HTML
