# Research: Performance Review

**Feature**: 002-performance-review
**Date**: 2026-03-31
**Status**: Complete

## Research Task 1: Current Backend Cache and Change-Detection State

**Context**: Verify whether the board cache TTL, WebSocket change detection, and sub-issue cache invalidation are fully implemented or only partially landed before planning optimization work.

### Decision: Backend cache infrastructure is fully implemented

**Rationale**: Codebase inspection confirms all three targeted mechanisms are in place:

1. **Board cache TTL (300s)** — `board.py` line 456 sets a 300-second TTL on board data entries via `cache.set(cache_key, board_data, ttl_seconds=300, data_hash=data_hash)`. This aligns with the frontend's 5-minute auto-refresh interval. Test coverage in `test_api_board.py` validates cache reuse and refresh bypass.

2. **WebSocket change detection** — `projects.py` (lines 412–427) computes `data_hash` on each periodic refresh and compares against the stored hash. On unchanged data, it calls `cache.refresh_ttl()` instead of re-storing, and does NOT emit a refresh event to the client. On changed data, it stores with the new hash and sends updated tasks. The stale-revalidation counter (`STALE_REVALIDATION_LIMIT = 20`, promoted to module-level constant) forces a fresh fetch after 20 consecutive stale cycles (~10 minutes at a 30-second interval).

3. **Sub-issue cache invalidation on manual refresh** — `board.py` (lines 388–399) iterates cached board items, constructs `sub_issues:{owner}/{repo}#{issue_number}` keys, and calls `cache.delete()` for each before fetching fresh data. Test coverage in `test_api_board.py` (`test_manual_refresh_clears_sub_issue_caches`) verifies this path.

**Alternatives considered**: None — this was a verification task, not a design decision.

