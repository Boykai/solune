"""Unit tests for DevOps recovery fallback in check_in_review_issues()."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.copilot_polling.auto_merge import AutoMergeResult


class TestDevopsRecoveryFallback:
    """Tests for the DevOps recovery fallback in check_in_review_issues().

    After a server restart, in-memory DevOps tracking state is lost.
    The recovery path optimistically checks every completed in-review
    issue's comments for the ``devops: Done!`` marker and re-attempts
    merge when found.
    """

    @pytest.mark.asyncio
    async def test_recovery_detects_done_and_merges(self):
        """When 'Done!' comment found on completed in-review issue, should attempt merge."""
        task = MagicMock()
        task.issue_number = 42
        task.status = "In Review"
        task.repository_owner = "owner"
        task.repository_name = "repo"
        task.labels = []

        pipeline = MagicMock()
        pipeline.is_complete = True
        pipeline.auto_merge = True
        pipeline.status = "In Review"
        pipeline.current_agent = None
        pipeline.completed_agents = []
        pipeline.agents = []

        config = MagicMock()
        config.status_in_review = "In Review"

        mock_check_done = AsyncMock(return_value=True)
        mock_attempt_merge = AsyncMock(
            return_value=AutoMergeResult(status="merged", pr_number=99, merge_commit="abc")
        )

        with (
            patch("src.services.copilot_polling.github_projects_service") as svc,
            patch(
                "src.services.copilot_polling.get_workflow_config",
                new_callable=AsyncMock,
                return_value=config,
            ),
            patch("src.services.copilot_polling.get_pipeline_state", return_value=pipeline),
            patch("src.services.copilot_polling.get_agent_slugs", return_value=["copilot-review"]),
            patch(
                "src.services.copilot_polling.auto_merge._check_devops_done_comment",
                mock_check_done,
            ),
            patch(
                "src.services.copilot_polling.auto_merge._attempt_auto_merge",
                mock_attempt_merge,
            ),
            patch(
                "src.services.copilot_polling.pipeline._process_pipeline_completion",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.copilot_polling.pipeline._get_or_reconstruct_pipeline",
                new_callable=AsyncMock,
                return_value=pipeline,
            ),
        ):
            svc.get_project_items = AsyncMock(return_value=[task])

            from src.services.copilot_polling.state import _pending_post_devops_retries

            _pending_post_devops_retries.pop(42, None)

            from src.services.copilot_polling.pipeline import check_in_review_issues

            await check_in_review_issues(
                access_token="token",
                project_id="PVT_123",
                owner="owner",
                repo="repo",
                tasks=[task],
            )

            mock_check_done.assert_awaited_once()
            mock_attempt_merge.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_recovery_skips_when_no_done_comment(self):
        """When no 'Done!' comment found, should not attempt merge."""
        from src.services.copilot_polling.state import _pending_post_devops_retries

        _pending_post_devops_retries.pop(42, None)

        task = MagicMock()
        task.issue_number = 42
        task.status = "In Review"
        task.repository_owner = "owner"
        task.repository_name = "repo"
        task.labels = []

        pipeline = MagicMock()
        pipeline.is_complete = True
        pipeline.auto_merge = True
        pipeline.status = "In Review"
        pipeline.current_agent = None
        pipeline.completed_agents = []
        pipeline.agents = []

        config = MagicMock()
        config.status_in_review = "In Review"

        mock_check_done = AsyncMock(return_value=False)
        mock_attempt_merge = AsyncMock()

        with (
            patch("src.services.copilot_polling.github_projects_service") as svc,
            patch(
                "src.services.copilot_polling.get_workflow_config",
                new_callable=AsyncMock,
                return_value=config,
            ),
            patch("src.services.copilot_polling.get_pipeline_state", return_value=pipeline),
            patch("src.services.copilot_polling.get_agent_slugs", return_value=["copilot-review"]),
            patch(
                "src.services.copilot_polling.auto_merge._check_devops_done_comment",
                mock_check_done,
            ),
            patch(
                "src.services.copilot_polling.auto_merge._attempt_auto_merge",
                mock_attempt_merge,
            ),
            patch(
                "src.services.copilot_polling.pipeline._process_pipeline_completion",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.copilot_polling.pipeline._get_or_reconstruct_pipeline",
                new_callable=AsyncMock,
                return_value=pipeline,
            ),
        ):
            svc.get_project_items = AsyncMock(return_value=[task])

            from src.services.copilot_polling.pipeline import check_in_review_issues

            await check_in_review_issues(
                access_token="token",
                project_id="PVT_123",
                owner="owner",
                repo="repo",
                tasks=[task],
            )

            mock_check_done.assert_awaited_once()
            mock_attempt_merge.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_recovery_skips_when_pipeline_incomplete(self):
        """When pipeline is not complete, should not check for Done! comment."""
        task = MagicMock()
        task.issue_number = 42
        task.status = "In Review"
        task.repository_owner = "owner"
        task.repository_name = "repo"
        task.labels = []

        pipeline = MagicMock()
        pipeline.is_complete = False
        pipeline.status = "In Review"
        pipeline.current_agent = "copilot-review"
        pipeline.completed_agents = []
        pipeline.agents = ["copilot-review"]

        config = MagicMock()
        config.status_in_review = "In Review"

        mock_check_done = AsyncMock()

        with (
            patch("src.services.copilot_polling.github_projects_service") as svc,
            patch(
                "src.services.copilot_polling.get_workflow_config",
                new_callable=AsyncMock,
                return_value=config,
            ),
            patch("src.services.copilot_polling.get_pipeline_state", return_value=pipeline),
            patch("src.services.copilot_polling.get_agent_slugs", return_value=["copilot-review"]),
            patch(
                "src.services.copilot_polling.auto_merge._check_devops_done_comment",
                mock_check_done,
            ),
            patch(
                "src.services.copilot_polling.pipeline._process_pipeline_completion",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            svc.get_project_items = AsyncMock(return_value=[task])

            from src.services.copilot_polling.pipeline import check_in_review_issues

            await check_in_review_issues(
                access_token="token",
                project_id="PVT_123",
                owner="owner",
                repo="repo",
                tasks=[task],
            )

            mock_check_done.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_recovery_skips_when_retry_already_pending(self):
        """When a post-DevOps retry is already pending, should not attempt recovery."""
        task = MagicMock()
        task.issue_number = 42
        task.status = "In Review"
        task.repository_owner = "owner"
        task.repository_name = "repo"
        task.labels = []

        pipeline = MagicMock()
        pipeline.is_complete = True
        pipeline.auto_merge = True
        pipeline.status = "In Review"
        pipeline.current_agent = None
        pipeline.completed_agents = []
        pipeline.agents = []

        config = MagicMock()
        config.status_in_review = "In Review"

        mock_check_done = AsyncMock()

        with (
            patch("src.services.copilot_polling.github_projects_service") as svc,
            patch(
                "src.services.copilot_polling.get_workflow_config",
                new_callable=AsyncMock,
                return_value=config,
            ),
            patch("src.services.copilot_polling.get_pipeline_state", return_value=pipeline),
            patch("src.services.copilot_polling.get_agent_slugs", return_value=["copilot-review"]),
            patch(
                "src.services.copilot_polling.auto_merge._check_devops_done_comment",
                mock_check_done,
            ),
            patch(
                "src.services.copilot_polling.pipeline._process_pipeline_completion",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.copilot_polling.pipeline._get_or_reconstruct_pipeline",
                new_callable=AsyncMock,
                return_value=pipeline,
            ),
        ):
            svc.get_project_items = AsyncMock(return_value=[task])

            from src.services.copilot_polling.state import _pending_post_devops_retries

            # Simulate an active retry
            _pending_post_devops_retries[42] = {"project_id": "PVT_123"}

            try:
                from src.services.copilot_polling.pipeline import check_in_review_issues

                await check_in_review_issues(
                    access_token="token",
                    project_id="PVT_123",
                    owner="owner",
                    repo="repo",
                    tasks=[task],
                )

                mock_check_done.assert_not_awaited()
            finally:
                _pending_post_devops_retries.pop(42, None)

    @pytest.mark.asyncio
    async def test_recovery_skips_when_auto_merge_disabled(self):
        """When pipeline has auto_merge disabled, should not check for Done! comment."""
        task = MagicMock()
        task.issue_number = 42
        task.status = "In Review"
        task.repository_owner = "owner"
        task.repository_name = "repo"
        task.labels = []

        pipeline = MagicMock()
        pipeline.is_complete = True
        pipeline.auto_merge = False
        pipeline.status = "In Review"
        pipeline.current_agent = None
        pipeline.completed_agents = []
        pipeline.agents = []

        config = MagicMock()
        config.status_in_review = "In Review"

        mock_check_done = AsyncMock()

        with (
            patch("src.services.copilot_polling.github_projects_service") as svc,
            patch(
                "src.services.copilot_polling.get_workflow_config",
                new_callable=AsyncMock,
                return_value=config,
            ),
            patch("src.services.copilot_polling.get_pipeline_state", return_value=pipeline),
            patch("src.services.copilot_polling.get_agent_slugs", return_value=["copilot-review"]),
            patch(
                "src.services.copilot_polling.auto_merge._check_devops_done_comment",
                mock_check_done,
            ),
            patch(
                "src.services.copilot_polling.pipeline._process_pipeline_completion",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.copilot_polling.pipeline._get_or_reconstruct_pipeline",
                new_callable=AsyncMock,
                return_value=pipeline,
            ),
        ):
            svc.get_project_items = AsyncMock(return_value=[task])

            from src.services.copilot_polling.state import _pending_post_devops_retries

            _pending_post_devops_retries.pop(42, None)

            from src.services.copilot_polling.pipeline import check_in_review_issues

            await check_in_review_issues(
                access_token="token",
                project_id="PVT_123",
                owner="owner",
                repo="repo",
                tasks=[task],
            )

            mock_check_done.assert_not_awaited()
