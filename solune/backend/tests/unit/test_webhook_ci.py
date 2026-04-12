"""Unit tests for webhook CI failure detection and routing."""

from __future__ import annotations

import pytest

from src.api.webhook_models import (
    CheckRunData,
    CheckRunEvent,
    CheckRunPR,
    CheckSuiteData,
    CheckSuiteEvent,
    OwnerData,
    RepositoryData,
)


class TestCheckRunEventModel:
    """Tests for CheckRunEvent Pydantic model."""

    def test_parse_completed_failure(self):
        """Parse a check_run completed with failure."""
        raw = {
            "action": "completed",
            "check_run": {
                "id": 123,
                "name": "test-suite",
                "status": "completed",
                "conclusion": "failure",
                "head_sha": "abc123",
                "pull_requests": [
                    {
                        "number": 42,
                        "head": {"ref": "feature-branch"},
                        "base": {"ref": "main"},
                    }
                ],
            },
            "repository": {
                "name": "test-repo",
                "owner": {"login": "owner"},
            },
        }
        event = CheckRunEvent.model_validate(raw)
        assert event.action == "completed"
        assert event.check_run.conclusion == "failure"
        assert event.check_run.name == "test-suite"
        assert len(event.check_run.pull_requests) == 1
        assert event.check_run.pull_requests[0].number == 42

    def test_parse_timed_out(self):
        """Parse a check_run with timed_out conclusion."""
        raw = {
            "action": "completed",
            "check_run": {
                "id": 456,
                "name": "integration-test",
                "status": "completed",
                "conclusion": "timed_out",
                "head_sha": "def456",
                "pull_requests": [],
            },
            "repository": {
                "name": "test-repo",
                "owner": {"login": "owner"},
            },
        }
        event = CheckRunEvent.model_validate(raw)
        assert event.check_run.conclusion == "timed_out"

    def test_extra_fields_ignored(self):
        """Extra fields should be ignored (ConfigDict extra='ignore')."""
        raw = {
            "action": "completed",
            "check_run": {
                "id": 789,
                "name": "test",
                "status": "completed",
                "conclusion": "success",
                "head_sha": "ghi789",
                "pull_requests": [],
                "extra_field": "should be ignored",
            },
            "repository": {
                "name": "test-repo",
                "owner": {"login": "owner"},
                "extra": True,
            },
            "sender": {"login": "user"},
        }
        event = CheckRunEvent.model_validate(raw)
        assert event.action == "completed"


class TestCheckSuiteEventModel:
    """Tests for CheckSuiteEvent Pydantic model."""

    def test_parse_completed_failure(self):
        """Parse a check_suite completed with failure."""
        raw = {
            "action": "completed",
            "check_suite": {
                "id": 100,
                "status": "completed",
                "conclusion": "failure",
                "head_sha": "abc123",
                "pull_requests": [
                    {
                        "number": 99,
                        "head": {"ref": "fix-branch"},
                        "base": {"ref": "main"},
                    }
                ],
            },
            "repository": {
                "name": "test-repo",
                "owner": {"login": "owner"},
            },
        }
        event = CheckSuiteEvent.model_validate(raw)
        assert event.action == "completed"
        assert event.check_suite.conclusion == "failure"
        assert len(event.check_suite.pull_requests) == 1

    def test_parse_success(self):
        """Parse a check_suite with success conclusion."""
        raw = {
            "action": "completed",
            "check_suite": {
                "id": 200,
                "status": "completed",
                "conclusion": "success",
                "head_sha": "def456",
                "pull_requests": [],
            },
            "repository": {
                "name": "test-repo",
                "owner": {"login": "owner"},
            },
        }
        event = CheckSuiteEvent.model_validate(raw)
        assert event.check_suite.conclusion == "success"


