"""Shared label classification service for parent issue creation paths."""

from __future__ import annotations

import json
from collections.abc import Iterable
from json import JSONDecodeError
from typing import Any

from src.constants import LABELS
from src.logging_utils import get_logger
from src.prompts.label_classification import build_label_classification_messages
from src.services.completion_providers import create_completion_provider

logger = get_logger(__name__)

TYPE_LABELS: set[str] = {
    label
    for label in (
        "feature",
        "bug",
        "enhancement",
        "refactor",
        "documentation",
        "testing",
        "infrastructure",
    )
    if label in LABELS
}
DEFAULT_TYPE_LABEL = "feature"
ALWAYS_INCLUDED_LABEL = "ai-generated"
DEFAULT_CLASSIFIED_LABELS = [ALWAYS_INCLUDED_LABEL, DEFAULT_TYPE_LABEL]
MAX_DESCRIPTION_LENGTH = 2000


class LabelClassificationError(RuntimeError):
    """Raised when AI label classification cannot produce a valid response."""


def validate_labels(raw_labels: Iterable[str]) -> list[str]:
    """Validate, deduplicate, and normalize a set of issue labels."""
    allowed_labels = set(LABELS)
    seen: set[str] = set()
    ordered_labels: list[str] = []

    for label in raw_labels:
        normalized = label.strip()
        if not normalized or normalized not in allowed_labels or normalized in seen:
            continue
        seen.add(normalized)
        ordered_labels.append(normalized)

    type_label = next(
        (label for label in ordered_labels if label in TYPE_LABELS), DEFAULT_TYPE_LABEL
    )
    other_labels = [
        label
        for label in ordered_labels
        if label not in TYPE_LABELS and label != ALWAYS_INCLUDED_LABEL
    ]
    return [ALWAYS_INCLUDED_LABEL, type_label, *other_labels]


def _extract_raw_labels(response: Any) -> list[str]:
    """Extract a labels list from a provider response."""
    data: Any = response
    if isinstance(response, str):
        try:
            data = json.loads(response)
        except JSONDecodeError as exc:
            raise LabelClassificationError("Classifier returned invalid JSON") from exc

    if not isinstance(data, dict):
        raise LabelClassificationError("Classifier response must be a JSON object")

    labels = data.get("labels")
    if not isinstance(labels, list):
        raise LabelClassificationError("Classifier response is missing a labels array")
    if any(not isinstance(label, str) for label in labels):
        raise LabelClassificationError("Classifier labels must be strings")
    return labels


async def classify_labels(
    title: str,
    description: str = "",
    *,
    github_token: str | None,
) -> list[str]:
    """Classify labels from an issue title and optional description."""
    normalized_title = title.strip()
    normalized_description = description.strip()
    if not normalized_title and not normalized_description:
        return DEFAULT_CLASSIFIED_LABELS.copy()

    provider = create_completion_provider()
    truncated_description = normalized_description[:MAX_DESCRIPTION_LENGTH]
    messages = build_label_classification_messages(normalized_title, truncated_description)

    try:
        response = await provider.complete(
            messages=messages,
            temperature=0.1,
            max_tokens=200,
            github_token=github_token,
        )
    except Exception as exc:
        logger.warning("Label classification failed", exc_info=True)
        raise LabelClassificationError("Label classification request failed") from exc

    labels = validate_labels(_extract_raw_labels(response))
    if labels == DEFAULT_CLASSIFIED_LABELS and (normalized_title or normalized_description):
        logger.debug("Label classifier returned only default labels")
    return labels
