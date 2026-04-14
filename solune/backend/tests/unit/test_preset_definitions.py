"""Unit tests for built-in pipeline preset definitions.

Validates that _PRESET_DEFINITIONS matches the required pipeline presets:
GitHub, Spec Kit, Default, and App Builder — each with a single 'In progress'
stage where all agents are in Group 1.
"""

from __future__ import annotations

from typing import ClassVar

import pytest

from src.services.pipelines.service import _PRESET_DEFINITIONS


def _find_preset(preset_id: str) -> dict:
    """Return a preset by its preset_id or fail."""
    for preset in _PRESET_DEFINITIONS:
        if preset["preset_id"] == preset_id:
            return preset
    pytest.fail(f"Preset {preset_id!r} not found in _PRESET_DEFINITIONS")


def _get_agents(preset: dict) -> list[dict]:
    """Return the flat list of agents from the single stage's single group."""
    stages = preset["stages"]
    assert len(stages) == 1, f"Expected 1 stage, got {len(stages)}"
    groups = stages[0]["groups"]
    assert len(groups) == 1, f"Expected 1 group, got {len(groups)}"
    return groups[0]["agents"]


class TestPresetDefinitionsStructure:
    """Verify _PRESET_DEFINITIONS contains exactly the 4 required presets."""

    def test_exactly_four_presets(self) -> None:
        assert len(_PRESET_DEFINITIONS) == 4

    def test_preset_ids(self) -> None:
        ids = {p["preset_id"] for p in _PRESET_DEFINITIONS}
        assert ids == {"github", "spec-kit", "default", "app-builder"}

    def test_preset_ids_unique(self) -> None:
        ids = [p["preset_id"] for p in _PRESET_DEFINITIONS]
        assert len(ids) == len(set(ids))

    def test_all_presets_have_required_fields(self) -> None:
        for preset in _PRESET_DEFINITIONS:
            assert "preset_id" in preset
            assert "name" in preset
            assert "description" in preset
            assert "stages" in preset

    def test_all_stages_named_in_progress(self) -> None:
        """Every preset must have a single stage named 'In progress'."""
        for preset in _PRESET_DEFINITIONS:
            stages = preset["stages"]
            assert len(stages) == 1, (
                f"Preset {preset['preset_id']!r} has {len(stages)} stages, expected 1"
            )
            assert stages[0]["name"] == "In progress", (
                f"Preset {preset['preset_id']!r} stage name is {stages[0]['name']!r}"
            )

    def test_all_stages_have_single_group(self) -> None:
        """Each stage must contain exactly one execution group (Group 1)."""
        for preset in _PRESET_DEFINITIONS:
            groups = preset["stages"][0]["groups"]
            assert len(groups) == 1, (
                f"Preset {preset['preset_id']!r} has {len(groups)} groups, expected 1"
            )


class TestGitHubPreset:
    """Verify the GitHub preset: single agent — GitHub Copilot."""

    def test_name(self) -> None:
        preset = _find_preset("github")
        assert preset["name"] == "GitHub"

    def test_single_agent(self) -> None:
        agents = _get_agents(_find_preset("github"))
        assert len(agents) == 1

    def test_agent_slug(self) -> None:
        agents = _get_agents(_find_preset("github"))
        assert agents[0]["agent_slug"] == "copilot"

    def test_agent_display_name(self) -> None:
        agents = _get_agents(_find_preset("github"))
        assert agents[0]["agent_display_name"] == "GitHub Copilot"


class TestSpecKitPreset:
    """Verify the Spec Kit preset: 5 speckit agents in correct order."""

    def test_name(self) -> None:
        preset = _find_preset("spec-kit")
        assert preset["name"] == "Spec Kit"

    def test_agent_count(self) -> None:
        agents = _get_agents(_find_preset("spec-kit"))
        assert len(agents) == 5

    def test_agent_slugs_in_order(self) -> None:
        agents = _get_agents(_find_preset("spec-kit"))
        slugs = [a["agent_slug"] for a in agents]
        assert slugs == [
            "speckit.specify",
            "speckit.plan",
            "speckit.tasks",
            "speckit.analyze",
            "speckit.implement",
        ]


class TestDefaultPreset:
    """Verify the Default preset: speckit agents + QA, tester, linter, review, judge."""

    def test_name(self) -> None:
        preset = _find_preset("default")
        assert preset["name"] == "Default"

    def test_agent_count(self) -> None:
        agents = _get_agents(_find_preset("default"))
        assert len(agents) == 10

    def test_agent_slugs_in_order(self) -> None:
        agents = _get_agents(_find_preset("default"))
        slugs = [a["agent_slug"] for a in agents]
        assert slugs == [
            "speckit.specify",
            "speckit.plan",
            "speckit.tasks",
            "speckit.analyze",
            "speckit.implement",
            "quality-assurance",
            "tester",
            "linter",
            "copilot-review",
            "judge",
        ]


