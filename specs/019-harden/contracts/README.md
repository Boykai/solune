# Contracts: #Harden

**Feature**: Harden Solune reliability, code quality, CI/CD, observability, DX
**Date**: 2026-04-10

## Overview

The #Harden initiative introduces **no new API endpoints or contracts**.
All changes are internal to existing service implementations, test
infrastructure, and build configurations.

## Existing Contracts (Unchanged)

### Chat API — Plan Mode

- `POST /api/chat/messages/plan` — Non-streaming plan-mode chat
- `POST /api/chat/messages/plan/stream` — Streaming plan-mode chat (SSE)
- `POST /api/chat/exit-plan-mode` — Exit plan mode

These endpoints already persist user messages **after** service availability
is confirmed (bug 3.4 already resolved).

### Agents API — Agent CRUD

- `PUT /api/agents/{agent_id}` — Update agent config

This endpoint already sets `lifecycle_status = pending_pr` when opening a PR
(bug 1.2 already resolved).

## Internal Contract Changes

### AgentPreview Construction

**Before**: `_extract_agent_preview()` accepts any `list` for tools field.
**After**: Validates each tool entry is a non-empty string before constructing
`AgentPreview`.

```python
# Validation contract
tools = config.get("tools", [])
if not isinstance(tools, list):
    return None
if not all(isinstance(t, str) and t.strip() for t in tools):
    return None
```

### Singleton Accessor Pattern

**Before**: Direct import of module-level singleton.
**After**: Accessor function with optional `app.state` injection.

```python
# New accessor contract
def get_github_projects_service(
    app_state: Any | None = None,
) -> GitHubProjectsService:
    ...
```

Callers in request contexts pass `request.app.state`. Background tasks
and non-request callers pass `None` to get the module-level fallback.
