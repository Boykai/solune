# Implementation Plan: Full Coverage Push + Bug Fixes

**Branch**: `001-test-coverage-bugfixes` | **Date**: 2026-04-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-test-coverage-bugfixes/spec.md`

## Summary

Fix 4 discovered bugs (2 concurrency race conditions in copilot polling, stale polling test mocks, missing agent preview regression test) and increase test coverage across both stacks. Backend target: 79% → 81%+. Frontend board target: 42% → 55%+. Approach: `asyncio.Lock` for concurrency, unit-only mocked tests for MCP server, Vitest with component renders for frontend.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript ~6.0.2 + React 19.2 (frontend)
**Primary Dependencies**: FastAPI, asyncio, pytest (backend); Vitest, happy-dom, Radix UI (frontend)
**Storage**: N/A — no schema changes; runtime state only (`PollingState` dataclass)
**Testing**: pytest + coverage (backend), Vitest + v8 coverage (frontend)
**Target Platform**: Linux server (backend), Browser SPA (frontend)
**Project Type**: Web application (monorepo with backend + frontend)
**Performance Goals**: N/A — bug fixes and tests only; no performance-critical paths changed
**Constraints**: Backend coverage ≥ 75% CI gate; Frontend statements ≥ 50%, branches ≥ 44%, functions ≥ 41%, lines ≥ 50%
**Scale/Scope**: ~14 mutation sites to guard with locks; ~12 new/enhanced test files; ~20 new test cases backend; ~30 new test cases frontend

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Specification-First** | ✅ PASS | spec.md created with 7 prioritized user stories, acceptance criteria, and scope |
| **II. Template-Driven** | ✅ PASS | All artifacts follow canonical templates from `.specify/templates/` |
| **III. Agent-Orchestrated** | ✅ PASS | speckit.plan produces plan.md, research.md, data-model.md, quickstart.md, contracts/ |
| **IV. Test Optionality** | ✅ PASS | Tests ARE explicitly requested — this is a test-coverage feature. TDD not applicable (tests are the deliverable) |
| **V. Simplicity and DRY** | ✅ PASS | `asyncio.Lock` is the simplest correct fix. No new abstractions. Unit mocks follow existing patterns |

**Post-Design Re-Check (Phase 1)**:

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Specification-First** | ✅ PASS | All research findings traced back to spec user stories |
| **II. Template-Driven** | ✅ PASS | Artifacts generated per template structure |
| **III. Agent-Orchestrated** | ✅ PASS | Phase handoff complete |
| **IV. Test Optionality** | ✅ PASS | Tests mandated by spec |
| **V. Simplicity and DRY** | ✅ PASS | No complexity violations identified |

## Project Structure

### Documentation (this feature)

```text
specs/001-test-coverage-bugfixes/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification
├── research.md          # Phase 0 output — 7 research decisions
├── data-model.md        # Phase 1 output — PollingState modifications + lock additions
├── quickstart.md        # Phase 1 output — step-by-step verification commands
├── contracts/
│   └── contracts.md     # Phase 1 output — internal contracts (no new APIs)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   ├── services/
│   │   ├── copilot_polling/
│   │   │   ├── state.py           # Add _polling_state_lock, _polling_startup_lock
│   │   │   ├── polling_loop.py    # Guard _polling_state mutations with lock
│   │   │   ├── pipeline.py        # Guard _polling_state mutations with lock
│   │   │   └── __init__.py        # Guard ensure_polling_started() with lock
│   │   ├── agents/
│   │   │   └── service.py         # Existing guard — regression test target
│   │   └── mcp_server/
│   │       ├── middleware.py       # Test target (41% → 80%+)
│   │       ├── resources.py        # Test target (46% → 70%+)
│   │       ├── prompts.py          # Test target (65% → 85%+)
│   │       └── tools/
│   │           ├── chores.py       # Test target (20% → 70%+)
│   │           ├── chat.py         # Test target (25% → 70%+)
│   │           └── activity.py     # Test target (30% → 70%+)
│   └── api/
│       └── templates.py            # Test target (52% → 75%+)
└── tests/
    ├── concurrency/
    │   ├── test_interleaving.py    # Remove xfail — US-1
    │   └── test_polling_races.py   # Remove xfail — US-2
    └── unit/
        ├── test_api_projects.py    # Refactor deprecated mocks — US-3
        ├── test_agents_service.py  # Add regression test — US-4
        ├── test_api_templates.py   # Enhance — US-5
        └── test_mcp_server/
            ├── test_middleware.py   # Enhance — US-5
            ├── test_resources.py   # Enhance — US-5
            ├── test_tools_chores.py  # New — US-5
            ├── test_tools_chat.py    # New — US-5
            └── test_tools_activity.py # New — US-5

