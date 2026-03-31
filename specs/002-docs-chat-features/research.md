# Research: Update Documentation with New Chat Features

**Feature**: 002-docs-chat-features | **Date**: 2026-03-31

This research resolves all technical unknowns and verifies codebase facts needed to accurately author the documentation updates.

---

## 1. Documentation Convention Patterns

**Decision**: Follow all existing conventions as-is — no new formatting patterns.

**Rationale**: The spec requires adherence to existing conventions (FR-012). Introducing new patterns would create inconsistency and violate Constitution Principle V (Simplicity).

**Conventions verified from existing docs**:

| Convention | Example Source | Pattern |
|------------|---------------|---------|
| Endpoint tables | `api-reference.md` | `\| Method \| Path \| Description \|` |
| Module tables | `architecture.md` | `\| Directory \| Purpose \|` |
| Component tables | `architecture.md` | `\| Directory \| Contents \|` — inline comma-separated list |
| Tree notation | `project-structure.md` | `├──`, `│   ├──`, inline `#` comments |
| Section headers | All docs | `#` title, `##` major, `###` sub, `####` sub-sub |
| "What's Next?" footer | `api-reference.md`, `architecture.md`, `project-structure.md` | `---` separator → `## What's Next?` → bullet links with `—` dash description |
| Page index table | `pages/README.md` | `\| Page \| Description \| Learn More \|` |
| Feature bullets | `pages/layout.md` | `**What you can do:**` → bullet list |
| Callouts | `roadmap.md` | `> blockquote` for notes |
| ASCII diagrams | `architecture.md`, `roadmap.md` | Box-drawing characters (`┌`, `─`, `└`, `│`) |
| Internal links | All docs | `[text](filename.md)` relative paths |

**Alternatives considered**: Adding Mermaid diagrams inline — rejected because existing page-level docs use ASCII art, and Mermaid is reserved for `architectures/*.mmd` files.

---

## 2. Chat Feature Implementation Verification

**Decision**: All 12 chat capabilities listed in the spec exist in the codebase and are implemented.

**Rationale**: The spec requires documenting only implemented features. Each capability was verified by inspecting the corresponding source files.

### Backend Verification

| Feature | Source File | Verified |
|---------|------------|----------|
| ChatAgentService | `services/chat_agent.py` | ✅ Agent Framework wrapper with `run()` and `run_stream()` |
| Session management | `services/chat_agent.py` → `AgentSessionMapping` | ✅ TTL eviction (default 3600s), max 100 concurrent, LRU |
| Tool registration + MCP | `services/chat_agent.py` | ✅ Project MCP configs loaded when project_id + db provided |
| Dual dispatch | `services/chat_agent.py` + `api/chat.py` | ✅ ai_enhance=true → Agent Framework, false → metadata-only fallback |
| Streaming SSE | `services/chat_agent.py` → `run_stream()` | ✅ Events: token, tool_call, tool_result, done, error |
| Chat endpoints | `api/chat.py` | ✅ GET/POST/DELETE /chat/messages, POST /chat/upload, proposals |
| File upload | `api/chat.py` | ✅ POST /chat/upload with validation |
| Chat models | `models/chat.py` | ✅ ChatMessage, ChatMessageRequest (ai_enhance, file_urls, pipeline_id), SenderType, ActionType |
| Rate limiting | `middleware/rate_limit.py` | ✅ RateLimitMiddleware applied globally |

### Frontend Verification

| Component | Location | Verified |
|-----------|----------|----------|
| MentionInput | `components/chat/MentionInput.tsx` | ✅ ContentEditable with @mention token support |
| MentionAutocomplete | `components/chat/MentionAutocomplete.tsx` | ✅ Floating dropdown, ARIA, keyboard navigation |
| FilePreviewChips | `components/chat/FilePreviewChips.tsx` | ✅ Inline file chips with status, progress |
| MarkdownRenderer | `components/chat/MarkdownRenderer.tsx` | ✅ GFM, code blocks + copy, tables, links |
| ChatMessageSkeleton | `components/chat/ChatMessageSkeleton.tsx` | ✅ Skeleton matching MessageBubble |
| PipelineWarningBanner | `components/chat/PipelineWarningBanner.tsx` | ✅ Warning when no pipeline assigned |
| PipelineIndicator | `components/chat/PipelineIndicator.tsx` | ✅ Badge showing active pipeline |
| ChatInterface | `components/chat/ChatInterface.tsx` | ✅ Main chat container |
| ChatPopup | `components/chat/ChatPopup.tsx` | ✅ Floating panel |
| MessageBubble | `components/chat/MessageBubble.tsx` | ✅ Individual message display |
| TaskPreview | `components/chat/TaskPreview.tsx` | ✅ Task proposal preview |
| StatusChangePreview | `components/chat/StatusChangePreview.tsx` | ✅ Status change proposal |
| IssueRecommendationPreview | `components/chat/IssueRecommendationPreview.tsx` | ✅ Issue recommendation |
| CommandAutocomplete | `components/chat/CommandAutocomplete.tsx` | ✅ Slash command autocomplete |
| SystemMessage | `components/chat/SystemMessage.tsx` | ✅ System message display |
| ChatToolbar | `components/chat/ChatToolbar.tsx` | ✅ Actions (attach, voice, etc.) |
| VoiceInputButton | `components/chat/VoiceInputButton.tsx` | ✅ Web Speech API voice input |

### Hook Verification

