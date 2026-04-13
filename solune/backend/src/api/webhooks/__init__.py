"""Webhooks API sub-package.

Splits the monolithic webhooks.py into focused modules:
- dispatch.py: Main webhook endpoint, signature verification, deduplication
- pull_requests.py: Pull request event handlers
- check_runs.py: Check run and check suite event handlers
- utils.py: Shared helpers (signature verification, PR classification, pipeline lookup)

Re-exports preserve backward compatibility so existing imports from
``src.api.webhooks`` continue to work.
"""

from src.api.webhooks.check_runs import (  # noqa: F401
    handle_check_run_event,
    handle_check_suite_event,
)
from src.api.webhooks.dispatch import (  # noqa: F401
    _processed_delivery_ids,
    github_webhook,
    router,
)
from src.api.webhooks.pull_requests import (  # noqa: F401
    handle_copilot_pr_ready,
    handle_pull_request_event,
    update_issue_status_for_copilot_pr,
)
from src.api.webhooks.utils import (  # noqa: F401
    _get_auto_merge_pipeline,
    _resolve_issue_for_pr,
    classify_pull_request_activity,
    extract_issue_number_from_pr,
    verify_webhook_signature,
)
