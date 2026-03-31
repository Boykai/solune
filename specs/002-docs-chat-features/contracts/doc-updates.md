# Documentation Update Contracts

**Feature**: 002-docs-chat-features | **Date**: 2026-03-31

This document specifies the exact changes required for each documentation file, serving as the contract between planning and implementation.

---

## Contract 1: docs/pages/chat.md (NEW)

**FR Coverage**: FR-001, FR-012, FR-013
**Priority**: P1 (User Story 1)
**Dependencies**: None (new file, no merge conflicts)

### Acceptance Criteria

- [ ] File exists at `docs/pages/chat.md`
- [ ] Contains sections for all 12 chat capabilities (per FR-001)
- [ ] Written for both developers and end users (FR-013)
- [ ] Follows existing page conventions: section headers, bullet lists, tables (FR-012)
- [ ] No "What's Next?" footer (leaf page, consistent with other pages/ docs)
- [ ] All internal links resolve to existing files (FR-011)

### Section Requirements

| Section | Must Include |
|---------|-------------|
| Sending Messages | Enter/Shift+Enter behavior, character limit |
| AI Enhance | Two modes, localStorage persistence, behavioral differences |
| @Mention Pipeline | @ trigger, autocomplete, inline tokens, one-active constraint |
| Voice Input | Web Speech API, en-US, HTTPS, recording states |
| File Attachments | Limits table, allowed/blocked types, .vtt/.srt transcript |
| History Navigation | Arrow Up/Down, 100 message buffer, in-memory |
| Slash Commands | Available commands, #agent reference |
| AI Proposals | Task proposals, issue recommendations, status changes |
| Streaming | Real-time tokens, tool call indicators |
| Markdown | GFM, code copy, tables, links |
| Message Types | user/assistant/system, retry, copy, clear |

---

## Contract 2: docs/api-reference.md (UPDATE)

**FR Coverage**: FR-002, FR-003, FR-004
**Priority**: P2 (User Story 2)
**Dependencies**: None

### Acceptance Criteria

- [ ] Chat endpoint table includes a dedicated streaming endpoint row for `POST /chat/messages/stream` with brief behavior description
- [ ] New subsection documents SSE event types (token, tool_call, tool_result, done, error) for the streaming endpoint
- [ ] File upload constraints documented (5 files, 10 MB, allowed/blocked, .vtt/.srt)
- [ ] POST /chat/messages description updated with `ai_enhance`, `file_urls`, `pipeline_id` params (non-streaming request/response)
- [ ] GET /chat/messages description notes pagination (`limit`, `offset`)
- [ ] Rate limit note added for `POST /chat/messages/stream` (10 streaming requests per minute)
- [ ] Follows existing table format (`| Method | Path | Description |`)

### Change Specification

1. **Update POST /chat/messages description** — Document `ai_enhance`, `file_urls`, and `pipeline_id` request params (non-streaming behavior)
2. **Add streaming endpoint and subsection** — Add a `POST /chat/messages/stream` row in the Chat endpoints table and a new `### Streaming` subsection under the Chat section with SSE event types table and 10/minute rate limit note
3. **Add file upload subsection** — New `### File Upload Constraints` subsection with limits and types
4. **Update GET /chat/messages** — Note pagination params

---

## Contract 3: docs/architecture.md (UPDATE)

**FR Coverage**: FR-005, FR-006, FR-007
**Priority**: P3 (User Story 3)
**Dependencies**: None

### Acceptance Criteria

