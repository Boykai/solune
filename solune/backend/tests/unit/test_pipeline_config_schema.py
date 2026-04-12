"""Unit tests for pipeline-config-schema.json contract.

Validates that the JSON Schema in contracts/pipeline-config-schema.json is:
- A well-formed JSON Schema Draft 7 document
- Consistent with the Pydantic models in src.models.pipeline
- Capable of validating all existing _PRESET_DEFINITIONS from PipelineService
- Correctly rejecting invalid pipeline data
- Loadable back into Pydantic models (round-trip fidelity)
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft7Validator, ValidationError, validate

from src.models.pipeline import (
    ExecutionGroup,
    PipelineAgentNode,
    PipelineStage,
)
from src.services.pipelines.service import _PRESET_DEFINITIONS

# Resolve the contracts directory relative to this test file.
# Layout: tests/unit/test_…py → backend/ → solune/ → (repo root) → contracts/
_CONTRACTS_DIR = Path(__file__).resolve().parents[4] / "contracts"
_SCHEMA_PATH = _CONTRACTS_DIR / "pipeline-config-schema.json"
_CLI_CONTRACT_PATH = _CONTRACTS_DIR / "fleet-dispatch-cli.yaml"


@pytest.fixture()
def schema() -> dict:
    """Load the pipeline config JSON Schema."""
    return json.loads(_SCHEMA_PATH.read_text())


@pytest.fixture()
def presets() -> list[dict]:
    """Return a deep copy of _PRESET_DEFINITIONS to avoid mutation across tests."""
    return copy.deepcopy(_PRESET_DEFINITIONS)


# ---------------------------------------------------------------------------
# Schema validity
# ---------------------------------------------------------------------------


class TestSchemaValidity:
    """Ensure the JSON Schema document itself is well-formed."""

    def test_schema_file_exists(self) -> None:
        assert _SCHEMA_PATH.exists(), f"Schema not found at {_SCHEMA_PATH}"

    def test_schema_is_valid_json(self) -> None:
        raw = _SCHEMA_PATH.read_text()
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)

    def test_schema_is_valid_draft7(self, schema: dict) -> None:
        Draft7Validator.check_schema(schema)

    def test_schema_root_is_array_of_presets(self, schema: dict) -> None:
        assert schema["type"] == "array"
        assert "$ref" in schema["items"]
        assert schema["items"]["$ref"] == "#/definitions/PipelinePreset"

    def test_schema_defines_all_required_types(self, schema: dict) -> None:
        expected = {"PipelinePreset", "PipelineStage", "ExecutionGroup", "AgentNode"}
        assert expected == set(schema["definitions"].keys())


# ---------------------------------------------------------------------------
# Preset validation (positive)
# ---------------------------------------------------------------------------


class TestPresetValidation:
    """All existing _PRESET_DEFINITIONS must validate against the schema."""

    def test_all_presets_validate_as_array(self, schema: dict, presets: list[dict]) -> None:
        validate(instance=presets, schema=schema)

    @pytest.mark.parametrize(
        "preset_id",
        [p["preset_id"] for p in _PRESET_DEFINITIONS],
        ids=[p["preset_id"] for p in _PRESET_DEFINITIONS],
    )
    def test_individual_preset_validates(self, schema: dict, preset_id: str) -> None:
        """Each preset validates when wrapped as a single-element array."""
        preset = next(p for p in _PRESET_DEFINITIONS if p["preset_id"] == preset_id)
        validate(instance=[copy.deepcopy(preset)], schema=schema)

    def test_every_preset_has_at_least_one_stage(self, presets: list[dict]) -> None:
        for preset in presets:
            assert len(preset["stages"]) >= 1, f"Preset {preset['preset_id']} has no stages"

    def test_stage_orders_are_contiguous_from_zero(self, presets: list[dict]) -> None:
        for preset in presets:
            orders = sorted(s["order"] for s in preset["stages"])
            expected = list(range(len(orders)))
            assert orders == expected, (
                f"Preset {preset['preset_id']} has non-contiguous stage orders: {orders}"
            )

    def test_preset_ids_are_unique(self, presets: list[dict]) -> None:
        ids = [p["preset_id"] for p in presets]
        assert len(ids) == len(set(ids))

    def test_preset_ids_match_pattern(self, schema: dict, presets: list[dict]) -> None:
        import re

        pattern = schema["definitions"]["PipelinePreset"]["properties"]["preset_id"]["pattern"]
        for preset in presets:
            assert re.match(pattern, preset["preset_id"]), (
                f"preset_id '{preset['preset_id']}' does not match pattern '{pattern}'"
            )

    def test_all_agent_nodes_have_required_fields(self, presets: list[dict]) -> None:
        for preset in presets:
            for stage in preset["stages"]:
                for group in stage.get("groups", []):
                    for agent in group.get("agents", []):
                        assert "id" in agent
                        assert "agent_slug" in agent


# ---------------------------------------------------------------------------
# Negative validation (schema rejects invalid data)
# ---------------------------------------------------------------------------


class TestSchemaRejectsInvalid:
    """Invalid pipeline configs must fail schema validation."""

    def test_rejects_empty_array(self, schema: dict) -> None:
        with pytest.raises(ValidationError):
            validate(instance=[], schema=schema)

    def test_rejects_preset_missing_preset_id(self, schema: dict, presets: list[dict]) -> None:
        bad = copy.deepcopy(presets[0])
        del bad["preset_id"]
        with pytest.raises(ValidationError, match="preset_id"):
            validate(instance=[bad], schema=schema)

    def test_rejects_preset_missing_name(self, schema: dict, presets: list[dict]) -> None:
        bad = copy.deepcopy(presets[0])
        del bad["name"]
        with pytest.raises(ValidationError, match="name"):
            validate(instance=[bad], schema=schema)

    def test_rejects_preset_missing_stages(self, schema: dict, presets: list[dict]) -> None:
        bad = copy.deepcopy(presets[0])
        del bad["stages"]
        with pytest.raises(ValidationError, match="stages"):
            validate(instance=[bad], schema=schema)

    def test_rejects_preset_with_empty_stages(self, schema: dict, presets: list[dict]) -> None:
        bad = copy.deepcopy(presets[0])
        bad["stages"] = []
        with pytest.raises(ValidationError):
            validate(instance=[bad], schema=schema)

    def test_rejects_preset_with_extra_property(self, schema: dict) -> None:
        bad = {
            "preset_id": "test",
            "name": "Test",
            "stages": [
                {
                    "id": "s1",
                    "name": "Stage",
                    "order": 0,
                    "groups": [],
                }
            ],
            "unknown_field": True,
        }
        with pytest.raises(ValidationError, match="additionalProperties"):
            validate(instance=[bad], schema=schema)

    def test_rejects_invalid_preset_id_pattern(self, schema: dict) -> None:
        bad = {
            "preset_id": "UPPERCASE",
            "name": "Bad",
            "stages": [{"id": "s1", "name": "S", "order": 0, "groups": []}],
        }
        with pytest.raises(ValidationError):
            validate(instance=[bad], schema=schema)

    def test_rejects_invalid_execution_mode(self, schema: dict) -> None:
        bad = [
            {
                "preset_id": "test",
                "name": "Test",
                "stages": [
                    {
                        "id": "s1",
                        "name": "S",
                        "order": 0,
                        "groups": [
                            {
                                "id": "g1",
                                "execution_mode": "random",
                                "agents": [],
                            }
                        ],
                    }
                ],
            }
        ]
        with pytest.raises(ValidationError):
            validate(instance=bad, schema=schema)

    def test_rejects_agent_missing_id(self, schema: dict) -> None:
        bad = [
            {
                "preset_id": "test",
                "name": "Test",
                "stages": [
                    {
                        "id": "s1",
                        "name": "S",
                        "order": 0,
                        "groups": [
                            {
                                "id": "g1",
                                "agents": [{"agent_slug": "coder"}],
                            }
                        ],
                    }
                ],
            }
        ]
        with pytest.raises(ValidationError, match="id"):
            validate(instance=bad, schema=schema)

    def test_rejects_agent_missing_slug(self, schema: dict) -> None:
        bad = [
            {
                "preset_id": "test",
                "name": "Test",
                "stages": [
                    {
                        "id": "s1",
                        "name": "S",
                        "order": 0,
                        "groups": [
                            {
                                "id": "g1",
                                "agents": [{"id": "a1"}],
                            }
                        ],
                    }
                ],
            }
        ]
        with pytest.raises(ValidationError, match="agent_slug"):
            validate(instance=bad, schema=schema)

    def test_rejects_negative_stage_order(self, schema: dict) -> None:
        bad = [
            {
                "preset_id": "test",
                "name": "Test",
                "stages": [{"id": "s1", "name": "S", "order": -1, "groups": []}],
            }
        ]
        with pytest.raises(ValidationError):
            validate(instance=bad, schema=schema)

    def test_rejects_stage_with_extra_property(self, schema: dict) -> None:
        bad = [
            {
                "preset_id": "test",
                "name": "Test",
                "stages": [
                    {
                        "id": "s1",
                        "name": "S",
                        "order": 0,
                        "groups": [],
                        "extra_field": "not allowed",
                    }
                ],
            }
        ]
        with pytest.raises(ValidationError, match="additionalProperties"):
            validate(instance=bad, schema=schema)


# ---------------------------------------------------------------------------
# Pydantic model ↔ JSON Schema field consistency
# ---------------------------------------------------------------------------


class TestSchemaModelConsistency:
    """Ensure the JSON Schema fields match Pydantic model fields exactly."""

    def test_agent_node_fields_match(self, schema: dict) -> None:
        pydantic_fields = set(PipelineAgentNode.model_fields.keys())
        schema_fields = set(schema["definitions"]["AgentNode"]["properties"].keys())
        assert pydantic_fields == schema_fields

    def test_execution_group_fields_match(self, schema: dict) -> None:
        pydantic_fields = set(ExecutionGroup.model_fields.keys())
        schema_fields = set(schema["definitions"]["ExecutionGroup"]["properties"].keys())
        assert pydantic_fields == schema_fields

    def test_pipeline_stage_fields_match(self, schema: dict) -> None:
        pydantic_fields = set(PipelineStage.model_fields.keys())
        schema_fields = set(schema["definitions"]["PipelineStage"]["properties"].keys())
        assert pydantic_fields == schema_fields

    def test_agent_node_required_fields(self, schema: dict) -> None:
        required = set(schema["definitions"]["AgentNode"]["required"])
        assert required == {"id", "agent_slug"}

    def test_execution_group_required_fields(self, schema: dict) -> None:
        required = set(schema["definitions"]["ExecutionGroup"]["required"])
        assert required == {"id", "agents"}

    def test_pipeline_stage_required_fields(self, schema: dict) -> None:
        required = set(schema["definitions"]["PipelineStage"]["required"])
        assert required == {"id", "name", "order", "groups"}


# ---------------------------------------------------------------------------
# Round-trip: preset dict → schema-validated → Pydantic model
# ---------------------------------------------------------------------------


class TestRoundTripFidelity:
    """Presets validated by the JSON Schema must load into Pydantic models faithfully."""

    @pytest.mark.parametrize(
        "preset_id",
        [p["preset_id"] for p in _PRESET_DEFINITIONS],
        ids=[p["preset_id"] for p in _PRESET_DEFINITIONS],
    )
    def test_preset_stages_load_into_pydantic(self, schema: dict, preset_id: str) -> None:
        preset = next(p for p in _PRESET_DEFINITIONS if p["preset_id"] == preset_id)
        data = copy.deepcopy(preset)

        # Step 1: validate against schema
        validate(instance=[data], schema=schema)

        # Step 2: load each stage into Pydantic
        for stage_data in data["stages"]:
            stage = PipelineStage(**stage_data)
            assert stage.id == stage_data["id"]
            assert stage.name == stage_data["name"]
            assert stage.order == stage_data["order"]
            assert len(stage.groups) == len(stage_data.get("groups", []))

            # Verify agents inside groups round-trip
            for i, group in enumerate(stage.groups):
                group_data = stage_data["groups"][i]
                assert group.id == group_data["id"]
                assert group.execution_mode == group_data.get("execution_mode", "sequential")
                assert len(group.agents) == len(group_data.get("agents", []))
                for j, agent in enumerate(group.agents):
                    agent_data = group_data["agents"][j]
                    assert agent.id == agent_data["id"]
                    assert agent.agent_slug == agent_data["agent_slug"]

    def test_pydantic_model_export_validates_against_schema(self, schema: dict) -> None:
        """A Pydantic-built stage can be serialized and validated by the schema."""
        agent = PipelineAgentNode(
            id="agent-1",
            agent_slug="copilot",
            agent_display_name="GitHub Copilot",
        )
        group = ExecutionGroup(
            id="group-1",
            order=0,
            execution_mode="parallel",
            agents=[agent],
        )
        stage = PipelineStage(
            id="stage-1",
            name="Build",
            order=0,
            groups=[group],
        )

        preset = {
            "preset_id": "test-roundtrip",
            "name": "Test Round Trip",
            "description": "Validates Pydantic → JSON → Schema flow",
            "stages": [json.loads(stage.model_dump_json())],
        }

        validate(instance=[preset], schema=schema)


# ---------------------------------------------------------------------------
# Fleet-dispatch CLI contract (YAML)
# ---------------------------------------------------------------------------


class TestFleetDispatchCliContract:
    """Validate the fleet-dispatch-cli.yaml contract structure."""

    @pytest.fixture()
    def cli_contract(self) -> dict:
        """Load and cache the CLI contract YAML."""
        return yaml.safe_load(_CLI_CONTRACT_PATH.read_text())

    def test_contract_file_exists(self) -> None:
        assert _CLI_CONTRACT_PATH.exists(), f"Contract not found at {_CLI_CONTRACT_PATH}"

    def test_contract_is_valid_yaml(self, cli_contract: dict) -> None:
        assert isinstance(cli_contract, dict)

    def test_contract_has_openapi_version(self, cli_contract: dict) -> None:
        assert "openapi" in cli_contract
        assert cli_contract["openapi"].startswith("3.")

    def test_contract_defines_dispatch_path(self, cli_contract: dict) -> None:
        assert "/dispatch" in cli_contract.get("paths", {})

    def test_contract_defines_fleet_state_schema(self, cli_contract: dict) -> None:
        schemas = cli_contract.get("components", {}).get("schemas", {})
        assert "FleetState" in schemas

    def test_contract_defines_agent_dispatch_schema(self, cli_contract: dict) -> None:
        schemas = cli_contract.get("components", {}).get("schemas", {})
        assert "AgentDispatch" in schemas

    def test_contract_defines_graphql_dispatch_request(self, cli_contract: dict) -> None:
        schemas = cli_contract.get("components", {}).get("schemas", {})
        assert "GraphQLDispatchRequest" in schemas

    def test_fleet_state_required_fields(self, cli_contract: dict) -> None:
        fleet_state = cli_contract["components"]["schemas"]["FleetState"]
        required = set(fleet_state.get("required", []))
        expected = {
            "run_id",
            "repo",
            "parent_issue",
            "base_ref",
            "pipeline_preset",
            "started_at",
            "status",
            "agents",
        }
        assert required == expected

    def test_dispatch_parameters_include_required_cli_args(self, cli_contract: dict) -> None:
        dispatch = cli_contract["paths"]["/dispatch"]["post"]
        params = {p["name"] for p in dispatch.get("parameters", [])}
        assert {"repo", "parent-issue", "config", "preset"} <= params

    def test_graphql_features_header_defined(self, cli_contract: dict) -> None:
        headers_schema = cli_contract["components"]["schemas"]["GraphQLHeaders"]
        props = headers_schema.get("properties", {})
        assert "GraphQL-Features" in props
        allowed = props["GraphQL-Features"]["enum"]
        assert "issues_copilot_assignment_api_support,coding_agent_model_selection" in allowed
