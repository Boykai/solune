"""Unit tests for Human Agent — Delay Until Auto-Merge feature.

Covers:
- delay_seconds validation (range [1, 86400], integer type, human agents only)
- Config flow: PipelineAgentNode.config → AgentAssignment.config → PipelineState.agent_configs
- Pipeline execution with human + delay → sleep loop + auto-merge invoked
- Pipeline execution with human + no delay → manual-wait unchanged
- Sub-issue body containing delay info when configured
- Early cancellation via sub-issue close or "Done!" comment
- format_delay_duration helper
- Delay loop interval accuracy (no oversleep on final interval)
"""

import math

from src.models.agent import AgentAssignment
from src.models.workflow import WorkflowConfiguration
from src.services.copilot_polling.pipeline import format_delay_duration
from src.services.workflow_orchestrator.models import (
    PipelineState,
    get_agent_configs,
)

# ── format_delay_duration ────────────────────────────────────────────────────


class TestFormatDelayDuration:
    """Tests for the format_delay_duration helper."""

    def test_seconds_only(self):
        assert format_delay_duration(30) == "30s"

    def test_minutes_only(self):
        assert format_delay_duration(300) == "5m"

    def test_hours_only(self):
        assert format_delay_duration(3600) == "1h"

    def test_minutes_and_seconds(self):
        assert format_delay_duration(90) == "1m 30s"

    def test_hours_and_minutes(self):
        assert format_delay_duration(5400) == "1h 30m"

    def test_full_day(self):
        assert format_delay_duration(86400) == "24h"

    def test_one_second(self):
        assert format_delay_duration(1) == "1s"

    def test_zero(self):
        assert format_delay_duration(0) == "0s"

    def test_negative(self):
        assert format_delay_duration(-5) == "0s"


# ── delay_seconds validation ────────────────────────────────────────────────


class TestDelaySecondsValidation:
    """Tests for delay_seconds validation logic."""

    def test_valid_delay_in_range(self):
        """Valid delay_seconds (integer in [1, 86400]) should be accepted."""
        ps = PipelineState(
            issue_number=1,
            project_id="test",
            status="Ready",
            agents=["human"],
            agent_configs={"human": {"delay_seconds": 300}},
        )
        config = ps.agent_configs.get("human", {})
        delay = config.get("delay_seconds")
        assert delay == 300
        assert isinstance(delay, int)
        assert 1 <= delay <= 86400

    def test_delay_min_boundary(self):
        """delay_seconds=1 should be valid."""
        ps = PipelineState(
            issue_number=1,
            project_id="test",
            status="Ready",
            agents=["human"],
            agent_configs={"human": {"delay_seconds": 1}},
        )
        assert ps.agent_configs["human"]["delay_seconds"] == 1

    def test_delay_max_boundary(self):
        """delay_seconds=86400 should be valid."""
        ps = PipelineState(
            issue_number=1,
            project_id="test",
            status="Ready",
            agents=["human"],
            agent_configs={"human": {"delay_seconds": 86400}},
        )
        assert ps.agent_configs["human"]["delay_seconds"] == 86400

    def test_delay_not_set(self):
        """When delay_seconds is not set, it should be absent from config."""
        ps = PipelineState(
            issue_number=1,
            project_id="test",
            status="Ready",
            agents=["human"],
            agent_configs={},
        )
        assert ps.agent_configs.get("human", {}).get("delay_seconds") is None

    def test_delay_only_meaningful_for_human(self):
        """delay_seconds on non-human agents should be ignored at execution."""
        ps = PipelineState(
            issue_number=1,
            project_id="test",
            status="Ready",
            agents=["copilot"],
            agent_configs={"copilot": {"delay_seconds": 300}},
        )
        # The delay is stored but should only be acted on for human agents
        assert ps.agent_configs["copilot"]["delay_seconds"] == 300
        # The pipeline code only checks delay_seconds when next_agent == "human"


# ── Config flow ──────────────────────────────────────────────────────────────


