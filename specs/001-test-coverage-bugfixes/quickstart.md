# Quickstart: Full Coverage Push + Bug Fixes

**Feature**: 001-test-coverage-bugfixes | **Date**: 2026-04-06

## Prerequisites

- Python 3.12+ with `uv` package manager
- Node.js 20+ with npm
- Repository cloned at project root

## Phase 1: Fix Concurrency Bugs

### Step 1.1 — Add polling state lock

```bash
# Edit state.py to add asyncio.Lock
# File: solune/backend/src/services/copilot_polling/state.py
# Add: _polling_state_lock = asyncio.Lock()

# Guard mutations in polling_loop.py and pipeline.py
# Wrap _polling_state field writes with: async with _polling_state_lock:

# Verify
cd solune/backend
PATH=$HOME/.local/bin:$PATH uv run pytest tests/concurrency/test_interleaving.py -v
```

### Step 1.2 — Add polling startup lock

```bash
# Edit state.py to add startup lock
# Add: _polling_startup_lock = asyncio.Lock()

# Wrap ensure_polling_started() check-then-create in __init__.py
# with: async with _polling_startup_lock:

# Verify
cd solune/backend
PATH=$HOME/.local/bin:$PATH uv run pytest tests/concurrency/test_polling_races.py -v
```

### Step 1.3 — Update stale test mocks

```bash
# Refactor test_api_projects.py L253-370
# Replace: get_project_repository → resolve_repository
# Replace: poll_for_copilot_completion → ensure_polling_started

# Verify no deprecated patches remain
grep -n "poll_for_copilot_completion\|get_project_repository" solune/backend/tests/unit/test_api_projects.py
# Should return no results

cd solune/backend
PATH=$HOME/.local/bin:$PATH uv run pytest tests/unit/test_api_projects.py -v
```

## Phase 2: Backend Bug Regression Test

```bash
# Add test to test_agents_service.py for non-list tools
# Test: _extract_agent_preview() with tools="read" returns None

cd solune/backend
PATH=$HOME/.local/bin:$PATH uv run pytest tests/unit/test_agents_service.py::TestExtractAgentPreview -v
```

## Phase 3: Backend MCP Server Coverage

```bash
# Create/enhance test files in tests/unit/test_mcp_server/
# New: test_tools_chores.py, test_tools_chat.py, test_tools_activity.py
# Enhance: test_middleware.py, test_resources.py

cd solune/backend
PATH=$HOME/.local/bin:$PATH uv run pytest tests/unit/test_mcp_server/ -v --cov=src/services/mcp_server --cov-report=term-missing
```

## Phase 4: Frontend Scroll Behavior Coverage

```bash
cd solune/frontend

# Create PageTransition.test.tsx
# Enhance CleanUpSummary.test.tsx
# Add section ID checks to page tests

npm run test -- --run src/layout/PageTransition.test.tsx
npm run test -- --run src/components/board/CleanUpSummary.test.tsx
```

## Phase 5: Frontend Board Component Coverage

```bash
cd solune/frontend

# Create: CleanUpButton.test.tsx, PipelineStagesSection.test.tsx, AddAgentPopover.test.tsx
# Create smoke tests: AgentDragOverlay.test.tsx, BoardDragOverlay.test.tsx, etc.

npm run test -- --run src/components/board/CleanUpButton.test.tsx
npm run test -- --run src/components/board/PipelineStagesSection.test.tsx
npm run test -- --run src/components/board/AddAgentPopover.test.tsx
```

## Full Verification

```bash
# Backend
cd solune/backend
PATH=$HOME/.local/bin:$PATH uv run pytest tests/concurrency/ -v
PATH=$HOME/.local/bin:$PATH uv run pytest tests/unit/ -v --cov=src --cov-report=term-missing
PATH=$HOME/.local/bin:$PATH uv run ruff check src tests
PATH=$HOME/.local/bin:$PATH uv run pyright src

# Frontend
cd solune/frontend
npm run lint
npm run type-check
npm run test:coverage

# Verify no deprecated patches
grep -rn "poll_for_copilot_completion" solune/backend/tests/unit/test_api_projects.py
# Should return nothing
```
