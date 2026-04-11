# Tasks: Multi-Chat App Page

**Input**: Design documents from `plan.md`, `specs/001-multi-chat-app-page/spec.md`, `data-model.md`, `research.md`, `contracts/`
**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `data-model.md`, `research.md`, `contracts/`

**Tests**: Tests ARE explicitly requested in Phase 5 of the spec. Test tasks are included for backend CRUD, frontend components, and hooks.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5, US6, US7)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/src/`, `solune/backend/tests/`, `solune/frontend/src/`
- Backend migrations: `solune/backend/src/migrations/`
- Backend tests: `solune/backend/tests/unit/test_<module>.py`
- Frontend hooks: `solune/frontend/src/hooks/`
- Frontend components: `solune/frontend/src/components/chat/`
- Frontend pages: `solune/frontend/src/pages/`
- Frontend tests: colocated `<Component>.test.tsx` or `src/__tests__/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the database migration and verify existing test suites are green before modifying any source code.

- [ ] T001 Create migration file `solune/backend/src/migrations/044_conversations.sql` — New `conversations` table (conversation_id, session_id, title, created_at, updated_at) with FK to user_sessions; ALTER chat_messages, chat_proposals, chat_recommendations to add nullable conversation_id column with FK ON DELETE SET NULL; create indexes idx_conversations_session_id, idx_conversations_updated_at, idx_chat_messages_conversation_id, idx_chat_proposals_conversation_id, idx_chat_recommendations_conversation_id
- [ ] T002 [P] Verify existing backend test suite passes with `cd solune/backend && python -m pytest tests/unit/ -q --timeout=120`
- [ ] T003 [P] Verify existing frontend test suite passes with `cd solune/frontend && npm test`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend models, store methods, API endpoints, agent isolation, and frontend types/schemas/API client. All user stories depend on this phase.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Backend Models

- [ ] T004 Add Conversation model (conversation_id UUID PK, session_id UUID, title str default "New Chat", created_at datetime, updated_at datetime) to `solune/backend/src/models/chat.py`
- [ ] T005 [P] Add ConversationCreateRequest model (title str, max_length=200, default "New Chat") to `solune/backend/src/models/chat.py`
- [ ] T006 [P] Add ConversationUpdateRequest model (title str, max_length=200) to `solune/backend/src/models/chat.py`
- [ ] T007 [P] Add ConversationsListResponse model (conversations: list[Conversation]) to `solune/backend/src/models/chat.py`
- [ ] T008 Add optional conversation_id (UUID | None = None) field to ChatMessage and ChatMessageRequest in `solune/backend/src/models/chat.py`

### Backend Store

- [ ] T009 Add save_conversation(db, session_id, conversation_id, title) method using INSERT with ON CONFLICT handling to `solune/backend/src/services/chat_store.py`
- [ ] T010 [P] Add get_conversations(db, session_id) method returning conversations ordered by updated_at DESC to `solune/backend/src/services/chat_store.py`
- [ ] T011 [P] Add get_conversation_by_id(db, conversation_id) method to `solune/backend/src/services/chat_store.py`
- [ ] T012 [P] Add update_conversation(db, conversation_id, title) method that also updates updated_at timestamp to `solune/backend/src/services/chat_store.py`
- [ ] T013 [P] Add delete_conversation(db, conversation_id) method to `solune/backend/src/services/chat_store.py`
- [ ] T014 Update save_message() to accept optional conversation_id parameter and include it in INSERT to `solune/backend/src/services/chat_store.py`
- [ ] T015 Update get_messages() to accept optional conversation_id parameter and append AND conversation_id = ? filter when present to `solune/backend/src/services/chat_store.py`
- [ ] T016 [P] Update count_messages() to accept optional conversation_id parameter with same filter logic to `solune/backend/src/services/chat_store.py`
- [ ] T017 [P] Update clear_messages() to accept optional conversation_id parameter to scope DELETE to conversation to `solune/backend/src/services/chat_store.py`

### Backend API

