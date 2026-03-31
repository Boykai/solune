# Regression Checklist

**Feature**: Performance Review (002)
**Date**: 2026-03-31

## Mapping: Existing Tests → Optimization Targets

| Test File | Existing Test | Guards Against | SC Target |
|-----------|--------------|----------------|-----------|
| test_cache.py | `test_refresh_ttl_updates_expiry` | TTL refresh without re-store | SC-001 |
| test_cache.py | `test_data_hash_stored_and_retrievable` | Hash-based change detection | SC-001 |
| test_cache.py | `test_cached_fetch_hash_match_refreshes_ttl` | Hash match avoids re-cache | SC-001 |
| test_cache.py | `test_stale_returned_on_rate_limit` | Graceful degradation | SC-001 |
| test_api_board.py | `test_warm_cache_prevents_api_calls` | Cache reuse on board fetch | SC-001 |
| test_api_board.py | `test_manual_refresh_clears_sub_issue_caches` | Manual refresh bypasses cache | SC-003 |
| test_api_board.py | `test_board_data_hash_excludes_rate_limit` | Hash stability | SC-001 |
| test_copilot_polling.py | `test_warm_cache_prevents_redundant_api_calls` | Polling cache reuse | SC-001 |
| test_copilot_polling.py | `test_unchanged_items_hash_preserves_existing_board_cache_entry` | Hash-based dedup | SC-001 |
| useRealTimeSync.test.tsx | `invalidates only tasks query` | Task-only invalidation | SC-003 |
| useRealTimeSync.test.tsx | `does not invalidate board data` | Board data protection | SC-003 |
| useRealTimeSync.test.tsx | `debounces reconnection invalidations` | Reconnect safety | SC-004 |
| useBoardRefresh.test.tsx | `manual refresh bypasses server cache` | Manual refresh bypass | SC-003 |
| useBoardRefresh.test.tsx | `requestBoardReload is debounced` | Deduplication | SC-004 |
| useBoardRefresh.test.tsx | `auto-refresh timer suppressed when WS connected` | Timer suppression | SC-001 |

## New Tests Added (This Feature)

| Test File | New Test | Guards Against | SC Target |
|-----------|----------|----------------|-----------|
| test_api_board.py | `test_stale_revalidation_idle_board` | Idle API over-fetching | SC-001 |
| test_api_board.py | `test_sub_issue_warm_cache_skips_api` | Sub-issue cache waste | SC-001 |
| test_copilot_polling.py | `test_polling_no_board_cache_invalidation` | Polling triggering board refresh | SC-004 |
| useRealTimeSync.test.tsx | `reconnection does not invalidate board data` | Reconnect board data safety | SC-003 |
| useRealTimeSync.test.tsx | `message type routing correctness` | Correct message handling | SC-003 |
| useBoardRefresh.test.tsx | `auto-refresh timer reset on manual refresh` | Timer management | SC-004 |
| useBoardRefresh.test.tsx | `overlapping refresh sources deduplicated` | Deduplication correctness | SC-004 |

## Verification Checklist

- [ ] All existing backend tests pass (417 tests)
- [ ] All existing frontend tests pass (76 tests)
- [ ] New backend tests pass
- [ ] New frontend tests pass
- [ ] Backend lint clean (ruff check + format)
- [ ] Frontend lint clean (eslint + tsc)
- [ ] Frontend build succeeds
