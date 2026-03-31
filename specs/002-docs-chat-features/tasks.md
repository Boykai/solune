# Tasks: Update Documentation with New Chat Features

**Input**: Design documents from `/specs/002-docs-chat-features/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Not required — documentation-only feature. Spec and constitution confirm tests are not needed (Constitution Principle IV: Test Optionality).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. Each documentation file maps to a single user story, so stories are naturally independent.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Documentation root**: `solune/docs/`
- **Page guides**: `solune/docs/pages/`
- All paths are relative to the repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No code setup needed — this is a documentation-only feature. Verify existing documentation structure and conventions before writing.

- [ ] T001 Verify existing documentation structure and conventions in solune/docs/ match research.md findings
- [ ] T002 [P] Review existing pages for style reference (solune/docs/pages/layout.md, solune/docs/pages/README.md)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational blocking tasks — all user stories target independent files. Contracts 1–5 are fully independent (see contracts/doc-updates.md dependency order). User Story 6 (cross-references) depends on User Story 1 (chat.md must exist).

**⚠️ NOTE**: Phase 2 is empty for this documentation-only feature. Proceed directly to user story phases.

**Checkpoint**: No blocking prerequisites — user story implementation can begin immediately after Phase 1

---

## Phase 3: User Story 1 — New Developer Learns Chat Features (Priority: P1) 🎯 MVP

**Goal**: Create a comprehensive, standalone chat feature guide (`docs/pages/chat.md`) that documents all 12 major chat capabilities for developers and end users.

**Independent Test**: Navigate to the chat page guide and confirm that every major chat feature (sending messages, AI Enhance toggle, @mention pipelines, voice input, file attachments, history navigation, slash commands, AI proposals, streaming, markdown rendering, message types, message actions) is documented with clear descriptions and behavioral details.

### Implementation for User Story 1

- [ ] T003 [US1] Create docs/pages/chat.md with page title, introduction paragraph, and document skeleton (11 content sections covering all 12 chat capabilities — "Message Types and Actions" is one combined section per data-model.md)
- [ ] T004 [US1] Write "Sending Messages" section in solune/docs/pages/chat.md — Enter/Shift+Enter behavior, character limit
- [ ] T005 [US1] Write "AI Enhance" section in solune/docs/pages/chat.md — two modes (Agent Framework vs metadata-only), localStorage persistence, behavioral differences
- [ ] T006 [US1] Write "@Mention Pipeline Selection" section in solune/docs/pages/chat.md — @ trigger, autocomplete, inline tokens, one-active-per-message constraint
- [ ] T007 [US1] Write "Voice Input" section in solune/docs/pages/chat.md — Web Speech API, en-US, HTTPS requirement, recording states (idle/recording/processing)
- [ ] T008 [US1] Write "File Attachments" section in solune/docs/pages/chat.md — limits table (5 files, 10 MB), allowed/blocked types, .vtt/.srt transcript auto-detection
- [ ] T009 [US1] Write "Chat History Navigation" section in solune/docs/pages/chat.md — Arrow Up/Down, shell-like behavior, 100 message buffer, in-memory
- [ ] T010 [US1] Write "Slash Commands" section in solune/docs/pages/chat.md — / trigger, available commands (/help, /theme, /clear), #agent command reference
- [ ] T011 [US1] Write "AI Proposals" section in solune/docs/pages/chat.md — task proposals (structured preview, confirm/reject), issue recommendations (preview + metadata), status changes
- [ ] T012 [US1] Write "Streaming Responses" section in solune/docs/pages/chat.md — real-time token delivery, tool call indicators, skeleton loading
- [ ] T013 [US1] Write "Markdown Rendering" section in solune/docs/pages/chat.md — GFM support, code blocks + copy button, tables, links
- [ ] T014 [US1] Write "Message Types and Actions" section in solune/docs/pages/chat.md — user/assistant/system types, retry, copy, clear actions

**Checkpoint**: `docs/pages/chat.md` exists with all 12 capability sections. User Story 1 is fully functional and independently testable.

---

## Phase 4: User Story 2 — Developer Integrates with Chat API (Priority: P2)

**Goal**: Update the API reference to accurately document the streaming chat endpoint, file upload constraints, rate limits, and new request parameters.

**Independent Test**: Review the API reference page and confirm that the streaming endpoint (POST /chat/messages with SSE), SSE event types, rate limits, file upload constraints, and new request/response parameters are all documented.

### Implementation for User Story 2

- [ ] T015 [P] [US2] Update POST /chat/messages description in solune/docs/api-reference.md — add streaming note (ai_enhance=true), file_urls, pipeline_id params
- [ ] T016 [P] [US2] Update GET /chat/messages description in solune/docs/api-reference.md — add pagination params (limit, offset)
- [ ] T017 [US2] Add "Streaming" subsection under Chat section in solune/docs/api-reference.md — SSE event types table (token, tool_call, tool_result, done, error), ai_enhance=true requirement, rate limit note
- [ ] T018 [US2] Add "File Upload Constraints" subsection in solune/docs/api-reference.md — allowed/blocked types, 10 MB per-file limit, 5-file maximum, .vtt/.srt transcript auto-detection

**Checkpoint**: API reference contains complete streaming endpoint documentation, file constraints, and updated parameters. User Story 2 is independently testable.

---

## Phase 5: User Story 3 — Developer Understands Chat Architecture (Priority: P3)

**Goal**: Update the architecture documentation with ChatAgentService design, missing frontend components, and chat-related hooks.

**Independent Test**: Review the architecture page and confirm that the ChatAgentService subsection exists with session management, tool registration, dual dispatch, and streaming details. Verify the frontend component table and hooks section include all chat-related entries.

### Implementation for User Story 3

- [ ] T019 [US3] Add "ChatAgentService" subsection after "AI Completion Providers" in solune/docs/architecture.md — Agent Framework wrapper, session management (TTL eviction 3600s, 100 max concurrent, LRU), tool registration + MCP, dual dispatch (ai_enhance on → Agent Framework, off → fallback), streaming (run_stream())
- [ ] T020 [P] [US3] Update components/chat/ row in Key Frontend Modules table in solune/docs/architecture.md — append MentionInput, MentionAutocomplete, FilePreviewChips, MarkdownRenderer, ChatMessageSkeleton, PipelineWarningBanner, PipelineIndicator
- [ ] T021 [P] [US3] Update hooks/ row in Key Frontend Modules table in solune/docs/architecture.md — append useChatProposals, useFileUpload, useMentionAutocomplete

**Checkpoint**: Architecture page has ChatAgentService subsection and all chat components/hooks in tables. User Story 3 is independently testable.

---

## Phase 6: User Story 4 — Developer Locates Chat Source Files (Priority: P4)

**Goal**: Update the project structure documentation to list all chat-related source files, components, and hooks.

**Independent Test**: Review the project structure page and confirm that services/chat_agent.py appears in the backend services listing, all 7 missing chat components appear in the frontend listing, and all 3 missing hooks appear in the hooks listing.

### Implementation for User Story 4

- [ ] T022 [US4] Add chat_agent.py, agent_provider.py, and agent_tools.py to backend services/ tree in solune/docs/project-structure.md — with inline # comments describing each
- [ ] T023 [P] [US4] Update components/chat/ listing in frontend tree in solune/docs/project-structure.md — add 7 missing components (MentionInput, MentionAutocomplete, FilePreviewChips, MarkdownRenderer, ChatMessageSkeleton, PipelineWarningBanner, PipelineIndicator)
- [ ] T024 [P] [US4] Update hooks/ listing in frontend tree in solune/docs/project-structure.md — add useFileUpload, useMentionAutocomplete, useChatProposals

**Checkpoint**: Project structure page lists all chat-related backend services, frontend components, and hooks. User Story 4 is independently testable.

---

## Phase 7: User Story 5 — Stakeholder Tracks Feature Progress (Priority: P5)

**Goal**: Update the roadmap to reflect that v0.2.0 chat features are implemented and the architecture evolution diagram is current.

**Independent Test**: Review the roadmap page and confirm that all v0.2.0 chat features are marked as implemented (✅) and the architecture evolution diagram reflects v0.2.0 as the current version.

### Implementation for User Story 5

- [ ] T025 [US5] Mark all v0.2.0 feature bullets as implemented (✅) in solune/docs/roadmap.md
- [ ] T026 [US5] Update architecture evolution diagram in solune/docs/roadmap.md — change "v0.1.0 (today)" to "v0.2.0 (current)", update left side to reflect Agent Framework architecture
- [ ] T027 [US5] Update timeline table in solune/docs/roadmap.md — reflect v0.2.0 as shipped

**Checkpoint**: Roadmap accurately reflects v0.2.0 as the current implemented version. User Story 5 is independently testable.

---

## Phase 8: User Story 6 — Reader Navigates Between Related Docs (Priority: P6)

**Goal**: Add cross-reference links so readers can discover the chat page guide from layout.md and the pages index.

**Independent Test**: Check that layout.md contains a link to chat.md, pages/README.md includes the chat page in its index, and all internal markdown links resolve correctly.

**⚠️ DEPENDENCY**: Requires User Story 1 (Phase 3) to be complete — `docs/pages/chat.md` must exist before adding links to it.

### Implementation for User Story 6

- [ ] T028 [P] [US6] Add cross-reference link to chat.md in the Chat Panel section of solune/docs/pages/layout.md — "For the full chat feature guide, see [Chat](chat.md)."
- [ ] T029 [P] [US6] Add Chat row to Page Overview table in solune/docs/pages/README.md — "| [Chat](chat.md) | AI chat panel — messaging, proposals, file uploads, and streaming | [chat.md](chat.md) |"

**Checkpoint**: Cross-reference links in place. All internal links resolve to existing files.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and quality checks across all updated documentation.

- [ ] T030 Verify all internal markdown links resolve across updated files — zero broken links (FR-011, SC-003)
- [ ] T031 Verify documentation follows existing conventions — markdown tables, bullets, callouts, "What's next?" footers where applicable (FR-012, SC-002)
- [ ] T032 Verify no code, env vars, or configuration changes were introduced (SC-008)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Empty for this feature — skip
- **User Stories 1–5 (Phases 3–7)**: All independent of each other — can proceed in parallel
- **User Story 6 (Phase 8)**: Depends on User Story 1 (chat.md must exist before linking to it)
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)** — `docs/pages/chat.md`: No dependencies — can start immediately
- **User Story 2 (P2)** — `docs/api-reference.md`: No dependencies — can start immediately
- **User Story 3 (P3)** — `docs/architecture.md`: No dependencies — can start immediately
- **User Story 4 (P4)** — `docs/project-structure.md`: No dependencies — can start immediately
- **User Story 5 (P5)** — `docs/roadmap.md`: No dependencies — can start immediately
- **User Story 6 (P6)** — `docs/pages/layout.md` + `docs/pages/README.md`: **Depends on US1** (chat.md must exist)

### Within Each User Story

- Documentation sections are sequential (write skeleton → fill sections)
- Different files can be edited in parallel within the same story
- Each story is independently verifiable after completion

### Parallel Opportunities

- **User Stories 1–5 can all run in parallel** — each targets a different file with no overlap
- Within US1: Section writing is sequential (same file), but can be batched
- Within US2: T015 and T016 can run in parallel (different table rows), then T017 and T018 are sequential (new subsections)
- Within US3: T020 and T021 can run in parallel (different table rows)
- Within US4: T023 and T024 can run in parallel (different tree sections)
- Within US6: T028 and T029 can run in parallel (different files)

---

## Parallel Example: User Stories 1–5

```bash
# All five user stories target different files — launch in parallel:
Task: "Create chat.md with all 12 sections"            → docs/pages/chat.md
Task: "Update API reference with streaming/files"        → docs/api-reference.md
Task: "Update architecture with ChatAgentService"        → docs/architecture.md
Task: "Update project structure with missing entries"    → docs/project-structure.md
Task: "Update roadmap with v0.2.0 status"               → docs/roadmap.md

