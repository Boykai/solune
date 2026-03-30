# Research: Intelligent Chat Agent (Microsoft Agent Framework)

**Feature**: 001-intelligent-chat-agent | **Date**: 2026-03-30

## Research Summary

This document captures all technology decisions, alternatives evaluated, and best practices identified during Phase 0 of the implementation plan. Every NEEDS CLARIFICATION item from the Technical Context has been resolved.

---

## Decision 1: Agent Framework Package Selection

**Decision**: Use `agent-framework-core`, `agent-framework-azure-ai`, and `agent-framework-github-copilot` (preview releases via `--pre` flag).

**Rationale**: The Microsoft Agent Framework (MAF) provides a unified Python SDK for building AI agents with built-in support for:
- Function tools via `@tool` decorator
- Session management via `AgentSession`
- Middleware pipeline for cross-cutting concerns
- Multiple LLM backends (OpenAI, Azure OpenAI, GitHub Copilot)
- Streaming responses via async iterators
- MCP tool integration (future v0.4.0 scope)

This directly maps to all requirements in the spec (FR-001 through FR-021) and eliminates the need for custom orchestration code.

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|-----------------|
| LangChain | Heavier dependency, over-engineered for single-agent use; MAF is Microsoft-native and aligns with existing Copilot SDK usage |
| Semantic Kernel | MAF is the successor; SK is entering maintenance mode for agentic patterns |
| Custom orchestration | Would replicate what MAF provides out-of-box (tool dispatch, sessions, middleware); violates Simplicity principle |
| AutoGen | Focused on multi-agent chat; overkill for single-agent with tools pattern needed here |

**Package Versions**: Install with `--pre` flag as MAF is in Release Candidate status. Pin to `>=1.0.0b` to track RC releases.

---

## Decision 2: GitHub Copilot Provider Integration

**Decision**: Use `agent-framework-github-copilot` package which wraps the existing `copilot-sdk` as a MAF-compatible provider.

**Rationale**: The `agent-framework-github-copilot` package provides `CopilotProvider` (or `GitHubCopilotAgent`) that integrates Copilot's OAuth-based model access into the MAF agent pipeline. This replaces the current `CopilotCompletionProvider` + `CopilotClientPool` pattern with a framework-native abstraction.

**Per-User Token Handling**: The current `CopilotClientPool` manages per-user OAuth tokens with bounded concurrency. The MAF Copilot provider supports per-run token passing via runtime kwargs or agent configuration. If per-run token injection is not natively supported, use a bounded ephemeral agent pool pattern (create agent instances per-request with user's token, bounded by a semaphore to limit concurrency).

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|-----------------|
| Direct copilot-sdk calls | Bypasses MAF's tool/session/middleware infrastructure; defeats the purpose of migration |
| Custom CopilotChatClient wrapper | Unnecessary since `agent-framework-github-copilot` already provides this |

---

## Decision 3: Azure OpenAI Provider Integration

**Decision**: Use `agent-framework-azure-ai` package with `AzureOpenAIChatClient` for Azure OpenAI backend.

**Rationale**: Provides a drop-in replacement for the current `AzureOpenAICompletionProvider` within the MAF pipeline. Supports the same deployment configuration (endpoint, API key, deployment name) but gains tool calling, sessions, and middleware for free.

**Configuration**: Reuse existing `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT` environment variables. The `AzureOpenAIChatClient` accepts these directly.

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|-----------------|
| Raw `openai` SDK | Would require manual tool dispatch and session management; loses MAF benefits |
| Azure AI Inference SDK | Lower-level than MAF; no built-in agent orchestration |

---

## Decision 4: Streaming Implementation (SSE)

**Decision**: Use `sse-starlette` library with FastAPI for Server-Sent Events endpoint at `POST /api/v1/chat/messages/stream`.

**Rationale**: The `sse-starlette` package provides `EventSourceResponse` which integrates seamlessly with FastAPI's async capabilities. MAF's `agent.run(stream=True)` returns an async iterator that yields response chunks, which maps directly to SSE events. This is the standard approach for streaming in FastAPI applications.

**Frontend Consumption**: Use the browser's native `fetch()` API with `ReadableStream` to consume SSE. This avoids adding new npm dependencies. The `EventSource` API is an alternative but doesn't support POST requests; `fetch` with stream processing is more flexible.

**Fallback Strategy**: Frontend attempts streaming endpoint first. On connection failure (network error, 404, 5xx), it automatically falls back to the existing non-streaming `POST /api/v1/chat/messages` endpoint. This is implemented as a try/catch in the API client.

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|-----------------|
| WebSocket | Overkill for unidirectional streaming; SSE is simpler and sufficient |
| Long polling | Higher latency, more complex client-side logic |
| Native Starlette StreamingResponse | Lacks SSE event formatting (event/data/id fields) |

---

## Decision 5: Tool Design Pattern

**Decision**: Each tool is a standalone async function decorated with `@tool`, receiving runtime context via `FunctionInvocationContext.kwargs`.

**Rationale**: MAF's `@tool` decorator exposes function parameters to the LLM schema while `kwargs` pass runtime context (project_id, github_token, session_id) invisibly. This separation ensures:
- LLM sees only semantically meaningful parameters (title, description, etc.)
- Security-sensitive tokens are never included in the LLM context
- Tools are testable with mocked context objects

**Tool Registration for Future MCP**: Tools are registered as a list passed to the Agent constructor. This list can be extended with MCP-sourced tools in v0.4.0 without changing the registration pattern (FR-021).

**Tool-to-ActionType Mapping**:
| Tool | Returns | action_type | action_data |
|------|---------|-------------|-------------|
| `create_task_proposal` | `AITaskProposal` dict | `TASK_CREATE` | `{proposal_id, title, description}` |
| `create_issue_recommendation` | `IssueRecommendation` dict | `ISSUE_CREATE` | `{recommendation_id, title, user_story, ...}` |
| `update_task_status` | `StatusChangeProposal` dict | `STATUS_UPDATE` | `{task_id, target_status, confidence}` |
| `analyze_transcript` | `IssueRecommendation` dict | `ISSUE_CREATE` | Same as issue recommendation |
| `ask_clarifying_question` | `str` (question text) | `None` | `None` (plain text response) |
| `get_project_context` | `dict` (project info) | `None` | `None` (informational) |
| `get_pipeline_list` | `list[dict]` | `None` | `None` (informational) |

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|-----------------|
| Class-based tools | More boilerplate; MAF's function-based `@tool` is simpler and aligns with framework idioms |
| Embedding context in tool schema | Exposes tokens to LLM; security risk |

---

## Decision 6: Session Management Strategy

**Decision**: Map Solune's `session_id` (UUID) to MAF `AgentSession` instances. SQLite remains the canonical conversation store; `AgentSession.state` holds only a summary of recent context for the LLM.

**Rationale**: This preserves the existing persistence layer (FR-018) while giving the agent multi-turn memory. On each `run()` call:
1. Look up or create `AgentSession` for the Solune `session_id`
2. Inject recent conversation summary from SQLite into session state
3. Agent uses session state for context-aware reasoning
4. Persist the agent's response back to SQLite

**Session Lifecycle**: Sessions are cached in-memory (dict keyed by session_id). Expired sessions are cleaned up on access (TTL-based eviction, matching existing `_messages` cache pattern in `chat.py`).

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|-----------------|
| Replace SQLite with AgentSession as store | Violates FR-018; loses existing persistence, pagination, and backup capabilities |
| No session state (re-inject full history) | Token-expensive for long conversations; AgentSession.state allows efficient summaries |
| External session store (Redis) | Over-engineered for current single-tenant deployment |

---

## Decision 7: System Instruction Consolidation

**Decision**: Create a single comprehensive system instruction in `src/prompts/agent_instructions.py` that replaces the three separate prompt modules.

**Rationale**: The agent needs unified guidance covering all tools, clarifying-question policy, difficulty assessment, and dynamic project context injection. Separate prompts for each action type are no longer needed because the agent's tool selection replaces the priority cascade. The unified prompt:
- Describes all available tools and when to use each
- Defines the clarifying-questions policy (2–3 questions for ambiguous requests)
- Includes difficulty/complexity assessment guidance
- Supports dynamic project context injection via template variables
- Preserves the same output schemas expected by the frontend

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|-----------------|
| Keep separate prompts, compose at runtime | Increases prompt token usage; agent needs holistic understanding of all tools |
| Minimal prompt (let tools self-describe) | Insufficient for nuanced behavior like clarifying-question policy and priority reasoning |

---

## Decision 8: Deprecation Strategy

**Decision**: Add `warnings.warn(DeprecationWarning)` to all public methods of `AIAgentService`, `CompletionProvider` subclasses, and old prompt module functions. Keep `identify_target_task()` on `AIAgentService` without deprecation warning (reused by `update_task_status` tool).

**Rationale**: This follows the spec's "deprecate, don't delete" policy (FR-013, FR-014). Old code continues to function during the transition period. Removal is deferred to v0.3.0. The deprecation warnings alert developers and appear in logs, creating urgency without breaking existing integrations.

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|-----------------|
| Delete immediately | Breaks any external integrations; violates spec decision |
| No warnings (silent deprecation) | No signal to migrate; developers discover breakage at removal time |

---

## Decision 9: Middleware Architecture

**Decision**: Implement two middleware classes following MAF's middleware pattern:
1. `LoggingAgentMiddleware` — records invocation timing, token counts, tool calls
2. `SecurityMiddleware` — detects prompt injection patterns, validates tool arguments

**Rationale**: MAF supports middleware as async callables that wrap agent execution. This is the idiomatic way to add cross-cutting concerns (FR-011, FR-012). The middleware runs on every agent invocation, providing consistent observability and security regardless of which tool is selected.

**Prompt Injection Detection**: Use pattern matching for known injection techniques (instruction overrides, role-play attacks, delimiter injection). This is a defense-in-depth layer — the agent's system instruction already constrains behavior, and tool argument validation prevents malicious payloads from reaching business logic.

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|-----------------|
| FastAPI middleware | Too broad (applies to all HTTP requests, not agent-specific); can't access agent internals |
| Decorator pattern | Less composable than MAF's native middleware pipeline |

---

## Decision 10: Frontend Streaming Architecture

**Decision**: Update `chatApi.sendMessage()` in `api.ts` to attempt the streaming endpoint first, falling back to non-streaming on failure. Use `fetch()` with `ReadableStream` for SSE consumption. Progressive rendering in `MessageBubble` via incremental state updates.

**Rationale**: This is additive — the existing non-streaming path remains fully functional. The streaming path enhances UX for longer responses (issue recommendations, detailed task proposals). No new npm dependencies are needed since `fetch` and `ReadableStream` are browser-native APIs.

**Rendering Strategy**: As SSE chunks arrive, append to message content and re-render. When a tool invocation result arrives (structured JSON), switch to the appropriate preview component (TaskPreview, IssueRecommendationPreview). This preserves the existing component architecture.

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|-----------------|
| `EventSource` API | Doesn't support POST requests; would require endpoint redesign |
| New npm SSE library | Unnecessary since fetch + ReadableStream suffices |
| WebSocket | Overkill for unidirectional streaming |