- [ ] T018 Add POST /conversations endpoint (creates conversation, returns 201 with Conversation) to `solune/backend/src/api/chat.py`
- [ ] T019 [P] Add GET /conversations endpoint (returns ConversationsListResponse for session) to `solune/backend/src/api/chat.py`
- [ ] T020 [P] Add PATCH /conversations/{conversation_id} endpoint (updates title, returns Conversation; 404 if not found) to `solune/backend/src/api/chat.py`
- [ ] T021 [P] Add DELETE /conversations/{conversation_id} endpoint (deletes conversation, returns message; 404 if not found) to `solune/backend/src/api/chat.py`
- [ ] T022 Update GET /messages endpoint to accept optional conversation_id query parameter for filtering to `solune/backend/src/api/chat.py`
- [ ] T023 Update POST /messages endpoint to accept optional conversation_id in request body to `solune/backend/src/api/chat.py`
- [ ] T024 [P] Update POST /messages/stream endpoint to accept optional conversation_id in request body to `solune/backend/src/api/chat.py`
- [ ] T025 [P] Update DELETE /messages endpoint to accept optional conversation_id query parameter for scoped deletion to `solune/backend/src/api/chat.py`

### Backend Agent Isolation

- [ ] T026 Add _agent_key(session_id, conversation_id=None) helper that returns "{session_id}:{conversation_id}" or "{session_id}:_" when None to `solune/backend/src/services/chat_agent.py`
- [ ] T027 Update run() and run_stream() methods to accept optional conversation_id and pass composite key to _session_mapping.get_or_create() in `solune/backend/src/services/chat_agent.py`

### Frontend Types

- [ ] T028 [P] Add Conversation interface (conversation_id, session_id, title, created_at, updated_at) and ConversationsListResponse interface to `solune/frontend/src/types/index.ts`
- [ ] T029 [P] Add optional conversation_id field to ChatMessage and ChatMessageRequest interfaces in `solune/frontend/src/types/index.ts`

### Frontend Schemas

- [ ] T030 [P] Add ConversationSchema and ConversationsListResponseSchema Zod schemas to `solune/frontend/src/services/schemas/chat.ts`
- [ ] T031 [P] Add optional conversation_id field to ChatMessageSchema in `solune/frontend/src/services/schemas/chat.ts`

### Frontend API Client

- [ ] T032 Add conversationApi namespace with create(), list(), update(id), delete(id) methods to `solune/frontend/src/services/api.ts`
- [ ] T033 Update chatApi.getMessages() to accept optional conversationId parameter and pass as query param to `solune/frontend/src/services/api.ts`
- [ ] T034 [P] Update chatApi.sendMessage() and sendMessageStream() to accept optional conversationId and include in request body to `solune/frontend/src/services/api.ts`
- [ ] T035 [P] Update chatApi.clearMessages() to accept optional conversationId and pass as query param to `solune/frontend/src/services/api.ts`

### Frontend State Hooks

- [ ] T036 Create useConversations React Query hook with useQuery(['conversations']) for list and useMutation for create/update/delete with auto-invalidation in `solune/frontend/src/hooks/useConversations.ts`
- [ ] T037 Update useChat hook to accept optional conversationId parameter, use ['chat', 'messages', conversationId ?? 'global'] as query key, and pass conversationId to all API calls in `solune/frontend/src/hooks/useChat.ts`

**Checkpoint**: Foundation ready — all backend endpoints functional, frontend types/API client/hooks compile, existing tests pass. User story implementation can now begin.

---

## Phase 3: User Story 1 — Start a Chat on the Home Page (Priority: P1) 🎯 MVP

**Goal**: Replace the AppPage marketing landing page with a full-viewport single chat panel experience. An authenticated user navigates to `/` and immediately sees a functional chat panel with all existing chat capabilities (streaming, proposals, plan mode, file upload, mentions, commands).

**Independent Test**: Navigate to `/`, type a message, verify a streaming response appears. All existing chat features work in the panel. Run `cd solune/frontend && npm test -- AppPage` to confirm.

### Implementation for User Story 1

- [ ] T038 [US1] Create useChatPanels hook with basic single-panel state (panels array with panelId, conversationId, widthPercent), addPanel(), removePanel(panelId) methods, and default single panel at 100% width in `solune/frontend/src/hooks/useChatPanels.ts`
- [ ] T039 [US1] Create ChatPanel component that accepts conversationId and onClose props, owns its own useChat(conversationId) + usePlan() instances, renders panel header with title and close button, and wraps ChatInterface with full existing functionality in `solune/frontend/src/components/chat/ChatPanel.tsx`
- [ ] T040 [US1] Create ChatPanelManager component that uses useChatPanels() + useConversations(), renders panels in a flexbox side-by-side layout, includes "Add Chat" button that creates a new conversation + panel in `solune/frontend/src/components/chat/ChatPanelManager.tsx`
- [ ] T041 [US1] Rewrite AppPage to replace marketing content with `<ChatPanelManager />` at full viewport height `h-[calc(100vh-<header-height>)]` in `solune/frontend/src/pages/AppPage.tsx`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Navigate to `/` and see a single working chat panel.

