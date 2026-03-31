"""Template renderer — substitutes ``{{var}}`` placeholders and writes files.

Security: all target paths are validated with ``os.path.realpath()`` to block
path-traversal attacks (R3 decision in research.md).
"""

import logging
import os
import re
from pathlib import Path

from src.models.app_template import AppTemplate
from src.services.app_templates.registry import get_template

logger = logging.getLogger(__name__)

_VAR_RE = re.compile(r"\{\{(\w+)\}\}")


def render_template(
    template_id: str,
    context: dict[str, str],
    target_dir: Path,
) -> list[Path]:
    """Render a template's files into *target_dir* with variable substitution.

    Args:
        template_id: Template identifier to render.
        context: Mapping of variable names to replacement values.
        target_dir: Destination directory for rendered files.

    Returns:
        List of created file paths.

    Raises:
        ValueError: If the template is not found, variables are undefined,
            or a target path escapes the boundary.
    """
    template = get_template(template_id)
    if template is None:
        msg = f"Template not found: {template_id}"
        raise ValueError(msg)

    return render_template_from(template, context, target_dir)


def render_template_from(
    template: AppTemplate,
    context: dict[str, str],
    target_dir: Path,
) -> list[Path]:
    """Render files from a loaded *template* instance into *target_dir*."""
    base_dir = Path(template._base_dir)  # noqa: SLF001
    if not base_dir.is_dir():
        msg = f"Template base directory does not exist: {base_dir}"
        raise ValueError(msg)

    target_dir = target_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    boundary = str(target_dir)

    created: list[Path] = []

    for tfile in template.files:
        # Substitute variables in the target path itself
        rendered_target = _substitute(tfile.target, context)
        out_path = (target_dir / rendered_target).resolve()
        _validate_path_boundary(out_path, boundary, rendered_target)

        # Read source template
        src_path = base_dir / tfile.source
        if not src_path.exists():
            msg = f"Template source file missing: {src_path}"
            raise ValueError(msg)

        content = src_path.read_text(encoding="utf-8")

        # Substitute variables in content
        rendered = _substitute(content, context)

        # Write rendered file
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
        created.append(out_path)
        logger.debug("Rendered %s → %s", tfile.source, out_path)

    logger.info(
        "Rendered %d files for template %s into %s",
        len(created),
        template.id,
        target_dir,
    )
    return created


def _substitute(text: str, context: dict[str, str]) -> str:
    """Replace all ``{{var}}`` placeholders with values from *context*."""

    def _replacer(m: re.Match[str]) -> str:
        var_name = m.group(1)
        if var_name not in context:
            msg = f"Undefined template variable: {var_name}"
            raise ValueError(msg)
        return context[var_name]

    return _VAR_RE.sub(_replacer, text)


def _validate_path_boundary(
    resolved: Path, boundary: str, original: str
) -> None:
    """Ensure *resolved* stays within *boundary*."""
    real = os.path.realpath(resolved)
    if not real.startswith(boundary + os.sep) and real != boundary:
        msg = f"Path traversal blocked: '{original}' resolves outside target directory"
        raise ValueError(msg)