class TestAppBuilderPreset:
    """Verify the App Builder preset: speckit + architect + QA suite."""

    def test_name(self) -> None:
        preset = _find_preset("app-builder")
        assert preset["name"] == "App Builder"

    def test_agent_count(self) -> None:
        agents = _get_agents(_find_preset("app-builder"))
        assert len(agents) == 11

    def test_agent_slugs_in_order(self) -> None:
        agents = _get_agents(_find_preset("app-builder"))
        slugs = [a["agent_slug"] for a in agents]
        assert slugs == [
            "speckit.specify",
            "speckit.plan",
            "speckit.tasks",
            "speckit.analyze",
            "speckit.implement",
            "architect",
            "quality-assurance",
            "tester",
            "linter",
            "copilot-review",
            "judge",
        ]

    def test_architect_agent_present(self) -> None:
        agents = _get_agents(_find_preset("app-builder"))
        architect = [a for a in agents if a["agent_slug"] == "architect"]
        assert len(architect) == 1
        assert architect[0]["agent_display_name"] == "Architect"


class TestAgentNodeShape:
    """Verify that every agent node in every preset has the correct fields."""

    _REQUIRED_KEYS: ClassVar[set[str]] = {
        "id",
        "agent_slug",
        "agent_display_name",
        "model_id",
        "model_name",
        "tool_ids",
        "tool_count",
        "config",
    }

    def test_all_agents_have_required_keys(self) -> None:
        for preset in _PRESET_DEFINITIONS:
            for agent in _get_agents(preset):
                missing = self._REQUIRED_KEYS - set(agent.keys())
                assert not missing, (
                    f"Preset {preset['preset_id']!r}, agent {agent.get('id', '?')}: "
                    f"missing keys {missing}"
                )

    def test_all_agents_have_empty_model_id(self) -> None:
        """Auto mode: model_id should be empty string."""
        for preset in _PRESET_DEFINITIONS:
            for agent in _get_agents(preset):
                assert agent["model_id"] == "", (
                    f"Agent {agent['id']} should have model_id='' (Auto mode)"
                )

    def test_all_agents_have_unique_ids_within_preset(self) -> None:
        for preset in _PRESET_DEFINITIONS:
            agents = _get_agents(preset)
            ids = [a["id"] for a in agents]
            assert len(ids) == len(set(ids)), (
                f"Duplicate agent IDs in preset {preset['preset_id']!r}"
            )

    def test_all_agent_ids_globally_unique(self) -> None:
        """Agent IDs must be unique across ALL presets, not just within each one."""
        all_ids: list[str] = []
        for preset in _PRESET_DEFINITIONS:
            all_ids.extend(a["id"] for a in _get_agents(preset))
        assert len(all_ids) == len(set(all_ids)), "Duplicate agent IDs across presets"


class TestLegacyPresetIdsAbsent:
    """Verify that old/retired preset IDs are no longer in the definitions."""

    _RETIRED_IDS: ClassVar[list[str]] = [
        "easy",
        "medium",
        "hard",
        "expert",
        "github-copilot",
    ]

    def test_no_retired_preset_ids(self) -> None:
        current_ids = {p["preset_id"] for p in _PRESET_DEFINITIONS}
        for retired in self._RETIRED_IDS:
            assert retired not in current_ids, (
                f"Retired preset ID {retired!r} should not be in _PRESET_DEFINITIONS"
            )

    def test_retired_ids_not_in_any_name_field(self) -> None:
        """Ensure 'Easy', 'Medium', 'Hard', 'Expert' names are gone too."""
        retired_names = {"Easy", "Medium", "Hard", "Expert"}
        current_names = {p["name"] for p in _PRESET_DEFINITIONS}
        overlap = retired_names & current_names
        assert not overlap, f"Retired preset names still present: {overlap}"


class TestHelperFunctions:
    """Verify _agent() and _grouped_stage() produce correct dict shapes."""

    def test_agent_helper_returns_correct_keys(self) -> None:
        from src.services.pipelines.service import _agent

        result = _agent("test-id", "test-slug", "Test Display")
        assert result == {
            "id": "test-id",
            "agent_slug": "test-slug",
            "agent_display_name": "Test Display",
            "model_id": "",
            "model_name": "",
            "tool_ids": [],
            "tool_count": 0,
            "config": {},
        }

    def test_grouped_stage_returns_correct_structure(self) -> None:
        from src.services.pipelines.service import _agent, _grouped_stage

        agents = [_agent("a1", "copilot", "Copilot")]
        result = _grouped_stage("s1", "In progress", 0, "g1", agents)
        assert result["id"] == "s1"
        assert result["name"] == "In progress"
        assert result["order"] == 0
        assert len(result["groups"]) == 1
        assert result["groups"][0]["id"] == "g1"
        assert result["groups"][0]["order"] == 0
        assert result["groups"][0]["execution_mode"] == "sequential"
        assert result["groups"][0]["agents"] == agents
        # Backward compat: flattened agents at stage level
        assert result["agents"] == agents
        assert result["execution_mode"] == "sequential"

    def test_grouped_stage_custom_execution_mode(self) -> None:
        from src.services.pipelines.service import _grouped_stage

        result = _grouped_stage("s1", "Build", 0, "g1", [], mode="parallel")
        assert result["groups"][0]["execution_mode"] == "parallel"
