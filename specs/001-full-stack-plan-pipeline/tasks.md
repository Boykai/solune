# Tasks: Full-Stack Plan Pipeline Enhancement (v2 — Copilot SDK + MAF)

**Input**: Design documents from `/specs/001-full-stack-plan-pipeline/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Included — spec P1 acceptance criteria require SDK hook verification, DAG validation in P3 requires unit tests for cycle detection, and existing coverage threshold (≥75%) must be maintained.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `solune/backend/src/`
- **Frontend**: `solune/frontend/src/`
- **Migrations**: `solune/backend/src/migrations/`
- **Backend tests**: `solune/backend/tests/unit/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: SDK upgrade and database schema migrations required by all user stories

- [x] T001 Upgrade `copilot-sdk>=1.0.17` (replace `github-copilot-sdk>=0.1.30,<1`) in solune/backend/pyproject.toml
- [x] T002 [P] Create migration 040_plan_versioning.sql adding `version` column to `chat_plans` and `chat_plan_versions` table in solune/backend/src/migrations/040_plan_versioning.sql
- [x] T003 [P] Create migration 041_plan_step_status.sql adding `approval_status` column to `chat_plan_steps` in solune/backend/src/migrations/041_plan_step_status.sql

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core model extensions and store methods that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Add `version: int` field (default 1) to Plan model in solune/backend/src/models/plan.py
- [x] T005 [P] Add PlanVersion model (version_id, plan_id, version, title, summary, steps_json, created_at) in solune/backend/src/models/plan.py
- [x] T006 [P] Add StepApprovalStatus enum (`pending`/`approved`/`rejected`) and `approval_status` field to PlanStep model in solune/backend/src/models/plan.py
- [x] T007 Implement `snapshot_plan_version()` to save current plan state to `chat_plan_versions` in solune/backend/src/services/chat_store.py
- [x] T008 [P] Implement `get_plan_versions()` to query version history for a plan in solune/backend/src/services/chat_store.py
- [x] T009 [P] Add v2 types (PlanVersion, StepApprovalStatus, StepCreateRequest, StepUpdateRequest, StepReorderRequest, StepApprovalRequest, StepFeedbackRequest/Response, enhanced SSE event types, DependencyGraph types) to solune/frontend/src/types/index.ts

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 — SDK Agent Orchestration Layer (Priority: P1) 🎯 MVP

**Goal**: Replace `is_plan_mode` flag-based switching with dedicated Copilot SDK custom agent sessions, session hooks for automatic plan versioning, sub-agent pipeline orchestration, and enhanced SSE streaming mapped from SDK events.

**Independent Test**: Create a plan session with custom agents, verify tool whitelist enforcement, confirm hook fires on `save_plan`, verify SDK events map to SSE

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T010 [P] [US1] Create unit tests for plan agent profiles, create_plan_session(), and session hooks in solune/backend/tests/unit/test_plan_agent_provider.py
- [x] T011 [P] [US1] Create unit tests for pipeline orchestrator stage sequencing, parallel groups, and sub-agent event handling in solune/backend/tests/unit/test_pipeline_orchestrator.py

### Implementation for User Story 1

#### Step 0A: Upgrade SDK + Define Plan Agent Profile

- [x] T012 [P] [US1] Define PLAN_AGENT_PROFILE (name: `solune-plan`, tool whitelist: `get_project_context`, `get_pipeline_list`, `save_plan`, PLAN_SYSTEM_INSTRUCTIONS prompt) and SPECKIT_AGENT_PROFILES for each pipeline stage in solune/backend/src/services/plan_agent_provider.py
- [x] T013 [US1] Implement `create_plan_session()` factory wrapping `CopilotClient.create_session(custom_agents=[...])` in solune/backend/src/services/plan_agent_provider.py
- [x] T014 [US1] Update `create_agent()` to route plan mode to SDK custom agent sessions via `create_plan_session()` in solune/backend/src/services/agent_provider.py

#### Step 0B: Session Hooks for Plan Versioning

- [x] T015 [US1] Register `on_pre_tool_use` hook: when `toolName == "save_plan"`, call `snapshot_plan_version()` to save current plan state in solune/backend/src/services/plan_agent_provider.py
- [x] T016 [US1] Register `on_post_tool_use` hook: after `save_plan` completes, emit `plan_diff` delta as SSE event in solune/backend/src/services/plan_agent_provider.py

#### Step 0C: Sub-Agent Pipeline Orchestrator

- [x] T017 [US1] Create pipeline_orchestrator.py: sequence speckit agents via SDK sessions, listen for `subagent.completed/failed` to drive stage transitions, support parallel groups via `asyncio.gather()`, emit `stage_started/completed/failed` SSE events in solune/backend/src/services/pipeline_orchestrator.py
- [x] T018 [US1] Wire pipeline orchestrator into chat_agent.py for pipeline-mode execution in solune/backend/src/services/chat_agent.py

