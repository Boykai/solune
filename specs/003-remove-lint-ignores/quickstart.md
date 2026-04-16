# Quickstart: Remove Lint/Test Ignores & Fix Discovered Bugs

**Feature**: `003-remove-lint-ignores` | **Date**: 2026-04-16

## Prerequisites

- Python 3.13+ with `uv` installed
- Node.js 22+ with npm
- Azure Bicep CLI (`az bicep`)
- Repository cloned and on the feature branch

## Verification Commands

### Phase 0 — Capture Baseline

```bash
# Backend baseline
cd solune/backend
uv sync --locked --extra dev
uv run ruff check src tests
uv run ruff format --check src tests
uv run bandit -r src/ -ll -ii --skip B104,B608
uv run pyright src
uv run pyright -p pyrightconfig.tests.json
uv run pytest --cov=src --cov-report=term-missing --durations=20 \
  --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency

# Frontend baseline
cd ../frontend
npm ci
npm run lint
npm run type-check
npm run type-check:test
npm run test:coverage
npm run build

# E2E baseline (requires running app)
npx playwright test

# Infrastructure baseline
cd ../../infra
az bicep build --file main.bicep
```

### Phase 1 — Backend Verification

After backend changes, run all checks at stricter settings:

```bash
cd solune/backend

# Lint (no E501 ignore, no B608 skip)
uv run ruff check src tests
uv run ruff format --check src tests

# Security scan (no B608 skip — this is the key change)
uv run bandit -r src/ -ll -ii --skip B104

# Type check (reportMissingImports = error)
uv run pyright src
uv run pyright -p pyrightconfig.tests.json

# Tests with coverage
uv run pytest --cov=src --cov-report=term-missing --durations=20 \
  --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency
```

### Phase 2 — Frontend Verification

After frontend changes, run all checks at stricter settings:

```bash
cd solune/frontend

# Lint with zero warnings
npm run lint -- --max-warnings=0

# Type check (including test config with noUnusedLocals/Parameters)
npm run type-check
npm run type-check:test

# Tests with coverage
npm run test:coverage

# Build
npm run build

# Mutation testing with ignoreStatic=false
npm run test:mutation
```

### Phase 3 — E2E Verification

After E2E changes:

```bash
cd solune/frontend
npx playwright test
```

### Phase 4 — Infrastructure Verification

After Bicep changes:

```bash
cd infra
az bicep build --file main.bicep
```

### Phase 5 — Suppression Guard Verification

After adding the CI guard:

```bash
# Test that the guard catches unjustified suppressions
# (create a test file with an unjustified suppression and verify the guard fails)
cd solune
./scripts/check-suppressions.sh --changed-files <test-file>
```

### Full Regression

Run all checks end-to-end to confirm no regressions:

```bash
# Backend
cd solune/backend
uv run ruff check src tests && \
uv run ruff format --check src tests && \
uv run bandit -r src/ -ll -ii --skip B104 && \
uv run pyright src && \
uv run pytest --cov=src --cov-report=term-missing \
  --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency

# Frontend
cd ../frontend
npm run lint -- --max-warnings=0 && \
npm run type-check && \
npm run type-check:test && \
npm run test:coverage && \
npm run build
```

## Key Files to Monitor

| Area | Key Files |
|------|-----------|
| Backend config | `solune/backend/pyproject.toml`, `solune/backend/pyrightconfig.tests.json` |
| Backend services | `solune/backend/src/api/chat.py`, `solune/backend/src/services/agent_provider.py`, `solune/backend/src/services/plan_agent_provider.py` |
| Backend tests | `solune/backend/tests/unit/test_run_mutmut_shard.py`, `solune/backend/tests/unit/test_mcp_server/test_context.py` |
| Frontend hooks | `solune/frontend/src/hooks/useChatPanels.ts`, `solune/frontend/src/hooks/useRealTimeSync.ts`, `solune/frontend/src/hooks/useVoiceInput.ts` |
| Frontend components | `solune/frontend/src/components/chat/ChatInterface.tsx`, `solune/frontend/src/components/agents/AgentChatFlow.tsx`, `solune/frontend/src/components/chores/ChoreChatFlow.tsx` |
| Frontend config | `solune/frontend/eslint.config.js`, `solune/frontend/stryker.config.mjs`, `solune/frontend/tsconfig.test.json` |
| E2E tests | `solune/frontend/e2e/integration.spec.ts`, `solune/frontend/e2e/project-load-performance.spec.ts`, `solune/frontend/e2e/fixtures.ts` |
| Infrastructure | `infra/modules/monitoring.bicep`, `infra/modules/openai.bicep`, `infra/modules/storage.bicep` |
| CI guard | `solune/scripts/check-suppressions.sh` (new), `.github/workflows/ci.yml` |
