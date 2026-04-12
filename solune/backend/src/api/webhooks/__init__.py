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
    github_projects_service,
    handle_copilot_pr_ready,
    handle_pull_request_event,
    update_issue_status_for_copilot_pr,
)
from src.config import get_settings
from src.services.activity_logger import log_event
from src.services.database import get_db

__all__ = [
    "_get_auto_merge_pipeline",
    "_processed_delivery_ids",
    "_resolve_issue_for_pr",
    "classify_pull_request_activity",
    "extract_issue_number_from_pr",
    "get_db",
    "get_settings",
    "github_projects_service",
    "github_webhook",
    "handle_check_run_event",
    "handle_check_suite_event",
    "handle_copilot_pr_ready",
    "handle_pull_request_event",
    "log_event",
    "router",
    "update_issue_status_for_copilot_pr",
    "verify_webhook_signature",
]
