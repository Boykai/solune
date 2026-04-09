"""Tests for issue_generation prompt module.

Covers:
- create_issue_generation_prompt() message structure and variable substitution
- create_feature_request_detection_prompt() message structure
- Edge cases: empty inputs, metadata handling
"""

from __future__ import annotations

from src.prompts.issue_generation import (
    FEATURE_REQUEST_DETECTION_PROMPT,
    ISSUE_GENERATION_SYSTEM_PROMPT,
    create_feature_request_detection_prompt,
    create_issue_generation_prompt,
)


class TestIssueGenerationSystemPrompt:
    """Verify the system prompt constant has expected structure."""

    def test_is_non_empty_string(self):
        assert isinstance(ISSUE_GENERATION_SYSTEM_PROMPT, str)
        assert len(ISSUE_GENERATION_SYSTEM_PROMPT) > 50

    def test_references_json_output(self):
        assert "JSON" in ISSUE_GENERATION_SYSTEM_PROMPT or "json" in ISSUE_GENERATION_SYSTEM_PROMPT


class TestCreateIssueGenerationPrompt:
    """Verify create_issue_generation_prompt() returns correct message list."""

    def test_returns_two_messages(self):
        msgs = create_issue_generation_prompt("Add login page", "My Project")
        assert len(msgs) == 2

    def test_first_message_is_system_role(self):
        msgs = create_issue_generation_prompt("Add login page", "My Project")
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == ISSUE_GENERATION_SYSTEM_PROMPT

    def test_user_message_contains_input(self):
        msgs = create_issue_generation_prompt("Add dark mode toggle", "Acme")
        user_content = msgs[1]["content"]
        assert "Add dark mode toggle" in user_content
        assert "Acme" in user_content

    def test_user_message_contains_dates(self):
        msgs = create_issue_generation_prompt("Feature X", "Proj")
        user_content = msgs[1]["content"]
        # Should contain date strings in YYYY-MM-DD format
        import re

        assert re.search(r"\d{4}-\d{2}-\d{2}", user_content)

    def test_metadata_context_includes_labels(self):
        metadata = {"labels": [{"name": "bug"}, {"name": "enhancement"}]}
        msgs = create_issue_generation_prompt("Fix login", "Proj", metadata_context=metadata)
        user_content = msgs[1]["content"]
        assert "bug" in user_content
        assert "enhancement" in user_content

    def test_metadata_context_includes_branches(self):
        metadata = {"branches": [{"name": "main"}, {"name": "develop"}]}
        msgs = create_issue_generation_prompt("Add feature", "Proj", metadata_context=metadata)
        user_content = msgs[1]["content"]
        assert "main" in user_content
        assert "develop" in user_content

    def test_metadata_context_includes_milestones(self):
        metadata = {"milestones": [{"title": "v2.0"}, {"title": "v3.0"}]}
        msgs = create_issue_generation_prompt("Plan release", "Proj", metadata_context=metadata)
        user_content = msgs[1]["content"]
        assert "v2.0" in user_content

    def test_metadata_context_includes_collaborators(self):
        metadata = {"collaborators": [{"login": "alice"}, {"login": "bob"}]}
        msgs = create_issue_generation_prompt("Assign work", "Proj", metadata_context=metadata)
        user_content = msgs[1]["content"]
        assert "alice" in user_content
        assert "bob" in user_content

    def test_empty_user_input(self):
        msgs = create_issue_generation_prompt("", "Proj")
        assert len(msgs) == 2
        assert msgs[1]["role"] == "user"

    def test_no_metadata_context(self):
        msgs = create_issue_generation_prompt("Test", "Proj", metadata_context=None)
        assert len(msgs) == 2

    def test_metadata_with_string_labels(self):
        """Labels can be plain strings (not dicts)."""
        metadata = {"labels": ["bug", "enhancement"]}
        msgs = create_issue_generation_prompt("Fix it", "Proj", metadata_context=metadata)
        user_content = msgs[1]["content"]
        assert "bug" in user_content


class TestCreateFeatureRequestDetectionPrompt:
    """Verify create_feature_request_detection_prompt() returns correct messages."""

    def test_returns_two_messages(self):
        msgs = create_feature_request_detection_prompt("I want a dark mode")
        assert len(msgs) == 2

    def test_first_message_is_system_role(self):
        msgs = create_feature_request_detection_prompt("test input")
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == FEATURE_REQUEST_DETECTION_PROMPT

    def test_user_message_contains_input(self):
        msgs = create_feature_request_detection_prompt("Add export to CSV")
        assert "Add export to CSV" in msgs[1]["content"]

    def test_empty_input(self):
        msgs = create_feature_request_detection_prompt("")
        assert len(msgs) == 2
        assert msgs[1]["role"] == "user"
