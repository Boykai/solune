# Implementation Plan: Increase Test Coverage with Meaningful Tests

**Branch**: `copilot/increase-test-coverage-backend` | **Date**: 2026-04-05 | **Spec**: `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/spec.md`  
**Input**: Feature specification from `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/spec.md`

## Summary

Raise backend and frontend coverage by adding behavior-first regression tests around the highest-risk existing modules, fixing the six bugs that those tests expose inline, and reusing the repository’s current pytest/Vitest infrastructure instead of introducing new tools. The design centers on expanding existing backend and frontend suites where they already exist, creating only the missing test files called out in the specification, and validating success with targeted module thresholds plus aggregate coverage, lint, and type-check smoke checks.

## Technical Context

**Language/Version**: Python 3.12+ in `/home/runner/work/solune/solune/solune/backend`; TypeScript ~6.0.2 + React 19.2 in `/home/runner/work/solune/solune/solune/frontend`  
**Primary Dependencies**: FastAPI, Pydantic v2, aiosqlite, slowapi, pytest, pytest-asyncio, pytest-cov, React, TanStack Query, Vitest, Testing Library, happy-dom  
**Storage**: SQLite via `aiosqlite` for backend state; temporary filesystem uploads/transcripts for chat attachment and transcript-path scenarios  
**Testing**: `uv run pytest` for backend unit/coverage work; `npm run test` and `npm run test:coverage` for frontend behavioral coverage; existing lint/type-check commands remain gate checks  
**Target Platform**: Linux/Docker backend plus browser SPA frontend  
**Project Type**: Web application monorepo with separate backend and frontend packages under `/home/runner/work/solune/solune/solune`  
**Performance Goals**: Deterministic, non-flaky tests; backend aggregate coverage ≥87% line and ≥78% branch; frontend statement coverage ≥63%; all module-level thresholds from `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/spec.md` must be met  
**Constraints**: No new test dependencies; no scope expansion into e2e/integration/fuzz/property testing; bug fixes stay inline with the tests that expose them; prefer shallow mocking via existing fixtures/test-utils; preserve green existing suites  
**Scale/Scope**: Backend work spans 9 target modules/surfaces (`chat.py`, `board.py`, `apps.py`, `utils.py`, `settings.py`, `onboarding.py`, `templates.py`, `pipeline_estimate.py`, `completion_providers.py`); frontend work spans 9 target surfaces (6 components + 3 utility/context modules)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. Specification-First Development** | ✅ PASS | `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/spec.md` defines prioritized stories, independent tests, acceptance scenarios, scope, and success criteria. |
| **II. Template-Driven Workflow** | ✅ PASS | This plan and the Phase 0/1 artifacts are limited to the canonical outputs: `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, and `contracts/`. |
| **III. Agent-Orchestrated Execution** | ✅ PASS | The feature remains within the existing Spec Kit flow: specification already exists, this plan defines research/design outputs, and no ad hoc workflow is introduced. |
| **IV. Test Optionality with Clarity** | ✅ PASS | Tests are explicitly required by the feature spec; this plan keeps test work behavior-focused and orders bug reproduction/regression coverage before inline fixes. |
| **V. Simplicity and DRY** | ✅ PASS | The plan reuses existing backend `conftest.py`, frontend `src/test/setup.ts`, and current test runners instead of inventing new harnesses or abstractions. |

**Post-Phase 1 Re-check**: ✅ PASS — research resolved all technical-context unknowns, the data model stays limited to planning entities for tests/coverage/bug-fixes, the contract stays additive and documents already-existing HTTP surfaces, and the quickstart uses only existing repository tooling.

## Project Structure

### Documentation (this feature)

```text
/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── test-coverage-surfaces.openapi.yaml
└── tasks.md                         # Phase 2 output; not created by this workflow
```

### Source Code (repository root)

```text
/home/runner/work/solune/solune/solune/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── chat.py
│   │   │   ├── board.py
│   │   │   ├── apps.py
│   │   │   ├── settings.py
│   │   │   ├── onboarding.py
│   │   │   └── templates.py
│   │   ├── services/
│   │   │   ├── pipeline_estimate.py
│   │   │   └── completion_providers.py
│   │   └── utils.py
│   └── tests/
│       ├── conftest.py
│       └── unit/
│           ├── test_api_chat.py
│           ├── test_api_board.py
│           ├── test_api_apps.py
│           ├── test_api_settings.py
│           ├── test_api_onboarding.py
│           ├── test_pipeline_estimate.py
│           ├── test_completion_providers.py
│           ├── test_utils.py
│           └── test_api_templates.py         # planned new file
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── agents/
    │   │   │   ├── AgentsPanel.tsx
    │   │   │   ├── AddAgentModal.tsx
    │   │   │   ├── AgentChatFlow.tsx
    │   │   │   └── __tests__/
    │   │   └── pipeline/
    │   │       ├── ExecutionGroupCard.tsx
    │   │       ├── PipelineModelDropdown.tsx
    │   │       └── PipelineRunHistory.tsx
    │   ├── context/SyncStatusContext.tsx
    │   ├── lib/
    │   │   ├── route-suggestions.ts
    │   │   └── commands/registry.ts
    │   └── test/
    │       ├── setup.ts
    │       └── test-utils.tsx
    └── package.json
