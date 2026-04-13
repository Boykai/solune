"""Main webhook router: GitHub endpoint, signature verification, and deduplication."""

from typing import Any, cast

from fastapi import APIRouter, Header, Request
from pydantic import ValidationError as PydanticValidationError

from src.api.webhook_models import (
    CheckRunEvent,
    CheckSuiteEvent,
    IssuesEvent,
    PingEvent,
    PullRequestEvent,
)
from src.api.webhooks.check_runs import handle_check_run_event, handle_check_suite_event
from src.api.webhooks.pull_requests import handle_pull_request_event
from src.api.webhooks.utils import classify_pull_request_activity, verify_webhook_signature
from src.config import get_settings
from src.exceptions import AppException, AuthenticationError
from src.logging_utils import get_logger
from src.services.activity_logger import log_event
from src.services.database import get_db
from src.utils import BoundedSet

logger = get_logger(__name__)
router = APIRouter()

# In-memory storage for tracking processed events (deduplication).
# Uses BoundedSet to maintain insertion order and automatically evict
# the oldest entries when capacity is reached.
_processed_delivery_ids: BoundedSet[str] = BoundedSet(maxlen=1000)


@router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: str | None = Header(None, alias="X-GitHub-Event"),
    x_github_delivery: str | None = Header(None, alias="X-GitHub-Delivery"),
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
) -> dict[str, Any]:
    """
    Handle incoming GitHub webhook events.

    Supported events:
    - pull_request: Detect when Copilot PRs are ready for review

    Headers:
    - X-GitHub-Event: Event type (e.g., "pull_request")
    - X-GitHub-Delivery: Unique delivery ID for deduplication
    - X-Hub-Signature-256: HMAC signature for verification
    """
    settings = get_settings()

    # Read raw body for signature verification
    body = await request.body()

    # Verify signature — always required regardless of debug mode.
    # Developers must configure a local test secret (GITHUB_WEBHOOK_SECRET).
    if settings.github_webhook_secret:
        if not verify_webhook_signature(body, x_hub_signature_256, settings.github_webhook_secret):
            logger.warning("Invalid webhook signature")
            raise AuthenticationError("Invalid or missing webhook signature")
    else:
        logger.warning("Webhook rejected: GITHUB_WEBHOOK_SECRET is not configured")
        raise AuthenticationError("Invalid or missing webhook signature")

    # Deduplicate by delivery ID
    if x_github_delivery:
        if x_github_delivery in _processed_delivery_ids:
            logger.info("Duplicate delivery %s, skipping", x_github_delivery)
            return {"status": "duplicate", "delivery_id": x_github_delivery}

        _processed_delivery_ids.add(x_github_delivery)

    # Parse JSON payload
    try:
        raw_payload = await request.json()
    except Exception as e:
        logger.error("Failed to parse webhook payload: %s", e)
        raise AppException("Invalid JSON payload", status_code=400) from e

    payload: (
        PullRequestEvent
        | IssuesEvent
        | PingEvent
        | CheckRunEvent
        | CheckSuiteEvent
        | dict[str, Any]
    )
    try:
        if x_github_event == "pull_request":
            payload = PullRequestEvent.model_validate(raw_payload)
        elif x_github_event == "issues":
            payload = IssuesEvent.model_validate(raw_payload)
        elif x_github_event == "ping":
            payload = PingEvent.model_validate(raw_payload)
        elif x_github_event == "check_run":
            payload = CheckRunEvent.model_validate(raw_payload)
        elif x_github_event == "check_suite":
            payload = CheckSuiteEvent.model_validate(raw_payload)
        else:
            payload = raw_payload
    except PydanticValidationError as e:
        logger.warning("Invalid webhook payload for event %s: %s", x_github_event, e)
        raise AppException(
            "Invalid webhook payload",
            status_code=422,
            details={"errors": e.errors()},
        ) from e

    logger.info(
        "Received GitHub webhook: event=%s, delivery=%s",
        x_github_event,
        x_github_delivery,
    )

    # Handle pull_request events
    if x_github_event == "pull_request":
        result = await handle_pull_request_event(cast(PullRequestEvent | dict[str, Any], payload))
        pr_info = raw_payload.get("pull_request", {}) if isinstance(raw_payload, dict) else {}
        sender = (
            pr_info.get("user", {}).get("login", "system")
            if isinstance(pr_info, dict)
            else "system"
        )
        activity_action, summary, detail = (
            classify_pull_request_activity(raw_payload)
            if isinstance(raw_payload, dict)
            else ("received", "Webhook: pull_request received", {"webhook_type": "pull_request"})
        )
        await log_event(
            get_db(),
            event_type="webhook",
            entity_type="issue",
            entity_id=str(pr_info.get("number", "")) if isinstance(pr_info, dict) else "",
            project_id=(
                result.get("project_id", "")
                if isinstance(result, dict) and isinstance(result.get("project_id"), str)
                else ""
            ),
            actor=sender,
            action=activity_action,
            summary=summary,
            detail=detail,
        )
        return result

    # Handle check_run events for CI failure detection (auto-merge)
    if x_github_event == "check_run" and isinstance(payload, CheckRunEvent):
        result = await handle_check_run_event(payload)
        return result

    # Handle check_suite events for CI failure detection (auto-merge)
    if x_github_event == "check_suite" and isinstance(payload, CheckSuiteEvent):
        result = await handle_check_suite_event(payload)
        return result

    # Acknowledge other events — do not echo user-controlled header values
    return {
        "status": "ignored",
        "message": "Event type not handled",
    }