---

## Phase 4: User Story 7 — Chat Popup Backward Compatibility (Priority: P1)

**Goal**: Ensure the existing floating ChatPopup on pages other than `/` (e.g., `/projects`, `/pipeline`, `/agents`) continues to function exactly as before. Messages without conversation_id remain accessible. No changes to ChatPopup.tsx.

**Independent Test**: Navigate to `/projects`, open the ChatPopup, send a message, verify it works identically to before. Run existing ChatPopup tests: `cd solune/frontend && npm test -- ChatPopup`.

### Verification for User Story 7

- [ ] T042 [US7] Verify ChatPopup.tsx and ChatInterface.tsx are NOT modified — confirm via `git diff` that these files have zero changes
- [ ] T043 [US7] Verify backend messages without conversation_id continue to work — GET /messages without conversation_id returns all session messages (existing behavior preserved in T015 and T022)
- [ ] T044 [US7] Run existing ChatPopup tests to confirm zero regressions: `cd solune/frontend && npm test -- ChatPopup`

**Checkpoint**: ChatPopup behavior is unchanged. All existing ChatPopup tests pass.

---

## Phase 5: User Story 2 — Open Multiple Chat Panels Side by Side (Priority: P2)

**Goal**: Users can click "Add Chat" to open additional chat panels. Each panel operates independently with its own conversation. Panels can be closed. Messages in one panel never appear in another.

**Independent Test**: Click "Add Chat," send different messages in each panel, confirm responses are independent. Close a panel, verify remaining panels redistribute width.

### Implementation for User Story 2

- [ ] T045 [US2] Extend useChatPanels hook to support multiple panels — addPanel() creates new conversation via conversationApi.create() and adds panel with redistributed widths (100/N per panel) in `solune/frontend/src/hooks/useChatPanels.ts`
- [ ] T046 [US2] Extend useChatPanels hook removePanel(panelId) — remove panel, redistribute remaining panel widths proportionally, prevent removal of last panel in `solune/frontend/src/hooks/useChatPanels.ts`
- [ ] T047 [US2] Update ChatPanelManager to render multiple panels in flexbox row layout with each panel receiving its widthPercent as flex-basis in `solune/frontend/src/components/chat/ChatPanelManager.tsx`
- [ ] T048 [US2] Add close button handler in ChatPanel that calls onClose callback to trigger removePanel() in `solune/frontend/src/components/chat/ChatPanel.tsx`

**Checkpoint**: Multiple panels open side-by-side, each sends/receives independently, close removes panel.

---

## Phase 6: User Story 3 — Resize Chat Panels (Priority: P3)

**Goal**: Users drag a resize handle between adjacent panels to allocate more space to one conversation. Panels enforce a 320px minimum width.

**Independent Test**: Open two panels, drag the resize handle, verify width changes. Attempt to resize below 320px, verify it snaps to minimum.

### Implementation for User Story 3

- [ ] T049 [US3] Add draggable resize handles between panels in ChatPanelManager — render thin vertical bar (4–8px) with `cursor: col-resize` between each pair of adjacent panels in `solune/frontend/src/components/chat/ChatPanelManager.tsx`
- [ ] T050 [US3] Implement resize drag logic using native mousedown/mousemove/mouseup on window with requestAnimationFrame gating — calculate delta, update adjacent panel widthPercent values in `solune/frontend/src/components/chat/ChatPanelManager.tsx`
- [ ] T051 [US3] Add min-width constraint (320px) to resize logic — prevent panels from shrinking below minimum, snap to minimum when drag exceeds limit in `solune/frontend/src/components/chat/ChatPanelManager.tsx`
- [ ] T052 [P] [US3] Add touch event support (touchstart/touchmove/touchend) for tablet resize in `solune/frontend/src/components/chat/ChatPanelManager.tsx`

**Checkpoint**: Resize handle works between panels. Min-width enforced. No layout jank during drag.

---

## Phase 7: User Story 4 — Manage Conversations (Priority: P3)

**Goal**: Users can rename a conversation by editing the title in the panel header. Titles persist via the PATCH /conversations/{id} endpoint. Users can also delete conversations.

**Independent Test**: Click the title in a panel header, edit it, confirm it persists after refresh. Delete a conversation, confirm panel is closed.

### Implementation for User Story 4

- [ ] T053 [US4] Add inline-editable title to ChatPanel header — click title to show input, Enter/blur saves via useConversations().updateConversation(), Escape cancels in `solune/frontend/src/components/chat/ChatPanel.tsx`
- [ ] T054 [US4] Add title truncation with ellipsis in ChatPanel header for long titles (CSS text-overflow: ellipsis, max-width) in `solune/frontend/src/components/chat/ChatPanel.tsx`
- [ ] T055 [P] [US4] Wire delete conversation to close panel — close button triggers conversation deletion via useConversations().deleteConversation() then removes panel in `solune/frontend/src/components/chat/ChatPanel.tsx`

**Checkpoint**: Conversation titles are editable inline, persist on save, and truncate gracefully. Delete removes conversation and panel.

---

## Phase 8: User Story 5 — Restore Panel Layout on Return (Priority: P3)

**Goal**: Panel layout (which conversations are open and their width percentages) is persisted to localStorage and restored on page load. Stale conversation references are pruned.

**Independent Test**: Open multiple panels, refresh browser, verify same panels reappear with correct conversations and widths.

### Implementation for User Story 5

- [ ] T056 [US5] Add debounced localStorage persistence to useChatPanels — save panel layout as JSON under key `solune:chat-panels` with schema `{ version: 1, panels: [...] }` on state changes (debounce writes during rapid interactions like resize) in `solune/frontend/src/hooks/useChatPanels.ts`
- [ ] T057 [US5] Add restore-on-load logic to useChatPanels — on mount, read from localStorage, validate schema version, load panels; if localStorage is empty or invalid, create default single panel in `solune/frontend/src/hooks/useChatPanels.ts`
- [ ] T058 [US5] Add stale conversation pruning — on restore, verify each panel's conversationId exists via conversationApi.list(); replace stale references with new empty conversations in `solune/frontend/src/hooks/useChatPanels.ts`

**Checkpoint**: Panel layout persists across browser refresh. Stale conversations are handled gracefully.

---

## Phase 9: User Story 6 — Mobile Chat Experience (Priority: P4)

**Goal**: On viewports below 768px, display panels one at a time with tab-based switching. A horizontal tab bar at the top shows conversation titles. Inactive panels remain mounted but hidden.

**Independent Test**: Resize browser to < 768px, verify single-panel display with tabs. Add second conversation, switch tabs, verify content changes.

### Implementation for User Story 6

- [ ] T059 [US6] Add mobile detection (viewport < 768px) to ChatPanelManager using a media query hook or window.matchMedia in `solune/frontend/src/components/chat/ChatPanelManager.tsx`
- [ ] T060 [US6] Implement tab bar UI for mobile — horizontal row of tab buttons showing conversation titles (truncated to ~15 chars), active tab highlighted with bottom border, "+" button for Add Chat in `solune/frontend/src/components/chat/ChatPanelManager.tsx`
- [ ] T061 [US6] Implement tab switching — active tab shows full ChatPanel, inactive panels use `display: none` to preserve state (React Query cache, scroll position, streaming state) in `solune/frontend/src/components/chat/ChatPanelManager.tsx`

**Checkpoint**: Mobile users see tab-based interface. Tab switching preserves conversation state.

---

## Phase 10: Testing & Verification

**Purpose**: Add tests for new backend conversation CRUD, new frontend components, and hooks. Update existing AppPage tests.

### Backend Tests

- [ ] T062 [P] Add conversation CRUD tests (save_conversation, get_conversations, get_conversation_by_id, update_conversation, delete_conversation) to `solune/backend/tests/unit/test_chat_store.py`
- [ ] T063 [P] Add message filtering by conversation_id tests (get_messages with conversation_id returns scoped results, get_messages without conversation_id returns all) to `solune/backend/tests/unit/test_chat_store.py`
- [ ] T064 [P] Add backward compatibility test (messages without conversation_id continue to work, conversation_id defaults to NULL) to `solune/backend/tests/unit/test_chat_store.py`
- [ ] T065 [P] Add conversation API endpoint tests (POST/GET/PATCH/DELETE /conversations, 404 handling) to `solune/backend/tests/unit/test_chat_api.py`
- [ ] T066 [P] Add agent session key isolation test (different conversation_ids produce different agent keys, None produces sentinel key) to `solune/backend/tests/unit/test_chat_agent.py`

### Frontend Tests

- [ ] T067 [P] Update AppPage tests for new chat layout — renders ChatPanelManager, single panel by default, no marketing content in `solune/frontend/src/pages/AppPage.test.tsx`
- [ ] T068 [P] Create ChatPanel component tests — renders with conversationId, shows title, close button works, wraps ChatInterface in `solune/frontend/src/components/chat/ChatPanel.test.tsx`
- [ ] T069 [P] Create ChatPanelManager component tests — renders single panel default, "Add Chat" adds second panel, close panel removes it, resize handle renders between panels in `solune/frontend/src/components/chat/ChatPanelManager.test.tsx`
- [ ] T070 [P] Create useConversations hook tests — list returns conversations, create invalidates cache, update saves title, delete removes conversation in `solune/frontend/src/__tests__/useConversations.test.ts`

**Checkpoint**: All new and existing tests pass. Run `cd solune/backend && python -m pytest tests/unit/ -q --timeout=120` and `cd solune/frontend && npm test`.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation, and cleanup across all user stories

- [ ] T071 Run full backend validation: `cd solune/backend && ruff check src/ tests/ && ruff format --check src/ tests/ && python -m pytest tests/unit/ -q --timeout=120`
- [ ] T072 Run full frontend validation: `cd solune/frontend && npm run lint && npm run type-check && npm test && npm run build`
- [ ] T073 Verify zero pre-existing test failures — compare test counts before and after changes
- [ ] T074 Run quickstart.md validation scenarios (create conversation, send message, list conversations, verify filtering)
- [ ] T075 [P] Verify all new files follow repository naming conventions and are properly exported/imported

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) — MVP delivery
- **User Story 7 (Phase 4)**: Depends on Foundational (Phase 2) — verification only, can run in parallel with US1
- **User Story 2 (Phase 5)**: Depends on US1 (Phase 3) — extends single-panel to multi-panel
- **User Story 3 (Phase 6)**: Depends on US2 (Phase 5) — adds resize to multi-panel
- **User Story 4 (Phase 7)**: Depends on US1 (Phase 3) — adds title editing to panel header
- **User Story 5 (Phase 8)**: Depends on US2 (Phase 5) — persists multi-panel layout
- **User Story 6 (Phase 9)**: Depends on US2 (Phase 5) — adds mobile tab switching
- **Testing (Phase 10)**: Can start after each story's phase completes; full suite after Phase 9
- **Polish (Phase 11)**: Depends on all user stories and testing being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **User Story 7 (P1)**: Can start after Foundational (Phase 2) — Verification only, parallel with US1
- **User Story 2 (P2)**: Depends on US1 for basic ChatPanel/ChatPanelManager to extend
- **User Story 3 (P3)**: Depends on US2 for multi-panel layout to add resize handles
- **User Story 4 (P3)**: Depends on US1 for ChatPanel header to add editable title — can run parallel with US2/US3
- **User Story 5 (P3)**: Depends on US2 for multi-panel state to persist — can run parallel with US3
- **User Story 6 (P4)**: Depends on US2 for multi-panel layout to add mobile tab switching

### Within Each User Story

- Models before services before endpoints (backend, Phase 2)
- Types before schemas before API client before hooks (frontend, Phase 2)
- Hooks before components before pages (frontend, Phases 3+)
- All tasks marked [P] within a phase can run in parallel (different files)
- Commit after each task or logical group
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1**: T002 and T003 can run in parallel (independent test suites)
- **Phase 2 Backend Models**: T005, T006, T007 can run in parallel (same file but independent sections)
- **Phase 2 Backend Store**: T010, T011, T012, T013 can run in parallel; T016, T017 can run in parallel
- **Phase 2 Backend API**: T019, T020, T021 can run in parallel; T024, T025 can run in parallel
- **Phase 2 Frontend**: T028+T029, T030+T031 can run in parallel (different files)
- **Phase 2 Frontend API**: T034, T035 can run in parallel
- **Phase 4 (US7)**: All verification tasks can run in parallel
- **Phase 10 (Testing)**: All test creation tasks (T062–T070) can run in parallel (separate test files)
- **Cross-story**: US4 (Phase 7) can run in parallel with US2/US3/US5/US6 since it only touches ChatPanel

---

## Parallel Example: User Story 1

```text
# Phase 2 foundational tasks that can be parallelized:
Task T028: "Add Conversation interface to solune/frontend/src/types/index.ts"
Task T030: "Add ConversationSchema to solune/frontend/src/services/schemas/chat.ts"

# Phase 3 US1 tasks are sequential (hooks → components → pages):
Task T038: "Create useChatPanels hook"
Task T039: "Create ChatPanel component" (depends on T038)
Task T040: "Create ChatPanelManager component" (depends on T039)
Task T041: "Rewrite AppPage" (depends on T040)
```

## Parallel Example: Testing Phase

```text
# All test tasks can run in parallel (separate files):
Task T062: "Conversation CRUD tests in test_chat_store.py"
Task T063: "Message filtering tests in test_chat_store.py"
Task T064: "Backward compat test in test_chat_store.py"
Task T065: "API endpoint tests in test_chat_api.py"
Task T066: "Agent session key test in test_chat_agent.py"
Task T067: "AppPage tests in AppPage.test.tsx"
Task T068: "ChatPanel tests in ChatPanel.test.tsx"
Task T069: "ChatPanelManager tests in ChatPanelManager.test.tsx"
Task T070: "useConversations tests in useConversations.test.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (migration + verify existing tests)
2. Complete Phase 2: Foundational (all backend + frontend types/API/hooks)
3. Complete Phase 3: User Story 1 (single chat panel on AppPage)
4. **STOP and VALIDATE**: Navigate to `/`, send a message, verify streaming response in chat panel
5. Deploy/demo if ready — AppPage is a working chat workspace

### Incremental Delivery

1. Complete Setup + Foundational → Backend fully functional, frontend typed
2. Add US1 (Single panel) → Test independently → AppPage is a chat workspace (MVP!)
3. Add US7 (Backward compat) → Verify ChatPopup still works → Regression safety
4. Add US2 (Multi-panel) → Test independently → Side-by-side panels work
5. Add US3 (Resize) → Test independently → Panels are resizable
6. Add US4 (Conversation management) → Test independently → Titles editable
7. Add US5 (Layout persistence) → Test independently → Panels restore on refresh
8. Add US6 (Mobile) → Test independently → Tab switching on mobile
9. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 → US2 → US3 (core panel path)
   - Developer B: User Story 7 (verification) → US4 (conversation management) → US5 (persistence)
   - Developer C: Testing (Phase 10) as stories complete → US6 (mobile) → Polish
3. Stories integrate cleanly because they touch different files/areas

---

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 75 (T001–T075) |
| Phase 1 (Setup) | 3 tasks |
| Phase 2 (Foundational) | 34 tasks |
| Phase 3 (US1 — Single Panel MVP) | 4 tasks |
| Phase 4 (US7 — Backward Compat) | 3 tasks |
| Phase 5 (US2 — Multi-Panel) | 4 tasks |
| Phase 6 (US3 — Resize) | 4 tasks |
| Phase 7 (US4 — Conversation Mgmt) | 3 tasks |
| Phase 8 (US5 — Layout Persistence) | 3 tasks |
| Phase 9 (US6 — Mobile) | 3 tasks |
| Phase 10 (Testing) | 9 tasks |
| Phase 11 (Polish) | 5 tasks |
| Parallel opportunities | 42 of 75 tasks are parallelizable |
| Suggested MVP scope | Setup + Foundational + US1 (Phases 1–3) |
| Independent test criteria | Each story validates with its own acceptance test |

### Task Count per User Story

| User Story | Priority | Tasks | Phase |
|------------|----------|-------|-------|
| US1: Start a Chat on Home Page | P1 | 4 | Phase 3 |
| US2: Multiple Panels Side by Side | P2 | 4 | Phase 5 |
| US3: Resize Chat Panels | P3 | 4 | Phase 6 |
| US4: Manage Conversations | P3 | 3 | Phase 7 |
| US5: Restore Panel Layout | P3 | 3 | Phase 8 |
| US6: Mobile Chat Experience | P4 | 3 | Phase 9 |
| US7: Chat Popup Backward Compat | P1 | 3 | Phase 4 |

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Foundational phase (Phase 2) is the largest — intentionally front-loaded to unblock all stories
- ChatPopup.tsx and ChatInterface.tsx are UNTOUCHED — reused as-is
- All conversation_id fields are nullable for backward compatibility
- Agent sessions use composite key `{session_id}:{conversation_id}` for isolation
- Panel layout persisted to localStorage under `solune:chat-panels` with schema version
- Mobile breakpoint at 768px switches from side-by-side panels to tab-based navigation
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
