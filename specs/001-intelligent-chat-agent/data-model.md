# Data Model: Intelligent Chat Agent (Microsoft Agent Framework)

**Feature**: 001-intelligent-chat-agent | **Date**: 2026-03-30

## Overview

This document defines the entities, relationships, and schemas introduced or modified by the Intelligent Chat Agent feature. The core principle is **schema stability** — the existing `ChatMessage`, `AITaskProposal`, and `IssueRecommendation` models are **unchanged**. New entities are internal to the agent service layer and do not affect the API contract or frontend.

---

## Existing Entities (Unchanged)

These entities are already defined in the codebase and remain unmodified. They are documented here for reference because agent tools produce outputs that map to them.

### ChatMessage

**Location**: `src/models/chat.py`

| Field | Type | Description |
|-------|------|-------------|
| `message_id` | `UUID` | Unique message identifier |
| `session_id` | `UUID` | Parent chat session |
| `sender_type` | `SenderType` | `"user"` \| `"assistant"` \| `"system"` |
| `content` | `str` | Message text (max 100,000 chars) |
| `action_type` | `ActionType \| None` | `"task_create"` \| `"status_update"` \| `"project_select"` \| `"issue_create"` |
| `action_data` | `dict[str, Any] \| None` | Action-specific structured payload |
| `timestamp` | `datetime` | Message creation time |

### ChatMessageRequest

**Location**: `src/models/chat.py`

| Field | Type | Description |
|-------|------|-------------|
| `content` | `str` | User message text |
| `ai_enhance` | `bool` | AI description rewrite flag (default: `True`) |
| `file_urls` | `list[str]` | Uploaded file URLs |
| `pipeline_id` | `str \| None` | Optional pipeline override |

### AITaskProposal

**Location**: `src/models/recommendation.py`

| Field | Type | Description |
|-------|------|-------------|
| `proposal_id` | `str` | Unique proposal identifier |
| `session_id` | `str` | Parent session |
| `title` | `str` | Proposed task title |
| `description` | `str` | Proposed task description (markdown) |
| `status` | `ProposalStatus` | `"pending"` \| `"confirmed"` \| `"rejected"` |
| `original_input` | `str` | User's original message |
| `created_at` | `datetime` | Creation timestamp |

### IssueRecommendation

**Location**: `src/models/recommendation.py`

| Field | Type | Description |
|-------|------|-------------|
| `recommendation_id` | `str` | Unique recommendation identifier |
| `session_id` | `str` | Parent session |
| `title` | `str` | Issue title (max 256 chars) |
| `user_story` | `str` | "As a [user], I want [goal] so that [benefit]" |
| `ui_ux_description` | `str` | Design guidance |
| `functional_requirements` | `list[str]` | 5–8 MUST/SHOULD statements |
| `technical_notes` | `str` | Implementation guidance |
| `metadata` | `IssueMetadata` | `{priority, size, estimate_hours, labels, ...}` |
| `status` | `RecommendationStatus` | `"pending"` \| `"confirmed"` \| `"rejected"` |
| `original_input` | `str` | User's original message |
| `original_context` | `str \| None` | Full transcript (for transcript analysis) |
| `created_at` | `datetime` | Creation timestamp |

### SenderType (StrEnum)

`USER` = `"user"` | `ASSISTANT` = `"assistant"` | `SYSTEM` = `"system"`

### ActionType (StrEnum)

`TASK_CREATE` = `"task_create"` | `STATUS_UPDATE` = `"status_update"` | `PROJECT_SELECT` = `"project_select"` | `ISSUE_CREATE` = `"issue_create"`

---

## New Entities (Agent Layer)

These entities are internal to the agent service layer. They do not appear in the REST API or database schema.

### AgentSessionMapping

**Location**: `src/services/chat_agent.py` (in-memory dict)

Maps Solune session IDs to MAF AgentSession instances for multi-turn memory.

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `UUID` | Solune chat session identifier (key) |
| `agent_session` | `AgentSession` | MAF session with conversation state |
| `created_at` | `datetime` | When the mapping was created |
| `last_accessed` | `datetime` | Last access time (for TTL eviction) |

**Lifecycle**:
- Created on first message in a session
- Updated on every `run()` call
- Evicted after configurable TTL (default: 1 hour of inactivity)

### ToolResult

**Location**: `src/services/agent_tools.py` (TypedDict or dataclass)

Standardized return type from all agent tools, enabling consistent conversion to `ChatMessage`.