- [ ] ChatAgentService subsection exists with: Agent Framework wrapper, session management (TTL, max concurrent), tool registration + MCP, dual dispatch, streaming
- [ ] `components/chat/` row in Key Frontend Modules table includes all 17 components (10 existing + 7 new)
- [ ] `hooks/` row includes the 3 new chat hooks
- [ ] New subsection follows existing pattern (### heading, prose + table)

### Change Specification

1. **Add `### ChatAgentService` subsection** — After "AI Completion Providers" section. Include: description, session management details, tool registration, dual dispatch model, streaming
2. **Update `components/chat/` table row** — Append: `MentionInput`, `MentionAutocomplete`, `FilePreviewChips`, `MarkdownRenderer`, `ChatMessageSkeleton`, `PipelineWarningBanner`, `PipelineIndicator`
3. **Update `hooks/` table row** — Append: `useChatProposals`, `useFileUpload`, `useMentionAutocomplete`

---

## Contract 4: docs/project-structure.md (UPDATE)

**FR Coverage**: FR-008
**Priority**: P4 (User Story 4)
**Dependencies**: None

### Acceptance Criteria

- [ ] `services/chat_agent.py` listed in backend services tree with description
- [ ] 7 missing chat components visible in frontend component tree
- [ ] 3 missing hooks visible in frontend hooks section
- [ ] Follows existing tree notation (`├──`, `│   ├──`, inline `#` comments)

### Change Specification

1. **Add `chat_agent.py`** — Under `services/` in the backend tree: `├── chat_agent.py       #   ChatAgentService (Microsoft Agent Framework wrapper)`
2. **Add `agent_provider.py`** — Under `services/`: `├── agent_provider.py   #   Agent provider factory (creates Agent Framework agents)`
3. **Add `agent_tools.py`** — Under `services/`: `├── agent_tools.py      #   Agent tool definitions (task proposals, status changes, recommendations)`
4. **Update `components/chat/` comment** — Add the 7 missing components to the inline listing
5. **Update `hooks/` comment** — Add the 3 missing hooks

---

## Contract 5: docs/roadmap.md (UPDATE)

**FR Coverage**: FR-009
**Priority**: P5 (User Story 5)
**Dependencies**: None

### Acceptance Criteria

- [ ] All v0.2.0 features marked as implemented (✅)
- [ ] Architecture evolution diagram shows `v0.2.0 (current)` instead of `v0.1.0 (today)`
- [ ] Timeline table reflects implemented status for v0.2.0
- [ ] No other roadmap versions modified

### Change Specification

1. **Update v0.2.0 feature list** — Add ✅ marker to each feature bullet
2. **Update architecture diagram** — Change `v0.1.0 (today)` to `v0.2.0 (current)`, update left side to show Agent Framework architecture
3. **Update timeline table** — Change v0.2.0 target from "Q2 2026" to "✅ Shipped" or similar indicator

---

## Contract 6: docs/pages/layout.md (UPDATE)

**FR Coverage**: FR-010
**Priority**: P6 (User Story 6)
**Dependencies**: Contract 1 (chat.md must exist)

### Acceptance Criteria

- [ ] Chat Panel section contains a link to `chat.md`
- [ ] Link uses relative path: `[chat feature guide](chat.md)`
- [ ] Wording is natural and follows existing prose style

### Change Specification

1. **Add link to Chat Panel section** — After the existing description or bullet list, add: `For the full chat feature guide, see [Chat](chat.md).`

---

## Contract 7: docs/pages/README.md (UPDATE)

**FR Coverage**: FR-010
**Priority**: P6 (User Story 6)
**Dependencies**: Contract 1 (chat.md must exist)

### Acceptance Criteria

- [ ] Page Overview table includes a Chat row
- [ ] Row follows format: `| [Chat](chat.md) | ... | [chat.md](chat.md) |`
- [ ] Position in table is logical (alphabetical or grouped with related pages)

### Change Specification

1. **Add Chat row to Page Overview table** — Insert between the appropriate rows: `| [Chat](chat.md) | AI chat panel — messaging, proposals, file uploads, and streaming | [chat.md](chat.md) |`

---

## Dependency Order

```text
Phase 1 (parallel): Contracts 1, 2, 3, 4, 5 — all independent
Phase 2 (sequential): Contracts 6, 7 — depend on Contract 1
Phase 3: Link verification across all files
```

All contracts can be implemented as independent tasks grouped by user story, with cross-reference contracts last.
