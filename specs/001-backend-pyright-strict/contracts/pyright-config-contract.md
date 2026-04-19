# Pyright Configuration Contract

**Feature**: 001-backend-pyright-strict
**Owners**: backend type-checking config files (`solune/backend/pyproject.toml`, `solune/backend/pyrightconfig.tests.json`)
**Consumers**: `uv run pyright` (local), `.github/workflows/ci.yml` Pyright step.

This contract specifies the exact post-condition state of both Pyright configuration files at each phase boundary. Implementation tasks must produce configuration that matches these exemplars verbatim (other than ordering of unrelated keys).

---

## C1 — `[tool.pyright]` block in `solune/backend/pyproject.toml`

### After Phase 1

```toml
[tool.pyright]
pythonVersion = "3.13"
typeCheckingMode = "standard"
include = ["src"]
exclude = ["**/__pycache__", "htmlcov"]
reportMissingTypeStubs = false
reportMissingImports = "error"
reportUnnecessaryTypeIgnoreComment = "error"
reportMissingParameterType = "error"
reportUnknownParameterType = "warning"
reportUnknownMemberType = "warning"
stubPath = "src/typestubs"
```

### After Phase 2

Identical to Phase 1, plus:

```toml
strict = ["src/api", "src/models", "src/services/agents"]
```

The `strict` line MAY be placed anywhere within the table; recommended position is immediately after `stubPath` for readability.

### After Phase 3

Same keys as Phase 2, with one change:

```toml
typeCheckingMode = "strict"   # was "standard"
```

### After Phase 4 (reportUnknownMemberType promotion — separate PR)

Same as Phase 3 with one change:

```toml
reportUnknownMemberType = "error"  # was "warning"
```

### Contract acceptance

For any phase, the following commands MUST succeed:

```bash
cd solune/backend
uv run pyright                          # exit 0
uv run pyright --outputjson | \
  jq -e '[.generalDiagnostics[] | select(.severity == "error")] | length == 0'
```

---

## C2 — `solune/backend/pyrightconfig.tests.json`

### Phase 0 (current)

```json
{
  "include": ["tests"],
  "exclude": ["**/__pycache__", "htmlcov"],
  "pythonVersion": "3.13",
  "typeCheckingMode": "off",
  "reportInvalidTypeForm": "none",
  "stubPath": "src/typestubs",
  "executionEnvironments": [
    {
      "root": ".",
      "extraPaths": ["src"]
    }
  ]
}
```

### After Phase 1 (and unchanged thereafter)

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

**Invariants** (FR-011): `typeCheckingMode` MUST equal `"off"` in every phase. No `strict` array is added to the tests config.

### Contract acceptance

```bash
cd solune/backend
uv run pyright -p pyrightconfig.tests.json   # exit 0 in every phase
```

---

## C3 — Forbidden states

The following configurations are explicitly disallowed at every phase and MUST cause CI to fail (enforced by Pyright itself or by the burn-down gate):

- `[tool.pyright] typeCheckingMode = "off"` — disables analysis project-wide.
- `[tool.pyright] typeCheckingMode = "basic"` — silently weakens analysis below the Phase 0 baseline.
- `[tool.pyright] strict = []` after Phase 2 — empty floor is a contract violation.
- `[tool.pyright] strict` containing any path *outside* `src/api`, `src/models`, `src/services/agents` without a follow-up spec amendment.
- `pyrightconfig.tests.json typeCheckingMode != "off"` (FR-011).
