# Tasks: Enrich Activity Page with Meaningful Events

**Input**: Design documents from `/specs/002-enrich-activity-events/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/activity-stats.yaml, quickstart.md

**Tests**: Included — explicitly requested in the feature specification (Phase 4 in spec and plan).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/src/`, `solune/frontend/src/`
- **Backend tests**: `solune/backend/tests/unit/`
- **Frontend tests**: `solune/frontend/tests/` or colocated with source

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new project setup needed — all changes extend existing files. This phase covers the shared model addition used by multiple user stories.

- [ ] T001 Add `ActivityStats` Pydantic model to `solune/backend/src/models/activity.py` with fields: `total_count: int`, `today_count: int`, `by_type: dict[str, int]`, `last_event_at: str | None`
- [ ] T002 Add `ActivityStats` TypeScript interface to `solune/frontend/src/types/index.ts` with fields: `total_count: number`, `today_count: number`, `by_type: Record<string, number>`, `last_event_at: string | null`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend stats service function and API endpoint that MUST be complete before frontend stats UI (US2) can be implemented. Also the stats API client method needed by the frontend hook.

**⚠️ CRITICAL**: The stats endpoint and API client must be complete before US2 frontend work can begin.

- [ ] T003 Add `get_activity_stats()` async function to `solune/backend/src/services/activity_service.py` — three SQL queries: (1) `SELECT COUNT(*), MAX(created_at)` for total + last event, (2) `SELECT COUNT(*) WHERE created_at >= datetime('now', '-1 day')` for today count, (3) `SELECT event_type, COUNT(*) WHERE created_at >= now-7d GROUP BY event_type` for type breakdown. All scoped by `project_id`.
- [ ] T004 Add `GET /activity/stats` route to `solune/backend/src/api/activity.py` — place **before** the `/{entity_type}/{entity_id}` route to avoid path conflict. Accept `project_id` query parameter, call `get_activity_stats()`, return `ActivityStats` response model.
- [ ] T005 [P] Add `activityApi.stats(projectId)` method to `solune/frontend/src/services/api.ts` — GET request to `/activity/stats` with `project_id` query parameter, returns `ActivityStats` type.
- [ ] T006 [P] Create `useActivityStats` hook in `solune/frontend/src/hooks/useActivityStats.ts` — fetch stats via `activityApi.stats()`, return `{ stats, isLoading, error }` following the existing hook patterns (e.g., `useActivityFeed`).

**Checkpoint**: Stats backend + frontend API client ready — US2 stats dashboard can now be built.

---

## Phase 3: User Story 1 — Track Pipeline Launches and Workflow Completions (Priority: P1) 🎯 MVP

**Goal**: Log pipeline launch events (with issue number and agent count) and orchestrator workflow completion/agent triggering events so users can trace automated operation lifecycles from the Activity page.

**Independent Test**: Launch a pipeline → verify "launched" event appears with issue number and agent count. Wait for workflow completion → verify "completed" event. Check agent trigger → verify "triggered" event. Filter by "Execution" category → only these events shown.

### Tests for User Story 1

- [ ] T007 [P] [US1] Add backend test in `solune/backend/tests/unit/test_api_activity.py` (or relevant pipeline test file) verifying `log_event` is called with `event_type="pipeline_run"`, `action="launched"`, and detail containing `issue_number` and `agent_count` when `execute_pipeline_launch()` succeeds.
- [ ] T008 [P] [US1] Add backend test verifying `log_event` is called with `event_type="agent_execution"`, `action="completed"` when orchestrator `handle_completion()` runs, and `action="triggered"` when `assign_agent_for_status()` runs.

### Implementation for User Story 1

- [ ] T009 [US1] Add `log_event` call in `solune/backend/src/api/pipelines.py` inside `execute_pipeline_launch()` after issue creation — `event_type="pipeline_run"`, `entity_type="pipeline"`, `action="launched"`, detail with `issue_number`, `agent_count`, `pipeline_name`.
- [ ] T010 [P] [US1] Add `log_event` call in `solune/backend/src/services/workflow_orchestrator/orchestrator.py` in `handle_completion()` — `event_type="agent_execution"`, `entity_type="pipeline"`, `action="completed"`, detail with `workflow_id`, `pipeline_name`.
- [ ] T011 [P] [US1] Add `log_event` call in `solune/backend/src/services/workflow_orchestrator/orchestrator.py` in `assign_agent_for_status()` — `event_type="agent_execution"`, `entity_type="agent"`, `action="triggered"`, detail with `agent_name`, `status`.
- [ ] T012 [US1] Add "Execution" filter category to `EVENT_CATEGORIES` in `solune/frontend/src/pages/ActivityPage.tsx` — maps to `["agent_execution"]` event types with appropriate icon.

