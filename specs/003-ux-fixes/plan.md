# Implementation Plan: UX Fixes — Scrolling, Agents Page, Chat Streaming, Auto Model

**Branch**: `003-ux-fixes` | **Date**: 2026-04-05 | **Spec**: `/home/runner/work/solune/solune/specs/003-ux-fixes/spec.md`
**Input**: Feature specification from `/home/runner/work/solune/solune/specs/003-ux-fixes/spec.md`

## Summary

Fix the visible UX regressions called out in `/home/runner/work/solune/solune/specs/003-ux-fixes/spec.md` by standardizing full-page layout shells to a single scroll owner, replacing the Agents modal browse flow with an inline catalog section, wiring existing SSE token streaming into the chat UI, and surfacing the concrete model chosen when a user leaves selection on “Auto.” The work stays additive and targeted: reuse the existing agents catalog/import APIs, preserve the current `/chat/messages/stream` contract while enriching the rendered state, and extend existing chat/pipeline result payloads only where needed to expose resolved model metadata.

## Technical Context

**Language/Version**: Python 3.12+ (`/home/runner/work/solune/solune/solune/backend/pyproject.toml`), TypeScript ~6.0.2 + React 19.2 (`/home/runner/work/solune/solune/solune/frontend/package.json`)  
**Primary Dependencies**: FastAPI, `sse-starlette`, `github-copilot-sdk`, React, Vite, `@tanstack/react-query`, Tailwind CSS, Vitest  
**Storage**: SQLite-backed backend state plus existing in-memory React UI state for scroll/streaming buffers  
**Testing**: `pytest` (backend), Vitest + Testing Library (frontend), Playwright for browser verification  
**Target Platform**: Linux-hosted FastAPI backend and modern desktop/laptop browsers for the SPA  
**Project Type**: Web application (`/home/runner/work/solune/solune/solune/backend` + `/home/runner/work/solune/solune/solune/frontend`)  
**Performance Goals**: First streamed token visible within 1 second of stream start (SC-003); no nested vertical scroll tracks on Settings/Agents/Pipeline views (SC-001); inline agent search updates on input without modal transitions  
**Constraints**: Must reuse `/home/runner/work/solune/solune/solune/backend/src/api/chat.py` SSE endpoint, `/home/runner/work/solune/solune/solune/backend/src/api/agents.py` catalog/import endpoints, and existing hooks in `/home/runner/work/solune/solune/solune/frontend/src/hooks/useAgents.ts`; must preserve current unsaved-agent-editor protections in `/home/runner/work/solune/solune/solune/frontend/src/components/agents/AgentsPanel.tsx`; avoid new nested scroll regions while keeping current page chrome intact  
**Scale/Scope**: 3 page shells (`SettingsPage`, `AgentsPage`, `AgentsPipelinePage`), 1 agent discovery flow refactor, 1 chat stream rendering path, and additive model metadata surfaced across chat/pipeline completion states

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. Specification-First Development** | ✅ PASS | `/home/runner/work/solune/solune/specs/003-ux-fixes/spec.md` contains prioritized P1-P3 user stories, independent tests, acceptance scenarios, edge cases, and measurable success criteria. |
| **II. Template-Driven Workflow** | ✅ PASS | This plan plus `/home/runner/work/solune/solune/specs/003-ux-fixes/research.md`, `/home/runner/work/solune/solune/specs/003-ux-fixes/data-model.md`, `/home/runner/work/solune/solune/specs/003-ux-fixes/quickstart.md`, and `/home/runner/work/solune/solune/specs/003-ux-fixes/contracts/ux-fixes.openapi.yaml` follow the canonical planning artifact set. |
| **III. Agent-Orchestrated Execution** | ✅ PASS | The implementation remains decomposed by responsibility: layout shell updates, inline catalog refactor, chat streaming render path, and auto-model metadata plumbing. Each phase has clear inputs/outputs for follow-on `/speckit.tasks`. |
| **IV. Test Optionality with Clarity** | ✅ PASS | Tests are included because SC-007 requires regression safety and each user story defines independent verification. Targeted frontend and backend tests already exist for the touched surfaces. |
| **V. Simplicity and DRY** | ✅ PASS | The plan reuses existing APIs/hooks/components instead of inventing parallel flows: move modal content inline, pass through existing `streamingContent`, and extend existing result models additively. |

**Post-Phase 1 Re-check**: ✅ PASS — the design artifacts keep the solution focused on existing page shells, existing catalog APIs, existing SSE framing, and additive response metadata only. No unjustified abstractions or extra services are introduced.

## Project Structure

### Documentation (this feature)

```text
/home/runner/work/solune/solune/specs/003-ux-fixes/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── ux-fixes.openapi.yaml
└── tasks.md              # Phase 2 output from /speckit.tasks
```

### Source Code (repository root)

```text
/home/runner/work/solune/solune/solune/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── agents.py
│   │   │   ├── chat.py
│   │   │   └── pipelines.py
│   │   ├── models/
│   │   │   ├── agents.py
│   │   │   ├── chat.py
│   │   │   └── workflow.py
│   │   └── services/
│   │       ├── agents/
│   │       ├── chat_agent.py
│   │       └── model_fetcher.py
│   └── tests/
│       └── unit/
│           ├── test_api_chat.py
│           └── test_model_fetcher.py
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── agents/
    │   │   │   ├── AgentsPanel.tsx
    │   │   │   └── BrowseAgentsModal.tsx
    │   │   ├── chat/
    │   │   │   ├── ChatInterface.tsx
    │   │   │   └── MessageBubble.tsx
    │   │   ├── pipeline/
    │   │   │   └── ModelSelector.tsx
    │   │   └── settings/
    │   │       └── PrimarySettings.tsx
    │   ├── hooks/
    │   │   ├── useAgents.ts
    │   │   └── useChat.ts
    │   ├── pages/
    │   │   ├── AgentsPage.tsx
    │   │   ├── AgentsPipelinePage.tsx
    │   │   └── SettingsPage.tsx
    │   ├── services/
    │   │   └── api.ts
    │   └── types/
    │       └── index.ts
    └── src/**/__tests__/
        ├── components/agents/AgentsPanel.test.tsx
        ├── components/chat/ChatInterface.test.tsx
        └── pages/SettingsPage.test.tsx
```

**Structure Decision**: Use the existing web-application structure. Layout and inline-catalog work is concentrated in `/home/runner/work/solune/solune/solune/frontend/src/pages` and `/home/runner/work/solune/solune/solune/frontend/src/components`, while streaming/model-resolution metadata remains additive in existing backend API/model files.

## Implementation Phases

### Phase 0 — Research and Design Decisions

1. Confirm the single-scroll-container pattern from existing page shells (`ToolsPage`, `ChoresPage`, `AgentsPipelinePage`) and document which inner wrappers currently violate it.
2. Confirm the inline catalog can reuse `useCatalogAgents()` and `useImportAgent()` from `/home/runner/work/solune/solune/solune/frontend/src/hooks/useAgents.ts` without new endpoints.
3. Confirm chat streaming already accumulates `streamingContent` in `/home/runner/work/solune/solune/solune/frontend/src/hooks/useChat.ts` and that the missing work is render-state propagation plus error preservation.
4. Confirm Auto model support already exists in `/home/runner/work/solune/solune/solune/frontend/src/components/pipeline/ModelSelector.tsx`, so the remaining gap is resolved-model reporting in response payloads and UI labels.

### Phase 1 — Page Shell and Scrolling Fixes

**Step 1.1: Settings page single scroll owner**
- Remove `overflow-y-auto` and unnecessary `h-full` ownership from the loading and main wrappers in `/home/runner/work/solune/solune/solune/frontend/src/pages/SettingsPage.tsx`.
- Keep one page-level scroll owner and allow inner settings sections to flow naturally.

**Step 1.2: Cross-page shell alignment**
- Audit `/home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPage.tsx` and `/home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPipelinePage.tsx` to ensure catalog/assignment content does not introduce nested independent scroll regions.
- Use `ToolsPage.tsx`/`ChoresPage.tsx` as reference shells for the shared pattern.

**Step 1.3: Layout regression coverage**
- Update `/home/runner/work/solune/solune/solune/frontend/src/pages/SettingsPage.test.tsx` and any relevant Agents/Pipeline page tests to assert the expected shell classes/structure and loading-state behavior.

### Phase 2 — Inline Agent Discovery

**Step 2.1: Extract modal content into an inline catalog section**
- Move the searchable catalog grid/list currently embedded in `/home/runner/work/solune/solune/solune/frontend/src/components/agents/BrowseAgentsModal.tsx` into an inline section rendered by `/home/runner/work/solune/solune/solune/frontend/src/components/agents/AgentsPanel.tsx`.
- Keep search filtering, loading, empty, and retry states intact.

