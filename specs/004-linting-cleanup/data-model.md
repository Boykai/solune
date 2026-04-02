# Data Model: Linting Clean Up

**Feature**: 004-linting-cleanup | **Date**: 2026-04-02
**Purpose**: Define configuration entities, relationships, and validation rules for the type-check gate expansion and suppression cleanup.

## Overview

This feature is a tooling/configuration change — it does not introduce new runtime data models, database entities, or API schemas. The "data model" consists of configuration files that control type-checking behaviour.

## Configuration Entities

### 1. Backend Pyright Configuration

**Entity**: `[tool.pyright]` section in `solune/backend/pyproject.toml`

| Field | Current Value | Target Value | Validation |
|-------|--------------|--------------|------------|
| `pythonVersion` | `"3.13"` | `"3.13"` (unchanged) | Must match runtime Python version |
| `typeCheckingMode` | `"standard"` | `"standard"` (unchanged) | Per assumption: no strictness change |
| `include` | `["src"]` | `["src"]` (unchanged for source gate) | Must cover all authored source files |
| `exclude` | `["**/__pycache__", "tests", "htmlcov"]` | `["**/__pycache__", "htmlcov"]` (remove `"tests"`) | Tests must NOT be excluded for test gate |
| `reportMissingTypeStubs` | `false` | `false` (unchanged) | Vendor stubs not required |
| `reportMissingImports` | `"warning"` | `"warning"` (unchanged) | Keeps optional dependency imports as warnings |

**State Transition**: The backend test type-check gate uses a separate pyright invocation with `tests/` included. This can be achieved via:
- Option A: A separate `pyrightconfig.test.json` at `solune/backend/` root
- Option B: CLI override `uv run pyright src tests` for the combined gate, keeping the existing config for source-only gate

**Recommended**: Option B — simpler, no new config file. CI runs `pyright src` (source gate) and `pyright src tests` (combined gate with tests) as separate steps.

### 2. Frontend TypeScript Test Configuration

**Entity**: `solune/frontend/tsconfig.test.json` (NEW FILE)

```jsonc
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "types": ["vite/client", "vitest/globals"],
    "noUnusedLocals": false,
    "noUnusedParameters": false
  },
  "include": ["src"],
  "exclude": []
}
```

| Field | Value | Rationale |
|-------|-------|-----------|
| `extends` | `"./tsconfig.json"` | Inherits all strict settings from production config |
| `types` | `["vite/client", "vitest/globals"]` | Adds Vitest global types needed by test files |
| `noUnusedLocals` | `false` | Test files may have setup variables not directly referenced |
| `noUnusedParameters` | `false` | Test callbacks often ignore parameters |
| `include` | `["src"]` | Covers entire src including test files |
| `exclude` | `[]` | Removes all test file exclusions from base config |

**Relationship**: Extends `tsconfig.json` → inherits `strict: true`, path aliases, and all compiler options.

### 3. Frontend ESLint Configuration Updates

**Entity**: `solune/frontend/eslint.config.js`

| Rule | Current | Target | Scope |
|------|---------|--------|-------|
| `@typescript-eslint/ban-ts-comment` | (default) | `error` with `ts-expect-error: allow-with-description` | All files |
| `@typescript-eslint/no-explicit-any` | (inherited from strict) | `error` (explicit) | All files |

**Validation**: After Phase 5, running `npm run lint` must exit cleanly with zero errors.

### 4. CI Workflow Configuration Updates

**Entity**: `.github/workflows/ci.yml`

New steps to add:

| Job | Step Name | Command | Fail Behaviour |
|-----|-----------|---------|----------------|
| Backend | Type Check Backend Tests | `uv run pyright tests` | Blocks merge |
| Frontend | Type Check Frontend Tests | `npx tsc --noEmit -p tsconfig.test.json` | Blocks merge |

### 5. Pre-Commit Configuration Updates

**Entity**: `solune/.pre-commit-config.yaml`

New hooks to add:

| Hook ID | Command | Stage | File Pattern |
|---------|---------|-------|-------------|
| `backend-pyright-tests` | `cd solune/backend && pyright tests` | commit | `^solune/backend/.*\.py$` |
| `frontend-typecheck-tests` | `cd solune/frontend && npx tsc --noEmit -p tsconfig.test.json` | commit | `^solune/frontend/.*\.(ts\|tsx)$` |

### 6. Pre-Commit Script Updates

**Entity**: `solune/scripts/pre-commit`

Add test type-check steps after existing type-check steps for both backend and frontend sections.

## Typed Helper Patterns (New)

### Backend: `RequestIdLogRecord` Protocol

```python
from typing import Protocol

class RequestIdLogRecord(Protocol):
    """LogRecord with request_id attribute set by RequestIdFilter."""
    request_id: str
    # All other LogRecord attributes inherited
```

**Used by**: `logging_utils.py` filter and `test_logging_utils.py` assertions.

### Backend: Typed Test Fakes

```python
@dataclass
class FakeL1Cache:
    """Typed replacement for loosely-typed cache fake in metadata tests."""
    data: dict[str, Any]
    set_calls: list[tuple[str, Any, float]]
    deleted: list[str]
```

**Used by**: `test_metadata_service.py` — replaces `# type: ignore[attr-defined]` on 8 lines.

### Frontend: Extended `createMockApi()`

The existing `createMockApi()` in `src/test/setup.ts` covers: `authApi`, `projectsApi`, `tasksApi`, `chatApi`, `boardApi`, `settingsApi`, `mcpApi`.

**Needs extension for**: `activityApi`, `agentsApi`, `agentToolsApi`, `appsApi`, `choresApi`, `cleanupApi`, `metadataApi`, `modelsApi`, `pipelinesApi`, `toolsApi`, `workflowApi`.

This eliminates ~34 `as unknown as` casts across hook test files.

## Relationships

```text
tsconfig.json ──extends──▶ tsconfig.test.json
                              │
                              ├── Covers: src/test/setup.ts
                              ├── Covers: src/**/*.test.ts
                              └── Covers: src/**/*.test.tsx

pyproject.toml
  └── [tool.pyright]
        ├── pyright src     (source gate — existing)
        └── pyright tests   (test gate — NEW)

eslint.config.js
  └── Rules tightened to flag new suppressions

ci.yml
  ├── Backend source type-check  (existing)
  ├── Backend test type-check    (NEW)
  ├── Frontend source type-check (existing)
  └── Frontend test type-check   (NEW)
```