#### Step 0D: Streaming Event Upgrade

- [x] T019 [US1] Map SDK events to enhanced SSE (`assistant.reasoning_delta` → `reasoning`, `tool.execution_start` → `tool_start`, `assistant.intent` → enhanced `thinking`, `subagent.*` → `stage_*`) preserving backward compatibility in solune/backend/src/services/chat_agent.py
- [x] T020 [US1] Update completion_providers.py for SDK v1.0.17 compatibility in solune/backend/src/services/completion_providers.py

#### Frontend: Enhanced Thinking + Streaming

- [x] T021 [P] [US1] Update ThinkingIndicator.tsx to handle new event types (`reasoning`, `tool_start`, `stage_started/completed/failed`) with progressive disclosure in solune/frontend/src/components/chat/ThinkingIndicator.tsx
- [x] T022 [US1] Add reasoning stream display and pipeline stage progress bar driven by `stage_*` events in solune/frontend/src/components/chat/PlanPreview.tsx

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently — plan mode uses dedicated SDK custom agents with tool whitelists, session hooks auto-snapshot versions, pipeline orchestrator drives stage transitions, and enhanced SSE events stream to the frontend.

---

## Phase 4: User Story 2 — Plan Versioning and Iterative Refinement (Priority: P2)

**Goal**: Automatic version snapshots on every save, plan version history with diff rendering, step-level feedback via SDK elicitation, and guided refinement prompts.

**Independent Test**: Save a plan twice, verify two version snapshots exist in history; submit step feedback and confirm agent receives structured feedback via elicitation handler.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T023 [P] [US2] Add plan versioning unit tests (snapshot creation, version increment, get_plan_versions ordering) to solune/backend/tests/unit/test_plan_store.py
- [x] T024 [P] [US2] Add history and feedback endpoint tests (GET /plans/{plan_id}/history, POST /plans/{plan_id}/steps/{step_id}/feedback) to solune/backend/tests/unit/test_api_chat.py

### Implementation for User Story 2

#### Backend: History + Feedback Endpoints

- [x] T025 [US2] Implement `GET /plans/{plan_id}/history` endpoint returning version snapshots ordered by version descending in solune/backend/src/api/chat.py
- [x] T026 [P] [US2] Implement `POST /plans/{plan_id}/steps/{step_id}/feedback` endpoint routing feedback to SDK `on_user_input_request` handler in solune/backend/src/api/chat.py

#### Backend: Refinement Prompt

- [x] T027 [US2] Enhance PLAN_SYSTEM_INSTRUCTIONS with version-history awareness (current version number, change summary) and per-step comment injection in solune/backend/src/prompts/plan_instructions.py

#### Frontend: Version History + Feedback UI

- [x] T028 [P] [US2] Add `getPlanHistory()` and `submitStepFeedback()` API calls to solune/frontend/src/services/api.ts
- [x] T029 [P] [US2] Add feedback mutation (`useSubmitStepFeedback`) and version history query (`usePlanHistory`) to solune/frontend/src/hooks/usePlan.ts
- [x] T030 [US2] Add refinement sidebar with "Request Changes" button → inline per-step comment input + handle elicitation SSE events in solune/frontend/src/components/chat/PlanPreview.tsx
- [x] T031 [US2] Implement version selector and client-side diff rendering between version snapshots in solune/frontend/src/components/chat/PlanPreview.tsx

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently — plan versions are automatically tracked, history is viewable with diffs, and step-level feedback flows through SDK elicitation.

---

## Phase 5: User Story 3 — Step CRUD and Dependency Graph (Priority: P3)

**Goal**: Full step mutation capabilities (add/edit/delete/reorder) with DAG validation ensuring no circular dependencies, visual dependency graph, per-step approval, and agent-driven step mutations via `@define_tool`.

**Independent Test**: Create steps with dependencies, verify DAG validation rejects cycles; use agent tools to mutate steps; approve individual steps and verify status tracking.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T032 [P] [US3] Add step CRUD and DAG validation unit tests (add/update/delete step, cycle detection, reorder) to solune/backend/tests/unit/test_plan_store.py
- [x] T033 [P] [US3] Add step CRUD, reorder, and approval endpoint tests (POST/PATCH/DELETE steps, reorder, approve) to solune/backend/tests/unit/test_api_chat.py

### Implementation for User Story 3

#### Backend: Step CRUD Store Methods

