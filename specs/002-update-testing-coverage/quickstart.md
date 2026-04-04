# Quickstart: Update Testing Coverage

**Feature**: 002-update-testing-coverage | **Date**: 2026-04-04

## Prerequisites

- Python 3.12+ with `uv` package manager
- Node.js 18+ with `npm`
- Playwright browsers installed (`npx playwright install`)
- Repository cloned and on a working branch

## Quick Commands

### Backend Tests

```bash
# Navigate to backend
cd solune/backend

# Install dependencies
uv sync --locked --extra dev

# Run all unit + integration tests with coverage
uv run pytest --cov=src --cov-report=term-missing --durations=20 \
  --ignore=tests/property --ignore=tests/fuzz \
  --ignore=tests/chaos --ignore=tests/concurrency

# Run a specific test file
uv run pytest tests/unit/test_agent_creator.py -v

# Run tests matching a pattern
uv run pytest -k "test_chat" -v

# Generate HTML coverage report
uv run pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser

# Generate JSON coverage for analysis
uv run pytest --cov=src --cov-report=json

# Run property-based tests
uv run pytest tests/property/ -v

# Run chaos/concurrency tests
uv run pytest tests/chaos/ tests/concurrency/ -v

# Lint
uv run ruff check src tests

# Type check
uv run pyright src
```

### Frontend Tests

```bash
# Navigate to frontend
cd solune/frontend

# Install dependencies
npm ci

# Run all unit tests
npm test

# Run with coverage
npm run test:coverage

# Run tests in watch mode
npm run test:watch

# Run a specific test file
npx vitest run src/hooks/useChat.test.ts

# Run E2E tests (requires dev server or E2E_BASE_URL)
npm run test:e2e

# Run E2E with headed browser
npm run test:e2e:headed

# Run E2E with Playwright UI mode
npm run test:e2e:ui

# View E2E report
npm run test:e2e:report

# Lint
npm run lint

# Type check
npm run type-check:test
```

## Workflow

### Step 1: Analyze Current Coverage

```bash
# Backend — generate and analyze coverage.json
cd solune/backend
uv run pytest --cov=src --cov-report=json --cov-report=term-missing \
  --ignore=tests/property --ignore=tests/fuzz \
  --ignore=tests/chaos --ignore=tests/concurrency

# Use Python to find worst files:
python3 -c "
import json
with open('coverage.json') as f:
    data = json.load(f)
files = data['files']
for fp, info in sorted(files.items(), key=lambda x: x[1]['summary']['percent_covered']):
    s = info['summary']
    print(f\"{s['percent_covered']:5.1f}% ({s['missing_lines']:3d} missing) {fp}\")
"
```

### Step 2: Write Tests for Target Files

Follow the test patterns defined in `contracts/testing-standards.yaml`:

1. Create test file in `tests/unit/test_{module_name}.py`
2. Import the module under test
3. Use AAA pattern (Arrange-Act-Assert)
4. Use `@pytest.mark.parametrize` for edge cases
5. Mock at service boundaries only

### Step 3: Identify and Remove Stale Tests

```bash
# Find tests with no assertions (backend)
cd solune/backend
grep -rn "def test_" tests/ | while read line; do
  file=$(echo "$line" | cut -d: -f1)
  # Check if the test function has assert/raise/pytest.raises
  # Manual review needed
done

# Find tests importing non-existent modules
uv run pyright tests/ 2>&1 | grep "Import"
```

### Step 4: Verify Coverage Improvement

```bash
# Backend — verify coverage meets new threshold
cd solune/backend
uv run pytest --cov=src --cov-fail-under=80 \
  --ignore=tests/property --ignore=tests/fuzz \
  --ignore=tests/chaos --ignore=tests/concurrency

# Frontend — verify thresholds
cd solune/frontend
npm run test:coverage
# vitest will fail if below thresholds in vitest.config.ts
```

### Step 5: Run Full CI Locally

```bash
# Backend full suite
cd solune/backend
uv run ruff check src tests
uv run ruff format --check src tests
uv run pyright src
uv run pytest --cov=src --cov-report=term-missing

# Frontend full suite
cd solune/frontend
npm run lint
npx tsc --noEmit -p tsconfig.test.json
npm test
npm run test:coverage
```

## Key Configuration Files

| File | Purpose |
|------|---------|
| `solune/backend/pyproject.toml` | Backend dependencies, pytest config, coverage settings |
| `solune/frontend/vitest.config.ts` | Frontend test config, coverage thresholds |
| `solune/frontend/playwright.config.ts` | E2E test config, browser projects |
| `.github/workflows/ci.yml` | CI pipeline with test jobs |
| `.github/workflows/mutation-testing.yml` | Weekly mutation testing |
| `.github/workflows/flaky-detection.yml` | Weekly flaky test detection |
