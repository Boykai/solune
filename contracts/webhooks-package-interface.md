# Contract: `api/webhooks/` Package Interface

**Feature**: Codebase Modularity Review | **Date**: 2026-04-11

> Defines the public interface of the `api/webhooks/` package after splitting `api/webhooks.py`.

## Package Entry Point — `api/webhooks/__init__.py`

```python
from fastapi import APIRouter

from .common import verify_signature
from .pull_requests import router as pr_router
from .check_runs import router as check_runs_router
from .issues import router as issues_router
from .handlers import router as handlers_router

router = APIRouter()
router.include_router(pr_router)
router.include_router(check_runs_router)
router.include_router(issues_router)
router.include_router(handlers_router)
```

**Backward Compatibility**: `from src.api.webhooks import router` continues to work.

## Module: `common.py` — Shared Webhook Utilities

```python
async def verify_signature(request: Request, secret: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature."""
    ...

def parse_webhook_payload(body: bytes, event_type: str) -> dict:
    """Parse and validate webhook payload based on event type."""
    ...

class WebhookContext:
    """Shared context for webhook handlers (repo info, sender, installation)."""
    owner: str
    repo: str
    sender: str
    installation_id: int | None
```

## Module: `pull_requests.py` — PR Event Handlers

```python
# Handles: pull_request.opened, pull_request.closed, pull_request.synchronize
async def handle_pull_request_event(payload: dict, context: WebhookContext) -> None: ...
```

## Module: `check_runs.py` — CI Check Handlers

```python
# Handles: check_run.completed, check_run.created
async def handle_check_run_event(payload: dict, context: WebhookContext) -> None: ...
```

## Module: `issues.py` — Issue Event Handlers

```python
# Handles: issues.opened, issues.edited, issues.labeled
async def handle_issues_event(payload: dict, context: WebhookContext) -> None: ...
```

## Module: `handlers.py` — Dispatch Registry

```python
# Maps event type → handler function
WEBHOOK_HANDLERS: dict[str, Callable] = {
    "pull_request": handle_pull_request_event,
    "check_run": handle_check_run_event,
    "issues": handle_issues_event,
}

# POST /api/v1/webhooks/github
async def github_webhook(request: Request) -> Response:
    """Main webhook entry point — verifies signature and dispatches to handler."""
    ...
```

## Cross-Module Dependencies

```text
handlers.py imports from: common, pull_requests, check_runs, issues
pull_requests.py imports from: common, services/github_projects, services/copilot_polling
check_runs.py imports from: common, services/copilot_polling
issues.py imports from: common, services/github_projects
common.py imports from: (standalone — no internal deps)
```