```

**Structure Decision**: Use the repository’s existing web-application split under `/home/runner/work/solune/solune/solune/backend` and `/home/runner/work/solune/solune/solune/frontend`. Backend API and service regression tests stay in `/home/runner/work/solune/solune/solune/backend/tests/unit`, while frontend component and utility tests stay colocated under `/home/runner/work/solune/solune/solune/frontend/src`.

## Implementation Phases

### Phase A — Backend low-coverage regression targets (Priority P1, block later phases)

**Goal**: Raise coverage in the existing high-risk backend modules first and land the six inline bug fixes closest to user-visible failures.

1. **Chat API regression pass**  
   **Targets**:
   - `/home/runner/work/solune/solune/solune/backend/src/api/chat.py`
   - `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_chat.py`
   
   **Work**:
   - Add tests for proposal expiry boundaries, `_retry_persist` transient/permanent failures, transcript path traversal rejection, upload size/type validation, unrecognized `action_type`, and streaming failures with missing `action_data`.
   - Fix the `expires_at is None` guard, add an `action_type` whitelist, and reject oversized transcript reads before file access.
   
   **Dependencies**: none
   
   **Exit criteria**:
   - chat coverage reaches the spec target (≥80%)
   - each of the three chat bugs is guarded by a regression test

2. **Board API error-classification pass**  
   **Targets**:
   - `/home/runner/work/solune/solune/solune/backend/src/api/board.py`
   - `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_board.py`
   
   **Work**:
   - Add tests for auth vs rate-limit classification, `_retry_after_seconds()` edges, stale cache fallback, manual refresh cache deletion, and stable hashing.
   - Fix the hash-ordering bug so the data hash includes the finalized `rate_limit` state.
   
   **Dependencies**: can run after or in parallel with chat once shared fixtures are understood
   
   **Exit criteria**:
   - board coverage reaches the spec target (≥85%)
   - rate-limit and auth failures follow distinct behavior under test

3. **Apps API branch-coverage pass**  
   **Targets**:
   - `/home/runner/work/solune/solune/solune/backend/src/api/apps.py`
   - `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_apps.py`
   
   **Work**:
   - Add tests for empty-after-strip name normalization, launch-failure warnings, duplicate import detection via normalized URLs, and force-delete partial failures.
   - Fix empty normalized names so invalid resources are rejected deterministically.
   
   **Dependencies**: none beyond existing backend fixtures
   
   **Exit criteria**:
   - branch coverage reaches the spec target (≥75%)
   - normalized-empty names fail with a tested error path

4. **Shared utility coverage pass**  
   **Targets**:
   - `/home/runner/work/solune/solune/solune/backend/src/utils.py`
   - `/home/runner/work/solune/solune/solune/backend/tests/unit/test_utils.py`
   
   **Work**:
   - Add boundary tests for `BoundedDict`, repository URL parsing, `resolve_repository()` fallback order, malformed REST URL handling, and `cached_fetch(refresh=True)`.
   
   **Dependencies**: can proceed in parallel with steps 1–3
   
   **Exit criteria**:
   - utils coverage reaches the spec target (≥85%)
   - repository parsing scenarios match the documented edge cases

### Phase B — Backend zero-coverage modules (Priority P1, starts after Phase A smoke is green)

**Goal**: establish a behavioral safety net around uncovered backend endpoints/services without introducing new test infrastructure.

1. **Settings endpoint suite**
   - Add or expand `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_settings.py`
   - Cover admin enforcement, empty-update no-op, workflow sync, cache invalidation, and missing-token model fetch behavior
   - Fix the no-op activity-log bug inline

2. **Onboarding endpoint suite**
   - Add or expand `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_onboarding.py`
   - Cover default state, progress persistence, completion timestamps, dismiss/completion separation, and `step > 13` validation

3. **Templates endpoint suite**
   - Create `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_templates.py`
   - Cover empty registry, invalid category, summary/detail separation, and 404 behavior

4. **Pipeline estimate service suite**
   - Add or expand `/home/runner/work/solune/solune/solune/backend/tests/unit/test_pipeline_estimate.py`
   - Cover hour thresholds, agent-count validation/logging, and deterministic date calculation

5. **Completion providers service suite**
   - Add or expand `/home/runner/work/solune/solune/solune/backend/tests/unit/test_completion_providers.py`
   - Cover concurrent client-pool access, cleanup on remove, timeout fallback, Azure config validation, and factory dispatch

**Dependencies**:
- reuse fixture patterns proven in Phase A
- run targeted backend smoke after each module cluster before aggregate backend coverage verification

**Exit criteria**:
- each target module reaches its threshold from the spec
- no new backend suite relies on integration/e2e/property-style infrastructure

### Phase C — Frontend critical component coverage (Priority P2, begin after backend P1 targets are stable)

**Goal**: add behavior-first tests to the most interactive UI surfaces while reusing existing Testing Library patterns.

1. **Agents surfaces**
   - Create `/home/runner/work/solune/solune/solune/frontend/src/components/agents/__tests__/AgentsPanel.test.tsx`
   - Create `/home/runner/work/solune/solune/solune/frontend/src/components/agents/__tests__/AddAgentModal.test.tsx`
   - Create `/home/runner/work/solune/solune/solune/frontend/src/components/agents/__tests__/AgentChatFlow.test.tsx`
   - Reuse `/home/runner/work/solune/solune/solune/frontend/src/test/test-utils.tsx` and existing mocked hook/provider patterns

2. **Pipeline surfaces**
   - Create `/home/runner/work/solune/solune/solune/frontend/src/components/pipeline/ExecutionGroupCard.test.tsx`
   - Create `/home/runner/work/solune/solune/solune/frontend/src/components/pipeline/PipelineModelDropdown.test.tsx`
   - Create `/home/runner/work/solune/solune/solune/frontend/src/components/pipeline/PipelineRunHistory.test.tsx`

**Dependencies**:
- stable frontend mock boundaries for API/hooks/context
- prefer targeted fake timers and explicit waits for async behavior called out in the spec’s edge cases

**Exit criteria**:
- component suites cover primary flows, loading/error states, and at least two edge cases per surface
- no snapshot-only coverage

### Phase D — Frontend utility and context coverage (Priority P3, parallel with late Phase C)

**Goal**: finish the feature with deterministic tests around foundational frontend logic.

1. Create `/home/runner/work/solune/solune/solune/frontend/src/lib/route-suggestions.test.ts`
2. Create `/home/runner/work/solune/solune/solune/frontend/src/lib/commands/registry.test.ts`
3. Create `/home/runner/work/solune/solune/solune/frontend/src/context/SyncStatusContext.test.tsx`

**Dependencies**:
- none on backend changes
- may run in parallel with component-test stabilization

**Exit criteria**:
- pure-function/context tests fully cover the listed threshold, filtering, parsing, and deduplication behaviors

## Execution Order and Dependencies

```text
Phase A (backend high-risk regressions)
  A1 chat ─┐
  A2 board ├──→ backend targeted smoke ───→ Phase B
  A3 apps ─┤
  A4 utils ┘

