# Runtime Error Checklist (P2)

**Category**: Runtime Errors
**Priority**: P2
**Scope**: All source files in `solune/backend/src/` and `solune/frontend/src/`

## Automated Scans

- [ ] Run `pyright src` on backend — review all type errors
- [ ] Run `tsc --noEmit` on frontend — review all type errors
- [ ] Run `pytest` and check for any runtime warnings or deprecation notices

## Manual Audit Areas

### Unhandled Exceptions

- [ ] All `async def` handlers in `src/api/` — Verify try/except covers external calls
- [ ] `src/services/chat_agent.py` — Verify LLM streaming errors are handled
- [ ] `src/services/copilot_polling/polling_loop.py` — Verify polling errors don't crash the service
- [ ] `src/services/signal_bridge.py` — Verify WebSocket disconnection is handled gracefully
- [ ] `src/services/github_projects/` — Verify GitHub API errors are handled (rate limits, 404s, 500s)

### Resource Leaks

- [ ] `src/services/database.py` — Verify all database connections are properly closed
- [ ] `src/services/cache.py` — Verify cached resources have TTL or cleanup
- [ ] HTTP clients (`httpx`) — Verify clients are used as context managers or properly closed
- [ ] `src/services/websocket.py` — Verify WebSocket connections are cleaned up on disconnect
- [ ] File handles — Verify all file operations use context managers (`with` statements)

### Race Conditions

- [ ] `src/services/task_registry.py` — Verify concurrent task creation is safe
- [ ] `src/services/copilot_polling/state.py` — Verify state updates are atomic
- [ ] `src/services/pipeline_state_store.py` — Verify pipeline state transitions are safe
- [ ] Frontend React state — Verify no stale closure issues in hooks

### Null/None References

- [ ] All optional return values — Verify callers check for None
- [ ] Dictionary access patterns — Verify `.get()` or `in` checks before key access
- [ ] Frontend optional chaining — Verify `?.` is used for nullable objects

### Missing Imports

- [ ] Verify all type hints reference imported types
- [ ] Verify all service dependencies are properly imported at module level

## Fix Criteria

For each finding:

1. Determine if the fix is obvious (clear error handling gap)
2. If obvious: add proper error handling + regression test
3. If ambiguous: add `TODO(bug-bash)` with description of trade-offs
