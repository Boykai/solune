"""Unit tests for the label classification prompt builder module.

Tests cover:
- _build_user_content: title-only, title+description, description truncation,
  empty/whitespace-only description handling
- build_label_classification_prompt: message structure and system prompt usage
- build_label_classification_with_priority_prompt: message structure, priority
  system prompt usage, urgency rule content
- System prompt constants: dynamic taxonomy injection, required keywords
"""

from __future__ import annotations

from src.constants import DOMAIN_LABELS, LABELS, SCOPE_LABELS, TYPE_LABELS
from src.prompts.label_classification import (
    LABEL_CLASSIFICATION_SYSTEM_PROMPT,
    LABEL_CLASSIFICATION_WITH_PRIORITY_SYSTEM_PROMPT,
    _build_user_content,
    build_label_classification_prompt,
    build_label_classification_with_priority_prompt,
)

# ── _build_user_content ─────────────────────────────────────────────────────


class TestBuildUserContent:
    def test_title_only(self):
        content = _build_user_content("Fix login button")
        assert content == "Title: Fix login button"

    def test_title_with_description(self):
        content = _build_user_content("Fix login", "User cannot authenticate")
        assert "Title: Fix login" in content
        assert "Description:" in content
        assert "User cannot authenticate" in content

    def test_description_truncated_at_max_length(self):
        long_desc = "x" * 5_000
        content = _build_user_content("Title", long_desc)
        # _MAX_DESCRIPTION_LENGTH is 2000; content = title line + desc ≤ 2000
        assert len(content) < 2_100

    def test_empty_description_excluded(self):
        content = _build_user_content("Title", "")
        assert "Description:" not in content

    def test_whitespace_only_description_excluded(self):
        content = _build_user_content("Title", "   \n  \t  ")
        assert "Description:" not in content

    def test_default_description_excluded(self):
        """Calling without description omits the description section."""
        content = _build_user_content("Title")
        assert "Description:" not in content


# ── build_label_classification_prompt ───────────────────────────────────────


class TestBuildLabelClassificationPrompt:
    def test_returns_two_messages(self):
        msgs = build_label_classification_prompt("Title", "Desc")
        assert isinstance(msgs, list)
        assert len(msgs) == 2

    def test_system_message_uses_base_prompt(self):
        msgs = build_label_classification_prompt("Title", "Desc")
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == LABEL_CLASSIFICATION_SYSTEM_PROMPT

    def test_user_message_contains_title(self):
        msgs = build_label_classification_prompt("My Feature Request", "")
        assert msgs[1]["role"] == "user"
        assert "My Feature Request" in msgs[1]["content"]

    def test_user_message_contains_description(self):
        msgs = build_label_classification_prompt("Title", "Some body text")
        assert "Some body text" in msgs[1]["content"]


# ── build_label_classification_with_priority_prompt ─────────────────────────


class TestBuildLabelClassificationWithPriorityPrompt:
    def test_returns_two_messages(self):
        msgs = build_label_classification_with_priority_prompt("Title", "Desc")
        assert isinstance(msgs, list)
        assert len(msgs) == 2

    def test_system_message_uses_priority_prompt(self):
        msgs = build_label_classification_with_priority_prompt("Title", "Desc")
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == LABEL_CLASSIFICATION_WITH_PRIORITY_SYSTEM_PROMPT

    def test_system_prompt_includes_priority_rules(self):
        msgs = build_label_classification_with_priority_prompt("Title", "")
        system = msgs[0]["content"]
        assert "priority" in system.lower()
        assert "P0" in system
        assert "P1" in system

    def test_user_message_contains_title(self):
        msgs = build_label_classification_with_priority_prompt("Auth Bug", "details")
        assert "Auth Bug" in msgs[1]["content"]


# ── System prompt constants ─────────────────────────────────────────────────


class TestSystemPromptConstants:
    def test_base_prompt_includes_type_labels(self):
        for label in TYPE_LABELS:
            assert label in LABEL_CLASSIFICATION_SYSTEM_PROMPT

    def test_base_prompt_includes_scope_labels(self):
        for label in SCOPE_LABELS:
            assert label in LABEL_CLASSIFICATION_SYSTEM_PROMPT

    def test_base_prompt_includes_domain_labels(self):
        for label in DOMAIN_LABELS:
            assert label in LABEL_CLASSIFICATION_SYSTEM_PROMPT

    def test_base_prompt_requires_ai_generated(self):
        assert "ai-generated" in LABEL_CLASSIFICATION_SYSTEM_PROMPT

    def test_priority_prompt_includes_urgency_signals(self):
        prompt = LABEL_CLASSIFICATION_WITH_PRIORITY_SYSTEM_PROMPT
        # The prompt should mention production outage / security for P0
        assert "outage" in prompt.lower() or "production" in prompt.lower()

    def test_priority_prompt_marks_priority_as_optional(self):
        prompt = LABEL_CLASSIFICATION_WITH_PRIORITY_SYSTEM_PROMPT
        assert "optional" in prompt.lower() or "omit" in prompt.lower()

    def test_priority_prompt_includes_all_taxonomy_labels(self):
        """All taxonomy labels from constants should appear in the priority prompt."""
        prompt_lower = LABEL_CLASSIFICATION_WITH_PRIORITY_SYSTEM_PROMPT.lower()
        for label in TYPE_LABELS | SCOPE_LABELS | DOMAIN_LABELS:
            assert label in prompt_lower

    def test_prompts_include_full_label_list(self):
        """Both system prompts reference the full LABELS list."""
        assert str(LABELS) in LABEL_CLASSIFICATION_SYSTEM_PROMPT
        assert str(LABELS) in LABEL_CLASSIFICATION_WITH_PRIORITY_SYSTEM_PROMPT
