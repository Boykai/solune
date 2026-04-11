# Quickstart: Codebase Modularity Review

**Feature**: Codebase Modularity Review | **Date**: 2026-04-11

## Overview

This guide walks through executing the six refactoring phases defined in `plan.md`. Each phase is independently verifiable — run the test suite after each phase to confirm no regressions.

## Prerequisites

- Python ≥3.12 with virtual environment
- Node.js ≥18 with npm
- Git
- Familiarity with FastAPI routing patterns and TypeScript module resolution

## Pre-Refactor Baseline

Before starting, establish a clean test baseline:

```bash
# Backend — confirm all tests pass
cd solune/backend
python -m pytest tests/unit/ -q --timeout=120
# Expected: 5,200+ tests passed

# Frontend — confirm all tests pass
cd solune/frontend
npm test
# Expected: 2,200+ tests passed
```

## Phase 1: Split `api/chat.py` → `api/chat/` Package

### Step 1: Create package structure

```bash
cd solune/backend/src/api

# Create the chat package directory
mkdir -p chat

# Create __init__.py for backward-compatible imports
cat > chat/__init__.py << 'EOF'
"""Chat API package — split from monolithic chat.py for maintainability."""
from src.api.chat.router import router  # noqa: F401

__all__ = ["router"]
EOF
```

### Step 2: Extract ChatStateManager

Create `api/chat/state.py` with the `ChatStateManager` class. This replaces the three module-level dicts (`_messages`, `_proposals`, `_locks`).

Key implementation notes:
- Use `BoundedDict` from `src.utils` for the locks dictionary (capacity: 10,000)
- Provide `get_chat_state()` dependency function that reads from `app.state`
- Register the instance in `main.py` lifespan function

### Step 3: Extract endpoint modules

For each endpoint group, create its module:

1. **`chat/conversations.py`** — Move `create_conversation`, `list_conversations`, `update_conversation`, `delete_conversation`
2. **`chat/messages.py`** — Move `get_messages`, `clear_messages`, `send_message`, plus helpers (`_persist_message`, `_retry_persist`, `store_proposal`, `store_recommendation`, etc.)
3. **`chat/proposals.py`** — Move `confirm_proposal`, `cancel_proposal`, `upload_file`
4. **`chat/plans.py`** — Move all `/plans/*` endpoints and `send_plan_message`
5. **`chat/streaming.py`** — Move `send_message_stream`, `send_plan_message_stream`

Each module creates its own `router = APIRouter()` and registers endpoints on it.

### Step 4: Create combined router

```python
# api/chat/router.py
from fastapi import APIRouter

from src.api.chat.conversations import router as conversations_router
from src.api.chat.messages import router as messages_router
from src.api.chat.proposals import router as proposals_router
from src.api.chat.plans import router as plans_router
from src.api.chat.streaming import router as streaming_router

router = APIRouter()
router.include_router(conversations_router)
router.include_router(messages_router)
router.include_router(proposals_router)
router.include_router(plans_router)
router.include_router(streaming_router)
```

### Step 5: Update test patch targets

```bash
# Find all test files that patch api.chat
cd solune/backend
grep -rn "patch.*src\.api\.chat" tests/ | head -50

# Update each patch target to the new module path
# Example: 'src.api.chat._messages' → use ChatStateManager mock
# Example: 'src.api.chat.confirm_proposal' → 'src.api.chat.proposals.confirm_proposal'
```

### Step 6: Delete old monolithic file

```bash
# Only after all tests pass with the new package
rm solune/backend/src/api/chat.py
```

### Step 7: Verify

```bash
cd solune/backend
python -m pytest tests/unit/ -q --timeout=120
pyright src/
ruff check src/
```

---

## Phase 2: Extract ProposalOrchestrator Service

### Step 1: Create the service

Create `services/proposal_orchestrator.py` with the `ProposalOrchestrator` class. Extract the five logical steps from `confirm_proposal()` into separate methods.

### Step 2: Create dependency function

```python
# In services/proposal_orchestrator.py or api/chat/proposals.py
async def get_proposal_orchestrator(request: Request) -> ProposalOrchestrator:
    return ProposalOrchestrator(
        github_service=get_github_service(request),
        connection_manager=get_connection_manager(request),
        copilot_poller=request.app.state.copilot_poller,
    )
```

### Step 3: Update the endpoint

The `confirm_proposal` endpoint in `api/chat/proposals.py` becomes a thin wrapper:

