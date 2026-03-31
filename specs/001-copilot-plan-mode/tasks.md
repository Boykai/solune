# Tasks: Copilot-Style Planning Mode (v2)

**Input**: Design documents from `/specs/001-copilot-plan-mode/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/plan-api.md

**Tests**: Not mandated by the specification. Test tasks are omitted per the spec's "Test Optionality with Clarity" principle.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/` under `solune/` repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Database migration for plan tables

- [X] T001 Create plan tables migration in backend/src/migrations/035_chat_plans.sql with chat_plans and chat_plan_steps tables, indices, and foreign keys per data-model.md schema

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models, CRUD operations, and type definitions that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Add PLAN_CREATE = "plan_create" to ActionType enum in backend/src/models/chat.py
- [X] T003 [P] Create Plan and PlanStep Pydantic models with PlanStatus enum (draft, approved, completed, failed), field validation (max lengths, non-negative position), and PlanResponse/PlanStepResponse/PlanApprovalResponse/PlanExitResponse/PlanUpdateRequest response models in backend/src/models/plan.py
- [X] T004 [P] Add plan CRUD functions to backend/src/services/chat_store.py: save_plan(db, plan) inserts/replaces plan + steps in a transaction, get_plan(db, plan_id) returns Plan with steps joined, update_plan(db, plan_id, title, summary) for metadata updates, update_plan_status(db, plan_id, status) for lifecycle transitions, update_plan_step_issue(db, step_id, issue_number, issue_url) for post-approval issue linking — all following existing aiosqlite CRUD patterns with Row factory
- [X] T005 [P] Add Plan, PlanStep, PlanStatus, ThinkingPhase, ThinkingEvent, and PlanCreateActionData types to frontend/src/types/index.ts; add 'plan_create' to ActionType union; add PlanCreateActionData to ActionData union type

**Checkpoint**: Foundation ready — data layer and types are in place for all user stories

---

## Phase 3: User Story 1 — Enter Plan Mode and Create a Plan (Priority: P1) 🎯 MVP

**Goal**: User types `/plan <description>` in a chat with a selected project; the agent researches context, generates a structured plan (title, summary, ordered steps with dependencies), and displays it as a rich preview card.

**Independent Test**: Type `/plan Add a notifications system` in a chat session with a selected project and verify a structured plan appears as a rich preview card with title, summary, steps, and action buttons.

### Implementation for User Story 1

- [X] T006 [P] [US1] Create plan-mode system prompt in backend/src/prompts/plan_instructions.py with build_plan_instructions(project_name, project_id, repo_owner, repo_name, available_statuses) that returns a system prompt instructing the agent to research context, generate a structured plan with title/summary/ordered steps/dependency annotations, and call save_plan when the plan is ready
- [X] T007 [P] [US1] Add save_plan tool function and register_plan_tools() in backend/src/services/agent_tools.py — save_plan accepts plan title, summary, and list of steps (each with title, description, dependencies), calls chat_store.save_plan to persist; register_plan_tools() returns a restricted read-only toolset (get_project_context, get_pipeline_list) plus save_plan
- [X] T008 [US1] Add run_plan() and run_plan_stream() methods to ChatAgentService in backend/src/services/chat_agent.py — run_plan() creates agent with plan system prompt (from plan_instructions.py) and plan tools (from register_plan_tools()), sets is_plan_mode=True and active_plan_id in agent_session.state, processes user message, returns ChatMessage with action_type=plan_create and plan data in action_data; run_plan_stream() yields SSE events (token, tool_call, tool_result, done) during agent execution
- [X] T009 [US1] Add plan mode routes to backend/src/api/chat.py: POST /messages/plan (non-streaming entry point — validates selected project via _resolve_repository(session), extracts description from content, calls run_plan(), returns ChatMessage), POST /messages/plan/stream (SSE streaming entry point — same validation, calls run_plan_stream(), returns EventSourceResponse), GET /plans/{plan_id} (retrieves plan via chat_store.get_plan, returns PlanResponse)
- [X] T010 [P] [US1] Add sendPlanMessageStream() method to frontend/src/services/api.ts that POSTs to /api/v1/chat/messages/plan/stream, processes SSE frames for token/tool_call/tool_result/done/error events (reusing existing SSE parsing logic), and invokes onDone callback with the complete ChatMessage; add getPlan(planId) method that GETs /api/v1/chat/plans/{planId}
- [X] T011 [P] [US1] Create PlanPreview component in frontend/src/components/chat/PlanPreview.tsx — renders plan data from action_data: header with project badge (repo_owner/repo_name) and status badge (Draft/Completed/Failed), ordered step list with titles, descriptions, and dependency annotations; action buttons "Request Changes" (focuses chat input) and "Approve & Create Issues" (disabled until US4)
- [X] T012 [US1] Wire PlanPreview into MessageBubble in frontend/src/components/chat/MessageBubble.tsx — render PlanPreview when action_type === 'plan_create', passing action_data as props
- [X] T013 [US1] Create usePlan hook in frontend/src/hooks/usePlan.ts — manages activePlan (Plan | null), isPlanMode (boolean), thinkingPhase (ThinkingPhase | null) state; exposes setActivePlan, enterPlanMode, exitPlanMode functions; uses React Query for getPlan cache

