# Research: Model Reasoning Level Selection

**Feature**: `545-model-reasoning-selection`  
**Date**: 2026-04-02  
**Status**: Complete

## Research Tasks

### R1: GitHub Copilot SDK — SessionConfig reasoning_effort support

**Decision**: Use the existing `reasoning_effort` field in `SessionConfig` TypedDict.

**Rationale**: The SDK's `SessionConfig` (from `copilot.types`) already defines a `reasoning_effort` field typed as `ReasoningEffort = Literal["low", "medium", "high", "xhigh"]`. The current codebase constructs SessionConfig with only `model`, `on_permission_request`, and optional `system_message`. Adding `reasoning_effort` is a matter of including it in the dict when non-empty.

**Alternatives considered**:
- Custom header injection → Rejected: SDK already has first-class support.
- Model ID suffixing (e.g., `o3-high`) → Rejected: Not how the SDK works; reasoning is a session-level parameter, not a model variant.

### R2: GitHub Copilot SDK — Model dataclass reasoning fields

**Decision**: Extract `supported_reasoning_efforts` and `default_reasoning_effort` from SDK Model objects using `getattr()`.

**Rationale**: The SDK's `Model` dataclass exposes `.supported_reasoning_efforts` (list of str or None) and `.default_reasoning_effort` (str or None). The current `fetch_models()` loop already uses `getattr(info, "id", "")` pattern for safe attribute access. The same pattern applies for reasoning fields.

**Alternatives considered**:
- Hard-code reasoning support per model → Rejected: SDK provides authoritative data; hard-coding would drift.
- Separate API call for reasoning metadata → Rejected: Data already present in list_models response.

### R3: agent_framework_github_copilot — reasoning_effort forwarding gap

**Decision**: Inject `reasoning_effort` into `GitHubCopilotOptions` dict passed to `GitHubCopilotAgent.default_options`.

**Rationale**: The MAF `GitHubCopilotAgent` accepts `default_options: GitHubCopilotOptions` which is forwarded to session creation. While `_create_session()` in the framework doesn't explicitly forward `reasoning_effort`, the options dict is spread into the SDK's `SessionConfig`. Adding `reasoning_effort` to the options dict should propagate. If the TypedDict doesn't include it, we can use type: ignore for the extra key since the underlying SDK accepts it.

**Alternatives considered**:
- Monkey-patch `_create_session()` → Rejected: Fragile; would break on framework updates.
- Post-creation session config override → Rejected: No public API for this.
- Upstream PR to MAF → Noted as future improvement; workaround sufficient for now.

### R4: Reasoning effort resolution precedence

**Decision**: Extend `_resolve_effective_model()` to return both model and reasoning_effort, using the same tiered precedence.

**Rationale**: The existing resolution pattern (pipeline config → user settings → fallback) is well-established for model selection. Reasoning effort follows the same pattern:
1. Pipeline agent node `config["reasoning_effort"]` (highest priority)
2. User settings `AIPreferences.reasoning_effort` 
3. Model default from `ModelOption.default_reasoning_effort`
4. Empty string (omit from SessionConfig — SDK uses its own default)

**Alternatives considered**:
- Always use model default → Rejected: Removes user agency; pipeline customization impossible.
- Separate resolution function → Rejected: Violates DRY; same precedence logic applies.

### R5: Frontend model expansion strategy

**Decision**: Expand reasoning-capable models in `useModels()` hook, producing per-level `AIModel` variants with `reasoning_effort` field.

**Rationale**: Centralizing expansion in the hook means all downstream consumers (`ModelSelector`, `PipelineModelDropdown`, `DynamicDropdown`) automatically see reasoning variants without per-component changes. Each variant carries both the original `id` (for API calls) and a `reasoning_effort` (for session config). Display name uses the format `{name} ({Level})` (e.g., "o3 (High)").

**Alternatives considered**:
- Expand in each component → Rejected: Violates DRY; 3+ components would need identical logic.
- Expand in API layer → Rejected: API should return raw data; presentation logic belongs in hooks.
- Composite model IDs (e.g., `o3::high`) → Rejected: Requires parsing everywhere; breaks existing ID-based lookups.

### R6: ReasoningBadge component design

**Decision**: Model `ReasoningBadge` after existing `CostTierBadge` in `ModelSelector.tsx`.

**Rationale**: `CostTierBadge` provides a proven pattern: switch on tier value, render color-coded pill with icon + label. For reasoning, use `Brain` icon from lucide-react (needs adding to `icons.ts` barrel). Color scheme: teal for low, sky for medium, amber for high, purple for xhigh. Mark the model's default reasoning level distinctly.

**Alternatives considered**:
- Text-only label → Rejected: Inconsistent with CostTierBadge visual language.
- Separate column/row → Rejected: Takes too much space; badge is compact and scannable.

### R7: Backwards compatibility

**Decision**: All new fields are optional with empty/null defaults. No breaking changes.

**Rationale**:
- `ModelOption.supported_reasoning_efforts: list[str] | None = None` — null for non-reasoning models.
- `ModelOption.default_reasoning_effort: str | None = None` — null for non-reasoning models.
- `AIPreferences.reasoning_effort: str = ""` — empty = omit from SessionConfig.
- `PipelineAgentNode.config` already a dict — adding `reasoning_effort` key is non-breaking.
- Frontend types use optional fields (`?`) — existing code unaffected.
- `modelsApi.list()` mapper adds fields only when present.

**Alternatives considered**: None — backwards compatibility is a hard requirement.

### R8: Icons barrel file update

**Decision**: Add `Brain` to the `icons.ts` barrel re-export from lucide-react.

**Rationale**: All Lucide icons must be re-exported from `solune/frontend/src/lib/icons.ts` barrel file. Direct lucide-react imports are blocked by ESLint `no-restricted-imports` rule. The `Brain` icon is not currently exported (95 icons exist; Brain is not among them).

**Alternatives considered**:
- Use existing icon (e.g., `Cpu`, `Sparkles`) → Rejected: Brain specifically conveys "reasoning/thinking".
- Skip icon → Rejected: Inconsistent with CostTierBadge which uses icons for each tier.
