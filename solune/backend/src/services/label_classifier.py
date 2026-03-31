"""Centralized label classification service for GitHub parent issues.

Provides :func:`classify_labels` — an async function that uses the existing
AI completion provider to infer content-based labels from an issue title and
optional description.  All three issue creation paths (pipeline launch, task
creation, agent tool) call this shared service.

The companion :func:`validate_labels` is a pure post-processing function that
ensures the label set satisfies the invariants defined in the contract:

* ``"ai-generated"`` is always present (index 0).
* Exactly one *type* label is present (defaults to ``"feature"``).
* All labels belong to the predefined taxonomy (``constants.LABELS``).
* No duplicates.
"""

from __future__ import annotations

import json

from src.constants import LABELS
from src.logging_utils import get_logger
from src.prompts.label_classification import build_label_classification_prompt

logger = get_logger(__name__)

# ── Category constants ──────────────────────────────────────────────────────

TYPE_LABELS: set[str] = {
    "feature",
    "bug",
    "enhancement",
    "refactor",
    "documentation",
    "testing",
    "infrastructure",
}

DEFAULT_TYPE_LABEL: str = "feature"
ALWAYS_INCLUDED_LABEL: str = "ai-generated"

# Pre-compute a lowercase lookup set for fast membership checks.
_VALID_LABELS: set[str] = {label.lower() for label in LABELS}

# Minimum valid fallback when classification fails entirely.
_FALLBACK_LABELS: list[str] = [ALWAYS_INCLUDED_LABEL, DEFAULT_TYPE_LABEL]


# ── Public API ──────────────────────────────────────────────────────────────


async def classify_labels(
    title: str,
    description: str = "",
    *,
    github_token: str,
) -> list[str]:
    """Classify labels for a GitHub issue based on its title and description.

    Returns a validated, deduplicated label list guaranteed to include
    ``"ai-generated"`` and exactly one type label.  On **any** failure the
    function falls back to ``["ai-generated", "feature"]`` — it never raises.

    Args:
        title: Issue title.
        description: Optional issue body (truncated internally).
        github_token: GitHub OAuth token for the AI provider.

    Returns:
        Validated label list.
    """
    # Fast path: if both inputs are effectively empty, skip the AI call.
    if not title.strip() and not (description and description.strip()):
        return list(_FALLBACK_LABELS)

    try:
        from src.services.completion_providers import create_completion_provider

        provider = create_completion_provider()
        messages = build_label_classification_prompt(title, description)

        raw_response = await provider.complete(
            messages=messages,
            temperature=0.3,
            max_tokens=200,
            github_token=github_token,
        )

        raw_labels = _parse_labels_response(raw_response)
        return validate_labels(raw_labels)

    except Exception:
        logger.warning(
            "Label classification failed for title=%r; using fallback labels",
            title[:80],
            exc_info=True,
        )
        return list(_FALLBACK_LABELS)


def validate_labels(raw_labels: list[str]) -> list[str]:
    """Post-process raw AI output into a valid label set.

    Guarantees:
    1. All labels are present in ``constants.LABELS`` (case-insensitive).
    2. ``"ai-generated"`` is always at index 0.
    3. Exactly one type label is present (defaults to ``"feature"``).
    4. No duplicate labels.

    This is a pure function with no side effects.
    """
    # 1. Normalise to lowercase and filter against taxonomy.
    seen: set[str] = set()
    filtered: list[str] = []
    for label in raw_labels:
        normalised = label.strip().lower()
        if normalised in _VALID_LABELS and normalised not in seen:
            seen.add(normalised)
            filtered.append(normalised)

    # 2. Ensure exactly one type label.
    type_labels_present = [lb for lb in filtered if lb in TYPE_LABELS]
    if len(type_labels_present) == 0:
        filtered.append(DEFAULT_TYPE_LABEL)
    elif len(type_labels_present) > 1:
        # Keep only the first type label; remove the rest.
        first_type = type_labels_present[0]
        filtered = [lb for lb in filtered if lb not in TYPE_LABELS or lb == first_type]

    # 3. Ensure "ai-generated" is present at index 0.
    if ALWAYS_INCLUDED_LABEL in filtered:
        filtered.remove(ALWAYS_INCLUDED_LABEL)
    filtered.insert(0, ALWAYS_INCLUDED_LABEL)

    return filtered


# ── Internal helpers ────────────────────────────────────────────────────────


def _parse_labels_response(raw: str) -> list[str]:
    """Extract a ``labels`` list from the AI's JSON response.

    Handles common formatting issues: markdown code fences, extra whitespace,
    and direct array responses.
    """
    text = raw.strip()
    # Strip markdown fences if present.
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()

    parsed = json.loads(text)

    if isinstance(parsed, dict):
        return list(parsed.get("labels", []))
    if isinstance(parsed, list):
        return list(parsed)

    return []
