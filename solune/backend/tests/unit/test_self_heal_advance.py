"""Tests for self-heal restart-recovery additions in recovery.py and polling_loop.py.

Covers ``_drive_advance_after_self_heal`` (sync advance after self-heal Done!
markers) and ``_startup_resume_scan`` (one-shot recovery sweep at backend
startup).  These guard against the race window where a backend restart
between agent completion and the next polling cycle leaves the pipeline
dormant.
"""

from __future__ import annotations

from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_CP = "src.services.copilot_polling"
_REC = f"{_CP}.recovery"
_PL = f"{_CP}.polling_loop"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _make_task(*, issue_number: int = 42) -> SimpleNamespace:
    return SimpleNamespace(
        issue_number=issue_number,
        github_item_id=f"item-{issue_number}",
        github_content_id=f"content-{issue_number}",
        title=f"Issue #{issue_number} title",
        repository_owner="octo",
        repository_name="repo",
    )


# ── _drive_advance_after_self_heal ────────────────────────────────


class TestDriveAdvanceAfterSelfHeal:
    """Tests for the synchronous _advance_pipeline driver."""

    async def test_drives_advance_when_pipeline_present(self):
        """Cached pipeline + non-empty status → _advance_pipeline is awaited."""
        task = _make_task()
        pipeline = SimpleNamespace(
            is_complete=False,
            status="In Progress",
            original_status=None,
            current_agent="architect",
        )

        with ExitStack() as stack:
            stack.enter_context(patch(f"{_REC}._advance_pipeline_locks", {}))
            stack.enter_context(patch(f"{_CP}.get_pipeline_state", return_value=pipeline))
            stack.enter_context(patch(f"{_CP}.get_next_status", return_value="In Review"))
            advance = AsyncMock(return_value={"status": "success"})
            stack.enter_context(patch(f"{_CP}.pipeline._advance_pipeline", advance))

            from src.services.copilot_polling.recovery import (
                _drive_advance_after_self_heal,
            )

            ok = await _drive_advance_after_self_heal(
                access_token="tok",
                project_id="proj-1",
                owner="octo",
                repo="repo",
                task=task,
                issue_number=42,
                agent_name="architect",
                config=SimpleNamespace(),
            )

        assert ok is True
        advance.assert_awaited_once()
        kwargs = advance.await_args.kwargs
        assert kwargs["from_status"] == "In Progress"
        assert kwargs["to_status"] == "In Review"
        assert kwargs["pipeline"] is pipeline

    async def test_skips_when_lock_already_held(self):
        """A recently-acquired lock for the same key short-circuits the advance."""
        task = _make_task()
        held_at = _utcnow()
        locks = {"42:architect": held_at}

        with ExitStack() as stack:
            stack.enter_context(patch(f"{_REC}._advance_pipeline_locks", locks))
            advance = AsyncMock()
            stack.enter_context(patch(f"{_CP}.pipeline._advance_pipeline", advance))
            # get_pipeline_state must not be called when lock blocks early
            gps = MagicMock(return_value=None)
            stack.enter_context(patch(f"{_CP}.get_pipeline_state", gps))

            from src.services.copilot_polling.recovery import (
                _drive_advance_after_self_heal,
            )

            ok = await _drive_advance_after_self_heal(
                access_token="tok",
                project_id="proj-1",
                owner="octo",
                repo="repo",
                task=task,
                issue_number=42,
                agent_name="architect",
                config=SimpleNamespace(),
            )

        assert ok is True  # treated as in-flight, not failure
        advance.assert_not_awaited()

    async def test_returns_false_when_reconstruction_fails(self):
        """No cached pipeline + reconstruction returning None → returns False."""
        task = _make_task()

        with ExitStack() as stack:
            stack.enter_context(patch(f"{_REC}._advance_pipeline_locks", {}))
            stack.enter_context(patch(f"{_CP}.get_pipeline_state", return_value=None))
            reconstruct = AsyncMock(return_value=None)
            stack.enter_context(
                patch(
                    f"{_CP}.agent_output._reconstruct_pipeline_if_missing",
                    reconstruct,
                )
            )
            advance = AsyncMock()
            stack.enter_context(patch(f"{_CP}.pipeline._advance_pipeline", advance))

            from src.services.copilot_polling.recovery import (
                _drive_advance_after_self_heal,
            )

            ok = await _drive_advance_after_self_heal(
                access_token="tok",
                project_id="proj-1",
                owner="octo",
                repo="repo",
                task=task,
                issue_number=42,
                agent_name="architect",
                config=SimpleNamespace(),
            )

        assert ok is False
        advance.assert_not_awaited()
        assert reconstruct.await_args.kwargs["preserve_current_agent"] == "architect"

    async def test_skips_when_reconstructed_pipeline_has_moved_past_agent(self):
        """If reconstruction shows a later current agent, no second advance is driven."""
        task = _make_task()
        reconstructed = SimpleNamespace(
            is_complete=False,
            status="In Progress",
            original_status=None,
            current_agent="judge",
        )

        with ExitStack() as stack:
            stack.enter_context(patch(f"{_REC}._advance_pipeline_locks", {}))
            stack.enter_context(patch(f"{_CP}.get_pipeline_state", return_value=None))
            reconstruct = AsyncMock(return_value=reconstructed)
            stack.enter_context(
                patch(
                    f"{_CP}.agent_output._reconstruct_pipeline_if_missing",
                    reconstruct,
                )
            )
            advance = AsyncMock()
            stack.enter_context(patch(f"{_CP}.pipeline._advance_pipeline", advance))

            from src.services.copilot_polling.recovery import (
                _drive_advance_after_self_heal,
            )

            ok = await _drive_advance_after_self_heal(
                access_token="tok",
                project_id="proj-1",
                owner="octo",
                repo="repo",
                task=task,
                issue_number=42,
                agent_name="architect",
                config=SimpleNamespace(),
            )

        assert ok is True
        advance.assert_not_awaited()
        assert reconstruct.await_args.kwargs["preserve_current_agent"] == "architect"

    async def test_expired_lock_does_not_block(self):
        """A lock older than the TTL is treated as released."""
        task = _make_task()
        from src.services.copilot_polling.state import (
            ADVANCE_PIPELINE_LOCK_TTL_SECONDS,
        )

        stale = _utcnow() - timedelta(seconds=ADVANCE_PIPELINE_LOCK_TTL_SECONDS + 60)
        locks = {"42:architect": stale}

        pipeline = SimpleNamespace(
            is_complete=False,
            status="In Progress",
            original_status=None,
            current_agent="architect",
        )

        with ExitStack() as stack:
            stack.enter_context(patch(f"{_REC}._advance_pipeline_locks", locks))
            stack.enter_context(patch(f"{_CP}.get_pipeline_state", return_value=pipeline))
            stack.enter_context(patch(f"{_CP}.get_next_status", return_value="In Review"))
            advance = AsyncMock(return_value={"status": "success"})
            stack.enter_context(patch(f"{_CP}.pipeline._advance_pipeline", advance))

            from src.services.copilot_polling.recovery import (
                _drive_advance_after_self_heal,
            )

            ok = await _drive_advance_after_self_heal(
                access_token="tok",
                project_id="proj-1",
                owner="octo",
                repo="repo",
                task=task,
                issue_number=42,
                agent_name="architect",
                config=SimpleNamespace(),
            )

        assert ok is True
        advance.assert_awaited_once()


