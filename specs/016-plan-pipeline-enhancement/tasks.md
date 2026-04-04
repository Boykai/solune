# Tasks: Full-Stack Plan Pipeline Enhancement

**Input**: Design documents from `/specs/016-plan-pipeline-enhancement/` and `/specs/017-plan-pipeline-enhancement/`
**Prerequisites**: plan.md (loaded), spec.md (loaded), research.md (loaded), data-model.md (loaded), contracts/ (loaded), quickstart.md (loaded)

**Tests**: Tests ARE requested — the specification explicitly mandates backend tests (pytest, ≥75% coverage) and frontend tests (Vitest, ≥50% coverage). See plan.md §Constitution Check IV and quickstart.md §Verification Commands.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. User stories map to spec.md priorities: US1 (P1), US2 (P1), US3 (P2), US4 (P2), US5 (P2), US6 (P3), US7 (P3), US8 (P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/src/`, `solune/frontend/src/`
- Backend API routes: `solune/backend/src/api/chat.py`
- Backend models: `solune/backend/src/models/plan.py`
- Backend store: `solune/backend/src/services/chat_store.py`
- Backend prompts: `solune/backend/src/prompts/plan_instructions.py`
- Backend agent: `solune/backend/src/services/chat_agent.py`
- Backend tools: `solune/backend/src/services/agent_tools.py`
- Backend issues: `solune/backend/src/services/plan_issue_service.py`
- Backend migrations: `solune/backend/src/migrations/`
- Frontend UI: `solune/frontend/src/components/chat/`
- Frontend hooks: `solune/frontend/src/hooks/`
- Frontend API: `solune/frontend/src/services/api.ts`
- Frontend types: `solune/frontend/src/types/index.ts`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Database migrations, model definitions, and shared type definitions that ALL user stories depend on

- [ ] T001 Create plan versioning migration in solune/backend/src/migrations/040_plan_versioning.sql — ALTER TABLE chat_plans ADD COLUMN version INTEGER NOT NULL DEFAULT 1; CREATE TABLE chat_plan_versions (version_id TEXT PK, plan_id TEXT FK, version INTEGER, title TEXT, summary TEXT, steps_snapshot TEXT JSON, created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE INDEX idx_plan_versions_plan_id; CREATE UNIQUE INDEX idx_plan_versions_unique ON (plan_id, version)
- [ ] T002 Create step status migration in solune/backend/src/migrations/041_plan_step_status.sql — ALTER TABLE chat_plan_steps ADD COLUMN issue_status TEXT
- [ ] T003 [P] Add version field to Plan model and add PlanVersion model in solune/backend/src/models/plan.py — extend Plan with version: int = 1; add PlanVersion(BaseModel) with version_id, plan_id, version, title, summary, steps_snapshot: list[dict[str, Any]], created_at; add issue_status: str | None = None to PlanStep
- [ ] T004 [P] Add request/response schemas in solune/backend/src/models/plan.py — add StepFeedback(BaseModel) with comment: str (min_length=1, max_length=4096); add StepCreate(BaseModel) with title, description, dependencies, position; add StepUpdate(BaseModel) with optional title, description, dependencies; add StepReorder(BaseModel) with step_ids: list[str]; extend PlanApproveRequest with optional step_ids: list[str] | None = None
- [ ] T005 [P] Add frontend TypeScript types in solune/frontend/src/types/index.ts — add PlanVersion interface; extend PlanStep with issue_status?: string; extend Plan with version: number; add StepFeedbackRequest, StepCreateRequest, StepUpdateRequest, StepReorderRequest, PlanApproveRequest interfaces; add ToolsUsedEvent, ContextGatheredEvent, PlanDiffEvent interfaces

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core backend utilities and store functions that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Create DAG validator utility in solune/backend/src/services/dag_validator.py — implement validate_step_dag(steps: list[PlanStep]) -> list[str] using Kahn's algorithm (BFS topological sort); return topological order on success; raise ValueError with cycle details on circular dependency; validate all dependency references exist and no self-references
- [ ] T007 Implement version snapshot logic in solune/backend/src/services/chat_store.py — add snapshot_plan_version(plan_id) method that copies current plan state into chat_plan_versions table; add version increment logic to save_plan() that calls snapshot before overwrite; add get_plan_history(plan_id) -> list[PlanVersion] method returning all versions ordered by version DESC
- [ ] T008 [P] Add unit tests for DAG validator in solune/backend/tests/unit/test_dag_validator.py — test valid DAG returns topological order; test circular dependency raises ValueError; test self-reference detection; test invalid dependency reference detection; test empty steps list; test single step with no deps; test linear chain; test diamond dependency pattern
- [ ] T009 [P] Add unit tests for plan versioning in solune/backend/tests/unit/test_plan_store.py — test save_plan increments version; test snapshot_plan_version creates version record; test get_plan_history returns ordered versions; test version starts at 1 for new plans; test steps_snapshot is valid JSON with complete step data

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 — Iterative Plan Refinement with Per-Step Feedback (Priority: P1) 🎯 MVP

**Goal**: Replace the broken "Request Changes" flow with per-step inline feedback that the AI agent uses to regenerate the plan

**Independent Test**: Create a plan → click "Request Changes" → inline comment inputs appear per step → submit feedback → verify the AI agent receives per-step comments and regenerates the plan addressing them

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T010 [P] [US1] Add contract test for POST /plans/{plan_id}/steps/{step_id}/feedback endpoint in solune/backend/tests/unit/test_api_chat.py — test 200 with valid comment; test 404 for missing plan/step; test 409 for non-draft plan; test validation for empty/oversize comment
- [ ] T011 [P] [US1] Add frontend test for refinement sidebar in solune/frontend/tests/src/components/chat/PlanPreview.test.tsx — test "Request Changes" expands inline comment inputs per step; test comment submission calls submitStepFeedback; test comment inputs are cleared after submission

### Implementation for User Story 1

- [ ] T012 [US1] Implement POST /plans/{plan_id}/steps/{step_id}/feedback endpoint in solune/backend/src/api/chat.py — accept StepFeedback request body; validate plan exists, is draft, and step exists; store feedback in agent session state dict state["step_feedback"][step_id] = comment; return {plan_id, step_id, status: "accepted"}
- [ ] T013 [US1] Inject step feedback into agent context in solune/backend/src/services/chat_agent.py — in run_plan_stream(), read state["step_feedback"] dict; format per-step comments into system prompt section; clear state["step_feedback"] after injection so feedback is consumed once
- [ ] T014 [US1] Enhance refinement instructions in solune/backend/src/prompts/plan_instructions.py — update PLAN_SYSTEM_INSTRUCTIONS to include section instructing agent to address per-step feedback comments; add structured refinement suggestion format; instruct agent to note which steps were modified and why
- [ ] T015 [US1] Add submitStepFeedback() client function in solune/frontend/src/services/api.ts — POST /chat/plans/{plan_id}/steps/{step_id}/feedback with {comment} body; return response JSON
- [ ] T016 [US1] Add submitStepFeedback mutation in solune/frontend/src/hooks/usePlan.ts — useMutation wrapping api.submitStepFeedback(); invalidate plan query on success
- [ ] T017 [US1] Implement refinement sidebar UI in solune/frontend/src/components/chat/PlanPreview.tsx — when "Request Changes" is clicked, expand inline comment input (textarea) per step instead of focusing global input; add per-step submit button; call submitStepFeedback mutation for each step with a comment; show loading/success state per step

**Checkpoint**: At this point, users can provide per-step feedback that the AI addresses in regenerated plans

---

## Phase 4: User Story 2 — Plan Versioning and Change Tracking (Priority: P1)

**Goal**: Maintain version history of plan revisions and visually highlight changes (yellow border for modified, green for new) between versions

**Independent Test**: Create a plan → refine it at least once → verify version history is accessible → verify diff highlights correctly show changed (yellow) and new (green) steps

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T018 [P] [US2] Add contract test for GET /plans/{plan_id}/history endpoint in solune/backend/tests/unit/test_api_chat.py — test 200 returns versions array with plan_id, current_version, versions; test 404 for missing plan; test versions contain steps_snapshot
- [ ] T019 [P] [US2] Add frontend test for diff highlights in solune/frontend/tests/src/components/chat/PlanPreview.test.tsx — test changed steps render with yellow border class; test new steps render with green border class; test unchanged steps have no diff border

### Implementation for User Story 2

- [ ] T020 [US2] Implement GET /plans/{plan_id}/history endpoint in solune/backend/src/api/chat.py — call get_plan_history(plan_id); return {plan_id, current_version, versions: list[PlanVersion]}; return 404 if plan not found
- [ ] T021 [US2] Add getPlanHistory() client function in solune/frontend/src/services/api.ts — GET /chat/plans/{plan_id}/history; return typed response with PlanVersion[]
- [ ] T022 [US2] Add usePlanHistory query in solune/frontend/src/hooks/usePlan.ts — useQuery wrapping api.getPlanHistory(); enabled when plan_id is available
- [ ] T023 [US2] Implement diff highlight logic in solune/frontend/src/components/chat/PlanPreview.tsx — compare current steps with previous version's steps_snapshot; compute step-level diff: yellow border (border-yellow-400) for steps whose title/description changed; green border (border-green-400) for steps with new step_ids not in previous version; no border for unchanged steps

**Checkpoint**: At this point, Users can see version history and visual diffs. User Stories 1 AND 2 deliver the complete iterative refinement loop

---

## Phase 5: User Story 3 — Step Management (Add, Edit, Delete, Reorder) (Priority: P2)

**Goal**: Transform the plan from a read-only AI output into an editable, user-owned artifact with full CRUD and drag-and-drop reorder

**Independent Test**: Create a plan → add a new step → edit an existing step inline → delete a step (with confirmation for dependents) → drag-and-drop reorder → verify each operation persists correctly

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T024 [P] [US3] Add contract tests for step CRUD endpoints in solune/backend/tests/unit/test_api_chat.py — test POST /steps returns 201 with new step; test PUT /steps/{id} returns 200 with updated step; test DELETE /steps/{id} returns 200 with affected_steps; test POST /steps/reorder returns 200 with reordered steps; test 404 for missing plan/step; test 409 for non-draft; test 422 for circular deps and invalid refs
- [ ] T025 [P] [US3] Add unit tests for step store functions in solune/backend/tests/unit/test_plan_store.py — test add_step appends and increments version; test update_step modifies fields and increments version; test delete_step cascades dependency removal and compacts positions; test reorder_steps validates all IDs present; test add_step respects 15-step limit
- [ ] T026 [P] [US3] Add frontend test for inline editing and step CRUD in solune/frontend/tests/src/components/chat/PlanPreview.test.tsx — test click on title enters edit mode; test "Add Step" button appends new step; test delete shows confirmation with dependents; test drag-and-drop triggers reorder API call

### Implementation for User Story 3

- [ ] T027 [US3] Implement step CRUD store functions in solune/backend/src/services/chat_store.py — add add_step(plan_id, step_create) with DAG validation, position assignment, version increment+snapshot; add update_step(plan_id, step_id, step_update) with DAG re-validation on dependency changes, version increment+snapshot; add delete_step(plan_id, step_id) with cascade dependency removal, position compaction, version increment+snapshot; add reorder_steps(plan_id, step_ids) with full-list validation, DAG validation, version increment+snapshot; enforce 15-step maximum on add
- [ ] T028 [US3] Implement step CRUD endpoints in solune/backend/src/api/chat.py — POST /chat/plans/{plan_id}/steps (addStep); PUT /chat/plans/{plan_id}/steps/{step_id} (updateStep); DELETE /chat/plans/{plan_id}/steps/{step_id} (deleteStep); POST /chat/plans/{plan_id}/steps/reorder (reorderSteps); all validate draft status, return appropriate HTTP codes per contracts/step-crud.yaml
- [ ] T029 [US3] Update save_plan in solune/backend/src/services/agent_tools.py — ensure save_plan tool call increments version and creates snapshot before overwriting plan data
- [ ] T030 [P] [US3] Add step CRUD client functions in solune/frontend/src/services/api.ts — addStep(plan_id, StepCreateRequest), updateStep(plan_id, step_id, StepUpdateRequest), deleteStep(plan_id, step_id), reorderSteps(plan_id, StepReorderRequest); all return typed responses
- [ ] T031 [US3] Add step CRUD mutations in solune/frontend/src/hooks/usePlan.ts — useMutation for addStep, updateStep, deleteStep, reorderSteps; invalidate plan query on success; handle 422 errors for DAG validation failures with user-friendly messages
- [ ] T032 [US3] Implement inline step editing in solune/frontend/src/components/chat/PlanPreview.tsx — click step title/description to enter inline edit mode (controlled input); blur or Enter to save via updateStep mutation; Escape to cancel edit; "Add Step" button at bottom of step list (disabled at 15 steps with tooltip); delete button per step with confirmation dialog showing dependents
- [ ] T033 [US3] Implement drag-and-drop reorder in solune/frontend/src/components/chat/PlanPreview.tsx — wrap step list in DndContext + SortableContext with verticalListSortingStrategy following ExecutionGroupCard.tsx pattern; each step wrapped in useSortable hook with drag handle; 5px PointerSensor activation distance; onDragEnd calls reorderSteps mutation with new position array; use @dnd-kit/core, @dnd-kit/sortable, @dnd-kit/utilities (already installed)

**Checkpoint**: At this point, users have full step management capabilities. The plan is an editable artifact.

---

## Phase 6: User Story 4 — Dependency Graph Visualization (Priority: P2)

**Goal**: Display a visual dependency graph showing steps as nodes in topological layers with directed edges, and clickable nodes that scroll to the corresponding step

**Independent Test**: Create a plan with step dependencies → view the dependency graph → verify nodes and edges display correctly → click a node → verify it scrolls to the step

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T034 [P] [US4] Add frontend test for PlanDependencyGraph in solune/frontend/tests/src/components/chat/PlanDependencyGraph.test.tsx — test renders SVG with nodes for each step; test renders edges for dependencies; test clicking a node triggers scroll callback; test handles empty dependency list; test handles plan with no steps

### Implementation for User Story 4

- [ ] T035 [US4] Create PlanDependencyGraph component in solune/frontend/src/components/chat/PlanDependencyGraph.tsx — new lightweight custom SVG component; implement Kahn's algorithm (BFS topological sort) to assign steps to layers; render steps as clickable rectangles arranged in topological layers; render dependencies as SVG path elements with bezier curves; onClick node triggers scroll to corresponding step in plan list; handle ≤15 steps; responsive sizing with viewBox
- [ ] T036 [US4] Integrate dependency graph toggle in solune/frontend/src/components/chat/PlanPreview.tsx — add "Show Graph" / "Hide Graph" toggle button; conditionally render PlanDependencyGraph component; pass steps and onNodeClick handler that scrolls to step element via ref

**Checkpoint**: At this point, users can visualize step dependencies in a graph and navigate between graph and step list

---

## Phase 7: User Story 5 — Selective Step Approval (Priority: P2)

**Goal**: Allow users to approve a subset of plan steps, triggering issue creation only for the selected subset while leaving unapproved steps editable

**Independent Test**: Create a plan → select subset of steps via checkboxes → click "Approve Selected" → verify issues created only for selected steps → verify unapproved steps remain editable

### Tests for User Story 5

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T037 [P] [US5] Add contract test for selective approval in solune/backend/tests/unit/test_api_chat.py — test POST /approve with step_ids creates issues only for selected steps; test POST /approve without step_ids approves all (backward-compatible); test 409 for already-approved plan; test 422 for invalid step_ids

### Implementation for User Story 5

- [ ] T038 [US5] Extend approve endpoint in solune/backend/src/api/chat.py — modify approve_plan_endpoint to accept optional PlanApproveRequest body with step_ids; pass step_ids filter to plan_issue_service
- [ ] T039 [US5] Update plan issue service in solune/backend/src/services/plan_issue_service.py — modify create_plan_issues() to accept optional step_ids filter; when step_ids provided, create issues only for matching steps; when step_ids is None, create issues for all steps (existing behavior)
- [ ] T040 [P] [US5] Add approvePlan client function in solune/frontend/src/services/api.ts — POST /chat/plans/{plan_id}/approve with optional {step_ids} body; return typed PlanApprovalResponse
- [ ] T041 [US5] Add approvePlan mutation in solune/frontend/src/hooks/usePlan.ts — useMutation wrapping api.approvePlan(); invalidate plan query on success
- [ ] T042 [US5] Implement per-step checkboxes and selective approval UI in solune/frontend/src/components/chat/PlanPreview.tsx — add checkbox per step for selection; "Approve Selected" button (enabled when ≥1 step selected) calls approvePlan with selected step_ids; "Approve All" retains existing behavior (no step_ids); approved steps visually distinguished (e.g., opacity, badge, or border)

**Checkpoint**: At this point, users can incrementally approve steps. Combined with US3 (step CRUD), this enables a fully interactive planning workflow.

---

## Phase 8: User Story 6 — Plan Export (Priority: P3)

**Goal**: Allow users to export the plan as a downloadable Markdown file or copy it to clipboard

**Independent Test**: Create a plan → click "Export as Markdown" → verify downloaded .md file contains formatted plan → click "Copy to clipboard" → paste and verify Markdown content

### Tests for User Story 6

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T043 [P] [US6] Add contract test for GET /plans/{plan_id}/export?format=markdown in solune/backend/tests/unit/test_api_chat.py — test 200 returns text/markdown content type; test response contains plan title, summary, and step details; test 404 for missing plan

### Implementation for User Story 6

- [ ] T044 [US6] Implement format_plan_as_markdown utility in solune/backend/src/services/chat_store.py — function that takes a plan dict and returns a structured Markdown string with title, summary, numbered step checklist with dependency annotations, and metadata footer
- [ ] T045 [US6] Implement GET /plans/{plan_id}/export endpoint in solune/backend/src/api/chat.py — accept format query param (default: markdown); call format_plan_as_markdown(); return Response with media_type="text/markdown"
- [ ] T046 [P] [US6] Add exportPlan client function in solune/frontend/src/services/api.ts — GET /chat/plans/{plan_id}/export?format=markdown; return raw text response
- [ ] T047 [US6] Add export actions in solune/frontend/src/components/chat/PlanPreview.tsx — "Export as Markdown" button triggers file download of .md content; "Copy to clipboard" button copies Markdown text via navigator.clipboard.writeText() with success toast notification

**Checkpoint**: At this point, users can share plans externally via Markdown export

---

## Phase 9: User Story 7 — Progress Tracking with Board Sync (Priority: P3)

**Goal**: After step approval, poll GitHub issue statuses and display a progress bar ("X/Y issues completed") at the top of the plan view

**Independent Test**: Approve steps → simulate issue status changes → verify progress bar updates → verify individual step status badges reflect current issue state

### Tests for User Story 7

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T048 [P] [US7] Add unit test for issue status sync in solune/backend/tests/unit/test_plan_store.py — test update_step_issue_status updates issue_status column; test get_plan returns steps with issue_status populated
- [ ] T049 [P] [US7] Add frontend test for progress bar in solune/frontend/tests/src/components/chat/PlanPreview.test.tsx — test progress bar renders "X/Y issues completed"; test progress bar shows 100% when all complete; test progress bar hidden when no approved steps

### Implementation for User Story 7

- [ ] T050 [US7] Implement issue status sync in solune/backend/src/services/chat_store.py — add update_step_issue_statuses(plan_id, statuses: dict[str, str]) method; bulk update issue_status for steps by step_id
- [ ] T051 [US7] Add sync-status endpoint or extend GET /plans/{plan_id} in solune/backend/src/api/chat.py — when plan has approved steps with issue_numbers, query GitHub issue states in bulk; update issue_status in chat_plan_steps; return updated plan data
- [ ] T052 [US7] Implement progress bar in solune/frontend/src/components/chat/PlanPreview.tsx — at top of plan view, compute completed/total from steps with issue_status; render "X/Y issues completed" progress bar; show individual step status badges (open, closed) next to approved steps
- [ ] T053 [US7] Add polling logic in solune/frontend/src/hooks/usePlan.ts — when plan status is "approved" and view is active, poll plan data every 30 seconds via useQuery refetchInterval; stop polling when all issues are completed or component unmounts

**Checkpoint**: At this point, the plan view is a living dashboard tracking execution progress

---

## Phase 10: User Story 8 — Enhanced Thinking Indicator (Priority: P3)

**Goal**: Replace the simple spinner with streaming breadcrumbs and collapsible tool call details during plan generation

**Independent Test**: Initiate plan generation → observe thinking indicator → verify breadcrumbs show current phase → verify tool call details appear in collapsible panels

### Tests for User Story 8

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T054 [P] [US8] Add frontend test for ThinkingIndicator v2 in solune/frontend/tests/src/components/chat/ThinkingIndicator.test.tsx — test breadcrumbs render phase names; test tool usage events render tool name; test collapsible detail panel expands/collapses

### Implementation for User Story 8

- [ ] T055 [US8] Emit richer SSE events in solune/backend/src/services/chat_agent.py — emit tools_used event after each tool call with {tool_name, duration_ms}; emit context_gathered event after research phase with {sources: string[]}; emit plan_diff event after refinement with {added, removed, changed} step IDs
- [ ] T056 [US8] Enhance ThinkingIndicator component in solune/frontend/src/components/chat/ThinkingIndicator.tsx — display streaming breadcrumbs showing current phase (researching → planning → refining); render tool usage as breadcrumb items with tool name; add collapsible detail panel per tool call showing duration and results; handle new SSE event types (tools_used, context_gathered, plan_diff)

**Checkpoint**: All user stories are now independently functional

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T057 [P] Run full backend test suite and ensure ≥75% coverage: cd solune/backend && uv run pytest tests/unit/ --cov=src --cov-report=term-missing --cov-fail-under=75
- [ ] T058 [P] Run full frontend test suite and ensure ≥50% coverage: cd solune/frontend && npm run test:coverage
- [ ] T059 [P] Run frontend lint and type check: cd solune/frontend && npm run lint -- --quiet && npx tsc --noEmit
- [ ] T060 Validate contracts match implementation: run validate-contracts.sh to ensure OpenAPI specs and TypeScript types are in sync
- [ ] T061 Run quickstart.md walkthrough for manual E2E validation — follow Phase 1 (refinement loop), Phase 2 (step CRUD), Phase 3 (export, progress) scenarios
- [ ] T062 [P] Code cleanup — remove any TODO/FIXME markers, ensure consistent error handling patterns across new endpoints, verify all new imports are used

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) — migrations and models must exist — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational (Phase 2) — feedback endpoint needs models + store
- **US2 (Phase 4)**: Depends on Foundational (Phase 2) — versioning frontend needs history endpoint + snapshot logic
- **US3 (Phase 5)**: Depends on Foundational (Phase 2) — step CRUD needs DAG validator + version increment
- **US4 (Phase 6)**: Depends on US3 (Phase 5) — graph needs step data with dependencies from CRUD
- **US5 (Phase 7)**: Depends on US3 (Phase 5) — selective approval needs inline editing context
- **US6 (Phase 8)**: Depends on Foundational (Phase 2) — export reads plan data (no CRUD dependency)
- **US7 (Phase 9)**: Depends on US5 (Phase 7) — board sync needs approved steps with issue numbers
- **US8 (Phase 10)**: No story dependencies — SSE events are independent (but Foundational phase must be complete)
- **Polish (Phase 11)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — No dependencies on other stories
- **US2 (P1)**: Can start after Foundational — No dependencies on other stories (parallel with US1)
- **US3 (P2)**: Can start after Foundational — No dependencies on other stories (parallel with US1, US2)
- **US4 (P2)**: Depends on US3 — needs step CRUD for dependency editing
- **US5 (P2)**: Depends on US3 — needs inline editing context; extends approval endpoint
- **US6 (P3)**: Can start after Foundational — reads plan data only (parallel with US1–US3)
- **US7 (P3)**: Depends on US5 — needs approved steps with issue numbers for status polling
- **US8 (P3)**: Can start after Foundational — SSE events are independent (parallel with US1–US3)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Backend models/store before API endpoints
- API endpoints before frontend client functions
- Client functions before hooks
- Hooks before UI components
- Core implementation before integration

### Parallel Opportunities

- **Phase 1**: T001 + T002 can run in parallel (different migrations modifying different tables), and T003 + T004 + T005 can run in parallel (different files)
- **Phase 2**: T006 + T007 are sequential (store depends on validator), but T008 + T009 can run in parallel with each other (test files)
- **US1 + US2 + US3 + US6 + US8**: Can all start in parallel after Foundational phase (different files, independent stories)
- **Within each story**: All tests marked [P] can run in parallel; all client functions marked [P] can run in parallel
- **US4 + US5**: Can run in parallel after US3 completes (different files)
- **US7**: Must wait for US5

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for POST feedback endpoint in solune/backend/tests/unit/test_api_chat.py"
Task: "Frontend test for refinement sidebar in solune/frontend/tests/src/components/chat/PlanPreview.test.tsx"

# Then implement backend in sequence:
Task: "Implement feedback endpoint in solune/backend/src/api/chat.py"
Task: "Inject feedback in solune/backend/src/services/chat_agent.py"
Task: "Enhance refinement instructions in solune/backend/src/prompts/plan_instructions.py"

# Frontend can start in parallel with backend (different files):
Task: "Add submitStepFeedback client in solune/frontend/src/services/api.ts"
Task: "Add submitStepFeedback mutation in solune/frontend/src/hooks/usePlan.ts"
Task: "Implement refinement sidebar UI in solune/frontend/src/components/chat/PlanPreview.tsx"
```

## Parallel Example: User Story 3

```bash
# Launch all tests together:
Task: "Contract tests for step CRUD in solune/backend/tests/unit/test_api_chat.py"
Task: "Unit tests for step store in solune/backend/tests/unit/test_plan_store.py"
Task: "Frontend test for inline editing in solune/frontend/tests/src/components/chat/PlanPreview.test.tsx"

# Backend store then endpoints (sequential):
Task: "Step CRUD store functions in solune/backend/src/services/chat_store.py"
Task: "Step CRUD endpoints in solune/backend/src/api/chat.py"
Task: "Update save_plan in solune/backend/src/services/agent_tools.py"

# Frontend client then hooks then UI (sequential, but parallel with backend):
Task: "Step CRUD client functions in solune/frontend/src/services/api.ts"
Task: "Step CRUD mutations in solune/frontend/src/hooks/usePlan.ts"
Task: "Inline editing UI in solune/frontend/src/components/chat/PlanPreview.tsx"
Task: "Drag-and-drop reorder in solune/frontend/src/components/chat/PlanPreview.tsx"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup (migrations, models, types)
2. Complete Phase 2: Foundational (DAG validator, versioning store, tests)
3. Complete Phase 3: User Story 1 — Per-step feedback (the core pain-point fix)
4. Complete Phase 4: User Story 2 — Versioning + diff highlights
5. **STOP and VALIDATE**: Test the iterative refinement loop end-to-end
6. Deploy/demo if ready — this alone fixes the broken refinement workflow

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add US1 (per-step feedback) → Test independently → Deploy (MVP!)
3. Add US2 (versioning + diffs) → Test independently → Deploy (Refinement loop complete)
4. Add US3 (step CRUD + DnD) → Test independently → Deploy (Editable plans)
5. Add US4 (dependency graph) → Test independently → Deploy (Visual dependencies)
6. Add US5 (selective approval) → Test independently → Deploy (Incremental approval)
7. Add US6 (export) → Test independently → Deploy (Shareable plans)
8. Add US7 (board sync) → Test independently → Deploy (Progress tracking)
9. Add US8 (thinking indicator) → Test independently → Deploy (Polish)

### Parallel Team Strategy

With multiple developers after Foundational phase:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 (feedback) + US2 (versioning) — P1 stories
   - Developer B: US3 (step CRUD) — P2 story, then US4 (graph) + US5 (approval)
   - Developer C: US6 (export) + US8 (thinking indicator) — independent P3 stories
3. After US5 completes: Developer C picks up US7 (board sync)
4. Stories complete and integrate independently

### Suggested Implementation Order (from plan.md)

Per the plan's suggested order optimized for unblocking:

1. **T015–T017** (US1 frontend sidebar) — immediate pain-point fix, no backend dep needed for UI shell
2. **T001–T009** (Setup + Foundational) — backend versioning + DAG
3. **T010–T014** (US1 backend) — completes the feedback loop
4. **T018–T023** (US2) — diff highlighting connects frontend + backend refinement
5. **T024–T033** (US3) — step CRUD + DnD
6. **T034–T036** (US4) — dependency graph
7. **T037–T042** (US5) — selective approval
8. **T043–T056** (US6–US8) — Phase 3 polish

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Max 15 plan steps enforced — "Add Step" disabled at limit
- DAG validation on every dependency-modifying mutation
- Version increment + snapshot on every plan-modifying operation
- Feedback is transient — consumed once per refinement cycle, then cleared
- @dnd-kit patterns from ExecutionGroupCard.tsx should be followed exactly
- Custom SVG graph — no new npm dependencies
- Polling at 30s intervals for board sync — stop when all issues complete
