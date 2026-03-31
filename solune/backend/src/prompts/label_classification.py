"""Prompt templates for AI-assisted issue label classification."""

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


LABEL_CLASSIFICATION_SYSTEM_PROMPT = """You are an expert GitHub issue label classifier.

Choose labels that best match the issue title and description.

Rules:
- Select labels ONLY from the provided taxonomy.
- Return 1 primary type label.
- Return relevant scope and domain labels when clearly supported by the content.
- Do not invent labels.
- Do not include explanations.

Return raw JSON only in this exact shape:
{"labels": ["bug", "backend"]}
"""


def create_label_classification_prompt(title: str, description: str) -> list[dict[str, str]]:
    """Create prompt messages for issue label classification."""
    allowed_labels = ", ".join(f'"{label}"' for label in LABELS)
    type_labels = ", ".join(f'"{label}"' for label in _TYPE_LABELS if label in LABELS)
    scope_labels = ", ".join(f'"{label}"' for label in _SCOPE_LABELS if label in LABELS)
    domain_labels = ", ".join(f'"{label}"' for label in _DOMAIN_LABELS if label in LABELS)

    user_message = f"""Classify labels for this GitHub issue.

Title: {title}

Description:
{description or "(empty)"}

Allowed labels:
{allowed_labels}

Type labels:
{type_labels}

Scope labels:
{scope_labels}

Domain labels:
{domain_labels}
"""

    return [
        {"role": "system", "content": LABEL_CLASSIFICATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
