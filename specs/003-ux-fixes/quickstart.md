# Quickstart: UX Fixes — Scrolling, Agents Page, Chat Streaming, Auto Model

**Branch**: `003-ux-fixes` | **Date**: 2026-04-05

## Prerequisites

- Node.js 20+ and npm
- Python 3.12+ and `uv`
- A local checkout at `/home/runner/work/solune/solune`
- Valid local development credentials for the existing Solune backend/frontend flows

## Setup

### 1. Install backend dependencies

```bash
cd /home/runner/work/solune/solune/solune/backend
uv sync
```

### 2. Install frontend dependencies

```bash
cd /home/runner/work/solune/solune/solune/frontend
npm install
```

### 3. Start the backend

```bash
cd /home/runner/work/solune/solune/solune/backend
uv run uvicorn src.main:app --reload --port 8000
```

### 4. Start the frontend

```bash
cd /home/runner/work/solune/solune/solune/frontend
npm run dev
```

## Feature Walkthrough

### A. Verify single-scroll Settings/Agents/Pipeline layouts

1. Open the Settings page.
2. Shrink the viewport vertically until content overflows.
3. Confirm only one vertical scrollbar appears in both loading and ready states.
4. Repeat on the Agents page and the pipeline page (`AgentsPipelinePage`) to confirm the catalog and assignment sections scroll with the page rather than inside their own scroll region.

### B. Verify inline agent discovery

1. Open the Agents page with a project selected.
2. Confirm the catalog appears inline on the page without opening a modal.
3. Type into the search field and confirm tiles filter immediately by name/description.
4. Import an available agent and confirm the tile updates to an imported state without leaving the page.
5. Force a catalog failure (or mock one in tests) and confirm the inline retry state appears.

### C. Verify live chat streaming display

1. Open chat and send a normal AI-enhanced message.
2. Confirm the assistant response appears token-by-token before the final message is stored.
3. While tokens are arriving, scroll upward and confirm auto-scroll pauses.
4. Scroll back to the bottom and confirm follow-mode resumes.
5. Force a stream error and confirm partial content remains visible with an error indicator.

### D. Verify Auto model resolution visibility

1. Select “Auto” in a pipeline/chat model selector.
2. Launch a pipeline or send a chat message.
3. Confirm the UI surfaces which model was actually used after completion.
4. Simulate a no-model-available case and confirm the UI shows actionable guidance to choose a model manually.

## Verification Commands

### Frontend

```bash
cd /home/runner/work/solune/solune/solune/frontend
npm run test -- --run src/pages/SettingsPage.test.tsx src/components/agents/__tests__/AgentsPanel.test.tsx src/components/chat/ChatInterface.test.tsx
npm run lint
npm run type-check
```

### Backend

```bash
cd /home/runner/work/solune/solune/solune/backend
uv run pytest -q tests/unit/test_api_chat.py tests/unit/test_model_fetcher.py
```

## Expected Outcomes

- Settings, Agents, and Pipeline views expose only one vertical scroll region.
- Agents can be discovered, searched, and imported inline.
- Chat tokens become visible incrementally and do not flicker/duplicate on completion.
- Auto model actions show the resolved model name or a clear failure message.
