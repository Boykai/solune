# Implementation Plan: Add Authenticated E2E Tests for Core Application

**Branch**: `001-authenticated-e2e-tests` | **Date**: 2026-03-30 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/001-authenticated-e2e-tests/spec.md`

## Summary

Add a comprehensive authenticated end-to-end test suite that exercises the core application flows (auth lifecycle, project CRUD, chat, pipelines, board operations) through the real FastAPI application. Tests use the dev-login endpoint for session bootstrapping with a real in-memory SQLite session store, mocking only external services (GitHub API, AI agents, WebSocket manager). An optional Phase 2 extends the frontend Playwright E2E fixtures to return authenticated user data and realistic API responses.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript (frontend)  
**Primary Dependencies**: FastAPI >=0.135.0, httpx >=0.28.0 (test client), pytest >=9.0.0, pytest-asyncio >=1.3.0, aiosqlite >=0.22.0, Playwright (frontend E2E)  
**Storage**: In-memory SQLite with migrations applied (`aiosqlite`, `:memory:` database path)  
**Testing**: pytest with `asyncio_mode = "auto"`, httpx `AsyncClient` with `ASGITransport` for ASGI-level requests  
**Target Platform**: Linux CI (GitHub Actions), local dev (macOS/Linux)  
**Project Type**: Web application (monorepo: `solune/backend/` + `solune/frontend/`)  
**Performance Goals**: Each E2E test completes within 5 seconds (SC-004)  
**Constraints**: Zero external network calls; all GitHub API / AI agent calls mocked; test isolation via fresh app + DB per test  
**Scale/Scope**: ~6 test files, ~25-35 test cases covering 5 authenticated flow domains + 1 frontend extension

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Specification-First** | ✅ PASS | `spec.md` contains 6 prioritized user stories (P1–P6) with Given-When-Then acceptance scenarios |
| **II. Template-Driven** | ✅ PASS | All artifacts follow canonical templates from `.specify/templates/` |
| **III. Agent-Orchestrated** | ✅ PASS | Plan phase produces `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` |
| **IV. Test Optionality** | ✅ PASS | This feature IS the tests — tests are the primary deliverable, explicitly requested in the specification. Test-first ordering applies: conftest fixtures (foundation) precede individual test files |
| **V. Simplicity & DRY** | ✅ PASS | Reuses existing patterns from `tests/conftest.py` (`make_mock_github_service`, `_apply_migrations`), existing `test_api_e2e.py` patterns, and `test_full_workflow.py` app assembly. No new abstractions introduced beyond necessary fixtures |

**Gate Result**: ✅ All principles satisfied. Proceeding to Phase 0 research.

## Project Structure

### Documentation (this feature)

```text
specs/001-authenticated-e2e-tests/
├── plan.md              # This file
├── research.md          # Phase 0: Research findings
├── data-model.md        # Phase 1: Test entity model
├── quickstart.md        # Phase 1: Getting started guide
├── contracts/           # Phase 1: Test contract definitions
│   └── test-fixtures.md # Fixture contracts and interfaces
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/backend/
├── src/
│   ├── api/
│   │   ├── auth.py              # dev-login, logout, get_current_session (existing)
│   │   ├── projects.py          # project CRUD, select_project (existing)
│   │   ├── chat.py              # send_message, get_messages (existing)
│   │   ├── pipelines.py         # pipeline CRUD, runs (existing)
│   │   └── board.py             # board data, status updates (existing)
│   ├── services/
│   │   ├── github_auth.py       # GitHubAuthService, create_session_from_token (existing)
│   │   ├── session_store.py     # save_session, get_session, delete_session (existing)
│   │   └── github_projects.py   # GitHubProjectsService (mocked in E2E)
│   ├── models/
│   │   └── user.py              # UserSession, UserResponse (existing)
│   ├── dependencies.py          # get_github_service, verify_project_access (existing)
│   ├── main.py                  # create_app() factory (existing)
│   └── migrations/              # SQL migration files (existing)
├── tests/
│   ├── conftest.py              # Existing shared fixtures (existing)
│   ├── test_api_e2e.py          # Existing unauthenticated E2E tests (existing)
│   ├── e2e/                     # NEW: Authenticated E2E test suite
│   │   ├── conftest.py          # Auth client fixture, mock_db_with_migrations
│   │   ├── test_auth_flow.py    # Auth lifecycle tests
│   │   ├── test_projects_flow.py # Project operations tests
│   │   ├── test_chat_flow.py    # Chat flow tests
│   │   ├── test_pipeline_flow.py # Pipeline CRUD tests
│   │   └── test_board_flow.py   # Board operations tests
│   └── helpers/
│       ├── factories.py         # Test data factories (existing)
│       └── assertions.py        # Custom assertions (existing)
└── pyproject.toml               # pytest config (existing, no changes needed)

solune/frontend/
├── e2e/
│   ├── fixtures.ts              # Unauthenticated fixture pattern (existing)
│   ├── authenticated-fixtures.ts # NEW: Authenticated fixture extension
│   └── authenticated-flows.spec.ts # NEW: Authenticated UI flow tests
└── playwright.config.ts         # Playwright config (existing)
```

**Structure Decision**: Web application monorepo structure. Backend E2E tests are placed in a new `tests/e2e/` directory to separate authenticated multi-request flow tests from the existing `tests/test_api_e2e.py` (which tests individual unauthenticated endpoints) and `tests/integration/` (which tests webhook/pipeline workflows). Frontend E2E tests extend the existing `e2e/` directory pattern.

## Complexity Tracking

> No constitution violations detected. No complexity justifications required.