# After all five complete, launch cross-references:
Task: "Add link in layout.md"                            → docs/pages/layout.md
Task: "Add row in README.md"                             → docs/pages/README.md
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verify conventions)
2. Complete Phase 3: User Story 1 — create `docs/pages/chat.md`
3. **STOP and VALIDATE**: Verify all 12 sections are complete, accurate, and follow conventions
4. This single page delivers the highest-impact documentation improvement

### Incremental Delivery

1. Complete US1 → Chat page guide exists → **MVP delivered!**
2. Complete US2 → API reference updated → API consumers unblocked
3. Complete US3 → Architecture documented → Maintainers unblocked
4. Complete US4 → Project structure updated → Code navigation improved
5. Complete US5 → Roadmap current → Stakeholders informed
6. Complete US6 → Cross-references added → Documentation fully connected
7. Complete Phase 9 → All links verified → Quality assured

### Parallel Team Strategy

With multiple contributors:

1. All contributors verify conventions (Phase 1) together
2. Once Phase 1 is done:
   - Contributor A: User Story 1 (chat.md — largest task, ~30 min)
   - Contributor B: User Stories 2 + 4 (api-reference.md + project-structure.md, ~25 min)
   - Contributor C: User Stories 3 + 5 (architecture.md + roadmap.md, ~25 min)