**Remaining gaps**: The optimization work should target behavioral refinements (e.g., ensuring fallback polling doesn't accidentally trigger expensive refreshes) rather than re-implementing these mechanisms.

---

## Research Task 2: WebSocket Subscription Refresh Semantics in Projects API

**Context**: Understand how the WebSocket subscription periodic refresh works and whether it can emit redundant board refreshes when data is unchanged.

### Decision: Subscription refresh has change detection but stale-revalidation can trigger unnecessary fetches

**Rationale**: The subscription loop in `projects.py` refreshes every 30 seconds:

- **Warm cache path**: Returns immediately from cache without API call — zero cost.
- **Expired cache path**: Fetches fresh data, computes hash, compares to stored hash.
  - If unchanged: `refresh_ttl()` only — no client notification, no redundant data transfer.
  - If changed: Stores new data with new hash, sends updated tasks to client.
- **Stale-revalidation path**: After `STALE_REVALIDATION_LIMIT` (10) consecutive stale responses, forces a fresh fetch regardless of cache state. This is the main candidate for unnecessary API consumption during truly idle boards.

The stale-revalidation counter resets on any fresh fetch that detects changes, so an idle board with no changes will cycle through 10 stale reads (~5 minutes at 30s intervals) and then force one fresh fetch. This produces roughly 1 unnecessary API call per 5 minutes on a truly idle board — low but not zero.

**Alternatives considered**:
- Removing stale-revalidation entirely: Rejected because it would prevent eventual consistency if the cache silently becomes stale (e.g., after a backend restart or external change).
- Increasing the revalidation limit: A simple increase (e.g., to 20) would halve the idle API rate. Worth considering if the target reduction is not met with other fixes.

---

## Research Task 3: Fallback Polling Behavior and Board Refresh Interaction

**Context**: Determine whether fallback polling (when WebSocket is unavailable) triggers expensive board data refreshes.

### Decision: Fallback polling invalidates tasks queries only — not board data

**Rationale**: The frontend `useRealTimeSync.ts` fallback polling path calls `queryClient.invalidateQueries({ queryKey: ['projects', projectId, 'tasks'] })` — it only invalidates the lightweight tasks query, NOT the board data query (`['board', 'data', projectId]`). Board data refreshes are exclusively managed by `useBoardRefresh.ts` on its 5-minute auto-refresh timer or manual refresh button.

The backend polling loop (`polling_loop.py`) operates independently from the board endpoint. It uses `get_project_items()` directly with its own cycle cache, and does not invalidate or interact with the board cache. Expensive polling steps (output posting, stalled recovery) are rate-limit-aware and skipped when quota is low.

**Remaining concern**: If `useBoardRefresh.ts` auto-refresh fires while fallback polling is also active, the board could receive two refresh triggers in quick succession. However, `useBoardRefresh.ts` already has a 2-second debounce window (`BOARD_RELOAD_DEBOUNCE_MS = 2000`) that coalesces concurrent triggers.

**Alternatives considered**: N/A — this was a verification task.

---

## Research Task 4: Frontend Query Invalidation and Refresh Path Separation

**Context**: Map which frontend refresh sources trigger which data queries, and identify any overlap or redundancy.

### Decision: Four refresh sources exist with mostly separate responsibilities, but auto-refresh and WebSocket reconnection can overlap

**Rationale**: Current refresh source mapping:

| Refresh Source | Triggers | Cache Bypass | Debounced |
|---------------|----------|-------------|-----------|
| WebSocket `task_update`/`status_changed` | `invalidateQueries(['projects', pid, 'tasks'])` | No | Yes (2s reconnect debounce) |
| WebSocket `refresh` message | `invalidateQueries(['projects', pid, 'tasks'])` | No | Yes (2s reconnect debounce) |
| Fallback polling (30s) | `invalidateQueries(['projects', pid, 'tasks'])` | No | No (interval-spaced) |
| Auto-refresh (5min) | `invalidateQueries(['board', 'data', pid])` | No (uses backend cache) | Yes (2s board reload debounce) |
| Manual refresh button | `boardApi.getBoardData(pid, true)` → `setQueryData` | Yes (`refresh=true`) | Yes (cancels pending, resets timer) |

**Overlap identified**: When the WebSocket reconnects after a drop, the `initial_data` message triggers a tasks invalidation, which may coincide with a pending auto-refresh. The 2-second debounce on `useBoardRefresh` handles this correctly for board data, but the tasks query has no debounce — it relies on React Query's built-in deduplication for in-flight requests.

**No redundant board reloads from task updates**: Task-level WebSocket messages only invalidate `['projects', pid, 'tasks']`, not `['board', 'data', pid]`. This separation is already correct.

**Alternatives considered**: N/A — verification task.

---

## Research Task 5: Frontend Render Optimization Opportunities

**Context**: Identify low-risk rendering improvements in board and chat components without introducing new dependencies or virtualization.

### Decision: Three categories of low-risk optimizations are viable

**Rationale**:

1. **Derived-data stabilization in ProjectsPage.tsx**: The page already uses `useMemo` for `heroStats`, `rateLimitState`, and `syncStatusLabel`. The `useBoardControls()` hook handles sorting/grouping. Board data transformation (`transformedBoardData`) is computed in the hook — not in render. **Finding: Already well-optimized.** Minor gains possible from ensuring `column.items` array reference stability when data hasn't changed (prevents unnecessary `BoardColumn` re-renders even through `memo`).

2. **Component memoization depth**: `BoardColumn` and `IssueCard` are both `memo`'d with default shallow comparison. This is correct but depends on prop reference stability. If the parent passes new array/object references on each render (e.g., a new `column` object from React Query), the memo boundary is broken. **Opportunity**: Ensure board data transformation produces stable references for unchanged columns/items.

3. **Event listener rationalization**: `ChatPopup.tsx` already uses RAF-gated mousemove and lifecycle-scoped listeners (only active during resize). `AddAgentPopover.tsx` uses Radix Popover for positioning with no custom listeners. **Finding: Already well-optimized.** No material gains available here without changing the drag library.

**Alternatives considered**:
- Board virtualization: Deferred per spec scope — only if measurements show large boards still regress.
- React.lazy for board components: Unlikely to help since the board is the primary view.
- Web Workers for data transformation: Over-engineered for the current data volumes.

---

## Research Task 6: Adaptive Polling and Board Query Configuration

**Context**: Understand the adaptive polling mechanism in `useProjectBoard.ts` and its interaction with board refresh.

### Decision: Adaptive polling dynamically adjusts refetch intervals based on change detection

**Rationale**: `useProjectBoard.ts` uses a custom `useAdaptivePolling()` hook that:

- Computes a lightweight change-detection hash: `JSON.stringify(result.columns.map(c => c.item_count))`
- Reports poll success (data changed) or failure (data unchanged) to the adaptive polling tier
- Dynamically adjusts the React Query `refetchInterval` based on the current tier

Query configuration:
- Projects list: stale time 15 minutes, static polling (disabled on project switch)
- Board data: stale time 1 minute, adaptive polling via `useAdaptivePolling()`

The adaptive polling reduces backend load on stable boards by progressively increasing the refetch interval when no changes are detected. This complements the backend's hash-based change detection.

**Concern**: The board query's 1-minute stale time means React Query considers the data stale after 60 seconds, which can trigger a refetch on window focus or component remount. This is separate from the adaptive polling interval and could produce extra requests on tab switches.

**Alternatives considered**: N/A — documentation of existing behavior.

---

## Research Task 7: Repository Resolution Duplication Assessment

**Context**: Determine if there is duplicate repository-resolution logic across the codebase.

### Decision: No duplication exists — resolution is centralized

**Rationale**: All repository resolution goes through `resolve_repository()` in `src/utils.py`, which implements a 5-step fallback:
1. In-memory cache (300s TTL, token-scoped)
2. Project items via GraphQL
3. Project items via REST
4. Workflow configuration (DB)
5. App settings defaults

Both `workflow.py` and `projects.py` import and use this shared function. The issue description mentioned a "known duplicate repository-resolution path" in `workflow.py`, but inspection confirms it uses the same centralized utility.

**Alternatives considered**: N/A — no action needed.

---

## Research Task 8: Best Practices for React Query Cache Invalidation in Real-Time Systems

**Context**: Validate that the current invalidation strategy follows React Query 5 best practices for WebSocket-driven updates.

### Decision: Current approach is sound; minor refinements possible

**Rationale**: The codebase follows recommended React Query patterns:

- **Separate query keys** for tasks (`['projects', pid, 'tasks']`) and board data (`['board', 'data', pid]`) — enables granular invalidation.
- **`invalidateQueries` for background updates** — marks queries as stale and refetches in background, not blocking UI.
- **`setQueryData` for manual refresh** — writes directly to cache for immediate UI update, avoiding flash of stale data.
- **Optimistic updates for mutations** — drag-and-drop status changes use optimistic cache writes with rollback on error.

Best practice refinement: For WebSocket task updates, consider using `setQueryData` to merge the update directly into the cached tasks list instead of `invalidateQueries`. This would eliminate the refetch entirely for known changes. However, this requires the WebSocket message to contain the full updated task object, which should be verified.

**Alternatives considered**:
- Switching to React Query's `useMutation` for WebSocket updates: Over-engineered — WebSocket events are not user-initiated mutations.
- Using `queryClient.setQueriesData` for bulk updates: Only needed if multiple query key variants exist for the same data, which is not the case here.

---

## Summary of Findings

All targeted backend mechanisms (cache TTL, change detection, sub-issue invalidation) are fully implemented. No duplicate repository resolution exists. Frontend refresh paths are mostly well-separated with appropriate debouncing.

**Highest-value optimization targets** (ordered by expected impact):

1. **Backend**: Tune stale-revalidation behavior in WebSocket subscription to reduce idle API calls on stable boards.
2. **Frontend**: Ensure board data transformation produces stable references for unchanged columns/items to maximize `memo` effectiveness.
3. **Frontend**: Verify that adaptive polling tier configuration matches the desired idle-board behavior.
4. **Backend/Frontend**: Extend regression test coverage for the identified refresh paths and cache behaviors.

**No NEEDS CLARIFICATION items remain** — all technical unknowns have been resolved through codebase inspection.