**Checkpoint**: User Story 1 is fully functional — users can type `/plan <description>` and see a structured plan displayed as a rich preview card

---

## Phase 4: User Story 2 — Iterate and Refine the Plan (Priority: P1)

**Goal**: After initial plan generation, follow-up messages are auto-routed to the plan agent (no `/plan` prefix needed). The agent incorporates feedback and updates the plan in-place, preserving the conversation trail.

**Independent Test**: Generate a plan, then send follow-up refinement messages (e.g., "Split step 3 into two smaller steps") and verify the plan updates in-place while conversation history shows the refinement trail.

### Implementation for User Story 2

- [X] T014 [US2] Add plan mode auto-delegation to existing run() and run_stream() methods in backend/src/services/chat_agent.py — check agent_session.state.get("is_plan_mode"); if True, delegate to run_plan()/run_plan_stream() instead of standard agent processing so follow-up messages are automatically routed without /plan prefix
- [X] T015 [US2] Add PATCH /plans/{plan_id} route to backend/src/api/chat.py — accepts PlanUpdateRequest (optional title, summary), validates plan is in draft status, calls chat_store.update_plan(), returns updated PlanResponse
- [X] T016 [US2] Ensure save_plan tool in backend/src/services/agent_tools.py supports update-in-place — when active_plan_id exists in session state, save_plan updates the existing plan record (via chat_store.save_plan with same plan_id) rather than creating a new one; the agent instruction prompt (plan_instructions.py) should guide the agent to refine the existing plan

**Checkpoint**: User Story 2 is fully functional — follow-up messages auto-route to plan agent, plan updates in-place, and conversation trail is preserved

---

## Phase 5: User Story 3 — Real-Time Thinking Indicators (Priority: P2)

**Goal**: While the agent is processing, users see phase-aware indicators: 🔍 "Researching project context…", 📋 "Drafting implementation plan…", ✏️ "Incorporating your feedback…" — replacing the generic loading animation.

**Independent Test**: Trigger plan mode and observe that phase-specific indicators appear during agent processing, with transitions between researching → planning → refining phases.

### Implementation for User Story 3

