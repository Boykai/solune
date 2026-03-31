# Data Model: Performance Review

**Feature**: 002-performance-review
**Date**: 2026-03-31
**Status**: Complete

## Overview

This feature does not introduce new persistent entities or data models. It optimizes the behavior of existing in-memory cache entries, refresh coordination state, and query invalidation patterns. The entities below document the existing data structures that are being optimized, their relationships, and the validation/state-transition rules that govern performance-critical paths.

## Entities

### CacheEntry\[T\]

**Location**: `solune/backend/src/services/cache.py`
**Role**: Core cache storage unit for all backend cached data (board data, tasks, sub-issues).

| Field | Type | Description |
|-------|------|-------------|
| value | T | The cached data payload |
| expires_at | datetime | UTC timestamp when entry becomes stale (`utcnow() + ttl`) |
| etag | str \| None | HTTP ETag for conditional requests |
| last_modified | str \| None | HTTP Last-Modified header value |
| data_hash | str \| None | SHA-256 hash of serialized data for change detection |

**Validation Rules**:
- `is_expired` property: `True` when `utcnow() > expires_at`
- `data_hash` computed via `compute_data_hash()`: SHA-256 of JSON-serialized value
- Hash comparison on store: if hash matches existing entry, only `refresh_ttl()` is called (no re-store)

**State Transitions**:
```text
[Empty] → set(value, ttl) → [Warm]
[Warm] → expires_at reached → [Stale]
[Stale] → refresh_ttl() → [Warm]  (hash match, no data change)
[Stale] → set(new_value, ttl) → [Warm]  (hash mismatch, data changed)
[Warm|Stale] → delete() → [Empty]  (manual refresh invalidation)
[Stale] → get_stale() → returns value  (graceful degradation)
```

### BoardData

**Location**: `solune/backend/src/api/board.py` (response model)
**Role**: Complete project board state returned by the board endpoint.

| Field | Type | Description |
|-------|------|-------------|
| columns | list[Column] | Board columns with status metadata |
| columns[].items | list[BoardItem] | Tasks within each column |
| columns[].item_count | int | Total item count (used for frontend change detection) |
| rate_limit | RateLimitInfo | Current GitHub API rate-limit state |
| data_hash | str | SHA-256 hash (excludes rate_limit for stability) |

**Cache Key**: `board:{project_id}` with 300-second TTL
**Sub-Issue Cache Key**: `sub_issues:{owner}/{repo}#{issue_number}` with 600-second TTL

**Validation Rules**:
- `data_hash` excludes `rate_limit` field to prevent cache churn from rate-limit counter changes
- Manual refresh (`refresh=true`) bypasses cache read but populates cache for subsequent requests
- Manual refresh deletes all associated sub-issue cache entries before fetching fresh data

### RefreshSource (Frontend Concept)

**Location**: Distributed across `useRealTimeSync.ts`, `useBoardRefresh.ts`, `useProjectBoard.ts`
**Role**: Logical classification of what triggered a data refresh.

| Source | Query Invalidated | Cache Bypass | Debounce Window |
|--------|-------------------|-------------|-----------------|
| WebSocket task_update | `['projects', pid, 'tasks']` | No | 2s (reconnect) |
| WebSocket refresh | `['projects', pid, 'tasks']` | No | 2s (reconnect) |
| Fallback polling | `['projects', pid, 'tasks']` | No | 30s interval |
| Auto-refresh timer | `['board', 'data', pid]` | No | 2s (board reload) |
| Manual refresh | `['board', 'data', pid]` via setQueryData | Yes (`refresh=true`) | Cancels pending |

**State Transitions** (board refresh lifecycle):
```text
[Idle] → WebSocket connected → [RealTime]
[RealTime] → connection lost → [FallbackPolling]
[FallbackPolling] → connection restored → [RealTime]
[RealTime|FallbackPolling] → 5min elapsed → [AutoRefresh] → completes → [RealTime|FallbackPolling]
[Any] → manual button click → [ManualRefresh] → completes → [previous state]
[Any] → tab hidden → [Paused]
[Paused] → tab visible + stale check → [AutoRefresh] or [Idle]
```

### AdaptivePollingTier (Frontend Concept)

**Location**: `useProjectBoard.ts` via `useAdaptivePolling()`
**Role**: Dynamic refetch interval adjustment based on detected board activity.

| Tier | Condition | Behavior |
|------|-----------|----------|
| Active | Recent changes detected | Shortest refetch interval |
| Normal | No recent changes | Default refetch interval |
| Idle | Extended period without changes | Longest refetch interval |

**Change Detection Hash**: `JSON.stringify(result.columns.map(c => c.item_count))`
- Lightweight comparison using only column item counts
- Avoids deep comparison of full board data
- Reports `pollSuccess()` on hash change, `pollFailure()` on hash match

### StaleRevalidation (Backend Concept)

**Location**: `solune/backend/src/api/projects.py` (WebSocket subscription loop)
**Role**: Counter-based mechanism to force periodic fresh fetches during sustained stale cache reads.

| Field | Type | Description |
|-------|------|-------------|
| stale_revalidation_count | int | Consecutive stale cache reads without fresh fetch |
| STALE_REVALIDATION_LIMIT | int (10) | Threshold to force fresh fetch |

**State Transitions**:
```text
[0] → stale read → [1] → stale read → [2] → ... → [10] → force fresh fetch → [0]
[N] → fresh fetch with changes → [0]  (reset on detected change)
```

**Performance Impact**: At 30-second refresh intervals, the counter reaches 10 after ~5 minutes, producing one forced API call per 5 minutes on a truly idle board.

## Relationships

```text
BoardData ──contains──▶ Column[] ──contains──▶ BoardItem[]
BoardItem ──cached-as──▶ CacheEntry[BoardData] (board:{project_id}, TTL=300s)
BoardItem ──has-sub-issues──▶ CacheEntry[SubIssue[]] (sub_issues:{owner}/{repo}#{number}, TTL=600s)

RefreshSource ──triggers──▶ Query Invalidation ──refetches──▶ CacheEntry (via backend API)
AdaptivePollingTier ──controls──▶ refetchInterval ──governs──▶ Board Query polling rate
StaleRevalidation ──gates──▶ fresh fetch ──updates──▶ CacheEntry + WebSocket client
```

## Performance-Critical Invariants

1. **Cache hash stability**: `data_hash` MUST exclude volatile fields (rate_limit) to prevent false cache invalidation.
2. **Sub-issue cache independence**: Sub-issue entries (600s TTL) MUST be independently invalidated from board data (300s TTL); only manual refresh triggers explicit sub-issue cache deletion.
3. **Refresh source isolation**: Task-level WebSocket updates MUST NOT trigger board data query invalidation; board refreshes are exclusively managed by auto-refresh timer or manual refresh.
4. **Debounce coverage**: All refresh paths that can overlap (auto-refresh + WebSocket reconnection, manual + auto-refresh) MUST pass through the 2-second board reload debounce window.
5. **Stale fallback safety**: `get_stale()` MUST return expired data rather than empty/null to maintain UI continuity during API failures.
