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
2. Include exactly ONE type label. If unsure, default to "enhancement".
3. Include all applicable scope and domain labels.
4. Do NOT invent labels outside the predefined list: {LABELS}
5. Return a JSON object with a single key "labels" containing an array of strings.

Example output:
{{"labels": ["ai-generated", "enhancement", "backend", "performance"]}}

Output raw JSON ONLY. No markdown fences, no explanation."""


LABEL_CLASSIFICATION_SYSTEM_PROMPT: str = _build_system_prompt()


def _build_system_prompt_with_priority() -> str:
    """Build the system prompt with optional priority detection."""
    type_str = ", ".join(sorted(TYPE_LABELS))
    scope_str = ", ".join(sorted(SCOPE_LABELS))
    domain_str = ", ".join(sorted(DOMAIN_LABELS))

    return f"""You are a label classifier for GitHub issues.

Given an issue title and optional description, select the most relevant labels from the PREDEFINED LIST below. Also detect urgency signals and optionally return a priority.

PREDEFINED LABELS (select ONLY from this list):

Type labels (pick exactly ONE):
  {type_str}

Scope labels (pick all that apply):
  {scope_str}

Domain labels (pick all that apply):
  {domain_str}

PRIORITY DETECTION (optional):
- Return "P0" for: production outage, data loss, security breach, system-wide downtime
- Return "P1" for: critical bug, security vulnerability, major functionality broken
- If no urgency signals are detected, omit the "priority" key entirely (most issues)

Rules:
1. Always include "ai-generated".
2. Include exactly ONE type label. If unsure, default to "enhancement".
3. Include all applicable scope and domain labels.
4. Do NOT invent labels outside the predefined list: {LABELS}
5. Return a JSON object with keys "labels" (required) and "priority" (optional).
6. Only include "priority" when strong urgency signals are present in the title or description.

Example output (no urgency):
{{"labels": ["ai-generated", "enhancement", "backend", "performance"]}}

Example output (urgent):
{{"labels": ["ai-generated", "bug", "backend", "security"], "priority": "P0"}}

Output raw JSON ONLY. No markdown fences, no explanation."""


LABEL_CLASSIFICATION_WITH_PRIORITY_SYSTEM_PROMPT: str = _build_system_prompt_with_priority()


def _build_user_content(title: str, description: str = "") -> str:
    """Build the user message content shared by all label classification prompts."""
    desc = description[:_MAX_DESCRIPTION_LENGTH] if description else ""

    user_content = f"Title: {title}"
    if desc.strip():
        user_content += f"\n\nDescription:\n{desc}"
    return user_content


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
    return [
        {"role": "system", "content": LABEL_CLASSIFICATION_SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_content(title, description)},
    ]


def build_label_classification_with_priority_prompt(
    title: str,
    description: str = "",
) -> list[dict[str, str]]:
    """Build chat messages for label classification with optional priority.

    Same as :func:`build_label_classification_prompt` but uses the extended
    system prompt that includes urgency/priority detection rules.

    Args:
        title: Issue title (always included in full).
        description: Optional issue body, truncated to
            ``_MAX_DESCRIPTION_LENGTH`` characters.

    Returns:
        List of ``{"role": ..., "content": ...}`` message dicts.
    """
    return [
        {"role": "system", "content": LABEL_CLASSIFICATION_WITH_PRIORITY_SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_content(title, description)},
    ]
