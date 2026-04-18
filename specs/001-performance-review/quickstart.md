# Quick Start: Performance Review

**Feature Branch**: `001-performance-review`
**Date**: 2026-04-18

## Prerequisites

- Python ≥3.12 with `uv` package manager
- Node.js (for frontend) with `npm`
- Repository cloned and on the `001-performance-review` branch

## Backend Setup

```bash
cd solune/backend

# Install dependencies (including dev tools: ruff, pyright, pytest)
uv pip install -e ".[dev]"

# Verify setup — run targeted tests
uv run pytest tests/unit/test_cache.py tests/unit/test_api_board.py -v

# Lint check
uv run ruff check src/

# Type check
uv run pyright src/
```

## Frontend Setup

```bash
cd solune/frontend

# Install dependencies
npm install

# Verify setup — run targeted tests
npx vitest run src/hooks/useRealTimeSync.test.tsx src/hooks/useBoardRefresh.test.tsx

# Lint check
npm run lint

# Type check
npm run type-check

# Build check
npm run build
```

## Implementation Order

### Phase 1 — Baseline and Guardrails (blocks everything)

1. **Backend baseline**: Run existing tests and record current behavior
   - `uv run pytest tests/unit/test_cache.py -v` — cache behavior baseline
   - `uv run pytest tests/unit/test_api_board.py -v` — board endpoint baseline
   - `uv run pytest tests/unit/test_copilot_polling.py -v` — polling baseline

2. **Frontend baseline**: Run existing tests and record current behavior
   - `npx vitest run src/hooks/useRealTimeSync.test.tsx` — WS/polling baseline
   - `npx vitest run src/hooks/useBoardRefresh.test.tsx` — refresh behavior baseline

3. **Confirm current state**: Verify hash-based change detection, board cache TTL (300s), and sub-issue cache invalidation are fully functional (see research.md RT-001)

### Phase 2 — Backend API Consumption Fixes

Target files:
- `backend/src/api/board.py` — sub-issue cache reuse validation
- `backend/src/api/projects.py` — WebSocket refresh signal semantics
- `backend/src/services/copilot_polling/polling_loop.py` — idle polling refinement

Key changes:
- Validate that idle board viewing with unchanged data produces zero redundant GitHub API calls
- Ensure warm sub-issue caches are reused during auto-refresh (not cleared)
- Confirm polling fallback does not trigger expensive board refreshes

### Phase 2 — Frontend Refresh Path Fixes (parallel with backend)

Target files:
- `frontend/src/hooks/useRealTimeSync.ts` — ensure polling fallback uses `onRefreshTriggered` callback
- `frontend/src/hooks/useBoardRefresh.ts` — validate debounce and deduplication
- `frontend/src/hooks/useProjectBoard.ts` — validate adaptive polling change detection

Key changes:
- Ensure polling fallback goes through `requestBoardReload()` for debouncing
- Verify WebSocket messages do not trigger full board data query invalidation
- Confirm auto-refresh suppression during active WebSocket connection

### Phase 3 — Frontend Render Optimization

Target files:
- `frontend/src/pages/ProjectsPage.tsx` — stabilize callback props with `useCallback`
- `frontend/src/components/board/BoardColumn.tsx` — verify memo effectiveness
- `frontend/src/components/board/IssueCard.tsx` — verify memo effectiveness
- `frontend/src/components/board/AddAgentPopover.tsx` — consider `memo()` wrapper
- `frontend/src/components/chat/ChatPopup.tsx` — verify RAF-gating

Key changes:
- Wrap event handler callbacks in `useCallback` where they are passed to memoized children
- Memoize expensive derived data that is recomputed unnecessarily
- Throttle high-frequency event listeners (drag, positioning) where not already handled

### Phase 3 — Verification and Regression Coverage (parallel with render)

Target files:
- `backend/tests/unit/test_cache.py` — extend with idle-behavior tests
- `backend/tests/unit/test_api_board.py` — extend with sub-issue reuse tests
- `frontend/src/hooks/useRealTimeSync.test.tsx` — extend with polling-fallback tests
- `frontend/src/hooks/useBoardRefresh.test.tsx` — extend with deduplication edge cases

## Verification Commands

```bash
# Backend — full targeted test suite
cd solune/backend
uv run pytest tests/unit/test_cache.py tests/unit/test_api_board.py tests/unit/test_copilot_polling.py -v

# Backend — lint + type check
uv run ruff check src/
uv run pyright src/

# Frontend — full targeted test suite
cd solune/frontend
npx vitest run src/hooks/useRealTimeSync.test.tsx src/hooks/useBoardRefresh.test.tsx

# Frontend — lint + type check + build
npm run lint
npm run type-check
npm run build
```

## Key Design Decisions

1. **No new dependencies**: All optimizations use existing React hooks and Python stdlib
2. **No architectural changes**: Three-hook frontend pattern preserved; backend cache layer unchanged
3. **Baseline-first**: All optimization work blocked until Phase 1 baselines are captured
4. **Low-risk only**: Memoization, throttling, cache reuse, debouncing — no virtualization or service decomposition
5. **Preserve manual refresh**: `refresh=true` always bypasses caches and clears sub-issues

## Reference Documents

- [spec.md](spec.md) — Feature specification with user stories and acceptance criteria
- [plan.md](plan.md) — Implementation plan with technical context
- [research.md](research.md) — Research findings for all technical decisions
- [data-model.md](data-model.md) — Key entities and state transitions
- [contracts/refresh-policy.md](contracts/refresh-policy.md) — Board refresh behavioral contract
