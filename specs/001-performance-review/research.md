# Research: Performance Review

**Feature Branch**: `001-performance-review`
**Date**: 2026-04-18
**Status**: Complete — all unknowns resolved

## Research Tasks

### RT-001: Current Backend Cache and Change-Detection State

**Context**: The spec assumes hash-based change detection and coalesced fetches are functional. Need to confirm the current implementation status before planning optimization work.

**Decision**: Confirmed fully implemented — no reimplementation needed.

**Rationale**: Code inspection of `cache.py` confirms:

- `InMemoryCache` supports per-entry `data_hash` (SHA-256 via `compute_data_hash()`)
- `cached_fetch()` accepts a `data_hash_fn` parameter; when the hash matches the existing entry, only the TTL is refreshed (no redundant store)
- `coalesced_fetch()` deduplicates concurrent requests for the same cache key using a shared `asyncio.Task` via `_inflight_fetches` dict
- `get_stale()` returns expired entries for rate-limit and error fallback
- Board cache TTL is 300 seconds (5 minutes) in `board.py` line 235
- Sub-issue cache key pattern: `f"sub_issues:{owner}/{repo}#{issue_number}"` — cleared per-issue on manual refresh (lines 527–536 in `board.py`)

**Alternatives considered**: None — the current implementation is correct and complete. Optimization targets utilization of these mechanisms, not reimplementation.

---

### RT-002: WebSocket Subscription Refresh Semantics

**Context**: The spec targets WebSocket change detection as a key area. Need to understand current WebSocket subscription behavior in `projects.py` and how it interacts with the polling loop.

**Decision**: WebSocket subscriptions provide real-time event delivery but do not perform server-side change detection. The polling loop provides the actual data refresh cycle.

**Rationale**: Code inspection of `projects.py` and `websocket.py` confirms:

- `ConnectionManager` tracks WebSocket connections per project via `broadcast_to_project()`
- `select_project()` subscribes the connection and triggers `_start_copilot_polling()` with repository resolution
- WebSocket messages are broadcast from the polling loop on agent completion, task updates, and status changes
- The WebSocket layer itself does not perform hash-based change detection — it relays events from the polling pipeline
- `_schedule_board_warmup()` prefetches board data in the background when a project is selected

The optimization opportunity is ensuring that the frontend correctly handles WebSocket messages as lightweight updates (without triggering full board refetches) and that the polling loop does not send redundant refresh signals when data is unchanged.

**Alternatives considered**: Server-side WebSocket change detection (comparing hashes before broadcasting). Rejected because the current broadcast-on-event model is correct — the issue is on the frontend consumption side, not the broadcast side.

---

### RT-003: Polling Loop Rate-Limit Budget and Expensive Steps

**Context**: The polling loop in `polling_loop.py` has steps flagged as "expensive." Need to understand the current rate-limit-aware behavior.

**Decision**: Confirmed rate-limit-aware polling with three thresholds is already implemented. Optimization should focus on validating that idle boards do not trigger expensive steps unnecessarily.

**Rationale**: Code inspection of `polling_loop.py` and its state module confirms:

- Three rate-limit thresholds: `RATE_LIMIT_PAUSE_THRESHOLD` (pause polling), `RATE_LIMIT_SKIP_EXPENSIVE_THRESHOLD` (skip steps 0 and 5), `RATE_LIMIT_SLOW_THRESHOLD` (log warning)
- Per-cycle cache (`_cycle_cache`) prevents duplicate sub-fetches within a single polling iteration
- Stale rate-limit guard: clears cached rate-limit data if the reset window has passed, preventing infinite pause loops
- Steps 0 (post agent outputs) and 5 (recover stalled) are flagged as expensive and skipped when budget is low

The remaining optimization opportunity is ensuring that the polling loop does not trigger board-level refreshes when no data has changed (by leveraging the existing hash-based change detection from the cache layer).

