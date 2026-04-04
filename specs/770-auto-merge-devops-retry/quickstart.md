# Quick Start: Auto-Merge After All Agents Complete + CI Pass + DevOps Retry

**Feature**: #770 — Auto-Merge After All Agents Complete + CI Pass + DevOps Retry  
**Date**: 2026-04-04

---

## Overview

This feature closes three gaps in the existing auto-merge pipeline:

1. **Gap 1**: DevOps agent template + registration (the dispatch code exists, but the agent definition is missing)
2. **Gap 2**: Post-DevOps re-merge scheduling (DevOps fixes CI but nothing re-triggers merge)
3. **Gap 3**: Webhook handlers wired to actions (check_run/check_suite handlers detect events but return early)

---

## Prerequisites

```bash
# Backend environment setup
cd solune/backend
uv sync --extra dev

# Verify existing tests pass
uv run python -m pytest tests/unit/test_auto_merge.py tests/unit/test_webhook_ci.py tests/unit/test_github_agents.py -q
```

---

## Key Files to Modify

| File | Change | Gap |
|------|--------|-----|
| `backend/templates/.github/agents/devops.agent.md` | NEW — agent template | 1 |
| `backend/src/services/github_projects/agents.py` | Add DevOps to BUILTIN_AGENTS | 1 |
| `backend/src/services/copilot_polling/auto_merge.py` | Add `schedule_post_devops_merge_retry()` | 2 |
| `backend/src/services/copilot_polling/state.py` | Add post-DevOps polling constants | 2 |
| `backend/src/services/copilot_polling/pipeline.py` | In Review polling fallback | 2 |
| `backend/src/api/webhooks.py` | Wire check_run → DevOps, check_suite → re-merge | 3 |

---

## Implementation Steps

### Step 1: Create DevOps Agent Template

Create `backend/templates/.github/agents/devops.agent.md`:

```yaml
---
name: DevOps
description: CI failure diagnosis and resolution agent.
mcp-servers:
  context7:
    type: http
    url: https://mcp.context7.com/mcp
    ...
---
# Agent Purpose
You are a DevOps agent specialized in CI/CD failure recovery...
```

Reference: `.github/agents/devops.agent.md` (deployed version already exists)

### Step 2: Register DevOps Agent

In `agents.py`, add to `BUILTIN_AGENTS`:

```python
AvailableAgent(
    slug="devops",
    display_name="DevOps",
    description="CI failure diagnosis and resolution agent",
    avatar_url=None,
    icon_name=None,
    source=AgentSource.BUILTIN,
),
```

Update tests: agent count from 8 → 9, add "devops" to expected slugs set.

### Step 3: Add Post-DevOps Retry Logic

In `auto_merge.py`, add:

```python
async def schedule_post_devops_merge_retry(
    access_token, owner, repo, issue_number, pipeline_metadata, project_id
) -> bool:
    """Schedule polling loop to check for DevOps 'Done!' and re-merge."""
    ...
```

Wire into `dispatch_devops_agent()` — call after successful dispatch.

### Step 4: Add In Review Polling Fallback

In `pipeline.py` `check_in_review_issues()`, add secondary check:
- If issue has `devops_active` in metadata and no pending retry task
- Check for "Done!" comment → re-attempt auto-merge

### Step 5: Wire Webhook Handlers

In `webhooks.py`:
- `handle_check_run_event()`: On failure → resolve PR to issue → dispatch DevOps
- `handle_check_suite_event()`: On success → resolve PR to issue → attempt auto-merge

---

## Verification

```bash
# Run targeted unit tests after each step
cd solune/backend
uv run python -m pytest tests/unit/test_github_agents.py -q          # Step 2
uv run python -m pytest tests/unit/test_auto_merge.py -q             # Step 3
uv run python -m pytest tests/unit/test_webhook_ci.py -q             # Step 5

# Run all affected tests
uv run python -m pytest tests/unit/test_auto_merge.py tests/unit/test_webhook_ci.py tests/unit/test_github_agents.py -q

# Lint
ruff check src/ tests/
ruff format --check src/ tests/
```

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                     Pipeline Orchestrator                      │
│                                                               │
│  All agents complete                                          │
│       │                                                       │
│       ▼                                                       │
│  _attempt_auto_merge()                                        │
│       │                                                       │
│  ┌────┴──────────┬──────────────┬──────────────┐             │
│  │ merged        │ retry_later  │ devops_needed │             │
│  │               │              │               │             │
│  ▼               ▼              ▼               │             │
│  Done ✅    Retry Loop    DevOps Dispatch       │             │
│           (60/120/240s)   (max 2 attempts)      │             │
│               │              │                   │             │
│               │              ▼                   │             │
│               │    Post-DevOps Retry             │             │
│               │    (120s polling)                 │             │
│               │         │                        │             │
│               │    "Done!" found                 │             │
│               │         │                        │             │
│               └────►  Re-merge  ◄────────────────┘             │
│                         │                                      │
│                    ┌────┴────┐                                 │
│                    ▼         ▼                                 │
│                 Done ✅   Retry/Fail                           │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│                    Webhook Fast-Paths                          │
│                                                               │
│  check_run failure ──► DevOps dispatch (proactive)            │
│  check_suite success ──► Re-merge attempt (proactive)         │
└──────────────────────────────────────────────────────────────┘
```

---

## Edge Cases

1. **DevOps fails 2×**: `devops_attempts >= 2` → broadcast `devops_cap_reached`, stop
2. **Server restart**: `check_in_review_issues()` polling fallback recovers stalled issues
3. **Concurrent webhook + polling**: `devops_active` deduplication guard prevents double-dispatch
4. **DevOps never posts "Done!"**: Timeout after `POST_DEVOPS_MAX_POLLS` (30 × 120 s ≈ 1 hr) → broadcast failure
5. **CI passes before DevOps finishes**: `check_suite` success webhook proactively triggers re-merge