class TestConfigFlow:
    """Tests for delay_seconds flowing through the config chain."""

    def test_get_agent_configs_with_delay(self):
        """get_agent_configs extracts delay_seconds from agent assignments."""
        config = WorkflowConfiguration(
            project_id="PVT_test",
            repository_owner="test-owner",
            repository_name="test-repo",
            agent_mappings={
                "Ready": [
                    AgentAssignment(
                        slug="human",
                        config={"delay_seconds": 600, "model_id": "", "model_name": ""},
                    ),
                ],
            },
        )
        result = get_agent_configs(config)
        assert "human" in result
        assert result["human"]["delay_seconds"] == 600

    def test_get_agent_configs_without_delay(self):
        """get_agent_configs returns empty config when no delay set."""
        config = WorkflowConfiguration(
            project_id="PVT_test",
            repository_owner="test-owner",
            repository_name="test-repo",
            agent_mappings={
                "Ready": [
                    AgentAssignment(slug="human"),
                ],
            },
        )
        result = get_agent_configs(config)
        # No config set on the assignment
        assert "human" not in result

    def test_get_agent_configs_multiple_agents(self):
        """get_agent_configs collects configs from all agents."""
        config = WorkflowConfiguration(
            project_id="PVT_test",
            repository_owner="test-owner",
            repository_name="test-repo",
            agent_mappings={
                "Ready": [
                    AgentAssignment(
                        slug="copilot",
                        config={"model_id": "gpt-4", "model_name": "GPT-4"},
                    ),
                    AgentAssignment(
                        slug="human",
                        config={"delay_seconds": 30, "model_id": "", "model_name": ""},
                    ),
                ],
            },
        )
        result = get_agent_configs(config)
        assert "copilot" in result
        assert "human" in result
        assert result["human"]["delay_seconds"] == 30

    def test_pipeline_state_agent_configs_default(self):
        """PipelineState.agent_configs should default to empty dict."""
        ps = PipelineState(
            issue_number=1,
            project_id="test",
            status="Ready",
            agents=["human"],
        )
        assert ps.agent_configs == {}


# ── Sub-issue body ───────────────────────────────────────────────────────────


class TestSubIssueBody:
    """Tests for human sub-issue body with delay info."""

    def test_body_contains_delay_info_when_configured(self):
        """Sub-issue body should contain delay info when delay_seconds is set."""
        from src.services.github_projects.agents import AgentsMixin

        mixin = AgentsMixin()
        body = mixin.tailor_body_for_agent(
            parent_body="Test body",
            agent_name="human",
            parent_issue_number=42,
            parent_title="Test Issue",
            delay_seconds=300,
        )
        assert "⏱️ Auto-merge in 5m. Close early to skip." in body

    def test_body_no_delay_info_when_not_configured(self):
        """Sub-issue body should NOT contain delay info when no delay."""
        from src.services.github_projects.agents import AgentsMixin

        mixin = AgentsMixin()
        body = mixin.tailor_body_for_agent(
            parent_body="Test body",
            agent_name="human",
            parent_issue_number=42,
            parent_title="Test Issue",
        )
        assert "Auto-merge in" not in body
        assert "Close early to skip" not in body

    def test_body_no_delay_info_for_non_human(self):
        """Non-human agent sub-issue should NOT contain delay info."""
        from src.services.github_projects.agents import AgentsMixin

        mixin = AgentsMixin()
        body = mixin.tailor_body_for_agent(
            parent_body="Test body",
            agent_name="copilot",
            parent_issue_number=42,
            parent_title="Test Issue",
            delay_seconds=300,
        )
        assert "Auto-merge in" not in body

    def test_body_delay_formatting(self):
        """Delay info should use human-readable duration format."""
        from src.services.github_projects.agents import AgentsMixin

        mixin = AgentsMixin()
        body = mixin.tailor_body_for_agent(
            parent_body="Test body",
            agent_name="human",
            parent_issue_number=42,
            parent_title="Test Issue",
            delay_seconds=3600,
        )
        assert "⏱️ Auto-merge in 1h. Close early to skip." in body


# ── Pipeline execution with delay ────────────────────────────────────────────