**Alternatives considered**: Removing expensive polling steps entirely. Rejected because they serve legitimate purposes (agent output posting, stall recovery) and are already conditionally skipped under rate-limit pressure.

---

### RT-004: Frontend Refresh Policy Architecture

**Context**: Three hooks coordinate board refresh behavior: `useRealTimeSync`, `useBoardRefresh`, and `useProjectBoard`. Need to map the current interaction model to identify where broad query invalidation occurs.

**Decision**: The current architecture has clear responsibilities but one key gap — polling fallback in `useRealTimeSync` can trigger broad query invalidation that includes the expensive board data query. The fix should ensure polling fallback uses the same `onRefreshTriggered` callback path as WebSocket updates.

**Rationale**: Code inspection confirms the following refresh flow:

1. **`useRealTimeSync`**: Manages WebSocket connection + polling fallback. Calls `onRefreshTriggered()` on WebSocket messages. Polling fallback triggers the same callback.
2. **`useBoardRefresh`**: Receives `resetTimer()` calls from `useRealTimeSync` via the `onRefreshTriggered` callback. Manages auto-refresh timer (5 min), manual refresh (cache bypass), and debounced board reload (`requestBoardReload()` with 2s window).
3. **`useProjectBoard`**: Owns the board data query via `useQuery`. Adaptive polling adjusts `refetchInterval` based on detected changes (hash comparison of `columns.map(c => c.item_count)`).

The debounce window (2s) and auto-refresh suppression during active WebSocket are already implemented. The optimization opportunity is:
- Ensuring `useRealTimeSync` polling fallback does not trigger `invalidateQueries` directly on the board data key (should go through `requestBoardReload()` for debouncing)
- Stabilizing callback references passed to board components to prevent unnecessary rerenders

**Alternatives considered**: Replacing the three-hook architecture with a single unified hook. Rejected because the current separation of concerns is clean and each hook has clear single-responsibility. The fix is surgical, not architectural.

---

### RT-005: Frontend Render Performance Patterns

**Context**: Need to assess current memoization discipline in board components and identify gaps.

**Decision**: `BoardColumn` and `IssueCard` are already wrapped in `React.memo()`. Key gaps are: unstable callback references from parent, non-memoized components (`ChatPopup`, `AddAgentPopover`), and repeated derived-data computation in `ProjectsPage`.

**Rationale**: Code inspection confirms:

- **`BoardColumn`**: Wrapped in `memo()`, uses `useMemo` for groups computation. Risk: parent may pass new `onCardClick` function on every render, defeating memoization.
- **`IssueCard`**: Wrapped in `memo()`, uses `useMemo` for labels, snippet, agent slug parsing. Risk: parent may pass new `onClick` on every render.
- **`ChatPopup`**: Not memoized but implements RAF-gating on resize drag (good pattern via `requestAnimationFrame`). Risk: rerenders on parent state changes.
- **`AddAgentPopover`**: Not memoized. Uses `useMemo` for `filteredAgents` and `assignedSlugs`. Risk: rerenders on parent state changes.
- **`ProjectsPage`**: 11+ useQuery/useMutation hooks; multiple `useMemo` hooks for derived data (`heroStats`, `rateLimitState`, `syncStatusLabel`). Risk: modal/dialog state toggles trigger full page rerenders that cascade to all children.

Optimization approach:
1. Stabilize callback props via `useCallback` in parent components
2. Memoize derived data that is recomputed unnecessarily
3. Consider `memo()` for `AddAgentPopover` if parent rerenders are frequent
4. Throttle positioning listeners in popover components (Radix handles most internally)

**Alternatives considered**: React Compiler (auto-memoization). Rejected because it is not yet stable for production use and would be a new dependency. Board virtualization (react-window or @tanstack/virtual). Rejected for first pass — defer unless baselines show large boards still lag after lighter fixes.

---

### RT-006: Duplicate Repository Resolution in workflow.py

**Context**: `workflow.py` calls `resolve_repository()` from `utils.py` but also has its own issue-fetching path that does not cache results.