**Checkpoint**: Pipeline launch and orchestrator events are logged and filterable via "Execution" category.

---

## Phase 4: User Story 2 — View Activity Summary Statistics (Priority: P1)

**Goal**: Display a stats dashboard header on the Activity page with 4 stat cards ("Total Events", "Today", "Most Common", "Last Activity") sourced from the `GET /activity/stats` endpoint.

**Independent Test**: Load Activity page with existing events → 4 stat cards render above filter chips with accurate counts. Load with no events → cards show "0" and "No activity" gracefully. Stats endpoint responds within 2 seconds.

### Tests for User Story 2

- [ ] T013 [P] [US2] Add backend tests in `solune/backend/tests/unit/test_api_activity.py` for `GET /activity/stats`: (1) returns correct counts with events, (2) returns zeros and null `last_event_at` when empty, (3) returns 401 without auth, (4) `by_type` groups correctly.
- [ ] T014 [P] [US2] Add frontend test for stats dashboard rendering — verify 4 stat cards render with mock data, verify empty state shows zeros/"No activity", verify loading state.

### Implementation for User Story 2

- [ ] T015 [US2] Render stats dashboard header in `solune/frontend/src/pages/ActivityPage.tsx` — 4 stat cards above filter chips: "Total Events" (`total_count`), "Today" (`today_count`), "Most Common" (key with highest value in `by_type`), "Last Activity" (relative time from `last_event_at`). Use responsive grid with TailwindCSS matching existing stat-box pattern. Handle loading and empty states (FR-010, FR-015).

**Checkpoint**: Activity page shows live stats dashboard with 4 cards sourced from the backend endpoint.

---

## Phase 5: User Story 3 — Track Settings and Project Lifecycle Changes (Priority: P2)

**Goal**: Log settings changes (user, global, project) and project lifecycle events (creation, selection) so users have an audit trail of configuration and project management actions.

**Independent Test**: Change a setting → "settings" event appears with changed fields in detail. Create a project → "project created" event appears. Select a project → "project selected" event appears. Filter by "Project" category → only these events shown.

### Tests for User Story 3

- [ ] T016 [P] [US3] Add backend test verifying `log_event` is called with `event_type="settings"`, `action="updated"`, and detail containing `scope` and `changed_fields` list when settings PUT endpoints are called.
- [ ] T017 [P] [US3] Add backend test verifying `log_event` is called with `event_type="project"`, `action="created"` for project creation and `action="selected"` for project selection.

### Implementation for User Story 3

- [ ] T018 [US3] Add `log_event` calls to settings PUT endpoints in `solune/backend/src/api/settings.py` — for each scope (user, global, project): compute `changed_fields` by comparing old vs new settings, then log `event_type="settings"`, `entity_type="settings"`, `action="updated"`, detail with `scope` and `changed_fields`. Log even for no-op saves (empty changed_fields list per spec edge case).
- [ ] T019 [P] [US3] Add `log_event` call to project creation endpoint in `solune/backend/src/api/projects.py` — `event_type="project"`, `entity_type="project"`, `action="created"`, detail with `project_name`.
- [ ] T020 [P] [US3] Add `log_event` call to project selection endpoint in `solune/backend/src/api/projects.py` — `event_type="project"`, `entity_type="project"`, `action="selected"`, detail with `project_name`.
- [ ] T021 [US3] Add "Project" filter category to `EVENT_CATEGORIES` in `solune/frontend/src/pages/ActivityPage.tsx` — maps to `["project", "settings"]` event types with appropriate icon.

**Checkpoint**: Settings and project lifecycle events are logged and filterable via "Project" category.

---

## Phase 6: User Story 4 — Distinguish Granular Webhook Events (Priority: P2)

**Goal**: Replace generic webhook `action="received"` with specific actions (`pr_merged`, `copilot_pr_ready`) based on payload inspection so users can identify exactly what triggered each webhook.

**Independent Test**: Trigger a PR merge webhook → event shows `action="pr_merged"`. Trigger a Copilot PR webhook → event shows `action="copilot_pr_ready"`. Trigger an unrecognized webhook → falls back to `action="received"`.

