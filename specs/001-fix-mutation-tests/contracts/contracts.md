# Contracts: Fix Mutation Tests

**Feature**: 001-fix-mutation-tests
**Date**: 2026-04-02
**Status**: Complete

## Overview

This feature does not introduce new API endpoints, REST resources, or GraphQL operations. The "contracts" here are configuration-level interfaces between CI workflows, tools, and documentation that must remain in sync.

---

## Contract 1: Backend Shard Alignment

**Parties**: `mutation-testing.yml` ↔ `run_mutmut_shard.py` ↔ `testing.md`

### Invariant

The set of shard names in the CI workflow matrix MUST equal the set of keys in the `SHARDS` dictionary in `run_mutmut_shard.py`, and MUST equal the set of shards documented in `testing.md`.

### Schema

```yaml
# mutation-testing.yml backend matrix
matrix:
  shard:
    - auth-and-projects
    - orchestration
    - app-and-data
    - agents-and-integrations
    - api-and-middleware      # ADDED
```

```python
# run_mutmut_shard.py SHARDS keys (no change needed — already defines all 5)
SHARDS = {
    "auth-and-projects": [...],
    "orchestration": [...],
    "app-and-data": [...],
    "agents-and-integrations": [...],
    "api-and-middleware": [...],
}
```

### Verification

```bash
# Extract shard names from CI workflow
grep -A10 'matrix:' .github/workflows/mutation-testing.yml | grep '^ *- ' | sed 's/^ *- //'

# Extract shard names from shard runner
python -c "exec(open('solune/backend/scripts/run_mutmut_shard.py').read()); print(list(SHARDS.keys()))"

# Compare outputs — they must match exactly
```

---

## Contract 2: Mutmut Workspace Parity

**Parties**: `pyproject.toml [tool.mutmut]` ↔ `registry.py` path resolution ↔ `template_files.py` path resolution

### Invariant

Every file path resolved by production code using `Path(__file__).resolve().parents[N]` traversal MUST be reachable from the mutmut workspace. The `also_copy` list in `pyproject.toml` MUST include all such paths.

### Schema

```toml
# pyproject.toml [tool.mutmut]
also_copy = [
    # ... existing entries ...
    "../templates/",          # ADDED — required by registry.py parents[3] traversal
]
```

### Path Resolution Map

| Source File | Resolution Expression | Target Path | Workspace Requirement |
|------------|----------------------|------------|----------------------|
| `registry.py` | `Path(__file__).resolve().parents[3] / "templates" / "app-templates"` | `solune/templates/app-templates/` | `../templates/` in `also_copy` |
| `template_files.py` | `Path(__file__).resolve().parents[4]` | repo root (for `.github/`, `.specify/`) | Env var `TEMPLATE_SOURCE_DIR` or copy |

### Verification

```bash
# Build mutant workspace and check for templates directory
cd solune/backend
uv run mutmut run --paths-to-mutate src/services/app_templates/registry.py --runner "python -m pytest tests/unit/test_agent_tools.py -x" 2>&1 | head -20
```

---

## Contract 3: Frontend Shard Coverage Completeness

**Parties**: `mutation-testing.yml` frontend matrix ↔ `stryker.config.mjs` base scope

### Invariant

The union of all frontend shard `--mutate` globs MUST cover every file matched by the base `stryker.config.mjs` `mutate` array. No file may be excluded by sharding.

### Schema

```yaml
# mutation-testing.yml frontend matrix
matrix:
  include:
    - shard: board-polling-hooks
      mutate: "src/hooks/useAdaptivePolling.ts,src/hooks/useBoardProjection.ts,src/hooks/useBoard*.ts,src/hooks/*Poll*.ts,!src/**/*.test.ts,!src/**/*.property.test.ts"
    - shard: data-query-hooks
      mutate: "src/hooks/useQuery*.ts,src/hooks/useMutation*.ts,src/hooks/use*Data*.ts,src/hooks/use*Fetch*.ts,!src/**/*.test.ts,!src/**/*.property.test.ts"
    - shard: general-hooks
      mutate: "src/hooks/**/*.ts,!src/hooks/useAdaptivePolling.ts,!src/hooks/useBoardProjection.ts,!src/hooks/useBoard*.ts,!src/hooks/*Poll*.ts,!src/hooks/useQuery*.ts,!src/hooks/useMutation*.ts,!src/hooks/use*Data*.ts,!src/hooks/use*Fetch*.ts,!src/**/*.test.ts,!src/**/*.property.test.ts"
    - shard: lib-utils
      mutate: "src/lib/**/*.ts,!src/**/*.test.ts,!src/**/*.property.test.ts"
```

### Verification

```bash
# List all files in original scope
find src/hooks -name '*.ts' ! -name '*.test.ts' ! -name '*.property.test.ts' | sort > /tmp/original-scope.txt

# List files matched by each shard glob and union them
# ... per-shard file lists ...
# Diff against original scope — must be empty
```

---

## Contract 4: Focused Mutation Commands

**Parties**: `package.json` scripts ↔ `stryker.config.mjs` ↔ `testing.md`

### Invariant

Every focused mutation command in `package.json` MUST use the same base Stryker configuration and MUST be documented in `testing.md`.

### Schema

```json
{
  "test:mutate": "stryker run",
  "test:mutate:file": "stryker run --mutate",
  "test:mutate:hooks-board": "stryker run --mutate 'src/hooks/useAdaptivePolling.ts,src/hooks/useBoardProjection.ts,src/hooks/useBoard*.ts,src/hooks/*Poll*.ts,!src/**/*.test.ts,!src/**/*.property.test.ts'",
  "test:mutate:hooks-data": "stryker run --mutate 'src/hooks/useQuery*.ts,src/hooks/useMutation*.ts,src/hooks/use*Data*.ts,src/hooks/use*Fetch*.ts,!src/**/*.test.ts,!src/**/*.property.test.ts'",
  "test:mutate:hooks-general": "stryker run --mutate 'src/hooks/**/*.ts,!src/hooks/useAdaptivePolling.ts,!src/hooks/useBoardProjection.ts,!src/hooks/useBoard*.ts,!src/hooks/*Poll*.ts,!src/hooks/useQuery*.ts,!src/hooks/useMutation*.ts,!src/hooks/use*Data*.ts,!src/hooks/use*Fetch*.ts,!src/**/*.test.ts,!src/**/*.property.test.ts'",
  "test:mutate:lib": "stryker run --mutate 'src/lib/**/*.ts,!src/**/*.test.ts,!src/**/*.property.test.ts'"
}
```

### Verification

```bash
# Verify all scripts reference stryker run
grep 'test:mutate' solune/frontend/package.json | grep -v 'stryker run' && echo "FAIL: non-stryker mutation command found" || echo "PASS"
```

---

## Contract 5: Provider Wrapper Nesting

**Parties**: `test-utils.tsx` ↔ all component test files using `renderWithProviders`

### Invariant

The `renderWithProviders` function MUST render `{children}` exactly once. All context providers MUST be nested, not siblings.

### Verification

```bash
# Count occurrences of {children} in the Wrapper function
grep -c '{children}' solune/frontend/src/test/test-utils.tsx
# Expected: 1 (exactly one occurrence)
```
