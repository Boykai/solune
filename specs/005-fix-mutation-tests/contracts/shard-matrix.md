# Shard Matrix Contract

**Feature**: 005-fix-mutation-tests
**Date**: 2026-04-02

## Purpose

This document defines the contract between the shard definitions (source of truth) and the CI workflow matrix entries. Any change to shard definitions MUST be reflected in the CI workflow and documentation.

## Backend Shard Contract

### Source of Truth

`solune/backend/scripts/run_mutmut_shard.py` → `SHARDS` dictionary

### Required CI Matrix Entries

File: `.github/workflows/mutation-testing.yml` → `jobs.backend-mutation.strategy.matrix.shard`

```yaml
shard:
  - auth-and-projects
  - orchestration
  - app-and-data
  - agents-and-integrations
  - api-and-middleware          # NEW — was missing
```

### Required also_copy Entries

File: `solune/backend/pyproject.toml` → `[tool.mutmut].also_copy`

Must include at minimum:
- All `src/` modules imported by test suite
- `templates/` (for app-template tests)

### Artifact Naming

Pattern: `backend-mutation-report-{shard}`
Example: `backend-mutation-report-api-and-middleware`

---

## Frontend Shard Contract

### Source of Truth

Individual Stryker config files in `solune/frontend/`:

| Config File | Shard Name |
|-------------|------------|
| `stryker-hooks-board.config.mjs` | `hooks-board` |
| `stryker-hooks-data.config.mjs` | `hooks-data` |
| `stryker-hooks-general.config.mjs` | `hooks-general` |
| `stryker-lib.config.mjs` | `lib` |

### Required CI Matrix Entries

File: `.github/workflows/mutation-testing.yml` → `jobs.frontend-mutation.strategy.matrix.shard`

```yaml
shard:
  - hooks-board
  - hooks-data
  - hooks-general
  - lib
```

### Required package.json Scripts

File: `solune/frontend/package.json` → `scripts`

```json
{
  "test:mutate": "stryker run",
  "test:mutate:hooks-board": "stryker run -c stryker-hooks-board.config.mjs",
  "test:mutate:hooks-data": "stryker run -c stryker-hooks-data.config.mjs",
  "test:mutate:hooks-general": "stryker run -c stryker-hooks-general.config.mjs",
  "test:mutate:lib": "stryker run -c stryker-lib.config.mjs"
}
```

### Artifact Naming

Pattern: `frontend-mutation-report-{shard}`
Example: `frontend-mutation-report-hooks-board`

---

## Documentation Contract

### testing.md Updates Required

1. Backend mutation section: list all 5 shards
2. Frontend mutation section: list all 4 shards and focused commands
3. CI Gates section: update shard counts

### CHANGELOG.md Updates Required

Under `[Unreleased]`:
- Backend: mutmut workspace parity fix, 5th shard addition
- Frontend: Stryker sharding, focused mutation commands, test-utils fix

---

## Verification Checklist

- [ ] `len(SHARDS)` in `run_mutmut_shard.py` == number of backend CI matrix entries
- [ ] Number of `stryker-*.config.mjs` files == number of frontend CI matrix entries
- [ ] Union of frontend shard mutate globs == original `stryker.config.mjs` mutate scope
- [ ] `also_copy` includes `templates/`
- [ ] Each CI shard uploads a uniquely named artifact
- [ ] `testing.md` documents all shards
- [ ] `CHANGELOG.md` has entries for all changes
