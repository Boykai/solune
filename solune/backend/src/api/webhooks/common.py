"""Common webhook utilities: signature verification, deduplication, and helpers."""

from __future__ import annotations

import hashlib
import hmac
import re
from typing import Any

from src.api.webhook_models import PullRequestData
from src.logging_utils import get_logger
from src.utils import BoundedSet

logger = get_logger(__name__)

# In-memory storage for tracking processed events (deduplication).
# Uses BoundedSet to maintain insertion order and automatically evict
# the oldest entries when capacity is reached.
_processed_delivery_ids: BoundedSet[str] = BoundedSet(maxlen=1000)


def _resolve_issue_for_pr(pr_number: int) -> int | None:
    """Reverse-lookup parent issue number from a PR number via _issue_main_branches cache."""
    try:
        from src.services.workflow_orchestrator import _issue_main_branches

        for issue_num, info in _issue_main_branches.items():
            if info.get("pr_number") == pr_number:
                return issue_num
    except Exception:
        pass
    return None


async def _get_auto_merge_pipeline(
    issue_number: int, owner: str, repo: str
) -> dict[str, Any] | None:
    """Get pipeline metadata for an issue if it's in an auto-merge-eligible state.

    Uses a 3-tier fallback strategy:
      Step A: L1 cache — ``get_pipeline_state(issue_number)``
      Step B: L2 SQLite — ``get_pipeline_state_async(issue_number)``
      Step C: Project-level — ``is_auto_merge_enabled(db, project_id)``

    Note: ``devops_attempts`` and ``devops_active`` are tracked in-memory via
    the ``pipeline_metadata`` dict passed to ``dispatch_devops_agent``; they
    are NOT persisted on ``PipelineState``.  Webhook-driven dispatches
    therefore start from defaults.  Deduplication for the webhook path
    relies on the ``_pending_post_devops_retries`` guard inside
    ``schedule_post_devops_merge_retry``.
    """
    try:
        import src.services.copilot_polling as _cp

        # Step A: L1 cache (fast, synchronous)
        pipeline = _cp.get_pipeline_state(issue_number)
        if pipeline and pipeline.is_complete and getattr(pipeline, "auto_merge", False):
            return {
                "project_id": getattr(pipeline, "project_id", ""),
                "devops_attempts": 0,
                "devops_active": False,
            }

        # Step B: L2 SQLite fallback (recovers from L1 eviction / restart)
        l2_pipeline = None
        if pipeline is None:
            try:
                l2_pipeline = await _cp.get_pipeline_state_async(issue_number)
                if (
                    l2_pipeline
                    and l2_pipeline.is_complete
                    and getattr(l2_pipeline, "auto_merge", False)
                ):
                    return {
                        "project_id": getattr(l2_pipeline, "project_id", ""),
                        "devops_attempts": 0,
                        "devops_active": False,
                    }
            except Exception:
                pass

        # Step C: Project-level fallback (state already removed, but project has auto-merge)
        try:
            project_id: str | None = None
            # Try to resolve project_id from L1 state (covers the case where
            # L1 returned a pipeline but auto_merge was False — e.g. a
            # reconstructed pipeline that lost the flag).
            if pipeline is not None:
                project_id = getattr(pipeline, "project_id", None) or None

            # Try to resolve project_id from L2 state (reuse result from Step B)
            if not project_id and l2_pipeline:
                project_id = getattr(l2_pipeline, "project_id", None)

            # Try to resolve project_id from _issue_main_branches
            if not project_id:
                try:
                    from src.services.workflow_orchestrator.transitions import (
                        _issue_main_branches,
                    )

                    branch_info = _issue_main_branches.get(issue_number)
                    if branch_info and isinstance(branch_info, dict):
                        project_id = branch_info.get("project_id")
                except Exception:
                    pass

            if project_id:
                db = _cp.get_db()
                if await _cp.is_auto_merge_enabled(db, project_id):
                    return {
                        "project_id": project_id,
                        "devops_attempts": 0,
                        "devops_active": False,
                    }
        except Exception:
            pass
    except Exception:
        pass
    return None


def classify_pull_request_activity(
    raw_payload: dict[str, Any],
) -> tuple[str, str, dict[str, Any]]:
    """Map a pull_request webhook payload to an activity action, summary, and detail."""
    pr_info = raw_payload.get("pull_request", {})
    repo_info = raw_payload.get("repository", {})
    webhook_action = raw_payload.get("action", "")
    repo_full = repo_info.get("full_name", "") if isinstance(repo_info, dict) else ""
    pr_number = pr_info.get("number", "") if isinstance(pr_info, dict) else ""
    head_ref = pr_info.get("head", {}).get("ref", "") if isinstance(pr_info, dict) else ""

    activity_action = webhook_action or "received"
    summary = f"Webhook: pull_request {activity_action} on {repo_full}".strip()

    if webhook_action == "closed" and isinstance(pr_info, dict) and pr_info.get("merged") is True:
        activity_action = "pr_merged"
        summary = f"Webhook: PR #{pr_number} merged on {repo_full}"
    elif isinstance(head_ref, str) and head_ref.startswith("copilot/"):
        activity_action = "copilot_pr_ready"
        summary = f"Webhook: Copilot PR #{pr_number} ready on {repo_full}"

    detail = {
        "webhook_type": "pull_request",
        "action": activity_action,
        "sender": (
            pr_info.get("user", {}).get("login", "system")
            if isinstance(pr_info, dict)
            else "system"
        ),
        "repository": repo_full,
        "branch": head_ref,
        "pr_number": pr_number,
    }
    return activity_action, summary, detail


def verify_webhook_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    """
    Verify GitHub webhook signature.

    Args:
        payload: Raw request body
        signature: X-Hub-Signature-256 header value
        secret: Webhook secret configured in GitHub

    Returns:
        True if signature is valid
    """
    if not signature:
        return False

    if not signature.startswith("sha256="):
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)


def extract_issue_number_from_pr(pr_data: PullRequestData | dict[str, Any]) -> int | None:
    """
    Extract linked issue number from PR body or branch name.

    Looks for patterns like:
    - "Fixes #123" or "Closes #123" in body
    - Branch names like "issue-123-..." or "123-feature"

    Args:
        pr_data: Pull request data from webhook

    Returns:
        Issue number if found, None otherwise
    """
    # Check PR body for issue references
    if isinstance(pr_data, PullRequestData):
        body = pr_data.body or ""
        branch_name = pr_data.head.ref
    else:
        body = pr_data.get("body") or ""
        branch_name = pr_data.get("head", {}).get("ref", "")

    # Common patterns: Fixes #123, Closes #123, Resolves #123, Related to #123
    patterns = [
        r"(?:fixes|closes|resolves|fix|close|resolve)\s*#(\d+)",
        r"(?:related\s+to|relates\s+to|ref|references?)\s*#(\d+)",
        r"#(\d+)",  # Fallback: any issue reference
    ]

    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            return int(match.group(1))

    # Check branch name for issue number
    # Patterns like: issue-123, 123-feature, feature/123-description
    branch_patterns = [
        r"issue[/-](\d+)",
        r"^(\d+)[/-]",
        r"/(\d+)[/-]",
    ]

    for pattern in branch_patterns:
        match = re.search(pattern, branch_name, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None
