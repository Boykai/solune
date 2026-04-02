# Feature Specification: Model Reasoning Level Selection

**Feature Branch**: `545-model-reasoning-selection`  
**Created**: 2026-04-02  
**Status**: Draft  
**Input**: Parent Issue #545 — Model Reasoning Level Selection

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Backend exposes reasoning data in model list (Priority: P1)

As a developer consuming the model list API, I want each model to include its supported reasoning efforts and default reasoning effort, so that the frontend can present reasoning level choices.

**Why this priority**: Without backend data exposure, no downstream features can function. This is the foundational data layer.

**Independent Test**: Can be fully tested by calling `GET /api/v1/settings/models/copilot` and verifying that reasoning-capable models return `supported_reasoning_efforts` and `default_reasoning_effort` fields.

**Acceptance Scenarios**:

1. **Given** a model with reasoning support (e.g., o3), **When** `GET /api/v1/settings/models/copilot` is called, **Then** the response includes `supported_reasoning_efforts: ["low", "medium", "high"]` and `default_reasoning_effort: "medium"`.
2. **Given** a model without reasoning support (e.g., gpt-4.1), **When** `GET /api/v1/settings/models/copilot` is called, **Then** `supported_reasoning_efforts` is `null` and `default_reasoning_effort` is `null`.
3. **Given** the OpenAPI schema, **When** contract validation runs, **Then** `ModelOption` schema includes the new optional fields.

---

### User Story 2 - Backend accepts and passes reasoning effort to sessions (Priority: P1)

As a user selecting a reasoning level, I want the backend to accept my reasoning_effort preference and pass it through to the Copilot SDK session, so that the AI model actually uses the specified reasoning level.

**Why this priority**: This is the core plumbing that makes reasoning selection functional end-to-end. Without it, UI changes are cosmetic only.

**Independent Test**: Can be tested by sending a chat request with `reasoning_effort: "high"` and verifying the SessionConfig passed to the SDK includes `reasoning_effort: "high"`.

**Acceptance Scenarios**:

1. **Given** a user with `reasoning_effort: "high"` in AIPreferences, **When** a completion request is made, **Then** `SessionConfig` includes `reasoning_effort: "high"`.
2. **Given** a pipeline agent node with `reasoning_effort: "medium"` in config, **When** the orchestrator resolves the model, **Then** reasoning_effort is resolved with precedence: pipeline config → user settings → model default → empty.
3. **Given** `reasoning_effort` is empty/unset, **When** a completion request is made, **Then** `reasoning_effort` is omitted from SessionConfig (API default behavior).
4. **Given** the MAF agent path, **When** a Copilot agent is created, **Then** reasoning_effort is injected into the session config.

---

### User Story 3 - Frontend displays reasoning level variants in model selectors (Priority: P2)

As a user choosing a model in Settings or Pipeline editor, I want reasoning-capable models expanded into variants (e.g., "o3 (High)", "o3 (Medium)"), so that I can visually select the reasoning level alongside the model.

**Why this priority**: This is the user-facing experience that makes the feature discoverable and usable. Depends on P1 stories.

**Independent Test**: Can be tested by loading the Settings page with mocked model data containing reasoning efforts and verifying the dropdown shows expanded variants with reasoning badges.

**Acceptance Scenarios**:

1. **Given** a model with `supported_reasoning_efforts: ["low", "medium", "high"]`, **When** the model selector renders, **Then** it shows 3 variants: "o3 (Low)", "o3 (Medium)", "o3 (High)".
2. **Given** a model without reasoning support, **When** the model selector renders, **Then** it shows the model name unchanged with no reasoning badge.
3. **Given** the model's `default_reasoning_effort` is "medium", **When** variants are displayed, **Then** the "medium" variant is visually marked as default.
4. **Given** a user selects "o3 (High)", **When** the selection is saved, **Then** `model: "o3"` and `reasoning_effort: "high"` are stored as separate fields.

---

### User Story 4 - Pipeline agent nodes support reasoning effort (Priority: P2)