### Tests for User Story 4

- [ ] T022 [P] [US4] Add backend test verifying webhook handler logs `action="pr_merged"` when payload is `pull_request` with `action="closed"` and `merged=true`, logs `action="copilot_pr_ready"` when PR head ref starts with `copilot/`, and falls back to `action="received"` for unrecognized types.

### Implementation for User Story 4

- [ ] T023 [US4] Enrich webhook logging in `solune/backend/src/api/webhooks.py` — inspect payload to classify action: (1) PR closed + merged → `action="pr_merged"`, (2) PR from `copilot/` branch → `action="copilot_pr_ready"`, (3) fallback → `action="received"`. Pass classified action to existing `log_event` call.

**Checkpoint**: Webhook events now show specific action labels instead of generic "received".

---

## Phase 7: User Story 5 — Browse Events with Time-Bucketed Grouping (Priority: P3)

**Goal**: Group activity events by time periods ("Today", "Yesterday", "This Week", "Earlier") with sticky section headers for easier navigation.

**Independent Test**: Load Activity page with events spanning multiple days → events grouped under correct time-bucket headers. Empty buckets are hidden. Scroll through long list → headers stick to top of viewport.

### Tests for User Story 5

- [ ] T024 [P] [US5] Add frontend test for time-bucketing utility function — verify events are correctly bucketed into "Today", "Yesterday", "This Week", "Earlier" based on `created_at` timestamps. Verify empty buckets are excluded from output.

### Implementation for User Story 5

- [ ] T025 [US5] Implement `groupEventsByTimeBucket()` utility function in `solune/frontend/src/pages/ActivityPage.tsx` (or a separate utils file) — categorize events by `created_at` relative to current date into "Today", "Yesterday", "This Week", "Earlier" buckets. Return ordered groups with bucket labels.
- [ ] T026 [US5] Render time-bucketed groups in `solune/frontend/src/pages/ActivityPage.tsx` — replace flat event list with grouped sections. Add sticky date section headers using CSS `position: sticky`. Hide empty buckets. Apply grouping to paginated result set (FR-012).

**Checkpoint**: Activity page shows events grouped by time period with sticky headers.

---

## Phase 8: User Story 6 — Identify Event Actions and Entity Types at a Glance (Priority: P3)

**Goal**: Add color-coded action badges and entity-type pills to each event row for rapid visual scanning.

**Independent Test**: Load Activity page → "created" events have green badge, "deleted" have red, "updated" have blue, "launched"/"triggered"/"completed" have purple. Entity-type pills (e.g., "pipeline", "settings") appear next to summaries.

### Tests for User Story 6

- [ ] T027 [P] [US6] Add frontend test for action badge color mapping — verify correct colors for each action type (green=created, red=deleted, blue=updated, purple=launched/triggered/started/completed, gray=default). Verify entity-type pills render the correct entity type text.

### Implementation for User Story 6

- [ ] T028 [US6] Add action badge component/rendering in `solune/frontend/src/pages/ActivityPage.tsx` — define static mapping from action strings to Tailwind color classes: `created→green`, `deleted→red`, `updated→blue`, `launched/triggered/started/completed→purple`, default→gray. Render as small inline badges (FR-013).
- [ ] T029 [US6] Add entity-type pill rendering in `solune/frontend/src/pages/ActivityPage.tsx` — display `entity_type` value (e.g., "pipeline", "agent", "settings", "project") as neutral pill badge next to event summary (FR-014).

**Checkpoint**: Event rows now show color-coded action badges and entity-type pills for at-a-glance identification.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, cleanup, and cross-cutting improvements

