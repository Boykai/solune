# Quickstart: Fix Mutation Tests

**Feature**: 001-fix-mutation-tests
**Date**: 2026-04-02

## Prerequisites

- Python 3.11+ with `uv` package manager
- Node.js 22+ with npm
- Git

## Implementation Order

The changes follow a strict dependency order based on the spec's user story priorities:

### Phase 1: Backend Workspace Parity (P1 — Blocker)

**Files**: `solune/backend/pyproject.toml`

```bash
# 1. Add ../templates/ to also_copy in [tool.mutmut]
cd solune/backend
# Edit pyproject.toml [tool.mutmut] also_copy list

# 2. Verify: run the app-template tests normally
uv run python -m pytest tests/unit/test_agent_tools.py -v -k "test_list_app_templates or test_get_app_template"

# 3. Verify: run a targeted mutmut test to confirm workspace parity
uv run python scripts/run_mutmut_shard.py --shard agents-and-integrations --dry-run
```

### Phase 2: Backend Shard Alignment (P2)

**Files**: `.github/workflows/mutation-testing.yml`, `solune/docs/testing.md`

```bash
# 1. Add api-and-middleware to the backend matrix in mutation-testing.yml
# 2. Update testing.md to document all 5 shards
# 3. Verify shard names match across all three sources:
python -c "
import yaml, ast
# Compare CI matrix shards vs run_mutmut_shard.py SHARDS keys
"
```

### Phase 3: Frontend Sharding (P2)

**Files**: `.github/workflows/mutation-testing.yml`, `solune/frontend/stryker.config.mjs` (no changes), `solune/frontend/package.json`

```bash
# 1. Add frontend shard matrix to mutation-testing.yml
# 2. Each shard uses --mutate CLI override
# 3. Verify: dry-run a single shard locally
cd solune/frontend
npx stryker run --mutate 'src/lib/**/*.ts,!src/**/*.test.ts,!src/**/*.property.test.ts' --dryRunOnly
```

### Phase 4: Focused Mutation Commands (P3)

**Files**: `solune/frontend/package.json`, `solune/docs/testing.md`

```bash
# 1. Add focused mutation scripts to package.json
# 2. Document in testing.md
# 3. Verify:
cd solune/frontend
npm run test:mutate:lib -- --dryRunOnly
```

### Phase 5: Test-Utils Provider Fix (P3)

**Files**: `solune/frontend/src/test/test-utils.tsx`

```bash
# 1. Nest providers correctly (children rendered once)
# 2. Run full frontend test suite to catch any regressions:
cd solune/frontend
npm test
```

### Phase 6: Survivor Cleanup Tests (P3)

**Files**: New test files or additions to existing tests for `useAdaptivePolling.ts` and `useBoardProjection.ts`

```bash
# 1. Add deterministic assertions for tier transitions, visibility polls, expansion ranges
# 2. Run targeted mutation test:
cd solune/frontend
npm run test:mutate:hooks-board
```

### Phase 7: Documentation & Changelog (P3)

**Files**: `solune/docs/testing.md`, `solune/CHANGELOG.md`

```bash
# 1. Update testing.md with full shard layout and focused commands
# 2. Add changelog entry under [Unreleased]
# 3. Verify no broken links or formatting:
cd solune
npx markdownlint docs/testing.md CHANGELOG.md
```

## Verification Checklist

```bash
# Backend: app-template tests pass
cd solune/backend && uv run python -m pytest tests/unit/test_agent_tools.py -v

# Backend: all 5 shards listed in CI workflow
grep -A20 'matrix:' ../.github/workflows/mutation-testing.yml | grep 'shard'

# Frontend: test suite passes (no double-render regressions)
cd solune/frontend && npm test

# Frontend: focused mutation command works
cd solune/frontend && npm run test:mutate:lib -- --dryRunOnly

# Documentation: shard lists match
# Compare testing.md shard list with CI workflow matrix
```

## Key Decisions (from research.md)

1. **Workspace parity**: Add `../templates/` to mutmut `also_copy` (not env vars or mocks)
2. **Frontend sharding**: 4 shards via `--mutate` CLI overrides (not separate config files)
3. **Provider fix**: Nest providers, don't remove them
4. **No threshold lowering**: All fixes via workspace parity, sharding, and better tests
