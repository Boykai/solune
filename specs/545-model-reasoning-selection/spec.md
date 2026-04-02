# Feature Specification: Model Reasoning Level Selection

**Feature Branch**: `545-model-reasoning-selection`  
**Created**: 2026-04-02  
**Status**: Draft  
**Input**: User description: "Model Reasoning Level Selection — Thread reasoning effort data from the AI provider end-to-end through backend and frontend so users can select and apply model reasoning levels."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Available Reasoning Levels for Models (Priority: P1)

As a user browsing available AI models, I want to see which reasoning levels each model supports (e.g., Low, Medium, High, Extra-High), so that I can make an informed decision about which model and reasoning level to use for my tasks.

**Why this priority**: Users need visibility into reasoning capabilities before they can select them. This is the foundational data that enables all downstream feature interactions.

**Independent Test**: Can be fully tested by viewing the model list and verifying that reasoning-capable models display their supported reasoning levels and default level, while non-reasoning models appear unchanged.

**Acceptance Scenarios**:

1. **Given** a reasoning-capable model (e.g., o3), **When** I view the model list, **Then** I can see the supported reasoning levels (e.g., Low, Medium, High) and which level is the default.
2. **Given** a model without reasoning support (e.g., gpt-4.1), **When** I view the model list, **Then** the model appears as it does today with no reasoning information shown.
3. **Given** the AI provider adds new reasoning levels to a model, **When** I refresh the model list, **Then** the updated reasoning levels appear automatically without any manual configuration.

---

### User Story 2 - Select a Reasoning Level in Chat Settings (Priority: P1)

As a user configuring my AI preferences, I want to choose a default reasoning level for my selected model, so that all my chat interactions use my preferred reasoning intensity without needing to set it each time.

**Why this priority**: This is the core user-facing functionality. Selecting a reasoning level in settings makes the feature usable end-to-end and delivers immediate value.

**Independent Test**: Can be tested by navigating to Settings, selecting a reasoning model variant from the dropdown, saving, then starting a chat and confirming the selected reasoning level is applied.

**Acceptance Scenarios**:

1. **Given** I am on the Settings page, **When** I open the model dropdown, **Then** reasoning-capable models are shown as expanded variants (e.g., "o3 (Low)", "o3 (Medium)", "o3 (High)") and models without reasoning support appear unchanged.
2. **Given** I select "o3 (High)" from the model dropdown and save my preferences, **When** I start a new chat, **Then** the system uses o3 with high reasoning effort.
3. **Given** I have a reasoning level saved in my preferences, **When** I switch to a model that does not support reasoning, **Then** my reasoning preference is gracefully ignored and the model operates normally.
4. **Given** a model's default reasoning level is Medium, **When** I view the model variants in the dropdown, **Then** the Medium variant is visually highlighted as the recommended default.

---

### User Story 3 - Configure Reasoning Level per Pipeline Agent (Priority: P2)

As a pipeline editor, I want to assign a specific reasoning level to each agent node in my pipeline, so that different stages of my pipeline can use different reasoning intensities optimized for their task.

**Why this priority**: Pipeline customization is an advanced use case that enables power users to fine-tune reasoning per task. It depends on the core infrastructure from P1 stories.

**Independent Test**: Can be tested by opening the pipeline editor, selecting a reasoning model variant for an agent node, saving the pipeline, and executing it to confirm the correct reasoning level is used for that agent.

**Acceptance Scenarios**:

1. **Given** I am editing a pipeline agent node, **When** I open the model selector, **Then** I see the same reasoning-expanded variants as in Settings (e.g., "o3 (High)", "o3 (Medium)").
2. **Given** I configure Agent A with "o3 (High)" and Agent B with "o3 (Low)", **When** the pipeline executes, **Then** Agent A uses high reasoning and Agent B uses low reasoning.
3. **Given** a pipeline agent has a reasoning level configured, **When** the user also has a default reasoning level in settings, **Then** the pipeline agent's configured level takes precedence over the user's default.

---

### User Story 4 - Reasoning Effort Applied to AI Responses (Priority: P1)

As a user who has selected a reasoning level, I want my AI interactions to actually use the chosen reasoning intensity, so that I get responses appropriate to the complexity of my task.

**Why this priority**: Without the system actually passing reasoning effort to the AI provider, the UI selections are cosmetic. This story ensures the selection has real effect.

**Independent Test**: Can be tested by selecting a high reasoning level, sending a complex prompt, and verifying through system behavior that the reasoning effort was communicated to the AI provider.

**Acceptance Scenarios**:

