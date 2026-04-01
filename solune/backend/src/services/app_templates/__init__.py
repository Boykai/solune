"""App template library — discovery, loading, rendering."""

from src.services.app_templates.loader import load_template
from src.services.app_templates.registry import (
    discover_templates,
    get_template,
    list_templates,
)
from src.services.app_templates.renderer import render_template

__all__ = [
    "discover_templates",
    "get_template",
    "list_templates",
    "load_template",
    "render_template",
]
