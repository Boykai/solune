from __future__ import annotations

import json
from pathlib import Path

from tests.fleet_dispatch_harness import read_log, run_script


def _base_config() -> dict:
    return {
        "version": "1",
        "name": "Test Fleet",
        "repository": {"owner": "Boykai", "name": "solune"},
        "defaults": {
            "baseRef": "main",
            "errorStrategy": "continue",
            "pollIntervalSeconds": 5,
            "taskTimeoutSeconds": 10,
        },
        "groups": [
            {
                "id": "serial",
                "name": "Serial",
                "order": 1,
                "executionMode": "serial",
                "agents": [
                    {
                        "slug": "alpha",
                        "displayName": "Alpha",
                        "customAgent": "alpha",
                        "model": "claude-opus-4.6",
                        "instructionTemplate": "solune/scripts/pipelines/templates/generic.md",
                        "retryable": True,
                        "subIssue": {
                            "title": "[Fleet] Alpha for #{{PARENT_ISSUE_NUMBER}}",
                            "labels": ["alpha"],
                        },
                    },
                    {
                        "slug": "beta",
                        "displayName": "Beta",
                        "customAgent": "beta",
                        "model": "claude-opus-4.6",
                        "instructionTemplate": "solune/scripts/pipelines/templates/generic.md",
                        "retryable": True,
                        "subIssue": {
                            "title": "[Fleet] Beta for #{{PARENT_ISSUE_NUMBER}}",
                            "labels": ["beta"],
                        },
                    },
                ],
            },
            {
                "id": "parallel",
                "name": "Parallel",
                "order": 2,
                "executionMode": "parallel",
                "agents": [
                    {
                        "slug": "gamma",
                        "displayName": "Gamma",
                        "customAgent": "gamma",
                        "model": "claude-opus-4.6",
                        "instructionTemplate": "solune/scripts/pipelines/templates/generic.md",
                        "retryable": True,
                        "subIssue": {
                            "title": "[Fleet] Gamma for #{{PARENT_ISSUE_NUMBER}}",
                            "labels": ["gamma"],
                        },
                    },
                    {
                        "slug": "delta",
                        "displayName": "Delta",
                        "customAgent": "delta",
                        "model": "claude-opus-4.6",
                        "instructionTemplate": "solune/scripts/pipelines/templates/generic.md",
                        "retryable": True,
                        "subIssue": {
                            "title": "[Fleet] Delta for #{{PARENT_ISSUE_NUMBER}}",
                            "labels": ["delta"],
                        },
                    },
                ],
            },
        ],
    }


def _existing_alpha_issue() -> dict:
    return {
        "number": 200,
        "node_id": "ISSUE_NODE_200",
        "html_url": "https://github.com/Boykai/solune/issues/200",
        "title": "Existing alpha issue",
        "body": "Existing body",
        "labels": ["fleet-dispatch", "fleet-parent:1555", "fleet-agent:alpha", "alpha"],
    }


class TestFleetDispatchCli:
    def test_dispatch_orders_serial_then_parallel(self, tmp_path: Path) -> None:
        result = run_script(tmp_path, _base_config())
        log_lines = read_log(tmp_path)

        assert result.returncode == 0, result.stderr
        assert log_lines.index("dispatch:[Fleet] Alpha for #1555") < log_lines.index(
            "task_view:task-1"
        )
        assert log_lines.index("task_view:task-1") < log_lines.index(
            "dispatch:[Fleet] Beta for #1555"
        )
        assert log_lines.index("dispatch:[Fleet] Beta for #1555") < log_lines.index(
            "task_view:task-2"
        )
        gamma_dispatch = log_lines.index("dispatch:[Fleet] Gamma for #1555")
        delta_dispatch = log_lines.index("dispatch:[Fleet] Delta for #1555")
        parallel_task_views = [
            idx for idx, line in enumerate(log_lines) if line.startswith("task_view:")
        ][2:]
        assert parallel_task_views, log_lines
        assert gamma_dispatch < parallel_task_views[0]
        assert delta_dispatch < parallel_task_views[0]

    def test_retry_unassigns_before_redispatch(self, tmp_path: Path) -> None:
        config = _base_config()
        config["groups"] = [
            {
                "id": "retry",
                "name": "Retry",
                "order": 1,
                "executionMode": "serial",
                "agents": [config["groups"][0]["agents"][1]],
            }
        ]
        extra_issue = {
            "number": 200,
            "node_id": "ISSUE_NODE_200",
            "html_url": "https://github.com/Boykai/solune/issues/200",
            "title": "Existing retry issue",
            "body": "Retry body",
            "labels": ["fleet-dispatch", "fleet-parent:1555", "fleet-agent:beta", "beta"],
        }
        result = run_script(
            tmp_path,
            config,
            extra_issues=[extra_issue],
            extra_args=["--retry", "--agent", "beta", "--sub-issue", "200"],
        )
        log_lines = read_log(tmp_path)

        assert result.returncode == 0, result.stderr
        assert log_lines.index("issue_edit:200") < log_lines.index("dispatch:Existing retry issue")

    def test_reuses_existing_sub_issue_by_default(self, tmp_path: Path) -> None:
        config = _base_config()
        config["groups"] = [config["groups"][0]]
        config["groups"][0]["agents"] = [config["groups"][0]["agents"][0]]

        result = run_script(tmp_path, config, extra_issues=[_existing_alpha_issue()])
        log_lines = read_log(tmp_path)

        assert result.returncode == 0, result.stderr
        assert "issue_create:[Fleet] Alpha for #1555" not in log_lines
        assert "dispatch:Existing alpha issue" in log_lines

    def test_no_resume_creates_new_sub_issue_when_match_exists(self, tmp_path: Path) -> None:
        config = _base_config()
        config["groups"] = [config["groups"][0]]
        config["groups"][0]["agents"] = [config["groups"][0]["agents"][0]]
        result = run_script(
            tmp_path,
            config,
            extra_issues=[_existing_alpha_issue()],
            extra_args=["--no-resume"],
        )
        log_lines = read_log(tmp_path)

        assert result.returncode == 0, result.stderr
        assert "issue_create:[Fleet] Alpha for #1555" in log_lines
        assert "dispatch:[Fleet] Alpha for #1555" in log_lines

    def test_dispatch_fails_when_agent_task_cannot_be_resolved(self, tmp_path: Path) -> None:
        config = _base_config()
        config["groups"] = [config["groups"][0]]
        config["groups"][0]["agents"] = [config["groups"][0]["agents"][0]]

        result = run_script(tmp_path, config, omit_task_for_agent="alpha")

        assert result.returncode != 0
        state_files = list((tmp_path / "dispatch-state").glob("*.json"))
        assert len(state_files) == 1
        state = json.loads(state_files[0].read_text())
        assert state["records"][0]["status"] == "failed"
        assert state["records"][0]["errorMessage"] == "Unable to resolve agent task after dispatch"
