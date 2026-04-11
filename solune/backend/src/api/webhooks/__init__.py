"""Webhooks package — backward-compatible re-exports.

All symbols that were previously importable from ``src.api.webhooks``
remain importable from this package.
"""

from __future__ import annotations

from src.api.webhooks.check_runs import handle_check_run_event, handle_check_suite_event
from src.api.webhooks.common import (
    _get_auto_merge_pipeline,
    _processed_delivery_ids,
    _resolve_issue_for_pr,
    classify_pull_request_activity,
    extract_issue_number_from_pr,
    verify_webhook_signature,
)
from src.api.webhooks.handlers import github_webhook, router
from src.api.webhooks.pull_requests import (
    handle_copilot_pr_ready,
    handle_pull_request_event,
    update_issue_status_for_copilot_pr,
)

__all__ = [
    # Router
    "router",
    # Main endpoint
    "github_webhook",
    # Common utilities
    "verify_webhook_signature",
    "_processed_delivery_ids",
    "_resolve_issue_for_pr",
    "_get_auto_merge_pipeline",
    "classify_pull_request_activity",
    "extract_issue_number_from_pr",
    # Pull request handlers
    "handle_pull_request_event",
    "handle_copilot_pr_ready",
    "update_issue_status_for_copilot_pr",
    # Check run/suite handlers
    "handle_check_run_event",
    "handle_check_suite_event",
]
