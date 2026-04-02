# Tasks: Model Reasoning Level Selection

**Input**: Design documents from `/specs/545-model-reasoning-selection/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included — the feature specification explicitly requests backend unit tests, frontend unit tests, and contract validation (Phase 4 in plan).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/src/`, `solune/frontend/src/`
- Backend tests: `solune/backend/tests/unit/`
- Frontend tests: co-located with source (e.g., `useModels.test.tsx` next to `useModels.ts`)

---

## Phase 1: Setup

**Purpose**: No new project initialization needed — this feature modifies an existing codebase. All scaffolding, dependencies, and tooling are already in place.

*No tasks in this phase.*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend model changes and frontend type extensions that MUST be complete before ANY user story can be implemented. These entities serve multiple stories.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T001 Add `supported_reasoning_efforts: list[str] | None = None` and `default_reasoning_effort: str | None = None` to ModelOption, and add `reasoning_effort: str = ""` to AIPreferences in solune/backend/src/models/settings.py
- [ ] T002 [P] Extend frontend types: add `supported_reasoning_efforts?: string[]`, `default_reasoning_effort?: string | null`, and `reasoning_effort?: string` to AIModel; add `reasoning_effort?: string` to AIPreferences; add `reasoningEffort?: string` to PipelineModelOverride in solune/frontend/src/types/index.ts
- [ ] T003 [P] Add `Brain` icon re-export from lucide-react in solune/frontend/src/lib/icons.ts

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — View Available Reasoning Levels for Models (Priority: P1) 🎯 MVP

**Goal**: Users can see which reasoning levels each model supports when browsing the model list. Reasoning-capable models display supported levels and a default; non-reasoning models appear unchanged.

**Independent Test**: View the model list and verify reasoning-capable models show supported reasoning levels with a visual badge, while non-reasoning models appear unchanged.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T004 [P] [US1] Add test verifying ModelOption serializes reasoning fields and mock `list_models` returns models with reasoning efforts in solune/backend/tests/unit/test_model_fetcher.py
- [ ] T005 [P] [US1] Add test verifying `useModels()` expansion logic: reasoning-capable models expand into N variants with display name `{name} ({Level})` and `reasoning_effort` field; non-reasoning models pass through unchanged in solune/frontend/src/hooks/useModels.test.tsx
- [ ] T006 [P] [US1] Add test verifying ReasoningBadge renders correct color and icon per level, highlights model default, and does not render for non-reasoning models in solune/frontend/src/components/pipeline/ModelSelector.test.tsx

### Implementation for User Story 1

- [ ] T007 [US1] Populate `supported_reasoning_efforts` and `default_reasoning_effort` from SDK Model dataclass using `getattr()` pattern in `GitHubCopilotModelFetcher.fetch_models()` loop in solune/backend/src/services/model_fetcher.py
- [ ] T008 [US1] Update `modelsApi.list()` response mapper to include `supported_reasoning_efforts` and `default_reasoning_effort` fields in solune/frontend/src/services/api.ts
- [ ] T009 [US1] Add reasoning model expansion logic in `useModels()` hook: for each model with `supported_reasoning_efforts`, generate N `AIModel` variants with `name: "{name} ({Level})"` and `reasoning_effort` set; non-reasoning models pass through unchanged in solune/frontend/src/hooks/useModels.ts
- [ ] T010 [US1] Add `ReasoningBadge` component (modeled after existing `CostTierBadge`) with Brain icon and color-coded pill (teal=low, sky=medium, amber=high, purple=xhigh) and integrate into `ModelRow` in solune/frontend/src/components/pipeline/ModelSelector.tsx

**Checkpoint**: At this point, User Story 1 should be fully functional — model list displays reasoning variants with badges

---

## Phase 4: User Story 2 — Select a Reasoning Level in Chat Settings (Priority: P1)

**Goal**: Users can choose a default reasoning level from the Settings page model dropdown. Reasoning-capable models appear as expanded variants (e.g., "o3 (High)"). Selection saves model and reasoning_effort as separate fields.

**Independent Test**: Navigate to Settings, open model dropdown, verify reasoning variants appear, select one, save, and confirm `reasoning_effort` is stored separately in AIPreferences.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T011 [P] [US2] Add test verifying settings form saves `reasoning_effort` as a separate field when a reasoning model variant is selected in solune/frontend/src/components/settings/PrimarySettings.test.tsx

