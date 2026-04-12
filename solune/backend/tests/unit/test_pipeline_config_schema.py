from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.models.pipeline import FleetDispatchConfig
from src.services.workflow_orchestrator.config import (
    build_pipeline_stages_from_fleet_config,
    get_default_fleet_dispatch_config_path,
    load_fleet_dispatch_config,
)


def _runtime_schema_path() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "pipelines"
        / "pipeline-config.schema.json"
    )


class TestFleetDispatchConfigSchema:
    def test_loads_canonical_config(self) -> None:
        config = load_fleet_dispatch_config()

        assert config.version == "1"
        assert [group.execution_mode for group in config.groups] == [
            "serial",
            "parallel",
            "parallel",
            "serial",
        ]
        assert [group.order for group in config.groups] == [1, 2, 3, 4]
        assert config.groups[0].agents[0].slug == "speckit.specify"
        assert config.groups[-1].agents[0].slug == "devops"

    def test_builds_pipeline_orchestrator_stages_from_shared_config(self) -> None:
        config = load_fleet_dispatch_config()
        stages = build_pipeline_stages_from_fleet_config(config)

        assert [stage["name"] for stage in stages] == [
            "speckit.specify",
            "speckit.plan",
            "speckit.tasks",
            "speckit.analyze",
            "speckit.implement",
            "quality-assurance",
            "tester",
            "copilot-review",
            "judge",
            "linter",
            "devops",
        ]
        assert [stage["parallel"] for stage in stages[:5]] == [False] * 5
        assert [stage["parallel"] for stage in stages[5:8]] == [True, True, True]
        assert [stage["parallel"] for stage in stages[8:10]] == [True, True]
        assert stages[-1] == {"name": "devops", "agent": "devops", "group": 4, "parallel": False}

    def test_runtime_schema_matches_expected_contract_keys(self) -> None:
        schema = json.loads(_runtime_schema_path().read_text())

        assert schema["properties"]["version"]["const"] == "1"
        assert schema["properties"]["defaults"]["required"] == [
            "baseRef",
            "errorStrategy",
            "pollIntervalSeconds",
            "taskTimeoutSeconds",
        ]
        assert schema["$defs"]["group"]["properties"]["executionMode"]["enum"] == [
            "serial",
            "parallel",
        ]

    def test_default_path_points_at_runtime_asset(self) -> None:
        assert (
            get_default_fleet_dispatch_config_path().resolve()
            == (
                Path(__file__).resolve().parents[3]
                / "scripts"
                / "pipelines"
                / "fleet-dispatch.json"
            ).resolve()
        )

    def test_rejects_timeout_shorter_than_poll_interval(self) -> None:
        raw = json.loads(get_default_fleet_dispatch_config_path().read_text())
        raw["defaults"]["pollIntervalSeconds"] = 30
        raw["defaults"]["taskTimeoutSeconds"] = 10

        with pytest.raises(ValueError):
            FleetDispatchConfig.model_validate(raw)