- [X] T017 [US3] Add SSE thinking event emission to run_plan_stream() in backend/src/services/chat_agent.py — yield {"event": "thinking", "data": {"phase": "researching"|"planning"|"refining", "detail": "..."}} events before/during agent execution phases: emit "researching" before context gathering, "planning" before plan generation, "refining" when processing follow-up feedback
- [X] T018 [US3] Extend SSE parser in frontend/src/services/api.ts — add handling for event type "thinking" in processFrame/SSE parsing logic; add onThinking callback parameter to sendPlanMessageStream() that receives ThinkingEvent objects; update sendPlanMessageStream to invoke onThinking when thinking frames arrive
- [X] T019 [P] [US3] Create ThinkingIndicator component in frontend/src/components/chat/ThinkingIndicator.tsx — accepts thinkingPhase (ThinkingPhase) and detail (string) props; renders phase-aware labels with icons: Search icon + "Researching project context…" for researching, ListChecks icon + "Drafting implementation plan…" for planning, Pencil icon + "Incorporating your feedback…" for refining; includes animated shimmer/pulse effect using Tailwind CSS
- [X] T020 [US3] Wire ThinkingIndicator into ChatInterface in frontend/src/components/chat/ChatInterface.tsx — replace generic 3-dot bounce loading animation with ThinkingIndicator when thinkingPhase (from usePlan hook) is set; pass thinkingPhase and detail as props; clear thinkingPhase when plan response arrives (done event)

**Checkpoint**: User Story 3 is fully functional — users see real-time phase-aware indicators during plan processing

---

## Phase 6: User Story 4 — Approve Plan and Create GitHub Issues (Priority: P2)

**Goal**: User clicks "Approve & Create Issues" on the plan card. System creates a parent GitHub issue (checklist body) + one sub-issue per step (with dependency references), updates the plan with issue links, and shows completed state with issue badges.

**Independent Test**: Create and approve a plan, then verify a parent issue and sub-issues are created in the target repository with correct titles, descriptions, checklist, dependency references, and linking.

### Implementation for User Story 4

- [X] T021 [US4] Create plan issue service in backend/src/services/plan_issue_service.py — implement create_plan_issues(access_token, plan, owner, repo) that: (1) creates parent GitHub issue via githubkit with plan title as issue title and summary + step checklist as body, (2) sequentially creates one sub-issue per PlanStep with step title as issue title, description + dependency references ("Depends on #N") as body, and "Part of #parent" linking, (3) calls chat_store.update_plan_step_issue() for each step and chat_store.update_plan_status() on completion, (4) handles partial failures by setting status to "failed" and returning created/failed step details per FR-019
- [X] T022 [US4] Add POST /plans/{plan_id}/approve route to backend/src/api/chat.py — validates plan is in draft status with at least one step, sets status to approved, calls plan_issue_service.create_plan_issues(), returns PlanApprovalResponse with issue numbers/URLs; on partial failure returns 502 with created_issues and failed_steps details
- [X] T023 [P] [US4] Add approvePlan(planId) method to frontend/src/services/api.ts — POSTs to /api/v1/chat/plans/{planId}/approve, returns PlanApprovalResponse
- [X] T024 [US4] Add approve mutation to usePlan hook in frontend/src/hooks/usePlan.ts — uses React Query useMutation calling approvePlan(); on success updates activePlan with completed status and issue links; on error surfaces error message
- [X] T025 [US4] Update PlanPreview component in frontend/src/components/chat/PlanPreview.tsx — wire "Approve & Create Issues" button to approve mutation from usePlan hook; show progress spinner during approval; on completion update card to "Completed" status badge; display issue number badges on each step linking to issue_url; show "View Parent Issue" link pointing to parent_issue_url; handle error state with retry option

**Checkpoint**: User Story 4 is fully functional — approved plans create linked GitHub parent issue + sub-issues with dependency references

---

## Phase 7: User Story 5 — Exit Plan Mode (Priority: P3)

**Goal**: User can exit plan mode via "Exit Plan Mode" button (shown after approval) or at any time. Exiting returns the chat to normal operation; the draft plan is preserved.

**Independent Test**: Enter plan mode, then exit and verify subsequent messages are handled by the normal chat agent without plan-mode context.

### Implementation for User Story 5

