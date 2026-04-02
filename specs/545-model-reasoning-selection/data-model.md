# Data Model: Model Reasoning Level Selection

**Feature**: `545-model-reasoning-selection`  
**Date**: 2026-04-02

## Entity Changes

### Backend Entities

#### ModelOption (modified)

**File**: `solune/backend/src/models/settings.py`  
**Type**: Pydantic `BaseModel`

| Field | Type | Default | Status | Description |
|-------|------|---------|--------|-------------|
| `id` | `str` | required | existing | Model identifier (e.g., `"o3"`) |
| `name` | `str` | required | existing | Display name (e.g., `"o3"`) |
| `provider` | `str` | required | existing | Provider slug (e.g., `"copilot"`) |
| `supported_reasoning_efforts` | `list[str] \| None` | `None` | **new** | Reasoning levels this model supports (e.g., `["low", "medium", "high"]`). `None` if model has no reasoning support. |
| `default_reasoning_effort` | `str \| None` | `None` | **new** | Default reasoning level for this model (e.g., `"medium"`). `None` if no reasoning support. |

**Validation rules**:
- `supported_reasoning_efforts` values must be from `{"low", "medium", "high", "xhigh"}` (SDK-defined).
- If `supported_reasoning_efforts` is `None`, `default_reasoning_effort` must also be `None`.
- If `default_reasoning_effort` is set, it must be a member of `supported_reasoning_efforts`.

**State transitions**: None (read-only data fetched from SDK).

---

#### AIPreferences (modified)

**File**: `solune/backend/src/models/settings.py`  
**Type**: Pydantic `BaseModel`

| Field | Type | Default | Status | Description |
|-------|------|---------|--------|-------------|
| `provider` | `AIProvider` | required | existing | AI provider enum |
| `model` | `str` | required | existing | Chat model ID |
| `temperature` | `float` | required | existing | Temperature (0.0-2.0) |
| `agent_model` | `str` | `""` | existing | Agent/reasoning model |
| `reasoning_effort` | `str` | `""` | **new** | User's default reasoning level (e.g., `"high"`). Empty = API default. |

**Validation rules**:
- Empty string or a valid reasoning level from `{"low", "medium", "high", "xhigh"}`.
- Backwards compatible: empty = no preference (SDK picks default).

---

#### PipelineAgentNode (unchanged — uses config dict)

**File**: `solune/backend/src/models/pipeline.py`  
**Type**: Pydantic `BaseModel`

The `config: dict` field already supports arbitrary key-value pairs. The orchestrator will read `config["reasoning_effort"]` alongside existing `config["model_id"]`.

| Config Key | Type | Status | Description |
|------------|------|--------|-------------|
| `model_id` | `str` | existing | Override model for this agent |
| `reasoning_effort` | `str` | **new (convention)** | Override reasoning level for this agent |

---

### Frontend Entities

#### AIModel (modified)

**File**: `solune/frontend/src/types/index.ts`

| Field | Type | Status | Description |
|-------|------|--------|-------------|
| `id` | `string` | existing | Model identifier |
| `name` | `string` | existing | Display name |
| `provider` | `string` | existing | Provider slug |
| `context_window_size` | `number?` | existing | Context window tokens |
| `cost_tier` | `'economy' \| 'standard' \| 'premium'?` | existing | Cost classification |
| `capability_category` | `string?` | existing | Capability grouping |
| `supported_reasoning_efforts` | `string[]?` | **new** | Reasoning levels supported |
| `default_reasoning_effort` | `string \| null?` | **new** | Default reasoning level |
| `reasoning_effort` | `string?` | **new** | Reasoning level for this variant (set by useModels expansion) |

**Note**: After `useModels()` expansion, reasoning-capable models become N entries. Each variant has:
- Same `id` (e.g., `"o3"`)
- Modified `name` (e.g., `"o3 (High)"`)
- Populated `reasoning_effort` (e.g., `"high"`)

---

#### AIPreferences (modified)

**File**: `solune/frontend/src/types/index.ts`

| Field | Type | Status | Description |
|-------|------|--------|-------------|
| `provider` | `AIProviderType` | existing | Provider enum |
| `model` | `string` | existing | Chat model ID |
| `temperature` | `number` | existing | Temperature |
| `agent_model` | `string` | existing | Agent model ID |
| `reasoning_effort` | `string?` | **new** | User's reasoning preference |

---

#### PipelineModelOverride (modified)

**File**: `solune/frontend/src/types/index.ts`

| Field | Type | Status | Description |
|-------|------|--------|-------------|
| `mode` | `'auto' \| 'specific' \| 'mixed'` | existing | Override mode |
| `modelId` | `string` | existing | Model ID |
| `modelName` | `string` | existing | Model display name |
| `reasoningEffort` | `string?` | **new** | Reasoning level |

---

## Entity Relationships

```text
ModelOption (backend)
  ├── fetched from: GitHub Copilot SDK client.list_models()
  ├── serialized to: AIModel (frontend) via modelsApi.list()
  └── expanded by: useModels() hook into reasoning variants

AIPreferences (backend)
  ├── stored in: settings JSON file
  ├── resolved by: orchestrator._resolve_effective_model()
  └── synced with: AIPreferences (frontend) via settings API

PipelineAgentNode.config
  ├── stored in: pipeline configuration
  ├── read by: orchestrator._resolve_effective_model()
  └── set by: AgentNode.tsx → ModelSelector → onModelSelect
```

## Data Flow

```text
SDK Model.supported_reasoning_efforts
  → model_fetcher.py → ModelOption.supported_reasoning_efforts
    → OpenAPI schema → modelsApi.list()
      → AIModel.supported_reasoning_efforts
        → useModels() expansion
          → AIModel variants with reasoning_effort set
            → ModelSelector / DynamicDropdown / PipelineModelDropdown

User selects variant (e.g., "o3 (High)")
  → model_id: "o3", reasoning_effort: "high"
    → AIPreferences.reasoning_effort (settings) OR PipelineAgentNode.config["reasoning_effort"]
      → orchestrator._resolve_effective_model() resolves final reasoning_effort
        → CopilotCompletionProvider.complete() / agent_provider._create_copilot_agent()
          → SessionConfig["reasoning_effort"] = "high"
            → GitHub Copilot SDK session
```
