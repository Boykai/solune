"""Tests for task_generation prompt module.

Covers:
- create_task_generation_prompt() message structure and variable substitution
- create_status_change_prompt() message structure
- Edge cases: empty inputs, special characters, long lists
"""

from __future__ import annotations

from src.prompts.task_generation import (
    STATUS_CHANGE_SYSTEM_PROMPT,
    TASK_GENERATION_SYSTEM_PROMPT,
    TASK_GENERATION_USER_PROMPT_TEMPLATE,
    create_status_change_prompt,
    create_task_generation_prompt,
)


class TestTaskGenerationSystemPrompt:
    """Verify the system prompt constants have expected structure."""

    def test_task_system_prompt_is_non_empty(self):
        assert isinstance(TASK_GENERATION_SYSTEM_PROMPT, str)
        assert len(TASK_GENERATION_SYSTEM_PROMPT) > 50

    def test_task_system_prompt_references_json(self):
        assert "JSON" in TASK_GENERATION_SYSTEM_PROMPT

    def test_status_change_prompt_is_non_empty(self):
        assert isinstance(STATUS_CHANGE_SYSTEM_PROMPT, str)
        assert len(STATUS_CHANGE_SYSTEM_PROMPT) > 50

    def test_user_prompt_template_has_placeholders(self):
        assert "{user_input}" in TASK_GENERATION_USER_PROMPT_TEMPLATE
        assert "{project_name}" in TASK_GENERATION_USER_PROMPT_TEMPLATE


class TestCreateTaskGenerationPrompt:
    """Verify create_task_generation_prompt() returns correct message list."""

    def test_returns_two_messages(self):
        msgs = create_task_generation_prompt("Add login page", "My Project")
        assert len(msgs) == 2

    def test_first_message_is_system_role(self):
        msgs = create_task_generation_prompt("Fix bug", "Proj")
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == TASK_GENERATION_SYSTEM_PROMPT

    def test_user_message_contains_input_and_project(self):
        msgs = create_task_generation_prompt("Implement caching", "Acme Backend")
        user_content = msgs[1]["content"]
        assert "Implement caching" in user_content
        assert "Acme Backend" in user_content

    def test_empty_user_input(self):
        msgs = create_task_generation_prompt("", "Proj")
        assert len(msgs) == 2
        assert msgs[1]["role"] == "user"

    def test_special_characters_in_input(self):
        msgs = create_task_generation_prompt("Fix <br> & 'quotes'", "Proj")
        assert "<br>" in msgs[1]["content"]
        assert "'quotes'" in msgs[1]["content"]


class TestCreateStatusChangePrompt:
    """Verify create_status_change_prompt() returns correct messages."""

    def test_returns_two_messages(self):
        msgs = create_status_change_prompt(
            "Move login to done",
            available_tasks=["Fix login", "Add tests"],
            available_statuses=["Todo", "Done"],
        )
        assert len(msgs) == 2

    def test_first_message_is_system_role(self):
        msgs = create_status_change_prompt("test", ["task1"], ["Todo"])
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == STATUS_CHANGE_SYSTEM_PROMPT

    def test_user_message_contains_tasks(self):
        tasks = ["Fix auth bug", "Add unit tests", "Update docs"]
        msgs = create_status_change_prompt("Move auth to done", tasks, ["Done"])
        user_content = msgs[1]["content"]
        assert "Fix auth bug" in user_content
        assert "Add unit tests" in user_content

    def test_user_message_contains_statuses(self):
        msgs = create_status_change_prompt("test", ["task1"], ["Todo", "In Progress", "Done"])
        user_content = msgs[1]["content"]
        assert "Todo" in user_content
        assert "In Progress" in user_content
        assert "Done" in user_content

    def test_empty_tasks_list(self):
        msgs = create_status_change_prompt("test", [], ["Todo"])
        assert len(msgs) == 2

    def test_long_tasks_list_truncates_to_20(self):
        tasks = [f"Task {i}" for i in range(50)]
        msgs = create_status_change_prompt("test", tasks, ["Todo"])
        user_content = msgs[1]["content"]
        # Only first 20 tasks should appear
        assert "Task 0" in user_content
        assert "Task 19" in user_content
        assert "Task 20" not in user_content