### Implementation for User Story 2

- [ ] T012 [US2] Update DynamicDropdown to display reasoning-expanded model variants (reuses expansion from `useModels()`) in solune/frontend/src/components/settings/DynamicDropdown.tsx
- [ ] T013 [US2] Update PrimarySettings to extract and save `reasoning_effort` separately from model ID when user selects a reasoning model variant in solune/frontend/src/components/settings/PrimarySettings.tsx

**Checkpoint**: At this point, User Stories 1 AND 2 should both work — users can view and select reasoning levels in Settings

---

## Phase 5: User Story 3 — Reasoning Effort Applied to AI Responses (Priority: P1)

**Goal**: The user's selected reasoning effort is actually passed to the AI provider when creating a session. The system resolves reasoning effort using precedence: pipeline config → user settings → model default → empty (provider default).

**Independent Test**: Select a high reasoning level, send a chat message, and verify (through backend logs or test mocks) that `reasoning_effort` is included in the SessionConfig sent to the AI provider.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T014 [P] [US3] Add test verifying `CopilotCompletionProvider.complete()` includes `reasoning_effort` in SessionConfig when provided, and omits it when empty in solune/backend/tests/unit/test_completion_providers.py
- [ ] T015 [P] [US3] Add test verifying `_resolve_effective_model()` returns correct reasoning_effort using precedence chain (pipeline config → user settings → model default → empty) in solune/backend/tests/unit/test_orchestrator.py

### Implementation for User Story 3

- [ ] T016 [US3] Add optional `reasoning_effort: str = ""` parameter to `CopilotCompletionProvider.complete()` and include in `SessionConfig` dict when non-empty in solune/backend/src/services/completion_providers.py
- [ ] T017 [P] [US3] Add optional `reasoning_effort: str = ""` parameter to `_create_copilot_agent()` and inject into `GitHubCopilotOptions` dict (with `type: ignore[typeddict-extra-key]`) when non-empty in solune/backend/src/services/agent_provider.py
- [ ] T018 [US3] Extend `_resolve_effective_model()` to also resolve and return `reasoning_effort` alongside model ID, using the same tiered precedence (pipeline config `config["reasoning_effort"]` → user settings `AIPreferences.reasoning_effort` → model default → empty) in solune/backend/src/services/workflow_orchestrator/orchestrator.py

**Checkpoint**: At this point, User Stories 1, 2, and 3 should work end-to-end — selecting a reasoning level in Settings results in the AI provider receiving the correct reasoning effort

---

## Phase 6: User Story 4 — Configure Reasoning Level per Pipeline Agent (Priority: P2)

**Goal**: Pipeline editors can assign a specific reasoning level to each agent node independently, so different pipeline stages can use different reasoning intensities.

**Independent Test**: Open the pipeline editor, select a reasoning model variant for an agent node, save, and verify `reasoning_effort` is stored in the agent node config alongside `model_id`.

### Implementation for User Story 4

- [ ] T019 [US4] Update AgentNode to store `reasoning_effort` alongside `model_id` in agent node config when a reasoning model variant is selected in solune/frontend/src/components/pipeline/AgentNode.tsx
- [ ] T020 [US4] Update PipelineModelDropdown to pass `reasoning_effort` through on model selection (leverages expanded models from `useModels()`) in solune/frontend/src/components/pipeline/PipelineModelDropdown.tsx

**Checkpoint**: All user stories should now be independently functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Schema regeneration, contract validation, and cross-cutting verification

- [ ] T021 Regenerate OpenAPI schema by running `python scripts/export-openapi.py` from solune/backend/
- [ ] T022 Run contract validation via `bash solune/scripts/validate-contracts.sh` to verify OpenAPI + frontend types stay in sync
- [ ] T023 Run full verification suite per solune/specs/545-model-reasoning-selection/quickstart.md: backend pytest, frontend npm test, TypeScript type check, contract validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Skipped — existing project, no initialization needed
- **Foundational (Phase 2)**: No dependencies — can start immediately. BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) completion
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) and User Story 1 (needs `useModels()` expansion logic from T009)
- **User Story 3 (Phase 5)**: Depends on Foundational (Phase 2) only — backend-only changes, independent of frontend stories
- **User Story 4 (Phase 6)**: Depends on Foundational (Phase 2) and User Story 1 (needs `useModels()` expansion and `ReasoningBadge` from T009/T010)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational — no dependencies on other stories
- **User Story 2 (P1)**: Depends on US1 for `useModels()` expansion logic (T009) and model variant display
- **User Story 3 (P1)**: Can start after Foundational — independent of frontend stories. Can run in parallel with US1/US2.
- **User Story 4 (P2)**: Depends on US1 for `useModels()` expansion and `ReasoningBadge` in pipeline selectors

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models/types before services
- Services before endpoints/UI
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 2**: T002 and T003 can run in parallel (different files); T001 must complete first (backend types needed by T002)
- **Phase 3 (US1)**: All three test tasks (T004, T005, T006) can run in parallel
- **Phase 4 (US2)**: T011 can run in parallel with US1 implementation
- **Phase 5 (US3)**: T014 and T015 can run in parallel; T017 can run in parallel with T016; **entire Phase 5 can run in parallel with Phases 3-4** (backend-only)
- **Phase 6 (US4)**: T019 and T020 can run in parallel (different files)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task T004: "Backend test - model fetcher reasoning fields in solune/backend/tests/unit/test_model_fetcher.py"
Task T005: "Frontend test - useModels expansion in solune/frontend/src/hooks/useModels.test.tsx"
Task T006: "Frontend test - ReasoningBadge rendering in solune/frontend/src/components/pipeline/ModelSelector.test.tsx"

# After tests written and failing, launch parallel backend + frontend:
Task T007: "Backend - populate reasoning from SDK in solune/backend/src/services/model_fetcher.py"
Task T008: "Frontend - update API mapper in solune/frontend/src/services/api.ts"
# Then sequential:
Task T009: "Frontend - useModels expansion in solune/frontend/src/hooks/useModels.ts"  (depends on T008)
Task T010: "Frontend - ReasoningBadge in solune/frontend/src/components/pipeline/ModelSelector.tsx"  (depends on T009)
```

## Parallel Example: Backend (US3) alongside Frontend (US1 + US2)

```bash
# These can run in parallel since they touch different codebases:
# Developer A (backend): T014 → T015 → T016 → T017 → T018  (US3 - all backend)
# Developer B (frontend): T005 → T006 → T008 → T009 → T010  (US1 frontend)
# Developer B (continued): T011 → T012 → T013               (US2 frontend)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Foundational (backend models + frontend types + icon)
2. Complete Phase 3: User Story 1 (model list shows reasoning variants with badges)
3. **STOP and VALIDATE**: Verify reasoning-capable models display expanded variants; non-reasoning models unchanged
4. Deploy/demo if ready — users can already see reasoning capabilities

### Incremental Delivery

1. Foundational (Phase 2) → Foundation ready
2. User Story 1 (Phase 3) → Users see reasoning levels → **MVP!**
3. User Story 2 (Phase 4) → Users can select reasoning in Settings
4. User Story 3 (Phase 5) → Reasoning is actually applied to AI sessions (can run in parallel with US1/US2)
5. User Story 4 (Phase 6) → Pipeline agents support per-node reasoning
6. Polish (Phase 7) → Schema + contracts + verification
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Foundational (Phase 2) together
2. Once Foundational is done:
   - Developer A (Backend): User Story 3 (pass-through + resolution)
   - Developer B (Frontend): User Story 1 → User Story 2 → User Story 4
3. Stories complete and integrate independently
4. Converge on Phase 7 (Polish) together

---

## Summary

| Metric | Value |
|--------|-------|
| **Total tasks** | 23 |
| **Foundational** | 3 tasks |
| **User Story 1 (P1)** | 7 tasks (3 tests + 4 implementation) |
| **User Story 2 (P1)** | 3 tasks (1 test + 2 implementation) |
| **User Story 3 (P1)** | 5 tasks (2 tests + 3 implementation) |
| **User Story 4 (P2)** | 2 tasks (implementation only) |
| **Polish** | 3 tasks |
| **Parallel opportunities** | 12 tasks marked [P]; US3 fully parallelizable with US1/US2 |
| **Suggested MVP scope** | Phase 2 + Phase 3 (User Story 1) — 10 tasks |
| **Files modified** | ~15 across backend and frontend |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Empty `reasoning_effort` = API default (backwards compatible)
- Copilot provider only — Azure OpenAI out of scope
