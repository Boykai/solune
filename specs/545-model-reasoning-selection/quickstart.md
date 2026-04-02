# Quickstart: Model Reasoning Level Selection

**Feature**: `545-model-reasoning-selection`  
**Date**: 2026-04-02

## Overview

This guide walks through implementing reasoning level selection end-to-end. The feature threads the GitHub Copilot SDK's existing reasoning data from the model list through session creation to frontend selectors.

## Prerequisites

- Python ≥3.12 with backend dependencies installed (`cd solune/backend && uv sync`)
- Node.js with frontend dependencies installed (`cd solune/frontend && npm install`)
- GitHub Copilot SDK (`copilot` package) with Model reasoning fields available
- `agent_framework_github_copilot` package installed

## Implementation Order

### Phase 1: Backend — Expose reasoning data (P1)

**Step 1: Extend ModelOption** (`solune/backend/src/models/settings.py`)

Add two optional fields to `ModelOption`:

```python
class ModelOption(BaseModel):
    """A single model option returned by a provider."""
    id: str
    name: str
    provider: str
    supported_reasoning_efforts: list[str] | None = None  # NEW
    default_reasoning_effort: str | None = None            # NEW
```

**Step 2: Populate from SDK** (`solune/backend/src/services/model_fetcher.py`)

In the `fetch_models()` loop, extract reasoning fields:

```python
for info in model_list:
    model_id = getattr(info, "id", "") or ""
    model_name = getattr(info, "name", "") or model_id
    if model_id:
        supported = getattr(info, "supported_reasoning_efforts", None)
        default = getattr(info, "default_reasoning_effort", None)
        models.append(
            ModelOption(
                id=model_id,
                name=model_name,
                provider="copilot",
                supported_reasoning_efforts=supported if supported else None,
                default_reasoning_effort=default if default else None,
            )
        )
```

**Step 3: Regenerate OpenAPI** (from repo root)

```bash
cd solune/backend && python ../scripts/export-openapi.py
```

**Step 4: Backend tests** (`solune/backend/tests/unit/test_model_fetcher.py`)

Add test that mock SDK models include reasoning fields and verify ModelOption serializes them.

### Phase 2: Backend — Accept and pass reasoning effort (P1)

**Step 5: Add to AIPreferences** (`solune/backend/src/models/settings.py`)

```python
class AIPreferences(BaseModel):
    """AI-related settings (fully resolved)."""
    provider: AIProvider
    model: str
    temperature: float = Field(ge=0.0, le=2.0)
    agent_model: str = ""
    reasoning_effort: str = ""  # NEW
```

**Step 6: Pass in CopilotCompletionProvider** (`solune/backend/src/services/completion_providers.py`)

Add `reasoning_effort` parameter to `complete()` and include in SessionConfig:

```python
async def complete(self, ..., reasoning_effort: str = "") -> ...:
    config: SessionConfig = {
        "model": self._model,
        "on_permission_request": PermissionHandler.approve_all,
    }
    if reasoning_effort:
        config["reasoning_effort"] = reasoning_effort  # NEW
    ...
```

**Step 7: Inject in agent provider** (`solune/backend/src/services/agent_provider.py`)

Add `reasoning_effort` parameter to `_create_copilot_agent()` and include in options:

```python
async def _create_copilot_agent(
    *,
    instructions: str,
    tools: list | None = None,
    github_token: str | None = None,
    mcp_servers: dict[str, Any] | None = None,
    reasoning_effort: str = "",  # NEW
) -> Any:
    ...
    options: GitHubCopilotOptions = {
        "model": settings.copilot_model,
        "on_permission_request": PermissionHandler.approve_all,
        "timeout": float(settings.agent_copilot_timeout_seconds),
    }
    if reasoning_effort:
        options["reasoning_effort"] = reasoning_effort  # type: ignore[typeddict-extra-key]
    ...
```

**Step 8: Resolve in orchestrator** (`solune/backend/src/services/workflow_orchestrator/orchestrator.py`)

Extend `_resolve_effective_model()` to also return reasoning_effort:

```python
async def _resolve_effective_model(self, ...) -> tuple[str, str]:
    """Returns (model_id, reasoning_effort)."""
    # ... existing model resolution ...
    
    # Reasoning effort resolution (same precedence)
    reasoning = ""
    if isinstance(config, dict):
        reasoning = (config.get("reasoning_effort") or "").strip()
    if not reasoning and user_reasoning_effort:
        reasoning = user_reasoning_effort.strip()
    # Model default can be resolved if ModelOption data is available
    
    return model_id, reasoning
```

### Phase 3: Frontend — Types, API, and UI (P2)

**Step 9: Extend types** (`solune/frontend/src/types/index.ts`)

```typescript
export interface AIModel {
  id: string;
  name: string;
  provider: string;
  context_window_size?: number;
  cost_tier?: 'economy' | 'standard' | 'premium';
  capability_category?: string;
  supported_reasoning_efforts?: string[];        // NEW
  default_reasoning_effort?: string | null;       // NEW
  reasoning_effort?: string;                      // NEW (set by expansion)
}

export interface AIPreferences {
  provider: AIProviderType;
  model: string;
  temperature: number;
  agent_model: string;
  reasoning_effort?: string;  // NEW
}

export interface PipelineModelOverride {
  mode: 'auto' | 'specific' | 'mixed';
  modelId: string;
  modelName: string;
  reasoningEffort?: string;  // NEW
}
```

**Step 10: Update API mapper** (`solune/frontend/src/services/api.ts`)

```typescript
return (response.models ?? []).map((model) => ({
  id: model.id,
  name: model.name,
  provider: model.provider,
  supported_reasoning_efforts: model.supported_reasoning_efforts,  // NEW
  default_reasoning_effort: model.default_reasoning_effort,        // NEW
}));
```

**Step 11: Expand in useModels** (`solune/frontend/src/hooks/useModels.ts`)

After fetching, expand reasoning models:

```typescript
const models = useMemo(() => {
  const raw = data ?? [];
  const expanded: AIModel[] = [];
  for (const model of raw) {
    if (model.supported_reasoning_efforts?.length) {
      for (const level of model.supported_reasoning_efforts) {
        expanded.push({
          ...model,
          name: `${model.name} (${level.charAt(0).toUpperCase() + level.slice(1)})`,
          reasoning_effort: level,
        });
      }
    } else {
      expanded.push(model);
    }
  }
  return expanded;
}, [data]);
```

**Step 12: Add ReasoningBadge** (`solune/frontend/src/components/pipeline/ModelSelector.tsx`)

Model after CostTierBadge, using Brain icon:

```typescript
function ReasoningBadge({ level, isDefault }: { level: string; isDefault?: boolean }) {
  // Color by level: low=teal, medium=sky, high=amber, xhigh=purple
  return (
    <span className={cn("inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[10px]...", colorClass)}>
      <Brain className="h-2.5 w-2.5" />
      {level}{isDefault ? " (Default)" : ""}
    </span>
  );
}
```

**Step 13: Update Brain icon export** (`solune/frontend/src/lib/icons.ts`)

```typescript
export { Brain } from 'lucide-react';
```

**Step 14: Update settings + pipeline forms**

- `PrimarySettings.tsx`: Save `reasoning_effort` as separate field
- `AgentNode.tsx`: Pass `reasoning_effort` in config
- `PipelineModelDropdown.tsx`: Include reasoning_effort in onModelChange

## Verification

```bash
# Backend tests
cd solune/backend && python -m pytest tests/unit/ -v

# Frontend tests
cd solune/frontend && npm test

# Type check
cd solune/frontend && npx tsc --noEmit

# Contract validation
bash solune/scripts/validate-contracts.sh
```

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Separate fields, not composite IDs | Cleaner API, no parsing, backwards compatible |
| Display: `{name} ({Level})` | Clear, consistent, scannable |
| Expansion at hook level | Single logic point; all selectors benefit automatically |
| MAF options dict injection | Workaround for missing framework support; clean and non-breaking |
| Copilot only | Azure OpenAI doesn't expose reasoning levels |
| Empty = API default | Backwards compatible; no breaking changes |
