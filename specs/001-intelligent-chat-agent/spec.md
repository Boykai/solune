# Feature Specification: Intelligent Chat Agent (Microsoft Agent Framework)

**Feature Branch**: `001-intelligent-chat-agent`  
**Created**: 2026-03-30  
**Status**: Draft  
**Input**: User description: "v0.2.0 — Intelligent Chat Agent (Microsoft Agent Framework)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Natural Conversation with Intelligent Tool Selection (Priority: P1)

A user sends a chat message describing what they need — a feature request, a task, a status update, or a question. Instead of the system following a rigid priority cascade, the intelligent agent understands the user's intent through reasoning and selects the appropriate action (tool) automatically. The user experience feels like talking to a knowledgeable project assistant that understands context and chooses the right response.

**Why this priority**: This is the core value proposition. Replacing the hardcoded priority dispatch with agent-driven reasoning enables more natural interactions, better intent understanding, and the ability to handle ambiguous requests that previously fell through the cascade. Without this, the entire migration has no purpose.

**Independent Test**: Can be fully tested by sending various chat messages (feature requests, task descriptions, status updates) and verifying the agent selects the correct tool and produces the expected structured output. Delivers immediate value by improving chat accuracy and removing rigid dispatch ordering.

**Acceptance Scenarios**:

1. **Given** a user is in an active chat session, **When** the user describes a feature request (e.g., "I want a dark mode toggle in settings"), **Then** the agent recognizes the intent and produces a structured issue recommendation with title, user story, functional requirements, and metadata — matching the existing `IssueRecommendation` schema.
2. **Given** a user is in an active chat session, **When** the user asks to create a task (e.g., "Add unit tests for the login module"), **Then** the agent produces a task proposal with title and description — matching the existing `AITaskProposal` schema.
3. **Given** a user is in an active chat session, **When** the user requests a status change (e.g., "Move the auth task to in progress"), **Then** the agent identifies the target task and updates its status.
4. **Given** a user is in an active chat session, **When** the user sends an ambiguous message, **Then** the agent asks 2–3 clarifying questions before taking action, rather than guessing incorrectly.
5. **Given** a user is in an active chat session with `ai_enhance=False`, **When** the user creates a task, **Then** the system bypasses the agent and uses simple title-only generation (preserving current behavior).

---

### User Story 2 - Multi-Turn Conversation Memory (Priority: P1)

A user has a multi-turn conversation where earlier messages provide context for later ones. The agent remembers what was said previously in the session — for example, if the user mentions "My project uses React and Node.js" early on, the agent incorporates that context when generating recommendations or tasks later in the conversation.

**Why this priority**: Multi-turn memory is essential for the agent to be useful. Without session continuity, each message is treated in isolation, leading to repetitive questions and loss of context. This is tied to P1 because it fundamentally determines whether the agent feels intelligent or stateless.

**Independent Test**: Can be tested by sending a sequence of messages in the same session and verifying that the agent's responses reference earlier context. Delivers value by eliminating repetitive questions and producing context-aware outputs.

**Acceptance Scenarios**:

1. **Given** a user has provided project context in earlier messages (e.g., "We use Python and FastAPI"), **When** the user later asks to create a feature, **Then** the agent's recommendation includes technology-appropriate details without re-asking about the stack.
2. **Given** a user is mid-conversation about a feature, **When** the user provides additional details in a follow-up message, **Then** the agent incorporates the new information into its existing understanding.
3. **Given** a user starts a new session, **When** the user sends a message, **Then** the agent starts fresh with no prior context (session isolation).

---

### User Story 3 - Transcript Analysis via Agent (Priority: P2)

A user uploads a meeting transcript file (.vtt, .srt). The agent analyzes the transcript content, extracts actionable requirements, identifies speakers and their contributions, and produces a structured issue recommendation — the same output as the current transcript analysis flow, but driven by the agent's reasoning rather than a dedicated handler.

**Why this priority**: Transcript analysis is a differentiated feature but not the primary interaction path. Most users will interact via text chat first. This is P2 because it extends the agent's capabilities to file-based inputs while maintaining the existing user-facing behavior.

**Independent Test**: Can be tested by uploading a transcript file and verifying the agent produces a complete issue recommendation with speaker attribution, user stories, and functional requirements. Delivers standalone value for meeting-driven workflows.

**Acceptance Scenarios**:

1. **Given** a user uploads a .vtt or .srt transcript file, **When** the agent processes the file content, **Then** it produces an `IssueRecommendation` with extracted speakers, features, user stories, and 5–8 functional requirements.
2. **Given** a transcript contains conflicting perspectives from multiple speakers, **When** the agent analyzes it, **Then** it synthesizes a balanced recommendation noting the different viewpoints.
3. **Given** a user uploads a non-transcript file, **When** the agent processes the message, **Then** it handles the file appropriately without treating it as a transcript.

---

### User Story 4 - Real-Time Streaming Responses (Priority: P2)

A user sends a message and sees the agent's response appear progressively, token by token, rather than waiting for the entire response to be generated. This provides immediate feedback that the system is working and reduces perceived latency.

**Why this priority**: Streaming significantly improves the user experience for longer responses (like detailed issue recommendations) but is not required for core functionality. The existing non-streaming endpoint continues to work. This is P2 because it's a UX enhancement that can be added alongside the core agent migration.

**Independent Test**: Can be tested by sending a message to the streaming endpoint and verifying that tokens arrive progressively via Server-Sent Events (SSE). The frontend gracefully renders partial content as it arrives. Delivers value through improved perceived responsiveness.

**Acceptance Scenarios**:

1. **Given** a user sends a message via the streaming endpoint, **When** the agent generates a response, **Then** tokens are delivered progressively via SSE and the user sees the response being typed out in real time.
2. **Given** a user sends a message, **When** the streaming endpoint is unavailable, **Then** the frontend automatically falls back to the non-streaming endpoint and displays the complete response.
3. **Given** the agent invokes a tool during streaming, **When** the tool returns structured data, **Then** the structured output (e.g., task proposal with confirm/reject buttons) is rendered correctly after the stream completes.

---

### User Story 5 - Signal Chat Integration with Agent (Priority: P3)

A user interacts with Solune via Signal messenger. Their text messages are processed by the same intelligent agent that powers the web chat, ensuring consistent behavior across channels. The Signal integration uses non-streaming responses since Signal does not support progressive delivery.

**Why this priority**: Signal is a secondary channel. The core agent behavior must work in web chat first. This is P3 because it extends agent capabilities to an existing integration point without introducing new user-facing features.

**Independent Test**: Can be tested by sending a Signal message and verifying the agent processes it and returns a response via Signal. Confirm/reject flows work via keyword responses ("yes"/"no"). Delivers value by ensuring consistent AI behavior across all channels.

**Acceptance Scenarios**:

1. **Given** a user sends a text message via Signal, **When** the agent processes it, **Then** it produces the same quality response as the web chat (non-streaming).
2. **Given** a user confirms a proposal via Signal by sending "yes", **When** the system processes the confirmation, **Then** the proposal is confirmed and a GitHub issue is created.

---

### User Story 6 - Switchable AI Provider Backends (Priority: P3)

An administrator configures which AI provider backend powers the agent — GitHub Copilot (using the user's OAuth token) or Azure OpenAI (using service-level API keys). The agent behavior remains identical regardless of which backend is selected, ensuring consistent results across deployment configurations.

**Why this priority**: Provider flexibility is important for enterprise deployments and cost management but does not affect end-user features. This is P3 because the existing provider abstraction already supports switching, and this story ensures the new agent layer preserves that capability.

**Independent Test**: Can be tested by running the same set of chat messages with `AI_PROVIDER=copilot` and `AI_PROVIDER=azure_openai` and verifying that both produce equivalent results. Delivers value for deployment flexibility.

**Acceptance Scenarios**:

1. **Given** the system is configured with `AI_PROVIDER=copilot`, **When** a user sends a chat message, **Then** the agent uses the GitHub Copilot backend with the user's OAuth token.
2. **Given** the system is configured with `AI_PROVIDER=azure_openai`, **When** a user sends a chat message, **Then** the agent uses the Azure OpenAI backend with service-level credentials and produces equivalent results.

---

### Edge Cases

- What happens when the agent fails to select any tool? The system returns a helpful fallback message rather than an error, equivalent to the current echo behavior.
- What happens when a tool invocation fails (e.g., GitHub API is down)? The agent reports the failure gracefully and suggests the user try again.
- What happens when the user sends an extremely long message (up to 100k characters)? The system respects existing input limits and the agent handles large inputs without crashing or timing out.
- What happens when the Copilot token expires mid-conversation? The system detects the authentication failure and prompts the user to re-authenticate.
- What happens when multiple tools could apply (e.g., a feature request that also implies a task)? The agent reasons about the best fit based on its instructions, preferring the higher-value action (issue recommendation over simple task creation).
- What happens during the deprecation period when old endpoints are still called? Deprecated service methods emit warnings but continue to function until removal in v0.3.0.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST replace the hardcoded priority dispatch cascade in the chat API with a single agent invocation that selects the appropriate tool based on reasoning.
- **FR-002**: System MUST provide function tools that map to all existing AI actions: task proposal creation, issue recommendation generation, status change requests, and transcript analysis.
- **FR-003**: System MUST introduce new function tools for clarifying questions and project context retrieval, enabling the agent to gather information before acting.
- **FR-004**: System MUST support multi-turn conversation memory within a session, allowing the agent to reference earlier messages when responding.
- **FR-005**: System MUST maintain the existing `ChatMessage` schema (message_id, session_id, sender_type, content, action_type, action_data, timestamp) so the frontend and API contract remain unchanged.
- **FR-006**: System MUST support both GitHub Copilot and Azure OpenAI as agent backends, selectable via the existing `AI_PROVIDER` configuration.
- **FR-007**: System MUST provide a streaming endpoint that delivers agent responses progressively via Server-Sent Events (SSE).
- **FR-008**: System MUST preserve the `ai_enhance=False` bypass behavior, using simple title-only generation without invoking the agent.
- **FR-009**: System MUST convert tool outputs (structured dictionaries) into `action_type` and `action_data` fields on `ChatMessage`, preserving the existing confirm/reject proposal flow.
- **FR-010**: System MUST update the Signal chat integration to use the new agent service for message processing (non-streaming).
- **FR-011**: System MUST include logging middleware that records timing and token usage for each agent invocation.
- **FR-012**: System MUST include security middleware that validates tool arguments and detects prompt injection attempts.
- **FR-013**: System MUST deprecate (not delete) the existing `AIAgentService`, `CompletionProvider` implementations, and prompt modules, adding deprecation warnings for removal in a future version.
- **FR-014**: System MUST keep the existing `identify_target_task()` method available, as it is reused by the task status update tool.
- **FR-015**: System MUST provide a single comprehensive system instruction that replaces the separate prompt modules (task generation, issue generation, transcript analysis) while preserving their behavior.
- **FR-016**: System MUST implement an agent clarifying-questions policy where the agent asks 2–3 targeted questions before taking action on ambiguous requests.
- **FR-017**: System MUST inject runtime context (project ID, GitHub token, session ID) into tool invocations without exposing these parameters to the LLM schema.
- **FR-018**: System MUST keep Solune's SQLite database as the source of truth for conversation history, syncing only summaries into the agent session state.
- **FR-019**: System MUST support the existing `/agent` meta-command handling separately from agent tool dispatch.
- **FR-020**: System MUST ensure the frontend streaming capability falls back gracefully to the non-streaming endpoint when streaming is unavailable or fails.
- **FR-021**: System MUST design tool registration to accommodate future MCP (Model Context Protocol) tool integration.

### Key Entities

- **Agent**: The intelligent assistant that processes user messages, reasons about intent, and invokes tools. Replaces the priority dispatch logic. Has a system instruction, a set of registered tools, and middleware.
- **Agent Session**: A stateful conversation context mapped to a Solune session ID. Maintains multi-turn memory for the agent while the SQLite database remains the canonical conversation store.
- **Function Tool**: A discrete action the agent can invoke (e.g., create task proposal, generate issue recommendation). Each tool has a typed input schema visible to the LLM and receives runtime context via invocation kwargs.
- **Agent Provider**: A factory that creates the appropriate agent instance based on configuration — either using GitHub Copilot credentials or Azure OpenAI service keys.
- **Middleware**: Processing layers that wrap agent invocations for cross-cutting concerns like logging (timing, token counts) and security (prompt injection detection, argument validation).
- **System Instruction**: A comprehensive prompt that guides the agent's behavior, replacing the individual prompt modules. Includes tool usage guidance, clarifying-question policy, and dynamic project context.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete all existing chat workflows (feature requests, task creation, status changes, transcript analysis) through the new agent without any loss of functionality.
- **SC-002**: The agent correctly selects the appropriate tool for at least 95% of unambiguous user requests, matching or exceeding the accuracy of the current priority dispatch.
- **SC-003**: Multi-turn conversations maintain context across at least 10 consecutive messages within a session.
- **SC-004**: Streaming responses begin delivering tokens to the user within 2 seconds of submitting a message, reducing perceived wait time compared to the current full-response delivery.
- **SC-005**: All existing unit tests continue to pass after migration, with updated mock targets reflecting the new service layer.
- **SC-006**: The system operates identically regardless of whether the GitHub Copilot or Azure OpenAI backend is selected, producing equivalent outputs for the same inputs.
- **SC-007**: Deprecated service methods emit warnings but remain functional, ensuring backward compatibility during the transition period.
- **SC-008**: The confirm/reject proposal flow (create proposal → user confirms → GitHub issue created) works end-to-end through the new agent, with no changes to the frontend interaction pattern.
- **SC-009**: Signal chat users experience the same quality of responses as web chat users, with consistent tool selection and output formatting.
- **SC-010**: The Docker-based deployment (`docker compose up --build`) starts successfully and passes end-to-end health checks with the new agent service.

### Assumptions

- The Microsoft Agent Framework packages (`agent-framework-core`, `agent-framework-github-copilot`, `agent-framework-azure-ai`) are available on PyPI and compatible with Python 3.12+.
- The `GitHubCopilotAgent` from the Agent Framework supports per-run token passing or can be configured with a bounded ephemeral agent pool similar to the current `CopilotClientPool`.
- The Agent Framework's `@tool` decorator supports async Python functions.
- SSE (Server-Sent Events) can be delivered through the existing FastAPI/Uvicorn stack using `EventSourceResponse` or equivalent.
- The existing SQLite storage layer and in-memory caching patterns are retained without modification.
- The frontend React application can consume SSE streams using the browser's native `ReadableStream` API or `EventSource`.
- The `ChatMessage` schema additions (if any, such as new `ActionType` values) are backward-compatible and do not require frontend schema changes.

### Dependencies

- Microsoft Agent Framework packages availability and API stability.
- Existing GitHub Copilot SDK functionality being preserved by the `agent-framework-github-copilot` wrapper.
- The current test suite remaining green as a baseline before migration begins.

### Out of Scope

- MCP (Model Context Protocol) tool integration — planned for v0.4.0.
- Replacing the SQLite storage layer — conversation history remains in Solune's database.
- Deleting deprecated service layers — removal is planned for v0.3.0.
- Adding new user-facing features beyond what exists today (the migration preserves existing functionality with improved intelligence).
- Per-user token management changes beyond what is needed for agent framework compatibility.
