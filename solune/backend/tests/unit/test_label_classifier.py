"""Unit tests for the shared label classification service."""

from unittest.mock import AsyncMock, patch

import pytest

from src.services.label_classifier import (
    DEFAULT_CLASSIFIED_LABELS,
    TYPE_LABELS,
    LabelClassificationError,
    classify_labels,
    validate_labels,
)


class TestValidateLabels:
    def test_filters_invalid_labels_and_deduplicates(self):
        labels = validate_labels(
            ["ai-generated", "backend", "invalid-label", "backend", "enhancement"]
        )
        assert labels == ["ai-generated", "enhancement", "backend"]

    def test_adds_default_type_and_ai_generated(self):
        labels = validate_labels(["performance", "frontend"])
        assert labels == ["ai-generated", "feature", "performance", "frontend"]

    def test_keeps_only_first_type_label(self):
        labels = validate_labels(["bug", "feature", "api"])
        assert labels == ["ai-generated", "bug", "api"]
        assert len([label for label in labels if label in TYPE_LABELS]) == 1


class TestClassifyLabels:
    @pytest.mark.asyncio
    async def test_returns_validated_labels_from_json(self):
        provider = AsyncMock()
        provider.complete.return_value = (
            '{"labels":["backend","ai-generated","performance","backend","invalid"]}'
        )

        with patch(
            "src.services.label_classifier.create_completion_provider",
            return_value=provider,
        ):
            labels = await classify_labels(
                title="Optimize API latency",
                description="Speed up slow backend queries.",
                github_token="test-token",
            )

        assert labels == ["ai-generated", "feature", "backend", "performance"]

    @pytest.mark.asyncio
    async def test_returns_defaults_for_empty_input_without_calling_provider(self):
        provider = AsyncMock()

        with patch(
            "src.services.label_classifier.create_completion_provider",
            return_value=provider,
        ):
            labels = await classify_labels(
                title="   ", description="   ", github_token="test-token"
            )

        assert labels == DEFAULT_CLASSIFIED_LABELS
        provider.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_truncates_long_description_before_prompting(self):
        provider = AsyncMock()
        provider.complete.return_value = '{"labels":["testing"]}'
        description = "x" * 5000

        with patch(
            "src.services.label_classifier.create_completion_provider",
            return_value=provider,
        ):
            labels = await classify_labels(
                title="Add regression coverage",
                description=description,
                github_token="test-token",
            )

        assert labels == ["ai-generated", "testing"]
        prompt_messages = provider.complete.await_args.kwargs["messages"]
        assert description[:2000] in prompt_messages[1]["content"]
        assert description[:2001] not in prompt_messages[1]["content"]

    @pytest.mark.asyncio
    async def test_raises_on_provider_error(self):
        provider = AsyncMock()
        provider.complete.side_effect = RuntimeError("boom")

        with (
            patch(
                "src.services.label_classifier.create_completion_provider",
                return_value=provider,
            ),
            pytest.raises(LabelClassificationError, match="request failed"),
        ):
            await classify_labels(
                title="Fix issue",
                description="Details",
                github_token="test-token",
            )

    @pytest.mark.asyncio
    async def test_raises_on_invalid_json_response(self):
        provider = AsyncMock()
        provider.complete.return_value = "not-json"

        with (
            patch(
                "src.services.label_classifier.create_completion_provider",
                return_value=provider,
            ),
            pytest.raises(LabelClassificationError, match="invalid JSON"),
        ):
            await classify_labels(
                title="Fix issue",
                description="Details",
                github_token="test-token",
            )