| Field | Type | Description |
|-------|------|-------------|
| `content` | `str` | Human-readable response text |
| `action_type` | `ActionType \| None` | Maps to ChatMessage.action_type |
| `action_data` | `dict[str, Any] \| None` | Maps to ChatMessage.action_data |

**Mapping Table**:

| Tool Function | action_type | action_data contents |
|---------------|-------------|---------------------|
| `create_task_proposal(title, description)` | `TASK_CREATE` | `AITaskProposal` serialized dict |
| `create_issue_recommendation(title, user_story, ...)` | `ISSUE_CREATE` | `IssueRecommendation` serialized dict |
| `update_task_status(task_reference, target_status)` | `STATUS_UPDATE` | `{task_id, task_title, target_status, confidence}` |
| `analyze_transcript(transcript_content)` | `ISSUE_CREATE` | `IssueRecommendation` serialized dict |
| `ask_clarifying_question(question)` | `None` | `None` |
| `get_project_context()` | `None` | `None` |
| `get_pipeline_list()` | `None` | `None` |

### AgentProviderConfig

**Location**: `src/config.py` (added to existing Settings class)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `agent_session_ttl_seconds` | `int` | `3600` | TTL for agent session cache |
| `agent_max_concurrent_sessions` | `int` | `100` | Max concurrent agent sessions |
| `agent_streaming_enabled` | `bool` | `True` | Enable/disable streaming endpoint |

These extend the existing `Settings` class which reads from environment variables.

---

## Relationships

```text
┌─────────────────┐     1:1      ┌──────────────────────┐
│  Solune Session  │─────────────│  AgentSessionMapping  │
│  (UUID)          │             │  (in-memory)          │
└────────┬────────┘             └──────────┬───────────┘
         │                                  │
         │ 1:N                              │ 1:1
         ▼                                  ▼
┌─────────────────┐             ┌──────────────────────┐
│  ChatMessage     │             │  MAF AgentSession    │
│  (SQLite)        │             │  (in-memory state)   │
└────────┬────────┘             └──────────────────────┘
         │
         │ 0..1:1
         ▼
┌─────────────────────┐
│  AITaskProposal     │  ◄── Created by create_task_proposal tool
│  -OR-               │
│  IssueRecommendation│  ◄── Created by create_issue_recommendation / analyze_transcript tools
│  (SQLite)           │
└─────────────────────┘
```

### Key Relationships

1. **Session → AgentSession** (1:1): Each Solune session maps to exactly one MAF AgentSession. Session isolation is maintained — no cross-session state leakage.

2. **Session → ChatMessages** (1:N): Unchanged. Messages are persisted to SQLite. The agent produces messages that are persisted like any other assistant message.

3. **ChatMessage → Proposal/Recommendation** (0..1:1): Unchanged. When a tool produces an `action_type`, the corresponding proposal or recommendation is created and persisted. The frontend's confirm/reject flow works identically.

4. **Agent → Tools** (1:N): A single Agent instance has N registered tools. Tool selection is done by the LLM at runtime.

5. **Agent → Middleware** (1:N): Middleware wraps each agent invocation. Order: SecurityMiddleware → LoggingMiddleware → Agent execution.

---

## State Transitions

### Agent Session State

```text
[No Session] ──── first message ────► [Active]
     │                                    │
     │                                    │ TTL expires (no messages for 1hr)
     │                                    ▼
     │                              [Evicted]
     │                                    │
     │                                    │ next message (re-creates)
     └────────────────────────────────────┘
```

### Proposal/Recommendation Status (Unchanged)

```text
[pending] ──── confirm ────► [confirmed] ──── GitHub issue created
    │
    └───── reject/cancel ──► [rejected]
```

---

## Validation Rules

### From Existing Models (Unchanged)

- `ChatMessage.content`: max 100,000 characters
- `IssueRecommendation.title`: max 256 characters
- `IssueRecommendation.functional_requirements`: 5–8 items expected
- `AITaskProposal.title`: required, non-empty
- File uploads: 10 MB max per file, 5 files per message, blocked extensions (.exe, .sh, .bat, .cmd, .js, .py, .rb)

### New Validation (Agent Layer)

- Tool arguments validated by MAF's type system (Pydantic-based schema generation from function signatures)
- `SecurityMiddleware` validates tool arguments for injection patterns before execution
- `AgentSessionMapping` enforces max concurrent sessions limit
- Streaming endpoint validates that `agent_streaming_enabled` config is `True`

---

## Database Schema Changes

**None**. The SQLite schema is unchanged. All new state (AgentSession, tool registry) is in-memory only. The existing `chat_messages`, `proposals`, and `recommendations` tables continue to be the persistence layer.
