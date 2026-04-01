# Backend Baseline Measurement Procedure

**Feature**: Performance Review (002)
**Date**: 2026-03-31

## Measurement: Idle API Request Count (SC-001)

### Setup
1. Open a board with ≥5 columns, ≥50 tasks
2. Ensure WebSocket connection is active (sync status: "connected")
3. No manual interactions during measurement window

### Procedure
1. Record start timestamp
2. Monitor outgoing GitHub API requests for 5 minutes via backend logs (`logger.debug` in `projects.py`)
3. Count:
   - Total GitHub GraphQL API calls
   - Total REST API calls
   - Stale-revalidation forced fetches
   - Cache hits (no API call)
4. Record end timestamp

### Metrics
| Metric | Baseline | After | Target |
|--------|----------|-------|--------|
| Total API requests (5 min) | — | — | ≤50% of baseline |
| Requests per minute | — | — | ≤50% of baseline |
| Stale revalidation fetches | — | — | ≤1 per 5 min |
| Cache hit rate | — | — | ≥80% |

### Key Code Paths
- `projects.py` line 360: `STALE_REVALIDATION_LIMIT` controls forced fresh fetch frequency
- `projects.py` lines 378-407: Stale-revalidation counter and cache bypass logic
- `cache.py` line 124: `refresh_ttl()` extends TTL without API call
- `board.py` line 456: Board cache with 300s TTL and data hash

### Baseline Observations
- STALE_REVALIDATION_LIMIT = 10 → at 30s refresh interval, forces 1 API call per ~5 minutes
- Board cache TTL = 300s aligns with frontend 5-minute auto-refresh
- Sub-issue cache TTL = 600s (10 minutes) covers 2 board refresh cycles
- WebSocket change detection via `compute_data_hash()` suppresses unchanged refreshes