```python
@router.post("/proposals/{proposal_id}/confirm", response_model=AITaskProposal)
async def confirm_proposal(
    proposal_id: str,
    session: UserSession = Depends(require_session),
    orchestrator: ProposalOrchestrator = Depends(get_proposal_orchestrator),
    state: ChatStateManager = Depends(get_chat_state),
):
    proposal = state.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return await orchestrator.confirm(proposal, session)
```

### Step 4: Verify

```bash
cd solune/backend
python -m pytest tests/unit/ -q --timeout=120
```

---

## Phase 3: Split `api/webhooks.py` → `api/webhooks/` Package

Follow the same pattern as Phase 1:

1. Create `api/webhooks/` directory with `__init__.py`
2. Extract `helpers.py` (signature verification, issue extraction, PR classification)
3. Extract `pull_requests.py` (PR event handlers)
4. Extract `check_runs.py` (check run/suite event handlers)
5. Create `router.py` (main dispatcher endpoint)
6. Update test patch targets
7. Delete old `api/webhooks.py`
8. Verify with full test suite

---

## Phase 4: Split `services/api.ts` → `services/api/` Directory

### Step 1: Create directory and client module

```bash
cd solune/frontend/src/services
mkdir -p api
```

Extract `ApiError`, `onAuthExpired()`, and base fetch utilities into `api/client.ts`.

### Step 2: Extract domain API modules

For each namespace object in the current `api.ts`, create a domain file:

```bash
# Create each domain file
touch api/auth.ts api/chat.ts api/board.ts api/projects.ts api/tasks.ts
touch api/settings.ts api/workflow.ts api/agents.ts api/signal.ts api/metadata.ts
```

Move each namespace object to its domain file. Each file imports shared utilities from `./client`.

### Step 3: Create barrel re-export

```typescript
// services/api/index.ts
export { ApiError, onAuthExpired } from './client';
export { authApi } from './auth';
export { chatApi, conversationApi } from './chat';
export { boardApi } from './board';
export { projectsApi } from './projects';
export { tasksApi } from './tasks';
export { settingsApi } from './settings';
export { workflowApi } from './workflow';
export type { AgentConfig, McpServerConfig, AgentCreateRequest, AgentUpdateRequest,
  AgentConfigResponse, AgentListResponse, McpServerConfigResponse, AgentDeleteResponse } from './agents';
export { agentApi, mcpConfigApi } from './agents';
export { signalApi } from './signal';
export { metadataApi, mcpApi, cleanupApi, choresApi } from './metadata';
```

### Step 4: Delete old monolithic file

```bash
rm solune/frontend/src/services/api.ts
```

### Step 5: Verify

```bash
cd solune/frontend
npx tsc --noEmit          # Type check
npm run build             # Build check
npm test                  # Test suite
```

---

## Phase 5: Domain-Scoped Types

### Step 1: Analyze dependencies

```bash
# Find which types are imported by which files
cd solune/frontend/src
grep -rn "from.*types" --include="*.ts" --include="*.tsx" | head -50
```

### Step 2: Create domain type files

Extract types into domain files following the dependency graph in `data-model.md`:

1. `types/common.ts` — shared enums and base types (no dependencies)
2. `types/tasks.ts` — imports from `common.ts`
3. `types/chat.ts` — imports from `common.ts` and `tasks.ts`
4. `types/board.ts` — imports from `common.ts`
5. `types/pipeline.ts` — imports from `common.ts`
6. `types/plans.ts` — imports from `common.ts`
7. `types/agents.ts` — imports from `common.ts`
8. `types/settings.ts` — no dependencies

### Step 3: Update barrel

```typescript
// types/index.ts
export * from './common';
export * from './chat';
export * from './board';
export * from './tasks';
export * from './pipeline';
export * from './plans';
export * from './agents';
export * from './settings';
```

### Step 4: Verify

```bash
cd solune/frontend
npx tsc --noEmit
npm run build
npm test
```

---

## Phase 6: Final Verification

### Full test suite

```bash
# Backend
cd solune/backend
python -m pytest tests/unit/ -q --timeout=120    # All 5,200+ tests
pyright src/                                       # Type checking
ruff check src/                                    # Linting

# Frontend
cd solune/frontend
npm test                                           # All 2,200+ tests
npx tsc --noEmit                                   # Type checking
npm run lint                                       # ESLint
npm run build                                      # Production build
```

### Import audit

