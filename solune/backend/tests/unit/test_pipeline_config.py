"""Unit tests for pipeline auto-configuration."""

from __future__ import annotations

from src.models.app_template import (
    AppCategory,
    AppTemplate,
    IaCTarget,
    ScaffoldType,
    TemplateFile,
)
from src.services.pipelines.pipeline_config import (
    DIFFICULTY_PRESET_MAP,
    configure_pipeline_preset,
)


def _make_template(
    difficulty: str = "M",
    iac_target: IaCTarget = IaCTarget.NONE,
) -> AppTemplate:
    """Create a minimal template for testing."""
    return AppTemplate(
        id="test-template",
        name="Test",
        description="",
        category=AppCategory.API,
        difficulty=difficulty,
        tech_stack=["python"],
        scaffold_type=ScaffoldType.SKELETON,
        files=[TemplateFile(source="f.tmpl", target="f.py", variables=[])],
        recommended_preset_id="medium",
        iac_target=iac_target,
    )


class TestConfigurePipelinePreset:
    def test_difficulty_s_maps_to_easy(self) -> None:
        t = _make_template(difficulty="S")
        preset_id, _ = configure_pipeline_preset(t)
        assert preset_id == "easy"

    def test_difficulty_m_maps_to_medium(self) -> None:
        t = _make_template(difficulty="M")
        preset_id, _ = configure_pipeline_preset(t)
        assert preset_id == "medium"

    def test_difficulty_l_maps_to_hard(self) -> None:
        t = _make_template(difficulty="L")
        preset_id, _ = configure_pipeline_preset(t)
        assert preset_id == "hard"

    def test_difficulty_xl_maps_to_expert(self) -> None:
        t = _make_template(difficulty="XL")
        preset_id, _ = configure_pipeline_preset(t)
        assert preset_id == "expert"

    def test_difficulty_override(self) -> None:
        t = _make_template(difficulty="S")
        preset_id, _ = configure_pipeline_preset(t, difficulty_override="XL")
        assert preset_id == "expert"

    def test_include_architect_when_iac_target_set(self) -> None:
        t = _make_template(iac_target=IaCTarget.AZURE)
        _, include = configure_pipeline_preset(t)
        assert include is True

    def test_no_architect_when_iac_target_none(self) -> None:
        t = _make_template(iac_target=IaCTarget.NONE)
        _, include = configure_pipeline_preset(t)
        assert include is False

    def test_architect_with_docker_target(self) -> None:
        t = _make_template(iac_target=IaCTarget.DOCKER)
        _, include = configure_pipeline_preset(t)
        assert include is True

    def test_architect_with_aws_target(self) -> None:
        t = _make_template(iac_target=IaCTarget.AWS)
        _, include = configure_pipeline_preset(t)
        assert include is True

    def test_unknown_difficulty_defaults_to_medium(self) -> None:
        _make_template(difficulty="M")
        # Modify difficulty to something unknown via object mutation
        # Since it's frozen, test the map directly
        assert DIFFICULTY_PRESET_MAP.get("UNKNOWN") is None
        # configure_pipeline_preset falls back to "medium"
        t2 = _make_template(difficulty="M")
        preset_id, _ = configure_pipeline_preset(t2, difficulty_override="UNKNOWN")
        assert preset_id == "medium"
