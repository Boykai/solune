# Implementation Plan: Harden Phase 3 — Code Quality & Tech Debt

**Branch**: `copilot/harden-phase-3-implementation-plan` | **Date**: 2026-04-10 | **Spec**: [#1253](https://github.com/Boykai/solune/issues/1253)
**Input**: Parent issue #1253 — Harden Phase 3: reliability, code quality, CI/CD, observability, and developer experience. No new features; making what exists better.

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Phase 3 is a hardening sprint focused on four workstreams that reduce tech debt, improve maintainability, and prevent regressions — with zero feature changes:

1. **3.1 — Singleton DI Refactor**: Remove module-level singletons tagged `TODO(018-codebase-audit-refactor)` in `service.py:479` and `agents.py:399`. Introduce a `get_github_service()` accessor pattern so request-context code pulls from `app.state` and non-request code (background tasks, polling, orchestrator) uses a controlled module-level fallback.
2. **3.2 — Pre-release Dependency Upgrades**: Upgrade `azure-ai-inference` (1.0.0b9→GA), `agent-framework-*` (1.0.0b1→stable), `opentelemetry-instrumentation-*` (0.54b0→stable), and `github-copilot-sdk` (v0.x→v2/copilot-sdk≥1.0.17).
3. **3.3 — Stryker Config Consolidation**: Replace 4 separate shard config files with a single unified `stryker.config.mjs` driven by a `STRYKER_SHARD` environment variable, reducing config drift and simplifying CI.
4. **3.4 — Plan-Mode Chat History Fix**: Already resolved — both plan-mode endpoints (`POST /messages/plan` and `POST /messages/plan/stream`) correctly persist user messages **after** `get_chat_agent_service()` succeeds. Verification-only workstream.

## Technical Context

**Language/Version**: Python ≥3.12 (backend), TypeScript ~6.0.2 (frontend)
**Primary Dependencies**: FastAPI, githubkit, azure-ai-inference, agent-framework-core/azure-ai/github-copilot, github-copilot-sdk, opentelemetry-instrumentation-*, @stryker-mutator/core 9.6.x
**Storage**: SQLite via aiosqlite (no schema changes)
**Testing**: pytest 8.x + pytest-asyncio (backend), Vitest 4.1.3 + @testing-library/react (frontend), Stryker 9.6.x (mutation)
**Target Platform**: Linux server (backend), Modern browsers (frontend)
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: N/A — refactoring-only; no runtime performance changes expected
**Constraints**: Zero breaking changes to public API; all existing tests must continue passing; coverage thresholds maintained (backend ≥75%, frontend ≥50% statements)
**Scale/Scope**: ~27 files affected by singleton refactor; 7 dependency lines in pyproject.toml; 5 Stryker config files → 1; 2 plan-mode endpoints (verification only)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Parent issue #1253 provides clear scope with 4 numbered workstreams and explicit file references |
| II. Template-Driven Workflow | ✅ PASS | Using canonical plan template; plan.md at repository root per branch convention |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan phase produces plan.md + artifacts; handoff to tasks phase for implementation |
| IV. Test Optionality | ✅ PASS | Existing tests must pass; new tests only where singleton accessor pattern needs coverage |
| V. Simplicity and DRY | ✅ PASS | Each workstream simplifies existing code: fewer singletons, fewer configs, cleaner DI, upgraded deps |

**Gate Result**: PASS — no violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
plan.md              # This file (repository root, /speckit.plan output)
research.md          # Phase 0 output — consolidated research findings
data-model.md        # Phase 1 output — affected data models and state shapes
quickstart.md        # Phase 1 output — developer getting-started for this feature
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── pyproject.toml                          # 3.2: dependency version bumps
│   ├── src/
│   │   ├── dependencies.py                     # 3.1: accessor pattern hub
│   │   ├── main.py                             # 3.1: app.state registration
│   │   ├── services/
│   │   │   ├── github_projects/
│   │   │   │   ├── __init__.py                 # 3.1: re-export accessor
│   │   │   │   ├── service.py                  # 3.1: remove singleton (line 479)
│   │   │   │   └── agents.py                   # 3.1: remove singleton (line 399)
│   │   │   ├── chat_agent.py                   # 3.4: verification only
│   │   │   ├── copilot_polling/                # 3.1: import migration
│   │   │   ├── signal_bridge.py                # 3.1: import migration
│   │   │   ├── signal_chat.py                  # 3.1: import migration
│   │   │   ├── workflow_orchestrator/          # 3.1: import migration
│   │   │   ├── agents/service.py               # 3.1: import migration
│   │   │   ├── agent_creator.py                # 3.1: import migration
│   │   │   ├── github_commit_workflow.py       # 3.1: import migration
│   │   │   ├── metadata_service.py             # 3.1: import migration
│   │   │   └── tools/service.py                # 3.1: import migration
│   │   └── api/
│   │       ├── chat.py                         # 3.1: use DI accessor; 3.4: verified
│   │       ├── board.py                        # 3.1: use DI accessor
│   │       ├── chores.py                       # 3.1: use DI accessor
│   │       ├── pipelines.py                    # 3.1: use DI accessor
│   │       ├── projects.py                     # 3.1: use DI accessor
│   │       ├── tasks.py                        # 3.1: use DI accessor
│   │       ├── tools.py                        # 3.1: use DI accessor
│   │       ├── webhooks.py                     # 3.1: use DI accessor
│   │       ├── workflow.py                     # 3.1: use DI accessor
│   │       ├── metadata.py                     # 3.1: use DI accessor
│   │       └── agents.py                       # 3.1: use DI accessor
│   └── tests/                                  # 3.1: update mocks for accessor
└── frontend/
    ├── stryker.config.mjs                      # 3.3: unified config with shard support
    ├── stryker-hooks-board.config.mjs          # 3.3: DELETE
    ├── stryker-hooks-data.config.mjs           # 3.3: DELETE
    ├── stryker-hooks-general.config.mjs        # 3.3: DELETE
    ├── stryker-lib.config.mjs                  # 3.3: DELETE
    └── package.json                            # 3.3: update npm scripts
```

**Structure Decision**: Existing monorepo web application layout (backend/ + frontend/ under solune/). No new directories; changes are exclusively modifications to existing files plus deletion of 4 Stryker shard configs.

## Complexity Tracking

> No constitution violations — all workstreams simplify existing code.

| Aspect | Current | After | Simplification |
|--------|---------|-------|---------------|
| Module-level singletons | 1 tagged for removal (2 TODO blocks in same service) | 0 tagged; accessor pattern consistent | DI is centralized in dependencies.py |
| Stryker config files | 5 (1 base + 4 shards) | 1 (unified with env-var sharding) | Single source of truth for mutation config |
| Pre-release deps | 7 packages pinned to beta/preview | 0 pre-release (all GA or v2) | Removes pip `--pre` / `allow-prereleases` requirement |
| Orphaned chat messages | Fixed (verified) | N/A | No code change needed |

---

## Workstream Details

### 3.1 — Remove Module-Level Singletons (DI Refactor)

#### Current State

Two identical `TODO(018-codebase-audit-refactor)` blocks exist:

- `solune/backend/src/services/github_projects/service.py:479–493` — `github_projects_service = GitHubProjectsService()`
- `solune/backend/src/services/github_projects/agents.py:399–413` — same TODO block (agents.py is a mixin; the singleton is the same `GitHubProjectsService` instance)

The singleton is imported directly by **27 files** across three contexts:

| Context | Files | Can Use app.state? |
|---------|-------|--------------------|
| API routes | 11 (board, chat, chores, pipelines, projects, tasks, tools, webhooks, workflow, metadata, agents) | ✅ Yes — `Request` available |
| Background / non-request | 6 (signal_bridge, signal_chat, copilot_polling/*, workflow_orchestrator) | ❌ No — no HTTP request |
| Service layer (mixed) | 6 (agents/service, agent_creator, agent_mcp_sync, github_commit_workflow, metadata_service, tools/service) | ⚠️ Sometimes |
| Framework | 4 (dependencies.py, main.py, utils.py, constants.py) | N/A |

#### DI Accessor Pattern (already exists in dependencies.py)

```python
def get_github_service(request: Request) -> GitHubProjectsService:
    svc = getattr(request.app.state, "github_service", None)
    if svc is not None:
        return svc
    from src.services.github_projects import github_projects_service
    return github_projects_service
```

#### Proposed Refactor

1. **Keep** the module-level singleton but remove the deferred-TODO comments — the accessor pattern makes it safe.
2. **Migrate all 11 API route files** to use `get_github_service(request)` via FastAPI `Depends()` injection instead of direct singleton import.
3. **Non-request files** (background tasks, polling, orchestrator) continue importing the singleton directly — this is the intended fallback path in `get_github_service()`.
4. **Service-layer files** called from both contexts receive the service as a parameter when possible, falling back to direct import otherwise.
5. **Update `__init__.py`** to also export the accessor function.
6. **Update test mocks** to patch the accessor or the singleton, depending on what is being tested.

#### Risk Assessment

- **Low risk**: The accessor already exists and is used. Migration is a mechanical refactor of import statements.
- **Test impact**: Any test that patches `src.services.github_projects.github_projects_service` may need updating to patch the accessor.
- **Rollback**: Revert import changes; singleton still works as-is.

---

### 3.2 — Upgrade Pre-release Dependencies

#### Current Versions (from pyproject.toml)

| Package | Current Pin | Target | Notes |
|---------|-------------|--------|-------|
| `github-copilot-sdk` | `>=0.1.30,<1` | `copilot-sdk>=1.0.17` | v2 upgrade — package name change (pyproject.toml:16 comment) |
| `azure-ai-inference` | `>=1.0.0b9,<2` | `>=1.0.0,<2` (GA when available) | Pre-release beta 9 |
| `agent-framework-core` | `>=1.0.0b1` | `>=1.0.0` (GA when available) | Pre-release beta 1 |
| `agent-framework-azure-ai` | `>=1.0.0b1` | `>=1.0.0` (GA when available) | Pre-release beta 1 |
| `agent-framework-github-copilot` | `>=1.0.0b1` | `>=1.0.0` (GA when available) | Pre-release beta 1 |
| `opentelemetry-instrumentation-fastapi` | `>=0.54b0,<1` | `>=0.55b0,<1` or GA | Pre-release |
| `opentelemetry-instrumentation-httpx` | `>=0.54b0,<1` | `>=0.55b0,<1` or GA | Pre-release |
| `opentelemetry-instrumentation-sqlite3` | `>=0.54b0,<1` | `>=0.55b0,<1` or GA | Pre-release |

#### Upgrade Strategy

1. **Research GA availability** for each package via PyPI at implementation time.
2. **Package rename**: `github-copilot-sdk` → `copilot-sdk` requires updating all import statements that reference the old package.
3. **Run full test suite** after each dependency upgrade to catch breaking changes.
4. **Update `allow-prereleases`** setting in pyproject.toml once all packages reach GA.
5. **agent-framework-*** packages: Check for API breaking changes between b1 and stable (method signatures, async patterns).

#### Risk Assessment

- **Medium risk**: Pre-release → GA may include breaking API changes.
- **github-copilot-sdk v2**: Highest risk — package rename means all import paths change. Requires audit of all files importing from the old package.
- **Mitigation**: Upgrade one package at a time; run tests after each. Pin exact versions initially, then relax to range pins.

---

### 3.3 — Consolidate Stryker Mutation Configs

#### Current State

5 config files in `solune/frontend/`:

| File | Purpose | Mutate Target |
|------|---------|---------------|
| `stryker.config.mjs` | Base config (also default `test:mutate`) | `src/hooks/**/*.ts`, `src/lib/**/*.ts` |
| `stryker-hooks-board.config.mjs` | Board hooks shard | 5 specific hook files |
| `stryker-hooks-data.config.mjs` | Data hooks shard | 7 specific hook files |
| `stryker-hooks-general.config.mjs` | General hooks shard | All hooks minus board + data |
| `stryker-lib.config.mjs` | Library utilities shard | `src/lib/**/*.ts` |

All 4 shard configs extend the base with `...baseConfig` and override only `mutate` and `htmlReporter.fileName`.

**CI**: `.github/workflows/mutation-testing.yml` runs a 4-job matrix: `hooks-board`, `hooks-data`, `hooks-general`, `lib`.

#### Proposed Consolidation

Replace the 4 shard configs with environment-variable–driven sharding in the base config:

```javascript
// stryker.config.mjs (unified)
const shards = {
  'hooks-board': {
    mutate: ['src/hooks/useAdaptivePolling.ts', 'src/hooks/useBoardProjection.ts',
             'src/hooks/useBoardRefresh.ts', 'src/hooks/useProjectBoard.ts',
             'src/hooks/useRealTimeSync.ts'],
    report: 'reports/mutation/hooks-board/mutation-report.html',
  },
  'hooks-data': {
    mutate: ['src/hooks/useProjects.ts', 'src/hooks/useChat.ts',
             'src/hooks/useChatHistory.ts', 'src/hooks/useCommands.ts',
             'src/hooks/useWorkflow.ts', 'src/hooks/useSettingsForm.ts',
             'src/hooks/useAuth.ts'],
    report: 'reports/mutation/hooks-data/mutation-report.html',
  },
  'hooks-general': {
    mutate: ['src/hooks/**/*.ts', '!src/hooks/**/*.test.ts',
             '!src/hooks/**/*.property.test.ts',
             /* exclude board + data hooks */],
    report: 'reports/mutation/hooks-general/mutation-report.html',
  },
  'lib': {
    mutate: ['src/lib/**/*.ts', '!src/lib/**/*.test.ts',
             '!src/lib/**/*.property.test.ts'],
    report: 'reports/mutation/lib/mutation-report.html',
  },
};
const shard = process.env.STRYKER_SHARD;
```

#### Updates Required

1. **`stryker.config.mjs`** — Add shard map and `STRYKER_SHARD` env-var support.
2. **Delete** `stryker-hooks-board.config.mjs`, `stryker-hooks-data.config.mjs`, `stryker-hooks-general.config.mjs`, `stryker-lib.config.mjs`.
3. **`package.json`** — Update npm scripts:
   - `"test:mutate:hooks-board": "STRYKER_SHARD=hooks-board stryker run"`
   - `"test:mutate:hooks-data": "STRYKER_SHARD=hooks-data stryker run"`
   - etc.
4. **`.github/workflows/mutation-testing.yml`** — Update matrix job to set `STRYKER_SHARD` env var instead of `-c` flag.
5. **`docs/testing.md`** — Update Stryker documentation to reflect single config with shard env var.

#### Risk Assessment

- **Low risk**: Config consolidation is purely structural; no mutation logic changes.
- **Verification**: Run each shard via the new mechanism; compare mutant counts to ensure identical coverage.

---

### 3.4 — Fix Plan-Mode Orphaned Chat History

#### Current State — ALREADY RESOLVED

Research confirms both plan-mode endpoints correctly persist user messages **after** the `get_chat_agent_service()` check:

| Endpoint | Service Check | User Message Persist | Status |
|----------|---------------|----------------------|--------|
| `POST /messages/plan` (line 2010–2024) | Lines 2010–2016 (hard fail) | Lines 2018–2024 (after) | ✅ RESOLVED |
| `POST /messages/plan/stream` (line 2083–2097) | Lines 2083–2089 (hard fail) | Lines 2091–2097 (after) | ✅ RESOLVED |

**Regular chat endpoints** (`POST /messages`) still persist user messages before the service check (line 1049–1055), but this is out of scope for task 3.4 which specifically targets plan-mode.

#### Action Required

- **Verification only**: Write a targeted test (or confirm existing test) that `send_plan_message` returns 503 without persisting a user message when `get_chat_agent_service()` raises.
- **No code changes** needed for the plan-mode endpoints.
- **Recommendation** (future work): Apply the same pattern to the regular `send_message` endpoint to prevent orphaned messages there too.

---

## Dependency Graph

```text
3.4 (verification) ──────────────────────────────────── can run anytime
3.3 (Stryker consolidation) ─────────────────────────── can run anytime (frontend-only)
3.1 (singleton DI refactor) ─────────────────────────── must complete before 3.2
3.2 (dependency upgrades) ───── depends on 3.1 ──────── SDK rename may touch same files
```

**Recommended execution order**: 3.4 → 3.3 → 3.1 → 3.2

- 3.4 is verification-only and fast.
- 3.3 is frontend-only and independent.
- 3.1 must precede 3.2 because the copilot-sdk v2 rename will touch import paths that 3.1 also modifies; doing 3.1 first avoids merge conflicts.
- 3.2 is last because it has the highest risk and benefits from a clean baseline.

---

## Post-Design Constitution Re-Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | All 4 workstreams mapped to explicit issue requirements |
| II. Template-Driven Workflow | ✅ PASS | plan.md follows canonical template structure |
| III. Agent-Orchestrated Execution | ✅ PASS | Clear handoff boundaries for each workstream |
| IV. Test Optionality | ✅ PASS | Tests only where needed (3.1 accessor tests, 3.4 verification) |
| V. Simplicity and DRY | ✅ PASS | Every workstream reduces complexity: fewer configs, cleaner DI, fewer pre-release pins |

**Gate Result**: ✅ ALL PASS — ready for `/speckit.tasks` phase
