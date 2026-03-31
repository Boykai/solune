"""Prompt template for AI-assisted label classification of GitHub issues.

Dynamically injects the predefined label taxonomy from ``constants.LABELS``
so that the prompt always reflects the current taxonomy (FR-010).
"""

from src.constants import LABELS

# Maximum characters of issue description to include in the prompt.
_MAX_DESCRIPTION_LENGTH = 2_000

# ── System prompt ────────────────────────────────────────────────────────────

LABEL_CLASSIFICATION_SYSTEM_PROMPT = f"""You are a label classifier for GitHub issues.

Given an issue title and optional description, select the most relevant labels from the PREDEFINED LIST below.

PREDEFINED LABELS (select ONLY from this list):

Type labels (pick exactly ONE):
  feature, bug, enhancement, refactor, documentation, testing, infrastructure

Scope labels (pick all that apply):
  frontend, backend, database, api

Domain labels (pick all that apply):
  security, performance, accessibility, ux

Rules:
1. Always include "ai-generated".
2. Include exactly ONE type label. If unsure, default to "feature".
3. Include all applicable scope and domain labels.
4. Do NOT invent labels outside the predefined list: {LABELS}
5. Return a JSON object with a single key "labels" containing an array of strings.

Example output:
{{"labels": ["ai-generated", "enhancement", "backend", "performance"]}}

Output raw JSON ONLY. No markdown fences, no explanation."""


def build_label_classification_prompt(
    title: str,
    description: str = "",
) -> list[dict[str, str]]:
    """Build chat messages for the label classification AI call.

    Args:
        title: Issue title (always included in full).
        description: Optional issue body, truncated to
            ``_MAX_DESCRIPTION_LENGTH`` characters.

    Returns:
        List of ``{"role": ..., "content": ...}`` message dicts.
    """
    desc = description[:_MAX_DESCRIPTION_LENGTH] if description else ""

    user_content = f"Title: {title}"
    if desc.strip():
        user_content += f"\n\nDescription:\n{desc}"

    return [
        {"role": "system", "content": LABEL_CLASSIFICATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
