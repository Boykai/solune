"""Pipeline auto-configuration — maps template + difficulty to preset."""

from src.models.app_template import AppTemplate, IaCTarget

DIFFICULTY_PRESET_MAP: dict[str, str] = {
    "S": "easy",
    "M": "medium",
    "L": "hard",
    "XL": "expert",
}


def configure_pipeline_preset(
    template: AppTemplate,
    difficulty_override: str | None = None,
) -> tuple[str, bool]:
    """Determine pipeline preset and architect-agent inclusion.

    Args:
        template: The app template being used.
        difficulty_override: Optional override for the template's default difficulty.

    Returns:
        A ``(preset_id, include_architect)`` tuple.
    """
    difficulty = difficulty_override or template.difficulty
    preset_id = DIFFICULTY_PRESET_MAP.get(difficulty, "medium")
    include_architect = template.iac_target != IaCTarget.NONE
    return preset_id, include_architect
