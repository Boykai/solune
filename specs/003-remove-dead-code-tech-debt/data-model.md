# Data Model: Remove Dead Code & Tech Debt

This feature is a cleanup/refactoring effort — no new entities or data models are introduced. This document maps the modules being removed and their dependency relationships to guide safe deletion order.

## 1. Deprecated Module: `AIAgentService` (`src/services/ai_agent.py`)

**Purpose**: Legacy AI completion service replaced by `ChatAgentService` (Microsoft Agent Framework).

| Symbol | Type | Consumers | Migration Target |
|--------|------|-----------|-----------------|
| `AIAgentService` | class | `tests/conftest.py` (type), `workflow_orchestrator/orchestrator.py` (type) | `ChatAgentService` |
| `get_ai_agent_service()` | factory | `api/chat.py`, `app_service.py`, `chores/chat.py`, `agents/service.py`, `api/pipelines.py`, `workflow_orchestrator/orchestrator.py`, `agent_creator.py`, `signal_chat.py` | `get_chat_agent_service()` |
| `_call_completion()` | method | `chores/chat.py` (×2), `agents/service.py` (×4) | `ChatAgentService.run()` |
| `analyze_transcript()` | method | `api/pipelines.py` (×1) | New utility or `ChatAgentService` method |
| `generate_agent_config()` | method | `agent_creator.py` (×1) | New utility or `ChatAgentService` method |

**Internal dependencies** (also being deleted):
- `src.prompts.issue_generation` → `create_issue_generation_prompt()`, `create_feature_request_detection_prompt()`
- `src.prompts.task_generation` → `create_task_generation_prompt()`, `create_status_change_prompt()`
- `src.prompts.transcript_analysis` → `create_transcript_analysis_prompt()`
- `src.services.completion_providers` → `CompletionProvider`, `create_completion_provider()`

**State**: Stateful singleton (module-level `_ai_agent_service` instance).

## 2. Deprecated Module: `completion_providers.py` (`src/services/completion_providers.py`)

**Purpose**: Legacy LLM completion abstraction replaced by `agent_provider` module.

| Symbol | Type | Consumers | Migration Target |
|--------|------|-----------|-----------------|
| `CopilotClientPool` | class | `model_fetcher.py` (type + usage), `agent_provider.py` (usage), `plan_agent_provider.py` (usage) | Relocate to `agent_provider.py` |
| `get_copilot_client_pool()` | factory | `agent_provider.py` (L200), `plan_agent_provider.py` (L194), `model_fetcher.py` (L17) | Relocate to `agent_provider.py` |
| `CompletionProvider` | abstract class | `ai_agent.py` (internal) | Delete (no external consumers after Phase 2) |
| `CopilotCompletionProvider` | class | `ai_agent.py` (internal) | Delete |
| `AzureOpenAICompletionProvider` | class | None (only via factory) | Delete |
| `create_completion_provider()` | factory | `label_classifier.py` (L101, L157) | Replace with `agent_provider`-based completion |

**State**: `CopilotClientPool` manages a pool of authenticated Copilot API clients. This state must be preserved when relocating to `agent_provider.py`.

## 3. Deprecated Prompt Modules (`src/prompts/`)

**Purpose**: Legacy prompt templates replaced by `src/prompts/agent_instructions`.

| Module | Exports | Only Consumer |
|--------|---------|---------------|
| `issue_generation.py` | `create_issue_generation_prompt()`, `create_feature_request_detection_prompt()` | `ai_agent.py` |
| `task_generation.py` | `create_task_generation_prompt()`, `create_status_change_prompt()` | `ai_agent.py` |
| `transcript_analysis.py` | `create_transcript_analysis_prompt()` | `ai_agent.py` |

**State**: Stateless pure functions. No migration of state needed.

## 4. Retained Field: `pipeline_metadata` (`auto_merge.py`)

**Purpose**: Deduplication and retry-cap tracking in devops agent dispatch flow.

| Field | Type | Location | Status |
|-------|------|----------|--------|
| `pipeline_metadata` | `dict[str, Any] \| None` | `dispatch_devops_agent()` param (L299) | Deferred — actively mutated |
| `pipeline_metadata` | `dict[str, Any]` | `_post_devops_retry_loop()` param (L497) | Deferred — required, not optional |
| `pipeline_metadata["devops_active"]` | `bool` | L540 mutation | Active side-effect in retry flow |

**Decision**: Retain. Removal deferred to a dedicated PR with data-migration analysis.

## Dependency Graph (Deletion Order)

```text
Phase 1 (no dependencies):
  issue_generation.py ──┐
  task_generation.py ───┤ Only imported by ai_agent.py
  transcript_analysis.py┘

Phase 2 (depends on Phase 1):
  ai_agent.py ─────────── imports Phase 1 modules + completion_providers.py
    └─ consumers: chat.py, app_service.py, chores/chat.py, agents/service.py,
       pipelines.py, orchestrator.py, agent_creator.py, signal_chat.py, conftest.py

Phase 3 (depends on Phase 2):
  completion_providers.py ─ CopilotClientPool relocated to agent_provider.py
    └─ consumers: agent_provider.py, plan_agent_provider.py, model_fetcher.py,
       label_classifier.py
```

## Test Artifacts Removed

| Test File | Tests Module | Removed In |
|-----------|-------------|------------|
| `test_issue_generation_prompt.py` | `src.prompts.issue_generation` | Phase 1 |
| `test_task_generation_prompt.py` | `src.prompts.task_generation` | Phase 1 |
| `test_transcript_analysis_prompt.py` | `src.prompts.transcript_analysis` | Phase 1 |
| `test_ai_agent.py` | `src.services.ai_agent` | Phase 2 |
| `test_completion_providers.py` | `src.services.completion_providers` | Phase 3 |
| `conftest.py` fixture `mock_ai_agent_service` | `src.services.ai_agent.AIAgentService` | Phase 2 |
