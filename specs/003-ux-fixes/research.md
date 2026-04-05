# Research: UX Fixes — Scrolling, Agents Page, Chat Streaming, Auto Model

**Branch**: `003-ux-fixes` | **Date**: 2026-04-05

## Research Tasks

### R1: Single-scroll-container pattern for full-page views

**Decision**: Standardize on a page-shell pattern where the outer page container owns vertical scrolling and inner content sections do not declare their own `overflow-y-auto` regions unless they are intentionally local widgets.

**Rationale**: `/home/runner/work/solune/solune/solune/frontend/src/pages/SettingsPage.tsx` currently applies `overflow-y-auto` to both the loading wrapper and the main settings panel, which creates the nested-scroll behavior described in the issue. Existing page shells like `/home/runner/work/solune/solune/solune/frontend/src/pages/ChoresPage.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/pages/ToolsPage.tsx`, and `/home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPipelinePage.tsx` already show the intended pattern: one page shell scroll owner with normal-flow children.

**Alternatives considered**:
- Keep nested scroll containers and try to hide one scrollbar with CSS — rejected because it masks, rather than removes, the ownership conflict.
- Introduce a new shared layout abstraction first — rejected as unnecessary abstraction for a small UX fix.

### R2: Inline agent discovery should reuse the existing catalog/import integration

**Decision**: Move the browse experience inline inside `/home/runner/work/solune/solune/solune/frontend/src/components/agents/AgentsPanel.tsx`, reusing `/home/runner/work/solune/solune/solune/frontend/src/hooks/useAgents.ts` (`useCatalogAgents`, `useImportAgent`) and the backend catalog/import endpoints in `/home/runner/work/solune/solune/solune/backend/src/api/agents.py`.

**Rationale**: The current modal at `/home/runner/work/solune/solune/solune/frontend/src/components/agents/BrowseAgentsModal.tsx` already contains the exact loading, search, retry, empty, and import states the spec requires. The issue is placement, not missing backend capability. Reusing the existing integration keeps the change small and preserves current duplicate/import-error semantics from `/home/runner/work/solune/solune/solune/backend/src/models/agents.py`.

**Alternatives considered**:
- Build a second “inline catalog” data path — rejected because it duplicates proven API/hooks.
- Keep the modal and add a preview strip on the page — rejected because FR-008 explicitly retires the modal flow.

### R3: Chat streaming gap is UI propagation, not transport

**Decision**: Treat `/home/runner/work/solune/solune/solune/frontend/src/hooks/useChat.ts` as the source of transient stream state and render that state directly in `/home/runner/work/solune/solune/solune/frontend/src/components/chat/ChatInterface.tsx` with a streaming-aware assistant bubble.

**Rationale**: The backend endpoint `/home/runner/work/solune/solune/solune/backend/src/api/chat.py` already emits `token`, `done`, and `error` events, and `/home/runner/work/solune/solune/solune/frontend/src/services/api.ts` already parses those events. `useChat.ts` appends incoming tokens into `streamingContent`, but `ChatInterface.tsx` only renders persisted `messages`. That means the missing link is purely presentational.

**Alternatives considered**:
- Persist partial assistant messages in the database while streaming — rejected because it complicates consistency and final-message replacement.
- Wait for the final `done` event only — rejected because it is the current broken UX.

### R4: Auto-scroll should follow the stream only while the user remains at the bottom

**Decision**: Add bottom-proximity tracking in the chat viewport so automatic scrolling follows streamed tokens only while the user is already reading the newest content.

**Rationale**: The spec explicitly calls out the edge case where a user scrolls upward during streaming. A simple “always scroll to bottom on any message change” effect, which `/home/runner/work/solune/solune/solune/frontend/src/components/chat/ChatInterface.tsx` currently uses, will fight the user. A near-bottom threshold is the smallest reliable policy.

**Alternatives considered**:
- Always auto-scroll on each token — rejected because it makes earlier content unreadable during long responses.
- Disable auto-scroll entirely during streaming — rejected because it breaks the default “follow the answer” experience.

### R5: Surface resolved Auto model metadata additively in existing response shapes

**Decision**: Extend existing chat and pipeline result payloads with optional resolved-model metadata rather than creating separate lookup endpoints.

**Rationale**: The UI already exposes “Auto” through `/home/runner/work/solune/solune/solune/frontend/src/components/pipeline/ModelSelector.tsx` and related settings controls, but `/home/runner/work/solune/solune/solune/frontend/src/types/index.ts` response shapes do not currently expose which model was ultimately used. Adding optional metadata to the final message/workflow result is the least disruptive way to satisfy FR-014 and FR-015.

**Alternatives considered**:
- Put the resolved model only in logs/tooltips with no API contract change — rejected because the frontend still needs a stable source of truth.
- Add a separate “resolve model” API call before every action — rejected because it adds latency and coupling to flows that already execute successfully.

### R6: Verification should stay targeted to the affected UX surfaces

**Decision**: Use targeted frontend tests (`SettingsPage`, `AgentsPanel`, `ChatInterface`) plus backend regression coverage around chat/model resolution, then finish with manual browser verification for scroll and streaming behavior.

**Rationale**: The feature spans multiple UI surfaces but only a handful of files. Targeted regression tests keep the validation focused and align with the spec’s independent-test requirements for each story.

**Alternatives considered**:
- Full-suite-only validation — rejected because it is slower and less diagnostic for a focused UX change.
- Manual verification only — rejected because SC-007 explicitly calls for regression safety.
