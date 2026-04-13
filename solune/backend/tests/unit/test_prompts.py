"""Unit tests for prompt construction functions.

Covers:
- _create_issue_generation_prompt()
- _create_feature_request_detection_prompt()
- _create_task_generation_prompt()
- _create_status_change_prompt()
"""

from datetime import timedelta

from src.constants import LABELS
from src.services.ai_utilities import (
    FEATURE_REQUEST_DETECTION_PROMPT,
    ISSUE_GENERATION_SYSTEM_PROMPT,
    STATUS_CHANGE_SYSTEM_PROMPT,
    TASK_GENERATION_SYSTEM_PROMPT,
    _create_feature_request_detection_prompt as create_feature_request_detection_prompt,
    _create_issue_generation_prompt as create_issue_generation_prompt,
    _create_status_change_prompt as create_status_change_prompt,
    _create_task_generation_prompt as create_task_generation_prompt,
)
from src.utils import utcnow

# =============================================================================
# Issue generation prompt
# =============================================================================


class TestCreateIssueGenerationPrompt:
    """Tests for create_issue_generation_prompt()."""

    def test_returns_two_messages(self):
        msgs = create_issue_generation_prompt("Add dark mode", "My Project")
        assert len(msgs) == 2

    def test_system_message_first(self):
        msgs = create_issue_generation_prompt("Add dark mode", "My Project")
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == ISSUE_GENERATION_SYSTEM_PROMPT

    def test_user_message_contains_input_and_project(self):
        msgs = create_issue_generation_prompt("Add dark mode", "My Project")
        user_content = msgs[1]["content"]
        assert "Add dark mode" in user_content
        assert "My Project" in user_content

    def test_user_message_contains_dates(self):
        msgs = create_issue_generation_prompt("feature", "proj")
        user_content = msgs[1]["content"]
        today = utcnow().strftime("%Y-%m-%d")
        assert today in user_content

    def test_user_message_contains_target_date(self):
        msgs = create_issue_generation_prompt("feature", "proj")
        user_content = msgs[1]["content"]
        tomorrow = (utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
        assert tomorrow in user_content

    def test_user_message_role(self):
        msgs = create_issue_generation_prompt("x", "y")
        assert msgs[1]["role"] == "user"

    # ── metadata_context tests ──────────────────────────────────────────

    def test_metadata_context_with_labels(self):
        ctx = {"labels": [{"name": "bug"}, {"name": "feature"}]}
        msgs = create_issue_generation_prompt("Add search", "Proj", metadata_context=ctx)
        content = msgs[1]["content"]
        assert '"bug"' in content
        assert '"feature"' in content
        assert "AVAILABLE LABELS" in content

    def test_metadata_context_with_string_labels(self):
        ctx = {"labels": ["bug", "feature"]}
        msgs = create_issue_generation_prompt("Add search", "Proj", metadata_context=ctx)
        content = msgs[1]["content"]
        assert '"bug"' in content
        assert '"feature"' in content

    def test_metadata_context_with_branches(self):
        ctx = {"branches": [{"name": "main"}, {"name": "develop"}]}
        msgs = create_issue_generation_prompt("Add search", "Proj", metadata_context=ctx)
        content = msgs[1]["content"]
        assert '"main"' in content
        assert '"develop"' in content
        assert "AVAILABLE BRANCHES" in content

    def test_metadata_context_with_milestones(self):
        ctx = {"milestones": [{"title": "v1.0"}, {"title": "v2.0"}]}
        msgs = create_issue_generation_prompt("Add search", "Proj", metadata_context=ctx)
        content = msgs[1]["content"]
        assert '"v1.0"' in content
        assert "AVAILABLE MILESTONES" in content

    def test_metadata_context_with_collaborators(self):
        ctx = {"collaborators": [{"login": "alice"}, {"login": "bob"}]}
        msgs = create_issue_generation_prompt("Add search", "Proj", metadata_context=ctx)
        content = msgs[1]["content"]
        assert '"alice"' in content
        assert '"bob"' in content
        assert "ASSIGNEE CANDIDATES" in content

    def test_metadata_context_all_fields(self):
        ctx = {
            "labels": [{"name": "bug"}],
            "branches": [{"name": "main"}],
            "milestones": [{"title": "v1.0"}],
            "collaborators": [{"login": "alice"}],
        }
        msgs = create_issue_generation_prompt("Add dark mode", "Proj", metadata_context=ctx)
        content = msgs[1]["content"]
        assert "AVAILABLE LABELS" in content
        assert "AVAILABLE BRANCHES" in content
        assert "AVAILABLE MILESTONES" in content
        assert "ASSIGNEE CANDIDATES" in content
        # Extra metadata fields should be injected for response schema
        assert "assignees" in content
        assert "milestone" in content
        assert "branch" in content

    def test_metadata_context_empty_lists_are_skipped(self):
        ctx = {"labels": [], "branches": [], "milestones": [], "collaborators": []}
        msgs = create_issue_generation_prompt("Add search", "Proj", metadata_context=ctx)
        content = msgs[1]["content"]
        assert "AVAILABLE LABELS" not in content
        assert "AVAILABLE BRANCHES" not in content

    def test_metadata_context_mixed_populated_empty(self):
        ctx = {"labels": [{"name": "bug"}], "branches": [], "milestones": [], "collaborators": []}
        msgs = create_issue_generation_prompt("Add search", "Proj", metadata_context=ctx)
        content = msgs[1]["content"]
        assert "AVAILABLE LABELS" in content
        assert "AVAILABLE BRANCHES" not in content

    def test_no_metadata_context_has_no_extra_fields(self):
        msgs = create_issue_generation_prompt("Add search", "Proj", metadata_context=None)
        content = msgs[1]["content"]
        assert "AVAILABLE LABELS" not in content
        assert "assignees" not in content


# =============================================================================
# Feature request detection prompt
# =============================================================================


class TestCreateFeatureRequestDetectionPrompt:
    """Tests for create_feature_request_detection_prompt()."""

    def test_returns_two_messages(self):
        msgs = create_feature_request_detection_prompt("I need a button")
        assert len(msgs) == 2

    def test_system_message_first(self):
        msgs = create_feature_request_detection_prompt("I need a button")
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == FEATURE_REQUEST_DETECTION_PROMPT

    def test_user_input_in_user_message(self):
        msgs = create_feature_request_detection_prompt("I need a button")
        assert "I need a button" in msgs[1]["content"]

    def test_user_message_role(self):
        msgs = create_feature_request_detection_prompt("anything")
        assert msgs[1]["role"] == "user"


# =============================================================================
# Task generation prompt
# =============================================================================


class TestCreateTaskGenerationPrompt:
    """Tests for create_task_generation_prompt()."""

    def test_returns_two_messages(self):
        msgs = create_task_generation_prompt("Fix login bug", "Backend")
        assert len(msgs) == 2

    def test_system_message_first(self):
        msgs = create_task_generation_prompt("Fix login bug", "Backend")
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == TASK_GENERATION_SYSTEM_PROMPT

    def test_user_message_contains_input_and_project(self):
        msgs = create_task_generation_prompt("Fix login bug", "Backend")
        assert "Fix login bug" in msgs[1]["content"]
        assert "Backend" in msgs[1]["content"]

    def test_user_message_role(self):
        msgs = create_task_generation_prompt("x", "y")
        assert msgs[1]["role"] == "user"


# =============================================================================
# Status change prompt
# =============================================================================


class TestCreateStatusChangePrompt:
    """Tests for create_status_change_prompt()."""

    def test_returns_two_messages(self):
        msgs = create_status_change_prompt(
            "Move login to done", ["Fix login", "Add test"], ["Todo", "Done"]
        )
        assert len(msgs) == 2

    def test_system_message_first(self):
        msgs = create_status_change_prompt("x", [], [])
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == STATUS_CHANGE_SYSTEM_PROMPT

    def test_user_message_contains_tasks_and_statuses(self):
        tasks = ["Fix login", "Add test"]
        statuses = ["Todo", "Done"]
        msgs = create_status_change_prompt("move login to done", tasks, statuses)
        content = msgs[1]["content"]
        assert "Fix login" in content
        assert "Add test" in content
        assert "Todo" in content
        assert "Done" in content
        assert "move login to done" in content

    def test_user_message_role(self):
        msgs = create_status_change_prompt("x", [], [])
        assert msgs[1]["role"] == "user"

    def test_truncates_long_task_list(self):
        """Tasks list is truncated at 20 items."""
        tasks = [f"Task {i}" for i in range(30)]
        msgs = create_status_change_prompt("x", tasks, ["Todo"])
        content = msgs[1]["content"]
        assert "Task 19" in content
        assert "Task 20" not in content


# =============================================================================
# Module-level constants sanity checks
# =============================================================================


class TestLabels:
    """Verify LABELS is well-formed."""

    def test_contains_ai_generated(self):
        assert "ai-generated" in LABELS

    def test_contains_feature(self):
        assert "feature" in LABELS

    def test_all_lowercase(self):
        for label in LABELS:
            assert label == label.lower(), f"Label not lowercase: {label}"

    def test_no_duplicates(self):
        assert len(LABELS) == len(set(LABELS))