# ── _startup_resume_scan ──────────────────────────────────────────


class TestStartupResumeScan:
    """Tests for the one-shot recovery sweep on polling startup."""

    async def test_invokes_recover_stalled_issues(self):
        """The scan delegates to recover_stalled_issues and tolerates empty results."""
        recover = AsyncMock(return_value=[])
        with (
            patch(f"{_PL}._check_rate_limit_budget", AsyncMock(return_value=(None, None))),
            patch(f"{_CP}.recover_stalled_issues", recover),
        ):
            from src.services.copilot_polling.polling_loop import _startup_resume_scan

            await _startup_resume_scan("tok", "proj-1", "octo", "repo")

        recover.assert_awaited_once_with(
            access_token="tok",
            project_id="proj-1",
            owner="octo",
            repo="repo",
        )

    async def test_logs_summary_when_actions_taken(self):
        """When recover_stalled_issues returns actions, the scan logs them."""
        recover = AsyncMock(
            return_value=[
                {"issue_number": 42, "status": "recovered"},
                {"issue_number": 43, "status": "recovered"},
            ]
        )
        with (
            patch(f"{_PL}._check_rate_limit_budget", AsyncMock(return_value=(None, None))),
            patch(f"{_CP}.recover_stalled_issues", recover),
        ):
            from src.services.copilot_polling.polling_loop import _startup_resume_scan

            # Should not raise on non-empty results
            await _startup_resume_scan("tok", "proj-1", "octo", "repo")

        recover.assert_awaited_once()

    async def test_swallows_recover_exception(self):
        """Errors from recover_stalled_issues must not propagate to the loop."""
        recover = AsyncMock(side_effect=RuntimeError("boom"))
        with (
            patch(f"{_PL}._check_rate_limit_budget", AsyncMock(return_value=(None, None))),
            patch(f"{_CP}.recover_stalled_issues", recover),
        ):
            from src.services.copilot_polling.polling_loop import _startup_resume_scan

            # Must not raise — startup must never be blocked by recovery failure
            await _startup_resume_scan("tok", "proj-1", "octo", "repo")

        recover.assert_awaited_once()

    async def test_skips_recovery_when_rate_limit_budget_low(self):
        """Startup scan should not spend calls on expensive recovery when budget is low."""
        from src.services.copilot_polling.state import RATE_LIMIT_SKIP_EXPENSIVE_THRESHOLD

        recover = AsyncMock(return_value=[])
        with (
            patch(
                f"{_PL}._check_rate_limit_budget",
                AsyncMock(return_value=(RATE_LIMIT_SKIP_EXPENSIVE_THRESHOLD, None)),
            ),
            patch(f"{_CP}.recover_stalled_issues", recover),
        ):
            from src.services.copilot_polling.polling_loop import _startup_resume_scan

            await _startup_resume_scan("tok", "proj-1", "octo", "repo")

        recover.assert_not_awaited()


