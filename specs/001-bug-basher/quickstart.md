# Quickstart: Bug Basher

**Feature**: 001-bug-basher | **Date**: 2026-04-17

## Prerequisites

- Python 3.12+ with `uv` package manager
- Node.js 20+ with `npm`
- Repository cloned and on the feature branch

## Setup

```bash
# Navigate to repository root
cd /path/to/solune

# Install backend dependencies
cd solune/backend
uv sync --locked --extra dev

# Install frontend dependencies
cd ../frontend
npm ci
```

## Execution Order

Execute phases in strict priority order. **Do not proceed to the next phase until all validations pass.**

### Phase 1: Security Audit (P1)

```bash
# 1. Run automated security scans
cd solune/backend
uv run bandit -r src/ -ll -ii --skip B104
uv run pip-audit .

# 2. Follow checklist: specs/001-bug-basher/contracts/security-checklist.md
# 3. For each finding: fix + add regression test OR add TODO(bug-bash) comment
# 4. Validate
uv run pytest --cov=src --cov-report=term-missing --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency
uv run ruff check src tests
uv run bandit -r src/ -ll -ii --skip B104
```

### Phase 2: Runtime Errors (P2)

```bash
# 1. Run type checking
cd solune/backend
uv run pyright src
cd ../frontend
npm run type-check

# 2. Follow checklist: specs/001-bug-basher/contracts/runtime-checklist.md
# 3. Fix + test each finding
# 4. Validate both backend and frontend test suites
```

### Phase 3: Logic Bugs (P3)

```bash
# 1. Follow checklist: specs/001-bug-basher/contracts/logic-checklist.md
# 2. Focus on services/ and hooks/ directories
# 3. Fix + test each finding
# 4. Validate full test suites
```

### Phase 4: Test Quality (P4)

```bash
# 1. Run coverage analysis
cd solune/backend
uv run pytest --cov=src --cov-report=term-missing --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency

cd ../frontend
npm run test:coverage

# 2. Follow checklist: specs/001-bug-basher/contracts/test-quality-checklist.md
# 3. Fix weak tests and add missing coverage
# 4. Validate
```

### Phase 5: Code Quality (P5)

```bash
# 1. Run linters with extended rules
cd solune/backend
uv run ruff check src tests

cd ../frontend
npm run lint

# 2. Follow checklist: specs/001-bug-basher/contracts/code-quality-checklist.md
# 3. Remove dead code, fix silent failures
# 4. Validate
```

## Final Validation

```bash
# Backend: full validation suite
cd solune/backend
uv run ruff check src tests
uv run ruff format --check src tests
uv run bandit -r src/ -ll -ii --skip B104
uv run pyright src
uv run pyright -p pyrightconfig.tests.json
uv run pytest --cov=src --cov-report=term-missing --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency

# Frontend: full validation suite
cd ../frontend
npm run lint
npm run type-check
npm run test

# Suppression guard
cd ../..
bash solune/scripts/check-suppressions.sh
```

## Output

After all phases, produce a summary table in the PR description:

| # | File | Line(s) | Category | Description | Status |
|---|------|---------|----------|-------------|--------|
| 1 | `path/to/file.py` | 42-45 | Security | Description | ✅ Fixed |
| 2 | `path/to/file.py` | 100 | Logic | Description | ⚠️ Flagged (TODO) |

Status key:

- **✅ Fixed** — bug resolved, regression test added, all tests pass
- **⚠️ Flagged (TODO)** — ambiguous issue left as `TODO(bug-bash)` for human review
