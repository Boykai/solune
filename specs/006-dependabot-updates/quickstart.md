# Quickstart: Dependabot Updates

**Feature**: Dependabot Updates | **Date**: 2026-04-14

## Prerequisites

- Node.js ≥18 with npm
- Python ≥3.12 with `uv` package manager
- Git
- GitHub CLI (`gh`) for PR management (optional)

## Setup

```bash
# Ensure you're on a clean branch from main
git checkout main
git pull origin main
git checkout -b chore/deps-batch-update
```

## Execution Steps

### Step 1: Apply Backend Patch Updates

```bash
cd solune/backend

# PR #1732: pytest 9.0.0 → 9.0.3
# Edit pyproject.toml: change "pytest>=9.0.0" to "pytest>=9.0.3"
uv lock && uv sync --extra dev
uv run pytest tests/unit/ -q
# If pass → commit; if fail → revert
```

### Step 2: Apply Frontend Patch Updates

```bash
cd solune/frontend

# PR #1777: happy-dom 20.8.9 → 20.9.0
# PR #1776: typescript-eslint 8.58.1 → 8.58.2
# PR #1775: react-router-dom 7.14.0 → 7.14.1
# Edit package.json for each, then:
npm install
npm run lint && npm run type-check && npm run test && npm run build
# If pass → commit; if fail → revert individual changes
```

### Step 3: Apply Backend Minor Updates (Dev)

```bash
cd solune/backend

# PR #1688: pytest-cov >=7.0.0 → >=7.1.0
# PR #1695: freezegun >=1.4.0 → >=1.5.5
# PR #1694: pip-audit >=2.9.0 → >=2.10.0
# PR #1697: mutmut >=3.2.0 → >=3.5.0
# PR #1690: bandit >=1.8.0 → >=1.9.4
# Edit pyproject.toml for each, then:
uv lock && uv sync --extra dev
uv run ruff check src/ tests/
uv run pyright src/
uv run pytest tests/unit/ -q
```

### Step 4: Apply Backend Minor Updates (Runtime)

```bash
cd solune/backend

# PR #1692: pynacl >=1.5.0 → >=1.6.2
# PR #1696: uvicorn >=0.42.0 → >=0.44.0
# PR #1698: agent-framework-core >=1.0.0b1 → >=1.0.1
# Edit pyproject.toml for each, then:
uv lock && uv sync --extra dev
uv run ruff check src/ tests/
uv run pyright src/
uv run pytest tests/unit/ -q
```

### Step 5: Apply Frontend Minor Updates

```bash
cd solune/frontend

# PR #1699: @tanstack/react-query 5.97.0 → 5.99.0
# Edit package.json, then:
npm install
npm run lint && npm run type-check && npm run test && npm run build
```

### Step 6: Apply Backend Major Updates

```bash
cd solune/backend

# PR #1693: pytest-randomly >=3.16.0 → >=4.0.1 (MAJOR)
# ⚠ Inspect changelog first for breaking changes
# Edit pyproject.toml, then:
uv lock && uv sync --extra dev
uv run pytest tests/unit/ -q
# If fail → skip, document migration steps needed
```

### Step 7: Create Batch PR

```bash
git add .
git commit -m "chore(deps): apply Dependabot batch update"
git push origin chore/deps-batch-update
# Create PR with applied/skipped checklist
```

## Verification

After all updates are applied:

```bash
# Full frontend validation
cd solune/frontend && npm run lint && npm run type-check && npm run test && npm run build

# Full backend validation
cd solune/backend && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run pyright src/ && uv run pytest tests/unit/ -q
```
