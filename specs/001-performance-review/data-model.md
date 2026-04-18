# Data Model: Performance Review

**Feature Branch**: `001-performance-review`
**Date**: 2026-04-18
**Source**: Extracted from spec.md functional requirements and codebase analysis

## Key Entities

### 1. Board Data Cache

Represents cached board content including items, columns, and metadata. This is the primary entity affected by backend optimization work.

**Existing Implementation**: `InMemoryCache` in `cache.py`, keyed by `board_data:{project_id}`

| Field | Type | Description |
|-------|------|-------------|
| cache_key | `str` | `"board_data:{project_id}"` — unique per project |
| value | `BoardData` | Full board response (columns, items, load_state, rate_limit) |
| ttl_seconds | `int` | 300 (5 minutes) — aligned with frontend auto-refresh |
| expires_at | `float` | `time.monotonic() + ttl_seconds` |
| data_hash | `str \| None` | SHA-256 hash of value (excluding rate_limit) for change detection |
| etag | `str \| None` | HTTP ETag from upstream (not currently used for board) |
| last_modified | `str \| None` | HTTP Last-Modified from upstream |

**Relationships**:

- One Board Data Cache entry per active project
- Contains references to Sub-Issue Cache entries (via `sub_issues:{owner}/{repo}#{issue_number}` keys)
- Invalidated by manual refresh (cache bypass + sub-issue cache clear)
- TTL refresh (no re-store) when data_hash matches on refetch

**Validation Rules**:

- `cache_key` must include a valid project ID
- `data_hash` is computed excluding `rate_limit` field to prevent stale rate-limit data leaking across requests
- `expires_at` must be monotonic-clock-based to avoid system clock drift issues

**State Transitions**:

```text
[Empty] → set() → [Warm] → get() → [Warm] (hit)
[Warm] → TTL expires → [Stale] → get_stale() → [Stale] (fallback)
[Warm] → manual refresh → [Empty] → fetch → [Warm]
[Warm] → cached_fetch(hash match) → [Warm] (TTL refreshed only)
[Warm] → cached_fetch(hash mismatch) → [Warm] (value + TTL updated)
[Stale] → rate_limit_fallback → serve stale + warning
```

---

### 2. Sub-Issue Cache

Represents cached sub-issue data associated with board items. Key optimization target for reducing GitHub API call count during board refreshes.

**Existing Implementation**: `InMemoryCache` in `cache.py`, keyed by `sub_issues:{owner}/{repo}#{issue_number}`

| Field | Type | Description |
|-------|------|-------------|
| cache_key | `str` | `"sub_issues:{owner}/{repo}#{issue_number}"` — per parent issue |
| value | `list[SubIssue]` | Sub-issue data for one parent issue |
| ttl_seconds | `int` | 300 (default) — inherits from cache config |
| expires_at | `float` | `time.monotonic() + ttl_seconds` |
| data_hash | `str \| None` | SHA-256 hash of sub-issue data |

**Relationships**:

- Many Sub-Issue Cache entries per Board Data Cache entry (one per parent issue with sub-issues)
- Cleared per-issue on manual refresh (lines 527–536 in `board.py`)
- Preserved on auto-refresh and WebSocket-triggered refreshes (optimization target)

**Validation Rules**:

- `cache_key` must match pattern `sub_issues:{owner}/{repo}#{number}` where number is a positive integer
- `value` may be an empty list (parent issue has no sub-issues — should still cache to avoid re-fetching)

**State Transitions**:

```text
[Empty] → board refresh fetches sub-issues → [Warm]
[Warm] → auto-refresh / WS update → [Warm] (preserved, reused)
[Warm] → manual refresh → [Empty] → re-fetch → [Warm]
[Warm] → TTL expires → [Stale] → get_stale() or re-fetch
```

---

### 3. Refresh Policy

Represents the coordinated rules governing when and how board data is refreshed. This is a logical entity spanning three frontend hooks.

**Existing Implementation**: Distributed across `useRealTimeSync.ts`, `useBoardRefresh.ts`, and `useProjectBoard.ts`

| Attribute | Type | Description |
|-----------|------|-------------|
| source | `'websocket' \| 'polling' \| 'auto-refresh' \| 'manual'` | Which mechanism triggered the refresh |
| debounce_window_ms | `number` | 2000ms — `BOARD_RELOAD_DEBOUNCE_MS` in `useBoardRefresh` |
| auto_refresh_interval_ms | `number` | 300000 (5 min) — suppressed when WebSocket connected |
| cache_bypass | `boolean` | `true` only for manual refresh; auto/WS/polling use cached path |
| is_websocket_connected | `boolean` | Tracked by `useRealTimeSync` — suppresses auto-refresh timer |
| last_board_reload_at | `number` | Timestamp of last `requestBoardReload()` execution |