- [X] T026 [US5] Add POST /plans/{plan_id}/exit route to backend/src/api/chat.py — clears is_plan_mode and active_plan_id from agent session state, returns PlanExitResponse with plan_id and current plan_status; preserves the plan record for future reference
- [X] T027 [P] [US5] Add exitPlanMode(planId) method to frontend/src/services/api.ts — POSTs to /api/v1/chat/plans/{planId}/exit, returns PlanExitResponse
- [X] T028 [US5] Add exit mutation to usePlan hook in frontend/src/hooks/usePlan.ts — uses React Query useMutation calling exitPlanMode(); on success clears activePlan and isPlanMode state
- [X] T029 [US5] Add "Exit Plan Mode" button to PlanPreview in frontend/src/components/chat/PlanPreview.tsx — shown after plan approval (completed status); also add exit affordance for draft plans; wires to exit mutation from usePlan hook

**Checkpoint**: User Story 5 is fully functional — users can exit plan mode and return to normal chat

---

## Phase 8: User Story 6 — Plan Mode Banner and Context Display (Priority: P3)

**Goal**: While plan mode is active, a persistent banner "Plan mode — {project_name}" appears above the chat input. The plan card shows a project badge with repo owner/name for context.

**Independent Test**: Enter plan mode and verify the banner appears above the input with the correct project name; exit and verify it disappears.

### Implementation for User Story 6

- [X] T030 [US6] Add plan mode banner to ChatInterface in frontend/src/components/chat/ChatInterface.tsx — render a banner above the chat input area when isPlanMode (from usePlan hook) is true, displaying "Plan mode — {project_name}" with a subtle background color and dismiss/exit action
- [X] T031 [US6] Refine PlanPreview header in frontend/src/components/chat/PlanPreview.tsx to ensure project badge showing repo_owner/repo_name (e.g., "octocat/my-app") is prominently styled — depends on T011 (which creates the initial PlanPreview with project badge); adjust badge styling, spacing, or layout if needed for context clarity

**Checkpoint**: User Story 6 is fully functional — plan mode banner and project context are clearly displayed

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Edge case handling, error resilience, and final integration improvements

- [ ] T032 Handle project switch during plan mode — add logic in backend/src/api/projects.py or chat session handling to exit plan mode and notify the user when the selected project changes while plan mode is active
- [X] T033 [P] Handle empty plan validation — ensure POST /plans/{plan_id}/approve returns 400 if plan has zero steps; ensure save_plan tool validates at least one step before saving
- [ ] T034 [P] Handle GitHub rate limit during issue creation — add retry logic with exponential backoff in backend/src/services/plan_issue_service.py when GitHub API returns 429 or 403 rate limit responses; surface progress to user showing which issues were created
- [X] T035 [P] Add plan mode error boundary handling — ensure /plan with empty description returns helpful prompt; /plan without selected project returns clear error; agent failures return actionable error messages via SSE error events
- [ ] T036 Run quickstart.md validation — follow the quickstart.md user flow end-to-end to verify all phases work together

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 migration — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational (Phase 2) — core plan creation
- **US2 (Phase 4)**: Depends on US1 (Phase 3) — requires plan mode infrastructure to add auto-delegation
- **US3 (Phase 5)**: Depends on US1 (Phase 3) — requires run_plan_stream() to add thinking events
- **US4 (Phase 6)**: Depends on US1 (Phase 3) — requires plan data model and PlanPreview to add approval
- **US5 (Phase 7)**: Depends on US1 (Phase 3) — requires plan mode state to add exit
- **US6 (Phase 8)**: Depends on US1 (Phase 3) — requires usePlan hook and PlanPreview
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **User Story 2 (P1)**: Depends on US1 — extends run()/run_stream() and save_plan with mode persistence
- **User Story 3 (P2)**: Depends on US1 — adds thinking events to run_plan_stream() and ThinkingIndicator to UI
- **User Story 4 (P2)**: Depends on US1 — adds issue creation service and approve flow; can proceed in parallel with US2/US3
- **User Story 5 (P3)**: Depends on US1 — adds exit endpoint and UI button; can proceed in parallel with US2/US3/US4
- **User Story 6 (P3)**: Depends on US1 — adds banner to ChatInterface; can proceed in parallel with US2/US3/US4/US5

