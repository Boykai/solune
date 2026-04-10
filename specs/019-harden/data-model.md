# Data Model: #Harden

**Feature**: Harden Solune reliability, code quality, CI/CD, observability, DX
**Date**: 2026-04-10

## Overview

The #Harden initiative is a **non-feature** hardening effort. It introduces no
new entities, tables, or API endpoints. All changes operate on existing data
structures and service internals.

## Affected Entities

### E1: AgentPreview (Pydantic model)

**File**: `solune/backend/src/services/agents/service.py`
**Change**: Tighten tool validation in `_extract_agent_preview()`.

| Field | Type | Validation Change |
|-------|------|-------------------|
| `tools` | `list[str]` | Add per-element `isinstance(item, str) and item.strip()` guard before construction |

**State transitions**: None changed.

### E2: Stryker Config (build config)

**Files**: `solune/frontend/stryker*.config.mjs` (5 files → 1 file)
**Change**: Consolidate into single config with target selection.

| Property | Current | Target |
|----------|---------|--------|
| `mutate` | Hard-coded per file | Dynamic via `STRYKER_TARGET` env var |
| `reporters` | Duplicated | Single definition |
| `thresholds` | Duplicated | Single definition |

### E3: Coverage Thresholds (test config)

**File**: `solune/backend/pyproject.toml`

| Setting | Current | Target |
|---------|---------|--------|
| `fail_under` | 75 | 80 |

**File**: `solune/frontend/vitest.config.ts`

| Setting | Current | Target |
|---------|---------|--------|
| `statements` | 50 | 60 |
| `branches` | 44 | 52 |
| `functions` | 41 | 50 |
| `lines` | 50 | 60 |

### E4: Module-Level Singletons

**Files**:

- `solune/backend/src/services/github_projects/service.py` (line 493)
- `solune/backend/src/services/github_projects/agents.py` (line 413)

**Change**: Replace direct singleton import with accessor function pattern.

```python
# Before
github_projects_service = GitHubProjectsService()

# After
_github_projects_service: GitHubProjectsService | None = None

def get_github_projects_service(app_state: Any | None = None) -> GitHubProjectsService:
    """Prefer app.state in request contexts; fall back to module singleton."""
    if app_state and hasattr(app_state, 'github_projects_service'):
        return app_state.github_projects_service
    global _github_projects_service
    if _github_projects_service is None:
        _github_projects_service = GitHubProjectsService()
    return _github_projects_service
```

### E5: Dependency Versions (pyproject.toml)

**File**: `solune/backend/pyproject.toml`

| Dependency | Current Spec | Target Spec |
|------------|-------------|-------------|
| `github-copilot-sdk` | `>=0.1.30,<1` | `>=1.0.17,<2` (v2 upgrade) |
| `azure-ai-inference` | `>=1.0.0b9,<2` | Latest 1.x beta or GA |
| `agent-framework-core` | `>=1.0.0b1` | Latest 1.x |
| `agent-framework-azure-ai` | `>=1.0.0b1` | Latest 1.x |
| `agent-framework-github-copilot` | `>=1.0.0b1` | Latest 1.x |
| `opentelemetry-instrumentation-*` | `>=0.54b0,<1` | Latest 0.x |

## Relationships

```text
AgentPreview ──uses──> _extract_agent_preview() ──creates──> AgentPreview
                                                              │
                                                              └──> tools: list[str] (tightened validation)

GitHubProjectsService ──singleton──> service.py:493
                       ──singleton──> agents.py:413
                       ──refactor──> get_github_projects_service() accessor

Coverage Thresholds ──backend──> pyproject.toml:fail_under
                    ──frontend──> vitest.config.ts:thresholds

Stryker Configs ──5 files──> 1 unified config
```

## Migration Notes

- No database schema migrations required
- No API contract changes
- All changes are backward-compatible within the monorepo
- Dependency upgrades require isolated CI validation per package
