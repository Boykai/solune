# Frontend Baseline Measurement Procedure

**Feature**: Performance Review (002)
**Date**: 2026-03-31

## Measurement: Board Responsiveness (SC-002, SC-005)

### Setup
1. Open a board with ≥5 columns, ≥50 tasks
2. Use Chrome DevTools Performance panel
3. Clear network log, enable "Preserve log"

### Procedure — Board Load
1. Record time-to-interactive from navigation to board fully rendered
2. Count React component renders via React DevTools Profiler
3. Note initial query count (board data + projects list + tasks)

### Procedure — Interaction
1. Drag a card between columns, measure frame rate via Performance panel
2. Open a card detail popover, measure render time
3. Scroll through a long column, measure frame rate
4. Toggle chat popup resize, measure frame rate

### Metrics
| Metric | Baseline | After | Target |
|--------|----------|-------|--------|
| Board time-to-interactive | — | — | ≤80% of baseline |
| Initial render component count | — | — | Stable |
| Frame rate during drag | — | — | ≥60fps |
| Frame rate during scroll | — | — | ≥60fps |
| Rerenders per interaction | — | — | ≤baseline |
| Query invalidations per WS message | — | — | 1 (tasks only) |

### Key Code Paths
- `useProjectBoard.ts` line 91: Board data query with adaptive polling
- `useRealTimeSync.ts` lines 67, 77, 89: Query invalidations (tasks only)
- `useBoardRefresh.ts` line 119: Auto-refresh invalidation (board data)
- `BoardColumn.tsx` line 30: `memo()` wrapper
- `IssueCard.tsx` line 110: `memo()` wrapper
- `ProjectsPage.tsx`: `useMemo` for heroStats, rateLimitState, syncStatusLabel

### Baseline Observations
- WebSocket messages only invalidate `['projects', projectId, 'tasks']` — never board data
- Board data refreshes only via auto-refresh (5 min) or manual refresh button
- BoardColumn and IssueCard already use `React.memo`
- ChatPopup uses RAF-gated resize with lifecycle-scoped listeners
- AddAgentPopover uses Radix Popover (no custom positioning listeners)
