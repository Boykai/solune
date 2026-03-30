# Quick Start: 100% Test Coverage with Bug Fixes

**Feature**: `001-full-test-coverage` | **Date**: 2026-03-30

## Prerequisites

- Python ≥3.12 with `uv` package manager
- Node.js 20 with npm
- Git
- Repository cloned at `solune/`

## Setup

```bash
# Backend dependencies
cd solune/backend
uv sync --locked --extra dev

# Frontend dependencies
cd ../frontend
npm ci
```

## Running Tests

### Backend

```bash
cd solune/backend

# Full test suite (CI-equivalent, excludes advanced test categories)
uv run pytest --cov=src --cov-branch --cov-report=term-missing \
  --ignore=tests/property --ignore=tests/fuzz \
  --ignore=tests/chaos --ignore=tests/concurrency

# Quick run (no coverage)
uv run pytest tests/unit/ -q

# Single test file
uv run pytest tests/unit/test_agent_middleware.py -v

# With mutation testing
uv run mutmut run
uv run mutmut results
```

### Frontend

```bash
cd solune/frontend

# Full test suite with coverage
npm run test:coverage

# Quick run (no coverage)
npm run test

# Watch mode (development)
npm run test:watch

# Single test file
npx vitest run src/components/agents/AgentCard.test.tsx

# Accessibility tests
npm run test:a11y

# Mutation testing
npm run test:mutate

# E2E tests (requires browser install)
npx playwright install
npm run test:e2e
```

## Linting & Type Checking

### Backend

```bash
cd solune/backend

# Lint
uv run ruff check src tests

# Format check
uv run ruff format --check src tests

# Type check
uv run pyright src

# Security scan
uv run bandit -r src/ -ll -ii
```

### Frontend

```bash
cd solune/frontend

# Lint
npm run lint

# Type check
npm run type-check

# Build (catches additional errors)
npm run build
```

## Phase-by-Phase Workflow

### Phase 1: Bug Fixes

1. Fix the 4 known bugs (devcontainer tag, exception handling, timeout, validation errors)
2. Run full suites to verify green baseline:
   ```bash
   cd solune/backend && uv run pytest
   cd ../frontend && npm run test
   ```

### Phase 2: Backend Untested Services

1. Create new test files following existing patterns:
   ```bash
   # Use conftest.py fixtures, factories.py for test data
   # Class-based organization, AsyncMock for async services
   ```
2. Verify:
   ```bash
   uv run pytest --cov=src --cov-branch --cov-fail-under=85
   ```

### Phase 3: Backend Branch Blitz

1. Audit coverage gaps:
   ```bash
   uv run pytest --cov=src --cov-branch --cov-report=json
   # Inspect coverage.json for files <90% branch coverage
   ```
2. Add branch tests for every conditional path
3. Verify:
   ```bash
   uv run pytest --cov=src --cov-branch --cov-fail-under=95
   ```

### Phase 4: Frontend Component Sprint (parallel with Phase 3)

1. Create test files for all untested components
2. Each test must include:
   ```typescript
   import { renderWithProviders } from '@/test/test-utils';
   import { axe } from 'jest-axe';
   // ... render + a11y check in every test
   ```
3. Verify:
   ```bash
   npm run test:coverage  # ≥80% all metrics
   npm run test:a11y
   ```

### Phase 5: Frontend Branch & Edge Cases

1. Audit coverage gaps:
   ```bash
   npm run test:coverage  # Inspect coverage-final.json
   ```
2. Add error/loading/empty state tests, negative paths, routing tests
3. Verify:
   ```bash
   npm run test:coverage  # 100% all metrics
   npm run test:mutate    # ≥80% kill rate
   npm run test:e2e
   ```

### Phase 6: Hardening

1. Update configuration thresholds
2. Expand mutation testing scope
3. Refactor singletons to DI
4. Verify:
   ```bash
   cd solune/backend && uv run pytest --cov=src --cov-branch --cov-fail-under=100
   cd ../frontend && npm run test:coverage  # 100% thresholds enforced
   ```

## Key Files Reference

| File | Purpose |
|------|---------|
| `solune/backend/pyproject.toml` | Coverage config, fail_under, mutmut paths |
| `solune/backend/tests/conftest.py` | Shared test fixtures |
| `solune/backend/tests/helpers/factories.py` | Test data factory functions |
| `solune/backend/tests/helpers/assertions.py` | Common assertion helpers |
| `solune/backend/coverage.json` | Per-file backend coverage data |
| `solune/frontend/vitest.config.ts` | Coverage thresholds |
| `solune/frontend/stryker.config.mjs` | Mutation testing scope |
| `solune/frontend/src/test/test-utils.tsx` | Custom render with providers |
| `solune/frontend/src/test/setup.ts` | Vitest setup (polyfills, mocks) |
