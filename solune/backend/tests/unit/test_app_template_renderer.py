"""Tests for src.services.app_templates.renderer — template rendering with variable substitution."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.models.app_template import (
    AppCategory,
    AppTemplate,
    IaCTarget,
    ScaffoldType,
    TemplateFile,
)
from src.services.app_templates.renderer import (
    _substitute,
    _validate_path_boundary,
    render_template_from,
)


def _make_template(tmp_path: Path, files: list[dict] | None = None) -> AppTemplate:
    """Create a minimal AppTemplate with source files on disk."""
    base_dir = tmp_path / "templates" / "test-tpl"
    base_dir.mkdir(parents=True)

    if files is None:
        files = [{"source": "main.py.tpl", "target": "src/{{app_name}}/main.py"}]

    template_files = []
    for f in files:
        src_path = base_dir / f["source"]
        src_path.parent.mkdir(parents=True, exist_ok=True)
        src_path.write_text(f.get("content", "# {{app_name}} app\nprint('Hello {{app_name}}')\n"))
        template_files.append(TemplateFile(source=f["source"], target=f["target"]))

    return AppTemplate(
        id="test-tpl",
        name="Test Template",
        description="A test template",
        category=AppCategory.API,
        difficulty="S",
        tech_stack=["python"],
        scaffold_type=ScaffoldType.SKELETON,
        files=template_files,
        recommended_preset_id="github-readonly",
        iac_target=IaCTarget.NONE,
        _base_dir=str(base_dir),
    )


class TestSubstitute:
    def test_replaces_single_variable(self) -> None:
        result = _substitute("Hello {{name}}!", {"name": "World"})
        assert result == "Hello World!"

    def test_replaces_multiple_variables(self) -> None:
        result = _substitute("{{a}} and {{b}}", {"a": "X", "b": "Y"})
        assert result == "X and Y"

    def test_no_variables_passes_through(self) -> None:
        result = _substitute("plain text", {})
        assert result == "plain text"

    def test_undefined_variable_raises(self) -> None:
        with pytest.raises(ValueError, match="Undefined template variable: missing"):
            _substitute("Hello {{missing}}", {})

    def test_repeated_variable_replaced(self) -> None:
        result = _substitute("{{x}} + {{x}}", {"x": "1"})
        assert result == "1 + 1"


class TestValidatePathBoundary:
    def test_path_within_boundary_passes(self, tmp_path: Path) -> None:
        boundary = str(tmp_path)
        path = tmp_path / "sub" / "file.txt"
        _validate_path_boundary(path, boundary, "sub/file.txt")

    def test_path_traversal_blocked(self, tmp_path: Path) -> None:
        boundary = str(tmp_path / "target")
        escaped = (tmp_path / "target" / ".." / "other" / "file.txt").resolve()
        with pytest.raises(ValueError, match="Path traversal blocked"):
            _validate_path_boundary(escaped, boundary, "../other/file.txt")


class TestRenderTemplateFrom:
    def test_renders_single_file(self, tmp_path: Path) -> None:
        template = _make_template(tmp_path)
        target_dir = tmp_path / "output"
        context = {"app_name": "myapp"}

        created = render_template_from(template, context, target_dir)
        assert len(created) == 1
        content = created[0].read_text()
        assert "myapp" in content
        assert "{{app_name}}" not in content

    def test_auto_derives_python_package_name(self, tmp_path: Path) -> None:
        template = _make_template(
            tmp_path,
            files=[
                {
                    "source": "init.py.tpl",
                    "target": "{{python_package_name}}/__init__.py",
                    "content": "# Package: {{python_package_name}}",
                }
            ],
        )
        target_dir = tmp_path / "output"
        context = {"app_name": "my-cool-app"}

        created = render_template_from(template, context, target_dir)
        assert len(created) == 1
        assert "my_cool_app" in str(created[0])
        content = created[0].read_text()
        assert "my_cool_app" in content

    def test_renders_multiple_files(self, tmp_path: Path) -> None:
        template = _make_template(
            tmp_path,
            files=[
                {"source": "a.txt", "target": "a.txt", "content": "File A {{app_name}}"},
                {"source": "b.txt", "target": "b.txt", "content": "File B {{app_name}}"},
            ],
        )
        target_dir = tmp_path / "output"
        created = render_template_from(template, {"app_name": "test"}, target_dir)
        assert len(created) == 2

    def test_missing_source_file_raises(self, tmp_path: Path) -> None:
        template = _make_template(tmp_path)
        # Delete the source file
        src = Path(template._base_dir) / "main.py.tpl"
        src.unlink()

        target_dir = tmp_path / "output"
        with pytest.raises(ValueError, match="Template source file missing"):
            render_template_from(template, {"app_name": "test"}, target_dir)

    def test_invalid_base_dir_raises(self, tmp_path: Path) -> None:
        template = _make_template(tmp_path)
        # Replace _base_dir with nonexistent path via a new instance
        bad_template = AppTemplate(
            id="test-tpl",
            name="Test Template",
            description="A test template",
            category=AppCategory.API,
            difficulty="S",
            tech_stack=["python"],
            scaffold_type=ScaffoldType.SKELETON,
            files=template.files,
            recommended_preset_id="github-readonly",
            _base_dir="/nonexistent/path",
        )
        target_dir = tmp_path / "output"
        with pytest.raises(ValueError, match="Template base directory does not exist"):
            render_template_from(bad_template, {"app_name": "test"}, target_dir)
