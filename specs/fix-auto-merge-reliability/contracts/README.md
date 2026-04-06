# API Contracts: Fix Auto-Merge Reliability

## No New API Contracts

This feature modifies **internal backend logic only**. No public API endpoints are added, changed, or removed.

### Rationale

All four phases of this fix operate on:
- Internal Python constants (`state.py`)
- Private helper functions (`webhooks.py:_get_auto_merge_pipeline`)
- Internal pipeline orchestration (`pipeline.py:_transition_after_pipeline_complete`)
- Background retry logic (`auto_merge.py:_auto_merge_retry_loop`)

The existing REST/WebSocket API surface remains unchanged:
- Webhook endpoints (`/webhooks/github`) — same payload format, same response
- Settings endpoints (`/settings/project/{project_id}`) — same auto-merge toggle behavior
- WebSocket events (`auto_merge_completed`, `auto_merge_failed`) — same event schema

### Internal Function Signature Change

The only signature change is internal to `webhooks.py`:

```python
# Before (sync, no extra params)
def _get_auto_merge_pipeline(issue_number: int) -> dict[str, Any] | None

# After (async, with owner/repo for project-level fallback)
async def _get_auto_merge_pipeline(issue_number: int, owner: str, repo: str) -> dict[str, Any] | None
```

This is a private function (prefixed with `_`) and is not part of any public API contract.
