"""Unit tests for the label classification service.

Tests cover:
- validate_labels: taxonomy filtering, dedup, type-label default, ai-generated guarantee
- classify_labels: happy path with mocked AI, fallback on failure, empty input fast path
- _parse_labels_response: JSON parsing edge cases
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.services.label_classifier import (
    ALWAYS_INCLUDED_LABEL,
    DEFAULT_TYPE_LABEL,
    TYPE_LABELS,
    _parse_labels_response,
    classify_labels,
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


# ── classify_labels ─────────────────────────────────────────────────────────


class TestClassifyLabels:
    @pytest.mark.anyio
    async def test_successful_classification(self):
        """Happy path: AI returns valid labels."""
        ai_response = json.dumps({"labels": ["enhancement", "backend", "performance"]})
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = ai_response

        with patch(
            "src.services.label_classifier.create_completion_provider",
            return_value=mock_provider,
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
        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = RuntimeError("AI unavailable")

        with patch(
            "src.services.label_classifier.create_completion_provider",
            return_value=mock_provider,
        ):
            result = await classify_labels(
                title="Some issue",
                github_token="tok",
            )

        assert result == [ALWAYS_INCLUDED_LABEL, DEFAULT_TYPE_LABEL]

    @pytest.mark.anyio
    async def test_fallback_on_invalid_json(self):
        """When the AI returns garbage, fallback labels are returned."""
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = "this is not json"

        with patch(
            "src.services.label_classifier.create_completion_provider",
            return_value=mock_provider,
        ):
            result = await classify_labels(
                title="Some issue",
                github_token="tok",
            )

        assert result == [ALWAYS_INCLUDED_LABEL, DEFAULT_TYPE_LABEL]

    @pytest.mark.anyio
    async def test_empty_title_returns_fallback_without_ai_call(self):
        """When title is blank, skip the AI call entirely."""
        mock_provider = AsyncMock()

        with patch(
            "src.services.label_classifier.create_completion_provider",
            return_value=mock_provider,
        ):
            result = await classify_labels(
                title="   ",
                description="",
                github_token="tok",
            )

        mock_provider.complete.assert_not_called()
        assert result == [ALWAYS_INCLUDED_LABEL, DEFAULT_TYPE_LABEL]

    @pytest.mark.anyio
    async def test_ai_returns_invalid_labels_filtered(self):
        """Invalid labels in the AI response are removed."""
        ai_response = json.dumps({"labels": ["bug", "MADE_UP", "frontend"]})
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = ai_response

        with patch(
            "src.services.label_classifier.create_completion_provider",
            return_value=mock_provider,
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
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = ai_response

        with patch(
            "src.services.label_classifier.create_completion_provider",
            return_value=mock_provider,
        ):
            result = await classify_labels(
                title="Add caching layer",
                description="   ",
                github_token="tok",
            )

        mock_provider.complete.assert_called_once()
        assert "feature" in result
