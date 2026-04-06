"""Tests for polling_loop.py — PollStep, stop_polling, get_polling_status (T103)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.copilot_polling.polling_loop import (
    POLL_STEPS,
    PollStep,
    get_polling_status,
    poll_app_pipeline,
    stop_polling,
)


class TestPollStep:
    """PollStep is a frozen dataclass describing a single polling step."""

    def test_default_not_expensive(self):
        async def noop():
            return []

        step = PollStep(name="test", execute=noop)
        assert step.name == "test"
        assert step.is_expensive is False

    def test_expensive(self):
        async def noop():
            return []

        step = PollStep(name="test", execute=noop, is_expensive=True)
        assert step.is_expensive is True

    def test_frozen(self):
        async def noop():
            return []

        step = PollStep(name="test", execute=noop)
        with pytest.raises(AttributeError):
            setattr(step, "name", "other")


class TestPollSteps:
    """POLL_STEPS is the ordered list of polling steps."""

    def test_has_expected_count(self):
        assert len(POLL_STEPS) == 7

    def test_all_are_poll_step_instances(self):
        for step in POLL_STEPS:
            assert isinstance(step, PollStep)

    def test_expensive_steps(self):
        expensive = [s.name for s in POLL_STEPS if s.is_expensive]
        assert "Step 0: agent outputs" in expensive
        assert "Step 5: stalled recovery" in expensive

    def test_all_steps_have_execute_callable(self):
        for step in POLL_STEPS:
            assert callable(step.execute)


class TestStopPolling:
    """stop_polling() sets is_running=False and cancels any active task."""

    @pytest.mark.asyncio
    async def test_sets_is_running_false(self):
        with (
            patch("src.services.copilot_polling.polling_loop._polling_state") as mock_state,
            patch("src.services.copilot_polling.polling_loop._cp") as mock_cp,
        ):
            mock_state.is_running = True
            mock_cp._polling_task = None
            await stop_polling()
            assert mock_state.is_running is False

    @pytest.mark.asyncio
    async def test_cancels_active_task(self):
        mock_task = MagicMock()
        mock_task.done.return_value = False
        with (
            patch("src.services.copilot_polling.polling_loop._polling_state") as mock_state,
            patch("src.services.copilot_polling.polling_loop._cp") as mock_cp,
        ):
            mock_cp._polling_task = mock_task
            await stop_polling()
            mock_task.cancel.assert_called_once()
            assert mock_state.is_running is False

    @pytest.mark.asyncio
    async def test_skips_cancel_when_task_done(self):
        mock_task = MagicMock()
        mock_task.done.return_value = True
        with (
            patch("src.services.copilot_polling.polling_loop._polling_state") as mock_state,
            patch("src.services.copilot_polling.polling_loop._cp") as mock_cp,
        ):
            mock_cp._polling_task = mock_task
            await stop_polling()
            mock_task.cancel.assert_not_called()
            assert mock_state.is_running is False


class TestGetPollingStatus:
    """get_polling_status() returns a dict of current polling state."""

    def test_default_state(self):
        with (
            patch("src.services.copilot_polling.polling_loop._polling_state") as mock_state,
            patch(
                "src.services.copilot_polling.polling_loop._processed_issue_prs",
                new=set(),
            ),
            patch("src.services.copilot_polling.polling_loop._cp") as mock_cp,
        ):
            mock_state.is_running = False
            mock_state.last_poll_time = None
            mock_state.poll_count = 0
            mock_state.errors_count = 0
            mock_state.last_error = None
            mock_cp.github_projects_service.get_last_rate_limit.return_value = None

            status = get_polling_status()
            assert status["is_running"] is False
            assert status["last_poll_time"] is None
            assert status["poll_count"] == 0
            assert status["rate_limit"] is None

    def test_with_rate_limit_info(self):
        with (
            patch("src.services.copilot_polling.polling_loop._polling_state") as mock_state,
            patch(
                "src.services.copilot_polling.polling_loop._processed_issue_prs",
                new={"1:2", "3:4"},
            ),
            patch("src.services.copilot_polling.polling_loop._cp") as mock_cp,
        ):
            mock_state.is_running = True
            mock_state.last_poll_time = datetime(2024, 6, 15, 10, 0, tzinfo=UTC)
            mock_state.poll_count = 5
            mock_state.errors_count = 1
            mock_state.last_error = "timeout"
            mock_cp.github_projects_service.get_last_rate_limit.return_value = {
                "limit": 5000,
                "remaining": 4500,
                "used": 500,
                "reset_at": 1718445600,
            }

            status = get_polling_status()
            assert status["is_running"] is True
            assert status["poll_count"] == 5
            assert status["errors_count"] == 1
            assert status["last_error"] == "timeout"
            assert status["processed_issues_count"] == 2
            rate_limit = status["rate_limit"]
            assert rate_limit is not None
            assert rate_limit.get("remaining") == 4500


class TestPollAppPipeline:
    """Tests for the scoped poll_app_pipeline() function."""

    async def test_runs_all_steps_including_expensive(self):
        """When rate-limit budget is healthy, expensive steps should execute."""
        executed_steps: list[str] = []

        async def _fake_execute(_at, _pid, _o, _r, _tasks, *, _name=""):
            executed_steps.append(_name)
            return []

        fake_steps = [
            PollStep(
                name=f"step-{i}",
                execute=lambda at, pid, o, r, t, n=f"step-{i}": _fake_execute(
                    at, pid, o, r, t, _name=n
                ),
                is_expensive=(i in (0, 5)),
            )
            for i in range(7)
        ]

        # First call: state not complete; second call: is_complete=True (exit)
        mock_state_active = MagicMock(is_complete=False)
        mock_state_done = MagicMock(is_complete=True)

        with (
            patch(
                "src.services.copilot_polling.polling_loop.POLL_STEPS",
                fake_steps,
            ),
            patch("src.services.copilot_polling.polling_loop._cp") as mock_cp,
            patch(
                "src.services.copilot_polling.polling_loop._check_rate_limit_budget",
                new_callable=AsyncMock,
                return_value=(5000, None),  # plenty of budget
            ),
            patch(
                "src.services.copilot_polling.polling_loop.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            mock_cp.get_pipeline_state.side_effect = [
                mock_state_active,  # pre-steps check
                mock_state_done,  # post-steps re-check
            ]
            mock_cp.github_projects_service.get_project_items = AsyncMock(return_value=[])
            mock_cp.github_projects_service.clear_cycle_cache = MagicMock()

            await poll_app_pipeline("tok", "proj", "owner", "repo", 42)

        # All 7 steps (including expensive 0 and 5) should have run
        assert len(executed_steps) == 7
        assert "step-0" in executed_steps
        assert "step-5" in executed_steps

    async def test_skips_expensive_when_rate_limit_low(self):
        """Expensive steps are skipped when rate-limit budget is low."""
        executed_steps: list[str] = []

        async def _fake_execute(_at, _pid, _o, _r, _tasks, *, _name=""):
            executed_steps.append(_name)
            return []

        fake_steps = [
            PollStep(
                name=f"step-{i}",
                execute=lambda at, pid, o, r, t, n=f"step-{i}": _fake_execute(
                    at, pid, o, r, t, _name=n
                ),
                is_expensive=(i in (0, 5)),
            )
            for i in range(7)
        ]

        mock_state_active = MagicMock(is_complete=False)
        mock_state_done = MagicMock(is_complete=True)

        with (
            patch(
                "src.services.copilot_polling.polling_loop.POLL_STEPS",
                fake_steps,
            ),
            patch("src.services.copilot_polling.polling_loop._cp") as mock_cp,
            patch(
                "src.services.copilot_polling.polling_loop._check_rate_limit_budget",
                new_callable=AsyncMock,
                return_value=(10, None),  # very low budget (below 100 threshold)
            ),
            patch(
                "src.services.copilot_polling.polling_loop.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            mock_cp.get_pipeline_state.side_effect = [
                mock_state_active,
                mock_state_done,
            ]
            mock_cp.github_projects_service.get_project_items = AsyncMock(return_value=[])
            mock_cp.github_projects_service.clear_cycle_cache = MagicMock()

            await poll_app_pipeline("tok", "proj", "owner", "repo", 42)

        # Only non-expensive steps should have run (5 out of 7)
        assert len(executed_steps) == 5
        assert "step-0" not in executed_steps
        assert "step-5" not in executed_steps

    async def test_survives_missing_state_up_to_three_cycles(self):
        """Pipeline state being None should not immediately kill the loop."""

        async def _noop(*_args, **_kwargs):
            return []

        fake_steps = [PollStep(name="noop", execute=_noop)]

        with (
            patch(
                "src.services.copilot_polling.polling_loop.POLL_STEPS",
                fake_steps,
            ),
            patch("src.services.copilot_polling.polling_loop._cp") as mock_cp,
            patch(
                "src.services.copilot_polling.polling_loop._check_rate_limit_budget",
                new_callable=AsyncMock,
                return_value=(5000, None),
            ),
            patch(
                "src.services.copilot_polling.polling_loop.asyncio.sleep",
                new_callable=AsyncMock,
            ) as mock_sleep,
        ):
            # Return non-complete state for pre-check, None for post-check
            # This simulates state being transiently unavailable.
            mock_cp.get_pipeline_state.side_effect = [
                MagicMock(is_complete=False),  # cycle 1 pre
                None,  # cycle 1 post → missing (1/3)
                MagicMock(is_complete=False),  # cycle 2 pre
                None,  # cycle 2 post → missing (2/3)
                MagicMock(is_complete=False),  # cycle 3 pre
                None,  # cycle 3 post → missing (3/3) → break
            ]
            mock_cp.github_projects_service.get_project_items = AsyncMock(return_value=[])
            mock_cp.github_projects_service.clear_cycle_cache = MagicMock()

            await poll_app_pipeline("tok", "proj", "owner", "repo", 42)

        # Should have slept twice (after cycles 1 and 2) then exited on cycle 3
        assert mock_sleep.call_count == 2
