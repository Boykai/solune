# Implementation Plan: Harden Phase 2

**Branch**: `copilot/speckit-plan-harden-phase-2` | **Date**: 2026-04-10 | **Spec**: [#1240](https://github.com/Boykai/solune/issues/1240)
**Input**: Parent issue #1240 — Harden Phase 2 (Test Coverage Improvement)

## Summary

Improve Solune's test coverage across four workstreams: (2.1) deepen backend unit tests to raise
`fail_under` from 75% to 80%, (2.2) add ~69 missing frontend component tests to raise
statements 50→60%, branches 44→52%, functions 41→50%, (2.3) expand property-based testing with
round-trip serialization, API validation edge cases, and migration idempotency tests, and
(2.4) integrate @axe-core/playwright a11y audits into auth, board, chat, and settings E2E flows.
No new features — only making what exists more reliable.

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript ~6.0 (frontend)
**Primary Dependencies**: FastAPI, pytest 9.0+, Hypothesis 6.131+ (backend); React 19, Vitest 4.1+, @fast-check/vitest 0.4, Playwright 1.59, @axe-core/playwright 4.10 (frontend)
**Storage**: N/A (no schema changes — test-only workstream)
**Testing**: pytest + pytest-cov (backend), Vitest + v8 coverage (frontend), Playwright (E2E)
**Target Platform**: Linux CI (GitHub Actions), local dev (macOS/Linux)
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: N/A (no runtime changes)
**Constraints**: All existing tests must continue to pass; no regressions in CI blocking jobs
**Scale/Scope**: ~171 backend source modules / 263 test files; ~128 frontend components / 560 test files; 19 E2E specs

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Check (Phase 0 Gate)

| Principle | Status | Notes |
|---|---|---|
| I. Specification-First | ✅ Pass | Parent issue #1240 provides structured requirements with sub-items 2.1–2.4 |
| II. Template-Driven Workflow | ✅ Pass | Using canonical plan-template.md; all artifacts follow `.specify/templates/` |
| III. Agent-Orchestrated Execution | ✅ Pass | speckit.plan agent produces plan.md, research.md, data-model.md, contracts/, quickstart.md |
| IV. Test Optionality with Clarity | ✅ Pass | Tests are the explicit deliverable — mandated by the feature specification |
| V. Simplicity and DRY | ✅ Pass | No new abstractions; adds tests to existing modules using established patterns |

### Post-Design Check (Phase 1 Gate)

| Principle | Status | Notes |
|---|---|---|
| I. Specification-First | ✅ Pass | Each workstream (2.1–2.4) maps to independently implementable user stories |
| II. Template-Driven Workflow | ✅ Pass | All generated artifacts follow canonical templates |
| III. Agent-Orchestrated Execution | ✅ Pass | Clear handoff: plan → tasks → implement |
| IV. Test Optionality with Clarity | ✅ Pass | Tests are the deliverable; follows test-first approach where applicable |
| V. Simplicity and DRY | ✅ Pass | Reuses existing test utilities (`test-utils.tsx`, `fixtures.ts`, conftest.py); no new test frameworks |

## Project Structure

### Documentation (this feature)

```text
specs/1240-harden-phase-2/
├── plan.md              # This file
├── research.md          # Phase 0: Coverage gap analysis and technology research
├── data-model.md        # Phase 1: Test coverage entities and tracking model
├── quickstart.md        # Phase 1: Developer guide for test expansion
├── contracts/
│   └── coverage-thresholds.yaml  # Phase 1: Coverage threshold contract
└── tasks.md             # Phase 2 output (speckit.tasks — NOT created by speckit.plan)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── src/
│   │   ├── api/           # 23 endpoint modules
│   │   ├── middleware/     # 5 middleware modules
│   │   ├── models/         # 29 data models
│   │   ├── prompts/        # 6 prompt templates
│   │   └── services/       # 100+ service modules
│   │       ├── agents/
│   │       ├── chores/
│   │       ├── copilot_polling/
│   │       ├── mcp_server/tools/
│   │       └── ...
│   ├── tests/
│   │   ├── unit/           # 206 test files (main target for 2.1)
│   │   ├── integration/    # 16 test files
│   │   ├── property/       # 9 files (target for 2.3)
│   │   ├── fuzz/           # 4 files
│   │   ├── chaos/          # 6 files
│   │   ├── concurrency/    # 5 files
│   │   └── e2e/            # 7 files
│   └── pyproject.toml      # fail_under = 75 → 80
│
└── frontend/
    ├── src/
    │   ├── components/     # ~128 components (target for 2.2)
    │   │   ├── chores/     # 13 untested
    │   │   ├── agents/     # 11 untested
    │   │   ├── tools/      # 9 untested
    │   │   ├── settings/   # 7 untested
    │   │   ├── ui/         # 13 untested
    │   │   └── pipeline/   # 16 untested
    │   ├── lib/            # Property test targets (2.3)
    │   └── test/           # test-utils.tsx, setup.ts
    ├── e2e/                # 19 Playwright specs (target for 2.4)
    │   ├── fixtures.ts     # Unauthenticated fixture
    │   ├── authenticated-fixtures.ts
    │   ├── auth.spec.ts          # Needs axe-core
    │   ├── board-navigation.spec.ts  # Needs axe-core
    │   ├── chat-interaction.spec.ts  # Needs axe-core
    │   └── settings-flow.spec.ts     # Needs axe-core
    ├── vitest.config.ts    # Threshold targets: 60/52/50/60
    └── package.json        # @axe-core/playwright, @fast-check/vitest already installed
```

**Structure Decision**: Existing web application monorepo (Option 2). No structural changes
required — all work targets existing test directories alongside existing source files.

## Workstream Breakdown

### WS 2.1 — Backend Coverage (75% → 80%)

**Objective**: Deepen test coverage in existing test files to raise the `fail_under` threshold
from 75 to 80.

**Approach**:

1. Run `pytest --cov=src --cov-report=term-missing` to identify files with lowest coverage
2. For each low-coverage file, add tests for:
   - Untested branches (error paths, edge cases, guard clauses)
   - Untested functions (private helpers, rarely-called utilities)
   - Async paths and exception handlers
3. Update `pyproject.toml` `fail_under` from 75 to 80

**Key modules to deepen** (based on research — all have test files but likely gaps):
- `prompts/` — template rendering edge cases, empty inputs, special characters
- `copilot_polling/` internals — recovery paths, state transitions, timeout handling
- `mcp_server/tools/` — error responses, pagination boundaries, auth failures
- `services/chores/` — scheduler edge cases, template builder variations
- `middleware/` — request_id propagation, rate limit boundaries, CSP header variations

**Dependencies**: None (independent workstream)

**Estimated scope**: ~30 test files to expand, ~200–400 new test cases

### WS 2.2 — Frontend Coverage (statements 50→60%, branches 44→52%, functions 41→50%)

**Objective**: Add unit tests for ~69 untested components and raise all coverage thresholds.

**Approach**:

1. Prioritize by category (highest gap first):
   - Pipeline (16 untested) → highest component count
   - Chores (13 untested) → user-critical flow
   - UI (13 untested) → shared primitives used everywhere
   - Agents (11 untested) → core feature
   - Tools (9 untested) → MCP integration
   - Settings (7 untested) → user preferences

2. For each component, create `ComponentName.test.tsx` or `__tests__/ComponentName.test.tsx`:
   - Import from `@/test/test-utils` (wraps render with providers)
   - Use `vi.mock()` for hooks and external dependencies
   - Test rendering, user interactions, and state changes
   - Follow existing patterns (SettingsSection.test.tsx, McpSettings.test.tsx)

3. Update `vitest.config.ts` thresholds:
   - statements: 50 → 60
   - branches: 44 → 52
   - functions: 41 → 50
   - lines: 50 → 60

**Dependencies**: None (independent workstream)

**Estimated scope**: ~69 new test files, ~350–500 new test cases

### WS 2.3 — Property-Based Testing Expansion

**Objective**: Expand from 15 property test files (9 backend + 6 frontend) with new categories.

**Approach**:

**Backend (Hypothesis)**:
1. Add round-trip serialization tests for API models:
   - `test_api_model_roundtrips.py` — Pydantic model → dict → model for request/response types
2. Add API validation edge cases:
   - `test_api_validation_properties.py` — boundary values, Unicode, empty strings, max-length
3. Add migration idempotency tests:
   - `test_migration_idempotency.py` — apply migration twice → same result

**Frontend (fast-check)**:
1. Add round-trip serialization:
   - `apiTypes.property.test.ts` — TypeScript type → JSON → type for API interfaces
2. Add validation edge cases:
   - `formValidation.property.test.ts` — form input boundaries, Unicode, special chars
3. Add state machine tests:
   - `pipelineState.property.test.ts` — pipeline state transitions always reach valid states

**Configuration**:
- Backend: Use existing `conftest.py` Hypothesis profiles (dev: 20 examples, CI: 200)
- Frontend: Use existing `@fast-check/vitest` integration

**Dependencies**: None (independent workstream)

**Estimated scope**: ~6 new property test files, ~30–50 new properties

### WS 2.4 — Axe-Core Playwright Integration

**Objective**: Add @axe-core/playwright a11y checks to auth, board, chat, and settings E2E flows.

**Approach**:

1. For each target spec file, add a11y test(s) using established pattern:

```typescript
import AxeBuilder from '@axe-core/playwright';

test('should pass accessibility audit', async ({ page }) => {
  await page.goto('/target-route');
  // Wait for page to stabilize
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  expect(results.violations).toEqual([]);
});
```

2. Target files and routes:
   - `auth.spec.ts` → `/login` page (uses `fixtures.ts`)
   - `board-navigation.spec.ts` → `/projects` board view (uses `authenticated-fixtures.ts`)
   - `chat-interaction.spec.ts` → `/projects` chat view (uses `authenticated-fixtures.ts`)
   - `settings-flow.spec.ts` → `/settings` page (uses `authenticated-fixtures.ts`)

3. Pattern matches existing usage in `ui.spec.ts` and `protected-routes.spec.ts`

**Dependencies**: None (independent workstream)

**Estimated scope**: 4 files modified, 4–8 new a11y test cases

## Execution Order

All four workstreams are independent and can be executed in parallel. Recommended order for
serial execution (based on risk and dependency):

1. **WS 2.4** (lowest risk, establishes a11y baseline) — 4 file modifications
2. **WS 2.3** (property tests, medium complexity) — ~6 new test files
3. **WS 2.1** (backend coverage, high volume) — ~30 files to expand
4. **WS 2.2** (frontend coverage, highest volume) — ~69 new test files

Final step (after all workstreams): bump threshold configs in `pyproject.toml` and
`vitest.config.ts`.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Coverage threshold bump breaks CI before all tests are written | Medium | High | Bump thresholds as the LAST commit after all tests pass |
| Frontend tests require complex mocking due to deep hook dependencies | Medium | Medium | Follow existing patterns in SettingsSection.test.tsx; use vi.mock() |
| Axe-core a11y violations discovered in existing UI | Low | Medium | Fix violations or document known issues with `axe.exclude()` |
| Property tests find actual bugs | Low | High | File separate issues; don't block the coverage workstream |
| TypeScript 6.0 strictness causes test compilation issues | Low | Medium | Use explicit initialization instead of definite assignment for nullable types |

## Complexity Tracking

> No constitution violations identified — no entries required.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| *(none)* | — | — |
