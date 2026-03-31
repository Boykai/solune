# Implementation Plan: Increase Backend Test Coverage & Fix Bugs

**Branch**: `002-backend-test-coverage` | **Date**: 2026-03-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-backend-test-coverage/spec.md`

## Summary

Increase backend test coverage from 78.3% toward ~85% by adding targeted tests for the 4 lowest-coverage source files: `projects.py` (37.7% → ~70%), `agent_creator.py` (39.4% → ~65%), `agents/service.py` (47.4% → ~70%), and `chores/service.py` (51.3% → ~75%). Phase 1 (fixing 9 broken async tests in `test_agent_provider.py`) is already completed. This plan covers Phases 2–6: writing new unit tests for error paths, caching edge cases, WebSocket lifecycle, multi-step pipelines, CAS trigger semantics, and SQL injection defense — all following existing test patterns and fixtures with no infrastructure refactoring.

## Technical Context

**Language/Version**: Python >=3.12 (pyright target: py313)
**Primary Dependencies**: FastAPI >=0.135.0, pytest >=9.0.0, pytest-asyncio >=1.3.0, aiosqlite >=0.22.0, githubkit >=0.14.6, pydantic >=2.12.0
**Storage**: SQLite via aiosqlite (settings.db — projects, agent configs, chores, MCP tool configs)
**Testing**: pytest with `asyncio_mode = "auto"`, pytest-cov (fail_under=75%), ruff >=0.15.0 (lint/format), pyright >=1.1.408 (type check)
**Target Platform**: Linux server (Docker container)
**Project Type**: Web application (backend + frontend monorepo)
**Performance Goals**: N/A — test-only changes, no runtime modifications
**Constraints**: No changes to production source code; no test infrastructure refactoring; keep existing fixtures and mock patterns; async tests use auto-detected mode
**Scale/Scope**: 4,071+ existing passing tests; 4 source files targeted; ~120–160 new test functions across 4 test files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Specification-First Development — ✅ PASS

Feature spec (`spec.md`) contains 6 prioritized user stories (P1–P6) with Given-When-Then acceptance scenarios, explicit coverage targets per file, and independent testing criteria. Each user story maps to a specific source module.

### II. Template-Driven Workflow — ✅ PASS

All artifacts follow canonical templates from `.specify/templates/`. This plan follows `plan-template.md`. Generated artifacts (research.md, data-model.md, contracts/, quickstart.md) follow standard formats.

### III. Agent-Orchestrated Execution — ✅ PASS

Workflow decomposes into single-responsibility phases: specify → plan → tasks → implement. Each agent operates on well-defined inputs (previous phase artifacts) and produces specific outputs.

### IV. Test Optionality with Clarity — ✅ PASS (Tests Required)

This feature is entirely about writing tests. Tests are explicitly required by:
1. The feature specification (all 6 user stories define test scenarios)
2. The parent issue (coverage targets for each file)
3. The constitution check (FR-001 through FR-020 mandate specific test coverage)

Tests follow existing patterns in `test_api_projects.py`, `test_agent_creator.py`, `test_agents_service.py`, and `test_chores_service.py`. No TDD approach needed — we are adding tests to existing production code.

### V. Simplicity and DRY — ✅ PASS

No production code changes. All new tests reuse existing fixtures (`mock_db`, `mock_settings`, `auth_client`, service mocks) and follow established patterns (`AsyncMock`, `MagicMock`, `@pytest.mark.asyncio`). No new abstractions, frameworks, or test infrastructure introduced.

## Project Structure

### Documentation (this feature)

```text
specs/002-backend-test-coverage/
├── plan.md              # This file
├── research.md          # Phase 0 output — resolved testing decisions
├── data-model.md        # Phase 1 output — test target entity definitions
├── quickstart.md        # Phase 1 output — getting started guide
├── contracts/           # Phase 1 output — test contracts per module
│   └── test-contracts.yaml
└── tasks.md             # Phase 2 output (created by /speckit.tasks — NOT this phase)
```

### Source Code (repository root)

```text
solune/
└── backend/
    ├── src/
    │   ├── api/
    │   │   └── projects.py                      # Target: 37.7% → ~70% (NO source changes)
    │   ├── services/
    │   │   ├── agent_creator.py                  # Target: 39.4% → ~65% (NO source changes)
    │   │   ├── agents/
    │   │   │   └── service.py                    # Target: 47.4% → ~70% (NO source changes)
    │   │   └── chores/
    │   │       └── service.py                    # Target: 51.3% → ~75% (NO source changes)
    │   └── ...                                   # No other files modified
    └── tests/
        └── unit/
            ├── test_api_projects.py              # + ~30 new tests (rate limit, cache, WS, SSE)
            ├── test_agent_creator.py             # + ~25 new tests (admin, status, pipeline, AI)
            ├── test_agents_service.py            # + ~35 new tests (cache, YAML, tools, create)
            └── test_chores_service.py            # + ~30 new tests (seed, validation, CAS, trigger)
```

**Structure Decision**: Web application layout (backend monorepo). All changes are test-only — 4 test files extended, 0 production source files modified. No frontend changes needed.

## Constitution Check — Post-Design Re-evaluation

*Re-evaluated after Phase 1 design artifacts (research.md, data-model.md, contracts/, quickstart.md) are complete.*

### I. Specification-First Development — ✅ PASS (unchanged)

All design artifacts trace back to spec.md user stories and acceptance scenarios. Test contracts map to functional requirements (FR-001 through FR-020). Each test group in `test-contracts.yaml` references specific acceptance scenarios from the spec.

### II. Template-Driven Workflow — ✅ PASS (unchanged)

All artifacts follow canonical templates. Plan, research, data-model, quickstart, and contracts follow established formats from the 001-intelligent-chat-agent reference.

### III. Agent-Orchestrated Execution — ✅ PASS (unchanged)

Phase outputs are well-defined: research.md resolves unknowns → data-model.md defines test targets → contracts define test scenarios → quickstart provides implementation guide. Each artifact feeds the next phase.

### IV. Test Optionality with Clarity — ✅ PASS (unchanged)

Tests are the primary deliverable of this feature. All 6 user stories produce test code. The testing approach, mocking strategy, and async patterns are documented in research.md (R1–R8) and quickstart.md.

### V. Simplicity and DRY — ✅ PASS (unchanged)

No production code changes. All test code reuses existing fixtures, mock patterns, and test infrastructure. No new abstractions, frameworks, or helper libraries introduced. The data-model.md documents existing entities — no new entities created.

## Complexity Tracking

> No violations found. All changes are test-only, follow existing patterns, and require no new abstractions.
