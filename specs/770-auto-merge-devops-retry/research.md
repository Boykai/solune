# Research: Auto-Merge After All Agents Complete + CI Pass + DevOps Retry

**Feature**: #770 — Auto-Merge After All Agents Complete + CI Pass + DevOps Retry  
**Date**: 2026-04-04

---

## 1. DevOps Agent Template Format

**Decision**: Follow existing `.agent.md` YAML front-matter + markdown body convention  
**Rationale**: All 18 existing agent templates in `backend/templates/.github/agents/` use this format. The deployed version at `.github/agents/devops.agent.md` already exists and follows this pattern.  
**Alternatives considered**:
- JSON agent config: Rejected — inconsistent with existing markdown-based templates
- Inline agent definition in Python: Rejected — agent templates are GitHub Copilot `.agent.md` files, not Python objects

**Evidence**: Examined `linter.agent.md` (204 lines), `tester.agent.md`, `quality-assurance.agent.md` — all share:
```yaml
---
name: <AgentName>
description: <one-liner>
mcp-servers:
  context7:
    type: http
    url: https://mcp.context7.com/mcp
    ...
---
# Agent Purpose
...
# Capabilities
...
# Workflow
...
# Completion
...
```

---

## 2. DevOps "Done!" Comment Detection

**Decision**: Scan issue comments for `devops: Done!` marker string using GitHub REST API  
**Rationale**: The existing DevOps agent template already includes the instruction: *"When work is done, include marker `devops: Done!` in final comment to signal completion to pipeline orchestrator."* The REST endpoint `GET /repos/{owner}/{repo}/issues/{number}/comments` (sorted newest-first with `?direction=desc`) provides efficient scanning.  
**Alternatives considered**:
- Webhook-based detection (issue_comment event): Would require new webhook handler registration + event routing. More responsive but adds complexity. **Retained as complementary future enhancement** — polling is the resilient baseline.
- Custom issue label: Rejected — labels are used for classification, not completion signaling in this codebase.
- Sub-issue closure: Rejected — DevOps operates on the parent issue directly, not a sub-issue.

**Implementation detail**:
```python
async def _check_devops_done_comment(
    access_token: str, owner: str, repo: str, issue_number: int
) -> bool:
    """Check if DevOps agent posted a 'Done!' completion marker."""
    comments = await github_service.list_issue_comments(
        access_token, owner, repo, issue_number,
        per_page=10, direction="desc",
    )
    return any("devops: Done!" in c.get("body", "") for c in comments)
```

---

## 3. Post-DevOps Re-Merge Trigger Mechanism

**Decision**: Polling loop at 120 s intervals after DevOps dispatch, with webhook as proactive fast-path  
**Rationale**: Polling is resilient to webhook delivery failures and server restarts. The 120 s interval balances responsiveness with API quota conservation. Webhook handlers (Gap 3) provide a faster path when available, but polling is the guaranteed fallback.  
**Alternatives considered**:
- Webhook-only (no polling): Rejected — webhook delivery is not guaranteed; server restarts lose in-flight state. The parent issue explicitly specifies: *"Webhooks provide proactive path; polling provides resilient fallback."*
- Shorter interval (30 s): Rejected — too aggressive for GitHub API rate limits; 120 s aligns with `ASSIGNMENT_GRACE_PERIOD_SECONDS` convention.
- Longer interval (300 s): Rejected — adds unnecessary latency to the merge cycle.

**Constants** (in `state.py`):
```python
POST_DEVOPS_POLL_INTERVAL = 120.0  # seconds between "Done!" checks
POST_DEVOPS_MAX_POLLS = 30         # max polls (~1 hour) before timeout
```

---

## 4. Webhook → Auto-Merge Issue Lookup

**Decision**: Use reverse PR-to-issue lookup via existing helpers  
**Rationale**: The `_discover_main_pr_for_review()` function in `helpers.py` already implements a 5-strategy PR discovery from issue number. The reverse direction (PR → issue) can leverage the in-memory `_issue_main_branches` cache or the GitHub `timeline` API to find linked issues.  
**Alternatives considered**:
- New dedicated PR-to-issue mapping table: Rejected — adds database complexity for a lookup that's already cacheable in memory.
- Parse PR body for issue references: Fragile — not all PRs reference the parent issue in the body.
- Use GitHub's "Development" sidebar API: Most reliable approach. PRs linked via development sidebar expose the issue number in the timeline events.

**Implementation approach**:
1. Webhook receives PR number from `check_run.pull_requests[].number`
2. Look up issue in `_issue_main_branches` cache (reverse scan: find issue where stored branch matches PR)
3. If cache miss: use `GET /repos/{owner}/{repo}/issues?mentioned=...` or pipeline state to find the parent issue
4. Cache the mapping for future lookups

---

## 5. check_suite "success" Handling for Proactive Re-Merge

**Decision**: Add `conclusion="success"` branch to `handle_check_suite_event()` for proactive re-merge  
**Rationale**: Currently `handle_check_suite_event()` only processes `conclusion="failure"`. Adding a `"success"` branch enables proactive merge when all CI checks pass, without waiting for the polling loop.  
**Alternatives considered**:
- Use `check_run` success events instead: Rejected — `check_run` fires per individual check; `check_suite` fires once when *all* checks in a suite complete, which is the correct signal for "all CI passed."
- Only rely on polling: Rejected — adds 60-240 s unnecessary latency when webhooks are available.

**Key change**: Modify the early-return guard:
```python
# BEFORE: Only process failures
if conclusion != "failure":
    return {"status": "ignored", "reason": "conclusion_not_failure"}

# AFTER: Process both failure and success
if conclusion not in ("failure", "success"):
    return {"status": "ignored", "reason": "conclusion_not_relevant"}
```

---

## 6. Existing Code Patterns — Best Practices

### Exponential Backoff (auto_merge.py)
- Pattern: `delay = BASE_DELAY * 2 ** (attempt - 1)`
- Constants in `state.py`: `AUTO_MERGE_RETRY_BASE_DELAY = 60.0`, `MAX_AUTO_MERGE_RETRIES = 3`
- Background task via `asyncio.create_task()`

### Deduplication (state.py)
- Pattern: `BoundedDict` / `BoundedSet` with `maxlen` caps
- Key format: `"issue_number:agent_name"` or `issue_number` as int key
- Check-then-act pattern with logging on skip

### Agent Dispatch (auto_merge.py)
- Pattern: Check `devops_active` + `devops_attempts < 2` guards
- Build instructions → assign Copilot → update metadata → broadcast event
- Return `True/False` for caller to decide next action

### WebSocket Broadcasting (pipeline.py, auto_merge.py)
- Pattern: `_cp.connection_manager.broadcast_to_project(project_id, {...})`
- Event types: `devops_triggered`, `auto_merge_completed`, `auto_merge_failed`

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| GitHub API rate limiting during polling | Medium | Retry delayed | Use 120 s interval; honor `RATE_LIMIT_PAUSE_THRESHOLD` |
| Webhook delivery failure | Low | Delayed merge | Polling fallback ensures eventual consistency |
| DevOps agent fails to post "Done!" | Low | Stuck in polling | Timeout after `POST_DEVOPS_MAX_POLLS` (~1 hr); broadcast failure |
| Concurrent DevOps dispatch from webhook + polling | Medium | Duplicate work | `devops_active` deduplication guard in `dispatch_devops_agent()` |
| Server restart during DevOps work | Medium | Lost polling task | `check_in_review_issues()` fallback in pipeline.py recovers |
