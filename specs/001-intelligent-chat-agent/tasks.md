# Tasks: Intelligent Chat Agent (Microsoft Agent Framework)

**Input**: Design documents from `/specs/001-intelligent-chat-agent/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/chat-api.yaml, quickstart.md

**Tests**: Included as mandated by spec (FR requires existing tests to pass; new tests for agent tools and chat agent service per plan Step 10).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/src/`, `solune/frontend/src/`
- **Backend tests**: `solune/backend/tests/unit/`
- **Config**: `solune/backend/pyproject.toml`, `solune/backend/src/config.py`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Install dependencies and configure the agent framework settings

- [ ] T001 Add agent-framework-core, agent-framework-azure-ai, agent-framework-github-copilot (with `--pre` / `>=1.0.0b` pins) and sse-starlette to dependencies in solune/backend/pyproject.toml
- [ ] T002 [P] Add agent framework config settings (agent_session_ttl_seconds, agent_max_concurrent_sessions, agent_streaming_enabled) to Settings class in solune/backend/src/config.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core agent infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 [P] Create unified system instruction with tool usage guidance, clarifying-question policy (2–3 questions before acting), difficulty assessment, and dynamic project context injection in solune/backend/src/prompts/agent_instructions.py
- [ ] T004 [P] Create agent provider factory with create_agent() returning Agent for copilot or azure_openai based on Settings.ai_provider in solune/backend/src/services/agent_provider.py
- [ ] T005 [P] Create ToolResult TypedDict (content, action_type, action_data) and register_tools() helper for tool list assembly in solune/backend/src/services/agent_tools.py

**Checkpoint**: Foundation ready — agent infrastructure in place, user story implementation can now begin

---

## Phase 3: User Story 1 — Natural Conversation with Intelligent Tool Selection (Priority: P1) 🎯 MVP

**Goal**: Replace the hardcoded priority dispatch cascade in chat.py with a single agent invocation that selects the appropriate tool based on reasoning. Users send messages and the agent automatically chooses the right action (task creation, issue recommendation, status change, clarifying questions).

**Independent Test**: Send various chat messages (feature requests, task descriptions, status updates, ambiguous requests) and verify the agent selects the correct tool and produces the expected structured output matching existing ChatMessage/AITaskProposal/IssueRecommendation schemas.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T006 [P] [US1] Write unit tests for create_task_proposal tool with mocked FunctionInvocationContext in solune/backend/tests/unit/test_agent_tools.py
- [ ] T007 [P] [US1] Write unit tests for create_issue_recommendation tool with mocked FunctionInvocationContext in solune/backend/tests/unit/test_agent_tools.py
- [ ] T008 [P] [US1] Write unit tests for update_task_status tool (using identify_target_task) with mocked context in solune/backend/tests/unit/test_agent_tools.py
- [ ] T009 [P] [US1] Write unit tests for ask_clarifying_question, get_project_context, get_pipeline_list tools in solune/backend/tests/unit/test_agent_tools.py
- [ ] T010 [P] [US1] Write unit tests for ChatAgentService.run() verifying response conversion (AgentResponse → ChatMessage with action_type/action_data) in solune/backend/tests/unit/test_chat_agent.py

### Implementation for User Story 1

- [ ] T011 [P] [US1] Implement create_task_proposal(title, description) @tool function returning ToolResult with action_type=TASK_CREATE in solune/backend/src/services/agent_tools.py
- [ ] T012 [P] [US1] Implement create_issue_recommendation(title, user_story, ui_ux_description, functional_requirements, technical_notes) @tool function returning ToolResult with action_type=ISSUE_CREATE in solune/backend/src/services/agent_tools.py
- [ ] T013 [P] [US1] Implement update_task_status(task_reference, target_status) @tool function (reusing identify_target_task from ai_agent.py) returning ToolResult with action_type=STATUS_UPDATE in solune/backend/src/services/agent_tools.py
- [ ] T014 [P] [US1] Implement ask_clarifying_question(question) @tool function returning ToolResult with action_type=None in solune/backend/src/services/agent_tools.py
- [ ] T015 [P] [US1] Implement get_project_context() and get_pipeline_list() @tool functions returning ToolResult with action_type=None in solune/backend/src/services/agent_tools.py
- [ ] T016 [US1] Create ChatAgentService class with singleton Agent instance, run() method that invokes agent and converts AgentResponse.messages → ChatMessage with action_type/action_data in solune/backend/src/services/chat_agent.py
- [ ] T017 [US1] Refactor send_message in solune/backend/src/api/chat.py to replace 5-tier priority dispatch (_handle_feature_request, _handle_status_change, _handle_task_generation, _handle_transcript_upload) with single ChatAgentService.run() call
- [ ] T018 [US1] Preserve ai_enhance=False bypass (simple title-only generation) and /agent meta-command handling in solune/backend/src/api/chat.py
- [ ] T019 [US1] Update mock targets from ai_service.* to chat_agent_service.run in solune/backend/tests/unit/test_api_chat.py

**Checkpoint**: At this point, User Story 1 should be fully functional — users can send messages and the agent selects the correct tool automatically. Existing chat workflows (task creation, feature requests, status changes) work through the new agent.

---

## Phase 4: User Story 2 — Multi-Turn Conversation Memory (Priority: P1)

**Goal**: The agent remembers context from earlier messages in the same session. Users can provide project details once and the agent incorporates that context in subsequent responses without re-asking.

**Independent Test**: Send a sequence of messages in the same session (e.g., "My project uses React and Node.js" followed by "Create a feature for dark mode") and verify the agent's response references earlier context. New sessions start fresh with no prior state.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T020 [P] [US2] Write unit tests for AgentSession ↔ session_id mapping creation and lookup in solune/backend/tests/unit/test_chat_agent.py
- [ ] T021 [P] [US2] Write unit tests for session TTL eviction (sessions expire after configurable inactivity) in solune/backend/tests/unit/test_chat_agent.py
- [ ] T022 [P] [US2] Write unit tests for conversation summary injection into agent session state in solune/backend/tests/unit/test_chat_agent.py

### Implementation for User Story 2

- [ ] T023 [US2] Implement AgentSessionMapping (session_id → AgentSession) with create-on-first-message and last_accessed tracking in solune/backend/src/services/chat_agent.py
- [ ] T024 [US2] Implement TTL-based session eviction (default 1 hour inactivity) and max concurrent sessions enforcement in solune/backend/src/services/chat_agent.py
- [ ] T025 [US2] Implement conversation summary sync from SQLite chat history into AgentSession.state on each run() call in solune/backend/src/services/chat_agent.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work — the agent handles messages intelligently AND remembers context across turns within a session.

---

## Phase 5: User Story 3 — Transcript Analysis via Agent (Priority: P2)

**Goal**: Users upload meeting transcript files (.vtt, .srt) and the agent analyzes the content, extracts actionable requirements, identifies speakers, and produces a structured IssueRecommendation — driven by agent reasoning rather than a dedicated handler.

**Independent Test**: Upload a transcript file and verify the agent produces a complete IssueRecommendation with speaker attribution, user stories, and 5–8 functional requirements. Non-transcript files are handled gracefully.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T026 [P] [US3] Write unit tests for analyze_transcript tool with sample .vtt/.srt content in solune/backend/tests/unit/test_agent_tools.py

### Implementation for User Story 3

- [ ] T027 [US3] Implement analyze_transcript(transcript_content) @tool function returning ToolResult with action_type=ISSUE_CREATE and full IssueRecommendation data in solune/backend/src/services/agent_tools.py
- [ ] T028 [US3] Update file upload handling in solune/backend/src/api/chat.py to pass transcript content through ChatAgentService.run() instead of dedicated _handle_transcript handler

**Checkpoint**: At this point, transcript analysis works through the agent — upload a .vtt/.srt file and receive a structured issue recommendation.

---

## Phase 6: User Story 4 — Real-Time Streaming Responses (Priority: P2)

**Goal**: Users see agent responses appear progressively, token by token, via Server-Sent Events (SSE). The frontend renders partial content as it arrives, reducing perceived latency. Falls back gracefully to non-streaming when unavailable.

**Independent Test**: Send a message to the streaming endpoint and verify tokens arrive progressively via SSE events (token, tool_call, tool_result, done). Frontend renders streaming content and falls back to non-streaming on failure.

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T029 [P] [US4] Write unit tests for POST /chat/messages/stream SSE endpoint (event types: token, tool_call, tool_result, done, error) in solune/backend/tests/unit/test_api_chat.py
- [ ] T030 [P] [US4] Write unit tests for ChatAgentService.run_stream() async iterator in solune/backend/tests/unit/test_chat_agent.py

### Backend Implementation for User Story 4

- [ ] T031 [US4] Implement run_stream() method on ChatAgentService returning async iterator of SSE events in solune/backend/src/services/chat_agent.py
- [ ] T032 [US4] Add POST /chat/messages/stream endpoint using EventSourceResponse from sse-starlette in solune/backend/src/api/chat.py

### Frontend Implementation for User Story 4

- [ ] T033 [P] [US4] Add streaming API client using fetch() + ReadableStream for SSE consumption in solune/frontend/src/services/api.ts
- [ ] T034 [US4] Add progressive rendering of streaming messages in solune/frontend/src/components/chat/ChatInterface.tsx
- [ ] T035 [US4] Implement automatic fallback from streaming to non-streaming endpoint on connection failure in solune/frontend/src/services/api.ts

**Checkpoint**: At this point, streaming responses work end-to-end — tokens appear progressively in the browser with graceful fallback.

---

## Phase 7: User Story 5 — Signal Chat Integration with Agent (Priority: P3)

**Goal**: Signal messenger users interact with the same intelligent agent that powers web chat. Messages are processed via ChatAgentService.run() (non-streaming) ensuring consistent behavior across channels.

**Independent Test**: Send a Signal message and verify the agent processes it and returns a response. Confirm/reject flows work via keyword responses ("yes"/"no").

### Implementation for User Story 5

- [ ] T036 [US5] Replace direct ai_service.* calls with ChatAgentService.run() (non-streaming) in solune/backend/src/services/signal_chat.py
- [ ] T037 [US5] Update Signal chat tests to mock ChatAgentService.run() instead of individual ai_service methods in solune/backend/tests/unit/test_signal_chat.py

**Checkpoint**: Signal users experience the same agent-powered responses as web chat users.

---

## Phase 8: User Story 6 — Switchable AI Provider Backends (Priority: P3)

**Goal**: Administrators configure which AI backend powers the agent (GitHub Copilot or Azure OpenAI) via the AI_PROVIDER setting. Agent behavior is identical regardless of backend.

**Independent Test**: Run the same chat messages with AI_PROVIDER=copilot and AI_PROVIDER=azure_openai and verify both produce equivalent results with correct credential handling.

### Implementation for User Story 6

- [ ] T038 [US6] Implement GitHubCopilotAgent creation with per-run token passing (or bounded ephemeral agent pool) in solune/backend/src/services/agent_provider.py
- [ ] T039 [US6] Implement Agent creation with AzureOpenAIChatClient using existing AZURE_OPENAI_* env vars in solune/backend/src/services/agent_provider.py
- [ ] T040 [US6] Add unit tests verifying provider factory returns correct agent type for each AI_PROVIDER value in solune/backend/tests/unit/test_chat_agent.py

**Checkpoint**: Both AI providers work identically — switching AI_PROVIDER produces equivalent agent behavior.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Middleware, deprecation, and final validation across all user stories

- [ ] T041 [P] Create LoggingAgentMiddleware recording invocation timing and token counts in solune/backend/src/services/agent_middleware.py
- [ ] T042 [P] Create SecurityMiddleware with prompt injection detection and tool argument validation in solune/backend/src/services/agent_middleware.py
- [ ] T043 Add deprecation warnings (DeprecationWarning for v0.3.0 removal) to all public methods of AIAgentService except identify_target_task() in solune/backend/src/services/ai_agent.py
- [ ] T044 [P] Add deprecation warnings to CompletionProvider, CopilotCompletionProvider, AzureOpenAICompletionProvider in solune/backend/src/services/completion_providers.py
- [ ] T045 [P] Add deprecation warnings to prompt functions in solune/backend/src/prompts/task_generation.py, solune/backend/src/prompts/issue_generation.py, solune/backend/src/prompts/transcript_analysis.py
- [ ] T046 Design tool registration list to accommodate future MCP tool integration (v0.4.0 scope) in solune/backend/src/services/agent_tools.py
- [ ] T047 Run quickstart.md validation scenarios (all 6 test scenarios from quickstart.md)
- [ ] T048 Docker deployment verification — docker compose up --build, health check, end-to-end chat

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phases 3–8)**: All depend on Foundational phase completion
  - US1 (Phase 3) and US2 (Phase 4) are both P1 — implement sequentially (US1 first, US2 builds on it)
  - US3 (Phase 5) and US4 (Phase 6) are both P2 — can proceed in parallel after US1/US2
  - US5 (Phase 7) and US6 (Phase 8) are both P3 — can proceed in parallel after Foundational
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **User Story 2 (P1)**: Depends on US1 (extends ChatAgentService with session management) — but independently testable
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) — adds one tool + routing, independently testable
- **User Story 4 (P2)**: Depends on US1 (needs ChatAgentService.run() before adding run_stream()) — independently testable
- **User Story 5 (P3)**: Depends on US1 (needs ChatAgentService.run()) — independently testable
- **User Story 6 (P3)**: Can start after Foundational (Phase 2) — refines agent_provider.py, independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Tools/Models before services
- Services before endpoints/API
- Backend before frontend (for US4)
- Core implementation before integration

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T001, T002)
- All Foundational tasks marked [P] can run in parallel (T003, T004, T005 — all three target different files with no dependencies)
- All tool implementation tasks within US1 (T011–T015) can run in parallel (different @tool functions in same file)
- All test tasks within a story marked [P] can run in parallel
- US3 and US4 can run in parallel (different tools, different endpoints)
- US5 and US6 can run in parallel (different files, no shared state)
- All Polish tasks marked [P] can run in parallel (T041/T042 middleware; T044/T045 deprecation)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit tests for create_task_proposal tool in tests/unit/test_agent_tools.py"
Task: "Unit tests for create_issue_recommendation tool in tests/unit/test_agent_tools.py"
Task: "Unit tests for update_task_status tool in tests/unit/test_agent_tools.py"
Task: "Unit tests for ask_clarifying_question tool in tests/unit/test_agent_tools.py"
Task: "Unit tests for ChatAgentService.run() in tests/unit/test_chat_agent.py"

# Launch all tool implementations for User Story 1 together:
Task: "Implement create_task_proposal @tool in src/services/agent_tools.py"
Task: "Implement create_issue_recommendation @tool in src/services/agent_tools.py"
Task: "Implement update_task_status @tool in src/services/agent_tools.py"
Task: "Implement ask_clarifying_question @tool in src/services/agent_tools.py"
Task: "Implement get_project_context and get_pipeline_list @tool in src/services/agent_tools.py"
```

## Parallel Example: User Story 4 (Frontend + Backend)

```bash
# After backend streaming is complete (T031, T032), frontend tasks can run in parallel:
Task: "Add streaming API client in frontend/src/services/api.ts"
Task: "Add progressive rendering in frontend/src/components/chat/ChatInterface.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T005)
3. Complete Phase 3: User Story 1 (T006–T019)
4. **STOP and VALIDATE**: Test User Story 1 independently — send chat messages, verify agent selects correct tools
5. Deploy/demo if ready — the core value proposition is working

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test multi-turn memory → Deploy/Demo
4. Add User Story 3 → Test transcript analysis → Deploy/Demo
5. Add User Story 4 → Test streaming → Deploy/Demo (significant UX improvement)
6. Add User Story 5 → Test Signal integration → Deploy/Demo
7. Add User Story 6 → Test provider switching → Deploy/Demo
8. Complete Polish → Full v0.2.0 release

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 → User Story 2 (sequential, P1 stories)
   - Developer B: User Story 3 (P2, independent after Foundational)
   - Developer C: User Story 6 (P3, independent after Foundational)
3. After US1 completes:
   - Developer B: User Story 4 (depends on US1 ChatAgentService)
   - Developer C: User Story 5 (depends on US1 ChatAgentService)
4. All: Polish phase

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- ChatMessage schema is UNCHANGED — all new behavior is internal to agent service layer
- Deprecate, don't delete — old service layer gets warnings, removed in v0.3.0
- ai_enhance=False bypasses agent entirely (preserves v0.1.x behavior)
- Tool registration designed for future MCP tool integration (v0.4.0)
- Runtime context (project_id, github_token, session_id) injected via FunctionInvocationContext.kwargs — never exposed to LLM