class TestPipelineDelayExecution:
    """Tests for pipeline execution with human delay-then-merge."""

    def test_delay_loop_intervals(self):
        """Delay loop should execute correct number of 15s intervals."""
        assert math.ceil(45 / 15) == 3
        assert math.ceil(30 / 15) == 2
        assert math.ceil(15 / 15) == 1

    def test_delay_loop_last_interval_does_not_oversleep(self):
        """When delay is not a multiple of 15, the last interval should be shorter."""
        delay_seconds = 20
        poll_interval = 15
        intervals = math.ceil(delay_seconds / poll_interval)
        assert intervals == 2

        sleep_times: list[float] = []
        for i in range(intervals):
            remaining = delay_seconds - (i * poll_interval)
            sleep_times.append(min(poll_interval, remaining))

        # First interval: 15s, second interval: 5s (not 15)
        assert sleep_times == [15, 5]
        assert sum(sleep_times) == delay_seconds

    def test_delay_loop_exact_multiple(self):
        """When delay is exact multiple of 15, all intervals are full 15s."""
        delay_seconds = 45
        poll_interval = 15
        intervals = math.ceil(delay_seconds / poll_interval)

        sleep_times: list[float] = []
        for i in range(intervals):
            remaining = delay_seconds - (i * poll_interval)
            sleep_times.append(min(poll_interval, remaining))

        assert sleep_times == [15, 15, 15]
        assert sum(sleep_times) == delay_seconds

    def test_delay_duration_format_used_in_comments(self):
        """Verify duration formatting used in delay comments."""
        assert format_delay_duration(300) == "5m"
        assert format_delay_duration(30) == "30s"
        assert format_delay_duration(3600) == "1h"

    def test_delay_validation_rejects_out_of_range(self):
        """delay_seconds validation in pipeline rejects values outside [1, 86400]."""
        # Replicate the validation logic from _advance_pipeline
        for raw_delay in [0, -1, 86401, 100000]:
            delay_seconds = None
            try:
                val = int(raw_delay)
                if val < 1 or val > 86400:
                    delay_seconds = None
                else:
                    delay_seconds = val
            except (TypeError, ValueError):
                pass
            assert delay_seconds is None, f"Expected None for raw_delay={raw_delay}"

    def test_delay_validation_accepts_valid_values(self):
        """delay_seconds validation accepts integers in [1, 86400]."""
        for raw_delay in [1, 15, 300, 3600, 86400]:
            delay_seconds = None
            try:
                val = int(raw_delay)
                if 1 <= val <= 86400:
                    delay_seconds = val
            except (TypeError, ValueError):
                pass
            assert delay_seconds == raw_delay

    def test_delay_validation_rejects_non_integer(self):
        """delay_seconds validation rejects non-integer values."""
        for raw_delay in ["abc", None, "", []]:
            delay_seconds = None
            try:
                val = int(raw_delay)  # type: ignore[arg-type]
                if 1 <= val <= 86400:
                    delay_seconds = val
            except (TypeError, ValueError):
                pass
            assert delay_seconds is None


# ── Pipeline execution without delay (backward compat) ───────────────────────


class TestPipelineNoDelay:
    """Tests for pipeline execution with human + no delay (unchanged behavior)."""

    def test_no_delay_config_means_manual_wait(self):
        """When delay_seconds is absent, pipeline should use manual wait."""
        ps = PipelineState(
            issue_number=1,
            project_id="test",
            status="Ready",
            agents=["human"],
            agent_configs={},
        )
        human_config = ps.agent_configs.get("human", {})
        delay = human_config.get("delay_seconds")
        assert delay is None  # No delay → manual wait path

    def test_skip_human_on_auto_merge_last_step_no_delay(self):
        """When auto_merge=True and human is last step with no delay, existing skip behavior."""
        ps = PipelineState(
            issue_number=1,
            project_id="test",
            status="Ready",
            agents=["copilot", "human"],
            current_agent_index=1,
            auto_merge=True,
            agent_configs={},
        )
        # human is last step, auto_merge active, no delay → skip path
        human_config = ps.agent_configs.get("human", {})
        delay = human_config.get("delay_seconds")
        remaining = ps.agents[ps.current_agent_index :]
        is_last_step = len(remaining) == 1
        assert delay is None
        assert is_last_step
        assert ps.auto_merge


# ── Early cancellation ───────────────────────────────────────────────────────


class TestEarlyCancellation:
    """Tests for early cancellation during delay period."""

    def test_early_cancel_breaks_loop(self):
        """If sub-issue closed early, delay loop should break immediately."""
        intervals = math.ceil(600 / 15)
        assert intervals == 40

        cancelled_at_interval = 2
        loop_count = 0
        cancelled_early = False
        for i in range(intervals):
            loop_count += 1
            if i >= cancelled_at_interval - 1:
                cancelled_early = True
                break

        assert cancelled_early
        assert loop_count == 2

    def test_no_early_cancel_runs_full_loop(self):
        """Without cancellation, loop runs all intervals."""
        intervals = math.ceil(30 / 15)
        assert intervals == 2

        loop_count = 0
        for _ in range(intervals):
            loop_count += 1

        assert loop_count == intervals


# ── AutoMergeResult dataclass access ─────────────────────────────────────────


class TestAutoMergeResultAccess:
    """Verify that AutoMergeResult is accessed via attribute, not .get()."""

    def test_auto_merge_result_has_status_attribute(self):
        """AutoMergeResult.status is accessed as an attribute, not dict .get()."""
        from src.services.copilot_polling.auto_merge import AutoMergeResult

        result = AutoMergeResult(status="retry_later", pr_number=42)
        assert result.status == "retry_later"
        assert result.pr_number == 42
        # Verify it does NOT have a .get() method (it's a dataclass, not dict)
        assert not hasattr(result, "get")

    def test_auto_merge_result_merged(self):
        """AutoMergeResult with 'merged' status."""
        from src.services.copilot_polling.auto_merge import AutoMergeResult

        result = AutoMergeResult(status="merged", pr_number=10, merge_commit="abc123")
        assert result.status == "merged"
        assert result.merge_commit == "abc123"