solune/frontend/
├── src/
│   ├── layout/
│   │   └── PageTransition.tsx      # Test target — US-6
│   └── components/
│       └── board/
│           ├── CleanUpSummary.tsx   # Enhance test — US-6
│           ├── CleanUpButton.tsx    # New test — US-7
│           ├── PipelineStagesSection.tsx # New test — US-7
│           ├── AddAgentPopover.tsx  # New test — US-7
│           ├── AgentDragOverlay.tsx # Smoke test — US-7
│           ├── BoardDragOverlay.tsx # Smoke test — US-7
│           ├── AgentColumnCell.tsx  # Smoke test — US-7
│           ├── AgentConfigRow.tsx   # Smoke test — US-7
│           └── AgentPresetSelector.tsx # Smoke test — US-7
└── (test files co-located with components)
```

**Structure Decision**: Web application (Option 2). Backend at `solune/backend/`, frontend at `solune/frontend/`. Both already exist with established test infrastructure.

## Implementation Phases

### Phase 1: Fix Concurrency Bugs (blocking — highest risk)

| Step | File(s) | Action | User Story |
|------|---------|--------|------------|
| 1.1 | `state.py` | Add `_polling_state_lock = asyncio.Lock()` | US-1 |
| 1.1 | `polling_loop.py` (L316,323,404-405,494-495,617,713) | Guard mutations with `async with _polling_state_lock` | US-1 |
| 1.1 | `pipeline.py` (L1009-1010,1102-1103,3284-3285,3464-3465) | Guard mutations with `async with _polling_state_lock` | US-1 |
| 1.1 | `test_interleaving.py` | Remove `@pytest.mark.xfail` | US-1 |
| 1.2 | `state.py` | Add `_polling_startup_lock = asyncio.Lock()` | US-2 |
| 1.2 | `__init__.py` (~L263-332) | Wrap check-and-create with `async with _polling_startup_lock` | US-2 |
| 1.2 | `test_polling_races.py` | Remove `@pytest.mark.xfail` | US-2 |
| 1.3 | `test_api_projects.py` (L253-370) | Replace deprecated patches with current API mocks | US-3 |

**Dependencies**: None (blocking — must complete before Phases 2-5).
**Verification**: `pytest tests/concurrency/ -v` — both tests pass. `grep poll_for_copilot_completion test_api_projects.py` returns nothing.

### Phase 2: Backend Bug Regression Tests (parallel with Phase 3)

| Step | File(s) | Action | User Story |
|------|---------|--------|------------|
| 2.1 | `test_agents_service.py` | Add test: `tools="read"` → `_extract_agent_preview()` returns None | US-4 |

**Dependencies**: Phase 1 complete.
**Verification**: `pytest tests/unit/test_agents_service.py::TestExtractAgentPreview -v`

### Phase 3: Backend MCP Server Coverage (parallel with Phase 2)

| Step | File(s) | Action | User Story |
|------|---------|--------|------------|
| 3.1 | `test_mcp_middleware.py` | Enhance: edge cases for header parsing, context cleanup, error paths | US-5 |
| 3.2 | `test_tools_chores.py` (new) | CRUD operations, error dicts | US-5 |
| 3.2 | `test_tools_chat.py` (new) | send_chat_message, get_metadata, cleanup_preflight | US-5 |
| 3.2 | `test_tools_activity.py` (new) | get_activity (limit boundaries), update_item_status | US-5 |
| 3.3 | `test_resources.py` | Enhance: resource type branches, error paths | US-5 |
| 3.4 | `test_api_templates.py` | Enhance: category enum filtering, 404, pagination | US-5 |

**Dependencies**: Phase 1 complete.
**Verification**: `pytest tests/unit/test_mcp_server/ -v --cov=src/services/mcp_server --cov-report=term-missing`

### Phase 4: Frontend Scroll Behavior Coverage

| Step | File(s) | Action | User Story |
|------|---------|--------|------------|
| 4.1 | `PageTransition.test.tsx` (new) | Test key={pathname} remount, animation class, null guard | US-6 |
| 4.2 | `CleanUpSummary.test.tsx` | Enhance: verify useScrollLock invocation | US-6 |
| 4.3 | Page test files | Verify section IDs render; test scrollIntoView in AgentsPipelinePage | US-6 |

**Dependencies**: Phase 1 complete.
**Verification**: `npx vitest run --run src/layout/PageTransition.test.tsx src/components/board/CleanUpSummary.test.tsx`

### Phase 5: Frontend Board Component Coverage

| Step | File(s) | Priority | User Story |
|------|---------|----------|------------|
| 5.1 | `CleanUpButton.test.tsx` (new) | High | US-7 |
| 5.2 | `PipelineStagesSection.test.tsx` (new) | High | US-7 |
| 5.3 | `AddAgentPopover.test.tsx` (new) | Medium | US-7 |
| 5.4 | `AgentDragOverlay.test.tsx`, `BoardDragOverlay.test.tsx`, `AgentColumnCell.test.tsx`, `AgentConfigRow.test.tsx`, `AgentPresetSelector.test.tsx` (new) | Low — smoke + a11y only | US-7 |

**Dependencies**: Phase 1 complete.
**Verification**: `npx vitest run --coverage` — board coverage 42% → 55%+; all thresholds pass.

## Verification Summary

| Command | Expected Result |
|---------|----------------|
| `pytest tests/concurrency/ -v` | Both formerly-xfail tests pass |
| `pytest tests/unit/ -v --cov=src --cov-report=term-missing` | Coverage 79% → 81%+ |
| `npx vitest run --coverage` | Board 42% → 55%+; all thresholds pass |
| `pyright src` | No new type errors |
| `npx tsc --noEmit` | No new type errors |
| `grep poll_for_copilot_completion test_api_projects.py` | No matches |

## Decisions

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| `asyncio.Lock` for concurrency | Simplest correct fix for low-contention single-event-loop paths | `asyncio.Condition` (overkill), `threading.Lock` (wrong granularity) |
| Unit-only MCP tests | Follows existing test_mcp_server/ patterns; integration deferred | Integration tests (Phase 6 scope) |
| Smoke + a11y for drag overlays | Complex DnD setup, low regression risk | Full interaction testing (deferred) |
| Excluded: otel_setup.py | Infrastructure-only, marginal test value | — |

## Complexity Tracking

> No constitution violations identified. No complexity justifications needed.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | — | — |
