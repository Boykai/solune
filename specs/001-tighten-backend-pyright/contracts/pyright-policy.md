# Contract: Pyright Policy Configuration

**Feature**: 001-tighten-backend-pyright | **Date**: 2026-04-18

> This feature has no REST/GraphQL API contracts. The "contract" is the
> configuration schema enforced by Pyright and validated by CI. This document
> defines the expected configuration state after each phase.

## Phase 1 — Safety-Net Settings

### pyproject.toml `[tool.pyright]`

```toml
[tool.pyright]
pythonVersion = "3.13"
typeCheckingMode = "standard"
include = ["src"]
exclude = ["**/__pycache__", "htmlcov"]
reportMissingTypeStubs = false
reportMissingImports = "error"
stubPath = "src/typestubs"
# Phase 1 additions:
reportUnnecessaryTypeIgnoreComment = "error"
reportMissingParameterType = "error"
reportUnknownParameterType = "error"
reportUnknownMemberType = "warning"
```

### pyrightconfig.tests.json

```json
{
  "include": ["tests"],
  "exclude": ["**/__pycache__", "htmlcov"],
  "pythonVersion": "3.13",
  "typeCheckingMode": "off",
  "reportInvalidTypeForm": "none",
  "reportUnnecessaryTypeIgnoreComment": "error",
  "stubPath": "src/typestubs",
  "executionEnvironments": [
    {
      "root": ".",
      "extraPaths": ["src"]
    }
  ]
}
```

### Verification

```bash
cd solune/backend
uv run pyright src                           # exit 0, 0 errors
uv run pyright -p pyrightconfig.tests.json   # exit 0, 0 errors
```

## Phase 2 — Strict Floor

### pyproject.toml `[tool.pyright]` (additions)

```toml
strict = ["src/api", "src/models", "src/services/agents"]
```

### Verification

```bash
cd solune/backend
uv run pyright src   # exit 0; strict-floor files checked at strict level
```

### Canary Test

```python
# Temporarily add to src/api/canary_test.py (not committed):
def foo(x):  # Must fail: missing parameter type + return type
    return x
```

Expected: pyright reports errors for `foo` in strict-floor scope.

## Phase 3 — Global Strict

### pyproject.toml `[tool.pyright]` (change)

```toml
typeCheckingMode = "strict"
```

### Legacy File Pragma Format

```python
# pyright: basic  — reason: <justification matching ADR entry>
```

### ADR Contract

File: `solune/backend/docs/decisions/001-pyright-strict-legacy-opt-outs.md`

Required fields per entry:

| Field | Required | Example |
|-------|----------|---------|
| Module path | Yes | `src/services/github_projects/` |
| Owner | Yes | `@backend-team` |
| Reason | Yes | Incomplete githubkit stubs |
| Date added | Yes | 2026-04-XX |

### Verification

```bash
cd solune/backend
uv run pyright src   # exit 0; all non-pragmaed files at strict
```

## Phase 4 — Burn-Down Gates

### CI Strict-Floor Integrity Gate

```bash
# Must exit non-zero if any pragma found in strict floor
if grep -rn "pyright: basic" src/api/ src/models/ src/services/agents/; then
  echo "ERROR: pyright: basic pragma found inside strict floor"
  exit 1
fi
```

### CI Downgrade Count Reporter

```bash
echo "Pyright downgrades remaining: $(grep -rn 'pyright: basic' src/ | wc -l)"
```

### Future Config Change

```toml
# When backlog is clear:
reportUnknownMemberType = "error"   # promoted from "warning"
```
