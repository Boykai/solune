# Quickstart: Fix Mutation Testing Infrastructure

**Feature**: 005-fix-mutation-tests
**Date**: 2026-04-02

## Prerequisites

- Python ≥3.12 with `uv` package manager
- Node.js 22 with npm
- Git

## Backend Mutation Testing

### Verify the workspace parity fix

After adding `templates/` to `pyproject.toml` `[tool.mutmut].also_copy`:

```bash
cd solune/backend

# 1. Confirm app-template tests pass normally
uv run pytest tests/unit/test_agent_tools.py -v -k "template"

# 2. Run a single mutmut shard to verify templates are copied
uv run python scripts/run_mutmut_shard.py --shard app-and-data --max-children 1

# 3. Check the report for real kills/survivors (not "not checked")
uv run python -m mutmut results
```

### Run all backend shards locally

```bash
cd solune/backend

# Available shards (all 5):
for shard in auth-and-projects orchestration app-and-data agents-and-integrations api-and-middleware; do
  echo "=== Running shard: $shard ==="
  uv run python scripts/run_mutmut_shard.py --shard "$shard" --max-children 1
  uv run python -m mutmut results > "mutmut-report-$shard.txt" 2>&1
done
```

### Dry-run a shard (see which paths it covers)

```bash
cd solune/backend
uv run python scripts/run_mutmut_shard.py --shard api-and-middleware --dry-run
```

## Frontend Mutation Testing

### Run a focused shard locally

After frontend shard configs are created:

```bash
cd solune/frontend

# Board/polling hooks shard
npm run test:mutate:hooks-board

# Data/query hooks shard
npm run test:mutate:hooks-data

# General hooks shard
npm run test:mutate:hooks-general

# Lib/utils shard
npm run test:mutate:lib

# Full run (all shards combined, original behavior)
npm run test:mutate
```

### Run Stryker with a specific config directly

```bash
cd solune/frontend
npx stryker run -c stryker-hooks-board.config.mjs
```

### Focused single-file mutation (for debugging survivors)

```bash
cd solune/frontend
npx stryker run --mutate src/hooks/useAdaptivePolling.ts --reporters clear-text
```

## CI Verification

### Backend

1. Push changes and trigger the mutation-testing workflow (or dispatch manually)
2. Confirm **5 backend shard jobs** appear: `auth-and-projects`, `orchestration`, `app-and-data`, `agents-and-integrations`, `api-and-middleware`
3. Each job should upload a `backend-mutation-report-<shard>.txt` artifact
4. Check that reports contain real kills/survivors, not "not checked" noise

### Frontend

1. Confirm **4 frontend shard jobs** appear: `hooks-board`, `hooks-data`, `hooks-general`, `lib`
2. Each job should upload a `frontend-mutation-report-<shard>` artifact
3. Each job should complete well under the 3-hour timeout

## Regression Testing

```bash
# Backend: run touched test files
cd solune/backend
uv run pytest tests/unit/test_agent_tools.py tests/unit/test_template_files.py -v

# Frontend: run unit tests + type check
cd solune/frontend
npm test
npm run type-check
npm run type-check:test

# Full lint gates
cd solune/backend
uv run ruff check src tests
uv run ruff format --check src tests
uv run pyright src

cd solune/frontend
npm run lint
```
