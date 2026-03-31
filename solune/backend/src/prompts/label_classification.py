"""Prompt builder for AI-powered issue label classification."""

from src.constants import LABELS

TYPE_LABELS = [
    "feature",
    "bug",
    "enhancement",
    "refactor",
    "documentation",
    "testing",
    "infrastructure",
]
SCOPE_LABELS = ["frontend", "backend", "database", "api"]
DOMAIN_LABELS = ["security", "performance", "accessibility", "ux"]
_EXCLUDED_LABELS = {
    "ai-generated",
    "sub-issue",
    "good first issue",
    "help wanted",
    "active",
    "stalled",
}
MAX_DESCRIPTION_LENGTH = 2000


def _available_labels(candidates: list[str]) -> list[str]:
    return [label for label in candidates if label in LABELS]


def build_label_classification_messages(
    title: str,
    description: str = "",
) -> list[dict[str, str]]:
    """Build chat messages that classify issue labels from the current taxonomy."""
    trimmed_title = title.strip()
    trimmed_description = description.strip()[:MAX_DESCRIPTION_LENGTH]

    type_labels = _available_labels(TYPE_LABELS)
    scope_labels = _available_labels(SCOPE_LABELS)
    domain_labels = _available_labels(DOMAIN_LABELS)
    categorized = {*type_labels, *scope_labels, *domain_labels}
    other_labels = [
        label for label in LABELS if label not in categorized and label not in _EXCLUDED_LABELS
    ]

    category_sections = [
        f"- Type labels (choose at most one): {', '.join(type_labels) or 'none'}",
        f"- Scope labels (choose any that apply): {', '.join(scope_labels) or 'none'}",
        f"- Domain labels (choose any that apply): {', '.join(domain_labels) or 'none'}",
    ]
    if other_labels:
        category_sections.append(
            f"- Other valid labels (choose only if clearly applicable): {', '.join(other_labels)}"
        )

    system_prompt = (
        "You classify GitHub issue labels.\n"
        'Return a raw JSON object with a single key named "labels" whose value is an array of '
        "lowercase label strings.\n"
        "Choose only labels from the taxonomy below.\n"
        'Do not include explanations, markdown, or any keys other than "labels".\n'
        "Do not include workflow/status labels such as ai-generated, sub-issue, good first issue, "
        "help wanted, active, or stalled.\n" + "\n".join(category_sections)
    )
    user_prompt = (
        "Classify labels for this issue.\n"
        f"Title: {trimmed_title}\n"
        f"Description:\n{trimmed_description or '(none)'}"
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