- [x] T034 [US3] Implement `add_plan_step()` with position auto-assignment and DAG validation in solune/backend/src/services/chat_store.py
- [x] T035 [P] [US3] Implement `update_plan_step()` with DAG re-validation after update in solune/backend/src/services/chat_store.py
- [x] T036 [P] [US3] Implement `delete_plan_step()` with cascade removal from other steps' dependency lists and position re-indexing in solune/backend/src/services/chat_store.py
- [x] T037 [US3] Implement `validate_dag()` using Kahn's algorithm for topological sort (O(V+E) cycle detection) in solune/backend/src/services/chat_store.py
- [x] T038 [US3] Implement `reorder_plan_steps()` with DAG re-validation in solune/backend/src/services/chat_store.py

#### Backend: Step CRUD API Endpoints

- [x] T039 [US3] Implement `POST /plans/{plan_id}/steps` endpoint (add step, 201 on success, 400 on DAG violation, 409 if not draft) in solune/backend/src/api/chat.py
- [x] T040 [P] [US3] Implement `PATCH /plans/{plan_id}/steps/{step_id}` endpoint (update step, re-validate DAG) in solune/backend/src/api/chat.py
- [x] T041 [P] [US3] Implement `DELETE /plans/{plan_id}/steps/{step_id}` endpoint (delete step, cascade dep removal, 204) in solune/backend/src/api/chat.py
- [x] T042 [US3] Implement `POST /plans/{plan_id}/steps/reorder` endpoint with DAG re-validation in solune/backend/src/api/chat.py
- [x] T043 [US3] Implement `POST /plans/{plan_id}/steps/{step_id}/approve` endpoint for per-step approval status in solune/backend/src/api/chat.py

#### Backend: Agent Tools

- [x] T044 [US3] Register `@define_tool` functions for `add_step`, `edit_step`, `delete_step` applying same CRUD and validation logic in solune/backend/src/services/agent_tools.py

#### Frontend: Step CRUD + Graph UI

- [x] T045 [P] [US3] Add step CRUD (`addStep`, `updateStep`, `deleteStep`), reorder (`reorderSteps`), and approve (`approveStep`) API calls to solune/frontend/src/services/api.ts
- [x] T046 [P] [US3] Add step CRUD mutations (`useAddStep`, `useUpdateStep`, `useDeleteStep`, `useReorderSteps`, `useApproveStep`) with optimistic updates to solune/frontend/src/hooks/usePlan.ts
- [x] T047 [US3] Implement click-to-edit inline editing for step title/description in solune/frontend/src/components/chat/PlanPreview.tsx
- [x] T048 [US3] Implement drag-and-drop step reorder with `@dnd-kit` integration in solune/frontend/src/components/chat/PlanPreview.tsx
- [x] T049 [US3] Add per-step approve/reject UI buttons with approval status visual indicators in solune/frontend/src/components/chat/PlanPreview.tsx
- [x] T050 [US3] Create PlanDependencyGraph.tsx component rendering DAG with step nodes, dependency edges, and approval status visual distinction in solune/frontend/src/components/chat/PlanDependencyGraph.tsx

**Checkpoint**: All core user stories (1–3) should now be independently functional — step CRUD with DAG validation, visual dependency graph, per-step approval, and agent-driven step mutations all work.

---

## Phase 6: User Story 4 (Stretch) — Copilot CLI Plugin and ACP Interop (Priority: P4)

**Goal**: Package plan agents as a Copilot CLI plugin enabling `copilot /plugin install` for CLI-native plan mode, and expose plan pipeline via Agent Client Protocol for IDE integration.

**Independent Test**: Install CLI plugin, create a plan via CLI commands; connect via ACP and verify pipeline access.

### Implementation for User Story 4

- [x] T051 [P] [US4] Create CLI plugin manifest (`plugin.json`) with plan agent metadata in solune/cli-plugin/plugin.json
- [x] T052 [P] [US4] Create plan agent definition for CLI in solune/cli-plugin/agents/solune-plan.agent.md
- [x] T053 [P] [US4] Create plan CRUD skill definition in solune/cli-plugin/skills/plan-crud/SKILL.md
- [x] T054 [P] [US4] Create hook configuration for CLI integration in solune/cli-plugin/hooks/hooks.json
- [x] T055 [P] [US4] Create MCP server configuration for CLI integration in solune/cli-plugin/.mcp.json
- [ ] T056 [US4] Implement optional `--acp` mode exposing plan pipeline via Agent Client Protocol with `ExternalServerConfig(url=...)` for containerized deployments in solune/backend/src/services/plan_agent_provider.py

**Checkpoint**: CLI plugin is installable and ACP server provides integration endpoint for external tools. Depends on Phases 3–5 (US1 + US2 + US3) being complete.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final verification

