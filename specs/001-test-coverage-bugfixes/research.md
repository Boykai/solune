# Research: Full Coverage Push + Bug Fixes

**Feature**: 001-test-coverage-bugfixes | **Date**: 2026-04-06

## R1: Concurrency Primitives for Polling State

**Decision**: Use `asyncio.Lock` to guard `_polling_state` mutations.

**Rationale**: The polling module uses a module-level `PollingState` dataclass singleton (`_polling_state` in `state.py` line 109). Multiple coroutines mutate its fields without synchronization — `polling_loop.py` (lines 316, 323, 404-405, 494-495, 617, 713) and `pipeline.py` (lines 1009-1010, 1102-1103, 3284-3285, 3464-3465). Since all access is within a single event loop and contention is low (polling runs on 15-second intervals), `asyncio.Lock` is the correct minimal primitive. No thread-level locks are needed because the backend is single-threaded async.

**Alternatives Considered**:
- `asyncio.Condition` — overkill; no wait/notify patterns needed.
- Thread-level `threading.Lock` — wrong granularity; all polling runs in one event loop.
- Atomic dataclass replacement — Python lacks native atomic field updates.

## R2: Duplicate Polling Task Prevention

**Decision**: Use `asyncio.Lock` around the check-then-create in `ensure_polling_started()`.

**Rationale**: The function at `__init__.py` lines 263-332 reads `get_polling_status()["is_running"]` and then creates a task if not running. Two concurrent callers can both pass the check and create duplicate tasks. Wrapping with `async with _polling_startup_lock:` makes the critical section atomic.

**Alternatives Considered**:
- `asyncio.Event` — could work for "first caller wins" but adds complexity.
- Module-level flag with CAS — Python lacks compare-and-swap; a Lock is simpler.

## R3: Test Mock Migration Strategy

**Decision**: Replace deprecated patches in `test_api_projects.py` lines 253-370 with mocks targeting current API surfaces.

**Rationale**: The tests patch `get_project_repository()` and `poll_for_copilot_completion()`, which are deprecated internal names. The current API uses `resolve_repository()` and `ensure_polling_started()`. Updating mocks prevents tests from silently passing while patching non-existent functions.

**Alternatives Considered**:
- Keep deprecated patches and add compatibility aliases — adds tech debt.
- Delete and rewrite tests entirely — unnecessary; structure is sound.

## R4: Agent Preview Guard Testing

**Decision**: Add targeted regression test for `_extract_agent_preview()` with non-list `tools` value.

**Rationale**: `service.py` lines 1465-1473 include a guard `if not isinstance(tools, list): return None`. When `tools` is a string like `"read"`, the function should return `None`. The existing `TestExtractAgentPreview` class (6 tests) covers valid configs, missing name, empty name, invalid JSON, and minimal configs, but NOT non-list tool values.

**Alternatives Considered**:
- Property-based testing with Hypothesis — overkill for a single guard check.
- Parametrized test with multiple invalid types — reasonable enhancement but single test suffices for regression.

## R5: MCP Server Test Architecture

**Decision**: Unit-only tests with mocked services, following existing patterns in `tests/unit/test_mcp_server/`.

**Rationale**: Existing test files (test_auth.py, test_middleware.py, test_resources.py, test_server.py, test_tools_agents.py, etc.) mock the MCP context and service dependencies. New tests for chores, chat, activity tools and prompts should follow the same pattern. Missing test files: test_tools_activity.py, test_tools_chat.py, test_tools_chores.py, test_prompts.py.

**Alternatives Considered**:
- Integration tests with real FastMCP server — deferred to Phase 6 feature.
- Contract tests — valuable but outside current scope.

## R6: Frontend Scroll Behavior Architecture

**Decision**: Test PageTransition via `key={pathname}` remount behavior and CSS animation class.

**Rationale**: `PageTransition.tsx` (layout/ and components/layout/ versions) uses `useLocation().pathname` as React `key` on the wrapper div. This forces a full remount on route change, which naturally resets scroll. The component applies `motion-safe:animate-page-enter` CSS class. Testing should verify: (a) key changes on pathname change, (b) animation class is present, (c) Outlet renders children.

**Alternatives Considered**:
- Testing scroll position directly — fragile in happy-dom environment.
- Testing CSS animation timing — not testable in unit tests.

## R7: Frontend Board Coverage Strategy

**Decision**: Prioritize CleanUpButton and PipelineStagesSection (high complexity, zero tests), then AddAgentPopover (medium), then smoke tests for drag overlays (low).

**Rationale**: Board directory has 22 components with 18 test files. The 7 untested components represent ~1,600 LOC. AgentConfigRow (481 LOC) and AgentPresetSelector (526 LOC) are the largest but are deferred to smoke+a11y only due to deep DnD/localStorage complexity. CleanUpButton (141 LOC) orchestrates the full cleanup workflow and is high-value. PipelineStagesSection (258 LOC) renders the pipeline editor with dropdown interactions.

**Alternatives Considered**:
- Full interaction testing for DnD components — deferred (complex setup, low regression risk).
- Snapshot testing — fragile, not recommended for dynamic components.
