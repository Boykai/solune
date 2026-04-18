# Data Model: Tighten Backend Pyright (Standard → Strict, Gradually)

**Feature**: 001-tighten-backend-pyright | **Date**: 2026-04-18

> This feature is a tooling/configuration change. There are no database entities,
> API models, or runtime data structures to define. The "entities" below describe
> the configuration artifacts and policy objects that govern the rollout.

## Entities

### 1. Backend Type-Checking Policy

**Location**: `solune/backend/pyproject.toml` → `[tool.pyright]`

| Field | Type | Phase | Description |
|-------|------|-------|-------------|
| `pythonVersion` | string | existing | Target Python version (`"3.13"`) |
| `typeCheckingMode` | string | P1: `"standard"` → P3: `"strict"` | Global checking level |
| `include` | list[string] | existing | Paths to check (`["src"]`) |
| `exclude` | list[string] | existing | Paths to skip |
| `reportMissingTypeStubs` | bool/string | existing | `false` |
| `reportMissingImports` | string | existing | `"error"` |
| `stubPath` | string | existing | `"src/typestubs"` |
| `reportUnnecessaryTypeIgnoreComment` | string | P1: `"error"` | Flags redundant `# type: ignore` |
| `reportMissingParameterType` | string | P1: `"error"` | Flags functions missing param types |
| `reportUnknownParameterType` | string | P1: `"error"` | Flags params with inferred `Unknown` |
| `reportUnknownMemberType` | string | P1: `"warning"` → P4: `"error"` | Flags members with `Unknown` type |
| `strict` | list[string] | P2: `["src/api", "src/models", "src/services/agents"]` | Protected strict-floor paths |

**Validation rules**:

- `typeCheckingMode` must be one of `"off"`, `"basic"`, `"standard"`, `"strict"`.
- `strict` paths must be subdirectories of `include` paths.
- After Phase 3, `typeCheckingMode = "strict"` and `strict` list coexist (floor contract).

**State transitions**:

```text
Phase 1: typeCheckingMode = "standard" + 4 new report rules
    ↓
Phase 2: typeCheckingMode = "standard" + strict = [3 paths]
    ↓
Phase 3: typeCheckingMode = "strict"  + strict = [3 paths] (floor preserved)
    ↓
Phase 4: reportUnknownMemberType promoted from "warning" to "error"
```

### 2. Protected Package Set

**Location**: `[tool.pyright].strict` in `pyproject.toml`

| Package Path | File Count | Phase Added | Notes |
|-------------|-----------|-------------|-------|
| `src/api` | 23 | Phase 2 | FastAPI route handlers; `Depends()` typing fixes needed |
| `src/models` | 29 | Phase 2 | Pydantic/dataclass models; expected to be cleanest |
| `src/services/agents` | 4 | Phase 2 | Agent service; `aiosqlite.Row` typed access fix needed |

**Invariant**: No file inside these paths may contain `# pyright: basic` or any
file-level downgrade pragma. Enforced by CI grep gate (Phase 4).

### 3. Legacy Downgrade Record

**Location**: `solune/backend/docs/decisions/001-pyright-strict-legacy-opt-outs.md`

| Field | Type | Description |
|-------|------|-------------|
| Module path | string | Relative path from `src/` |
| Owner | string | Team or individual responsible for cleanup |
| Reason | string | Why the module cannot pass strict yet |
| Date added | date | When the pragma was introduced |
| Pragma | string | Always `# pyright: basic` (never `# pyright: off`) |

**Expected initial entries** (Phase 3):

| Module | Reason |
|--------|--------|
| `src/services/github_projects/**` | Incomplete githubkit stubs; deep dynamic API usage |
| `src/services/copilot_polling/**` | Copilot SDK partial typing |
| `src/main.py` | FastAPI app assembly with dynamic imports |
| `src/services/chat_agent.py` | Complex agent orchestration with dynamic dispatch |

### 4. Tests Type-Checking Config

**Location**: `solune/backend/pyrightconfig.tests.json`

| Field | Current | Change |
|-------|---------|--------|
| `typeCheckingMode` | `"off"` | No change (stays off) |
| `reportUnnecessaryTypeIgnoreComment` | *(absent)* | P1: `"error"` |

**Rationale**: Tests use heavy mocking (`MagicMock`, `AsyncMock`) that creates
false-positive strict diagnostics. Only redundant-suppression detection is mirrored.

## Relationships

```text
pyproject.toml [tool.pyright]
    ├── governs → src/**/*.py (all source files)
    ├── strict floor → src/api/, src/models/, src/services/agents/
    └── references → src/typestubs/ (stub augmentation)

pyrightconfig.tests.json
    └── governs → tests/**/*.py (test files only)

docs/decisions/001-*.md
    └── lists → files with # pyright: basic pragmas

CI workflow (ci.yml)
    ├── runs → uv run pyright src
    ├── runs → uv run pyright -p pyrightconfig.tests.json
    ├── gate → grep for pragmas in strict floor
    └── reports → pragma count per build
```