| Hook | Location | Verified |
|------|----------|----------|
| useFileUpload | `hooks/useFileUpload.ts` | ✅ File selection, validation (size/type/count), upload state, preview |
| useMentionAutocomplete | `hooks/useMentionAutocomplete.ts` | ✅ @trigger, pipeline filtering, keyboard nav, token management |
| useChatProposals | `hooks/useChatProposals.ts` | ✅ Pending proposals (task, status, issue), confirm/reject |
| useChat | `hooks/useChat.ts` | ✅ Core chat logic |
| useChatHistory | `hooks/useChatHistory.ts` | ✅ History navigation (Arrow Up/Down) |
| useVoiceInput | `hooks/useVoiceInput.ts` | ✅ Web Speech API integration |

---

## 3. Streaming Endpoint Details

**Decision**: Document the streaming endpoint as a dedicated `POST /chat/messages/stream` SSE endpoint, separate from the non-streaming `POST /chat/messages` JSON endpoint.

**Rationale**: The codebase exposes a dedicated streaming endpoint at `@router.post("/messages/stream")` in `api/chat.py` (line 1336), rate-limited at 10/minute. The non-streaming `POST /chat/messages` always returns a single JSON `ChatMessage`. The `ai_enhance` parameter on the streaming endpoint must be `true`; if `false`, the endpoint returns a 400 error directing clients to the non-streaming endpoint.

**SSE Event Types** (from `chat_agent.py` → `run_stream()`):

| Event | Data | Description |
|-------|------|-------------|
| `token` | Partial text string | Incremental text content from the agent |
| `tool_call` | Tool name + arguments | Agent invoking a registered tool |
| `tool_result` | Tool output + action payload | Tool execution completed |
| `done` | Final `ChatMessage` JSON | Stream complete, includes full message |
| `error` | Error message string | An error occurred during streaming |

**Alternatives considered**: Documenting streaming as a mode of `POST /chat/messages` with `Accept: text/event-stream` — rejected because the codebase exposes a separate `/messages/stream` path.

---

## 4. File Upload Constraints

**Decision**: Document the following constraints as found in the codebase.

**Rationale**: Values verified from `useFileUpload.ts` and `api/chat.py`.

| Constraint | Value | Source |
|------------|-------|--------|
| Max files per message | 5 | `useFileUpload.ts` |
| Max file size | 10 MB | `useFileUpload.ts` |
| Allowed types | Images, PDFs, text, CSV, VTT, SRT, common docs | `useFileUpload.ts` |
| Blocked types | Executables and scripts (`.exe`, `.sh`, `.bat`, `.cmd`, `.js`, `.py`, `.rb`); note: `.zip` archives are allowed | `useFileUpload.ts` |
| Transcript auto-detection | `.vtt`, `.srt` files | `api/chat.py` |

---

## 5. Roadmap v0.2.0 Status Assessment

**Decision**: Mark the following v0.2.0 features as implemented (✅).

**Rationale**: All features described in the v0.2.0 roadmap section have corresponding implemented code in the repository, verified in Research Section 2 above.

| Roadmap Feature | Implementation Evidence |
|----------------|----------------------|
| Agent Framework chat agent | `ChatAgentService` wrapping Microsoft Agent Framework |
| Clarifying questions | Agent Framework multi-turn conversation support |
| Difficulty assessment | `agent_tools.py` → `DIFFICULTY_PRESET_MAP` |
| Autonomous project creation | `agent_tools.py` → task proposals, issue recommendations |
| Tool/skill extensibility | MCP tool registration in `ChatAgentService` |
| Model flexibility | Pluggable `CompletionProvider` (Copilot SDK, Azure OpenAI) |
| Conversation history | `chat_store.py` + `useChatHistory` hook |

**Additional implemented features** (not in original roadmap but part of v0.2.0 delivery):
- Streaming SSE responses
- File uploads with transcript detection
- @mention pipeline selection
- AI Enhance toggle
- Chat history keyboard navigation
- Markdown rendering with GFM

---

## 6. Architecture Diagram Update Scope

**Decision**: Update the `v0.1.0 (today)` label in `roadmap.md` to `v0.2.0 (current)` and adjust the architecture evolution ASCII art to reflect v0.2.0 as the current version.

**Rationale**: The roadmap architecture evolution diagram currently labels v0.1.0 as "today". Since v0.2.0 features are now implemented, the diagram should reflect the current state.

**Alternatives considered**: Creating a detailed intermediate diagram showing v0.2.0 architecture — rejected because the evolution diagram is intentionally simplified to show start and target states. The detailed architecture is in `architecture.md`.

---

## 7. Component Table Update Strategy

**Decision**: Add the 7 missing components to the existing `components/chat/` row in `architecture.md`'s Key Frontend Modules table, using the same inline comma-separated format.

**Rationale**: The existing table uses a single row per directory with components listed inline. Adding a separate row would break the established pattern.

**Components to add**: `MentionInput`, `MentionAutocomplete`, `FilePreviewChips`, `MarkdownRenderer`, `ChatMessageSkeleton`, `PipelineWarningBanner`, `PipelineIndicator`

**Hooks to add** (to the existing `hooks/` row): `useChatProposals`, `useFileUpload`, `useMentionAutocomplete`

---

## 8. Cross-Reference Link Strategy

**Decision**: Add links in two locations:
1. `pages/layout.md` — In the Chat Panel section, add a sentence linking to the new `chat.md` guide
2. `pages/README.md` — Add a row to the Page Overview table for the chat page

**Rationale**: These are the two natural discovery points for the chat page. The layout page describes the chat panel UI element; the README is the page index. Both use established patterns that accommodate new entries without structural changes.

**Alternatives considered**: Adding links from other pages (e.g., dashboard.md, agents.md) — rejected because these pages don't have existing chat sections and adding cross-links would exceed the spec scope.