1. **Given** I have selected "High" reasoning effort for my model, **When** I send a chat message, **Then** the system communicates "high" reasoning effort to the AI provider session.
2. **Given** no reasoning effort is configured (empty/unset), **When** I send a chat message, **Then** the system omits reasoning effort from the request, allowing the AI provider to use its own default.
3. **Given** a reasoning effort is configured at multiple levels (pipeline config, user settings, model default), **When** a request is processed, **Then** the system resolves the effort using this precedence: pipeline config → user settings → model default → provider default.

---

### Edge Cases

- What happens when a model reports empty or null reasoning levels? → Treat as a non-reasoning model: no expansion, no badge, no reasoning variant shown.
- What happens when a user has a saved reasoning level but the model no longer supports it? → The system passes the saved value to the provider; the provider handles validation and fallback.
- What happens when reasoning effort is set to an empty string? → Treat as unset; omit from the provider request so the provider uses its default behavior.
- How does this interact with non-Copilot providers (e.g., Azure OpenAI)? → Reasoning level selection is scoped to the Copilot provider only. Other providers remain unchanged.
- What happens when a model's supported reasoning levels change between sessions? → On next model list refresh, the updated levels are displayed. Previously saved preferences that reference removed levels are passed through and handled by the provider.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose each model's supported reasoning levels and default reasoning level in the model listing.
- **FR-002**: The system MUST populate reasoning level data automatically from the AI provider without manual configuration.
- **FR-003**: The system MUST allow users to select a default reasoning level as part of their AI preferences.
- **FR-004**: The system MUST store the selected model and reasoning level as separate, independent values (not as a composite identifier).
- **FR-005**: The system MUST pass the user's selected reasoning effort through to the AI provider when creating a session.
- **FR-006**: The system MUST resolve reasoning effort using this precedence: pipeline agent config → user settings → model default → empty (provider default).
- **FR-007**: The system MUST expand reasoning-capable models into per-level variants in all model selection dropdowns (Settings and Pipeline editor).
- **FR-008**: The system MUST display a visual indicator (reasoning badge) on model variants to communicate the reasoning level.
- **FR-009**: The system MUST visually highlight the model's default reasoning level among its variants.
- **FR-010**: The system MUST display models without reasoning support unchanged — no badges, no suffixes, no expansion.
- **FR-011**: The system MUST support configuring reasoning effort independently per pipeline agent node.
- **FR-012**: The system MUST keep the API contract (schema) in sync with the new reasoning fields.
- **FR-013**: The system MUST maintain backwards compatibility — existing users with no reasoning preference MUST experience no change in behavior.

### Key Entities

- **Model**: An AI model available for use; gains metadata about supported reasoning levels and a default reasoning level.
- **AI Preferences**: User-level AI configuration; gains a reasoning effort field for the user's default reasoning intensity.
- **Pipeline Agent Node**: Per-agent configuration within a pipeline; gains a reasoning effort setting alongside the model selection.
- **Model Variant**: A frontend display concept where a single reasoning-capable model is expanded into multiple selectable entries, one per supported reasoning level.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can see reasoning level options for all reasoning-capable models within the model selection interface.
- **SC-002**: Users can select a reasoning level and have it persist across sessions without re-selection.
- **SC-003**: Selecting a reasoning model variant in Settings results in the AI provider receiving the correct reasoning effort for subsequent interactions.
- **SC-004**: Pipeline agents configured with different reasoning levels produce interactions that reflect their individual reasoning configurations.
- **SC-005**: Models without reasoning support display identically to their current presentation — no visual changes, no additional UI elements.
- **SC-006**: The model and reasoning level are stored as separate fields, ensuring no parsing is needed and backwards compatibility is maintained.
- **SC-007**: The API contract between frontend and backend remains valid and in sync after the changes.
- **SC-008**: 100% of existing automated tests continue to pass after the changes (no regressions).
- **SC-009**: Users can complete the reasoning level selection workflow (open dropdown → see variants → select → save) in under 10 seconds.

## Assumptions

- The AI provider already returns reasoning level metadata (supported levels and default level) for each model. No provider changes are needed.
- Reasoning effort values are string identifiers (e.g., "low", "medium", "high", "xhigh") defined by the AI provider.
- The Copilot provider is the only provider that currently supports reasoning levels. Other providers will be extended separately if/when they gain support.
- The display format for reasoning variants follows the pattern "ModelName (Level)" (e.g., "o3 (High)") with capitalized level names for user-friendliness.
- Empty or unset reasoning effort is semantically equivalent to "use the provider's default behavior."
- The precedence chain (pipeline config → user settings → model default → empty) is consistent with how model selection already works in the system.