### Within Each User Story

- Backend models/CRUD before services
- Services before API routes
- Backend before frontend (for API contract alignment)
- Core implementation before integration/wiring
- Story complete before moving to next priority

### Parallel Opportunities

- T002, T003, T004, T005 (Foundational) can all run in parallel — different files, no cross-dependencies
- T006, T007 (US1 backend) can run in parallel — different files
- T010, T011 (US1 frontend) can run in parallel — different files
- US3, US4, US5, US6 (Phases 5–8) can all start in parallel after US1 completes
- T019 (ThinkingIndicator) can run in parallel with T017, T018
- T023 (approvePlan API method) can run in parallel with T021, T022
- T027 (exitPlanMode API method) can run in parallel with T026

---

## Parallel Example: User Story 1

```bash
# Launch foundational tasks in parallel:
Task T002: "Add PLAN_CREATE to ActionType in backend/src/models/chat.py"
Task T003: "Create Plan/PlanStep models in backend/src/models/plan.py"
Task T004: "Add plan CRUD to backend/src/services/chat_store.py"
Task T005: "Add Plan/PlanStep types to frontend/src/types/index.ts"

# Then launch US1 backend tasks in parallel:
Task T006: "Create plan_instructions.py in backend/src/prompts/"
Task T007: "Add save_plan tool + register_plan_tools() in backend/src/services/agent_tools.py"

# Then launch US1 frontend tasks in parallel:
Task T010: "Add sendPlanMessageStream/getPlan to frontend/src/services/api.ts"
Task T011: "Create PlanPreview component in frontend/src/components/chat/PlanPreview.tsx"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002–T005) — CRITICAL, blocks all stories
3. Complete Phase 3: User Story 1 (T006–T013) — core plan creation
4. Complete Phase 4: User Story 2 (T014–T016) — plan iteration
5. **STOP and VALIDATE**: Test plan creation and refinement end-to-end
6. Deploy/demo if ready — users can create and iterate on plans

### Incremental Delivery

1. Setup + Foundational → Data layer ready
2. Add User Story 1 → Test independently → Deploy (MVP: plan creation!)
3. Add User Story 2 → Test independently → Deploy (plan iteration)
4. Add User Story 3 → Test independently → Deploy (thinking indicators UX)
5. Add User Story 4 → Test independently → Deploy (issue creation — completes the value loop)
6. Add User Story 5 → Test independently → Deploy (exit plan mode)
7. Add User Story 6 → Test independently → Deploy (banner + context polish)
8. Polish phase → Final integration validation

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Developer A completes User Story 1 (required first)
3. Once US1 is done:
   - Developer A: User Story 2 (plan iteration — extends US1 directly)
   - Developer B: User Story 4 (issue creation — independent backend service)
   - Developer C: User Story 3 (thinking indicators — independent frontend component)
4. After US1–US4 complete:
   - Developer A: User Story 5 (exit mode)
   - Developer B: User Story 6 (banner/context)
   - Developer C: Polish phase

---

## Summary

| Metric | Value |
|--------|-------|
| **Total tasks** | 36 |
| **Phase 1 (Setup)** | 1 task |
| **Phase 2 (Foundational)** | 4 tasks |
| **US1 — Enter Plan Mode (P1)** | 8 tasks |
| **US2 — Iterate Plan (P1)** | 3 tasks |
| **US3 — Thinking Indicators (P2)** | 4 tasks |
| **US4 — Approve & Create Issues (P2)** | 5 tasks |
| **US5 — Exit Plan Mode (P3)** | 4 tasks |
| **US6 — Banner & Context (P3)** | 2 tasks |
| **Polish** | 5 tasks |
| **Parallel opportunities** | 7 groups of parallelizable tasks identified |
| **Suggested MVP scope** | US1 + US2 (Phases 1–4, 16 tasks) |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable after Phase 2
- Tests are not included per spec — "Test Optionality with Clarity" principle
- All file paths use `backend/src/` and `frontend/src/` under the `solune/` repository root
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
