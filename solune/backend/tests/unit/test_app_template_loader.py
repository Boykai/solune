"""Tests for src.services.app_templates.loader — template loading from disk."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.app_templates.loader import load_template


def _make_template_dir(tmp_path: Path, meta: dict | None = None) -> Path:
    """Create a minimal template directory with template.json."""
    tdir = tmp_path / "my-template"
    tdir.mkdir()

    if meta is None:
        meta = {
            "id": "test-template",
            "name": "Test Template",
            "description": "A test template",
            "category": "api",
            "difficulty": "S",
            "tech_stack": ["python"],
            "scaffold_type": "skeleton",
            "recommended_preset_id": "github-readonly",
            "iac_target": "none",
            "files": [
                {"source": "main.py", "target": "src/main.py", "variables": ["app_name"]},
            ],
        }
    (tdir / "template.json").write_text(json.dumps(meta))
    return tdir


class TestLoadTemplate:
    def test_loads_valid_template(self, tmp_path: Path) -> None:
        tdir = _make_template_dir(tmp_path)
        template = load_template(tdir)
        assert template.id == "test-template"
        assert template.name == "Test Template"
        assert template.category.value == "api"
        assert template.difficulty == "S"
        assert len(template.files) == 1
        assert template.files[0].source == "main.py"
        assert template.files[0].target == "src/main.py"

    def test_raises_when_template_json_missing(self, tmp_path: Path) -> None:
        tdir = tmp_path / "empty-dir"
        tdir.mkdir()
        with pytest.raises(FileNotFoundError, match=r"template\.json not found"):
            load_template(tdir)

    def test_raises_on_invalid_category(self, tmp_path: Path) -> None:
        meta = {
            "id": "bad-cat",
            "name": "Bad",
            "category": "invalid-category",
            "difficulty": "S",
            "tech_stack": ["python"],
            "scaffold_type": "skeleton",
            "recommended_preset_id": "github-readonly",
            "files": [{"source": "a.py", "target": "a.py"}],
        }
        tdir = _make_template_dir(tmp_path, meta)
        with pytest.raises(ValueError):
            load_template(tdir)

    def test_raises_on_invalid_difficulty(self, tmp_path: Path) -> None:
        meta = {
            "id": "bad-diff",
            "name": "Bad",
            "category": "api",
            "difficulty": "XXL",
            "tech_stack": ["python"],
            "scaffold_type": "skeleton",
            "recommended_preset_id": "github-readonly",
            "files": [{"source": "a.py", "target": "a.py"}],
        }
        tdir = _make_template_dir(tmp_path, meta)
        with pytest.raises(ValueError, match="difficulty"):
            load_template(tdir)

    def test_sets_base_dir(self, tmp_path: Path) -> None:
        tdir = _make_template_dir(tmp_path)
        template = load_template(tdir)
        assert template._base_dir == str(tdir)

    def test_default_iac_target_is_none(self, tmp_path: Path) -> None:
        meta = {
            "id": "no-iac",
            "name": "No IaC",
            "category": "api",
            "difficulty": "S",
            "tech_stack": ["python"],
            "scaffold_type": "skeleton",
            "recommended_preset_id": "github-readonly",
            "files": [{"source": "a.py", "target": "a.py"}],
        }
        tdir = _make_template_dir(tmp_path, meta)
        template = load_template(tdir)
        assert template.iac_target.value == "none"

    def test_empty_description_defaults(self, tmp_path: Path) -> None:
        meta = {
            "id": "no-desc",
            "name": "No Desc",
            "category": "api",
            "difficulty": "S",
            "tech_stack": ["python"],
            "scaffold_type": "skeleton",
            "recommended_preset_id": "github-readonly",
            "files": [{"source": "a.py", "target": "a.py"}],
        }
        tdir = _make_template_dir(tmp_path, meta)
        template = load_template(tdir)
        assert template.description == ""
