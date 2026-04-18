# Contract: Board Refresh Policy

**Feature Branch**: `001-performance-review`
**Date**: 2026-04-18
**Type**: Internal behavioral contract (no external API changes)

## Overview

This contract defines the refresh behavior for board data across all trigger sources. It codifies the rules that the three frontend hooks (`useRealTimeSync`, `useBoardRefresh`, `useProjectBoard`) and the backend board endpoint must follow after optimization.

No new API endpoints are introduced. No existing endpoint signatures change. This contract governs the **behavioral rules** for when and how existing endpoints are called.

## Refresh Sources and Rules

### Rule 1: WebSocket Message → Task-Level Update Only

**Trigger**: WebSocket message of type `task_update`, `task_created`, `status_changed`, `auto_merge_*`, `devops_triggered`
**Action**: Call `onRefreshTriggered()` → `resetTimer()` in `useBoardRefresh`
**Board Data Query**: NOT invalidated. Timer restarted only.
**Sub-Issue Cache**: NOT cleared.
**Rationale**: WebSocket messages indicate task-level changes. The board data query should not refetch because the update is lightweight and the auto-refresh timer restart ensures eventual consistency.

### Rule 2: WebSocket `initial_data` → Debounced Board Reload

**Trigger**: WebSocket message of type `initial_data` (connection/reconnection)
**Action**: Debounced (2000ms) — suppresses duplicate `initial_data` within window
**Board Data Query**: Invalidated via `requestBoardReload()` (uses `invalidateQueries`, not force-refresh)
**Sub-Issue Cache**: NOT cleared.
**Rationale**: On reconnection, data may have changed during the disconnection period. A debounced reload ensures freshness without triggering a storm of concurrent refetches.

### Rule 3: Polling Fallback → Debounced Board Reload

**Trigger**: Polling interval fires when WebSocket is disconnected
**Action**: Call `onRefreshTriggered()` → `requestBoardReload()` in `useBoardRefresh`
**Board Data Query**: Invalidated via `requestBoardReload()` (debounced, 2000ms window)
**Sub-Issue Cache**: NOT cleared.
**Rationale**: Polling fallback is a degraded-mode refresh path. It must go through the same debouncing as other triggers to prevent polling storms.

### Rule 4: Auto-Refresh Timer → Lightweight Invalidation

**Trigger**: 5-minute auto-refresh timer fires (only when WebSocket is NOT connected)
**Action**: `invalidateQueries()` on the board data query key
**Board Data Query**: Invalidated (TanStack Query refetches using normal queryFn, may hit backend cache)
**Sub-Issue Cache**: NOT cleared.
**Rationale**: Auto-refresh is a background freshness mechanism. It should use the cached path (not bypass) and is suppressed entirely when WebSocket is delivering real-time updates.

### Rule 5: Manual Refresh → Full Cache Bypass

**Trigger**: User clicks the manual refresh button
**Action**: `cancelQueries()` → `boardApi.getBoardData(projectId, refresh=true)` → `setQueryData()`
**Board Data Query**: Replaced with fresh data (bypasses backend cache via `refresh=true` param)
**Sub-Issue Cache**: Cleared (per-issue deletion in `board.py` lines 527–536)
**Rationale**: Manual refresh is an explicit user intent to get the latest data. It bypasses all caches and ensures a clean fetch from GitHub.

### Rule 6: Concurrent Trigger Deduplication

**Trigger**: Multiple refresh triggers fire within 2000ms (e.g., WebSocket reconnection + auto-refresh timer + polling fallback)
**Action**: Only one board data fetch executes within the debounce window
**Implementation**: `lastBoardReloadRef` timestamp + `BOARD_RELOAD_DEBOUNCE_MS` (2000ms) gate in `requestBoardReload()`
**Exception**: Manual refresh always executes immediately and cancels any pending debounced reload
**Rationale**: Prevents the "polling storm" scenario where multiple sources trigger concurrent refetches.

### Rule 7: Tab Visibility → Staleness Check

**Trigger**: Browser tab becomes visible after being hidden
**Action**: Check `lastRefreshedAt` against auto-refresh threshold. Refresh only if stale.
**Board Data Query**: Invalidated only if data age exceeds threshold
**Sub-Issue Cache**: NOT cleared.
**Rationale**: Prevents catch-up refresh storms when a tab is restored after extended backgrounding.

### Rule 8: Project Switch → Cancel Previous Work

**Trigger**: User selects a different project
**Action**: Cancel in-flight background work for previous project. Reset `previousDataRef` and `lastUpdated` in `useProjectBoard`.
**Board Data Query**: New query key (`['board', 'data', newProjectId]`) — old query naturally abandoned
**Sub-Issue Cache**: Previous project's sub-issue entries remain until TTL expiration (not actively cleared)
**Rationale**: Prevents wasted API budget on data the user is no longer viewing.

## Backend Board Endpoint Contract

### `GET /api/v1/board/projects/{project_id}`

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `refresh` | `bool` | `false` | When `true`: bypass backend cache, clear sub-issue caches, fetch fresh from GitHub |
| `load_mode` | `str` | `"INITIAL"` | `"INITIAL"` for fast first paint; `"FULL"` for complete data |

**Cache Behavior**:

| Scenario | Cache Action | Sub-Issue Cache | Response Source |
|----------|-------------|-----------------|-----------------|
| `refresh=false`, cache warm | Return cached | Preserved | Cache |
| `refresh=false`, cache expired | Fetch + cache | Preserved | GitHub API |
| `refresh=true` | Fetch + cache | Cleared per-issue | GitHub API |
| `refresh=false`, rate limited | Return stale | Preserved | Stale cache |
| `refresh=true`, rate limited | Return stale + warning | Preserved (bypass failed) | Stale cache |

**Coalescing**: Concurrent requests for the same `(project_id, load_mode)` share a single in-flight fetch via `coalesced_fetch()`.

**Change Detection**: `data_hash` (SHA-256, excluding `rate_limit` field) is computed on each fetch. If hash matches existing cache entry, only TTL is refreshed (no redundant store).

## Success Criteria Mapping

| Contract Rule | Success Criteria |
|--------------|-----------------|
| Rule 1 (WS → task-level only) | SC-003 (lightweight updates in <2s) |
| Rule 2 (initial_data debounce) | SC-004 (max 1 fetch per 2s) |
| Rule 3 (polling → debounced) | SC-004, SC-001 (reduced idle API calls) |
| Rule 4 (auto-refresh suppression) | SC-001 (reduced idle API calls) |
| Rule 5 (manual → bypass) | FR-013 (preserve manual refresh behavior) |
| Rule 6 (deduplication) | SC-004 (max 1 fetch per 2s debounce) |
| Rule 7 (tab visibility) | Edge case: overnight tab scenario |
| Rule 8 (project switch cancel) | FR-015 (cancel/deprioritize previous work) |
