# Data Model: Update Documentation with New Chat Features

**Feature**: 002-docs-chat-features | **Date**: 2026-03-31

For a documentation-only feature, the "data model" describes the information architecture — the structure, content entities, and relationships between documents.

---

## Document Inventory

### New Documents

| Document | Path | Type | Primary Audience | FR Coverage |
|----------|------|------|------------------|-------------|
| Chat Page Guide | `docs/pages/chat.md` | Feature guide | Developers + End users | FR-001, FR-012, FR-013 |

### Updated Documents

| Document | Path | Change Type | FR Coverage |
|----------|------|-------------|-------------|
| API Reference | `docs/api-reference.md` | Add rows + sections | FR-002, FR-003, FR-004 |
| Architecture | `docs/architecture.md` | Add subsection + update tables | FR-005, FR-006, FR-007 |
| Project Structure | `docs/project-structure.md` | Update tree notation | FR-008 |
| Roadmap | `docs/roadmap.md` | Update status + diagram | FR-009 |
| Layout Guide | `docs/pages/layout.md` | Add cross-reference | FR-010 |
| Pages Index | `docs/pages/README.md` | Add table row | FR-010 |

---

## Content Structure: docs/pages/chat.md (NEW)

The chat page guide is the largest deliverable. Its structure follows the pattern established by other pages/ documents (e.g., `layout.md`, `agents.md`).

### Section Outline

```text
# Chat
  Introduction paragraph (what the chat panel is, who it's for)

## Sending Messages
  Text input, Enter/Shift+Enter, message length

## AI Enhance
  Toggle description, Agent Framework vs metadata-only, localStorage persistence

## @Mention Pipeline Selection
  @ trigger, autocomplete, inline tokens, one-active-per-message constraint

## Voice Input
  Web Speech API, en-US, HTTPS requirement, recording states (idle/recording/processing)

## File Attachments
  Limits table (5 files, 10 MB), allowed/blocked types, transcript auto-detection (.vtt/.srt)

## Chat History Navigation
  Arrow Up/Down, shell-like behavior, 100 message limit, in-memory

## Slash Commands
  / trigger, available commands, #agent command reference

## AI Proposals
  ### Task Proposals
    Structured preview, confirm/reject, metadata
  ### Issue Recommendations
    Preview + metadata
  ### Status Changes
    Status change proposals

## Streaming Responses
  Real-time token delivery, tool call indicators, skeleton loading

## Markdown Rendering
  GFM support, code blocks + copy button, tables, links

## Message Types and Actions
  User/assistant/system, retry, copy, clear
```

### Content Entities per Section

| Section | Key Facts to Document | Source |
|---------|----------------------|--------|
| Sending Messages | Enter sends, Shift+Enter newline, 100K char max | `models/chat.py` → `ChatMessageRequest` |
| AI Enhance | `ai_enhance` param, default true, localStorage key | `ChatMessageRequest`, `ChatInterface.tsx` |
| @Mention | `@` trigger, 150ms debounce, max 10 results, one active pipeline | `useMentionAutocomplete.ts` |
| Voice Input | Web Speech API, `en-US` lang, HTTPS required | `VoiceInputButton.tsx`, `useVoiceInput.ts` |
| File Attachments | 5 max, 10MB, allowed/blocked types, .vtt/.srt transcript | `useFileUpload.ts`, `api/chat.py` |
| History Navigation | Arrow keys, 100 message buffer, in-memory | `useChatHistory.ts` |
| Slash Commands | `/help`, `/theme`, `/clear`, `#agent` | `lib/commands/`, `api/chat.py` |
| Task Proposals | `task_create` action, confirm/reject UI | `useChatProposals.ts`, `TaskPreview.tsx` |
| Issue Recommendations | `issue_create` action, structured preview | `IssueRecommendationPreview.tsx` |
| Status Changes | `status_update` action | `StatusChangePreview.tsx` |
| Streaming | SSE events (token, tool_call, tool_result, done, error) | `chat_agent.py` → `run_stream()` |
| Markdown | GFM, code copy, tables, links, celestial styling | `MarkdownRenderer.tsx` |
| Message Types | user/assistant/system, retry, copy, clear | `models/chat.py` → `SenderType` |

---

## Content Structure: api-reference.md Updates

### New Endpoint Row

| Field | Value |
|-------|-------|
| Method | POST |
| Path | `/chat/messages` (streaming) |
| Description | Send message with SSE streaming response (`ai_enhance=true` required) |

### New Subsections

1. **Streaming Response** — SSE event types table (token, tool_call, tool_result, done, error)
2. **Request Parameters** — `ai_enhance`, `file_urls`, `pipeline_id` for POST
3. **File Upload Constraints** — Allowed/blocked types, size/count limits, transcript detection
4. **Pagination** — `limit`, `offset` for GET /chat/messages
5. **Rate Limits** — Note on streaming endpoint rate limiting

---

## Content Structure: architecture.md Updates

### New Subsection: ChatAgentService

| Content | Details |
|---------|---------|
| Location | After "AI Completion Providers" section |
| Agent Framework wrapper | `ChatAgentService` class description |
| Session management | `AgentSessionMapping` — TTL eviction (3600s), max 100 concurrent, LRU |
| Tool registration | MCP tool loading from project config |
| Dual dispatch | ai_enhance on → Agent Framework, off → fallback |
| Streaming | `run_stream()` method, SSE event types |

### Table Updates

| Table | Current Row | Components to Add |
|-------|-------------|-------------------|
| Key Frontend Modules → `components/chat/` | 10 components listed | +7: MentionInput, MentionAutocomplete, FilePreviewChips, MarkdownRenderer, ChatMessageSkeleton, PipelineWarningBanner, PipelineIndicator |
| Key Frontend Modules → `hooks/` | 25 hooks listed | +3: useChatProposals, useFileUpload, useMentionAutocomplete |

---

## Content Structure: project-structure.md Updates

### Backend Updates

| Item | Location in Tree | Description |
|------|-----------------|-------------|
| `chat_agent.py` | Under `services/` | ChatAgentService (Microsoft Agent Framework wrapper) |
| `agent_provider.py` | Under `services/` | Agent provider factory |
| `agent_tools.py` | Under `services/` | Agent tool definitions (task proposals, status changes) |

### Frontend Updates

| Item | Location in Tree | Description |
|------|-----------------|-------------|
| 7 components | Under `components/chat/` | MentionInput, MentionAutocomplete, FilePreviewChips, MarkdownRenderer, ChatMessageSkeleton, PipelineWarningBanner, PipelineIndicator |
| 3 hooks | Under `hooks/` | useFileUpload, useMentionAutocomplete, useChatProposals |

---

## Content Structure: roadmap.md Updates

### Status Changes

| Item | Current | Target |
|------|---------|--------|
| v0.2.0 features | Unmarked (planned) | All marked ✅ (implemented) |
| Architecture diagram left label | `v0.1.0 (today)` | `v0.2.0 (current)` |

---

## Cross-Reference Map

```text
pages/README.md  ──────► pages/chat.md     (new table row)
pages/layout.md  ──────► pages/chat.md     (Chat Panel section link)
pages/chat.md    ──────► api-reference.md   (API details link, in "What's Next?" or inline)
pages/chat.md    ──────► layout.md          (layout context link)
```

All links use relative paths. All target files will exist after the update is complete, satisfying FR-011.
