"""Tests for src.services.tools.presets — static MCP preset catalog."""

from __future__ import annotations

import json

from src.services.tools.presets import list_mcp_presets


class TestListMcpPresets:
    def test_returns_non_empty_list(self) -> None:
        result = list_mcp_presets()
        assert result.count > 0
        assert len(result.presets) == result.count

    def test_all_presets_have_required_fields(self) -> None:
        result = list_mcp_presets()
        for preset in result.presets:
            assert preset.id, "id must not be empty"
            assert preset.name, "name must not be empty"
            assert preset.description, "description must not be empty"
            assert preset.category, "category must not be empty"
            assert preset.icon, "icon must not be empty"
            assert preset.config_content, "config_content must not be empty"

    def test_config_content_is_valid_json(self) -> None:
        result = list_mcp_presets()
        for preset in result.presets:
            parsed = json.loads(preset.config_content)
            assert "mcpServers" in parsed, f"Preset {preset.id} missing mcpServers key"

    def test_preset_ids_are_unique(self) -> None:
        result = list_mcp_presets()
        ids = [p.id for p in result.presets]
        assert len(ids) == len(set(ids)), "Preset IDs must be unique"

    def test_github_readonly_preset_exists(self) -> None:
        result = list_mcp_presets()
        ids = {p.id for p in result.presets}
        assert "github-readonly" in ids

    def test_github_full_preset_exists(self) -> None:
        result = list_mcp_presets()
        ids = {p.id for p in result.presets}
        assert "github-full" in ids

    def test_azure_preset_exists(self) -> None:
        result = list_mcp_presets()
        ids = {p.id for p in result.presets}
        assert "azure" in ids

    def test_categories_are_valid_strings(self) -> None:
        result = list_mcp_presets()
        for preset in result.presets:
            assert isinstance(preset.category, str)
            assert len(preset.category) > 0

    def test_config_content_ends_with_newline(self) -> None:
        result = list_mcp_presets()
        for preset in result.presets:
            assert preset.config_content.endswith("\n"), (
                f"Preset {preset.id} config should end with newline"
            )