```bash
# Backend — verify no imports reference deleted files
cd solune/backend
grep -rn "from src.api.chat import\|from src.api import chat" src/ tests/ | grep -v __pycache__
# Should only show: from src.api.chat import router (via __init__.py)

grep -rn "from src.api.webhooks import\|from src.api import webhooks" src/ tests/ | grep -v __pycache__
# Should only show: from src.api.webhooks import router (via __init__.py)

# Frontend — verify no imports reference deleted files
cd solune/frontend
grep -rn "from.*services/api'" src/ | grep -v node_modules
# Should resolve to services/api/index.ts (barrel)

grep -rn "from.*services/api.ts" src/ | grep -v node_modules
# Should return zero results (old file deleted)
```

### Module size audit

```bash
# Backend — verify no module exceeds 500 lines
cd solune/backend/src/api
wc -l chat/*.py webhooks/*.py

# Frontend — verify no module exceeds 500 lines
cd solune/frontend/src
wc -l services/api/*.ts types/*.ts
```

## Troubleshooting

### Import errors after splitting

If `ModuleNotFoundError: No module named 'src.api.chat'` appears:
1. Verify `api/chat/__init__.py` exists
2. Check that `from src.api.chat.router import router` works in a Python shell
3. Ensure no stale `.pyc` files: `find . -name "*.pyc" -delete && find . -name "__pycache__" -type d -exec rm -rf {} +`

### Test patch targets broken

If tests fail with `ModuleNotFoundError` in `patch()` calls:
1. Run `grep -rn "patch.*src.api.chat" tests/` to find all occurrences
2. Update the target path to the new module (e.g., `src.api.chat.messages.send_message`)
3. For patching global state, replace `patch('src.api.chat._messages', ...)` with mocking `ChatStateManager`

### TypeScript barrel resolution issues

If imports from `services/api` fail:
1. Verify `services/api/index.ts` exists with correct re-exports
2. Run `npx tsc --traceResolution` to debug module resolution
3. Check that no `tsconfig.json` path aliases conflict

### Circular import errors

If Python raises `ImportError: cannot import name 'X' from partially initialized module`:
1. Check for circular imports between the new modules (e.g., `messages.py` ↔ `streaming.py`)
2. Use late imports or restructure the dependency (extract shared code to `state.py` or a `_helpers.py`)

## Key Files Reference

### Backend (new files)

| File | Purpose |
|------|---------|
| `src/api/chat/__init__.py` | Package entry; re-exports router |
| `src/api/chat/state.py` | ChatStateManager class |
| `src/api/chat/conversations.py` | Conversation CRUD endpoints |
| `src/api/chat/messages.py` | Message endpoints + persistence |
| `src/api/chat/proposals.py` | Proposal confirm/cancel + upload |
| `src/api/chat/plans.py` | Plan management endpoints |
| `src/api/chat/streaming.py` | SSE streaming endpoints |
| `src/api/chat/router.py` | Combined router |
| `src/services/proposal_orchestrator.py` | Extracted proposal workflow |
| `src/api/webhooks/__init__.py` | Package entry; re-exports router |
| `src/api/webhooks/helpers.py` | Shared webhook utilities |
| `src/api/webhooks/pull_requests.py` | PR event handlers |
| `src/api/webhooks/check_runs.py` | Check run/suite handlers |
| `src/api/webhooks/router.py` | Webhook dispatcher |

### Frontend (new files)

| File | Purpose |
|------|---------|
| `src/services/api/index.ts` | Barrel re-export |
| `src/services/api/client.ts` | Base HTTP client |
| `src/services/api/auth.ts` | Auth API |
| `src/services/api/chat.ts` | Chat + conversation API |
| `src/services/api/board.ts` | Board API |
| `src/services/api/projects.ts` | Projects API |
| `src/services/api/tasks.ts` | Tasks API |
| `src/services/api/settings.ts` | Settings API |
| `src/services/api/workflow.ts` | Workflow API |
| `src/services/api/agents.ts` | Agent + MCP config API |
| `src/services/api/signal.ts` | Signal API |
| `src/services/api/metadata.ts` | Metadata, MCP, cleanup, chores API |
| `src/types/common.ts` | Shared enums, base types |
| `src/types/chat.ts` | Chat domain types |
| `src/types/board.ts` | Board types |
| `src/types/tasks.ts` | Task types |
| `src/types/pipeline.ts` | Pipeline types |
| `src/types/plans.ts` | Plan types |
| `src/types/agents.ts` | Agent types |
| `src/types/settings.ts` | Settings types |

### Deleted files

| File | Replaced By |
|------|-------------|
| `src/api/chat.py` | `src/api/chat/` package |
| `src/api/webhooks.py` | `src/api/webhooks/` package |
| `src/services/api.ts` | `src/services/api/` directory |
