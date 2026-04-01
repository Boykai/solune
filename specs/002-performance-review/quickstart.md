# Quickstart: Performance Review

**Feature**: 002-performance-review
**Date**: 2026-03-31

## Prerequisites

- Python ≥3.12 with `uv` package manager
- Node.js with `npm`
- Access to a GitHub project board (for manual baseline measurements)

## Setup

### Backend

```bash
cd solune/backend
uv sync --locked --extra dev
```

### Frontend

```bash
cd solune/frontend
npm install
```

## Running Tests

### Backend — Targeted Performance-Related Tests

```bash
cd solune/backend

# Cache behavior (TTL, stale fallback, hash change detection)
uv run pytest tests/unit/test_cache.py -v

# Board endpoint (cache reuse, manual refresh, sub-issue invalidation)
uv run pytest tests/unit/test_api_board.py -v

# Polling behavior (rate-limit budgeting, sub-issue filtering)
uv run pytest tests/unit/test_copilot_polling.py -v
```

### Backend — Full Lint and Type Check

```bash
cd solune/backend

# Linting
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests

# Type checking
uv run pyright src
```

### Frontend — Targeted Performance-Related Tests

```bash
cd solune/frontend

# Real-time sync (WebSocket lifecycle, fallback polling, invalidation)
npx vitest run src/hooks/useRealTimeSync.test.tsx

# Board refresh (timer dedup, manual refresh, visibility API)
npx vitest run src/hooks/useBoardRefresh.test.tsx
```

### Frontend — Full Lint, Type Check, and Build

```bash
cd solune/frontend

# Linting
npx eslint src/

# Type checking
npx tsc --noEmit

# Build check
npm run build
```

## Baseline Measurement Procedure

### Backend Baseline (FR-001)

1. Start the backend server locally
2. Open a project board in the browser
3. Leave the board idle for 10 minutes
4. Count outgoing requests to the GitHub API during the 10-minute idle period
5. Record: total requests, requests per minute, request types (GraphQL vs REST)
6. Note the stale-revalidation cycle count (expected: ~1 forced fetch per 10 minutes with 30s refresh and `STALE_REVALIDATION_LIMIT = 20`)

### Frontend Baseline (FR-002)

1. Open browser DevTools → Performance tab
2. Load a representative board (5+ columns, 50+ tasks)
3. Record: time-to-interactive, initial render component count
4. Perform interactions: scroll columns, drag a task, open a popover
5. Record: frame rate during drag, rerender count per interaction
6. Check Network tab: count query invalidations per WebSocket message type

### Before/After Comparison (FR-003, SC-007)

After optimization changes are applied, repeat both procedures above and compare:

| Metric | Baseline | After | Target |
|--------|----------|-------|--------|
| Idle API calls / 5min | (measure) | (measure) | ≤50% of baseline |
| Board load time | (measure) | (measure) | ≥20% faster |
| Full board reloads per task update | (measure) | (measure) | 0 |
| Fallback polling board reloads (no changes) | (measure) | (measure) | 0 |

## Key Files to Modify

### Backend (Phase 2)

| File | What to Change |
|------|---------------|
| `src/api/projects.py` | Tune stale-revalidation behavior; verify change detection is fully wired |
| `src/api/board.py` | Verify sub-issue cache reuse on warm reads |
| `src/services/cache.py` | No changes expected (fully implemented) |
| `tests/unit/test_cache.py` | Extend coverage for idle-board scenarios |
| `tests/unit/test_api_board.py` | Extend coverage for sub-issue cache hit paths |

### Frontend (Phase 2–3)

| File | What to Change |
|------|---------------|
| `src/hooks/useRealTimeSync.ts` | Verify task-only invalidation; no board data invalidation on fallback |
| `src/hooks/useBoardRefresh.ts` | Verify debounce and timer reset behavior |
| `src/hooks/useProjectBoard.ts` | Verify adaptive polling tiers; stabilize data references |
| `src/components/board/BoardColumn.tsx` | Verify memo effectiveness; check items reference stability |
| `src/components/board/IssueCard.tsx` | Verify memo effectiveness; check prop reference stability |
| `src/pages/ProjectsPage.tsx` | Verify useMemo dependency arrays |
| `src/hooks/useRealTimeSync.test.tsx` | Extend coverage for refresh-source isolation |
| `src/hooks/useBoardRefresh.test.tsx` | Extend coverage for deduplication edge cases |

## Implementation Order

```text
Phase 1: Baseline capture (FR-001 through FR-004)
    ↓ blocks all optimization work
Phase 2a: Backend API fixes (FR-005 through FR-008)  ──┐
Phase 2b: Frontend refresh fixes (FR-009 through FR-012) ──┤ parallel
    ↓                                                      │
Phase 3a: Frontend render optimization (FR-013 through FR-015) ◄──┘
Phase 3b: Verification and regression coverage (FR-016 through FR-018)
    ↓
Phase 4: Optional second-wave (only if measurements justify)
```
