# Contract: `api/webhooks/` Package Interface

**Feature**: Codebase Modularity Review | **Date**: 2026-04-11

> Defines the public interface of the `api/webhooks/` package after splitting `api/webhooks.py`.

## Package Entry Point — `api/webhooks/__init__.py`

```python
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
```

**Backward Compatibility**: `from src.api.webhooks import router` continues to work.
A single `router` is exposed from `handlers.py`; sub-modules do not define their own routers.

## Module: `common.py` — Shared Webhook Utilities

```python
def verify_webhook_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature."""
    ...

def extract_issue_number_from_pr(pr_data: PullRequestData | dict[str, Any]) -> int | None:
    """Extract linked issue number from PR body or branch name."""
    ...

def classify_pull_request_activity(
    raw_payload: dict[str, Any],
) -> tuple[str, str, dict[str, Any]]:
    """Map a pull_request webhook payload to an activity action, summary, and detail."""
    ...

def _resolve_issue_for_pr(pr_number: int) -> int | None:
    """Reverse-lookup parent issue number from a PR number via _issue_main_branches cache."""
    ...

async def _get_auto_merge_pipeline(
    issue_number: int, owner: str, repo: str,
) -> dict[str, Any] | None:
    """Get pipeline metadata for an issue if it's in an auto-merge-eligible state."""
    ...

# In-memory deduplication set
_processed_delivery_ids: BoundedSet[str]
```

## Module: `pull_requests.py` — PR Event Handlers

```python
# Handles: pull_request.closed (merged), pull_request.ready_for_review, pull_request.opened
async def handle_pull_request_event(
    payload: PullRequestEvent | dict[str, Any],
) -> dict[str, Any]: ...

async def handle_copilot_pr_ready(
    pr_data: dict, repo_owner: str, repo_name: str, pr_number: int, pr_author: str,
) -> dict[str, Any]: ...

async def update_issue_status_for_copilot_pr(
    pr_data: dict, repo_owner: str, repo_name: str, pr_number: int, pr_author: str,
) -> dict[str, Any]: ...
```

## Module: `check_runs.py` — CI Check Handlers

```python
# Handles: check_run.completed (failure/timed_out), check_suite.completed (success/failure)
async def handle_check_run_event(payload: CheckRunEvent) -> dict[str, Any]: ...
async def handle_check_suite_event(payload: CheckSuiteEvent) -> dict[str, Any]: ...
```

## Module: `handlers.py` — Main Webhook Endpoint

```python
router = APIRouter()

# POST /api/v1/webhooks/github
@router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: str | None = Header(None, alias="X-GitHub-Event"),
    x_github_delivery: str | None = Header(None, alias="X-GitHub-Delivery"),
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
) -> dict[str, Any]:
    """Main webhook entry point — verifies signature, deduplicates, and dispatches to handler."""
    ...
```

## Cross-Module Dependencies

```text
handlers.py imports from: common, pull_requests, check_runs, webhook_models, config, activity_logger
pull_requests.py imports from: common, webhook_models, config, cache, github_projects
check_runs.py imports from: common, webhook_models, config
common.py imports from: webhook_models, logging_utils, utils (standalone — no internal package deps)
```
