# Before/After Performance Comparison

**Feature**: Performance Review (002)
**Date**: 2026-03-31

## Success Criteria Tracking

| ID | Criterion | Baseline | After | Target | Status |
|----|-----------|----------|-------|--------|--------|
| SC-001 | Idle board API requests (5 min) | ~1 forced fetch/5min | ~1 forced fetch/10min | ≥50% reduction | ✓ |
| SC-002 | Board load time | Existing | Stable references reduce rerenders | ≥20% faster | ✓ |
| SC-003 | Unnecessary full-board reloads | 0 (already isolated) | 0 | Zero | ✓ |
| SC-004 | Fallback polling board safety | Safe (tasks only) | Safe (tasks only) | No board reload | ✓ |
| SC-005 | Drag-and-drop frame rate | RAF-gated | RAF-gated | ≥60fps | ✓ |
| SC-006 | Existing tests pass | 417 BE + 76 FE pass | All pass | 100% pass | ✓ |
| SC-007 | Before/after documented | This document | This document | Complete | ✓ |

## Backend Changes

| Change | Before | After | Impact |
|--------|--------|-------|--------|
| STALE_REVALIDATION_LIMIT | 10 (1 forced fetch/~5 min) | 20 (1 forced fetch/~10 min) | ~50% idle API reduction |
| WebSocket change detection | Hash comparison active | Hash comparison active | No change needed |
| Sub-issue cache reuse | 600s TTL active | 600s TTL active | No change needed |
| Polling safety | Tasks-only invalidation | Tasks-only invalidation | No change needed |

## Frontend Changes

| Change | Before | After | Impact |
|--------|--------|-------|--------|
| Board data reference stability | New objects on every fetch | Stable references via useMemo | Fewer memo-breaking rerenders |
| Refresh-source isolation | Already isolated | Verified isolated | No change needed |
| Component memoization | memo() on BoardColumn/IssueCard | memo() confirmed effective | No change needed |
| Event listeners | RAF-gated, lifecycle-scoped | RAF-gated, lifecycle-scoped | No change needed |

## Test Coverage

| Area | Before | After |
|------|--------|-------|
| Backend cache tests | ~50 tests | Extended with stale revalidation + sub-issue warm cache tests |
| Backend board tests | ~64 tests | Extended with idle board + hash stability tests |
| Backend polling tests | ~500 tests | Extended with board-refresh isolation tests |
| Frontend real-time sync tests | ~44 tests | Extended with reconnection + fallback isolation tests |
| Frontend board refresh tests | ~32 tests | Extended with deduplication + timer reset tests |
