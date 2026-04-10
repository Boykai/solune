# Quickstart: Harden Phase 3 — Code Quality & Tech Debt

**Feature**: Harden Phase 3 | **Date**: 2026-04-10 | **Plan**: [plan.md](plan.md)

## Prerequisites

- Python ≥3.12 with pip
- Node.js ≥20.x with npm
- Git

## Getting Started

### 1. Clone and set up the backend

```bash
cd solune/backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Set up the frontend

```bash
cd solune/frontend
npm install
```

### 3. Run existing tests (baseline)

```bash
# Backend
cd solune/backend
pytest --tb=short -q

# Frontend
cd solune/frontend
npm test
```

## Workstream-Specific Commands

### 3.1 — Singleton DI Refactor

After making import changes, run the backend tests:

```bash
cd solune/backend
pytest tests/ --tb=short -q
```

Key files to verify:

- `src/dependencies.py` — accessor functions
- `src/services/github_projects/__init__.py` — re-exports
- All API route files in `src/api/` — should use `Depends(get_github_service)`

### 3.2 — Pre-release Dependency Upgrades

Upgrade one package at a time and test:

```bash
cd solune/backend

# Example: upgrade azure-ai-inference
pip install "azure-ai-inference>=1.0.0"
pytest --tb=short -q

# Example: upgrade agent-framework (all three together)
pip install "agent-framework-core>=1.0.0" "agent-framework-azure-ai>=1.0.0" "agent-framework-github-copilot>=1.0.0"
pytest --tb=short -q
```

For the copilot-sdk v2 rename:

```bash
pip install "copilot-sdk>=1.0.17"
# Then grep and update all imports:
grep -rn "github.copilot.sdk\|github_copilot_sdk" solune/backend/src/
```

### 3.3 — Stryker Config Consolidation

After consolidating configs, verify each shard:

```bash
cd solune/frontend

# Run each shard via the new unified approach
STRYKER_SHARD=hooks-board npx stryker run
STRYKER_SHARD=hooks-data npx stryker run
STRYKER_SHARD=hooks-general npx stryker run
STRYKER_SHARD=lib npx stryker run

# Run full (no shard = all targets)
npx stryker run
```

### 3.4 — Plan-Mode Chat History (Verification)

No code changes needed. Run the relevant test:

```bash
cd solune/backend
pytest tests/ -k "plan" --tb=short -q
```

## Verification Checklist

- [ ] All backend tests pass (`pytest`)
- [ ] All frontend tests pass (`npm test`)
- [ ] Backend type checking passes (`pyright` or `mypy`)
- [ ] Frontend type checking passes (`tsc --noEmit`)
- [ ] Pre-commit hooks pass
- [ ] CI pipeline green
