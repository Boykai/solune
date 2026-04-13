"""Unit tests for the label classification service.

Tests cover:
- validate_labels: taxonomy filtering, dedup, type-label default, ai-generated guarantee
- classify_labels: happy path with mocked AI, fallback on failure, empty input fast path,
  timeout handling, custom fallback_labels
- ClassificationResult: dataclass immutability and defaults
- classify_labels_with_priority: urgency detection, no-urgency fallback, AI timeout,
  invalid priority handling
- _parse_labels_response: JSON parsing edge cases
- _parse_labels_and_priority_response: priority extraction edge cases
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from src.constants import TYPE_LABELS
from src.models.recommendation import IssuePriority
from src.services.label_classifier import (
    ALWAYS_INCLUDED_LABEL,
    DEFAULT_TYPE_LABEL,
    ClassificationResult,
    _parse_labels_and_priority_response,
    _parse_labels_response,
    _strip_markdown_fences,
    classify_labels,
    classify_labels_with_priority,
    validate_labels,
)

# ── validate_labels ─────────────────────────────────────────────────────────


class TestValidateLabels:
    def test_valid_labels_preserved(self):
        result = validate_labels(["ai-generated", "bug", "frontend", "security"])
        assert result == ["ai-generated", "bug", "frontend", "security"]

    def test_invalid_labels_filtered(self):
        result = validate_labels(["ai-generated", "bug", "INVALID", "nonsense"])
        assert "INVALID" not in result
        assert "nonsense" not in result
        assert "bug" in result

    def test_ai_generated_always_first(self):
        result = validate_labels(["bug", "backend"])
        assert result[0] == ALWAYS_INCLUDED_LABEL

    def test_ai_generated_not_duplicated(self):
        result = validate_labels(["ai-generated", "ai-generated", "bug"])
        assert result.count("ai-generated") == 1

    def test_default_type_label_when_none(self):
        """When no type label is in the input, 'feature' is added."""
        result = validate_labels(["frontend", "security"])
        type_labels = [lb for lb in result if lb in TYPE_LABELS]
        assert len(type_labels) == 1
        assert DEFAULT_TYPE_LABEL in type_labels

    def test_multiple_type_labels_keeps_first(self):
        """When multiple type labels are present, only the first is kept."""
        result = validate_labels(["bug", "enhancement", "frontend"])
        type_labels = [lb for lb in result if lb in TYPE_LABELS]
        assert type_labels == ["bug"]

    def test_deduplication(self):
        result = validate_labels(["bug", "bug", "frontend", "frontend"])
        assert result.count("bug") == 1
        assert result.count("frontend") == 1

    def test_case_insensitive(self):
        result = validate_labels(["BUG", "Frontend", "AI-GENERATED"])
        assert "bug" in result
        assert "frontend" in result
        assert result.count("ai-generated") == 1

    def test_empty_input(self):
        result = validate_labels([])
        assert result[0] == ALWAYS_INCLUDED_LABEL
        assert DEFAULT_TYPE_LABEL in result

    def test_whitespace_labels_stripped(self):
        result = validate_labels(["  bug  ", " frontend "])
        assert "bug" in result
        assert "frontend" in result

    def test_all_scope_and_domain_labels_preserved(self):
        result = validate_labels(
            ["feature", "frontend", "backend", "database", "api", "security", "performance"]
        )
        for label in ["frontend", "backend", "database", "api", "security", "performance"]:
            assert label in result


# ── _strip_markdown_fences ──────────────────────────────────────────────────


class TestStripMarkdownFences:
    def test_plain_json(self):
        assert _strip_markdown_fences('{"labels": ["bug"]}') == '{"labels": ["bug"]}'

    def test_fenced_json(self):
        assert _strip_markdown_fences('```json\n{"a":1}\n```') == '{"a":1}'

    def test_leading_trailing_whitespace(self):
        assert _strip_markdown_fences("  \n  hello  \n  ") == "hello"

    def test_fences_without_language(self):
        assert _strip_markdown_fences("```\n[1,2]\n```") == "[1,2]"

    def test_opening_fence_only(self):
        """Only an opening fence — should strip it and return the content."""
        result = _strip_markdown_fences('```\n{"labels": []}')
        assert '{"labels": []}' == result

    def test_empty_string(self):
        assert _strip_markdown_fences("") == ""
        assert _strip_markdown_fences("   ") == ""


# ── _parse_labels_response ──────────────────────────────────────────────────


class TestParseLabelsResponse:
    def test_json_object_with_labels_key(self):
        raw = json.dumps({"labels": ["bug", "frontend"]})
        assert _parse_labels_response(raw) == ["bug", "frontend"]

    def test_json_array_directly(self):
        raw = json.dumps(["bug", "frontend"])
        assert _parse_labels_response(raw) == ["bug", "frontend"]

    def test_markdown_fenced_json(self):
        raw = '```json\n{"labels": ["bug"]}\n```'
        assert _parse_labels_response(raw) == ["bug"]

    def test_empty_labels(self):
        raw = json.dumps({"labels": []})
        assert _parse_labels_response(raw) == []

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_labels_response("not json at all")

    def test_labels_as_string_returns_empty(self):
        """When AI returns labels as a string instead of a list, return []."""
        raw = json.dumps({"labels": "bug"})
        assert _parse_labels_response(raw) == []


# ── classify_labels ─────────────────────────────────────────────────────────


class TestClassifyLabels:
    @pytest.mark.anyio
    async def test_successful_classification(self):
        """Happy path: AI returns valid labels."""
        ai_response = json.dumps({"labels": ["enhancement", "backend", "performance"]})

        with patch(
            "src.services.agent_provider.call_completion",
            new_callable=AsyncMock,
            return_value=ai_response,
        ):
            result = await classify_labels(
                title="Optimize database queries",
                description="Slow queries on dashboard",
                github_token="tok",
            )

        assert result[0] == ALWAYS_INCLUDED_LABEL
        assert "enhancement" in result
        assert "backend" in result
        assert "performance" in result
        # Exactly one type label
        assert len([lb for lb in result if lb in TYPE_LABELS]) == 1

    @pytest.mark.anyio
    async def test_fallback_on_ai_failure(self):
        """When the AI call raises, fallback labels are returned."""
        with patch(
            "src.services.agent_provider.call_completion",
            new_callable=AsyncMock,
            side_effect=RuntimeError("AI unavailable"),
        ):
            result = await classify_labels(
                title="Some issue",
                github_token="tok",
            )

        assert result == [ALWAYS_INCLUDED_LABEL, DEFAULT_TYPE_LABEL]

    @pytest.mark.anyio
    async def test_fallback_on_invalid_json(self):
        """When the AI returns garbage, fallback labels are returned."""

        with patch(
            "src.services.agent_provider.call_completion",
            new_callable=AsyncMock,
            return_value="this is not json",
        ):
            result = await classify_labels(
                title="Some issue",
                github_token="tok",
            )

        assert result == [ALWAYS_INCLUDED_LABEL, DEFAULT_TYPE_LABEL]

    @pytest.mark.anyio
    async def test_empty_title_returns_fallback_without_ai_call(self):
        """When title is blank, skip the AI call entirely."""
        with patch(
            "src.services.agent_provider.call_completion",
            new_callable=AsyncMock,
        ) as mock_completion:
            result = await classify_labels(
                title="   ",
                description="",
                github_token="tok",
            )

        mock_completion.assert_not_called()
        assert result == [ALWAYS_INCLUDED_LABEL, DEFAULT_TYPE_LABEL]

    @pytest.mark.anyio
    async def test_ai_returns_invalid_labels_filtered(self):
        """Invalid labels in the AI response are removed."""
        ai_response = json.dumps({"labels": ["bug", "MADE_UP", "frontend"]})

        with patch(
            "src.services.agent_provider.call_completion",
            new_callable=AsyncMock,
            return_value=ai_response,
        ):
            result = await classify_labels(
                title="Fix login",
                github_token="tok",
            )

        assert "MADE_UP" not in result
        assert "bug" in result
        assert "frontend" in result

    @pytest.mark.anyio
    async def test_description_only_triggers_ai(self):
        """Non-empty title with whitespace description still calls AI."""
        ai_response = json.dumps({"labels": ["feature", "backend"]})

        with patch(
            "src.services.agent_provider.call_completion",
            new_callable=AsyncMock,
            return_value=ai_response,
        ) as mock_completion:
            result = await classify_labels(
                title="Add caching layer",
                description="   ",
                github_token="tok",
            )

        mock_completion.assert_called_once()
        assert "feature" in result

    @pytest.mark.anyio
    async def test_custom_fallback_labels_on_failure(self):
        """When classification fails, caller-supplied fallback_labels are returned."""
        with patch(
            "src.services.agent_provider.call_completion",
            new_callable=AsyncMock,
            side_effect=RuntimeError("AI unavailable"),
        ):
            result = await classify_labels(
                title="Some issue",
                github_token="tok",
                fallback_labels=["ai-generated", "pipeline:core"],
            )

        assert result == ["ai-generated", "pipeline:core"]

    @pytest.mark.anyio
    async def test_empty_title_with_description_returns_fallback(self):
        """When title is blank (even with a description), skip the AI call."""

        with patch(
            "src.services.agent_provider.call_completion",
            new_callable=AsyncMock,
        ) as mock_completion:
            result = await classify_labels(
                title="   ",
                description="Some description here",
                github_token="tok",
            )

        mock_completion.assert_not_called()
        assert result == [ALWAYS_INCLUDED_LABEL, DEFAULT_TYPE_LABEL]

    @pytest.mark.anyio
    async def test_timeout_returns_fallback(self):
        """When the AI call exceeds the timeout, fallback labels are returned."""

        async def slow_complete(**kwargs):
            await asyncio.sleep(60)
            return json.dumps({"labels": ["bug"]})

        with (
            patch(
                "src.services.agent_provider.call_completion",
                new_callable=AsyncMock,
                side_effect=slow_complete,
            ),
            patch(
                "src.services.label_classifier._CLASSIFICATION_TIMEOUT_SECONDS",
                0.1,
            ),
        ):
            result = await classify_labels(
                title="Some issue",
                github_token="tok",
            )

        assert result == [ALWAYS_INCLUDED_LABEL, DEFAULT_TYPE_LABEL]

    @pytest.mark.anyio
    async def test_description_truncated_in_prompt(self):
        """Descriptions longer than 2,000 chars are truncated before the AI call."""
        ai_response = json.dumps({"labels": ["feature", "backend"]})

        long_desc = "x" * 5_000

        with patch(
            "src.services.agent_provider.call_completion",
            new_callable=AsyncMock,
            return_value=ai_response,
        ) as mock_completion:
            result = await classify_labels(
                title="Big issue",
                description=long_desc,
                github_token="tok",
            )

        # Verify the prompt was called and description was truncated.
        mock_completion.assert_called_once()
        messages = mock_completion.call_args.kwargs["messages"]
        user_msg = messages[1]["content"]
        # The description portion should not contain the full 5,000 chars.
        assert len(user_msg) < 5_000
        assert "feature" in result


# ── ClassificationResult ────────────────────────────────────────────────────


class TestClassificationResult:
    def test_defaults(self):
        result = ClassificationResult()
        assert result.labels == []
        assert result.priority is None

    def test_with_labels_and_priority(self):
        result = ClassificationResult(
            labels=["ai-generated", "bug"],
            priority=IssuePriority.P1,
        )
        assert result.labels == ["ai-generated", "bug"]
        assert result.priority == IssuePriority.P1

    def test_immutable(self):
        result = ClassificationResult(labels=["bug"])
        with pytest.raises(AttributeError):
            setattr(result, "priority", IssuePriority.P0)  # noqa: B010


# ── _parse_labels_and_priority_response ─────────────────────────────────────


class TestParseLabelsAndPriorityResponse:
    def test_labels_only(self):
        raw = json.dumps({"labels": ["bug", "backend"]})
        labels, priority = _parse_labels_and_priority_response(raw)
        assert labels == ["bug", "backend"]
        assert priority is None

    def test_labels_with_priority(self):
        raw = json.dumps({"labels": ["bug", "security"], "priority": "P0"})
        labels, priority = _parse_labels_and_priority_response(raw)
        assert labels == ["bug", "security"]
        assert priority == IssuePriority.P0

    def test_invalid_priority_ignored(self):
        raw = json.dumps({"labels": ["bug"], "priority": "P5"})
        labels, priority = _parse_labels_and_priority_response(raw)
        assert labels == ["bug"]
        assert priority is None

    def test_priority_null_treated_as_none(self):
        raw = json.dumps({"labels": ["feature"], "priority": None})
        labels, priority = _parse_labels_and_priority_response(raw)
        assert labels == ["feature"]
        assert priority is None

    def test_priority_as_integer_ignored(self):
        raw = json.dumps({"labels": ["feature"], "priority": 1})
        _labels, priority = _parse_labels_and_priority_response(raw)
        assert priority is None

    def test_array_response_no_priority(self):
        raw = json.dumps(["bug", "backend"])
        labels, priority = _parse_labels_and_priority_response(raw)
        assert labels == ["bug", "backend"]
        assert priority is None

    def test_markdown_fenced_json(self):
        raw = '```json\n{"labels": ["bug"], "priority": "P1"}\n```'
        labels, priority = _parse_labels_and_priority_response(raw)
        assert labels == ["bug"]
        assert priority == IssuePriority.P1

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_labels_and_priority_response("not json at all")

    def test_labels_as_string_returns_empty(self):
        """When AI returns labels as a string instead of a list, return []."""
        raw = json.dumps({"labels": "bug", "priority": "P0"})
        labels, priority = _parse_labels_and_priority_response(raw)
        assert labels == []
        assert priority == IssuePriority.P0

    @pytest.mark.parametrize(
        ("priority_str", "expected"),
        [
            ("P0", IssuePriority.P0),
            ("P1", IssuePriority.P1),
            ("P2", IssuePriority.P2),
            ("P3", IssuePriority.P3),
        ],
    )
    def test_all_valid_priority_values(self, priority_str: str, expected: IssuePriority):
        """Every valid IssuePriority enum value is parsed correctly."""
        raw = json.dumps({"labels": ["feature"], "priority": priority_str})
        _labels, priority = _parse_labels_and_priority_response(raw)
        assert priority == expected

    def test_empty_dict_returns_empty_labels_no_priority(self):
        """An empty dict returns empty labels and no priority."""
        raw = json.dumps({})
        labels, priority = _parse_labels_and_priority_response(raw)
        assert labels == []
        assert priority is None


# ── classify_labels_with_priority ───────────────────────────────────────────


class TestClassifyLabelsWithPriority:
    @pytest.mark.anyio
    async def test_urgency_detected(self):
        """AI returns P0 for production outage issues."""
        ai_response = json.dumps(
            {
                "labels": ["bug", "backend", "security"],
                "priority": "P0",
            }
        )
        with patch(
            "src.services.agent_provider.call_completion",
            new_callable=AsyncMock,
            return_value=ai_response,
        ):
            result = await classify_labels_with_priority(
                title="Critical security vulnerability in authentication module",
                description="Production system compromised",
                github_token="tok",
            )

        assert isinstance(result, ClassificationResult)
        assert result.priority == IssuePriority.P0
        assert "bug" in result.labels
        assert result.labels[0] == ALWAYS_INCLUDED_LABEL

    @pytest.mark.anyio
    async def test_no_urgency_returns_none_priority(self):
        """AI omits priority for routine issues."""
        ai_response = json.dumps(
            {
                "labels": ["feature", "frontend"],
            }
        )
        with patch(
            "src.services.agent_provider.call_completion",
            new_callable=AsyncMock,
            return_value=ai_response,
        ):
            result = await classify_labels_with_priority(
                title="Add pagination to user list",
                github_token="tok",
            )

        assert result.priority is None
        assert "feature" in result.labels

    @pytest.mark.anyio
    async def test_ai_failure_returns_fallback_with_no_priority(self):
        """On AI failure, fallback labels returned with priority=None."""
        with patch(
            "src.services.agent_provider.call_completion",
            new_callable=AsyncMock,
            side_effect=RuntimeError("AI unavailable"),
        ):
            result = await classify_labels_with_priority(
                title="Some issue",
                github_token="tok",
            )

        assert result.labels == [ALWAYS_INCLUDED_LABEL, DEFAULT_TYPE_LABEL]
        assert result.priority is None

    @pytest.mark.anyio
    async def test_timeout_returns_fallback(self):
        """AI timeout returns fallback with no priority."""

        async def slow_complete(**kwargs):
            await asyncio.sleep(60)
            return json.dumps({"labels": ["bug"], "priority": "P1"})

        with (
            patch(
                "src.services.agent_provider.call_completion",
                new_callable=AsyncMock,
                side_effect=slow_complete,
            ),
            patch(
                "src.services.label_classifier._CLASSIFICATION_TIMEOUT_SECONDS",
                0.1,
            ),
        ):
            result = await classify_labels_with_priority(
                title="Some issue",
                github_token="tok",
            )

        assert result.labels == [ALWAYS_INCLUDED_LABEL, DEFAULT_TYPE_LABEL]
        assert result.priority is None

    @pytest.mark.anyio
    async def test_invalid_priority_value_from_ai(self):
        """AI returns an invalid priority value — ignored."""
        ai_response = json.dumps(
            {
                "labels": ["bug", "backend"],
                "priority": "urgent",
            }
        )
        with patch(
            "src.services.agent_provider.call_completion",
            new_callable=AsyncMock,
            return_value=ai_response,
        ):
            result = await classify_labels_with_priority(
                title="Some urgent issue",
                github_token="tok",
            )

        assert result.priority is None
        assert "bug" in result.labels

    @pytest.mark.anyio
    async def test_empty_title_returns_fallback(self):
        """Empty title returns fallback without calling AI."""
        result = await classify_labels_with_priority(
            title="   ",
            github_token="tok",
        )
        assert result.labels == [ALWAYS_INCLUDED_LABEL, DEFAULT_TYPE_LABEL]
        assert result.priority is None

    @pytest.mark.anyio
    async def test_custom_fallback_on_failure(self):
        """Custom fallback labels are used on failure."""
        with patch(
            "src.services.agent_provider.call_completion",
            new_callable=AsyncMock,
            side_effect=RuntimeError("AI unavailable"),
        ):
            result = await classify_labels_with_priority(
                title="Some issue",
                github_token="tok",
                fallback_labels=["ai-generated", "pipeline:core"],
            )

        assert result.labels == ["ai-generated", "pipeline:core"]
        assert result.priority is None
