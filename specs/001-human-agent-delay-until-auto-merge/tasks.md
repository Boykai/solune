# Tasks: Human Agent — Delay Until Auto-Merge

**Input**: Design documents from `/specs/001-human-agent-delay-until-auto-merge/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Included — unit tests explicitly requested in the feature specification verification section.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No project initialization needed — this feature extends an existing codebase with an established backend (`solune/backend/`) and frontend (`solune/frontend/`). Phase is intentionally empty.

*(No tasks — existing project structure is already in place.)*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend config flow changes that MUST be complete before ANY user story implementation. These ensure `delay_seconds` can flow from the frontend config dict through to the pipeline execution runtime.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T001 Merge full `node.config` dict into `AgentAssignment.config` in the group-aware path in `solune/backend/src/services/workflow_orchestrator/config.py` (line ~371-376). Change from `config={"model_id": node.model_id, "model_name": node.model_name} if node.model_id else None` to `config={**node.config, "model_id": node.model_id, "model_name": node.model_name} if node.model_id or node.config else None`
- [x] T002 Apply the same `node.config` dict merge to the legacy fallback path in `solune/backend/src/services/workflow_orchestrator/config.py` (line ~397-405)
- [x] T003 [P] Add `agent_configs: dict[str, dict] = field(default_factory=dict)` field to the `PipelineState` dataclass in `solune/backend/src/services/workflow_orchestrator/models.py` (after the `auto_merge: bool = False` field, line ~177)
- [x] T004 Populate `agent_configs` from `WorkflowConfiguration`'s `AgentAssignment.config` dicts when constructing `PipelineState` in `solune/backend/src/api/pipelines.py` (line ~467-489). Map each agent's slug to its config dict so the execution loop can read `delay_seconds` at runtime.

**Checkpoint**: Config flow foundation ready — `delay_seconds` flows from `PipelineAgentNode.config` → `AgentAssignment.config` → `PipelineState.agent_configs["human"]`. User story implementation can now begin.

---

## Phase 3: User Story 1 — Configure Delay on Human Agent Node (Priority: P1) 🎯 MVP

**Goal**: Allow pipeline owners to configure an optional `delay_seconds` value on Human agent nodes via a toggle in the pipeline board UI, with visual badge feedback showing the configured mode.

**Independent Test**: Open a pipeline board with a Human agent node, toggle "Delay until auto-merge" on, enter 300, and confirm `config.delay_seconds: 300` persists after save. Badge reads "⏱️ Auto-merge: 5m." Toggle off and confirm badge reads "Manual review." Verify the toggle does not appear on non-human agent nodes.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T005 [P] [US1] Unit test for `delay_seconds` validation — valid range `[1, 86400]`, integer type, rejected for values ≤0, >86400, and non-integer types; only meaningful for `agent_slug == "human"` in `solune/backend/tests/unit/test_human_delay.py`
- [x] T006 [P] [US1] Unit test for config flow — verify `delay_seconds` in `PipelineAgentNode.config` flows through `AgentAssignment.config` to `PipelineState.agent_configs["human"]["delay_seconds"]` in `solune/backend/tests/unit/test_human_delay.py`

### Implementation for User Story 1

- [x] T007 [P] [US1] Add delay toggle and numeric input to Human agent node in `solune/frontend/src/components/pipeline/AgentNode.tsx`. When `agent_slug === 'human'`, render below the model selector: toggle "Delay until auto-merge" (off by default); when on: `<input type="number" min={1} max={86400}>` for seconds. Updates via existing `onUpdateAgent → config.delay_seconds`. Toggle and input MUST NOT render for non-human agent nodes.
- [x] T008 [P] [US1] Verify config merge in `solune/frontend/src/hooks/usePipelineBoardMutations.ts` — confirm `updateAgentInStage` spreads existing config when merging partial updates (line ~193) so updating `config.delay_seconds` does not clobber `config.model_id` or other existing config keys. Fix if needed.
- [x] T009 [US1] Add display badge to Human agent node in `solune/frontend/src/components/pipeline/AgentNode.tsx`. When `delay_seconds` is set: show badge "⏱️ Auto-merge: {formatted_duration}". When not set: show badge "Manual review". Duration formatting: 300s→"5m", 3600s→"1h", 90s→"1m 30s", 86400s→"24h".

**Checkpoint**: Human agent node shows delay toggle, accepts numeric input, persists value in config, displays mode badge. Non-human agents show no delay UI. User Story 1 is fully functional and testable independently.

---

## Phase 4: User Story 2 — Pipeline Executes Delay Then Auto-Merges (Priority: P1)

**Goal**: When `delay_seconds` is configured on a Human agent, the pipeline creates the human sub-issue (audit trail), posts a countdown comment, waits the configured duration, then triggers the existing `_attempt_auto_merge()` flow. Sub-issue is closed after merge completes.

**Independent Test**: Configure a Human agent with `delay_seconds: 30`, trigger a pipeline run, observe: (1) sub-issue created with body containing "⏱️ Auto-merge in 30s. Close early to skip.", (2) comment "⏱️ Auto-merge in 30s" posted, (3) ~30 second wait, (4) `_attempt_auto_merge()` triggered, (5) sub-issue closed, (6) pipeline advances.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T010 [P] [US2] Unit test for pipeline execution with human + delay → `asyncio.sleep` loop executes for correct number of iterations and `_attempt_auto_merge()` is invoked after delay expires in `solune/backend/tests/unit/test_human_delay.py`
- [x] T011 [P] [US2] Unit test for sub-issue body containing "⏱️ Auto-merge in {duration}. Close early to skip." when delay is configured, and NOT containing it when delay is not configured, in `solune/backend/tests/unit/test_human_delay.py`

### Implementation for User Story 2

- [x] T012 [US2] Add `delay_seconds` validation guard in `solune/backend/src/services/copilot_polling/pipeline.py`. When `agent_slug == "human"` and `config.get("delay_seconds")` is present: validate it is an `int` in range `[1, 86400]`. If invalid, log a warning and treat as `None` (fall through to existing behavior).
- [x] T013 [US2] Implement delay-then-merge execution block in `solune/backend/src/services/copilot_polling/pipeline.py` (augmenting the human agent handling block at line ~1951-2039). When `delay_seconds` is set: (1) create sub-issue (existing flow), (2) comment "⏱️ Auto-merge in {formatted_duration}" on sub-issue, (3) loop `asyncio.sleep(15)` for `ceil(delay_seconds / 15)` iterations, (4) trigger `_attempt_auto_merge()`, (5) close sub-issue with completion comment, (6) mark agent as completed, (7) advance pipeline. Duration formatting: 300s→"5m", 3600s→"1h", 30s→"30s".
- [x] T014 [US2] Append "⏱️ Auto-merge in {formatted_duration}. Close early to skip." to human sub-issue body when delay is configured in `solune/backend/src/services/workflow_orchestrator/orchestrator.py` (or `solune/backend/src/services/github_projects/agents.py` — locate where `tailor_body_for_agent` constructs the human sub-issue body and add the delay info there)

**Checkpoint**: Pipeline with delay-configured Human agent creates sub-issue with delay info, posts countdown comment, waits the full delay duration, triggers auto-merge, closes sub-issue, and advances. User Story 2 is fully functional and testable independently.

---

## Phase 5: User Story 3 — Early Cancellation by Closing the Sub-Issue (Priority: P2)

**Goal**: During the delay wait period, if the reviewer closes the sub-issue or comments "Done!" before the timer expires, the pipeline detects this within 15 seconds and proceeds immediately with auto-merge instead of waiting for the full delay.

**Independent Test**: Configure a Human agent with `delay_seconds: 600`, trigger pipeline, close the sub-issue after 30 seconds. Verify the pipeline detects closure within ~15 seconds and proceeds immediately (total wait ~45s, not 600s).

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T015 [P] [US3] Unit test for early cancellation — mock sub-issue as closed after 2 polling intervals → pipeline breaks delay loop immediately and proceeds to `_attempt_auto_merge()`, skipping remaining sleep iterations in `solune/backend/tests/unit/test_human_delay.py`
- [x] T016 [P] [US3] Unit test for early cancellation via "Done!" comment — mock "Done!" comment detected after 1 polling interval → pipeline breaks delay loop immediately in `solune/backend/tests/unit/test_human_delay.py`

### Implementation for User Story 3

- [x] T017 [US3] Enhance delay loop in `solune/backend/src/services/copilot_polling/pipeline.py` to check sub-issue status (closed or "Done!" comment) after each 15-second `asyncio.sleep` interval. If early cancellation detected, break loop immediately and proceed to `_attempt_auto_merge()`. This refines the delay loop from T013 — instead of blind sleeping, each iteration checks the sub-issue via the existing GitHub API polling infrastructure.

**Checkpoint**: Early cancellation works — closing the sub-issue or commenting "Done!" during the delay period causes immediate pipeline progression within one polling interval (~15s). User Story 3 is fully functional and testable independently.

---

## Phase 6: User Story 4 — Manual Review Behavior Preserved (Priority: P2)

**Goal**: When `delay_seconds` is NOT configured on a Human agent, all existing behavior is identical to pre-feature behavior: (a) pipeline pauses until manual sub-issue close or "Done!" comment, (b) skip-and-auto-merge for last-step human with auto_merge active.

**Independent Test**: Run pipeline with Human agent (no delay) → verify it pauses until manual intervention. Run pipeline with `auto_merge: true` + Human as last step + no delay → verify existing skip-and-auto-merge behavior is preserved.

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T018 [P] [US4] Unit test for pipeline execution with human + no delay → manual-wait behavior unchanged (pipeline pauses, no `_attempt_auto_merge()` called until sub-issue is manually closed) in `solune/backend/tests/unit/test_human_delay.py`
- [x] T019 [P] [US4] Unit test for pipeline execution with human + no delay + `auto_merge: true` + human is last step → existing skip-and-auto-merge behavior preserved (human step skipped, pipeline transitions to auto-merge) in `solune/backend/tests/unit/test_human_delay.py`

### Implementation for User Story 4

- [x] T020 [US4] Verify and adjust the delay-aware execution block in `solune/backend/src/services/copilot_polling/pipeline.py` to ensure the `else` branch (when `delay_seconds` is NOT set) preserves: (a) manual-wait path where pipeline pauses until sub-issue close or "Done!" comment, (b) skip-and-auto-merge path for last-step human with `auto_merge` active. No new code expected — this validates the else branch of T013's implementation and confirms backward compatibility.

**Checkpoint**: Existing manual-review and skip-human-on-auto-merge behaviors are confirmed preserved with zero regressions. User Story 4 is verified.

---

## Phase 7: User Story 5 — Tracking Table Displays Delay Status (Priority: P3)

**Goal**: Pipeline tracking table shows "⏱️ Delay ({formatted_duration})" for Human agents in the delay-waiting state, distinguishing them from standard manual-wait Human agents.

**Independent Test**: Trigger pipeline with a delay-configured Human agent, check the tracking table output for "⏱️ Delay (5m)" format. Verify manual-wait Human agents retain existing status display.

### Implementation for User Story 5

- [x] T021 [US5] Render delayed human agent row as "⏱️ Delay ({formatted_duration})" in `solune/backend/src/services/agent_tracking.py` when the human agent is in the delay-waiting state. Duration formatting: 300s→"5m", 3600s→"1h". Manual-wait human agents retain their existing status display unchanged.

**Checkpoint**: Tracking table clearly distinguishes delay-wait ("⏱️ Delay (5m)") from manual-wait human agents. User Story 5 is complete.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T022 [P] Extract shared duration formatting helper (seconds → human-readable: 300→"5m", 3600→"1h", 90→"1m 30s", 86400→"24h") into reusable utilities if not already extracted. Backend: `solune/backend/src/services/copilot_polling/pipeline.py` or shared utils module. Frontend: `solune/frontend/src/components/pipeline/AgentNode.tsx` or shared utils.
- [x] T023 Run `solune/backend/tests/unit/test_human_delay.py` full suite and verify all tests pass
- [ ] T024 Run backend regression suite: `cd solune/backend && uv run pytest --cov=src --cov-report=json --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency` — verify coverage ≥75% and no regressions
- [ ] T025 Run frontend test suite: `cd solune/frontend && npm run test` — verify no regressions
- [ ] T026 Run `specs/001-human-agent-delay-until-auto-merge/quickstart.md` validation steps

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No tasks — existing project
- **Foundational (Phase 2)**: No dependencies — can start immediately. **BLOCKS all user stories.**
- **US1 (Phase 3)**: Depends on Phase 2 completion (config flow must be in place for frontend to save/load `delay_seconds`)
- **US2 (Phase 4)**: Depends on Phase 2 completion (`agent_configs` must be populated for execution logic)
- **US3 (Phase 5)**: Depends on US2 (Phase 4) — early cancellation refines the delay loop implemented in US2
- **US4 (Phase 6)**: Depends on US2 (Phase 4) — verifies backward compatibility of execution changes from US2
- **US5 (Phase 7)**: Depends on US2 (Phase 4) — tracking display needs the delay-waiting state introduced in US2
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — **no dependencies on other stories**
- **US2 (P1)**: Can start after Phase 2 — **no dependencies on other stories**. Can run **in parallel** with US1.
- **US3 (P2)**: Depends on US2 — refines the delay loop
- **US4 (P2)**: Depends on US2 — verifies backward compatibility of execution changes
- **US5 (P3)**: Depends on US2 — needs the delay-waiting state

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Config/model changes before service logic
- Service logic before UI components
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 2**: T001 and T002 (both in config.py) are sequential; T003 (models.py) can run in parallel with T001/T002; T004 depends on T001–T003
- **Phase 3 (US1)**: T005 and T006 (tests) can run in parallel; T007 and T008 (different frontend files) can run in parallel; T009 depends on T007
- **Phase 4 (US2)**: T010 and T011 (tests) can run in parallel; T012 → T013 → T014 are sequential (same file or dependent)
- **Phase 5 (US3)**: T015 and T016 (tests) can run in parallel; T017 depends on T013
- **Phase 6 (US4)**: T018 and T019 (tests) can run in parallel; T020 is verification only
- **Cross-story**: **US1 and US2 can start simultaneously** after Phase 2 (frontend and backend work in parallel)

---

## Parallel Example: US1 (Frontend) ‖ US2 (Backend)

```bash
# After Phase 2 completes, launch US1 and US2 simultaneously:

# Developer A (Frontend — US1):
Task T005: "Unit test for delay_seconds validation in test_human_delay.py"
Task T007: "Add delay toggle and numeric input to AgentNode.tsx"
Task T009: "Add display badge to AgentNode.tsx"

# Developer B (Backend — US2):
Task T010: "Unit test for delay execution in test_human_delay.py"
Task T012: "Add delay_seconds validation guard in pipeline.py"
Task T013: "Implement delay-then-merge execution block in pipeline.py"
Task T014: "Sub-issue body with delay info in orchestrator.py"
```

---

## Implementation Strategy

### MVP First (US1 + US2 — Both P1)

1. Complete Phase 2: Foundational (config flow) — 4 tasks
2. Complete Phase 3: US1 (configure delay via UI) — 5 tasks
3. Complete Phase 4: US2 (delay-then-merge execution) — 5 tasks
4. **STOP and VALIDATE**: Delay can be configured, saved, and executed end-to-end
5. Deploy/demo if ready — **MVP delivers full value with 14 tasks**

### Incremental Delivery

1. Phase 2 (Foundational) → Config flow works
2. US1 (Configure Delay) + US2 (Execute Delay) → Core feature complete (**MVP!**)
3. US3 (Early Cancellation) → Improved UX for reviewers who finish early
4. US4 (Manual Review Preserved) → Backward compatibility verified
5. US5 (Tracking Table) → Observability polish
6. Polish → Regression suite, cleanup, shared utilities

### Parallel Team Strategy

With two developers:

1. Both complete Phase 2 together (4 small, focused tasks)
2. After Phase 2:
   - **Developer A**: US1 (frontend toggle + badge) → US5 (tracking table)
   - **Developer B**: US2 (execution logic) → US3 (early cancel) → US4 (backward compat)
3. Polish phase together

---

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 26 |
| Phase 2 (Foundational) | 4 tasks |
| US1 — Configure Delay (P1) | 5 tasks |
| US2 — Delay Execution (P1) | 5 tasks |
| US3 — Early Cancellation (P2) | 3 tasks |
| US4 — Manual Review Preserved (P2) | 3 tasks |
| US5 — Tracking Table (P3) | 1 task |
| Polish | 5 tasks |
| Parallel opportunities | US1 ‖ US2 after Phase 2; tests within each story |
| MVP scope | Phase 2 + US1 + US2 (14 tasks) |
| Independent test criteria | Each user story has its own checkpoint |
| Format validated | ✅ All 26 tasks follow `- [ ] [ID] [P?] [Story?] Description with file path` |