As a pipeline editor, I want to configure reasoning effort per agent node, so that different agents in a pipeline can use different reasoning levels.

**Why this priority**: Pipeline customization is an advanced use case that builds on the core infrastructure.

**Independent Test**: Can be tested by configuring a pipeline agent with a reasoning model variant and verifying `reasoning_effort` is stored in the agent node config and passed through orchestration.

**Acceptance Scenarios**:

1. **Given** a pipeline agent node, **When** I select "o3 (High)" from the model dropdown, **Then** `model_id: "o3"` and `reasoning_effort: "high"` are stored in the node config.
2. **Given** a pipeline with a reasoning-configured agent, **When** the pipeline executes, **Then** the orchestrator passes the correct reasoning_effort to the session.

---

### Edge Cases

- What happens when the SDK returns a model with empty `supported_reasoning_efforts`? → Treat as non-reasoning model (no expansion, no badge).
- What happens when a user has a saved `reasoning_effort` but the model no longer supports it? → The backend should pass it anyway; the SDK will handle validation.
- What happens when `reasoning_effort` is "auto" or an empty string? → Treat as unset; omit from SessionConfig.
- How does this interact with Azure OpenAI provider? → Scoped to Copilot provider only. Azure OpenAI models remain unchanged.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `ModelOption` MUST include optional `supported_reasoning_efforts: list[str] | None` and `default_reasoning_effort: str | None` fields.
- **FR-002**: `GitHubCopilotModelFetcher.fetch_models()` MUST extract reasoning data from the SDK's Model dataclass.
- **FR-003**: OpenAPI schema MUST be regenerated to reflect new `ModelOption` fields.
- **FR-004**: `AIPreferences` MUST include optional `reasoning_effort: str` field (default empty).
- **FR-005**: `PipelineAgentNode` MUST support `reasoning_effort` in its config dict.
- **FR-006**: `CopilotCompletionProvider.complete()` MUST accept and pass `reasoning_effort` to `SessionConfig`.
- **FR-007**: Agent provider MUST inject `reasoning_effort` into Copilot agent session config.
- **FR-008**: Orchestrator MUST resolve `reasoning_effort` with precedence: pipeline config → user settings → model default → empty.
- **FR-009**: Frontend `AIModel` type MUST include `supported_reasoning_efforts` and `default_reasoning_effort`.
- **FR-010**: `modelsApi.list()` MUST pass through reasoning fields from backend.
- **FR-011**: `useModels()` hook MUST expand reasoning-capable models into per-level variants.
- **FR-012**: `ModelSelector.ModelRow` MUST display a `ReasoningBadge` for reasoning variants.
- **FR-013**: Settings form MUST store `model` and `reasoning_effort` as separate fields.
- **FR-014**: Pipeline model dropdown and agent node MUST support reasoning_effort selection.
- **FR-015**: Models without reasoning support MUST display unchanged (no badge, no suffix).

### Key Entities

- **ModelOption**: Backend model descriptor; gains reasoning metadata fields.
- **AIPreferences**: User-level AI settings; gains reasoning_effort preference.
- **PipelineAgentNode**: Per-agent pipeline config; gains reasoning_effort in config dict.
- **AIModel**: Frontend model descriptor; gains reasoning metadata and per-variant reasoning_effort.
- **PipelineModelOverride**: Pipeline-level model override; gains reasoning_effort field.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `GET /api/v1/settings/models/copilot` returns reasoning fields for all reasoning-capable models.
- **SC-002**: All backend tests pass (`pytest tests/ -v`).
- **SC-003**: All frontend tests pass (`npm test`).
- **SC-004**: TypeScript type check passes (`npx tsc --noEmit`).
- **SC-005**: Contract validation passes (`bash scripts/validate-contracts.sh`).
- **SC-006**: Settings model dropdown shows reasoning variants (e.g., "o3 (High)") for reasoning-capable models.
- **SC-007**: Pipeline model selector shows reasoning variants.
- **SC-008**: Selecting a reasoning model variant results in `reasoning_effort` appearing in SessionConfig in backend logs.
- **SC-009**: Models without reasoning support display unchanged.
