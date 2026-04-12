# Quickstart: Codebase Modularity Review

**Feature**: Codebase Modularity Review | **Date**: 2026-04-12

> **Status note (2026-04-12):** This is a structural refactoring — no new features, no new dependencies, no database migrations. All changes are file moves and extractions with barrel re-exports for backward compatibility.

## Prerequisites

- Python 3.11+ with pip
- Node.js ≥18 with npm
- Git

## Setup

```bash
cd solune/backend

# Install backend dependencies
pip install -e ".[dev]"

cd ../frontend

# Install frontend dependencies
npm install
```

## Verify Before Refactoring

Run the full test suites to establish a passing baseline:

```bash
# Backend tests
cd solune/backend
python -m pytest tests/ -x -q

# Frontend tests
cd solune/frontend
npx vitest run

# Frontend type-checking
npx tsc --noEmit

# Frontend linting
npx eslint .
```

## Phase Execution Order

### Phase 1: Backend ChatStateManager + bootstrap.py

**What changes**: Extract 4 module-level dicts and their accessor functions from `api/chat.py` into `services/chat_state_manager.py`. Extract startup/shutdown helpers from `main.py` into `services/bootstrap.py`.

```bash
# Files created:
# - solune/backend/src/services/chat_state_manager.py
# - solune/backend/src/services/bootstrap.py
# - solune/backend/tests/unit/test_chat_state_manager.py

# Verify:
python -m pytest tests/unit/test_chat_state_manager.py -v
python -m pytest tests/unit/test_main.py -v
```

### Phase 2: Backend ProposalOrchestrator

**What changes**: Extract `confirm_proposal()` from `api/chat.py` into `services/proposal_orchestrator.py`.

```bash
# Files created:
# - solune/backend/src/services/proposal_orchestrator.py
# - solune/backend/tests/unit/test_proposal_orchestrator.py

# Verify:
python -m pytest tests/unit/test_proposal_orchestrator.py -v
python -m pytest tests/ -x -q  # Full backend suite
```

### Phase 3: Backend Split api/chat.py

**What changes**: Convert `api/chat.py` to `api/chat/` package with 5 domain modules.

```bash
# Files created:
# - solune/backend/src/api/chat/__init__.py
# - solune/backend/src/api/chat/conversations.py
# - solune/backend/src/api/chat/messages.py
# - solune/backend/src/api/chat/proposals.py
# - solune/backend/src/api/chat/plans.py
# - solune/backend/src/api/chat/streaming.py

# File deleted:
# - solune/backend/src/api/chat.py

# Verify:
python -m pytest tests/ -x -q
```

### Phase 4: Backend Split api/webhooks.py

**What changes**: Convert `api/webhooks.py` to `api/webhooks/` package with 3 domain modules.

```bash
# Files created:
# - solune/backend/src/api/webhooks/__init__.py
# - solune/backend/src/api/webhooks/handlers.py
# - solune/backend/src/api/webhooks/pull_requests.py
# - solune/backend/src/api/webhooks/ci.py

# File deleted:
# - solune/backend/src/api/webhooks.py

# Verify:
python -m pytest tests/ -x -q
```

### Phase 5: Frontend Split services/api.ts

**What changes**: Convert `services/api.ts` to `services/api/` directory with 16 domain files + barrel index.ts.

```bash
# Files created:
# - solune/frontend/src/services/api/index.ts (barrel)
# - solune/frontend/src/services/api/client.ts
# - solune/frontend/src/services/api/{auth,projects,tasks,chat,board,...}.ts

# File deleted:
# - solune/frontend/src/services/api.ts

# Verify:
npx tsc --noEmit
npx vitest run
npx eslint .
```

### Phase 6: Frontend Split types/index.ts

**What changes**: Split `types/index.ts` into 17 domain files + barrel index.ts.

```bash
# Files created:
# - solune/frontend/src/types/common.ts
# - solune/frontend/src/types/{auth,projects,tasks,chat,board,...}.ts

# File modified:
# - solune/frontend/src/types/index.ts (becomes barrel re-export)

# Verify:
npx tsc --noEmit
npx vitest run
npx eslint .
```

### Phase 7: Full Verification

```bash
# Backend full suite
cd solune/backend
python -m pytest tests/ -v

# Frontend full suite
cd solune/frontend
npx vitest run
npx tsc --noEmit
npx eslint .

# Regenerate architecture diagrams (if applicable)
cd ../..
bash solune/scripts/generate-diagrams.sh
```

## Key Invariants

1. **All existing imports work unchanged** — Barrel `index.ts` / `__init__.py` re-exports preserve import paths
2. **No functional changes** — Same endpoints, same responses, same behavior
3. **No new dependencies** — Zero additions to `pyproject.toml` or `package.json`
4. **No database migrations** — No schema changes
5. **Test patch paths may change** — `src.api.chat.X` becomes `src.api.chat.module.X` in some test mocks

## Common Issues

### Backend: Import patch paths in tests

After splitting `chat.py` into a package, test mocks like `@patch("src.api.chat.get_github_service")` may need to become `@patch("src.api.chat.proposals.get_github_service")` depending on where the import is used.

### Frontend: Circular imports in types

If domain type files import from each other (e.g., `chat.ts` needs `PlanCreateActionData` from `plans.ts`), ensure the barrel `index.ts` is not in the import chain. Domain files should import directly from sibling files (`import { PlanCreateActionData } from './plans'`).

### Diagram regeneration

After converting `api/chat.py` and `api/webhooks.py` to packages, run `generate-diagrams.sh` to update `backend-components.mmd`. The script already handles both `.py` files and package directories with `__init__.py`.
