"""Check run and check suite webhook event handlers."""

from __future__ import annotations

from typing import Any

from src.api.webhook_models import CheckRunEvent, CheckSuiteEvent
from src.api.webhooks.common import _get_auto_merge_pipeline, _resolve_issue_for_pr
from src.config import get_settings
from src.logging_utils import get_logger

logger = get_logger(__name__)


async def handle_check_run_event(payload: CheckRunEvent) -> dict[str, Any]:
    """Handle check_run webhook events for CI failure detection.

    Routes check_run completed events with failure/timed_out conclusions
    to the DevOps agent dispatcher for auto-merge-enabled pipelines.
    """
    if payload.action != "completed":
        return {"status": "ignored", "reason": "action_not_completed"}

    conclusion = payload.check_run.conclusion
    if conclusion not in ("failure", "timed_out"):
        return {"status": "ignored", "reason": "conclusion_not_failure"}

    # Find associated PRs
    pr_numbers = [pr.number for pr in payload.check_run.pull_requests]
    if not pr_numbers:
        return {"status": "ignored", "reason": "no_associated_prs"}

    owner = payload.repository.owner.login
    repo_name = payload.repository.name

    logger.info(
        "Check run '%s' failed (conclusion=%s) for PRs %s",
        payload.check_run.name,
        conclusion,
        pr_numbers,
    )

    # Attempt to dispatch DevOps for auto-merge issues
    devops_dispatched = False
    for pr_num in pr_numbers:
        issue_number = _resolve_issue_for_pr(pr_num)
        if issue_number is None:
            continue

        pipeline = await _get_auto_merge_pipeline(issue_number, owner, repo_name)
        if pipeline is None:
            continue

        settings = get_settings()
        access_token = settings.github_webhook_token
        if not access_token:
            logger.warning("No webhook token available for DevOps dispatch")
            break

        merge_result_context: dict[str, Any] = {
            "reason": "ci_failure",
            "failed_checks": [
                {
                    "name": payload.check_run.name,
                    "conclusion": conclusion,
                }
            ],
        }

        try:
            from src.services.copilot_polling.auto_merge import dispatch_devops_agent

            pipeline_metadata: dict[str, Any] = {
                "devops_attempts": pipeline.get("devops_attempts", 0),
                "devops_active": pipeline.get("devops_active", False),
            }
            dispatched = await dispatch_devops_agent(
                access_token=access_token,
                owner=owner,
                repo=repo_name,
                issue_number=issue_number,
                pipeline_metadata=pipeline_metadata,
                project_id=pipeline.get("project_id", ""),
                merge_result_context=merge_result_context,
            )
            if dispatched:
                devops_dispatched = True
                logger.info(
                    "DevOps agent dispatched for issue #%d via check_run webhook",
                    issue_number,
                )
        except Exception:
            logger.warning(
                "Failed to dispatch DevOps for issue #%d via check_run webhook",
                issue_number,
                exc_info=True,
            )

    return {
        "status": "processed",
        "event": "check_run_failure",
        "check_name": payload.check_run.name,
        "conclusion": conclusion,
        "pr_numbers": pr_numbers,
        "devops_dispatched": devops_dispatched,
    }


async def handle_check_suite_event(payload: CheckSuiteEvent) -> dict[str, Any]:
    """Handle check_suite webhook events for CI pass/failure detection.

    Routes check_suite completed events: on success, attempts auto-merge
    for associated auto-merge issues; on failure, dispatches DevOps agent.
    """
    if payload.action != "completed":
        return {"status": "ignored", "reason": "action_not_completed"}

    conclusion = payload.check_suite.conclusion
    if conclusion not in ("failure", "success"):
        return {"status": "ignored", "reason": "conclusion_not_relevant"}

    # Find associated PRs
    pr_numbers = [pr.number for pr in payload.check_suite.pull_requests]
    if not pr_numbers:
        return {"status": "ignored", "reason": "no_associated_prs"}

    owner = payload.repository.owner.login
    repo_name = payload.repository.name

    if conclusion == "success":
        logger.info(
            "Check suite passed (conclusion=%s) for PRs %s",
            conclusion,
            pr_numbers,
        )

        # Proactive re-merge on CI success
        merge_attempted = False
        for pr_num in pr_numbers:
            issue_number = _resolve_issue_for_pr(pr_num)
            if issue_number is None:
                continue

            pipeline = await _get_auto_merge_pipeline(issue_number, owner, repo_name)
            if pipeline is None:
                continue

            settings = get_settings()
            access_token = settings.github_webhook_token
            if not access_token:
                logger.warning("No webhook token available for auto-merge attempt")
                break

            try:
                from src.services.copilot_polling.auto_merge import _attempt_auto_merge

                merge_result = await _attempt_auto_merge(
                    access_token=access_token,
                    owner=owner,
                    repo=repo_name,
                    issue_number=issue_number,
                )
                merge_attempted = True
                logger.info(
                    "Auto-merge attempt for issue #%d via check_suite webhook: %s",
                    issue_number,
                    merge_result.status,
                )
            except Exception:
                logger.warning(
                    "Failed auto-merge attempt for issue #%d via check_suite webhook",
                    issue_number,
                    exc_info=True,
                )

        return {
            "status": "processed",
            "event": "check_suite_success",
            "conclusion": conclusion,
            "pr_numbers": pr_numbers,
            "merge_attempted": merge_attempted,
        }

    # conclusion == "failure"
    logger.info(
        "Check suite failed (conclusion=%s) for PRs %s",
        conclusion,
        pr_numbers,
    )

    return {
        "status": "processed",
        "event": "check_suite_failure",
        "conclusion": conclusion,
        "pr_numbers": pr_numbers,
    }