**Step 2.2: Retire modal-only browse flow**
- Remove the “Browse Agents” modal trigger from `/home/runner/work/solune/solune/solune/frontend/src/components/agents/AgentsPanel.tsx`.
- Retain `AddAgentModal` and the existing inline editor/unsaved changes dialog.

**Step 2.3: Import and status rendering**
- Preserve `already_imported`/error/importing states from `/home/runner/work/solune/solune/solune/backend/src/models/agents.py` and `/home/runner/work/solune/solune/solune/frontend/src/hooks/useAgents.ts`.
- Expand `/home/runner/work/solune/solune/solune/frontend/src/components/agents/__tests__/AgentsPanel.test.tsx` to cover inline search and import state transitions.

### Phase 3 — Live Chat Streaming Display

**Step 3.1: Render transient assistant streaming state**
- Thread `streamingContent` and `isStreaming` from `/home/runner/work/solune/solune/solune/frontend/src/hooks/useChat.ts` into `/home/runner/work/solune/solune/solune/frontend/src/components/chat/ChatInterface.tsx`.
- Add a transient assistant bubble in `/home/runner/work/solune/solune/solune/frontend/src/components/chat/MessageBubble.tsx` or a nearby specialized component.

**Step 3.2: Preserve partial content and smooth completion**
- Keep the streaming buffer visible until the final `done` payload replaces it.
- On `error`, keep partial text visible and show an inline failure indicator instead of clearing the buffer immediately.

**Step 3.3: Auto-scroll policy**
- Track whether the user is already near the bottom before auto-scrolling.
- Follow the stream while the user stays at the bottom; pause when they scroll upward; resume when they return to the bottom.

**Step 3.4: Streaming regression tests**
- Expand `/home/runner/work/solune/solune/solune/frontend/src/components/chat/ChatInterface.test.tsx` for incremental token rendering, no duplication on completion, preserved partial content on error, and scroll-follow/pause behavior.
- Keep `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_chat.py` focused on token/done/error event framing compatibility.

### Phase 4 — Auto Model Resolution Visibility

**Step 4.1: Resolve and expose used model metadata**
- Extend `/home/runner/work/solune/solune/solune/backend/src/models/chat.py` and `/home/runner/work/solune/solune/solune/backend/src/models/workflow.py` response payloads with additive resolved-model metadata for chat replies and pipeline launches/runs.
- Populate that metadata in `/home/runner/work/solune/solune/solune/backend/src/api/chat.py` and `/home/runner/work/solune/solune/solune/backend/src/api/pipelines.py` using the existing model-selection path.

**Step 4.2: Surface the resolved model in the UI**
- Show the chosen model name anywhere Auto is user-visible: final assistant message metadata, pipeline launch/result messaging, and model-selection affordances that currently only say “Auto.”
- Keep `/home/runner/work/solune/solune/solune/frontend/src/components/pipeline/ModelSelector.tsx` and `/home/runner/work/solune/solune/solune/frontend/src/components/settings/PrimarySettings.tsx` consistent with the additive metadata.

**Step 4.3: Failure-state clarity**
- When Auto resolution fails, present an actionable UI message that points the user back to manual model selection.
- Add or update backend unit coverage around `/home/runner/work/solune/solune/solune/backend/tests/unit/test_model_fetcher.py` for resolution/no-model cases.

## Dependency Graph

```text
[Phase 1: scroll shells]
        │
        ├── informs shared page-shell pattern for Phase 2
        │
        ├──→ [Phase 2: inline agent catalog]
        │         └── depends on existing catalog/import APIs only
        │
        └──→ [Phase 3: streaming UI]
                  └── depends on existing SSE endpoint and useChat buffer state

[Phase 3: streaming UI] ──→ [Phase 4: resolved model visibility]
                              ├── chat completion metadata reuse
                              └── pipeline launch/result metadata reuse
```

## Files Changed

