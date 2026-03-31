"""Tests for the shared label classifier service."""

from unittest.mock import AsyncMock, patch

import pytest

from src.services.label_classifier import classify_labels, validate_labels


class TestValidateLabels:
    def test_filters_invalid_labels_and_deduplicates(self):
        labels = validate_labels(["backend", "invalid", "backend", "performance", "feature"])
        assert labels == ["ai-generated", "backend", "performance", "feature"]

    def test_defaults_type_when_only_scope_labels_are_present(self):
        assert validate_labels(["backend"]) == ["ai-generated", "backend", "feature"]

    def test_defaults_type_label_when_missing(self):
        assert validate_labels([]) == ["ai-generated", "feature"]

    def test_keeps_only_first_type_label(self):
        labels = validate_labels(["bug", "feature", "frontend"])
        assert labels == ["ai-generated", "frontend", "bug"]


class TestClassifyLabels:
    @pytest.mark.anyio
    async def test_returns_validated_labels_from_provider(self):
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = (
            '{"labels":["enhancement","backend","performance","enhancement","invalid"]}'
        )

        with patch(
            "src.services.label_classifier.create_completion_provider",
            return_value=mock_provider,
        ):
            labels = await classify_labels(
                "Improve API latency", "Tune slow database query", github_token="t"
            )

        assert labels == ["ai-generated", "backend", "performance", "enhancement"]

    @pytest.mark.anyio
    async def test_falls_back_when_provider_raises(self):
        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = RuntimeError("boom")

        with patch(
            "src.services.label_classifier.create_completion_provider",
            return_value=mock_provider,
        ):
            labels = await classify_labels(
                "Improve API latency", "Tune slow database query", github_token="t"
            )

        assert labels == ["ai-generated", "feature"]

    @pytest.mark.anyio
    async def test_falls_back_on_invalid_json(self):
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = "not-json"

        with patch(
            "src.services.label_classifier.create_completion_provider",
            return_value=mock_provider,
        ):
            labels = await classify_labels(
                "Improve API latency", "Tune slow database query", github_token="t"
            )

        assert labels == ["ai-generated", "feature"]

    @pytest.mark.anyio
    async def test_skips_provider_for_blank_content(self):
        with patch("src.services.label_classifier.create_completion_provider") as mock_factory:
            labels = await classify_labels("   ", "  ", github_token="t")

        assert labels == ["ai-generated", "feature"]
        mock_factory.assert_not_called()

    @pytest.mark.anyio
    async def test_truncates_description_in_prompt(self):
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = '{"labels":["frontend"]}'
        long_description = "A" * 2105 + "TRUNCATED"

        with patch(
            "src.services.label_classifier.create_completion_provider",
            return_value=mock_provider,
        ):
            await classify_labels("Improve dashboard", long_description, github_token="t")

        messages = mock_provider.complete.await_args.args[0]
        user_message = messages[1]["content"]
        assert "A" * 2000 in user_message
        assert "TRUNCATED" not in user_message
