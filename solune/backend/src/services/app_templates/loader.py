"""Template loader — reads template.json from disk and returns an AppTemplate."""

import json
import logging
from pathlib import Path

from src.models.app_template import (
    AppCategory,
    AppTemplate,
    IaCTarget,
    ScaffoldType,
    TemplateFile,
)

logger = logging.getLogger(__name__)


def load_template(template_dir: Path) -> AppTemplate:
    """Load an AppTemplate from a directory containing ``template.json``.

    Args:
        template_dir: Path to the template directory (must contain template.json).

    Returns:
        A validated ``AppTemplate`` instance.

    Raises:
        FileNotFoundError: If ``template.json`` is missing.
        ValueError: If the metadata is invalid.
    """
    meta_path = template_dir / "template.json"
    if not meta_path.exists():
        msg = f"template.json not found in {template_dir}"
        raise FileNotFoundError(msg)

    with meta_path.open() as fh:
        raw: dict = json.load(fh)

    files = [TemplateFile(**f) for f in raw.get("files", [])]

    template = AppTemplate(
        id=raw["id"],
        name=raw["name"],
        description=raw.get("description", ""),
        category=AppCategory(raw["category"]),
        difficulty=raw["difficulty"],
        tech_stack=raw["tech_stack"],
        scaffold_type=ScaffoldType(raw["scaffold_type"]),
        files=files,
        recommended_preset_id=raw["recommended_preset_id"],
        iac_target=IaCTarget(raw.get("iac_target", "none")),
        _base_dir=str(template_dir),
    )
    logger.debug("Loaded template %s from %s", template.id, template_dir)
    return template
