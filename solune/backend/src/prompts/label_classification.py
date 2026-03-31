"""Prompt template for AI-assisted label classification of GitHub issues.

Dynamically injects the predefined label taxonomy from ``constants`` so that
the prompt always reflects the current taxonomy (FR-010).  Category sets
(TYPE_LABELS, SCOPE_LABELS, DOMAIN_LABELS) are imported from constants.py —
adding a label there automatically updates the prompt.
"""

from src.constants import DOMAIN_LABELS, LABELS, SCOPE_LABELS, TYPE_LABELS

# Maximum characters of issue description to include in the prompt.
_MAX_DESCRIPTION_LENGTH = 2_000


def _build_system_prompt() -> str:
    """Build the system prompt dynamically from the label taxonomy."""
    type_str = ", ".join(sorted(TYPE_LABELS))
    scope_str = ", ".join(sorted(SCOPE_LABELS))
    domain_str = ", ".join(sorted(DOMAIN_LABELS))

    return f"""You are a label classifier for GitHub issues.

Given an issue title and optional description, select the most relevant labels from the PREDEFINED LIST below.

PREDEFINED LABELS (select ONLY from this list):

Type labels (pick exactly ONE):
  {type_str}

Scope labels (pick all that apply):
  {scope_str}

Domain labels (pick all that apply):
  {domain_str}

Rules:
1. Always include "ai-generated".
2. Include exactly ONE type label. If unsure, default to "feature".
3. Include all applicable scope and domain labels.
4. Do NOT invent labels outside the predefined list: {LABELS}
5. Return a JSON object with a single key "labels" containing an array of strings.

Example output:
{{"labels": ["ai-generated", "enhancement", "backend", "performance"]}}

Output raw JSON ONLY. No markdown fences, no explanation."""


LABEL_CLASSIFICATION_SYSTEM_PROMPT: str = _build_system_prompt()


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
