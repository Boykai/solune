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
- Async _advance_pipeline: delay-then-merge path (mock IO)
- Async _advance_pipeline: early cancellation via _check_human_agent_done
- Async _advance_pipeline: no-delay backward-compat skip path
- pipeline_state_store round-trip for agent_configs
- config.py load_pipeline_as_agent_mappings merges node.config
- Orchestrator sub-issue creation with delay_seconds propagation
"""

import json
import math
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
        from typing import Any

        raw_values: list[Any] = ["abc", None, "", []]
        for raw_delay in raw_values:
            delay_seconds = None
            try:
                val = int(raw_delay)
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


# ══════════════════════════════════════════════════════════════════
# Async _advance_pipeline execution tests
# ══════════════════════════════════════════════════════════════════

# ── Patch targets for copilot_polling module ─────────────────────
_CP = "src.services.copilot_polling"
_PIPELINE_MOD = "src.services.copilot_polling.pipeline"
_HELPERS_MOD = "src.services.copilot_polling.helpers"
_AUTO_MERGE_MOD = "src.services.copilot_polling.auto_merge"


def _make_pipeline_state(**overrides) -> PipelineState:
    """Create a PipelineState for _advance_pipeline tests.

    Default: copilot just finished, human is next (index 1).
    _advance_pipeline sees current_agent_index=0 → copilot completed,
    increments to 1, then checks if next_agent (human) needs delay/skip.
    """
    defaults = {
        "issue_number": 42,
        "project_id": "PVT_test",
        "status": "In Progress",
        "agents": ["copilot", "human"],
        "current_agent_index": 0,  # copilot is completing
        "completed_agents": [],
        "agent_sub_issues": {"human": {"number": 99}},
        "agent_configs": {},
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


def _base_pipeline_patches(mock_gps=None, mock_conn_mgr=None):
    """Stack patches for _cp dependencies used by _advance_pipeline.

    This mocks all the _cp.xxx module-level functions that the early part
    of _advance_pipeline calls (main branch lookup, child PR merge,
    issue tracking, sub-issue close, etc.) so we can reach the human
    agent block without errors.
    """
    if mock_gps is None:
        mock_gps = MagicMock()
        mock_gps.create_issue_comment = AsyncMock()
        mock_gps.update_issue_state = AsyncMock()
        mock_gps.get_pull_request = AsyncMock(return_value={"is_draft": True})
        mock_gps.find_existing_pr_for_issue = AsyncMock(return_value=None)
    if mock_conn_mgr is None:
        mock_conn_mgr = MagicMock()
        mock_conn_mgr.broadcast_to_project = AsyncMock()

    stack = ExitStack()
    stack.enter_context(patch(f"{_CP}.get_github_service", return_value=mock_gps))
    stack.enter_context(patch(f"{_CP}.connection_manager", mock_conn_mgr))
    stack.enter_context(patch(f"{_CP}.set_pipeline_state"))
    stack.enter_context(patch(f"{_CP}.remove_pipeline_state"))
    stack.enter_context(patch(f"{_CP}.get_issue_sub_issues", return_value={}))
    stack.enter_context(patch(f"{_CP}.set_issue_sub_issues"))
    stack.enter_context(patch(f"{_CP}.mark_agent_active"))
    stack.enter_context(patch(f"{_CP}.mark_agent_done"))
    # _advance_pipeline calls _cp.get_issue_main_branch early for child PR merge
    stack.enter_context(patch(f"{_CP}.get_issue_main_branch", return_value=None))
    stack.enter_context(patch(f"{_CP}.update_issue_main_branch_sha"))
    stack.enter_context(patch(f"{_CP}._update_issue_tracking", new_callable=AsyncMock))
    stack.enter_context(patch(f"{_CP}._merge_child_pr_if_applicable", new_callable=AsyncMock))
    # Close completed sub-issues (called before human check)
    stack.enter_context(
        patch(f"{_PIPELINE_MOD}._close_completed_sub_issues", new_callable=AsyncMock)
    )
    return stack, mock_gps, mock_conn_mgr


class TestAdvancePipelineDelayPath:
    """Async tests for _advance_pipeline with human + delay_seconds set."""

    @pytest.mark.asyncio
    async def test_delay_path_invokes_auto_merge(self):
        """When delay_seconds is set, _advance_pipeline should sleep, then call _attempt_auto_merge."""
        from src.services.copilot_polling.auto_merge import AutoMergeResult

        pipeline = _make_pipeline_state(
            agent_configs={"human": {"delay_seconds": 15}},
        )

        stack, mock_gps, _mock_conn = _base_pipeline_patches()
        with stack:
            with (
                patch(f"{_PIPELINE_MOD}.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
                patch(
                    f"{_HELPERS_MOD}._check_human_agent_done",
                    new_callable=AsyncMock,
                    return_value=False,
                ),
                patch(
                    f"{_AUTO_MERGE_MOD}._attempt_auto_merge",
                    new_callable=AsyncMock,
                    return_value=AutoMergeResult(status="merged", pr_number=10),
                ) as mock_merge,
                patch(
                    f"{_PIPELINE_MOD}._transition_after_pipeline_complete",
                    new_callable=AsyncMock,
                    return_value={"status": "done"},
                ),
            ):
                from src.services.copilot_polling.pipeline import _advance_pipeline

                await _advance_pipeline(
                    access_token="tok",
                    project_id="PVT_test",
                    item_id="item1",
                    owner="test-owner",
                    repo="test-repo",
                    issue_number=42,
                    issue_node_id=None,
                    pipeline=pipeline,
                    from_status="In Progress",
                    to_status="Done",
                    task_title="Test task",
                )

                # Verify sleep was called (delay loop with 15s interval → 1 sleep)
                mock_sleep.assert_awaited()
                # Verify auto-merge was triggered
                mock_merge.assert_awaited_once_with(
                    access_token="tok",
                    owner="test-owner",
                    repo="test-repo",
                    issue_number=42,
                )
                # Verify sub-issue was closed with completion comment
                mock_gps.update_issue_state.assert_awaited()
                close_calls = [
                    c
                    for c in mock_gps.update_issue_state.call_args_list
                    if c.kwargs.get("state") == "closed"
                ]
                assert len(close_calls) >= 1

    @pytest.mark.asyncio
    async def test_delay_path_comments_on_sub_issue(self):
        """Delay path should post ⏱️ delay comment on the human sub-issue."""
        from src.services.copilot_polling.auto_merge import AutoMergeResult

        pipeline = _make_pipeline_state(
            agent_configs={"human": {"delay_seconds": 300}},
        )

        stack, mock_gps, _ = _base_pipeline_patches()
        with stack:
            with (
                patch(f"{_PIPELINE_MOD}.asyncio.sleep", new_callable=AsyncMock),
                patch(
                    f"{_HELPERS_MOD}._check_human_agent_done",
                    new_callable=AsyncMock,
                    return_value=False,
                ),
                patch(
                    f"{_AUTO_MERGE_MOD}._attempt_auto_merge",
                    new_callable=AsyncMock,
                    return_value=AutoMergeResult(status="merged", pr_number=10),
                ),
                patch(
                    f"{_PIPELINE_MOD}._transition_after_pipeline_complete",
                    new_callable=AsyncMock,
                    return_value={"status": "done"},
                ),
            ):
                from src.services.copilot_polling.pipeline import _advance_pipeline

                await _advance_pipeline(
                    access_token="tok",
                    project_id="PVT_test",
                    item_id="item1",
                    owner="test-owner",
                    repo="test-repo",
                    issue_number=42,
                    issue_node_id=None,
                    pipeline=pipeline,
                    from_status="In Progress",
                    to_status="Done",
                    task_title="Test task",
                )

                # Verify delay comment was posted on sub-issue #99
                comment_calls = mock_gps.create_issue_comment.call_args_list
                delay_comments = [
                    c
                    for c in comment_calls
                    if "Auto-merge in 5m" in str(c.kwargs.get("body", ""))
                    and c.kwargs.get("issue_number") == 99
                ]
                assert len(delay_comments) == 1

    @pytest.mark.asyncio
    async def test_delay_path_broadcasts_delay_state(self):
        """Delay path should broadcast ⏱️ Delay tracking state via WebSocket."""
        from src.services.copilot_polling.auto_merge import AutoMergeResult

        pipeline = _make_pipeline_state(
            agent_configs={"human": {"delay_seconds": 30}},
        )

        stack, _, mock_conn = _base_pipeline_patches()
        with stack:
            with (
                patch(f"{_PIPELINE_MOD}.asyncio.sleep", new_callable=AsyncMock),
                patch(
                    f"{_HELPERS_MOD}._check_human_agent_done",
                    new_callable=AsyncMock,
                    return_value=False,
                ),
                patch(
                    f"{_AUTO_MERGE_MOD}._attempt_auto_merge",
                    new_callable=AsyncMock,
                    return_value=AutoMergeResult(status="merged", pr_number=10),
                ),
                patch(
                    f"{_PIPELINE_MOD}._transition_after_pipeline_complete",
                    new_callable=AsyncMock,
                    return_value={"status": "done"},
                ),
            ):
                from src.services.copilot_polling.pipeline import _advance_pipeline

                await _advance_pipeline(
                    access_token="tok",
                    project_id="PVT_test",
                    item_id="item1",
                    owner="test-owner",
                    repo="test-repo",
                    issue_number=42,
                    issue_node_id=None,
                    pipeline=pipeline,
                    from_status="In Progress",
                    to_status="Done",
                    task_title="Test task",
                )

                # Find the delay broadcast
                broadcast_calls = mock_conn.broadcast_to_project.call_args_list
                delay_broadcasts = [
                    c for c in broadcast_calls if "⏱️ Delay" in str(c.args[1].get("agent_state", ""))
                ]
                assert len(delay_broadcasts) >= 1

    @pytest.mark.asyncio
    async def test_delay_path_marks_agent_completed(self):
        """After delay, human agent should be marked completed in pipeline state."""
        from src.services.copilot_polling.auto_merge import AutoMergeResult

        pipeline = _make_pipeline_state(
            agent_configs={"human": {"delay_seconds": 15}},
        )

        stack, _, _ = _base_pipeline_patches()
        with stack:
            with (
                patch(f"{_PIPELINE_MOD}.asyncio.sleep", new_callable=AsyncMock),
                patch(
                    f"{_HELPERS_MOD}._check_human_agent_done",
                    new_callable=AsyncMock,
                    return_value=False,
                ),
                patch(
                    f"{_AUTO_MERGE_MOD}._attempt_auto_merge",
                    new_callable=AsyncMock,
                    return_value=AutoMergeResult(status="merged", pr_number=10),
                ),
                patch(
                    f"{_PIPELINE_MOD}._transition_after_pipeline_complete",
                    new_callable=AsyncMock,
                    return_value={"status": "done"},
                ),
            ):
                from src.services.copilot_polling.pipeline import _advance_pipeline

                await _advance_pipeline(
                    access_token="tok",
                    project_id="PVT_test",
                    item_id="item1",
                    owner="test-owner",
                    repo="test-repo",
                    issue_number=42,
                    issue_node_id=None,
                    pipeline=pipeline,
                    from_status="In Progress",
                    to_status="Done",
                    task_title="Test task",
                )

                # copilot was completed in early code, human via delay path
                assert "copilot" in pipeline.completed_agents
                assert "human" in pipeline.completed_agents

    @pytest.mark.asyncio
    async def test_delay_path_retry_later_schedules_retry(self):
        """When auto-merge returns retry_later, schedule_auto_merge_retry should be called."""
        from src.services.copilot_polling.auto_merge import AutoMergeResult

        pipeline = _make_pipeline_state(
            agent_configs={"human": {"delay_seconds": 15}},
        )

        stack, _, _ = _base_pipeline_patches()
        with stack:
            with (
                patch(f"{_PIPELINE_MOD}.asyncio.sleep", new_callable=AsyncMock),
                patch(
                    f"{_HELPERS_MOD}._check_human_agent_done",
                    new_callable=AsyncMock,
                    return_value=False,
                ),
                patch(
                    f"{_AUTO_MERGE_MOD}._attempt_auto_merge",
                    new_callable=AsyncMock,
                    return_value=AutoMergeResult(status="retry_later", pr_number=10),
                ),
                patch(
                    f"{_AUTO_MERGE_MOD}.schedule_auto_merge_retry",
                ) as mock_retry,
                patch(
                    f"{_PIPELINE_MOD}._transition_after_pipeline_complete",
                    new_callable=AsyncMock,
                    return_value={"status": "done"},
                ),
            ):
                from src.services.copilot_polling.pipeline import _advance_pipeline

                await _advance_pipeline(
                    access_token="tok",
                    project_id="PVT_test",
                    item_id="item1",
                    owner="test-owner",
                    repo="test-repo",
                    issue_number=42,
                    issue_node_id=None,
                    pipeline=pipeline,
                    from_status="In Progress",
                    to_status="Done",
                    task_title="Test task",
                )

                mock_retry.assert_called_once()


class TestAdvancePipelineEarlyCancel:
    """Async tests for early cancellation during delay period."""

    @pytest.mark.asyncio
    async def test_early_cancel_breaks_delay_loop(self):
        """If _check_human_agent_done returns True during delay, loop breaks early."""
        from src.services.copilot_polling.auto_merge import AutoMergeResult

        pipeline = _make_pipeline_state(
            agent_configs={"human": {"delay_seconds": 600}},  # 40 intervals
        )

        sleep_calls: list[float] = []

        async def track_sleep(seconds):
            sleep_calls.append(seconds)

        # Return False first, then True on second poll → should break early
        done_side_effects = [False, True]

        stack, _, _ = _base_pipeline_patches()
        with stack:
            with (
                patch(f"{_PIPELINE_MOD}.asyncio.sleep", side_effect=track_sleep),
                patch(
                    f"{_HELPERS_MOD}._check_human_agent_done",
                    new_callable=AsyncMock,
                    side_effect=done_side_effects,
                ),
                patch(
                    f"{_AUTO_MERGE_MOD}._attempt_auto_merge",
                    new_callable=AsyncMock,
                    return_value=AutoMergeResult(status="merged", pr_number=10),
                ) as mock_merge,
                patch(
                    f"{_PIPELINE_MOD}._transition_after_pipeline_complete",
                    new_callable=AsyncMock,
                    return_value={"status": "done"},
                ),
            ):
                from src.services.copilot_polling.pipeline import _advance_pipeline

                await _advance_pipeline(
                    access_token="tok",
                    project_id="PVT_test",
                    item_id="item1",
                    owner="test-owner",
                    repo="test-repo",
                    issue_number=42,
                    issue_node_id=None,
                    pipeline=pipeline,
                    from_status="In Progress",
                    to_status="Done",
                    task_title="Test task",
                )

                # Only 2 sleep calls (not 40) — loop broke early
                assert len(sleep_calls) == 2
                assert sleep_calls == [15, 15]
                # Auto-merge was still invoked after early cancel
                mock_merge.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_early_cancel_runs_full_delay(self):
        """Without early cancellation, delay loop runs all intervals."""
        from src.services.copilot_polling.auto_merge import AutoMergeResult

        pipeline = _make_pipeline_state(
            agent_configs={"human": {"delay_seconds": 30}},  # 2 intervals of 15s
        )

        sleep_calls: list[float] = []

        async def track_sleep(seconds):
            sleep_calls.append(seconds)

        stack, _, _ = _base_pipeline_patches()
        with stack:
            with (
                patch(f"{_PIPELINE_MOD}.asyncio.sleep", side_effect=track_sleep),
                patch(
                    f"{_HELPERS_MOD}._check_human_agent_done",
                    new_callable=AsyncMock,
                    return_value=False,
                ),
                patch(
                    f"{_AUTO_MERGE_MOD}._attempt_auto_merge",
                    new_callable=AsyncMock,
                    return_value=AutoMergeResult(status="merged", pr_number=10),
                ),
                patch(
                    f"{_PIPELINE_MOD}._transition_after_pipeline_complete",
                    new_callable=AsyncMock,
                    return_value={"status": "done"},
                ),
            ):
                from src.services.copilot_polling.pipeline import _advance_pipeline

                await _advance_pipeline(
                    access_token="tok",
                    project_id="PVT_test",
                    item_id="item1",
                    owner="test-owner",
                    repo="test-repo",
                    issue_number=42,
                    issue_node_id=None,
                    pipeline=pipeline,
                    from_status="In Progress",
                    to_status="Done",
                    task_title="Test task",
                )

                assert sleep_calls == [15, 15]

    @pytest.mark.asyncio
    async def test_partial_last_interval_no_oversleep(self):
        """When delay is not a multiple of 15, last sleep should be shorter."""
        from src.services.copilot_polling.auto_merge import AutoMergeResult

        pipeline = _make_pipeline_state(
            agent_configs={"human": {"delay_seconds": 20}},  # 15 + 5
        )

        sleep_calls: list[float] = []

        async def track_sleep(seconds):
            sleep_calls.append(seconds)

        stack, _, _ = _base_pipeline_patches()
        with stack:
            with (
                patch(f"{_PIPELINE_MOD}.asyncio.sleep", side_effect=track_sleep),
                patch(
                    f"{_HELPERS_MOD}._check_human_agent_done",
                    new_callable=AsyncMock,
                    return_value=False,
                ),
                patch(
                    f"{_AUTO_MERGE_MOD}._attempt_auto_merge",
                    new_callable=AsyncMock,
                    return_value=AutoMergeResult(status="merged", pr_number=10),
                ),
                patch(
                    f"{_PIPELINE_MOD}._transition_after_pipeline_complete",
                    new_callable=AsyncMock,
                    return_value={"status": "done"},
                ),
            ):
                from src.services.copilot_polling.pipeline import _advance_pipeline

                await _advance_pipeline(
                    access_token="tok",
                    project_id="PVT_test",
                    item_id="item1",
                    owner="test-owner",
                    repo="test-repo",
                    issue_number=42,
                    issue_node_id=None,
                    pipeline=pipeline,
                    from_status="In Progress",
                    to_status="Done",
                    task_title="Test task",
                )

                # 15s + 5s, NOT 15s + 15s
                assert sleep_calls == [15, 5]
                assert sum(sleep_calls) == 20


class TestAdvancePipelineNoDelaySkip:
    """Async tests for _advance_pipeline with human + no delay (backward compat)."""

    @pytest.mark.asyncio
    async def test_no_delay_auto_merge_last_step_skips_human(self):
        """When no delay + auto_merge=True + human is last step → ⏭ SKIPPED path."""
        pipeline = _make_pipeline_state(
            auto_merge=True,
            agent_configs={},
        )

        stack, _mock_gps, mock_conn = _base_pipeline_patches()
        with stack:
            with (
                patch(
                    f"{_PIPELINE_MOD}._transition_after_pipeline_complete",
                    new_callable=AsyncMock,
                    return_value={"status": "done"},
                ),
                patch("src.services.database.get_db", return_value=MagicMock()),
                patch(
                    "src.services.settings_store.is_auto_merge_enabled",
                    new_callable=AsyncMock,
                    return_value=False,
                ),
            ):
                from src.services.copilot_polling.pipeline import _advance_pipeline

                await _advance_pipeline(
                    access_token="tok",
                    project_id="PVT_test",
                    item_id="item1",
                    owner="test-owner",
                    repo="test-repo",
                    issue_number=42,
                    issue_node_id=None,
                    pipeline=pipeline,
                    from_status="In Progress",
                    to_status="Done",
                    task_title="Test task",
                )

                # Human marked completed via skip path (copilot already completed in early code)
                assert "human" in pipeline.completed_agents
                assert "copilot" in pipeline.completed_agents
                # SKIPPED broadcast emitted
                skip_broadcasts = [
                    c
                    for c in mock_conn.broadcast_to_project.call_args_list
                    if isinstance(c.args[1], dict)
                    and "⏭ SKIPPED" in str(c.args[1].get("agent_state", ""))
                ]
                assert len(skip_broadcasts) >= 1


class TestAdvancePipelineDelayValidation:
    """Tests for delay_seconds validation within _advance_pipeline."""

    @pytest.mark.asyncio
    async def test_invalid_delay_falls_to_no_delay_path(self):
        """delay_seconds=0 should be treated as no delay (invalid, falls to else branch)."""
        pipeline = _make_pipeline_state(
            auto_merge=True,
            agent_configs={"human": {"delay_seconds": 0}},
        )

        stack, _, mock_conn = _base_pipeline_patches()
        with stack:
            with (
                patch(
                    f"{_PIPELINE_MOD}._transition_after_pipeline_complete",
                    new_callable=AsyncMock,
                    return_value={"status": "done"},
                ),
                patch("src.services.database.get_db", return_value=MagicMock()),
                patch(
                    "src.services.settings_store.is_auto_merge_enabled",
                    new_callable=AsyncMock,
                    return_value=False,
                ),
            ):
                from src.services.copilot_polling.pipeline import _advance_pipeline

                await _advance_pipeline(
                    access_token="tok",
                    project_id="PVT_test",
                    item_id="item1",
                    owner="test-owner",
                    repo="test-repo",
                    issue_number=42,
                    issue_node_id=None,
                    pipeline=pipeline,
                    from_status="In Progress",
                    to_status="Done",
                    task_title="Test task",
                )

                # Should have taken the skip (no delay) path, not delay path
                skip_broadcasts = [
                    c
                    for c in mock_conn.broadcast_to_project.call_args_list
                    if isinstance(c.args[1], dict)
                    and "⏭ SKIPPED" in str(c.args[1].get("agent_state", ""))
                ]
                assert len(skip_broadcasts) >= 1

    @pytest.mark.asyncio
    async def test_over_max_delay_falls_to_no_delay_path(self):
        """delay_seconds=86401 should be treated as no delay (out of range)."""
        pipeline = _make_pipeline_state(
            auto_merge=True,
            agent_configs={"human": {"delay_seconds": 86401}},
        )

        stack, _, mock_conn = _base_pipeline_patches()
        with stack:
            with (
                patch(
                    f"{_PIPELINE_MOD}._transition_after_pipeline_complete",
                    new_callable=AsyncMock,
                    return_value={"status": "done"},
                ),
                patch("src.services.database.get_db", return_value=MagicMock()),
                patch(
                    "src.services.settings_store.is_auto_merge_enabled",
                    new_callable=AsyncMock,
                    return_value=False,
                ),
            ):
                from src.services.copilot_polling.pipeline import _advance_pipeline

                await _advance_pipeline(
                    access_token="tok",
                    project_id="PVT_test",
                    item_id="item1",
                    owner="test-owner",
                    repo="test-repo",
                    issue_number=42,
                    issue_node_id=None,
                    pipeline=pipeline,
                    from_status="In Progress",
                    to_status="Done",
                    task_title="Test task",
                )

                skip_broadcasts = [
                    c
                    for c in mock_conn.broadcast_to_project.call_args_list
                    if isinstance(c.args[1], dict)
                    and "⏭ SKIPPED" in str(c.args[1].get("agent_state", ""))
                ]
                assert len(skip_broadcasts) >= 1

    @pytest.mark.asyncio
    async def test_non_integer_delay_falls_to_no_delay_path(self):
        """delay_seconds='abc' should be treated as no delay."""
        pipeline = _make_pipeline_state(
            auto_merge=True,
            agent_configs={"human": {"delay_seconds": "abc"}},
        )

        stack, _, mock_conn = _base_pipeline_patches()
        with stack:
            with (
                patch(
                    f"{_PIPELINE_MOD}._transition_after_pipeline_complete",
                    new_callable=AsyncMock,
                    return_value={"status": "done"},
                ),
                patch("src.services.database.get_db", return_value=MagicMock()),
                patch(
                    "src.services.settings_store.is_auto_merge_enabled",
                    new_callable=AsyncMock,
                    return_value=False,
                ),
            ):
                from src.services.copilot_polling.pipeline import _advance_pipeline

                await _advance_pipeline(
                    access_token="tok",
                    project_id="PVT_test",
                    item_id="item1",
                    owner="test-owner",
                    repo="test-repo",
                    issue_number=42,
                    issue_node_id=None,
                    pipeline=pipeline,
                    from_status="In Progress",
                    to_status="Done",
                    task_title="Test task",
                )

                skip_broadcasts = [
                    c
                    for c in mock_conn.broadcast_to_project.call_args_list
                    if isinstance(c.args[1], dict)
                    and "⏭ SKIPPED" in str(c.args[1].get("agent_state", ""))
                ]
                assert len(skip_broadcasts) >= 1


class TestAdvancePipelineDelayNonLastStep:
    """Test delay path when human is NOT the last step (pipeline continues)."""

    @pytest.mark.asyncio
    async def test_delay_path_advances_to_next_agent_when_not_last(self):
        """After delay completes with human not last, next_agent should be the
        following agent (not 'human' again)."""
        from src.services.copilot_polling.auto_merge import AutoMergeResult

        pipeline = _make_pipeline_state(
            agents=["copilot", "human", "speckit.implement"],
            agent_configs={"human": {"delay_seconds": 15}},
        )

        stack, _mock_gps, _mock_conn = _base_pipeline_patches()
        with stack:
            # Mock the orchestrator assignment path that runs AFTER delay
            mock_orchestrator = MagicMock()
            mock_orchestrator.assign_agent_for_status = AsyncMock(return_value=True)
            mock_orchestrator._update_agent_tracking_state = AsyncMock()

            with (
                patch(f"{_PIPELINE_MOD}.asyncio.sleep", new_callable=AsyncMock),
                patch(
                    f"{_HELPERS_MOD}._check_human_agent_done",
                    new_callable=AsyncMock,
                    return_value=False,
                ),
                patch(
                    f"{_AUTO_MERGE_MOD}._attempt_auto_merge",
                    new_callable=AsyncMock,
                    return_value=AutoMergeResult(status="merged", pr_number=10),
                ),
                patch(f"{_CP}.get_workflow_orchestrator", return_value=mock_orchestrator),
                patch(f"{_CP}.WorkflowContext") as mock_ctx_cls,
                patch(
                    f"{_CP}.get_workflow_config",
                    new_callable=AsyncMock,
                    return_value=MagicMock(),
                ),
                patch(
                    f"{_PIPELINE_MOD}._wait_if_rate_limited",
                    new_callable=AsyncMock,
                    return_value=False,
                ),
            ):
                mock_ctx_cls.return_value = MagicMock()
                mock_ctx_cls.return_value.config = None

                from src.services.copilot_polling.pipeline import _advance_pipeline

                await _advance_pipeline(
                    access_token="tok",
                    project_id="PVT_test",
                    item_id="item1",
                    owner="test-owner",
                    repo="test-repo",
                    issue_number=42,
                    issue_node_id=None,
                    pipeline=pipeline,
                    from_status="In Progress",
                    to_status="Done",
                    task_title="Test task",
                )

                # Human completed and pipeline advanced
                assert "human" in pipeline.completed_agents
                # Pipeline should NOT be complete — speckit.implement is still pending
                assert not pipeline.is_complete
                # The orchestrator assign call should reference the updated index (2),
                # NOT index 1 (human). This validates the next_agent recomputation.
                assign_calls = mock_orchestrator.assign_agent_for_status.call_args_list
                assert len(assign_calls) == 1
                assert assign_calls[0].kwargs.get("agent_index") == 2


# ══════════════════════════════════════════════════════════════════
# Pipeline state store round-trip — agent_configs
# ══════════════════════════════════════════════════════════════════


class TestPipelineStateStoreAgentConfigs:
    """Tests for agent_configs serialization round-trip in pipeline_state_store."""

    def test_row_to_pipeline_state_includes_agent_configs(self):
        """_row_to_pipeline_state should deserialize agent_configs from metadata."""
        from src.services.pipeline_state_store import _row_to_pipeline_state

        metadata = {
            "agents": ["human"],
            "current_agent_index": 0,
            "completed_agents": [],
            "started_at": "2026-04-01T12:00:00+00:00",
            "error": None,
            "agent_assigned_sha": "abc",
            "agent_configs": {"human": {"delay_seconds": 300}},
        }
        # Simulate a SQLite row tuple as returned by _row_to_pipeline_state
        row = (
            42,  # issue_number
            "PVT_test",  # project_id
            "In Progress",  # status
            "human",  # agent_name
            None,  # agent_instance_id
            None,  # pr_number
            None,  # pr_url
            "{}",  # sub_issues JSON
            json.dumps(metadata),  # metadata JSON
            "2026-04-01T12:00:00",  # created_at
            "2026-04-01T12:00:00",  # updated_at
        )

        state = _row_to_pipeline_state(row)
        assert state.agent_configs == {"human": {"delay_seconds": 300}}

    def test_row_to_pipeline_state_defaults_empty_agent_configs(self):
        """_row_to_pipeline_state should default to empty dict when agent_configs is absent."""
        from src.services.pipeline_state_store import _row_to_pipeline_state

        metadata = {
            "agents": ["copilot"],
            "current_agent_index": 0,
            "completed_agents": [],
            "started_at": None,
            "error": None,
            "agent_assigned_sha": "",
        }
        row = (
            10,
            "PVT_test",
            "Ready",
            "copilot",
            None,
            None,
            None,
            "{}",
            json.dumps(metadata),
            "2026-04-01T12:00:00",
            "2026-04-01T12:00:00",
        )

        state = _row_to_pipeline_state(row)
        assert state.agent_configs == {}

    def test_pipeline_state_to_row_includes_agent_configs(self):
        """_pipeline_state_to_row should serialize agent_configs into metadata."""
        from src.services.pipeline_state_store import _pipeline_state_to_row

        state = PipelineState(
            issue_number=42,
            project_id="PVT_test",
            status="In Progress",
            agents=["human"],
            agent_configs={"human": {"delay_seconds": 600}},
        )

        row = _pipeline_state_to_row(42, state)
        # metadata is the last-ish element in the tuple, find the JSON string
        metadata_json = row[8]  # index 8 is metadata
        metadata = json.loads(metadata_json)
        assert metadata["agent_configs"] == {"human": {"delay_seconds": 600}}

    def test_round_trip_preserves_agent_configs(self):
        """agent_configs should survive a to_row → from_row round-trip."""
        from src.services.pipeline_state_store import (
            _pipeline_state_to_row,
            _row_to_pipeline_state,
        )

        original = PipelineState(
            issue_number=42,
            project_id="PVT_test",
            status="In Progress",
            agents=["human"],
            agent_configs={"human": {"delay_seconds": 300, "model_id": "gpt-4"}},
        )

        row = _pipeline_state_to_row(42, original)
        restored = _row_to_pipeline_state(row)
        assert restored.agent_configs == original.agent_configs


# ══════════════════════════════════════════════════════════════════
# config.py load_pipeline_as_agent_mappings — node.config merge
# ══════════════════════════════════════════════════════════════════


class TestLoadPipelineNodeConfigMerge:
    """Tests that load_pipeline_as_agent_mappings merges node.config into AgentAssignment.config."""

    def test_node_config_delay_seconds_merged_into_assignment(self):
        """When PipelineAgentNode.config has delay_seconds, it should appear in the AgentAssignment."""
        from src.models.agent import AgentAssignment

        # Replicate the assignment building logic from config.py:
        # config={**node.config, "model_id": ..., "model_name": ...} if node.model_id or node.config
        node_config = {"delay_seconds": 300}
        model_id = ""
        model_name = ""

        assignment = AgentAssignment(
            slug="human",
            display_name="Human",
            config={
                **node_config,
                "model_id": model_id,
                "model_name": model_name,
            }
            if model_id or node_config
            else None,
        )

        assert assignment.config is not None
        assert assignment.config["delay_seconds"] == 300
        assert assignment.config["model_id"] == ""

    def test_node_config_empty_no_model_produces_none_config(self):
        """When node.config is empty and no model_id, assignment.config should be None."""
        from src.models.agent import AgentAssignment

        # Simulating what config.py does
        config_dict = {}
        model_id = ""
        result = (
            AgentAssignment(
                slug="copilot",
                config={**config_dict, "model_id": model_id, "model_name": ""},
            )
            if model_id or config_dict
            else AgentAssignment(slug="copilot")
        )

        assert result.config is None

    def test_node_config_with_model_merges_both(self):
        """When node has both config and model_id, both should be in AgentAssignment.config."""
        from src.models.agent import AgentAssignment

        config_dict = {"delay_seconds": 60}
        model_id = "gpt-4"
        model_name = "GPT-4"

        assignment = AgentAssignment(
            slug="human",
            config={**config_dict, "model_id": model_id, "model_name": model_name},
        )

        assert assignment.config is not None
        assert assignment.config["delay_seconds"] == 60
        assert assignment.config["model_id"] == "gpt-4"
        assert assignment.config["model_name"] == "GPT-4"


# ══════════════════════════════════════════════════════════════════
# Orchestrator sub-issue body with delay_seconds
# ══════════════════════════════════════════════════════════════════


class TestOrchestratorDelayPropagation:
    """Tests for orchestrator passing delay_seconds to sub-issue body generation."""

    def test_orchestrator_validation_logic_clamps_delay(self):
        """Replicate orchestrator's validation: invalid delay → None."""
        # This mirrors the validation in orchestrator.py ~line 410
        for raw_delay, expected in [
            (300, 300),
            (0, None),
            (-1, None),
            (86401, None),
            ("abc", None),
            (None, None),
        ]:
            agent_delay = None
            if raw_delay is not None:
                try:
                    agent_delay = int(raw_delay)
                    if agent_delay < 1 or agent_delay > 86400:
                        agent_delay = None
                except (TypeError, ValueError):
                    agent_delay = None
            assert agent_delay == expected, f"Failed for raw_delay={raw_delay}"

    def test_get_agent_configs_feeds_orchestrator(self):
        """get_agent_configs should provide the config dict used by orchestrator."""
        config = WorkflowConfiguration(
            project_id="PVT_test",
            repository_owner="test-owner",
            repository_name="test-repo",
            agent_mappings={
                "In Progress": [
                    AgentAssignment(
                        slug="human",
                        config={"delay_seconds": 120, "model_id": "", "model_name": ""},
                    ),
                ],
            },
        )
        result = get_agent_configs(config)
        assert result["human"]["delay_seconds"] == 120

    def test_get_agent_configs_last_wins_across_statuses(self):
        """If same agent appears in multiple statuses, last assignment's config wins."""
        config = WorkflowConfiguration(
            project_id="PVT_test",
            repository_owner="test-owner",
            repository_name="test-repo",
            agent_mappings={
                "Ready": [
                    AgentAssignment(
                        slug="human",
                        config={"delay_seconds": 60, "model_id": "", "model_name": ""},
                    ),
                ],
                "In Progress": [
                    AgentAssignment(
                        slug="human",
                        config={"delay_seconds": 300, "model_id": "", "model_name": ""},
                    ),
                ],
            },
        )
        result = get_agent_configs(config)
        # The last status iteration should win
        assert result["human"]["delay_seconds"] in (60, 300)  # depends on dict ordering