**Refresh Source Behavior Matrix**:

| Source | Invalidates Board Query | Bypasses Backend Cache | Clears Sub-Issue Cache | Debounced |
|--------|------------------------|----------------------|----------------------|-----------|
| WebSocket message | No (task-level update via callback) | No | No | N/A |
| Polling fallback | Via `requestBoardReload()` | No | No | Yes (2s) |
| Auto-refresh timer | Via `invalidateQueries()` | No | No | No (timer-gated) |
| Manual refresh | Via `setQueryData()` | Yes (`refresh=true`) | Yes | No (immediate) |

**State Transitions**:

```text
[Idle] → WS message → resetTimer() → [Idle] (timer restarted)
[Idle] → polling tick → requestBoardReload() → debounce check → [Refreshing] or [Idle]
[Idle] → auto-refresh timer fires → invalidateQueries() → [Refreshing]
[Idle] → manual refresh → cancelQueries() + getBoardData(refresh=true) → [Refreshing]
[Refreshing] → response received → setQueryData() → [Idle]
[Any] → tab hidden → [Paused] → tab visible → staleness check → [Idle] or [Refreshing]
```

---

### 4. Performance Baseline

Represents a recorded snapshot of system performance metrics at a point in time. This is a measurement artifact, not a runtime entity.

**Implementation**: Captured via test instrumentation and manual profiling (no persistent storage)

| Metric Category | Metric | Measurement Method |
|----------------|--------|-------------------|
| Backend — Idle API | GitHub API calls during 10-min idle window | pytest mock call counting |
| Backend — Endpoint Cost | Board endpoint response time + triggered API calls | pytest timing + mock counting |
| Backend — WS/Polling | Refresh signals sent when data unchanged | pytest mock assertion |
| Frontend — Render | Initial board load render time | Browser DevTools / Vitest profiling |
| Frontend — Interaction | Frame rate during scroll/drag on 50+ item board | Browser DevTools Performance tab |
| Frontend — Network | Board data fetches per 2-min observation window | Network tab / Vitest mock counting |
| Frontend — Rerender | Component rerender count during board-level state change | React DevTools Profiler |

**Relationships**:

- Before-baseline captured in Phase 1 (blocks all optimization work)
- After-baseline captured in Phase 3 (verification)
- Comparison validates success criteria SC-001 through SC-010

---

### 5. Coalesced Fetch State

Represents in-flight request deduplication for concurrent cache misses. Already implemented — included for completeness.

**Existing Implementation**: `_inflight_fetches` dict in `InMemoryCache`, `_inflight_graphql` BoundedDict in `GitHubProjectsService`

| Field | Type | Description |
|-------|------|-------------|
| inflight_key | `str` | Cache key or SHA-256 hash of query parameters |
| task | `asyncio.Task` | Shared async task that concurrent callers await |
| maxlen | `int \| None` | 256 for GraphQL (BoundedDict); unbounded for cache |

**State Transitions**:

```text
[No inflight] → first caller → create Task → [Inflight]
[Inflight] → second caller → await existing Task → [Inflight]
[Inflight] → Task completes → remove from dict → [No inflight]
[Inflight] → BoundedDict eviction → cancel evicted Task → [No inflight]
```

---

## Entity Relationship Diagram

```text
┌─────────────────────┐
│  Board Data Cache    │ 1 per project
│  (InMemoryCache)     │
│  TTL: 300s           │
│  Hash: SHA-256       │
└────────┬────────────┘
         │ contains refs to
         ▼
┌─────────────────────┐
│  Sub-Issue Cache     │ N per board (1 per parent issue)
│  (InMemoryCache)     │
│  TTL: 300s           │
│  Cleared on manual   │
│  refresh only        │
└─────────────────────┘

┌─────────────────────┐       ┌─────────────────────┐
│  Refresh Policy      │──────▶│  Board Data Cache    │
│  (3 frontend hooks)  │ triggers│                     │
│  Debounce: 2s        │       └─────────────────────┘
│  Auto-refresh: 5min  │
└────────┬────────────┘
         │ sources
         ▼
┌─────────────────────────────────────────────┐
│  WebSocket  │  Polling  │  Auto  │  Manual  │
│  (light)    │  (debounced)│(timer)│ (bypass) │
└─────────────────────────────────────────────┘

┌─────────────────────┐
│  Coalesced Fetch     │ deduplicates concurrent
│  (inflight dict)     │ requests to same cache key
└─────────────────────┘

┌─────────────────────┐
│  Performance Baseline│ measurement artifact
│  (before + after)    │ validates SC-001..SC-010
└─────────────────────┘
```
