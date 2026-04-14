"""Unit tests verifying DIFFICULTY_PRESET_MAP consistency across modules.

Both agent_tools.py and pipeline_config.py define DIFFICULTY_PRESET_MAP.
These tests ensure the two maps stay in sync and reference valid preset IDs.
"""

from __future__ import annotations

from src.services.agent_tools import DIFFICULTY_PRESET_MAP as AGENT_TOOLS_MAP
from src.services.pipelines.pipeline_config import DIFFICULTY_PRESET_MAP as PIPELINE_CONFIG_MAP
from src.services.pipelines.service import _PRESET_DEFINITIONS

# The valid preset IDs are those defined in _PRESET_DEFINITIONS.
_VALID_PRESET_IDS = {p["preset_id"] for p in _PRESET_DEFINITIONS}


class TestDifficultyPresetMapConsistency:
    """Ensure the two DIFFICULTY_PRESET_MAP instances stay aligned."""

    def test_pipeline_config_map_values_are_valid_preset_ids(self) -> None:
        for difficulty, preset_id in PIPELINE_CONFIG_MAP.items():
            assert preset_id in _VALID_PRESET_IDS, (
                f"pipeline_config.DIFFICULTY_PRESET_MAP[{difficulty!r}] = {preset_id!r} "
                f"is not a valid preset ID. Valid: {_VALID_PRESET_IDS}"
            )

    def test_agent_tools_map_values_are_valid_preset_ids(self) -> None:
        for difficulty, preset_id in AGENT_TOOLS_MAP.items():
            assert preset_id in _VALID_PRESET_IDS, (
                f"agent_tools.DIFFICULTY_PRESET_MAP[{difficulty!r}] = {preset_id!r} "
                f"is not a valid preset ID. Valid: {_VALID_PRESET_IDS}"
            )

    def test_shared_keys_agree(self) -> None:
        """Keys present in both maps must map to the same preset."""
        shared = set(PIPELINE_CONFIG_MAP) & set(AGENT_TOOLS_MAP)
        for key in shared:
            assert PIPELINE_CONFIG_MAP[key] == AGENT_TOOLS_MAP[key], (
                f"Mismatch for difficulty {key!r}: "
                f"pipeline_config→{PIPELINE_CONFIG_MAP[key]!r}, "
                f"agent_tools→{AGENT_TOOLS_MAP[key]!r}"
            )

    def test_agent_tools_map_has_expected_keys(self) -> None:
        """agent_tools adds XS mapping; pipeline_config has S/M/L/XL."""
        assert "XS" in AGENT_TOOLS_MAP
        assert "S" in AGENT_TOOLS_MAP
        assert "M" in AGENT_TOOLS_MAP
        assert "L" in AGENT_TOOLS_MAP
        assert "XL" in AGENT_TOOLS_MAP

    def test_pipeline_config_map_mappings(self) -> None:
        """Verify the exact difficulty→preset mapping."""
        assert PIPELINE_CONFIG_MAP["S"] == "github"
        assert PIPELINE_CONFIG_MAP["M"] == "spec-kit"
        assert PIPELINE_CONFIG_MAP["L"] == "default"
        assert PIPELINE_CONFIG_MAP["XL"] == "app-builder"

    def test_pipeline_config_unknown_difficulty_defaults_to_default(self) -> None:
        """Unknown difficulty should not be in the map; fallback is 'default'."""
        assert PIPELINE_CONFIG_MAP.get("UNKNOWN") is None
