"""Webhooks API sub-package."""

from src.api.webhooks.router import router  # noqa: F401

# Re-export for backward compatibility
from src.api.webhooks.utils import (  # noqa: F401
    classify_pull_request_activity,
    extract_issue_number_from_pr,
    verify_webhook_signature,
)
