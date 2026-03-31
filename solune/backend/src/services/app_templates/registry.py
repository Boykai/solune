"""Template registry — discovers, caches, and looks up templates on disk."""

import logging
from pathlib import Path

from src.models.app_template import AppCategory, AppTemplate
from src.services.app_templates.loader import load_template

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = (
    Path(__file__).resolve().parents[3] / "templates" / "app-templates"
)

_cache: dict[str, AppTemplate] | None = None


def _ensure_cache() -> dict[str, AppTemplate]:
    global _cache  # noqa: PLW0603
    if _cache is None:
        _cache = discover_templates(_TEMPLATES_DIR)
    return _cache


def discover_templates(base_dir: Path) -> dict[str, AppTemplate]:
    """Scan *base_dir* for template directories and return a mapping of id → template."""
    templates: dict[str, AppTemplate] = {}
    if not base_dir.is_dir():
        logger.warning("Templates directory does not exist: %s", base_dir)
        return templates

    for child in sorted(base_dir.iterdir()):
        if not child.is_dir():
            continue
        meta = child / "template.json"
        if not meta.exists():
            continue
        try:
            tmpl = load_template(child)
            templates[tmpl.id] = tmpl
            logger.debug("Discovered template: %s", tmpl.id)
        except Exception:
            logger.exception("Failed to load template from %s", child)

    logger.info("Discovered %d templates in %s", len(templates), base_dir)
    return templates


def get_template(template_id: str) -> AppTemplate | None:
    """Return a single template by *template_id*, or ``None`` if not found."""
    return _ensure_cache().get(template_id)


def list_templates(category: AppCategory | None = None) -> list[AppTemplate]:
    """Return all templates, optionally filtered by *category*."""
    cache = _ensure_cache()
    templates = list(cache.values())
    if category is not None:
        templates = [t for t in templates if t.category == category]
    return templates


def reload_templates() -> None:
    """Force re-scan of templates from disk (useful for testing)."""
    global _cache  # noqa: PLW0603
    _cache = None
