# Implementation Plan: #Harden

**Branch**: `copilot/speckit-plan-harden-implementation` | **Date**: 2026-04-10 | **Spec**: [#1208](https://github.com/Boykai/solune/issues/1208)
**Input**: Parent issue #1208 — Harden Solune's reliability, code quality, CI/CD, observability, and developer experience.

## Summary

Harden the Solune monorepo (Python/FastAPI backend + React/TypeScript frontend) without adding new features. The initiative spans three phases: critical bug fixes, test coverage improvement, and code quality / tech debt reduction. Research (Phase 0) confirmed that **3 of 4 bugs are already resolved** in prior work — the remaining work focuses on one residual validation gap, ~91 untested modules/components, property-based test expansion, a11y integration, singleton refactoring, dependency upgrades, and Stryker config consolidation.

## Technical Context

**Language/Version**: Python ≥3.12 (backend), TypeScript ~6.0.2 (frontend)
**Primary Dependencies**: FastAPI, pytest 8.x, pytest-asyncio, pytest-cov, hypothesis, Vitest 4.1.3, @testing-library/react 16.x, Playwright 1.59, React 19.2.0
**Storage**: SQLite (aiosqlite) — no schema changes
**Testing**: pytest (backend), Vitest + Playwright (frontend), Stryker (mutation), hypothesis (property-based)
**Target Platform**: Linux server (backend), Modern browsers (frontend)
**Project Type**: Web application (backend + frontend monorepo)
**Performance Goals**: No regressions — maintain existing response times
**Constraints**: All CI jobs must pass; no breaking API changes
**Scale/Scope**: 185 backend source files, 275 frontend source files, 19 E2E specs

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Specification-First Development ✅

The parent issue #1208 serves as the specification with prioritized phases (P1 bug fixes → P2 coverage → P3 tech debt). Each phase item has clear acceptance criteria. No formal `spec.md` with user stories because this is a non-feature hardening effort — the issue description itself provides the structured requirements.

**Justified deviation**: No `spec.md` file created. The parent issue serves as the authoritative specification for a hardening-only initiative with no user-facing feature changes.

### II. Template-Driven Workflow ✅

This plan follows the canonical `plan-template.md`. Research, data model, contracts, and quickstart artifacts are generated per the template workflow.

### III. Agent-Orchestrated Execution ✅

The `speckit.plan` agent produces this plan. `speckit.tasks` will decompose into executable tasks. `speckit.implement` will execute. Each agent operates on the outputs of the previous phase.

### IV. Test Optionality with Clarity ✅

Tests are a **primary deliverable** in Phase 2 (coverage improvement). Phase 1 bug fixes include targeted regression tests. Phase 3 tech debt changes require tests for refactored code.

### V. Simplicity and DRY ✅

All changes favor simple, direct fixes:

- Bug 1.3: One additional guard clause (2 lines)
- Singleton refactor: Accessor function pattern (well-documented in existing TODO)
- Stryker consolidation: Reduces 5 config files to 1
- No premature abstractions introduced

### Post-Design Re-Check ✅

All constitution principles satisfied. No violations requiring justification in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/019-harden/
├── plan.md              # This file
├── research.md          # Phase 0 output — 10 research decisions
├── data-model.md        # Phase 1 output — affected entities
├── quickstart.md        # Phase 1 output — getting started
├── contracts/
│   └── README.md        # Phase 1 output — no new APIs
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── src/
│   │   ├── api/chat.py                          # Bug 3.4 (already fixed)
│   │   ├── models/agents.py                     # AgentStatus enum (unchanged)
│   │   ├── services/
│   │   │   ├── agents/service.py                # Bug 1.2 (fixed), 1.3 (needs fix), 3.1 (TODO)
│   │   │   ├── chat_agent.py                    # get_chat_agent_service (unchanged)
│   │   │   ├── github_projects/
│   │   │   │   ├── service.py                   # 3.1 singleton (TODO)
│   │   │   │   └── agents.py                    # 3.1 singleton (TODO)
│   │   │   └── pipeline_state_store.py          # Bug 1.1 (already fixed)
│   │   └── utils.py                             # BoundedDict (unchanged)
│   ├── tests/
│   │   ├── unit/                                # New tests for ~30 modules
│   │   └── property/                            # Expanded property tests
│   └── pyproject.toml                           # Coverage threshold 75→80
├── frontend/
│   ├── src/                                     # New tests for ~61 components
│   ├── e2e/                                     # Axe-core a11y integration
│   ├── vitest.config.ts                         # Coverage thresholds raised
│   ├── stryker.config.mjs                       # Unified (consolidate 5→1)
│   ├── stryker-hooks-board.config.mjs           # REMOVE
│   ├── stryker-hooks-data.config.mjs            # REMOVE
│   ├── stryker-hooks-general.config.mjs         # REMOVE
│   └── stryker-lib.config.mjs                   # REMOVE
└── docker-compose.yml                           # Unchanged
```

**Structure Decision**: Existing web application structure (backend + frontend monorepo). No new directories or structural changes needed.

## Phase 1 — Critical Bug Fixes

### 1.1 Fix `_project_launch_locks` Memory Leak ✅ ALREADY RESOLVED

**Status**: No action required.
**Evidence**: `pipeline_state_store.py:40` uses `BoundedDict(maxlen=10_000)` with LRU-like `.touch()` refresh at line 70. See research.md R1.

### 1.2 Fix `update_agent()` Lifecycle Status ✅ ALREADY RESOLVED

**Status**: No action required.
**Evidence**: All three SQL persistence paths in `update_agent()` set `lifecycle_status = AgentStatus.PENDING_PR.value` (lines 1246, 1279, 1311). Returned `Agent` object sets `status=AgentStatus.PENDING_PR` (line 1326). See research.md R2.

### 1.3 Fix `_extract_agent_preview()` — Malformed Config Validation ⚠️ NEEDS FIX

**Current state**: Guards against `tools: "read"` (non-list) but does not validate individual list elements.
**Fix**: Add per-element validation in `_extract_agent_preview()`:

```python
tools = config.get("tools", [])
if not isinstance(tools, list):
    return None
if not all(isinstance(t, str) and t.strip() for t in tools):
    return None
```

**Files changed**: `solune/backend/src/services/agents/service.py` (2 lines added after line 1472)
**Test**: Add test case in `tests/unit/test_agents_service.py` with malformed tool entries (int, None, empty string, dict).
**Dependencies**: None.

## Phase 2 — Test Coverage Improvement

### 2.1 Backend Coverage: 75% → 80%

**Target**: ~30 untested modules across 5 categories.

| Category | Modules | Priority | Estimated Tests |
|----------|---------|----------|-----------------|
| Prompt templates (`prompts/`) | 6 | P2 | 12–18 |
| Copilot polling internals | 4 | P2 | 8–12 |
| MCP server tools | 8 | P1 | 16–24 |
| Chores service internals | 4 | P2 | 8–12 |
| Middleware (`request_id.py`) | 1 | P3 | 2–4 |

**Config change**: Update `pyproject.toml` line 137: `fail_under = 80`
**Dependencies**: Phase 1 bug fixes completed first (to avoid test noise).

### 2.2 Frontend Coverage: Raise Thresholds

**Target**: ~61 untested components across 7 categories.

| Category | Components | Priority | Estimated Tests |
|----------|-----------|----------|-----------------|
| Chores | 13 | P1 | 26–39 |
| Agents | 10 | P1 | 20–30 |
| Tools | 9 | P2 | 18–27 |
| UI primitives | 7 | P2 | 14–21 |
| Settings | 4 | P2 | 8–12 |
| Pipeline | 4 | P3 | 8–12 |
| Chat | 4 | P3 | 8–12 |

**Config change**: Update `vitest.config.ts` thresholds:

```typescript
thresholds: {
    statements: 60,
    branches: 52,
    functions: 50,
    lines: 60,
}
```

**Dependencies**: None (can run in parallel with 2.1).

### 2.3 Property-Based Testing Expansion

**Current**: 7 backend property test files (`tests/property/`), 6 frontend property test files (`*.property.test.ts`).

**New property tests to add**:

| Category | File | Tests |
|----------|------|-------|
| Backend — Round-trip serialization | `test_model_roundtrips.py` (expand) | Agent, Pipeline, Chat models |
| Backend — API validation edge cases | `test_api_validation.py` (new) | Boundary inputs for all endpoints |
| Backend — Migration idempotency | `test_migration_idempotency.py` (new) | Run migrations up/down repeatedly |
| Frontend — Component prop fuzzing | New `*.property.test.ts` files | Agent, Pipeline, Settings components |

**Dependencies**: 2.1 and 2.2 should be mostly complete to avoid merge conflicts.

### 2.4 Axe-Core Playwright A11y Integration

**Current**: `@axe-core/playwright` imported in 2 of 19 E2E specs (ui.spec.ts, protected-routes.spec.ts).

**Target E2E specs for a11y integration**:

| Spec File | A11y Check |
|-----------|-----------|
| `auth.spec.ts` | Login/logout page a11y |
| `board-navigation.spec.ts` | Board view a11y |
| `chat-interaction.spec.ts` | Chat interface a11y |
| `settings-flow.spec.ts` | Settings pages a11y |

**Pattern** (established in existing specs):

```typescript
import AxeBuilder from '@axe-core/playwright';

test('should pass axe-core accessibility audit', async ({ page }) => {
    const results = await new AxeBuilder({ page })
        .analyze();
    expect(results.violations).toEqual([]);
});
```

**Dependencies**: None (can run in parallel with other Phase 2 work).

## Phase 3 — Code Quality & Tech Debt

### 3.1 Remove Module-Level Singletons

**Files**: `service.py:479–493`, `agents.py:399–413`
**Approach**: See research.md R4 and data-model.md E4.

**Steps**:

1. Audit all 17+ files importing the singletons directly
2. Introduce `get_github_projects_service()` accessor function
3. Update request-context callers to pass `request.app.state`
4. Update non-request callers to use accessor without app_state (fallback)
5. Update test mocks to use the accessor
6. Remove the direct singleton exports

**Risk**: Medium — requires touching 17+ files across background tasks, signal bridge, orchestrator.
**Dependencies**: Phase 1 and Phase 2 complete (clean CI baseline).

### 3.2 Upgrade Pre-Release Dependencies

**Approach**: Serial upgrades with isolated CI validation. See research.md R5.

**Execution order** (lowest to highest risk):

1. OpenTelemetry instrumentation packages (3 packages — low risk)
2. `azure-ai-inference` (medium risk)
3. `agent-framework-*` (3 packages — medium risk)
4. `github-copilot-sdk` v2 upgrade (high risk — major version)

Each upgrade is a separate commit with full CI pass.
**Dependencies**: Phase 1 and Phase 2 complete (stable test suite for regression detection).

### 3.3 Consolidate Stryker Configs

**Current**: 5 config files with ~80% duplication.
**Target**: 1 unified `stryker.config.mjs` with `STRYKER_TARGET` env var.

**Steps**:

1. Define target profiles: `all`, `hooks-board`, `hooks-data`, `hooks-general`, `lib`
2. Merge all configs into single file with conditional `mutate` patterns
3. Update CI workflow and package.json scripts
4. Remove 4 redundant config files
5. Update documentation

**Dependencies**: None (can start any time).

### 3.4 Fix Plan-Mode Orphaned Chat History ✅ ALREADY RESOLVED

**Status**: No action required.
**Evidence**: Both plan-mode endpoints persist user messages after service availability check (lines 2018–2024 and 2091–2097). See research.md R7.

## Execution Order & Dependencies

```text
Phase 1 (Bug Fixes)
  └── 1.3 _extract_agent_preview fix ─────────────────────┐
                                                           │
Phase 2 (Test Coverage) — starts after 1.3                 │
  ├── 2.1 Backend coverage (parallel) ────────────────────┤│
  ├── 2.2 Frontend coverage (parallel) ───────────────────┤│
  ├── 2.3 Property tests (after 2.1/2.2 mostly done) ────┤│
  └── 2.4 Axe-core a11y (parallel) ──────────────────────┤│
                                                           ││
Phase 3 (Code Quality) — starts after Phase 2              ││
  ├── 3.1 Singleton refactor ─────────────────────────────┤│
  ├── 3.2 Dependency upgrades (serial, after 3.1) ────────┘│
  └── 3.3 Stryker consolidation (parallel, any time) ──────┘
```

## Risk Assessment

| Item | Risk | Mitigation |
|------|------|-----------|
| 3.1 Singleton refactor | Medium | Audit all 17+ consumers first; accessor pattern preserves backward compat |
| 3.2 Copilot SDK v2 upgrade | High | Isolated commit; full CI pass; rollback plan |
| 2.1/2.2 Coverage threshold increases | Low | Incremental threshold bumps; verify coverage first |
| 3.3 Stryker consolidation | Low | Existing patterns well-understood; CI validates |

## Complexity Tracking

> No Constitution Check violations. No complexity justifications needed.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
