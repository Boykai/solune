"""Unit tests for app template registry, loader, renderer, and path-traversal validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.models.app_template import (
    AppCategory,
    AppTemplate,
    ScaffoldType,
    TemplateFile,
)
from src.services.app_templates.loader import load_template
from src.services.app_templates.registry import (
    _TEMPLATES_DIR,
    discover_templates,
    get_template,
    list_templates,
    reload_templates,
)
from src.services.app_templates.renderer import (
    _substitute,
    _validate_path_boundary,
    render_template,
    render_template_from,
)

# ── Model Tests ─────────────────────────────────────────────────────────


class TestAppTemplateModel:
    def test_valid_template(self) -> None:
        t = AppTemplate(
            id="test-template",
            name="Test",
            description="A test template",
            category=AppCategory.API,
            difficulty="M",
            tech_stack=["python"],
            scaffold_type=ScaffoldType.SKELETON,
            files=[TemplateFile(source="f.tmpl", target="f.py", variables=[])],
            recommended_preset_id="spec-kit",
        )
        assert t.id == "test-template"
        assert t.category == AppCategory.API

    def test_invalid_kebab_case(self) -> None:
        with pytest.raises(ValueError, match="kebab-case"):
            AppTemplate(
                id="InvalidCase",
                name="Bad",
                description="",
                category=AppCategory.API,
                difficulty="S",
                tech_stack=["x"],
                scaffold_type=ScaffoldType.SKELETON,
                files=[TemplateFile(source="a", target="b", variables=[])],
                recommended_preset_id="github",
            )

    def test_empty_tech_stack(self) -> None:
        with pytest.raises(ValueError, match="tech_stack"):
            AppTemplate(
                id="empty-stack",
                name="Bad",
                description="",
                category=AppCategory.CLI,
                difficulty="S",
                tech_stack=[],
                scaffold_type=ScaffoldType.SKELETON,
                files=[TemplateFile(source="a", target="b", variables=[])],
                recommended_preset_id="github",
            )

    def test_empty_files(self) -> None:
        with pytest.raises(ValueError, match="files"):
            AppTemplate(
                id="empty-files",
                name="Bad",
                description="",
                category=AppCategory.CLI,
                difficulty="S",
                tech_stack=["python"],
                scaffold_type=ScaffoldType.SKELETON,
                files=[],
                recommended_preset_id="github",
            )


class TestTemplateFile:
    def test_path_traversal_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not contain"):
            TemplateFile(source="a.tmpl", target="../escape.py", variables=[])

    def test_absolute_path_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not be absolute"):
            TemplateFile(source="a.tmpl", target="/etc/passwd", variables=[])

    def test_valid_nested_path(self) -> None:
        f = TemplateFile(source="a.tmpl", target="src/main.py", variables=["app_name"])
        assert f.target == "src/main.py"


# ── Loader Tests ────────────────────────────────────────────────────────


class TestLoader:
    def test_load_template_success(self, tmp_path: Path) -> None:
        meta = {
            "id": "my-tmpl",
            "name": "My Template",
            "description": "test desc",
            "category": "api",
            "difficulty": "M",
            "tech_stack": ["python"],
            "scaffold_type": "skeleton",
            "recommended_preset_id": "spec-kit",
            "iac_target": "none",
            "files": [
                {"source": "files/main.py.tmpl", "target": "main.py", "variables": ["app_name"]}
            ],
        }
        (tmp_path / "template.json").write_text(json.dumps(meta))
        t = load_template(tmp_path)
        assert t.id == "my-tmpl"
        assert t.name == "My Template"
        assert len(t.files) == 1

    def test_load_template_missing_json(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_template(tmp_path)


# ── Registry Tests ──────────────────────────────────────────────────────


class TestRegistry:
    def setup_method(self) -> None:
        reload_templates()

    def test_discover_templates_finds_all(self) -> None:
        templates = discover_templates(_TEMPLATES_DIR)
        assert len(templates) == 4
        assert "saas-react-fastapi" in templates
        assert "api-fastapi" in templates
        assert "cli-python" in templates
        assert "dashboard-react" in templates

    def test_get_template_returns_correct(self) -> None:
        t = get_template("cli-python")
        assert t is not None
        assert t.name == "CLI \u2014 Python"
        assert t.category == AppCategory.CLI

    def test_get_template_returns_none_for_unknown(self) -> None:
        assert get_template("nonexistent") is None

    def test_list_templates_all(self) -> None:
        templates = list_templates()
        assert len(templates) == 4

    def test_list_templates_with_category_filter(self) -> None:
        templates = list_templates(category=AppCategory.API)
        assert len(templates) == 1
        assert templates[0].id == "api-fastapi"

    def test_list_templates_empty_category(self) -> None:
        # No templates in a category that doesn't match any
        templates = list_templates(category=AppCategory.SAAS)
        assert len(templates) == 1
        assert templates[0].category == AppCategory.SAAS

    def test_to_summary_dict(self) -> None:
        t = get_template("api-fastapi")
        assert t is not None
        d = t.to_summary_dict()
        assert d["id"] == "api-fastapi"
        assert "files" not in d  # summaries don't include files

    def test_to_detail_dict(self) -> None:
        t = get_template("api-fastapi")
        assert t is not None
        d = t.to_detail_dict()
        assert "files" in d
        assert d["recommended_preset_id"] == "spec-kit"

    def test_discover_templates_empty_for_missing_dir(self, tmp_path: Path) -> None:
        """discover_templates returns empty dict when base_dir does not exist."""
        result = discover_templates(tmp_path / "nonexistent")
        assert result == {}

    def test_discover_templates_skips_files_without_template_json(self, tmp_path: Path) -> None:
        """Directories without template.json are silently skipped."""
        (tmp_path / "no-meta").mkdir()
        (tmp_path / "no-meta" / "README.md").write_text("Not a template")
        result = discover_templates(tmp_path)
        assert len(result) == 0

    def test_discover_templates_skips_plain_files(self, tmp_path: Path) -> None:
        """Non-directory entries in the base dir are ignored."""
        (tmp_path / "stray-file.txt").write_text("not a dir")
        result = discover_templates(tmp_path)
        assert len(result) == 0

    def test_discover_templates_handles_malformed_json(self, tmp_path: Path) -> None:
        """A directory with invalid template.json is skipped without crashing."""
        bad_dir = tmp_path / "bad-template"
        bad_dir.mkdir()
        (bad_dir / "template.json").write_text("{invalid json}")
        result = discover_templates(tmp_path)
        assert len(result) == 0

    def test_templates_dir_resolves_to_real_directory(self) -> None:
        """_TEMPLATES_DIR should point to the actual templates/app-templates/ directory."""
        assert _TEMPLATES_DIR.is_dir(), f"Expected {_TEMPLATES_DIR} to exist"
        subdirs = [p.name for p in _TEMPLATES_DIR.iterdir() if p.is_dir()]
        assert len(subdirs) >= 4, f"Expected at least 4 template dirs, found {subdirs}"

    def test_reload_templates_clears_cache(self) -> None:
        """Calling reload_templates clears the cache so next access re-scans disk."""
        t1 = get_template("api-fastapi")
        assert t1 is not None
        reload_templates()
        t2 = get_template("api-fastapi")
        assert t2 is not None
        # Both are valid, but t2 comes from a fresh scan
        assert t1.id == t2.id

    def test_list_templates_returns_list_not_dict_values(self) -> None:
        """list_templates returns a proper list, not a dict_values view."""
        result = list_templates()
        assert isinstance(result, list)
        assert all(isinstance(t, AppTemplate) for t in result)

    def test_discovered_templates_sorted_deterministically(self) -> None:
        """Templates should be discovered in sorted order by directory name."""
        templates = discover_templates(_TEMPLATES_DIR)
        ids = list(templates.keys())
        assert ids == sorted(ids), f"Template IDs should be sorted, got {ids}"


# ── Renderer Tests ──────────────────────────────────────────────────────


class TestSubstitution:
    def test_simple_substitution(self) -> None:
        result = _substitute("Hello {{name}}!", {"name": "World"})
        assert result == "Hello World!"

    def test_multiple_variables(self) -> None:
        result = _substitute("{{a}} and {{b}}", {"a": "X", "b": "Y"})
        assert result == "X and Y"

    def test_undefined_variable_raises(self) -> None:
        with pytest.raises(ValueError, match="Undefined template variable"):
            _substitute("{{missing}}", {})

    def test_no_variables(self) -> None:
        result = _substitute("plain text", {})
        assert result == "plain text"


class TestPathBoundary:
    def test_valid_path(self, tmp_path: Path) -> None:
        valid = (tmp_path / "sub" / "file.py").resolve()
        _validate_path_boundary(valid, str(tmp_path), "sub/file.py")

    def test_traversal_blocked(self, tmp_path: Path) -> None:
        escaped = (tmp_path / ".." / "escape.py").resolve()
        with pytest.raises(ValueError, match="Path traversal blocked"):
            _validate_path_boundary(escaped, str(tmp_path), "../escape.py")


class TestRenderer:
    def setup_method(self) -> None:
        reload_templates()

    def test_render_template_success(self, tmp_path: Path) -> None:
        files = render_template(
            "cli-python",
            {"app_name": "my-tool", "description": "A CLI tool"},
            tmp_path,
        )
        assert len(files) == 3
        readme = (tmp_path / "README.md").read_text()
        assert "my-tool" in readme
        assert "A CLI tool" in readme

    def test_render_template_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Template not found"):
            render_template("nonexistent", {}, tmp_path)

    def test_render_rejects_path_traversal_in_target(self, tmp_path: Path) -> None:
        """Ensure path traversal in rendered target path is blocked at render time.

        TemplateFile model validation catches '..', so we test the renderer's
        realpath boundary check by using a symlink that escapes the target dir.
        """
        tmpl_dir = tmp_path / "evil-tmpl"
        tmpl_dir.mkdir()
        files_dir = tmpl_dir / "files"
        files_dir.mkdir()
        (files_dir / "evil.tmpl").write_text("pwned")

        out_dir = tmp_path / "output"
        out_dir.mkdir()

        # Create a symlink inside the output dir pointing outside it
        escape_dir = tmp_path / "escaped"
        escape_dir.mkdir()
        link_path = out_dir / "link"
        link_path.symlink_to(escape_dir)

        template = AppTemplate(
            id="evil-tmpl",
            name="Evil",
            description="",
            category=AppCategory.CLI,
            difficulty="S",
            tech_stack=["python"],
            scaffold_type=ScaffoldType.SKELETON,
            files=[TemplateFile(source="files/evil.tmpl", target="link/escape.py", variables=[])],
            recommended_preset_id="github",
            _base_dir=str(tmpl_dir),
        )

        with pytest.raises(ValueError, match="Path traversal blocked"):
            render_template_from(template, {}, out_dir)

    def test_render_rejects_absolute_target(self) -> None:
        with pytest.raises(ValueError, match="must not be absolute"):
            TemplateFile(source="a.tmpl", target="/etc/passwd", variables=[])

    def test_render_undefined_variable_fails(self, tmp_path: Path) -> None:
        """Template with variables but context missing them should fail."""
        # cli-python template has {{app_name}} and {{description}} variables
        with pytest.raises(ValueError, match="Undefined template variable"):
            render_template("cli-python", {}, tmp_path)
