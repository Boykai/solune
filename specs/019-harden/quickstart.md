# Quickstart: #Harden

**Feature**: Harden Solune reliability, code quality, CI/CD, observability, DX
**Date**: 2026-04-10

## Prerequisites

- Python ≥ 3.12 with `uv` package manager
- Node.js (LTS) with npm
- Git

## Getting Started

### 1. Clone and Set Up Backend

```bash
cd solune/backend
uv sync --dev
source .venv/bin/activate
```

### 2. Clone and Set Up Frontend

```bash
cd solune/frontend
npm install
```

### 3. Run Backend Tests

```bash
cd solune/backend
python -m pytest tests/ --cov=src --cov-fail-under=75 -q
```

### 4. Run Frontend Tests

```bash
cd solune/frontend
npm run test
```

### 5. Run Frontend E2E Tests

```bash
cd solune/frontend
npx playwright test
```

### 6. Run Stryker Mutation Tests

```bash
cd solune/frontend
npx stryker run
```

### 7. Run Linting

```bash
# Backend
cd solune/backend
ruff check src/ tests/ && ruff format --check src/ tests/

# Frontend
cd solune/frontend
npm run lint && npm run type-check
```

## Phase-Specific Workflows

### Phase 1: Bug Fixes

Only one bug remains to fix (1.3 — agent preview validation). The other bugs
(1.1 memory leak, 1.2 lifecycle status, 3.4 plan-mode messages) have been
resolved in prior work.

**Verify bug 1.3 fix**:

```bash
cd solune/backend
python -m pytest tests/unit/test_agents_service.py -k "extract_agent_preview" -v
```

### Phase 2: Test Coverage

**Check current backend coverage**:

```bash
cd solune/backend
python -m pytest tests/ --cov=src --cov-report=term-missing -q
```

**Check current frontend coverage**:

```bash
cd solune/frontend
npx vitest run --coverage
```

### Phase 3: Code Quality

**Run type checking**:

```bash
# Backend
cd solune/backend
pyright src/

# Frontend
cd solune/frontend
npm run type-check
```

**Run security scanning**:

```bash
cd solune/backend
bandit -r src/ -c pyproject.toml
```

## CI Pipeline

The CI pipeline has 9 jobs. All blocking jobs must pass for PR merge:

1. Backend (tests + coverage)
2. Backend Advanced Tests (continue-on-error)
3. Frontend (tests + coverage)
4. Frontend E2E (continue-on-error)
5. Docs Lint
6. Diagrams
7. Contract Validation
8. Build Validation
9. Docker Build (needs backend + frontend)
