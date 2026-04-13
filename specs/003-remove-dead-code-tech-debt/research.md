# Research: Remove Dead Code & Tech Debt

## Decision 1: Migration path for `AIAgentService._call_completion()` consumers

- **Decision**: Replace lazy `get_ai_agent_service()` imports in `chores/chat.py` and `agents/service.py` with `get_chat_agent_service()` from `src.services.chat_agent`, using `ChatAgentService.run()` as the replacement for `_call_completion()`.
- **Rationale**: `ChatAgentService.run()` (L338–443 of `chat_agent.py`) already wraps the Microsoft Agent Framework's completion flow and accepts messages with temperature/token parameters. The `_call_completion()` pattern in `ai_agent.py` is a thin wrapper around the deprecated `CompletionProvider`; `ChatAgentService.run()` provides equivalent functionality through the modern agent framework.
- **Alternatives considered**:
  - Inline direct OpenAI/Copilot client calls — rejected because it would bypass the agent framework's session management and tool integration.
  - Create a standalone `CompletionService` — rejected per YAGNI; `ChatAgentService` already provides the abstraction layer.

## Decision 2: Migration path for `AIAgentService.analyze_transcript()` in `pipelines.py`

- **Decision**: Move `analyze_transcript()` logic into a standalone utility function or a new method on `ChatAgentService`, using the agent framework's completion API for the underlying LLM call.
- **Rationale**: `analyze_transcript()` in `ai_agent.py` (L~800–850) performs prompt construction using `create_transcript_analysis_prompt()` and then calls `_call_completion()`. The prompt logic can be preserved as a utility while the completion call routes through `ChatAgentService`. The prompt module `transcript_analysis.py` is deleted in Phase 1, so the prompt text must be inlined or moved to `prompts/agent_instructions` (the designated replacement per the deprecated modules' docstrings).
- **Alternatives considered**:
  - Keep `transcript_analysis.py` alive for just this function — rejected because it defeats the purpose of removing deprecated prompt modules.
  - Drop transcript analysis entirely — rejected because `pipelines.py` actively uses it for pipeline launches from issue context.

## Decision 3: Migration path for `AIAgentService.generate_agent_config()` in `agent_creator.py`

- **Decision**: Migrate `generate_agent_config()` into `ChatAgentService` or a new lightweight function in `agent_creator.py` itself, using the agent-provider completion pattern.
- **Rationale**: `generate_agent_config()` uses `_call_completion()` with a configuration-generation prompt. The logic is self-contained and can be implemented as a method on `ChatAgentService` or inlined in `agent_creator.py` with a direct `agent_provider` call. Given that `agent_creator.py` already has a module-level import (L28), migrating to `ChatAgentService` maintains the existing dependency pattern.
- **Alternatives considered**:
  - Create a separate `AgentConfigService` — rejected per YAGNI; the function is used in exactly one place.

## Decision 4: Relocation of `CopilotClientPool` / `get_copilot_client_pool`

- **Decision**: Move `CopilotClientPool` class and `get_copilot_client_pool()` singleton from `completion_providers.py` into `agent_provider.py`, which is the designated non-deprecated replacement module.
- **Rationale**: `agent_provider.py` already imports `get_copilot_client_pool` (L200) and is the primary consumer. `plan_agent_provider.py` (L194) and `model_fetcher.py` (L17) also import these symbols. Moving them into `agent_provider.py` consolidates the client-pool lifecycle in the module that manages agent creation. The `CopilotClientPool` class (~70 lines) and factory function (~5 lines) are small enough to inline without introducing a new module.
- **Alternatives considered**:
  - Create a new `copilot_client_pool.py` module — rejected because it would add a file for ~75 lines of code that logically belongs with agent provisioning.
  - Keep `completion_providers.py` with only `CopilotClientPool` — rejected because the file name is misleading and the module is marked deprecated.

## Decision 5: Migration of `create_completion_provider()` in `label_classifier.py`

- **Decision**: Replace `create_completion_provider()` calls in `label_classifier.py` (L101, L157) with the `agent_provider`-based completion pattern, using `get_copilot_client_pool()` and constructing a completion call through the Copilot client directly.
- **Rationale**: `create_completion_provider()` returns a `CompletionProvider` instance (either `CopilotCompletionProvider` or `AzureOpenAICompletionProvider`). The label classifier only needs the completion API surface. After relocating `CopilotClientPool` to `agent_provider.py`, the classifier can use the client pool directly or a thin wrapper function in `agent_provider.py`.
- **Alternatives considered**:
  - Keep `CompletionProvider` abstract class alive — rejected because it's the deprecated abstraction layer we're removing.
  - Use `ChatAgentService` for label classification — rejected because label classification is a simple stateless completion, not an agent conversation.

## Decision 6: `pipeline_metadata` field in `auto_merge.py` — defer removal

- **Decision**: Keep the `pipeline_metadata` parameter in `dispatch_devops_agent()` and `_post_devops_retry_loop()` for now. Document as deferred tech debt.
- **Rationale**: The field is not merely passed through — it is actively mutated in the retry loop (`pipeline_metadata["devops_active"] = False` at L540) and forwarded through `schedule_post_devops_merge_retry()`. Removing it requires: (1) auditing all call sites that construct the dict, (2) verifying no external callers depend on the mutation side-effect, and (3) potentially migrating the `devops_active` flag to a different state mechanism. This exceeds the scope of a cleanup PR.
- **Alternatives considered**:
  - Remove the parameter and inline `devops_active` state — rejected because the retry flow's interaction with `pipeline_metadata` is complex enough to warrant its own focused PR with dedicated testing.

## Decision 7: Frontend logging approach — `import.meta.env.DEV` guards

- **Decision**: Wrap `console.debug()` calls in `api.ts` and `console.warn()` in `usePipelineConfig.ts` with `if (import.meta.env.DEV)` guards. No changes needed for `tooltip.tsx` (already guarded).
- **Rationale**: The simplest approach per the issue specification. Vite tree-shakes `import.meta.env.DEV` branches in production builds, so the guards add zero runtime cost. No need for a logging abstraction layer for 4 console statements.
- **Alternatives considered**:
  - Build a structured logger utility — rejected per YAGNI; only 4 statements across 2 files need guarding.
  - Use `console.log` removal via ESLint rule — rejected because it would affect all console usage globally, including intentional production logging.

## Decision 8: Root-level spec file relocation

- **Decision**: Move 6 root-level spec files (`plan.md`, `spec.md`, `tasks.md`, `data-model.md`, `research.md`, `quickstart.md`) into `specs/000-simplify-page-headers/` to match the mono-spec pattern established by `specs/001-fleet-dispatch-pipelines/`.
- **Rationale**: The root-level files belong to the "Simplify Page Headers" feature (confirmed by `spec.md` header: "Feature Specification: Simplify Page Headers for Focused UI"). The `specs/` directory structure expects `NNN-short-name/` directories. Moving these files eliminates the inconsistency and aligns with the naming convention (`000-` prefix for the earliest feature).
- **Alternatives considered**:
  - Delete the root-level files (duplicates may exist in `specs/001-*`) — rejected because the root-level files are for a different feature (000-simplify-page-headers, not 001-fleet-dispatch-pipelines).
  - Keep root-level files as-is — rejected because it violates the mono-spec organization pattern.

## Decision 9: Singleton TODO markers — convert to tracked issue

- **Decision**: If singleton TODO markers exist in `service.py` and `agents.py` at the specified locations, convert them to reference the existing TODO-018 tracking issue. If not found at those exact lines (exploration showed no TODO markers at the specified locations), document the discrepancy and skip.
- **Rationale**: The issue mentions "address or convert singleton TODO markers to a tracked issue" which aligns with the deferred singleton DI refactor. The exploration found no TODO/FIXME markers at the specified lines in `agents/service.py` or `chores/service.py`, suggesting they may have been addressed in a prior commit or the line numbers shifted. A grep for TODO-018 or singleton-related TODOs will confirm.
- **Alternatives considered**:
  - Perform the singleton DI refactor — rejected per the issue's own "Deferred" decision and the constitution's Simplicity principle.