3. After US1 completes: Any contributor handles US6 (cross-references, ~5 min)
4. Final: Link verification (Phase 9)

---

## Summary

| Metric | Value |
|--------|-------|
| **Total tasks** | 32 |
| **User Story 1 (P1)** | 12 tasks (T003–T014) — chat.md |
| **User Story 2 (P2)** | 4 tasks (T015–T018) — api-reference.md |
| **User Story 3 (P3)** | 3 tasks (T019–T021) — architecture.md |
| **User Story 4 (P4)** | 3 tasks (T022–T024) — project-structure.md |
| **User Story 5 (P5)** | 3 tasks (T025–T027) — roadmap.md |
| **User Story 6 (P6)** | 2 tasks (T028–T029) — layout.md + README.md |
| **Setup** | 2 tasks (T001–T002) |
| **Polish** | 3 tasks (T030–T032) |
| **Parallel opportunities** | US1–US5 fully parallel; T015∥T016, T020∥T021, T023∥T024, T028∥T029 within stories |
| **Independent test per story** | ✅ Each story targets a separate file; independently verifiable |
| **Suggested MVP scope** | User Story 1 only (chat.md — 12 tasks) |
| **Format validation** | ✅ All tasks follow `- [ ] [TaskID] [P?] [Story?] Description with file path` |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and verifiable
- No tests needed — documentation-only feature (Constitution Principle IV)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All file paths reference `solune/docs/` directory structure