Phase B (backend zero-coverage modules)
  B1 settings ─┐
  B2 onboarding├──→ backend aggregate coverage/lint/type smoke ───→ Phase C
  B3 templates ┤
  B4 estimate  ┤
  B5 providers ┘

Phase C (frontend critical components)
  C1 agents ─┐
  C2 pipeline├──→ frontend targeted smoke ───→ Phase D / final verification

Phase D (frontend utility + context)
  D1 route suggestions ─┐
  D2 command registry   ├──→ frontend aggregate coverage/lint/type smoke
  D3 sync status        ┘
```

## Planned File Touchpoints

| Area | Files | Planned Change |
|------|-------|----------------|
| Backend API fixes/tests | `src/api/chat.py`, `src/api/board.py`, `src/api/apps.py`, `tests/unit/test_api_chat.py`, `tests/unit/test_api_board.py`, `tests/unit/test_api_apps.py` | Add regression tests and minimal inline bug fixes |
| Backend utility coverage | `src/utils.py`, `tests/unit/test_utils.py` | Expand branch/error-path coverage |
| Backend uncovered modules | `src/api/settings.py`, `src/api/onboarding.py`, `src/api/templates.py`, `src/services/pipeline_estimate.py`, `src/services/completion_providers.py`, matching unit tests | Add new or expanded suites and one no-op bug fix in settings |
| Frontend component tests | `src/components/agents/**`, `src/components/pipeline/*.test.tsx` | Add behavior-driven component tests |
| Frontend utility/context tests | `src/lib/route-suggestions.test.ts`, `src/lib/commands/registry.test.ts`, `src/context/SyncStatusContext.test.tsx` | Add deterministic pure-function/context tests |

## Verification Plan

### Targeted checks during implementation

```bash
cd /home/runner/work/solune/solune/solune/backend
uv run pytest \
  tests/unit/test_api_chat.py \
  tests/unit/test_api_board.py \
  tests/unit/test_api_apps.py \
  tests/unit/test_utils.py

cd /home/runner/work/solune/solune/solune/backend
uv run pytest \
  tests/unit/test_api_settings.py \
  tests/unit/test_api_onboarding.py \
  tests/unit/test_api_templates.py \
  tests/unit/test_pipeline_estimate.py \
  tests/unit/test_completion_providers.py

cd /home/runner/work/solune/solune/solune/frontend
npm run test -- \
  src/components/agents/__tests__/AgentsPanel.test.tsx \
  src/components/agents/__tests__/AddAgentModal.test.tsx \
  src/components/agents/__tests__/AgentChatFlow.test.tsx \
  src/components/pipeline/ExecutionGroupCard.test.tsx \
  src/components/pipeline/PipelineModelDropdown.test.tsx \
  src/components/pipeline/PipelineRunHistory.test.tsx \
  src/lib/route-suggestions.test.ts \
  src/lib/commands/registry.test.ts \
  src/context/SyncStatusContext.test.tsx
```

### Final suite gates

```bash
cd /home/runner/work/solune/solune/solune/backend
uv run pytest tests/unit/ --cov=src --cov-report=term-missing -q
uv run ruff check src tests
uv run pyright src

cd /home/runner/work/solune/solune/solune/frontend
npm run test:coverage
npm run lint
npm run type-check
npm run type-check:test
npm run build
```

## Key Planning Decisions

| Decision | Why |
|----------|-----|
| Extend existing suites before creating new ones | Keeps test ownership localized and matches current repo patterns |
| Fix defects inline with tests | Required by the spec and produces clear regression proof |
| Delay frontend work until backend P1 stabilization | Backend defects have higher user and reliability impact and should not be masked by unrelated frontend failures |
| Keep contracts limited to real HTTP surfaces | Avoids inventing fake APIs for internal utilities/services |

## Complexity Tracking

No constitutional violations require justification at planning time.
