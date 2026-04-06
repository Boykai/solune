# Feature Specification: Full Coverage Push + Bug Fixes

**Branch**: `001-test-coverage-bugfixes` | **Date**: 2026-04-06 | **Priority**: P1
**Parent Issue**: [#960](https://github.com/Boykai/solune/issues/960)

## Summary

Increase test coverage across frontend and backend while fixing 4 discovered bugs: 2 concurrency race conditions in copilot polling, stale polling test mocks, and a missing agent preview regression test. 5 phases ordered by risk/impact.

## User Stories

### US-1 (P1): Fix Polling State Race Condition

**As** a platform operator,
**I want** copilot polling state mutations to be atomic,
**So that** concurrent polling cycles do not produce stale or corrupted state.

**Acceptance Criteria:**
- Given concurrent polling loops modifying `_polling_state`,
  When mutations interleave,
  Then the latest write always wins (no stale overwrites).
- `test_interleaving.py` xfail marker is removed and the test passes.

### US-2 (P1): Fix Duplicate Polling Tasks

**As** a platform operator,
**I want** `ensure_polling_started()` to atomically check-and-create polling tasks,
**So that** concurrent startup calls never create duplicate polling tasks.

**Acceptance Criteria:**
- Given two concurrent calls to `ensure_polling_started()`,
  When both reach the creation gate simultaneously,
  Then exactly one polling task is created.
- `test_polling_races.py` xfail marker is removed and the test passes.

### US-3 (P1): Update Stale Polling Test Mocks

**As** a developer,
**I want** test_api_projects.py to mock current API surfaces,
**So that** tests remain valid as internal implementations evolve.

**Acceptance Criteria:**
- `get_project_repository()` / `poll_for_copilot_completion()` patches are replaced with `resolve_repository()` / `ensure_polling_started()` mocks.
- No references to deprecated patch targets remain in test_api_projects.py.

### US-4 (P2): Agent Preview Regression Test

**As** a developer,
**I want** a regression test for malformed agent tool configs,
**So that** `_extract_agent_preview()` safely returns None for invalid input.

**Acceptance Criteria:**
- A test in test_agents_service.py passes a `"read"` config (non-list tools) to `_extract_agent_preview()` and asserts it returns None.

### US-5 (P2): Backend MCP Server Coverage

**As** a developer,
**I want** unit tests for MCP middleware, tools, resources, and prompts,
**So that** backend coverage rises from ~79% toward 81%+.

**Acceptance Criteria:**
- test_mcp_middleware.py covers valid token, missing header, malformed token, context cleanup.
- test_mcp_tools.py covers chores CRUD, chat operations, activity limit boundaries.
- test_mcp_resources.py covers resource type branches, prompt template selection.
- test_api_templates.py covers category enum filtering, 404, pagination.

### US-6 (P2): Frontend Scroll Behavior Coverage

**As** a developer,
**I want** tests for PageTransition, CleanUpSummary scroll lock, and page section IDs,
**So that** scroll-related regressions are caught by CI.

**Acceptance Criteria:**
- PageTransition.test.tsx tests pathname-based remount and animation class.
- CleanUpSummary.test.tsx verifies useScrollLock is invoked.
- Page tests verify section IDs (#agents-catalog, #chores-catalog, #tools-catalog) render.

### US-7 (P2): Frontend Board Component Coverage

**As** a developer,
**I want** tests for board components (CleanUpButton, PipelineStagesSection, AddAgentPopover, drag overlays),
**So that** board coverage rises from 42% toward 55%+.

**Acceptance Criteria:**
- CleanUpButton.test.tsx tests the cleanup workflow orchestration.
- PipelineStagesSection.test.tsx tests pipeline stages and agent dropdown.
- AddAgentPopover.test.tsx tests Radix Popover and async fetch.
- Drag overlay + config components have smoke + a11y tests.

## Scope

**In Scope:** Concurrency bug fixes (asyncio.Lock), stale mock refactoring, regression test, MCP server coverage, frontend scroll/board coverage.

**Out of Scope:** otel_setup.py (infrastructure-only), deep DnD interaction testing (deferred), backend API branch coverage follow-up.

## Decisions

- **Concurrency approach**: `asyncio.Lock` — simplest correct fix for low-contention paths.
- **MCP tests**: Unit-only with mocked services (defensive coverage).
- **Frontend drag overlays (5.4)**: Smoke + a11y only, lowest priority.
