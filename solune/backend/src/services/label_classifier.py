"""Shared issue label classification service."""

from __future__ import annotations

import json
from typing import Any

from src.constants import LABELS
from src.logging_utils import get_logger
from src.prompts.label_classification import build_label_classification_messages
from src.services.completion_providers import create_completion_provider

logger = get_logger(__name__)

TYPE_LABELS = {
    "feature",
    "bug",
    "enhancement",
    "refactor",
    "documentation",
    "testing",
    "infrastructure",
}
DEFAULT_TYPE_LABEL = "feature"
ALWAYS_INCLUDED_LABEL = "ai-generated"
FALLBACK_LABELS = [ALWAYS_INCLUDED_LABEL, DEFAULT_TYPE_LABEL]


def validate_labels(raw_labels: list[Any]) -> list[str]:
    """Normalize classifier output to the supported label taxonomy."""
    valid_labels = set(LABELS)
    validated_labels: list[str] = []
    seen: set[str] = set()

    for raw_label in raw_labels:
        if not isinstance(raw_label, str):
            continue
        label = raw_label.strip().lower()
        if not label or label not in valid_labels or label in seen:
            continue
        seen.add(label)
        validated_labels.append(label)

    type_label = next((label for label in validated_labels if label in TYPE_LABELS), None)
    validated_without_types = [label for label in validated_labels if label not in TYPE_LABELS]

    labels = [ALWAYS_INCLUDED_LABEL]
    labels.extend(label for label in validated_without_types if label != ALWAYS_INCLUDED_LABEL)
    labels.append(type_label or DEFAULT_TYPE_LABEL)
    return labels


async def classify_labels(title: str, description: str = "", *, github_token: str) -> list[str]:
    """Classify issue labels from title and description using the configured AI provider."""
    if not title.strip() and not description.strip():
        return FALLBACK_LABELS.copy()

    try:
        provider = create_completion_provider()
        response = await provider.complete(
            build_label_classification_messages(title, description),
            temperature=0.0,
            max_tokens=200,
            github_token=github_token,
        )
        parsed = _parse_label_response(response)
        labels = parsed.get("labels")
        if not isinstance(labels, list):
            raise ValueError("Label classifier response did not contain a labels array")
        return validate_labels(labels)
    except Exception:
        logger.warning("Falling back to default labels for issue classification", exc_info=True)
        return FALLBACK_LABELS.copy()


def _parse_label_response(response: str) -> dict[str, Any]:
    content = response.strip()
    if content.startswith("```"):
        content = content.strip("`").removeprefix("json").strip()

    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("Label classifier response must be a JSON object")
    return parsed