- [ ] T030 Run backend linting and type checking: `ruff check src tests`, `ruff format --check src tests`, `pyright src` in `solune/backend/`
- [ ] T031 Run full backend test suite: `uv run pytest tests/unit/ -q --tb=short` in `solune/backend/` — all tests pass including new stats and log_event tests
- [ ] T032 [P] Run frontend tests: `npm test` in `solune/frontend/` — all tests pass including new stats, time-bucketing, and badge tests
- [ ] T033 Run `solune/scripts/generate-diagrams.sh` to regenerate architecture diagrams (new stats route in `api/activity.py` will be auto-discovered)
- [ ] T034 Verify empty state: load Activity page with no events → stat cards show 0 and "No activity", no errors or broken layouts (FR-015, SC-008)
- [ ] T035 Run quickstart.md verification steps from `specs/002-enrich-activity-events/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (T001 for backend model, T002 for frontend type) — BLOCKS US2 frontend stats dashboard
- **US1 (Phase 3)**: Depends on Phase 1 only (no stats dependency) — can start after T001
- **US2 (Phase 4)**: Depends on Phase 2 completion (T003, T004, T005, T006 for stats infrastructure)
- **US3 (Phase 5)**: Depends on Phase 1 only — can start after T001, parallel with US1
- **US4 (Phase 6)**: Depends on Phase 1 only — can start after T001, parallel with US1/US3
- **US5 (Phase 7)**: No backend dependency — can start after Phase 1 (T002 for frontend types)
- **US6 (Phase 8)**: No backend dependency — can start after Phase 1 (T002 for frontend types)
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Independent — only needs existing `log_event` + `activity_events` schema
- **User Story 2 (P1)**: Depends on Foundational phase (stats endpoint + API client + hook)
- **User Story 3 (P2)**: Independent — only needs existing `log_event`
- **User Story 4 (P2)**: Independent — modifies existing webhook `log_event` call
- **User Story 5 (P3)**: Independent — frontend-only, no backend changes
- **User Story 6 (P3)**: Independent — frontend-only, no backend changes

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Backend changes before frontend changes (when both exist)
- Core implementation before UI enhancements
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1**: T001 and T002 can run in parallel (different stacks)
- **Phase 2**: T003 → T004 (sequential), but T005 and T006 can run in parallel with each other (and after T002)
- **Phase 3 + Phase 5 + Phase 6**: US1, US3, and US4 backend tasks can all run in parallel (different files)
- **Phase 7 + Phase 8**: US5 and US6 frontend tasks can run in parallel (different concerns in same file, or extractable to utils)
- **Phase 9**: T030, T031, T032 can run in parallel (backend lint vs backend tests vs frontend tests)

---

## Parallel Example: Backend Log Points (US1 + US3 + US4)

```text
# These backend tasks touch different files and can run simultaneously:
T009 [US1] Add log_event to pipelines.py
T010 [US1] Add log_event to orchestrator.py (completed)
T011 [US1] Add log_event to orchestrator.py (triggered)
T018 [US3] Add log_event to settings.py
T019 [US3] Add log_event to projects.py (created)
T020 [US3] Add log_event to projects.py (selected)
T023 [US4] Enrich webhook logging in webhooks.py
```

## Parallel Example: Frontend Enhancements (US5 + US6)

```text
# These frontend tasks are independent concerns:
T025 [US5] Implement groupEventsByTimeBucket utility
T028 [US6] Add action badge color mapping
T029 [US6] Add entity-type pill rendering
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup (T001, T002)
2. Complete Phase 2: Foundational (T003–T006)
3. Complete Phase 3: User Story 1 — Pipeline + orchestrator log events (T007–T012)
4. Complete Phase 4: User Story 2 — Stats dashboard (T013–T015)
5. **STOP and VALIDATE**: Test US1 + US2 independently — pipeline events logged, stats dashboard renders
6. Deploy/demo if ready — this delivers the two P1 stories

### Incremental Delivery

1. Complete Setup + Foundational → Backend stats infrastructure ready
2. Add US1 (pipeline/orchestrator logging) → Test independently → **MVP milestone**
3. Add US2 (stats dashboard) → Test independently → **Stats visible**
4. Add US3 (settings/project logging) → Test independently → **Audit trail complete**
5. Add US4 (granular webhooks) → Test independently → **Webhook clarity**
6. Add US5 (time bucketing) → Test independently → **Navigation improved**
7. Add US6 (badges/pills) → Test independently → **Visual polish complete**
8. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 (pipeline + orchestrator logging) + US2 (stats dashboard)
   - Developer B: US3 (settings + project logging) + US4 (webhook enrichment)
   - Developer C: US5 (time bucketing) + US6 (badges + pills)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- All backend log_event calls use existing fire-and-forget pattern — never block primary operations
- No database migration needed — new event types are string values in existing schema (FR-016)
- Stats computed server-side via SQL for efficiency (FR-009), not client-side aggregation
- Time bucketing is frontend-only grouping on paginated results
- Frontend stats follow existing stat-box/PipelineAnalytics pattern — no charting library
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
