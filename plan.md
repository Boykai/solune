# Implementation Plan: Increase Test Coverage with Meaningful Tests Using Modern Best Practices

**Branch**: `copilot/speckit-plan-increase-test-coverage` | **Date**: 2026-04-09 | **Spec**: [#1175](https://github.com/Boykai/solune/issues/1175)
**Input**: Parent issue #1175 — Increase test coverage with meaningful tests, using modern best practices. Resolve any discovered bugs/issues.

## Summary

This plan targets measurable coverage gains across the Solune monorepo (Python backend + React/TypeScript frontend) by adding meaningful tests for currently untested modules and resolving bugs discovered during the audit. The repository already has a mature test infrastructure (235 backend test files, 232 frontend test files, 19 E2E specs) with modern tooling (pytest-asyncio auto mode, Vitest 4.1.3 + happy-dom, Playwright, property-based testing, mutation testing). All 16 existing skip markers are conditional infrastructure guards — no unconditional skips exist.

**Key findings from research (Phase 0)**:

- **Backend**: 185 source files, 235 test files. Coverage threshold at 75% (`fail_under`). ~30 source modules lack dedicated test coverage, concentrated in prompt templates (6), copilot polling internals (4), MCP server tools (8), and chores service internals (4).
- **Frontend**: 275 source files, 232 test files. Coverage thresholds at 50%/44%/41%/50% (statements/branches/functions/lines). ~61 components untested (chores: 13, agents: 10, tools: 9, UI primitives: 7, settings: 4, pipeline: 4, chat: 4). Hooks (98%) and pages (100%) are well-covered.
- **Bug found**: `_project_launch_locks` dictionary in `pipeline_state_store.py` grows unbounded — only cleared in test fixtures, never in production code.
- **Infrastructure**: Test configurations (pyproject.toml, vitest.config.ts) already follow modern best practices. No changes needed.

## Technical Context

**Language/Version**: Python >=3.12 (backend), TypeScript ~6.0.2 (frontend)
**Primary Dependencies**: FastAPI, pytest 8.x, pytest-asyncio, pytest-randomly, pytest-cov, hypothesis, Vitest 4.1.3, @testing-library/react 16.x, Playwright 1.59, React 19.2.0
**Storage**: SQLite via aiosqlite (test isolation handled by existing conftest fixtures)
**Testing**: pytest (backend), Vitest + Testing Library + jest-axe (frontend unit), Playwright + @axe-core/playwright (E2E)
**Target Platform**: Linux server (backend), Modern browsers (frontend)
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: N/A — test infrastructure changes, no runtime impact
**Constraints**: Zero breaking changes to production code; all existing tests must continue passing; coverage thresholds maintained (backend ≥75%, frontend ≥50% statements)
**Scale/Scope**: ~30 untested backend modules; ~61 untested frontend components; 1 bug to fix; ~40–50 new test functions total

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Parent issue #1175 provides clear scope: increase coverage, use modern practices, resolve bugs |
| II. Template-Driven Workflow | ✅ PASS | Using canonical plan template; plan.md at repository root per branch convention |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan phase produces plan.md; handoff to tasks phase for implementation |
| IV. Test Optionality | ✅ PASS | This feature IS about testing — tests are the primary deliverable |
| V. Simplicity and DRY | ✅ PASS | Leverages existing infrastructure where correct; adds only missing coverage and fixes |

**Gate Result**: ✅ ALL PASS — proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
plan.md                  # This file (repository root)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── pyproject.toml                              # Verified: fail_under = 75, asyncio_mode = "auto"
│   ├── pyrightconfig.json                          # Verified: standard mode
│   ├── pyrightconfig.tests.json                    # Verified: basic mode with stubPath
│   ├── src/
│   │   ├── utils.py                                # Test target: BoundedSet, resolve_repository()
│   │   ├── constants.py                            # Test target: constant values validation
│   │   ├── api/webhooks.py                         # Already tested — HMAC, deduplication
│   │   ├── middleware/request_id.py                # Test target: request ID propagation
│   │   ├── services/encryption.py                  # Already tested (test_token_encryption.py)
│   │   ├── services/pipeline_state_store.py        # Bug target: unbounded _project_launch_locks
│   │   ├── services/tools/presets.py               # Already tested (test_presets.py)
│   │   ├── services/copilot_polling/               # Test target: completion, helpers, pipeline, state
│   │   ├── services/chores/                        # Test target: chat, counter, scheduler, template_builder
│   │   ├── services/mcp_server/tools/              # Test target: 8 tool modules
│   │   └── prompts/                                # Test target: 6 prompt template modules
│   └── tests/
│       ├── conftest.py                             # Verified: proper cleanup, BUG FIX comment noted
│       ├── unit/                                   # 194 test files — add ~15–20 new
│       ├── integration/                            # 14 test files — add 2–3 new
│       ├── property/                               # 7 test files — add 1–2 new
│       ├── e2e/                                    # 5 test files
│       ├── chaos/                                  # 5 test files
│       ├── concurrency/                            # 4 test files
│       └── fuzz/                                   # 3 test files
│
├── frontend/
│   ├── vitest.config.ts                            # Verified: happy-dom, v8, thresholds correct
│   ├── package.json                                # Verified: jest-axe 10.0.0 already installed
│   ├── src/
│   │   ├── test/setup.ts                           # Verified: UUID stubs, MockWebSocket, createMockApi
│   │   ├── components/
│   │   │   ├── chores/                             # Test target: 13 untested components
│   │   │   ├── agents/                             # Test target: 10 untested components
│   │   │   ├── tools/                              # Test target: 9 untested components
│   │   │   ├── ui/                                 # Test target: 7 untested primitives
│   │   │   ├── settings/                           # Test target: 4 untested components
│   │   │   ├── pipeline/                           # Test target: 4 untested components
│   │   │   └── chat/                               # Test target: 4 untested components
│   │   ├── hooks/useConfirmation.tsx               # Test target: 1 untested hook
│   │   └── services/api.ts                         # Already tested (api.test.ts)
│   └── e2e/                                        # 19 E2E test files — no changes needed
│
└── .github/workflows/ci.yml                        # Reference: 9 CI jobs, coverage enforcement
```

**Structure Decision**: Web application. Changes span `solune/backend/tests/` (new test files) and `solune/frontend/src/` (new test files adjacent to components). One production bug fix in `solune/backend/src/services/pipeline_state_store.py`.

## Phase 0: Research & Audit

### R1: Skip Marker Classification

**Decision**: All 16 skip markers are conditional infrastructure guards — retain all.

| File | Count | Guard Type | Action |
|------|-------|------------|--------|
| `tests/unit/test_run_mutmut_shard.py:138` | 1 | `@pytest.mark.skipif` — CI workflow YAML missing | No change |
| `tests/architecture/test_import_rules.py:54,93,116` | 3 | `pytest.skip()` — directory structure check | No change |
| `tests/performance/test_board_load_time.py:40–71` | 4 | `pytest.skip()` — backend/credentials required | No change |
| `tests/integration/test_custom_agent_assignment.py:45` | 1 | `pytest.skip()` — GITHUB_TOKEN required | No change |
| `e2e/integration.spec.ts:62,73` | 2 | `test.skip()` — health-check catch block | No change |
| `e2e/project-load-performance.spec.ts:47,50,65,114` | 4 | `test.skip()` — prerequisites missing | No change |

**Rationale**: Removing these guards would cause CI failures when infrastructure is absent. They correctly gate tests on external dependencies.
**Alternatives Considered**: (1) Replace with pytest markers — rejected because guards evaluate HTTP health at runtime, not decoration time. (2) Force-remove — rejected because tests would fail without credentials.

### R2: Test Infrastructure Audit

**Decision**: No infrastructure changes needed — both backend and frontend configurations follow modern best practices.

| Config | Setting | Current Value | Status |
|--------|---------|---------------|--------|
| `pyproject.toml` | `asyncio_mode` | `"auto"` | ✅ Modern |
| `pyproject.toml` | `asyncio_default_fixture_loop_scope` | `"function"` | ✅ Modern |
| `pyproject.toml` | `fail_under` | `75` | ✅ Exceeds 70% minimum |
| `pyproject.toml` | `branch` coverage | `true` | ✅ Enabled |
| `vitest.config.ts` | `environment` | `"happy-dom"` | ✅ Modern |
| `vitest.config.ts` | `globals` | `true` | ✅ Correct |
| `vitest.config.ts` | `coverage.provider` | `"v8"` | ✅ Modern |
| `vitest.config.ts` | `coverage.thresholds.statements` | `50` | ✅ Enforced |
| `package.json` | `jest-axe` | `^10.0.0` | ✅ Installed |
| `package.json` | `@fast-check/vitest` | `^0.4.0` | ✅ Property testing available |

**Rationale**: Infrastructure is already modern. Effort should focus on adding tests, not changing tooling.

### R3: Coverage Gap Prioritization

**Decision**: Prioritize by risk × coverage-impact. High-priority modules have security/data implications and are currently untested.

**Backend Priority Matrix** (sorted by risk):

| Priority | Module | Risk | Why Untested | Action |
|----------|--------|------|-------------|--------|
| P1-HIGH | `services/copilot_polling/{completion,helpers,pipeline,state}` | HIGH — orchestrates PR automation | Complex async state machine | Add unit tests with mocked GitHub API |
| P1-HIGH | `middleware/request_id.py` | MEDIUM — observability gap | Simple middleware, overlooked | Add unit test for header propagation |
| P1-HIGH | `services/pipeline_state_store.py` (lock leak) | HIGH — memory leak in production | Bug discovered during audit | Fix + add regression test |
| P2-MED | `prompts/{agent_instructions,issue_generation,label_classification,plan_instructions,task_generation,transcript_analysis}` | LOW — string templates | Pure functions, low complexity | Add structure/contract tests |
| P2-MED | `services/chores/{chat,counter,scheduler,template_builder}` | MEDIUM — user-facing feature | Service-internal modules | Add unit tests with mocked dependencies |
| P2-MED | `services/mcp_server/tools/{activity,agents,apps,chat,chores,pipelines,tasks}` | MEDIUM — API-exposed tools | MCP protocol layer | Add unit tests per tool handler |
| P3-LOW | `constants.py` | LOW — static values | No logic to test | Add smoke test for expected exports |
| P3-LOW | `services/app_templates/{loader,registry,renderer}` | LOW — template loading | Already tested indirectly via API tests | Add focused unit tests if time allows |

**Frontend Priority Matrix** (sorted by impact):

| Priority | Area | Count | Risk | Action |
|----------|------|-------|------|--------|
| P1-HIGH | `hooks/useConfirmation.tsx` | 1 | Hook gap breaks 98% coverage claim | Add test matching hook conventions |
| P2-MED | `components/chores/` | 13 | User-facing CRUD | Add tests for key components (ChoreCard, ChoresPanel, AddChoreModal) |
| P2-MED | `components/agents/` | 10 | Agent management UI | Add tests for AgentCard, AddAgentModal, AgentsPanel |
| P2-MED | `components/tools/` | 9 | MCP tool configuration | Add tests for ToolCard, ToolsPanel, McpPresetsGallery |
| P2-MED | `components/settings/` | 4 | User preferences | Add tests for key settings components |
| P3-LOW | `components/ui/` | 7 | Radix UI wrappers, minimal logic | Add basic render tests for non-trivial ones |
| P3-LOW | `components/pipeline/` | 4 | Pipeline visualization | Add tests for ModelSelector, PipelineStagesOverview |
| P3-LOW | `components/chat/` | 4 | Chat UI augmentation | Add tests for PlanDependencyGraph, MentionAutocomplete |

**Rationale**: Security and data-integrity modules first, user-facing features second, low-complexity wrappers last.
**Alternatives Considered**: (1) Alphabetical order — rejected, doesn't account for risk. (2) Frontend-first — rejected, backend has higher-risk gaps.

### R4: Bug Discovery — Unbounded Lock Dictionary

**Decision**: Fix the `_project_launch_locks` memory leak in `pipeline_state_store.py`.

**Location**: `solune/backend/src/services/pipeline_state_store.py:38–61`

```python
_project_launch_locks: dict[str, asyncio.Lock] = {}  # Line 38 — grows unbounded

def _get_project_launch_lock(project_id: str) -> asyncio.Lock:  # Line 55
    if project_id not in _project_launch_locks:
        _project_launch_locks[project_id] = asyncio.Lock()  # Never cleaned up
    return _project_launch_locks[project_id]
```

**Impact**: Long-running instances accumulate one `asyncio.Lock` object per unique project ID. With many projects over time, this is a memory leak. The test conftest already has `pss_mod._project_launch_locks.clear()` (line 299) as a workaround, confirming the issue is known.

**Fix approach**: Add a bounded eviction strategy (e.g., LRU with max size using `BoundedSet` pattern already in `utils.py`, or a simple size check with oldest-key eviction). The lock objects are lightweight but the dictionary growth is unbounded.

**Rationale**: This is the only production bug found during the audit. All other issues are coverage gaps, not behavioral defects.

## Phase 1: Design & Contracts

### Data Model: Test Coverage Targets

| Area | Current State | Target | Metric |
|------|--------------|--------|--------|
| Backend overall | ≥75% (enforced) | ≥75% (maintain) | `pytest --cov-fail-under=75` |
| Backend untested modules | ~30 files with 0% | ≥1 test per P1/P2 module | New test file count |
| Frontend statements | ≥50% (enforced) | ≥50% (maintain) | Vitest coverage threshold |
| Frontend untested components | ~61 files with 0% | ≥1 test per P1/P2 component | New test file count |
| Frontend hooks | 60/61 (98%) | 61/61 (100%) | useConfirmation test |

### Contract: Backend Test Patterns

New backend tests MUST follow these patterns (derived from existing test conventions):

1. **File naming**: `test_<module_name>.py` in appropriate `tests/unit/` or `tests/integration/` directory
2. **Async tests**: Use `async def test_*` directly — `asyncio_mode = "auto"` handles the rest
3. **Fixtures**: Use existing conftest fixtures (`mock_settings`, `mock_db`, `test_client`, etc.)
4. **Assertions**: Assert behavior, not implementation. Test happy path + at least one error case.
5. **Mocking**: Use `unittest.mock.patch` or `pytest-mock`'s `mocker` fixture. Mock at service boundaries.
6. **No new skips**: Zero new `@pytest.mark.skip` or `pytest.skip()` calls without infrastructure justification.
7. **Property tests**: Use `hypothesis` for functions with complex input domains (e.g., prompt templates).
8. **Naming convention**: `test_<function>_<scenario>` (e.g., `test_get_project_lock_returns_same_lock_for_same_project`)

### Contract: Frontend Test Patterns

New frontend tests MUST follow these patterns (derived from existing test conventions):

1. **File naming**: `<ComponentName>.test.tsx` adjacent to source file
2. **Rendering**: Use `render` from `@/test/test-utils` (wraps with providers) or `renderHook` from `@testing-library/react`
3. **Queries**: Prefer `screen.getByRole`, `screen.getByText`, `screen.getByLabelText` (accessible queries first)
4. **User interaction**: Use `await userEvent.setup().click(...)` pattern
5. **Mocking**: Use `vi.mock()` with `vi.hoisted()` for hook mocks. Use `createMockApi()` from setup.ts for API mocks.
6. **Assertions**: Assert rendered output, not internal state. Test user-visible behavior.
7. **Accessibility**: Include `expect(await axe(container)).toHaveNoViolations()` for new component tests where applicable.
8. **No new skips**: Zero new `.skip`, `.todo`, `xit`, or `xdescribe` markers.

### Quickstart: Developer Guide for Adding Tests

**Backend**:

```bash
cd solune/backend
# Run specific test file
python -m pytest tests/unit/test_<module>.py -v
# Run with coverage for specific module
python -m pytest tests/unit/test_<module>.py --cov=src/<module> --cov-report=term-missing
# Run full suite with coverage enforcement
python -m pytest tests/ --cov=src --cov-fail-under=75 -q
# Lint and type-check
ruff check src/ tests/ && ruff format --check src/ tests/ && pyright src/
```

**Frontend**:

```bash
cd solune/frontend
# Run specific test file
npx vitest run src/components/<dir>/<Component>.test.tsx
# Run with coverage
npx vitest run --coverage
# Run all tests
npm run test
# Type-check
npm run type-check
```

## Execution Phases

### Step 1 — Fix Production Bug: Unbounded Lock Dictionary

| Task | File | Action |
|------|------|--------|
| 1.1 | `src/services/pipeline_state_store.py` | Add bounded eviction to `_project_launch_locks` (use max-size check, evict oldest when over limit) |
| 1.2 | `tests/unit/test_pipeline_state_store.py` | Add regression test: verify lock count stays bounded after many project accesses |

**Acceptance**: `_project_launch_locks` has a maximum size; existing tests pass; new regression test passes.

### Step 2 — Backend P1 Coverage: Copilot Polling & Middleware

| Task | Target Module | New Test File | Test Count |
|------|--------------|---------------|-----------|
| 2.1 | `services/copilot_polling/state.py` | `tests/unit/test_copilot_polling_state.py` | 3–5 tests |
| 2.2 | `services/copilot_polling/helpers.py` | `tests/unit/test_copilot_polling_helpers.py` | 3–5 tests |
| 2.3 | `services/copilot_polling/completion.py` | `tests/unit/test_copilot_polling_completion.py` | 3–5 tests |
| 2.4 | `services/copilot_polling/pipeline.py` | `tests/unit/test_copilot_polling_pipeline.py` | 3–5 tests |
| 2.5 | `middleware/request_id.py` | `tests/unit/test_request_id.py` | 2–3 tests |

**Test design**: Mock GitHub API responses and database calls. Test state transitions, error handling, and edge cases (empty responses, timeouts, invalid data).

**Acceptance**: All new tests pass; no new skip markers; overall backend coverage ≥75%.

### Step 3 — Backend P2 Coverage: Prompts, Chores, MCP Tools

| Task | Target Module | New Test File | Test Count |
|------|--------------|---------------|-----------|
| 3.1 | `prompts/*.py` (6 files) | `tests/unit/test_prompts.py` | 6–12 tests (structure/contract tests) |
| 3.2 | `services/chores/scheduler.py` | `tests/unit/test_chores_scheduler.py` | 3–5 tests |
| 3.3 | `services/chores/counter.py` | `tests/unit/test_chores_counter.py` | 2–3 tests |
| 3.4 | `services/chores/template_builder.py` | `tests/unit/test_chores_template_builder.py` | 2–3 tests |
| 3.5 | `services/chores/chat.py` | `tests/unit/test_chores_chat.py` | 2–3 tests |
| 3.6 | `services/mcp_server/tools/*.py` (7 files) | `tests/unit/test_mcp_server/test_mcp_tools_*.py` | 7–14 tests |

**Test design**: Prompts → verify output contains required sections/placeholders. Chores → mock database, test scheduling logic and counter math. MCP tools → mock context, test tool dispatch and response formatting.

**Acceptance**: All new tests pass; P2 modules have ≥1 test each.

### Step 4 — Frontend P1 Coverage: Missing Hook + Key Components

| Task | Target | New Test File | Test Count |
|------|--------|---------------|-----------|
| 4.1 | `hooks/useConfirmation.tsx` | `hooks/useConfirmation.test.tsx` | 3–5 tests |
| 4.2 | `components/chores/ChoreCard.tsx` | `components/chores/ChoreCard.test.tsx` | 3–4 tests |
| 4.3 | `components/chores/ChoresPanel.tsx` | `components/chores/ChoresPanel.test.tsx` | 2–3 tests |
| 4.4 | `components/chores/AddChoreModal.tsx` | `components/chores/AddChoreModal.test.tsx` | 2–3 tests |
| 4.5 | `components/agents/AgentCard.tsx` | `components/agents/AgentCard.test.tsx` | 3–4 tests |
| 4.6 | `components/agents/AddAgentModal.tsx` | `components/agents/AddAgentModal.test.tsx` | 2–3 tests |

**Test design**: Render component with minimal props, verify visible output. Test user interactions (click, type). Mock hooks via `vi.mock()` with `vi.hoisted()`.

**Acceptance**: All new tests pass; `useConfirmation` hook at 100% coverage; frontend coverage ≥50%.

### Step 5 — Frontend P2 Coverage: Tools, Settings, UI Primitives

| Task | Target | New Test File | Test Count |
|------|--------|---------------|-----------|
| 5.1 | `components/tools/ToolCard.tsx` | `components/tools/ToolCard.test.tsx` | 2–3 tests |
| 5.2 | `components/tools/ToolsPanel.tsx` | `components/tools/ToolsPanel.test.tsx` | 2–3 tests |
| 5.3 | `components/settings/ProjectSettings.tsx` | `components/settings/ProjectSettings.test.tsx` | 2–3 tests |
| 5.4 | `components/ui/copy-button.tsx` | `components/ui/copy-button.test.tsx` | 2 tests |
| 5.5 | `components/ui/confirmation-dialog.tsx` | `components/ui/confirmation-dialog.test.tsx` | 2–3 tests |
| 5.6 | `components/pipeline/ModelSelector.tsx` | `components/pipeline/ModelSelector.test.tsx` | 2–3 tests |

**Test design**: Same patterns as Step 4. UI primitives → render + verify accessible structure. Dialogs → test open/close/confirm flows.

**Acceptance**: All new tests pass; no regressions.

### Step 6 — Validate Full Suite and CI

| Task | Command | Expected |
|------|---------|----------|
| 6.1 | `cd solune/backend && ruff check src/ tests/` | Zero lint errors |
| 6.2 | `cd solune/backend && ruff format --check src/ tests/` | Zero format violations |
| 6.3 | `cd solune/backend && pyright src/` | Zero type errors |
| 6.4 | `cd solune/backend && python -m pytest tests/ --cov=src --cov-fail-under=75 -q` | All pass, coverage ≥75% |
| 6.5 | `cd solune/frontend && npm run lint` | Zero lint errors |
| 6.6 | `cd solune/frontend && npm run type-check` | Zero type errors |
| 6.7 | `cd solune/frontend && npm run test` | All pass |
| 6.8 | `cd solune/frontend && npm run build` | Build succeeds |

**Acceptance**: All suites exit 0; CI green; zero unconditional skip markers remain; coverage thresholds maintained.

## Design Decisions

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| Retain all 16 conditional skip markers | They correctly detect missing infrastructure at runtime; removing them would cause CI failures when prerequisites are absent | Force-remove: tests fail without credentials. Replace with decorators: can't evaluate HTTP health at decoration time. |
| Fix `_project_launch_locks` leak with bounded eviction | Only production bug found; memory grows unbounded; `BoundedSet` pattern already exists in codebase | Ignore: memory leak worsens over time. Weak references: `asyncio.Lock` doesn't support `weakref`. |
| Prioritize copilot polling tests over prompt tests | Copilot polling handles PR automation with complex async state; prompts are pure string templates | Alphabetical: doesn't account for risk. Prompts first: lower impact per test. |
| Keep coverage thresholds at 75% backend, 50% frontend | Already enforced and achievable; raising thresholds risks blocking unrelated merges | 80%+: too aggressive without major refactoring effort. Lower: reduces existing quality bar. |
| Per-test jest-axe import, not global | Not all tests need axe; jest-axe already in package.json | Global setup: adds overhead to all tests. Skip axe: accessibility regression risk. |
| Add tests for P1+P2 modules only, not P3 | Maximizes coverage gain per effort; P3 modules are either static values or Radix UI wrappers with minimal logic | Test everything: too much effort for low-value wrappers. P1 only: leaves significant P2 gaps. |

## Constitution Re-Check (Post Phase 1 Design)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Parent issue #1175 with clear scope; plan decomposes into 6 execution steps |
| II. Template-Driven Workflow | ✅ PASS | Using canonical plan template structure; consistent artifact naming |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan phase complete; handoff to tasks phase for implementation |
| IV. Test Optionality | ✅ PASS | Testing IS the feature — tests are the primary deliverable |
| V. Simplicity and DRY | ✅ PASS | Leverages existing correct infrastructure; adds only missing coverage and one bug fix |

**Gate Result**: ✅ ALL PASS — proceed to tasks phase

## Complexity Tracking

> One minor complexity: production bug fix in Step 1 goes beyond "just add tests" but is directly discovered during the audit and is small in scope.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Bug fix in `pipeline_state_store.py` | Memory leak discovered during test audit; directly related to test coverage work | "Just add tests": would leave a known production bug unfixed that was found as part of this work |
