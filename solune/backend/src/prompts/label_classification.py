"""Prompt helpers for AI-assisted issue label classification."""

from src.constants import LABELS

_TYPE_LABELS = [
    "feature",
    "bug",
    "enhancement",
    "refactor",
    "documentation",
    "testing",
    "infrastructure",
]
_SCOPE_LABELS = ["frontend", "backend", "database", "api"]
_DOMAIN_LABELS = ["security", "performance", "accessibility", "ux"]
_ALWAYS_INCLUDED_LABEL = "ai-generated"


def _supported_labels(candidates: list[str]) -> list[str]:
    """Return labels that are still present in the global taxonomy."""
    return [label for label in candidates if label in LABELS]


def build_label_classification_messages(
    title: str,
    description: str = "",
) -> list[dict[str, str]]:
    """Build prompt messages for issue label classification."""
    type_labels = _supported_labels(_TYPE_LABELS)
    scope_labels = _supported_labels(_SCOPE_LABELS)
    domain_labels = _supported_labels(_DOMAIN_LABELS)

    user_content = f"Title: {title.strip() or '(untitled)'}"
    if description.strip():
        user_content += f"\nDescription:\n{description.strip()}"

    system_content = f"""You classify GitHub issue labels for Solune.

Return raw JSON only in this shape:
{{"labels": ["ai-generated", "feature"]}}

Rules:
- Use ONLY labels from the categories below.
- Always include "{_ALWAYS_INCLUDED_LABEL}".
- Include EXACTLY ONE type label.
- Include any applicable scope and domain labels.
- Omit labels that are not clearly supported by the title/description.
- Do not include explanations or markdown fences.

Allowed labels:
Type labels: {", ".join(type_labels)}
Scope labels: {", ".join(scope_labels)}
Domain labels: {", ".join(domain_labels)}
Always include: {_ALWAYS_INCLUDED_LABEL}
"""

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
