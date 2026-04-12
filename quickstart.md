# Quickstart: Codebase Modularity Review

**Feature**: Codebase Modularity Review | **Date**: 2026-04-11

## Overview

This refactoring decomposes six monolithic hotspots into domain-scoped modules. No new features are added — the public API surface and database schema remain unchanged. All existing tests must pass after each refactoring step.

## Prerequisites

- Python ≥3.12 with virtual environment
- Node.js ≥18 with npm
- Git
- Familiarity with the existing test suites

## Refactoring Execution Order

Execute refactoring targets in strict dependency order. Each target is independently verifiable — all tests must pass before proceeding to the next.

### Target 1: Split `api/chat.py` → `api/chat/` package

**Highest impact — reduces the single largest backend file from 2930 lines to ~10 focused modules.**

```bash
cd solune/backend

# 1. Create the package directory
mkdir -p src/api/chat

# 2. Run existing tests first (baseline)
python -m pytest tests/unit/test_api_chat.py -v --timeout=120

# 3. After splitting, run the same tests to verify no regression
python -m pytest tests/unit/test_api_chat.py -v --timeout=120

# 4. Run full backend suite
python -m pytest tests/unit/ -q --timeout=120
```

**Verification**:

- `from src.api.chat import router` still works (barrel re-export)
- All 40 endpoints respond identically
- No import errors at startup: `python -c "from src.api.chat import router; print('OK')"`

### Target 2: Extract `ProposalOrchestrator` service

**Converts the 348-line `confirm_proposal()` god function into a testable service class.**

```bash
cd solune/backend

# 1. Run proposal-specific tests (baseline)
python -m pytest tests/unit/test_api_chat.py -k "confirm_proposal or proposal" -v

# 2. After extraction, verify
python -m pytest tests/unit/test_api_chat.py -k "confirm_proposal or proposal" -v

# 3. Run full suite
python -m pytest tests/unit/ -q --timeout=120
```

**Verification**:

- `confirm_proposal` endpoint returns identical responses
- New `ProposalOrchestrator` can be instantiated and tested independently
- Error handling behavior unchanged (expired proposals, missing proposals, GitHub API errors)

### Target 3: Split `services/api.ts` → `services/api/` package

**Improves frontend code-splitting and review scope.**

```bash
cd solune/frontend

# 1. Run existing API tests (baseline)
npm test -- --reporter=verbose api.test

# 2. After splitting, verify all imports resolve
npm run build

# 3. Run full test suite
npm test
```

**Verification**:

- `import { chatApi } from '@/services/api'` still works (barrel re-export)
- Build succeeds with no missing imports
- Bundle size remains the same (±5%)

### Target 4: Domain-scoped types — `types/index.ts` → `types/*.ts`

**Reduces merge conflicts and improves IDE navigation.**

```bash
cd solune/frontend

# 1. Build baseline
npm run build

# 2. After splitting, verify
npm run build
npm test
```

**Verification**:

- `import { ChatMessage } from '@/types'` still works (barrel re-export)
- TypeScript compilation succeeds with zero new errors
- No circular import warnings

### Target 5: Consolidate backend global state — `ChatStateManager`

**Wraps module-level dicts in a managed class with capacity limits.**

```bash
cd solune/backend

# 1. Run chat tests (baseline)
python -m pytest tests/unit/test_api_chat.py -v --timeout=120

# 2. After consolidation, verify
python -m pytest tests/unit/test_api_chat.py -v --timeout=120
python -m pytest tests/unit/ -q --timeout=120
```

**Verification**:

- Chat endpoints work identically
- `ChatStateManager` respects capacity limits
- No module-level mutable dicts remain in `api/chat/`

### Target 6: Split `api/webhooks.py` → `api/webhooks/` package

```bash
cd solune/backend

# 1. Run webhook tests (baseline)
python -m pytest tests/unit/test_webhooks.py -v --timeout=120

# 2. After splitting, verify
python -m pytest tests/unit/test_webhooks.py -v --timeout=120
python -m pytest tests/unit/ -q --timeout=120
```

**Verification**:

- `from src.api.webhooks import router` still works
- Webhook signature verification unchanged
- All event handlers respond identically

## Running Full Test Suites

### Backend

```bash
cd solune/backend

# Full unit test suite (5200+ tests, ~7 minutes)
python -m pytest tests/unit/ -q --timeout=120

# Coverage check (must stay ≥80%)
python -m pytest tests/unit/ --cov=src --cov-report=term-missing --cov-fail-under=80
```

### Frontend

```bash
cd solune/frontend

# Full test suite (2200+ tests, ~2 minutes)
npm test

# Build verification
npm run build
```

## Key Files Reference

### Backend — Split Targets

| Before | After | Lines Reduced |
|--------|-------|---------------|
| `src/api/chat.py` (2930 lines) | `src/api/chat/` (10 files) | 2930 → ~10 files × 100-450 lines |
| `src/api/webhooks.py` (1033 lines) | `src/api/webhooks/` (6 files) | 1033 → ~6 files × 100-300 lines |
| `src/main.py` (859 lines) | `src/main.py` (~120 lines) + `src/services/bootstrap.py` (~700 lines) | Single file → focused app definition |

### Backend — New Files

| File | Purpose |
|------|---------|
| `src/services/proposal_orchestrator.py` | Extracted `confirm_proposal` orchestration logic |
| `src/services/bootstrap.py` | Extracted lifespan/startup logic from `main.py` |
| `src/api/chat/state.py` | `ChatStateManager` class |

### Frontend — Split Targets

| Before | After |
|--------|-------|
| `src/services/api.ts` (1876 lines) | `src/services/api/` (18 files) |
| `src/types/index.ts` (1525 lines) | `src/types/` (11 files) |

### Untouched

| Area | Reason |
|------|--------|
| Database schema | No schema changes — this is a code-organization refactoring |
| API endpoints | All endpoints retain the same URL paths, request/response shapes |
| `ChatPopup.tsx` | Independent component, not part of any monolithic file |
| Middleware stack | Already well-structured |

## Troubleshooting

### Import errors after split

If `ModuleNotFoundError` occurs after splitting a file into a package:

1. Verify the `__init__.py` exists in the new package directory
2. Check that the barrel re-exports use the correct relative imports
3. Run `python -c "from src.api.chat import router"` to isolate the error

### Test failures after move

If tests fail with import errors:

1. Check test files for direct imports of moved functions (e.g., `from src.api.chat import _persist_message`)
2. Update test imports to use the new module paths
3. Private functions that were imported in tests should be importable from the sub-module

### TypeScript build errors after type split

If `tsc` reports missing types:

1. Check that `types/index.ts` barrel re-exports the moved type
2. Verify no circular imports between domain type files
3. Run `npx tsc --noEmit` for detailed error locations

### Bundle size regression

If the frontend bundle grows after splitting:

1. Verify barrel exports don't accidentally import all domains
2. Check that route-level code splitting still works (`React.lazy()` boundaries)
3. Use `npx vite-bundle-analyzer` to compare before/after