| Area | File | Change Type | Description |
|------|------|-------------|-------------|
| Layout | `/home/runner/work/solune/solune/solune/frontend/src/pages/SettingsPage.tsx` | MODIFY | Remove nested scroll ownership from loading and main containers |
| Layout | `/home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPage.tsx` | MODIFY | Keep the page shell as the single scroll owner |
| Layout | `/home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPipelinePage.tsx` | MODIFY | Verify pipeline page matches the shared shell pattern |
| Agents | `/home/runner/work/solune/solune/solune/frontend/src/components/agents/AgentsPanel.tsx` | MODIFY | Render inline catalog section and retire modal entry point |
| Agents | `/home/runner/work/solune/solune/solune/frontend/src/components/agents/BrowseAgentsModal.tsx` | MODIFY/REMOVE | Extract or retire modal-only browse UI |
| Agents | `/home/runner/work/solune/solune/solune/frontend/src/hooks/useAgents.ts` | REUSE | Keep existing catalog/import hooks; only adjust consuming UI if needed |
| Streaming | `/home/runner/work/solune/solune/solune/frontend/src/hooks/useChat.ts` | MODIFY | Preserve streaming buffer/error state for the UI |
| Streaming | `/home/runner/work/solune/solune/solune/frontend/src/components/chat/ChatInterface.tsx` | MODIFY | Render streaming bubble and scroll-follow behavior |
| Streaming | `/home/runner/work/solune/solune/solune/frontend/src/components/chat/MessageBubble.tsx` | MODIFY | Add streaming/error presentation without duplicating final messages |
| Chat API | `/home/runner/work/solune/solune/solune/frontend/src/services/api.ts` | MODIFY | Keep SSE parsing compatible with token/done/error and additive metadata |
| Models | `/home/runner/work/solune/solune/solune/backend/src/models/chat.py` | MODIFY | Add optional resolved-model payload for chat responses |
| Models | `/home/runner/work/solune/solune/solune/backend/src/models/workflow.py` | MODIFY | Add optional resolved-model payload for pipeline results |
| API | `/home/runner/work/solune/solune/solune/backend/src/api/chat.py` | MODIFY | Persist and emit resolved-model metadata alongside final messages |
| API | `/home/runner/work/solune/solune/solune/backend/src/api/pipelines.py` | MODIFY | Include resolved-model metadata in launch/run outputs where Auto is used |
| Tests | `/home/runner/work/solune/solune/solune/frontend/src/pages/SettingsPage.test.tsx` | MODIFY | Cover single-scroll loading and content shells |
| Tests | `/home/runner/work/solune/solune/solune/frontend/src/components/agents/__tests__/AgentsPanel.test.tsx` | MODIFY | Cover inline catalog search/import behavior |
| Tests | `/home/runner/work/solune/solune/solune/frontend/src/components/chat/ChatInterface.test.tsx` | MODIFY | Cover incremental streaming, scroll following, and error preservation |
| Tests | `/home/runner/work/solune/solune/solune/backend/tests/unit/test_api_chat.py` | MODIFY | Ensure SSE framing and final-message metadata remain compatible |
| Tests | `/home/runner/work/solune/solune/solune/backend/tests/unit/test_model_fetcher.py` | MODIFY | Cover Auto resolution success/failure cases |

## Verification

```bash
# Frontend targeted regression coverage
cd /home/runner/work/solune/solune/solune/frontend
npm run test -- --run src/pages/SettingsPage.test.tsx src/components/agents/__tests__/AgentsPanel.test.tsx src/components/chat/ChatInterface.test.tsx

# Frontend static checks
cd /home/runner/work/solune/solune/solune/frontend
npm run lint
npm run type-check

# Backend targeted regression coverage
cd /home/runner/work/solune/solune/solune/backend
uv run pytest -q tests/unit/test_api_chat.py tests/unit/test_model_fetcher.py

# Manual verification
# 1. Open Settings and verify exactly one vertical scrollbar in loading and ready states.
# 2. Open Agents and confirm the catalog is inline, searchable, and importable without a modal.
# 3. Send a chat message and watch tokens appear progressively, pause auto-scroll by scrolling up, then resume at bottom.
# 4. Run a chat/pipeline action with Auto selected and confirm the resolved model name is surfaced.
```

## Decisions

| Decision | Rationale |
|----------|-----------|
| Use the page shell as the only scroll owner | Fixes nested-scroll defects with the smallest layout change and aligns with existing shells already used elsewhere in the frontend |
| Reuse catalog/import APIs rather than inventing a new discovery backend | `/agents/{project_id}/catalog` and `/agents/{project_id}/import` already expose the required data and statuses |
| Render a transient streaming assistant bubble instead of storing partial messages in persistence | Keeps the database/persisted chat history authoritative while giving immediate UI feedback |
| Extend chat/pipeline result models additively with resolved-model metadata | Meets FR-014/FR-015 without changing how Auto selection is chosen in existing flows |

## Complexity Tracking

No constitution violations are expected for this feature.
