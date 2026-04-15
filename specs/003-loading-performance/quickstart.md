# Quickstart: Loading Performance

**Feature**: Loading Performance | **Date**: 2026-04-15

Status note: this quickstart captures the scoped implementation and validation path for the loading-performance work on this branch.

## Prerequisites

- Python/`uv` environment for `/home/runner/work/solune/solune/solune/backend`
- Node.js/npm environment for `/home/runner/work/solune/solune/solune/frontend`
- Optional authenticated test credentials for performance/E2E checks

## Setup

```bash
cd /home/runner/work/solune/solune
```

## Implementation Sequence

### Step 1: Refactor the backend board hot path

Focus files:

- `/home/runner/work/solune/solune/solune/backend/src/services/github_projects/board.py`
- `/home/runner/work/solune/solune/solune/backend/src/api/board.py`
- `/home/runner/work/solune/solune/solune/backend/src/models/board.py`
- `/home/runner/work/solune/solune/solune/backend/src/services/github_projects/issues.py`

Goals:

1. Separate interactive board assembly from deferred Done/history backfill and reconciliation.
2. Skip Done/closed parent sub-issue fetches during the initial load.
3. Continue using existing Done-item persistence and sub-issue cache data for pill rendering.
4. Keep manual refresh as the path that forces a full-fidelity reload.

### Step 2: Add selection warm-up and request deduplication

Focus files:

- `/home/runner/work/solune/solune/solune/backend/src/api/projects.py`
- `/home/runner/work/solune/solune/solune/backend/src/services/cache.py`
- `/home/runner/work/solune/solune/solune/backend/src/services/github_projects/service.py`
- `/home/runner/work/solune/solune/solune/backend/src/services/copilot_polling/polling_loop.py`

Goals:

1. Start a best-effort board warm-up task from `POST /projects/{id}/select`.
2. Ensure concurrent list/board/warm-up requests share in-flight results where needed.
3. Cancel or supersede stale work when users switch projects quickly.
4. Preserve deferred Copilot polling behavior.

### Step 3: Expose progressive-load state to the frontend

Focus files:

- `/home/runner/work/solune/solune/solune/frontend/src/services/api.ts`
- `/home/runner/work/solune/solune/solune/frontend/src/hooks/useProjectBoard.ts`
- `/home/runner/work/solune/solune/solune/frontend/src/hooks/useProjects.ts`
- `/home/runner/work/solune/solune/solune/frontend/src/pages/ProjectsPage.tsx`
- Existing board-loading components under `/home/runner/work/solune/solune/solune/frontend/src/components/board/`

Goals:

1. Parse any added board-load metadata.
2. Render active columns as soon as they are ready.
3. Show a subtle Done/history progress indicator instead of blocking the whole page.
4. Keep manual refresh and stale/error banners working.

## Validation Commands

### Markdown artifacts

```bash
cd /home/runner/work/solune/solune
npx --yes markdownlint-cli \
  plan.md research.md data-model.md quickstart.md \
  specs/003-loading-performance/plan.md \
  specs/003-loading-performance/research.md \
  specs/003-loading-performance/data-model.md \
  specs/003-loading-performance/quickstart.md \
  --config solune/.markdownlint.json
```

### Backend targeted tests

```bash
cd /home/runner/work/solune/solune/solune/backend
uv run --with pytest --with pytest-asyncio pytest \
  tests/unit/test_api_board.py \
  tests/unit/test_api_projects.py \
  tests/unit/test_board.py \
  tests/unit/test_github_projects.py -q
```

### Backend performance check (optional, authenticated)

```bash
cd /home/runner/work/solune/solune/solune/backend
PERF_GITHUB_TOKEN=... PERF_PROJECT_ID=... \
uv run --with pytest pytest tests/performance/test_board_load_time.py -m performance -q
```

### Frontend targeted validation

```bash
cd /home/runner/work/solune/solune/solune/frontend
npm run test -- --reporter=verbose --run \
  src/hooks/useProjects.test.tsx \
  src/hooks/useProjectBoard.test.tsx \
  src/pages/ProjectsPage.test.tsx
npm run type-check
npm run lint
npm run build
```

### Playwright timing check (optional, authenticated)

```bash
cd /home/runner/work/solune/solune/solune/frontend
E2E_PROJECT_ID=... npx playwright test e2e/project-load-performance.spec.ts --headed
```

## Manual Verification Checklist

1. Log in and open `/projects`.
2. Select a project and confirm the board becomes interactive before Done/history work is fully complete.
3. Confirm active columns are usable while any Done-progress indicator remains subtle and non-blocking.
4. Trigger manual refresh and confirm the board performs the full-fidelity refresh path.
5. Rapidly switch between two projects and confirm stale warm-up/background work does not overwrite the active board.
6. If a cached Done fallback is used, confirm the Done column still shows parent cards and GitHub-linked sub-issue pills.

## Key Files Reference

| File | Purpose |
|------|---------|
| `/home/runner/work/solune/solune/solune/backend/src/services/github_projects/board.py` | Core board load staging, sub-issue policy, reconciliation split |
| `/home/runner/work/solune/solune/solune/backend/src/api/board.py` | Board API contract and refresh semantics |
| `/home/runner/work/solune/solune/solune/backend/src/api/projects.py` | Project selection, warm-up scheduling, delayed polling |
| `/home/runner/work/solune/solune/solune/frontend/src/hooks/useProjectBoard.ts` | Frontend board query behavior |
| `/home/runner/work/solune/solune/solune/frontend/src/pages/ProjectsPage.tsx` | Loading UX and progress indicators |
| `/home/runner/work/solune/solune/solune/frontend/e2e/project-load-performance.spec.ts` | Existing timing regression check |
