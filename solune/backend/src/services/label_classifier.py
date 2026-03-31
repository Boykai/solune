"""Helpers for AI-assisted issue label classification."""

from __future__ import annotations

import json
import re
from typing import Any

from src.constants import LABELS
from src.logging_utils import get_logger
from src.prompts.label_classification import create_label_classification_prompt
from src.services.completion_providers import CompletionProvider, create_completion_provider

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


def validate_labels(
    labels: list[str] | None,
    repo_labels: list[str | dict[str, Any]] | None = None,
) -> list[str]:
    """Normalize and validate a label list, ensuring required defaults exist."""
    valid_label_set = {label.lower() for label in LABELS}
    if repo_labels:
        for label in repo_labels:
            if isinstance(label, dict):
                name = label.get("name")
            else:
                name = label
            if isinstance(name, str):
                valid_label_set.add(name.strip().lower())

    validated_labels: list[str] = []
    seen: set[str] = set()

    for label in labels or []:
        if not isinstance(label, str):
            continue
        normalized = label.strip().lower()
        if normalized and normalized in valid_label_set and normalized not in seen:
            validated_labels.append(normalized)
            seen.add(normalized)

    if ALWAYS_INCLUDED_LABEL in seen:
        validated_labels.remove(ALWAYS_INCLUDED_LABEL)
    validated_labels.insert(0, ALWAYS_INCLUDED_LABEL)

    if not any(label in TYPE_LABELS for label in validated_labels):
        validated_labels.append(DEFAULT_TYPE_LABEL)

    return validated_labels


def _parse_label_response(response: str) -> list[str]:
    """Parse label output from the model response."""
    content = response.strip()
    if not content:
        return []

    parsed: Any
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", content, re.DOTALL)
        if not match:
            return []
        try:
            parsed = json.loads(match.group(1))
        except json.JSONDecodeError:
            return []

    if isinstance(parsed, dict):
        parsed = parsed.get("labels", [])

    if isinstance(parsed, str):
        return [part.strip() for part in parsed.split(",") if part.strip()]

    if isinstance(parsed, list):
        return [label for label in parsed if isinstance(label, str)]

    return []


async def classify_labels(
    title: str,
    description: str,
    *,
    github_token: str | None,
    provider: CompletionProvider | None = None,
) -> list[str]:
    """Classify labels for an issue title and description."""
    if not github_token:
        return validate_labels([])

    completion_provider = provider or create_completion_provider()
    messages = create_label_classification_prompt(title, description)

    try:
        response = await completion_provider.complete(
            messages=messages,
            temperature=0.0,
            max_tokens=120,
            github_token=github_token,
        )
    except Exception:
        logger.exception("Failed to classify issue labels")
        return validate_labels([])

    return validate_labels(_parse_label_response(response))