class TestReconstructPipelineIfMissing:
    """Tests for reconstruction anchored to the tracking table's active agent."""

    async def test_preserves_tracking_tables_current_agent_when_requested(self):
        """A synthetic Done! marker must not shift reconstruction to the next agent."""
        body = """
---

## 🤖 Agents Pipelines

| # | Status | Agent | Model | State |
|---|--------|-------|-------|-------|
| 1 | In Progress | `linter` | TBD | ✅ Done |
| 2 | In Progress | `architect` | TBD | 🔄 Active |
| 3 | In Progress | `judge` | TBD | ⏳ Pending |
"""
        comments = [
            {"body": "linter: Done!", "created_at": "2026-04-19T00:00:00+00:00"},
            {"body": "architect: Done!", "created_at": "2026-04-19T00:01:00+00:00"},
        ]

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    f"{_CP}._get_tracking_state_from_issue",
                    AsyncMock(return_value=(body, comments)),
                )
            )
            stack.enter_context(patch(f"{_CP}.get_pipeline_state", return_value=None))
            stack.enter_context(patch(f"{_CP}.set_pipeline_state"))
            stack.enter_context(
                patch(
                    f"{_CP}._reconstruct_sub_issue_mappings",
                    AsyncMock(return_value={}),
                )
            )
            stack.enter_context(
                patch(
                    f"{_CP}.get_issue_main_branch",
                    return_value={"head_sha": "abc123", "branch": "main", "pr_number": 12},
                )
            )

            from src.services.copilot_polling.agent_output import (
                _reconstruct_pipeline_if_missing,
            )

            pipeline = await _reconstruct_pipeline_if_missing(
                access_token="tok",
                owner="octo",
                repo="repo",
                issue_number=42,
                project_id="proj-1",
                preserve_current_agent="architect",
            )

        assert pipeline is not None
        assert pipeline.current_agent == "architect"
        assert pipeline.current_agent_index == 1
        assert pipeline.completed_agents == ["linter"]


@pytest.fixture(autouse=True)
def _clear_advance_locks():
    """Ensure each test starts with an empty _advance_pipeline_locks dict."""
    from src.services.copilot_polling.state import _advance_pipeline_locks

    _advance_pipeline_locks.clear()
    yield
    _advance_pipeline_locks.clear()
