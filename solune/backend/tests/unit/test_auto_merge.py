"""Unit tests for _attempt_auto_merge() and related auto-merge logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.copilot_polling.auto_merge import (
    AutoMergeResult,
    _attempt_auto_merge,
    _auto_merge_retry_loop,
    _build_devops_instructions,
    _check_devops_done_comment,
    _post_devops_retry_loop,
    dispatch_devops_agent,
    schedule_auto_merge_retry,
    schedule_post_devops_merge_retry,
)
from src.services.copilot_polling.state import (
    AUTO_MERGE_RETRY_BASE_DELAY,
    MAX_AUTO_MERGE_RETRIES,
)


@pytest.fixture()
def mock_service():
    """Mock the GitHub projects service used by auto_merge."""
    with patch("src.services.copilot_polling.get_github_service") as svc:
        svc = svc.return_value
        yield svc


@pytest.fixture()
def mock_discover():
    """Mock _discover_main_pr_for_review."""
    with patch(
        "src.services.copilot_polling.helpers._discover_main_pr_for_review",
        new_callable=AsyncMock,
    ) as discover:
        yield discover


@pytest.fixture()
def mock_ws():
    """Mock the WebSocket connection manager."""
    with patch("src.services.copilot_polling.connection_manager") as ws:
        ws.broadcast_to_project = AsyncMock()
        yield ws


class TestAttemptAutoMerge:
    """Tests for _attempt_auto_merge()."""

    @pytest.mark.asyncio
    async def test_success_path(self, mock_service, mock_discover):
        """CI passes, PR mergeable, squash merge succeeds → merged."""
        mock_discover.return_value = {
            "pr_number": 42,
            "pr_id": "PR_node_42",
            "head_ref": "feature-branch",
            "is_draft": False,
        }
        mock_service.get_check_runs_for_ref = AsyncMock(
            return_value=[
                {"status": "completed", "conclusion": "success", "name": "ci"},
            ]
        )
        mock_service.get_pr_mergeable_state = AsyncMock(return_value="MERGEABLE")
        mock_service.merge_pull_request = AsyncMock(
            return_value={"merged": True, "merge_commit": "abc123def456"}
        )

        result = await _attempt_auto_merge(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=10,
        )

        assert result.status == "merged"
        assert result.pr_number == 42
        assert result.merge_commit == "abc123def456"
        mock_service.merge_pull_request.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ci_failure_returns_devops_needed(self, mock_service, mock_discover):
        """CI failure → devops_needed."""
        mock_discover.return_value = {
            "pr_number": 42,
            "pr_id": "PR_node_42",
            "head_ref": "feature-branch",
            "is_draft": False,
        }
        mock_service.get_check_runs_for_ref = AsyncMock(
            return_value=[
                {
                    "status": "completed",
                    "conclusion": "failure",
                    "name": "ci-test",
                },
            ]
        )

        result = await _attempt_auto_merge(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=10,
        )

        assert result.status == "devops_needed"
        assert result.pr_number == 42
        assert result.context is not None
        assert result.context["reason"] == "ci_failure"

    @pytest.mark.asyncio
    async def test_conflicting_returns_devops_needed(self, mock_service, mock_discover):
        """CONFLICTING mergeability state → devops_needed."""
        mock_discover.return_value = {
            "pr_number": 42,
            "pr_id": "PR_node_42",
            "head_ref": "feature-branch",
            "is_draft": False,
        }
        mock_service.get_check_runs_for_ref = AsyncMock(
            return_value=[
                {"status": "completed", "conclusion": "success", "name": "ci"},
            ]
        )
        mock_service.get_pr_mergeable_state = AsyncMock(return_value="CONFLICTING")

        result = await _attempt_auto_merge(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=10,
        )

        assert result.status == "devops_needed"
        assert result.context is not None
        assert result.context["reason"] == "conflicting"

    @pytest.mark.asyncio
    async def test_merge_api_failure_returns_merge_failed(self, mock_service, mock_discover):
        """Merge API call fails → merge_failed."""
        mock_discover.return_value = {
            "pr_number": 42,
            "pr_id": "PR_node_42",
            "head_ref": "feature-branch",
            "is_draft": False,
        }
        mock_service.get_check_runs_for_ref = AsyncMock(
            return_value=[
                {"status": "completed", "conclusion": "success", "name": "ci"},
            ]
        )
        mock_service.get_pr_mergeable_state = AsyncMock(return_value="MERGEABLE")
        mock_service.merge_pull_request = AsyncMock(side_effect=Exception("API error"))

        result = await _attempt_auto_merge(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=10,
        )

        assert result.status == "merge_failed"
        assert result.pr_number == 42
        assert "API error" in (result.error or "")

    @pytest.mark.asyncio
    async def test_draft_pr_marked_ready(self, mock_service, mock_discover):
        """Draft PR should be marked ready-for-review before merge."""
        mock_discover.return_value = {
            "pr_number": 42,
            "pr_id": "PR_node_42",
            "head_ref": "feature-branch",
            "is_draft": True,
        }
        mock_service.mark_pr_ready_for_review = AsyncMock(return_value=True)
        mock_service.get_check_runs_for_ref = AsyncMock(
            return_value=[
                {"status": "completed", "conclusion": "success", "name": "ci"},
            ]
        )
        mock_service.get_pr_mergeable_state = AsyncMock(return_value="MERGEABLE")
        mock_service.merge_pull_request = AsyncMock(
            return_value={"merged": True, "merge_commit": "abc123"}
        )

        result = await _attempt_auto_merge(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=10,
        )

        assert result.status == "merged"
        mock_service.mark_pr_ready_for_review.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_pr_found_returns_merge_failed(self, mock_service, mock_discover):
        """No main PR found → merge_failed."""
        mock_discover.return_value = None

        result = await _attempt_auto_merge(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=10,
        )

        assert result.status == "merge_failed"
        assert "No main PR found" in (result.error or "")

    @pytest.mark.asyncio
    async def test_pending_checks_returns_retry_later(self, mock_service, mock_discover):
        """Checks still running → retry_later (not devops_needed)."""
        mock_discover.return_value = {
            "pr_number": 42,
            "pr_id": "PR_node_42",
            "head_ref": "feature-branch",
            "is_draft": False,
        }
        mock_service.get_check_runs_for_ref = AsyncMock(
            return_value=[
                {"status": "in_progress", "conclusion": None, "name": "ci"},
            ]
        )

        result = await _attempt_auto_merge(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=10,
        )

        assert result.status == "retry_later"
        assert result.context is not None
        assert result.context["reason"] == "checks_pending"

    @pytest.mark.asyncio
    async def test_missing_head_ref_returns_retry_later(self, mock_service, mock_discover):
        """Missing head_ref → retry_later (fail closed)."""
        mock_discover.return_value = {
            "pr_number": 42,
            "pr_id": "PR_node_42",
            "head_ref": "",
            "is_draft": False,
        }

        result = await _attempt_auto_merge(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=10,
        )

        assert result.status == "retry_later"
        assert result.context is not None
        assert result.context["reason"] == "ci_status_unavailable"

    @pytest.mark.asyncio
    async def test_check_runs_fetch_failure_returns_retry_later(self, mock_service, mock_discover):
        """Failed to fetch check runs → retry_later (fail closed)."""
        mock_discover.return_value = {
            "pr_number": 42,
            "pr_id": "PR_node_42",
            "head_ref": "feature-branch",
            "is_draft": False,
        }
        mock_service.get_check_runs_for_ref = AsyncMock(return_value=None)

        result = await _attempt_auto_merge(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=10,
        )

        assert result.status == "retry_later"
        assert result.context is not None
        assert result.context["reason"] == "ci_status_unavailable"

    @pytest.mark.asyncio
    async def test_unknown_mergeability_returns_retry_later(self, mock_service, mock_discover):
        """UNKNOWN mergeability → retry_later (not devops_needed)."""
        mock_discover.return_value = {
            "pr_number": 42,
            "pr_id": "PR_node_42",
            "head_ref": "feature-branch",
            "is_draft": False,
        }
        mock_service.get_check_runs_for_ref = AsyncMock(
            return_value=[
                {"status": "completed", "conclusion": "success", "name": "ci"},
            ]
        )
        mock_service.get_pr_mergeable_state = AsyncMock(return_value="UNKNOWN")

        result = await _attempt_auto_merge(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=10,
        )

        assert result.status == "retry_later"
        assert result.context is not None
        assert result.context["reason"] == "unknown_mergeability"


class TestDispatchDevopsAgent:
    """Tests for dispatch_devops_agent()."""

    @pytest.mark.asyncio
    async def test_dispatch_succeeds(self, mock_ws, mock_service):
        """First dispatch should succeed."""
        mock_service.get_issue_node_and_project_item = AsyncMock(
            return_value=("ISSUE_NODE_ID", "ITEM_ID")
        )
        mock_service.assign_copilot_to_issue = AsyncMock(return_value=True)
        metadata: dict = {}

        result = await dispatch_devops_agent(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=10,
            pipeline_metadata=metadata,
            project_id="PVT_123",
        )

        assert result is True
        assert metadata["devops_active"] is True
        assert metadata["devops_attempts"] == 1
        mock_service.assign_copilot_to_issue.assert_awaited_once()
        call_kwargs = mock_service.assign_copilot_to_issue.call_args[1]
        assert call_kwargs["custom_agent"] == "devops"

    @pytest.mark.asyncio
    async def test_dedup_skips_when_active(self, mock_ws):
        """Should skip dispatch when DevOps is already active."""
        metadata: dict = {"devops_active": True, "devops_attempts": 1}

        result = await dispatch_devops_agent(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=10,
            pipeline_metadata=metadata,
            project_id="PVT_123",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_retry_cap(self, mock_ws):
        """Should not dispatch after 2 attempts."""
        metadata: dict = {"devops_active": False, "devops_attempts": 2}

        result = await dispatch_devops_agent(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=10,
            pipeline_metadata=metadata,
            project_id="PVT_123",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_broadcasts_devops_triggered(self, mock_ws, mock_service):
        """Should broadcast devops_triggered event."""
        mock_service.get_issue_node_and_project_item = AsyncMock(
            return_value=("ISSUE_NODE_ID", "ITEM_ID")
        )
        mock_service.assign_copilot_to_issue = AsyncMock(return_value=True)
        metadata: dict = {}

        await dispatch_devops_agent(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=10,
            pipeline_metadata=metadata,
            project_id="PVT_123",
        )

        mock_ws.broadcast_to_project.assert_awaited_once()
        call_args = mock_ws.broadcast_to_project.call_args
        assert call_args[0][1]["type"] == "devops_triggered"


class TestAutoMergeResult:
    """Tests for AutoMergeResult dataclass."""

    def test_merged_result(self):
        result = AutoMergeResult(status="merged", pr_number=42, merge_commit="abc123")
        assert result.status == "merged"
        assert result.pr_number == 42
        assert result.merge_commit == "abc123"
        assert result.error is None

    def test_devops_needed_result(self):
        result = AutoMergeResult(
            status="devops_needed",
            pr_number=42,
            context={"reason": "ci_failure"},
        )
        assert result.status == "devops_needed"
        assert result.context is not None

    def test_merge_failed_result(self):
        result = AutoMergeResult(status="merge_failed", error="Branch protection")
        assert result.status == "merge_failed"
        assert result.error == "Branch protection"


class TestScheduleAutoMergeRetry:
    """Tests for schedule_auto_merge_retry()."""

    def test_schedules_retry_when_not_pending(self):
        """Should schedule a retry task and add it to _background_tasks."""
        mock_task = MagicMock()
        with patch(
            "src.services.copilot_polling.auto_merge.asyncio.create_task",
            return_value=mock_task,
        ) as mock_create_task:
            from src.services.copilot_polling.state import (
                _background_tasks,
                _pending_auto_merge_retries,
            )

            _pending_auto_merge_retries.pop(999, None)

            result = schedule_auto_merge_retry(
                access_token="token",
                owner="owner",
                repo="repo",
                issue_number=999,
                project_id="PVT_123",
                item_id="ITEM_1",
                task_title="Test",
            )

            assert result is True
            mock_create_task.assert_called_once()
            assert mock_task in _background_tasks
            mock_task.add_done_callback.assert_called_once()
            # Clean up
            _pending_auto_merge_retries.pop(999, None)
            _background_tasks.discard(mock_task)

    def test_skips_when_already_pending(self):
        """Should skip and return False if a retry is already pending."""
        from src.services.copilot_polling.state import _pending_auto_merge_retries

        _pending_auto_merge_retries[999] = 1

        with patch(
            "src.services.copilot_polling.auto_merge.asyncio.create_task"
        ) as mock_create_task:
            result = schedule_auto_merge_retry(
                access_token="token",
                owner="owner",
                repo="repo",
                issue_number=999,
                project_id="PVT_123",
                item_id="ITEM_1",
                task_title="Test",
            )

            assert result is False
            mock_create_task.assert_not_called()

        # Clean up
        _pending_auto_merge_retries.pop(999, None)


class TestAutoMergeRetryLoop:
    """Tests for _auto_merge_retry_loop()."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_second_attempt(self, mock_service, mock_ws):
        """retry_later then merged → success on attempt 2."""
        results = iter(
            [
                AutoMergeResult(
                    status="retry_later",
                    pr_number=42,
                    context={"reason": "checks_pending"},
                ),
                AutoMergeResult(
                    status="merged",
                    pr_number=42,
                    merge_commit="abc123",
                ),
            ]
        )

        with (
            patch(
                "src.services.copilot_polling.auto_merge._attempt_auto_merge",
                new_callable=AsyncMock,
                side_effect=lambda **_: next(results),
            ) as mock_attempt,
            patch(
                "src.services.copilot_polling.auto_merge.asyncio.sleep",
                new_callable=AsyncMock,
            ) as mock_sleep,
            patch(
                "src.services.copilot_polling.get_workflow_config",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("src.services.copilot_polling.get_github_service") as svc,
        ):
            svc.update_item_status_by_name = AsyncMock()
            svc.update_issue_state = AsyncMock()

            from src.services.copilot_polling.state import _pending_auto_merge_retries

            _pending_auto_merge_retries.pop(42, None)

            await _auto_merge_retry_loop(
                access_token="token",
                owner="owner",
                repo="repo",
                issue_number=42,
                project_id="PVT_123",
                item_id="ITEM_1",
                task_title="Test",
            )

            assert mock_attempt.await_count == 2
            # First delay = 45s, second delay = 90s
            assert mock_sleep.await_count == 2
            assert mock_sleep.await_args_list[0][0][0] == 45.0
            assert mock_sleep.await_args_list[1][0][0] == 90.0
            # Should have broadcast auto_merge_completed
            broadcast_calls = mock_ws.broadcast_to_project.call_args_list
            completed_events = [
                c for c in broadcast_calls if c[0][1].get("type") == "auto_merge_completed"
            ]
            assert len(completed_events) == 1
            # Tracking cleaned up
            assert 42 not in _pending_auto_merge_retries

    @pytest.mark.asyncio
    async def test_retry_exhausted_broadcasts_failure(self, mock_ws):
        """All retries return retry_later → broadcasts failure."""
        with (
            patch(
                "src.services.copilot_polling.auto_merge._attempt_auto_merge",
                new_callable=AsyncMock,
                return_value=AutoMergeResult(
                    status="retry_later",
                    pr_number=42,
                    context={"reason": "checks_pending"},
                ),
            ),
            patch(
                "src.services.copilot_polling.auto_merge.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            from src.services.copilot_polling.state import _pending_auto_merge_retries

            _pending_auto_merge_retries.pop(42, None)

            await _auto_merge_retry_loop(
                access_token="token",
                owner="owner",
                repo="repo",
                issue_number=42,
                project_id="PVT_123",
                item_id="ITEM_1",
                task_title="Test",
            )

            # Should broadcast auto_merge_failed
            broadcast_calls = mock_ws.broadcast_to_project.call_args_list
            failed_events = [
                c for c in broadcast_calls if c[0][1].get("type") == "auto_merge_failed"
            ]
            assert len(failed_events) == 1
            assert "retry" in failed_events[0][0][1]["error"].lower()
            # Tracking cleaned up
            assert 42 not in _pending_auto_merge_retries

    @pytest.mark.asyncio
    async def test_retry_devops_needed_dispatches_and_stops(self, mock_service, mock_ws):
        """retry_later then devops_needed → dispatches devops and stops retrying."""
        results = iter(
            [
                AutoMergeResult(
                    status="retry_later",
                    pr_number=42,
                    context={"reason": "checks_pending"},
                ),
                AutoMergeResult(
                    status="devops_needed",
                    pr_number=42,
                    context={"reason": "ci_failure", "failed_checks": []},
                ),
            ]
        )

        mock_service.get_issue_node_and_project_item = AsyncMock(
            return_value=("ISSUE_NODE_ID", "ITEM_ID")
        )
        mock_service.assign_copilot_to_issue = AsyncMock(return_value=True)

        with (
            patch(
                "src.services.copilot_polling.auto_merge._attempt_auto_merge",
                new_callable=AsyncMock,
                side_effect=lambda **_: next(results),
            ) as mock_attempt,
            patch(
                "src.services.copilot_polling.auto_merge.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            from src.services.copilot_polling.state import _pending_auto_merge_retries

            _pending_auto_merge_retries.pop(42, None)

            await _auto_merge_retry_loop(
                access_token="token",
                owner="owner",
                repo="repo",
                issue_number=42,
                project_id="PVT_123",
                item_id="ITEM_1",
                task_title="Test",
            )

            assert mock_attempt.await_count == 2
            mock_service.assign_copilot_to_issue.assert_awaited_once()
            assert 42 not in _pending_auto_merge_retries


class TestCheckDevopsDoneComment:
    """Tests for _check_devops_done_comment()."""

    @pytest.mark.asyncio
    async def test_returns_true_when_done_marker_present(self, mock_service):
        """Should return True when a comment contains 'devops: Done!'."""
        mock_service.get_issue_with_comments = AsyncMock(
            return_value={
                "title": "Test",
                "body": "",
                "comments": [
                    {"body": "Working on fixes..."},
                    {"body": "devops: Done!"},
                ],
                "user": {"login": ""},
            }
        )
        result = await _check_devops_done_comment(
            access_token="token", owner="owner", repo="repo", issue_number=10
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_no_done_marker(self, mock_service):
        """Should return False when no comment contains the marker."""
        mock_service.get_issue_with_comments = AsyncMock(
            return_value={
                "title": "Test",
                "body": "",
                "comments": [
                    {"body": "Working on fixes..."},
                    {"body": "Still debugging..."},
                ],
                "user": {"login": ""},
            }
        )
        result = await _check_devops_done_comment(
            access_token="token", owner="owner", repo="repo", issue_number=10
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_empty_comments(self, mock_service):
        """Should return False when there are no comments."""
        mock_service.get_issue_with_comments = AsyncMock(
            return_value={
                "title": "Test",
                "body": "",
                "comments": [],
                "user": {"login": ""},
            }
        )
        result = await _check_devops_done_comment(
            access_token="token", owner="owner", repo="repo", issue_number=10
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_api_error(self, mock_service):
        """Should return False when the API call fails."""
        mock_service.get_issue_with_comments = AsyncMock(side_effect=Exception("API error"))
        result = await _check_devops_done_comment(
            access_token="token", owner="owner", repo="repo", issue_number=10
        )
        assert result is False


class TestSchedulePostDevopsMergeRetry:
    """Tests for schedule_post_devops_merge_retry()."""

    def test_schedules_retry_when_not_pending(self):
        """Should schedule a retry task and add it to _background_tasks."""
        mock_task = MagicMock()
        with patch(
            "src.services.copilot_polling.auto_merge.asyncio.create_task",
            return_value=mock_task,
        ) as mock_create_task:
            from src.services.copilot_polling.state import (
                _background_tasks,
                _pending_post_devops_retries,
            )

            _pending_post_devops_retries.pop(777, None)

            result = schedule_post_devops_merge_retry(
                access_token="token",
                owner="owner",
                repo="repo",
                issue_number=777,
                pipeline_metadata={},
                project_id="PVT_123",
            )

            assert result is True
            mock_create_task.assert_called_once()
            assert mock_task in _background_tasks
            mock_task.add_done_callback.assert_called_once()
            # Clean up
            _pending_post_devops_retries.pop(777, None)
            _background_tasks.discard(mock_task)

    def test_skips_when_already_pending(self):
        """Should skip and return False if a retry is already pending."""
        from src.services.copilot_polling.state import _pending_post_devops_retries

        _pending_post_devops_retries[777] = {"project_id": "PVT_123"}

        with patch(
            "src.services.copilot_polling.auto_merge.asyncio.create_task"
        ) as mock_create_task:
            result = schedule_post_devops_merge_retry(
                access_token="token",
                owner="owner",
                repo="repo",
                issue_number=777,
                pipeline_metadata={},
                project_id="PVT_123",
            )

            assert result is False
            mock_create_task.assert_not_called()

        # Clean up
        _pending_post_devops_retries.pop(777, None)


class TestDispatchTriggersPostDevopsRetry:
    """Tests for dispatch_devops_agent() calling schedule_post_devops_merge_retry()."""

    @pytest.mark.asyncio
    async def test_dispatch_triggers_post_devops_retry(self, mock_ws, mock_service):
        """Successful dispatch should schedule post-DevOps retry."""
        mock_service.get_issue_node_and_project_item = AsyncMock(
            return_value=("ISSUE_NODE_ID", "ITEM_ID")
        )
        mock_service.assign_copilot_to_issue = AsyncMock(return_value=True)
        metadata: dict = {}

        with patch(
            "src.services.copilot_polling.auto_merge.schedule_post_devops_merge_retry"
        ) as mock_schedule:
            result = await dispatch_devops_agent(
                access_token="token",
                owner="owner",
                repo="repo",
                issue_number=10,
                pipeline_metadata=metadata,
                project_id="PVT_123",
            )

            assert result is True
            mock_schedule.assert_called_once_with(
                access_token="token",
                owner="owner",
                repo="repo",
                issue_number=10,
                pipeline_metadata=metadata,
                project_id="PVT_123",
            )


class TestDevopsCapBroadcast:
    """Tests for DevOps cap-reached broadcast on dispatch_devops_agent()."""

    @pytest.mark.asyncio
    async def test_cap_reached_broadcasts_failure(self, mock_ws):
        """Should broadcast auto_merge_failed with devops_cap_reached when cap is hit."""
        metadata: dict = {"devops_active": False, "devops_attempts": 2}

        result = await dispatch_devops_agent(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=10,
            pipeline_metadata=metadata,
            project_id="PVT_123",
        )

        assert result is False
        mock_ws.broadcast_to_project.assert_awaited_once()
        call_args = mock_ws.broadcast_to_project.call_args
        assert call_args[0][1]["type"] == "auto_merge_failed"
        assert call_args[0][1]["reason"] == "devops_cap_reached"


class TestBuildDevopsInstructions:
    """Tests for _build_devops_instructions()."""

    def test_ci_failure_context(self):
        """CI failure context → generates CI failure instructions."""
        context = {
            "reason": "ci_failure",
            "failed_checks": [
                {"name": "ci-tests", "conclusion": "failure"},
                {"name": "lint", "conclusion": "timed_out"},
            ],
        }
        result = _build_devops_instructions(
            owner="owner", repo="repo", issue_number=10, merge_result_context=context
        )
        assert "CI Failures" in result
        assert "**ci-tests**: failure" in result
        assert "**lint**: timed_out" in result
        assert "Fix merge/CI issues for issue #10 in owner/repo" in result

    def test_conflicting_context(self):
        """Conflicting mergeability → generates merge conflict instructions."""
        context = {"reason": "conflicting"}
        result = _build_devops_instructions(
            owner="owner", repo="repo", issue_number=20, merge_result_context=context
        )
        assert "Merge Conflicts" in result
        assert "conflicts" in result.lower()

    def test_no_context(self):
        """No context → generates generic fallback instructions."""
        result = _build_devops_instructions(
            owner="owner", repo="repo", issue_number=30, merge_result_context=None
        )
        assert "auto-merge attempt failed" in result
        assert "issue #30" in result.lower()

    def test_unknown_reason(self):
        """Unknown reason → generates generic instructions with the reason string."""
        context = {"reason": "some_other_error", "details": "Network timeout occurred"}
        result = _build_devops_instructions(
            owner="owner", repo="repo", issue_number=40, merge_result_context=context
        )
        assert "some_other_error" in result
        assert "Network timeout occurred" in result

    def test_unknown_reason_without_details(self):
        """Unknown reason without details → only heading, no extra lines."""
        context = {"reason": "something_else"}
        result = _build_devops_instructions(
            owner="owner", repo="repo", issue_number=50, merge_result_context=context
        )
        assert "something_else" in result

    def test_empty_context(self):
        """Empty dict context → fallback (``not {}`` is True in Python)."""
        result = _build_devops_instructions(
            owner="owner", repo="repo", issue_number=60, merge_result_context={}
        )
        # `not {}` evaluates to True, entering the fallback branch
        assert "auto-merge attempt failed" in result


class TestPostDevopsRetryLoop:
    """Tests for _post_devops_retry_loop()."""

    @pytest.mark.asyncio
    async def test_done_detected_merge_succeeds(self, mock_ws, mock_service):
        """DevOps 'Done!' detected → merge succeeds → broadcasts completion."""
        mock_check_done = AsyncMock(return_value=True)
        mock_attempt = AsyncMock(
            return_value=AutoMergeResult(status="merged", pr_number=42, merge_commit="sha123")
        )
        metadata: dict = {"devops_active": True, "devops_attempts": 1}

        with (
            patch(
                "src.services.copilot_polling.auto_merge._check_devops_done_comment",
                mock_check_done,
            ),
            patch(
                "src.services.copilot_polling.auto_merge._attempt_auto_merge",
                mock_attempt,
            ),
            patch(
                "src.services.copilot_polling.auto_merge.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            from src.services.copilot_polling.state import _pending_post_devops_retries

            _pending_post_devops_retries[42] = {"project_id": "PVT_123"}

            await _post_devops_retry_loop(
                access_token="token",
                owner="owner",
                repo="repo",
                issue_number=42,
                pipeline_metadata=metadata,
                project_id="PVT_123",
            )

            mock_check_done.assert_awaited_once()
            mock_attempt.assert_awaited_once()
            assert metadata["devops_active"] is False

            # Should broadcast post_devops_merge_completed
            broadcast_calls = mock_ws.broadcast_to_project.call_args_list
            completed_events = [
                c for c in broadcast_calls if c[0][1].get("type") == "post_devops_merge_completed"
            ]
            assert len(completed_events) == 1
            assert completed_events[0][0][1]["pr_number"] == 42
            assert completed_events[0][0][1]["merge_commit"] == "sha123"

            # Tracking cleaned up
            assert 42 not in _pending_post_devops_retries

    @pytest.mark.asyncio
    async def test_done_detected_devops_needed_re_dispatches(self, mock_ws, mock_service):
        """DevOps 'Done!' detected but merge still needs DevOps → re-dispatch."""
        mock_check_done = AsyncMock(return_value=True)
        mock_attempt = AsyncMock(
            return_value=AutoMergeResult(
                status="devops_needed",
                pr_number=42,
                context={"reason": "ci_failure", "failed_checks": []},
            )
        )
        mock_service.get_issue_node_and_project_item = AsyncMock(
            return_value=("NODE_ID", "ITEM_ID")
        )
        mock_service.assign_copilot_to_issue = AsyncMock(return_value=True)
        metadata: dict = {"devops_active": True, "devops_attempts": 1}

        with (
            patch(
                "src.services.copilot_polling.auto_merge._check_devops_done_comment",
                mock_check_done,
            ),
            patch(
                "src.services.copilot_polling.auto_merge._attempt_auto_merge",
                mock_attempt,
            ),
            patch(
                "src.services.copilot_polling.auto_merge.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            from src.services.copilot_polling.state import _pending_post_devops_retries

            _pending_post_devops_retries[42] = {"project_id": "PVT_123"}

            await _post_devops_retry_loop(
                access_token="token",
                owner="owner",
                repo="repo",
                issue_number=42,
                pipeline_metadata=metadata,
                project_id="PVT_123",
            )

            mock_check_done.assert_awaited_once()
            mock_attempt.assert_awaited_once()
            # DevOps should have been re-dispatched
            mock_service.assign_copilot_to_issue.assert_awaited_once()
            # Tracking cleaned up
            assert 42 not in _pending_post_devops_retries

    @pytest.mark.asyncio
    async def test_done_detected_merge_fails(self, mock_ws):
        """DevOps 'Done!' detected but merge fails → broadcasts failure and stops."""
        mock_check_done = AsyncMock(return_value=True)
        mock_attempt = AsyncMock(
            return_value=AutoMergeResult(
                status="merge_failed", pr_number=42, error="Branch protection"
            )
        )

        with (
            patch(
                "src.services.copilot_polling.auto_merge._check_devops_done_comment",
                mock_check_done,
            ),
            patch(
                "src.services.copilot_polling.auto_merge._attempt_auto_merge",
                mock_attempt,
            ),
            patch(
                "src.services.copilot_polling.auto_merge.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            from src.services.copilot_polling.state import _pending_post_devops_retries

            _pending_post_devops_retries[42] = {"project_id": "PVT_123"}

            await _post_devops_retry_loop(
                access_token="token",
                owner="owner",
                repo="repo",
                issue_number=42,
                pipeline_metadata={"devops_active": True, "devops_attempts": 1},
                project_id="PVT_123",
            )

            # Should broadcast auto_merge_failed
            broadcast_calls = mock_ws.broadcast_to_project.call_args_list
            failed_events = [
                c for c in broadcast_calls if c[0][1].get("type") == "auto_merge_failed"
            ]
            assert len(failed_events) == 1
            assert failed_events[0][0][1]["error"] == "Branch protection"
            assert 42 not in _pending_post_devops_retries

    @pytest.mark.asyncio
    async def test_done_detected_retry_later_continues_polling(self, mock_ws):
        """DevOps 'Done!' detected, merge returns retry_later → continues polling."""
        # First poll: done=True, merge=retry_later
        # Second poll: done=True, merge=merged
        done_side_effects = [True, True]
        merge_side_effects = [
            AutoMergeResult(
                status="retry_later",
                pr_number=42,
                context={"reason": "checks_pending"},
            ),
            AutoMergeResult(
                status="merged",
                pr_number=42,
                merge_commit="sha456",
            ),
        ]

        with (
            patch(
                "src.services.copilot_polling.auto_merge._check_devops_done_comment",
                new_callable=AsyncMock,
                side_effect=done_side_effects,
            ),
            patch(
                "src.services.copilot_polling.auto_merge._attempt_auto_merge",
                new_callable=AsyncMock,
                side_effect=merge_side_effects,
            ),
            patch(
                "src.services.copilot_polling.auto_merge.asyncio.sleep",
                new_callable=AsyncMock,
            ) as mock_sleep,
        ):
            from src.services.copilot_polling.state import _pending_post_devops_retries

            _pending_post_devops_retries[42] = {"project_id": "PVT_123"}

            await _post_devops_retry_loop(
                access_token="token",
                owner="owner",
                repo="repo",
                issue_number=42,
                pipeline_metadata={"devops_active": True, "devops_attempts": 1},
                project_id="PVT_123",
            )

            # Should have polled twice (sleep called twice)
            assert mock_sleep.await_count == 2
            # Should broadcast completion
            broadcast_calls = mock_ws.broadcast_to_project.call_args_list
            completed_events = [
                c for c in broadcast_calls if c[0][1].get("type") == "post_devops_merge_completed"
            ]
            assert len(completed_events) == 1
            assert 42 not in _pending_post_devops_retries

    @pytest.mark.asyncio
    async def test_polling_timeout(self, mock_ws):
        """Exhausting all polls without 'Done!' → broadcasts timeout failure."""
        with (
            patch(
                "src.services.copilot_polling.auto_merge._check_devops_done_comment",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "src.services.copilot_polling.auto_merge.asyncio.sleep",
                new_callable=AsyncMock,
            ),
            patch(
                "src.services.copilot_polling.state.POST_DEVOPS_MAX_POLLS",
                3,
            ),
        ):
            from src.services.copilot_polling.state import _pending_post_devops_retries

            _pending_post_devops_retries[42] = {"project_id": "PVT_123"}

            await _post_devops_retry_loop(
                access_token="token",
                owner="owner",
                repo="repo",
                issue_number=42,
                pipeline_metadata={"devops_active": True, "devops_attempts": 1},
                project_id="PVT_123",
            )

            # Should broadcast auto_merge_failed with devops_timeout
            broadcast_calls = mock_ws.broadcast_to_project.call_args_list
            failed_events = [
                c for c in broadcast_calls if c[0][1].get("type") == "auto_merge_failed"
            ]
            assert len(failed_events) == 1
            assert failed_events[0][0][1]["reason"] == "devops_timeout"
            assert 42 not in _pending_post_devops_retries

    @pytest.mark.asyncio
    async def test_cleanup_on_exception(self, mock_ws):
        """Exception during loop → finally block cleans up tracking state."""
        with (
            patch(
                "src.services.copilot_polling.auto_merge._check_devops_done_comment",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Unexpected"),
            ),
            patch(
                "src.services.copilot_polling.auto_merge.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            from src.services.copilot_polling.state import _pending_post_devops_retries

            _pending_post_devops_retries[42] = {"project_id": "PVT_123"}

            with pytest.raises(RuntimeError, match="Unexpected"):
                await _post_devops_retry_loop(
                    access_token="token",
                    owner="owner",
                    repo="repo",
                    issue_number=42,
                    pipeline_metadata={"devops_active": True, "devops_attempts": 1},
                    project_id="PVT_123",
                )

            # Finally block should have cleaned up
            assert 42 not in _pending_post_devops_retries


class TestDispatchDevopsAgentEdgeCases:
    """Edge case tests for dispatch_devops_agent()."""

    @pytest.mark.asyncio
    async def test_node_id_resolution_failure(self, mock_ws, mock_service):
        """When issue node ID resolution raises an exception, dispatch should return False."""
        mock_service.get_issue_node_and_project_item = AsyncMock(
            side_effect=Exception("GraphQL error")
        )
        metadata: dict = {"devops_active": False, "devops_attempts": 0}

        result = await dispatch_devops_agent(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=10,
            pipeline_metadata=metadata,
            project_id="PVT_123",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_node_id_returns_none(self, mock_ws, mock_service):
        """When issue node ID resolution returns None, dispatch should return False."""
        mock_service.get_issue_node_and_project_item = AsyncMock(return_value=(None, "ITEM_ID"))
        metadata: dict = {"devops_active": False, "devops_attempts": 0}

        result = await dispatch_devops_agent(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=10,
            pipeline_metadata=metadata,
            project_id="PVT_123",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_copilot_assignment_exception(self, mock_ws, mock_service):
        """When Copilot assignment throws, dispatch should return False."""
        mock_service.get_issue_node_and_project_item = AsyncMock(
            return_value=("ISSUE_NODE_ID", "ITEM_ID")
        )
        mock_service.assign_copilot_to_issue = AsyncMock(
            side_effect=Exception("Assignment API error")
        )
        metadata: dict = {"devops_active": False, "devops_attempts": 0}

        result = await dispatch_devops_agent(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=10,
            pipeline_metadata=metadata,
            project_id="PVT_123",
        )

        assert result is False
        assert metadata.get("devops_active") is not True

    @pytest.mark.asyncio
    async def test_copilot_assignment_returns_false(self, mock_ws, mock_service):
        """When Copilot assignment returns False, dispatch should return False."""
        mock_service.get_issue_node_and_project_item = AsyncMock(
            return_value=("ISSUE_NODE_ID", "ITEM_ID")
        )
        mock_service.assign_copilot_to_issue = AsyncMock(return_value=False)
        metadata: dict = {"devops_active": False, "devops_attempts": 0}

        result = await dispatch_devops_agent(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=10,
            pipeline_metadata=metadata,
            project_id="PVT_123",
        )

        assert result is False
        assert metadata.get("devops_active") is not True

    @pytest.mark.asyncio
    async def test_merge_result_context_passed_to_instructions(self, mock_ws, mock_service):
        """dispatch should pass merge_result_context to _build_devops_instructions."""
        mock_service.get_issue_node_and_project_item = AsyncMock(
            return_value=("ISSUE_NODE_ID", "ITEM_ID")
        )
        mock_service.assign_copilot_to_issue = AsyncMock(return_value=True)
        metadata: dict = {"devops_active": False, "devops_attempts": 0}
        context = {
            "reason": "ci_failure",
            "failed_checks": [{"name": "build", "conclusion": "failure"}],
        }

        with patch(
            "src.services.copilot_polling.auto_merge._build_devops_instructions",
            wraps=_build_devops_instructions,
        ) as mock_build:
            result = await dispatch_devops_agent(
                access_token="token",
                owner="owner",
                repo="repo",
                issue_number=10,
                pipeline_metadata=metadata,
                project_id="PVT_123",
                merge_result_context=context,
            )

        assert result is True
        mock_build.assert_called_once_with(
            owner="owner",
            repo="repo",
            issue_number=10,
            merge_result_context=context,
        )
        # Verify custom_instructions was passed to assignment
        call_kwargs = mock_service.assign_copilot_to_issue.call_args[1]
        assert "CI Failures" in call_kwargs["custom_instructions"]
        assert "**build**: failure" in call_kwargs["custom_instructions"]


class TestRetryWindowConstants:
    """Tests for auto-merge retry window constants (Phase 1)."""

    def test_max_auto_merge_retries_is_five(self):
        """MAX_AUTO_MERGE_RETRIES should be 5 to cover slow CI."""
        assert MAX_AUTO_MERGE_RETRIES == 5

    def test_auto_merge_retry_base_delay_is_45(self):
        """AUTO_MERGE_RETRY_BASE_DELAY should be 45.0 for faster first retry."""
        assert AUTO_MERGE_RETRY_BASE_DELAY == 45.0

    def test_total_backoff_covers_slow_ci(self):
        """Total exponential backoff should cover at least 15 minutes (900s)."""
        total = sum(AUTO_MERGE_RETRY_BASE_DELAY * (2**i) for i in range(MAX_AUTO_MERGE_RETRIES))
        assert total >= 900  # At least 15 minutes


class TestWebhookL2Fallback:
    """Tests for _get_auto_merge_pipeline() L2 and project-level fallback."""

    @pytest.mark.asyncio
    async def test_l1_miss_l2_hit_returns_pipeline(self):
        """L1 cache miss + L2 SQLite hit → returns pipeline metadata."""
        from src.api.webhooks import _get_auto_merge_pipeline

        l2_pipeline = MagicMock()
        l2_pipeline.is_complete = True
        l2_pipeline.auto_merge = True
        l2_pipeline.project_id = "PVT_123"

        with (
            patch(
                "src.services.copilot_polling.get_pipeline_state",
                return_value=None,
            ),
            patch(
                "src.services.copilot_polling.get_pipeline_state_async",
                new_callable=AsyncMock,
                return_value=l2_pipeline,
            ),
        ):
            result = await _get_auto_merge_pipeline(10, "owner", "repo")
            assert result is not None
            assert result["project_id"] == "PVT_123"
            assert result["devops_attempts"] == 0
            assert result["devops_active"] is False

    @pytest.mark.asyncio
    async def test_l1_l2_miss_project_auto_merge_returns_metadata(self):
        """L1+L2 miss but project auto-merge enabled → returns metadata."""
        from src.api.webhooks import _get_auto_merge_pipeline

        # L2 returns a state with project_id (but not auto_merge)
        l2_state = MagicMock()
        l2_state.is_complete = False
        l2_state.auto_merge = False
        l2_state.project_id = "PVT_456"

        with (
            patch(
                "src.services.copilot_polling.get_pipeline_state",
                return_value=None,
            ),
            patch(
                "src.services.copilot_polling.get_pipeline_state_async",
                new_callable=AsyncMock,
                return_value=l2_state,
            ),
            patch(
                "src.services.copilot_polling.get_db",
                return_value=MagicMock(),
            ),
            patch(
                "src.services.copilot_polling.is_auto_merge_enabled",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            result = await _get_auto_merge_pipeline(10, "owner", "repo")
            assert result is not None
            assert result["project_id"] == "PVT_456"
            assert result["devops_attempts"] == 0

    @pytest.mark.asyncio
    async def test_all_miss_returns_none(self):
        """L1, L2, and project-level all miss → returns None."""
        from src.api.webhooks import _get_auto_merge_pipeline

        with (
            patch(
                "src.services.copilot_polling.get_pipeline_state",
                return_value=None,
            ),
            patch(
                "src.services.copilot_polling.get_pipeline_state_async",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.copilot_polling.get_db",
                return_value=MagicMock(),
            ),
            patch(
                "src.services.copilot_polling.is_auto_merge_enabled",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "src.services.workflow_orchestrator.transitions._issue_main_branches",
                {},
            ),
        ):
            result = await _get_auto_merge_pipeline(10, "owner", "repo")
            assert result is None

    @pytest.mark.asyncio
    async def test_l1_no_auto_merge_project_level_fallback_uses_l1_project_id(self):
        """L1 pipeline exists without auto_merge → Step C uses L1's project_id for project-level check."""
        from src.api.webhooks import _get_auto_merge_pipeline

        # L1 returns a pipeline that is complete but auto_merge is False
        # (e.g. a reconstructed pipeline that lost the flag — root cause #3)
        l1_pipeline = MagicMock()
        l1_pipeline.is_complete = True
        l1_pipeline.auto_merge = False
        l1_pipeline.project_id = "PVT_L1"

        with (
            patch(
                "src.services.copilot_polling.get_pipeline_state",
                return_value=l1_pipeline,
            ),
            # L2 is skipped when L1 is not None, but patch for safety
            patch(
                "src.services.copilot_polling.get_pipeline_state_async",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.copilot_polling.get_db",
                return_value=MagicMock(),
            ),
            patch(
                "src.services.copilot_polling.is_auto_merge_enabled",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            result = await _get_auto_merge_pipeline(10, "owner", "repo")
            assert result is not None
            assert result["project_id"] == "PVT_L1"
            assert result["devops_attempts"] == 0
            assert result["devops_active"] is False


class TestDeferredRemoval:
    """Tests for deferred pipeline state removal during auto-merge retry."""

    @pytest.mark.asyncio
    async def test_state_not_removed_on_retry_later(self, mock_ws):
        """Pipeline state should NOT be removed when merge returns retry_later."""
        mock_remove = MagicMock()
        with (
            patch(
                "src.services.copilot_polling.auto_merge._attempt_auto_merge",
                new_callable=AsyncMock,
                return_value=AutoMergeResult(
                    status="retry_later",
                    pr_number=42,
                    context={"reason": "checks_pending"},
                ),
            ),
            patch(
                "src.services.copilot_polling.auto_merge.asyncio.sleep",
                new_callable=AsyncMock,
            ),
            patch(
                "src.services.copilot_polling.remove_pipeline_state",
                mock_remove,
            ),
        ):
            from src.services.copilot_polling.state import _pending_auto_merge_retries

            _pending_auto_merge_retries.pop(42, None)

            await _auto_merge_retry_loop(
                access_token="token",
                owner="owner",
                repo="repo",
                issue_number=42,
                project_id="PVT_123",
                item_id="ITEM_1",
                task_title="Test",
            )

            # remove_pipeline_state is called once at exhaust (or in finally),
            # but never during the retry_later iterations.
            # After exhaustion, it should be called exactly once.
            assert mock_remove.call_count == 1

    @pytest.mark.asyncio
    async def test_state_removed_after_retry_succeeds(self, mock_ws):
        """Pipeline state should be removed after retry succeeds with 'merged'."""
        results = iter(
            [
                AutoMergeResult(
                    status="retry_later",
                    pr_number=42,
                    context={"reason": "checks_pending"},
                ),
                AutoMergeResult(
                    status="merged",
                    pr_number=42,
                    merge_commit="abc123",
                ),
            ]
        )
        mock_remove = MagicMock()
        with (
            patch(
                "src.services.copilot_polling.auto_merge._attempt_auto_merge",
                new_callable=AsyncMock,
                side_effect=lambda **_: next(results),
            ),
            patch(
                "src.services.copilot_polling.auto_merge.asyncio.sleep",
                new_callable=AsyncMock,
            ),
            patch(
                "src.services.copilot_polling.get_workflow_config",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("src.services.copilot_polling.get_github_service") as svc,
            patch(
                "src.services.copilot_polling.remove_pipeline_state",
                mock_remove,
            ),
        ):
            svc.update_item_status_by_name = AsyncMock()
            svc.update_issue_state = AsyncMock()

            from src.services.copilot_polling.state import _pending_auto_merge_retries

            _pending_auto_merge_retries.pop(42, None)

            await _auto_merge_retry_loop(
                access_token="token",
                owner="owner",
                repo="repo",
                issue_number=42,
                project_id="PVT_123",
                item_id="ITEM_1",
                task_title="Test",
            )

            mock_remove.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_state_removed_after_retries_exhausted(self, mock_ws):
        """Pipeline state should be removed after all retries are exhausted."""
        mock_remove = MagicMock()
        with (
            patch(
                "src.services.copilot_polling.auto_merge._attempt_auto_merge",
                new_callable=AsyncMock,
                return_value=AutoMergeResult(
                    status="retry_later",
                    pr_number=42,
                    context={"reason": "checks_pending"},
                ),
            ),
            patch(
                "src.services.copilot_polling.auto_merge.asyncio.sleep",
                new_callable=AsyncMock,
            ),
            patch(
                "src.services.copilot_polling.remove_pipeline_state",
                mock_remove,
            ),
        ):
            from src.services.copilot_polling.state import _pending_auto_merge_retries

            _pending_auto_merge_retries.pop(42, None)

            await _auto_merge_retry_loop(
                access_token="token",
                owner="owner",
                repo="repo",
                issue_number=42,
                project_id="PVT_123",
                item_id="ITEM_1",
                task_title="Test",
            )

            mock_remove.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_state_removed_on_merge_failed(self, mock_ws):
        """Pipeline state should be removed immediately on merge_failed."""
        results = iter(
            [
                AutoMergeResult(
                    status="merge_failed",
                    pr_number=42,
                    error="merge conflict",
                ),
            ]
        )
        mock_remove = MagicMock()
        with (
            patch(
                "src.services.copilot_polling.auto_merge._attempt_auto_merge",
                new_callable=AsyncMock,
                side_effect=lambda **_: next(results),
            ),
            patch(
                "src.services.copilot_polling.auto_merge.asyncio.sleep",
                new_callable=AsyncMock,
            ),
            patch(
                "src.services.copilot_polling.remove_pipeline_state",
                mock_remove,
            ),
        ):
            from src.services.copilot_polling.state import _pending_auto_merge_retries

            _pending_auto_merge_retries.pop(42, None)

            await _auto_merge_retry_loop(
                access_token="token",
                owner="owner",
                repo="repo",
                issue_number=42,
                project_id="PVT_123",
                item_id="ITEM_1",
                task_title="Test",
            )

            mock_remove.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_finally_safety_net_removes_state(self, mock_ws):
        """Finally block should remove state if not already removed (on exception)."""
        mock_remove = MagicMock()
        with (
            patch(
                "src.services.copilot_polling.auto_merge._attempt_auto_merge",
                new_callable=AsyncMock,
                side_effect=RuntimeError("unexpected"),
            ),
            patch(
                "src.services.copilot_polling.auto_merge.asyncio.sleep",
                new_callable=AsyncMock,
            ),
            patch(
                "src.services.copilot_polling.remove_pipeline_state",
                mock_remove,
            ),
        ):
            from src.services.copilot_polling.state import _pending_auto_merge_retries

            _pending_auto_merge_retries.pop(42, None)

            # The function will raise due to the unexpected error, but the
            # finally block should still clean up pipeline state.
            with pytest.raises(RuntimeError, match="unexpected"):
                await _auto_merge_retry_loop(
                    access_token="token",
                    owner="owner",
                    repo="repo",
                    issue_number=42,
                    project_id="PVT_123",
                    item_id="ITEM_1",
                    task_title="Test",
                )

            # The finally safety net should have called remove_pipeline_state
            mock_remove.assert_called_once_with(42)