**Decision**: The duplicate is benign for this performance pass. `resolve_repository()` in `utils.py` is already cached (300s TTL with token-scoped keys). The `_build_retry_context()` issue fetch in `workflow.py` is not on the hot path for idle board viewing.

**Rationale**: `workflow.py`'s `_build_retry_context()` calls `resolve_repository()` from `utils.py` (which is cached) and separately calls `get_issue_with_comments()` (which is not cached). However, this path only executes during explicit workflow retry operations — not during idle board viewing or polling. Optimizing this is out of scope for the idle-rate-limit reduction goals.

**Alternatives considered**: Caching issue data in `_build_retry_context()`. Deferred — not on the idle hot path and would add complexity without measurable impact on the target success criteria.

---

### RT-007: Best Practices for React Performance Optimization

**Context**: Need to confirm best practices for the specific optimization patterns planned.

**Decision**: Use established React patterns: `React.memo()` with stable props, `useCallback` for event handlers, `useMemo` for expensive computations, `requestAnimationFrame` gating for drag handlers, and `throttle` for positioning listeners.

**Rationale**:
- `React.memo()` is effective when combined with stable prop references (useCallback, useMemo). Already used for `BoardColumn` and `IssueCard`.
- `useCallback` prevents child re-renders when parent state changes don't affect the callback. Must include correct dependency arrays.
- `useMemo` prevents re-execution of expensive derivations. Already used extensively in `ProjectsPage`.
- RAF gating is already implemented in `ChatPopup` for drag resize. Good pattern to extend to other high-frequency handlers.
- TanStack React Query's `structuralSharing` (enabled by default) prevents unnecessary rerenders when query data is referentially identical.

**Alternatives considered**: External memoization libraries (reselect, proxy-memoize). Rejected — React's built-in hooks are sufficient for the optimizations planned and avoid new dependencies.

---

### RT-008: Backend Testing Strategy for Performance Verification

**Context**: The spec requires extending test coverage (FR-012, SC-008). Need to confirm existing test patterns.

**Decision**: Extend existing pytest test classes with new test cases that validate the optimized behavior. Use the established mock patterns (patching cache, service, and settings).

**Rationale**: Existing tests provide comprehensive coverage:
- `test_cache.py` (38 tests): Covers TTL, hashing, coalesced fetch, stale fallback
- `test_api_board.py` (75 tests): Covers cache hit/miss, sub-issue invalidation, manual refresh
- `test_copilot_polling.py` (317 tests): Covers polling lifecycle, rate limits, step skipping

New tests should validate:
- Idle board produces zero redundant API calls over simulated interval
- Warm sub-issue cache reduces total API call count
- Polling fallback does not trigger expensive board refresh
- WebSocket change detection prevents downstream refresh on unchanged data

**Alternatives considered**: Property-based testing with Hypothesis for cache behavior. Considered but deferred — the existing pattern of explicit scenario tests is more readable and already well-established in the codebase.

## Summary of Decisions

| # | Topic | Decision | Key Rationale |
|---|-------|----------|---------------|
| RT-001 | Cache/change detection | Fully implemented; optimize utilization | Code confirms hash, coalescing, stale fallback all present |
| RT-002 | WebSocket subscriptions | Event relay, not server-side detection | Frontend consumption is the optimization target |
| RT-003 | Polling rate limits | Three thresholds implemented; validate idle behavior | Expensive steps already conditionally skipped |
| RT-004 | Frontend refresh policy | Surgical fix to polling fallback path | Three-hook architecture is sound; gap is in invalidation scope |
| RT-005 | Render performance | Stabilize callbacks + selective memoization | Existing memo discipline is good; gaps are in parent callbacks |
| RT-006 | Duplicate repo resolution | Benign for this pass; defer | Not on idle hot path |
| RT-007 | React optimization patterns | Built-in hooks sufficient | No new dependencies needed |
| RT-008 | Test strategy | Extend existing test classes | Established patterns cover all optimization areas |