- [x] T057 [P] Implement `GET /plans/{plan_id}/export?format=markdown|github_issues` endpoint in solune/backend/src/api/chat.py
- [ ] T058 [P] Implement board sync — after plan approval, sync step status changes to project board columns in solune/backend/src/services/chat_store.py
- [ ] T059 Add batch operations (select multiple steps → bulk approve/reject/delete, bulk dependency assignment) to solune/backend/src/api/chat.py
- [ ] T060 [P] Run backend coverage validation: `cd solune/backend && uv run pytest tests/unit/ --cov=src --cov-fail-under=75`
- [ ] T061 [P] Run frontend lint and type check: `cd solune/frontend && npm run lint -- --quiet && npx tsc --noEmit`
- [ ] T062 [P] Run frontend component tests: `cd solune/frontend && npm test -- --run PlanPreview.test.tsx usePlan.test.tsx PlanDependencyGraph.test.tsx`
- [ ] T063 Run quickstart.md validation against implemented features

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational phase completion — **MVP target**
- **US2 (Phase 4)**: Depends on Foundational phase completion — can run in parallel with US1
- **US3 (Phase 5)**: Depends on Foundational phase completion — can run in parallel with US1 and US2
- **US4 (Phase 6)**: Depends on US1 (Phase 3) + US2 (Phase 4) + US3 (Phase 5) — stretch goal
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories. Requires `copilot-sdk>=1.0.17` from Setup.
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) — Independently testable. Session hooks from US1 enhance automatic snapshotting, but versioning works via store methods alone.
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) — Independently testable. Agent-driven step mutations (T044) benefit from US1's `@define_tool` framework but can be tested independently.
- **User Story 4 (P4, stretch)**: Depends on US1 + US2 + US3 being complete — CLI plugin wraps the entire plan pipeline.

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services (covered in Foundational)
- Store methods before API endpoints
- Backend before frontend
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- **Setup**: T002 and T003 can run in parallel (different migration files)
- **Foundational**: T005, T006, T008, T009 can run in parallel (different files/methods)
- **US1**: T010 + T011 tests in parallel; T012 in parallel with other setup; T021 frontend in parallel with backend
- **US2**: T023 + T024 tests in parallel; T025 + T026 endpoints in parallel; T028 + T029 frontend in parallel
- **US3**: T032 + T033 tests in parallel; T035 + T036 store methods in parallel; T040 + T041 endpoints in parallel; T045 + T046 frontend in parallel
- **US4**: T051–T055 all in parallel (independent files)
- **Cross-story**: Once Foundational is complete, US1, US2, and US3 can proceed in parallel by different developers

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: T010 "Unit tests for plan agent provider in tests/unit/test_plan_agent_provider.py"
Task: T011 "Unit tests for pipeline orchestrator in tests/unit/test_pipeline_orchestrator.py"

# Launch parallel implementation tasks (different files):
Task: T012 "Define agent profiles in plan_agent_provider.py"
Task: T020 "Update completion_providers.py for SDK v1.0.17"
Task: T021 "Update ThinkingIndicator.tsx for v2 events"
```

## Parallel Example: User Story 3

```bash
# Launch all tests for User Story 3 together:
Task: T032 "Step CRUD and DAG validation tests in test_plan_store.py"
Task: T033 "Step CRUD endpoint tests in test_api_chat.py"

# Launch parallel endpoint implementations (different endpoints, same file — apply sequentially):
Task: T040 "Implement PATCH /plans/{plan_id}/steps/{step_id} endpoint"
Task: T041 "Implement DELETE /plans/{plan_id}/steps/{step_id} endpoint"

# Launch parallel frontend tasks (different files):
Task: T045 "Add step CRUD API calls to api.ts"
Task: T046 "Add step CRUD mutations to usePlan.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T009) — CRITICAL, blocks all stories
3. Complete Phase 3: User Story 1 (T010–T022)
4. **STOP and VALIDATE**: Test User Story 1 independently
   - `uv run pytest tests/unit/test_plan_agent_provider.py tests/unit/test_pipeline_orchestrator.py`
   - Verify SDK custom agent session creates with tool whitelist
   - Verify session hooks fire on `save_plan`
   - Verify enhanced SSE events stream to frontend
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (**MVP!**)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Add User Story 4 (stretch) → Test independently → Deploy/Demo
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (SDK Agent Orchestration)
   - Developer B: User Story 2 (Plan Versioning + Refinement)
   - Developer C: User Story 3 (Step CRUD + Dependency Graph)
3. Stories complete and integrate independently
4. Developer A or B: User Story 4 (CLI Plugin — stretch, after US1–US3 merge)

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Backward compatibility: no breaking changes to existing `/plans/{plan_id}` GET/PATCH/approve/exit endpoints
- SDK pin: `copilot-sdk>=1.0.17` — latest public preview, Python 3.11+ required (project uses 3.12+)
- Wrap all SDK calls behind `agent_provider.py` / `plan_agent_provider.py` to absorb breaking SDK changes