class TestWebhookRouting:
    """Tests for check_run/check_suite webhook handler routing logic."""

    @pytest.mark.asyncio
    async def test_check_run_failure_processed(self):
        """check_run with failure conclusion should be processed."""
        from src.api.webhooks import handle_check_run_event

        event = CheckRunEvent(
            action="completed",
            check_run=CheckRunData(
                id=1,
                name="test-ci",
                status="completed",
                conclusion="failure",
                head_sha="abc123",
                pull_requests=[
                    CheckRunPR(number=42),
                ],
            ),
            repository=RepositoryData(
                name="repo",
                owner=OwnerData(login="owner"),
            ),
        )
        result = await handle_check_run_event(event)
        assert result["status"] == "processed"
        assert result["event"] == "check_run_failure"
        assert 42 in result["pr_numbers"]

    @pytest.mark.asyncio
    async def test_check_run_timed_out_processed(self):
        """check_run with timed_out conclusion should be processed."""
        from src.api.webhooks import handle_check_run_event

        event = CheckRunEvent(
            action="completed",
            check_run=CheckRunData(
                id=2,
                name="slow-test",
                status="completed",
                conclusion="timed_out",
                head_sha="def456",
                pull_requests=[CheckRunPR(number=99)],
            ),
            repository=RepositoryData(
                name="repo",
                owner=OwnerData(login="owner"),
            ),
        )
        result = await handle_check_run_event(event)
        assert result["status"] == "processed"
        assert result["conclusion"] == "timed_out"

    @pytest.mark.asyncio
    async def test_check_run_success_ignored(self):
        """check_run with success conclusion should be ignored."""
        from src.api.webhooks import handle_check_run_event

        event = CheckRunEvent(
            action="completed",
            check_run=CheckRunData(
                id=3,
                name="test",
                status="completed",
                conclusion="success",
                head_sha="ghi789",
                pull_requests=[CheckRunPR(number=1)],
            ),
            repository=RepositoryData(
                name="repo",
                owner=OwnerData(login="owner"),
            ),
        )
        result = await handle_check_run_event(event)
        assert result["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_check_run_non_completed_ignored(self):
        """check_run with non-completed action should be ignored."""
        from src.api.webhooks import handle_check_run_event

        event = CheckRunEvent(
            action="created",
            check_run=CheckRunData(
                id=4,
                name="test",
                status="queued",
                head_sha="jkl012",
                pull_requests=[],
            ),
            repository=RepositoryData(
                name="repo",
                owner=OwnerData(login="owner"),
            ),
        )
        result = await handle_check_run_event(event)
        assert result["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_check_suite_failure_processed(self):
        """check_suite with failure conclusion should be processed."""
        from src.api.webhooks import handle_check_suite_event

        event = CheckSuiteEvent(
            action="completed",
            check_suite=CheckSuiteData(
                id=10,
                status="completed",
                conclusion="failure",
                head_sha="abc123",
                pull_requests=[CheckRunPR(number=55)],
            ),
            repository=RepositoryData(
                name="repo",
                owner=OwnerData(login="owner"),
            ),
        )
        result = await handle_check_suite_event(event)
        assert result["status"] == "processed"
        assert result["event"] == "check_suite_failure"

    @pytest.mark.asyncio
    async def test_check_suite_success_processed(self):
        """check_suite with success conclusion should be processed (triggers re-merge)."""
        from src.api.webhooks import handle_check_suite_event

        event = CheckSuiteEvent(
            action="completed",
            check_suite=CheckSuiteData(
                id=20,
                status="completed",
                conclusion="success",
                head_sha="def456",
                pull_requests=[CheckRunPR(number=1)],
            ),
            repository=RepositoryData(
                name="repo",
                owner=OwnerData(login="owner"),
            ),
        )
        result = await handle_check_suite_event(event)
        assert result["status"] == "processed"
        assert result["event"] == "check_suite_success"

    @pytest.mark.asyncio
    async def test_check_suite_no_prs_ignored(self):
        """check_suite with no associated PRs should be ignored."""
        from src.api.webhooks import handle_check_suite_event

        event = CheckSuiteEvent(
            action="completed",
            check_suite=CheckSuiteData(
                id=30,
                status="completed",
                conclusion="failure",
                head_sha="ghi789",
                pull_requests=[],
            ),
            repository=RepositoryData(
                name="repo",
                owner=OwnerData(login="owner"),
            ),
        )
        result = await handle_check_suite_event(event)
        assert result["status"] == "ignored"
        assert result["reason"] == "no_associated_prs"


class TestWebhookDevopsDispatch:
    """Tests for check_run webhook dispatching DevOps agent."""

    @pytest.mark.asyncio
    async def test_check_run_dispatches_devops_when_issue_found(self):
        """check_run failure should dispatch DevOps when PR is linked to auto-merge issue."""
        from unittest.mock import AsyncMock, patch

        from src.api.webhooks import handle_check_run_event

        event = CheckRunEvent(
            action="completed",
            check_run=CheckRunData(
                id=100,
                name="ci-tests",
                status="completed",
                conclusion="failure",
                head_sha="abc123",
                pull_requests=[CheckRunPR(number=42)],
            ),
            repository=RepositoryData(
                name="repo",
                owner=OwnerData(login="owner"),
            ),
        )

        mock_settings = type("Settings", (), {"github_webhook_token": "test-token"})()

        with (
            patch(
                "src.api.webhooks.check_runs._resolve_issue_for_pr",
                return_value=10,
            ),
            patch(
                "src.api.webhooks.check_runs._get_auto_merge_pipeline",
                return_value={
                    "project_id": "PVT_123",
                    "devops_attempts": 0,
                    "devops_active": False,
                },
            ),
            patch("src.api.webhooks.check_runs.get_settings", return_value=mock_settings),
            patch(
                "src.services.copilot_polling.auto_merge.dispatch_devops_agent",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_dispatch,
        ):
            result = await handle_check_run_event(event)

        assert result["status"] == "processed"
        assert result["devops_dispatched"] is True
        mock_dispatch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_run_no_dispatch_when_no_linked_issue(self):
        """check_run failure without linked issue should not dispatch DevOps."""
        from unittest.mock import patch

        from src.api.webhooks import handle_check_run_event

        event = CheckRunEvent(
            action="completed",
            check_run=CheckRunData(
                id=101,
                name="ci-tests",
                status="completed",
                conclusion="failure",
                head_sha="abc123",
                pull_requests=[CheckRunPR(number=42)],
            ),
            repository=RepositoryData(
                name="repo",
                owner=OwnerData(login="owner"),
            ),
        )

        with patch(
            "src.api.webhooks.check_runs._resolve_issue_for_pr",
            return_value=None,
        ):
            result = await handle_check_run_event(event)

        assert result["status"] == "processed"
        assert result["devops_dispatched"] is False


class TestWebhookAutoMerge:
    """Tests for check_suite webhook triggering auto-merge."""

    @pytest.mark.asyncio
    async def test_check_suite_success_attempts_merge(self):
        """check_suite success should attempt auto-merge for linked issues."""
        from unittest.mock import AsyncMock, patch

        from src.api.webhooks import handle_check_suite_event

        event = CheckSuiteEvent(
            action="completed",
            check_suite=CheckSuiteData(
                id=200,
                status="completed",
                conclusion="success",
                head_sha="def456",
                pull_requests=[CheckRunPR(number=42)],
            ),
            repository=RepositoryData(
                name="repo",
                owner=OwnerData(login="owner"),
            ),
        )

        mock_settings = type("Settings", (), {"github_webhook_token": "test-token"})()

        with (
            patch(
                "src.api.webhooks.check_runs._resolve_issue_for_pr",
                return_value=10,
            ),
            patch(
                "src.api.webhooks.check_runs._get_auto_merge_pipeline",
                return_value={
                    "project_id": "PVT_123",
                    "devops_attempts": 0,
                    "devops_active": False,
                },
            ),
            patch("src.api.webhooks.check_runs.get_settings", return_value=mock_settings),
            patch(
                "src.services.copilot_polling.auto_merge._attempt_auto_merge",
                new_callable=AsyncMock,
                return_value=type("Result", (), {"status": "merged"})(),
            ) as mock_merge,
        ):
            result = await handle_check_suite_event(event)

        assert result["status"] == "processed"
        assert result["event"] == "check_suite_success"
        assert result["merge_attempted"] is True
        mock_merge.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_suite_success_no_merge_when_no_issue(self):
        """check_suite success without linked issue should not attempt merge."""
        from unittest.mock import patch

        from src.api.webhooks import handle_check_suite_event

        event = CheckSuiteEvent(
            action="completed",
            check_suite=CheckSuiteData(
                id=201,
                status="completed",
                conclusion="success",
                head_sha="def456",
                pull_requests=[CheckRunPR(number=42)],
            ),
            repository=RepositoryData(
                name="repo",
                owner=OwnerData(login="owner"),
            ),
        )

        with patch(
            "src.api.webhooks.check_runs._resolve_issue_for_pr",
            return_value=None,
        ):
            result = await handle_check_suite_event(event)

        assert result["status"] == "processed"
        assert result["event"] == "check_suite_success"
        assert result["merge_attempted"] is False

    @pytest.mark.asyncio
    async def test_check_suite_neutral_ignored(self):
        """check_suite with neutral conclusion should be ignored."""
        from src.api.webhooks import handle_check_suite_event

        event = CheckSuiteEvent(
            action="completed",
            check_suite=CheckSuiteData(
                id=202,
                status="completed",
                conclusion="neutral",
                head_sha="abc123",
                pull_requests=[CheckRunPR(number=1)],
            ),
            repository=RepositoryData(
                name="repo",
                owner=OwnerData(login="owner"),
            ),
        )
        result = await handle_check_suite_event(event)
        assert result["status"] == "ignored"
        assert result["reason"] == "conclusion_not_relevant"


class TestCheckRunDevopsDispatchEdgeCases:
    """Edge case tests for check_run DevOps dispatch path."""

    @pytest.mark.asyncio
    async def test_check_run_dispatch_exception_handled_gracefully(self):
        """When dispatch_devops_agent raises, handler should still return processed."""
        from unittest.mock import AsyncMock, patch

        from src.api.webhooks import handle_check_run_event

        event = CheckRunEvent(
            action="completed",
            check_run=CheckRunData(
                id=300,
                name="ci-tests",
                status="completed",
                conclusion="failure",
                head_sha="abc123",
                pull_requests=[CheckRunPR(number=42)],
            ),
            repository=RepositoryData(
                name="repo",
                owner=OwnerData(login="owner"),
            ),
        )

        mock_settings = type("Settings", (), {"github_webhook_token": "test-token"})()

        with (
            patch("src.api.webhooks.check_runs._resolve_issue_for_pr", return_value=10),
            patch(
                "src.api.webhooks.check_runs._get_auto_merge_pipeline",
                return_value={
                    "project_id": "PVT_123",
                    "devops_attempts": 0,
                    "devops_active": False,
                },
            ),
            patch("src.api.webhooks.check_runs.get_settings", return_value=mock_settings),
            patch(
                "src.services.copilot_polling.auto_merge.dispatch_devops_agent",
                new_callable=AsyncMock,
                side_effect=Exception("Dispatch failed"),
            ),
        ):
            result = await handle_check_run_event(event)

        assert result["status"] == "processed"
        assert result["devops_dispatched"] is False

    @pytest.mark.asyncio
    async def test_check_run_no_pipeline_no_dispatch(self):
        """When pipeline is None for the linked issue, no dispatch occurs."""
        from unittest.mock import patch

        from src.api.webhooks import handle_check_run_event

        event = CheckRunEvent(
            action="completed",
            check_run=CheckRunData(
                id=301,
                name="ci-tests",
                status="completed",
                conclusion="failure",
                head_sha="abc123",
                pull_requests=[CheckRunPR(number=42)],
            ),
            repository=RepositoryData(
                name="repo",
                owner=OwnerData(login="owner"),
            ),
        )

        with (
            patch("src.api.webhooks.check_runs._resolve_issue_for_pr", return_value=10),
            patch("src.api.webhooks.check_runs._get_auto_merge_pipeline", return_value=None),
        ):
            result = await handle_check_run_event(event)

        assert result["status"] == "processed"
        assert result["devops_dispatched"] is False

    @pytest.mark.asyncio
    async def test_check_run_no_webhook_token(self):
        """When no webhook token is available, handler should not dispatch."""
        from unittest.mock import patch

        from src.api.webhooks import handle_check_run_event

        event = CheckRunEvent(
            action="completed",
            check_run=CheckRunData(
                id=302,
                name="ci-tests",
                status="completed",
                conclusion="failure",
                head_sha="abc123",
                pull_requests=[CheckRunPR(number=42)],
            ),
            repository=RepositoryData(
                name="repo",
                owner=OwnerData(login="owner"),
            ),
        )

        mock_settings = type("Settings", (), {"github_webhook_token": ""})()

        with (
            patch("src.api.webhooks.check_runs._resolve_issue_for_pr", return_value=10),
            patch(
                "src.api.webhooks.check_runs._get_auto_merge_pipeline",
                return_value={"project_id": "PVT_123"},
            ),
            patch("src.api.webhooks.check_runs.get_settings", return_value=mock_settings),
        ):
            result = await handle_check_run_event(event)

        assert result["status"] == "processed"
        assert result["devops_dispatched"] is False

    @pytest.mark.asyncio
    async def test_check_run_timed_out_dispatches_devops(self):
        """check_run with timed_out conclusion should also dispatch DevOps."""
        from unittest.mock import AsyncMock, patch

        from src.api.webhooks import handle_check_run_event

        event = CheckRunEvent(
            action="completed",
            check_run=CheckRunData(
                id=303,
                name="integration-tests",
                status="completed",
                conclusion="timed_out",
                head_sha="abc123",
                pull_requests=[CheckRunPR(number=42)],
            ),
            repository=RepositoryData(
                name="repo",
                owner=OwnerData(login="owner"),
            ),
        )

        mock_settings = type("Settings", (), {"github_webhook_token": "test-token"})()

        with (
            patch("src.api.webhooks.check_runs._resolve_issue_for_pr", return_value=10),
            patch(
                "src.api.webhooks.check_runs._get_auto_merge_pipeline",
                return_value={
                    "project_id": "PVT_123",
                    "devops_attempts": 0,
                    "devops_active": False,
                },
            ),
            patch("src.api.webhooks.check_runs.get_settings", return_value=mock_settings),
            patch(
                "src.services.copilot_polling.auto_merge.dispatch_devops_agent",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_dispatch,
        ):
            result = await handle_check_run_event(event)

        assert result["status"] == "processed"
        assert result["devops_dispatched"] is True
        mock_dispatch.assert_awaited_once()
        # Verify merge_result_context contains timed_out conclusion
        call_kwargs = mock_dispatch.call_args[1]
        assert call_kwargs["merge_result_context"]["reason"] == "ci_failure"
        assert call_kwargs["merge_result_context"]["failed_checks"][0]["conclusion"] == "timed_out"

    @pytest.mark.asyncio
    async def test_check_run_multiple_prs_dispatches_for_each(self):
        """check_run with multiple PRs should attempt dispatch for each linked issue."""
        from unittest.mock import AsyncMock, patch

        from src.api.webhooks import handle_check_run_event

        event = CheckRunEvent(
            action="completed",
            check_run=CheckRunData(
                id=304,
                name="ci-tests",
                status="completed",
                conclusion="failure",
                head_sha="abc123",
                pull_requests=[CheckRunPR(number=42), CheckRunPR(number=43)],
            ),
            repository=RepositoryData(
                name="repo",
                owner=OwnerData(login="owner"),
            ),
        )

        mock_settings = type("Settings", (), {"github_webhook_token": "test-token"})()

        # Both PRs linked to different issues
        def resolve_issue(pr_num: int) -> int | None:
            return {42: 10, 43: 11}.get(pr_num)

        with (
            patch("src.api.webhooks.check_runs._resolve_issue_for_pr", side_effect=resolve_issue),
            patch(
                "src.api.webhooks.check_runs._get_auto_merge_pipeline",
                return_value={
                    "project_id": "PVT_123",
                    "devops_attempts": 0,
                    "devops_active": False,
                },
            ),
            patch("src.api.webhooks.check_runs.get_settings", return_value=mock_settings),
            patch(
                "src.services.copilot_polling.auto_merge.dispatch_devops_agent",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_dispatch,
        ):
            result = await handle_check_run_event(event)

        assert result["status"] == "processed"
        assert result["devops_dispatched"] is True
        assert mock_dispatch.await_count == 2


class TestCheckSuiteAutoMergeEdgeCases:
    """Edge case tests for check_suite auto-merge path."""

    @pytest.mark.asyncio
    async def test_check_suite_success_merge_exception_handled(self):
        """When auto-merge raises during check_suite success, handler returns processed."""
        from unittest.mock import AsyncMock, patch

        from src.api.webhooks import handle_check_suite_event

        event = CheckSuiteEvent(
            action="completed",
            check_suite=CheckSuiteData(
                id=400,
                status="completed",
                conclusion="success",
                head_sha="def456",
                pull_requests=[CheckRunPR(number=42)],
            ),
            repository=RepositoryData(
                name="repo",
                owner=OwnerData(login="owner"),
            ),
        )

        mock_settings = type("Settings", (), {"github_webhook_token": "test-token"})()

        with (
            patch("src.api.webhooks.check_runs._resolve_issue_for_pr", return_value=10),
            patch(
                "src.api.webhooks.check_runs._get_auto_merge_pipeline",
                return_value={"project_id": "PVT_123"},
            ),
            patch("src.api.webhooks.check_runs.get_settings", return_value=mock_settings),
            patch(
                "src.services.copilot_polling.auto_merge._attempt_auto_merge",
                new_callable=AsyncMock,
                side_effect=Exception("Merge exploded"),
            ),
        ):
            result = await handle_check_suite_event(event)

        assert result["status"] == "processed"
        assert result["event"] == "check_suite_success"
        # merge_attempted should still be False (exception caught)
        assert result["merge_attempted"] is False

    @pytest.mark.asyncio
    async def test_check_suite_success_no_pipeline(self):
        """check_suite success with no auto-merge pipeline should not attempt merge."""
        from unittest.mock import patch

        from src.api.webhooks import handle_check_suite_event

        event = CheckSuiteEvent(
            action="completed",
            check_suite=CheckSuiteData(
                id=401,
                status="completed",
                conclusion="success",
                head_sha="def456",
                pull_requests=[CheckRunPR(number=42)],
            ),
            repository=RepositoryData(
                name="repo",
                owner=OwnerData(login="owner"),
            ),
        )

        with (
            patch("src.api.webhooks.check_runs._resolve_issue_for_pr", return_value=10),
            patch("src.api.webhooks.check_runs._get_auto_merge_pipeline", return_value=None),
        ):
            result = await handle_check_suite_event(event)

        assert result["status"] == "processed"
        assert result["event"] == "check_suite_success"
        assert result["merge_attempted"] is False

    @pytest.mark.asyncio
    async def test_check_suite_success_no_webhook_token(self):
        """When no webhook token is configured, should not attempt merge."""
        from unittest.mock import patch

        from src.api.webhooks import handle_check_suite_event

        event = CheckSuiteEvent(
            action="completed",
            check_suite=CheckSuiteData(
                id=402,
                status="completed",
                conclusion="success",
                head_sha="def456",
                pull_requests=[CheckRunPR(number=42)],
            ),
            repository=RepositoryData(
                name="repo",
                owner=OwnerData(login="owner"),
            ),
        )

        mock_settings = type("Settings", (), {"github_webhook_token": ""})()

        with (
            patch("src.api.webhooks.check_runs._resolve_issue_for_pr", return_value=10),
            patch(
                "src.api.webhooks.check_runs._get_auto_merge_pipeline",
                return_value={"project_id": "PVT_123"},
            ),
            patch("src.api.webhooks.check_runs.get_settings", return_value=mock_settings),
        ):
            result = await handle_check_suite_event(event)

        assert result["status"] == "processed"
        assert result["event"] == "check_suite_success"
        assert result["merge_attempted"] is False

    @pytest.mark.asyncio
    async def test_check_suite_non_completed_action_ignored(self):
        """check_suite with non-completed action should be ignored."""
        from src.api.webhooks import handle_check_suite_event

        event = CheckSuiteEvent(
            action="requested",
            check_suite=CheckSuiteData(
                id=403,
                status="queued",
                conclusion=None,
                head_sha="abc123",
                pull_requests=[CheckRunPR(number=1)],
            ),
            repository=RepositoryData(
                name="repo",
                owner=OwnerData(login="owner"),
            ),
        )
        result = await handle_check_suite_event(event)
        assert result["status"] == "ignored"
        assert result["reason"] == "action_not_completed"


class TestWebhookHelpers:
    """Tests for webhook helper functions _resolve_issue_for_pr and _get_auto_merge_pipeline."""

    def test_resolve_issue_for_pr_found(self):
        """Should return issue number when PR is in the cache."""
        from unittest.mock import patch

        from src.api.webhooks import _resolve_issue_for_pr

        mock_branches = {
            10: {"pr_number": 42, "branch": "feature"},
            20: {"pr_number": 55, "branch": "fix"},
        }
        with patch(
            "src.services.workflow_orchestrator._issue_main_branches",
            mock_branches,
        ):
            result = _resolve_issue_for_pr(42)
            assert result == 10

    def test_resolve_issue_for_pr_not_found(self):
        """Should return None when PR is not in the cache."""
        from unittest.mock import patch

        from src.api.webhooks import _resolve_issue_for_pr

        mock_branches = {
            10: {"pr_number": 42, "branch": "feature"},
        }
        with patch(
            "src.services.workflow_orchestrator._issue_main_branches",
            mock_branches,
        ):
            result = _resolve_issue_for_pr(999)
            assert result is None

    def test_resolve_issue_for_pr_empty_cache_returns_none(self):
        """When the cache is empty, function should return None."""
        from unittest.mock import patch

        from src.api.webhooks import _resolve_issue_for_pr

        with patch(
            "src.services.workflow_orchestrator._issue_main_branches",
            {},
        ):
            result = _resolve_issue_for_pr(42)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_auto_merge_pipeline_complete(self):
        """Should return pipeline metadata for complete auto-merge pipelines."""
        from unittest.mock import MagicMock, patch

        from src.api.webhooks import _get_auto_merge_pipeline

        pipeline = MagicMock()
        pipeline.is_complete = True
        pipeline.auto_merge = True
        pipeline.project_id = "PVT_123"

        with patch(
            "src.services.copilot_polling.get_pipeline_state",
            return_value=pipeline,
        ):
            result = await _get_auto_merge_pipeline(10, "owner", "repo")
            assert result is not None
            assert result["devops_attempts"] == 0
            assert result["devops_active"] is False

    @pytest.mark.asyncio
    async def test_get_auto_merge_pipeline_complete_no_auto_merge(self):
        """Should return None for complete pipelines without auto_merge enabled."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from src.api.webhooks import _get_auto_merge_pipeline

        pipeline = MagicMock()
        pipeline.is_complete = True
        pipeline.auto_merge = False
        pipeline.project_id = "PVT_123"

        with (
            patch(
                "src.services.copilot_polling.get_pipeline_state",
                return_value=pipeline,
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
    async def test_get_auto_merge_pipeline_incomplete(self):
        """Should return None for incomplete pipelines."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from src.api.webhooks import _get_auto_merge_pipeline

        pipeline = MagicMock()
        pipeline.is_complete = False

        with (
            patch(
                "src.services.copilot_polling.get_pipeline_state",
                return_value=pipeline,
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
    async def test_get_auto_merge_pipeline_no_pipeline(self):
        """Should return None when no pipeline state exists."""
        from unittest.mock import AsyncMock, MagicMock, patch

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
