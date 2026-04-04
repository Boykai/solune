# Tasks: Auto-Merge After All Agents Complete + CI Pass + DevOps Retry

**Input**: Design documents from `/specs/770-auto-merge-devops-retry/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/auto-merge-events.yaml, quickstart.md

**Tests**: Included — the parent issue (#770) and plan.md specify unit, integration, and edge-case verification criteria.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `backend/tests/` (all paths relative to `solune/` monorepo root)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add configuration constants and in-memory tracking structures required by all subsequent phases

- [ ] T001 Add `POST_DEVOPS_POLL_INTERVAL: float = 120.0` and `POST_DEVOPS_MAX_POLLS: int = 30` constants to `backend/src/services/copilot_polling/state.py` alongside the existing `AUTO_MERGE_RETRY_BASE_DELAY` and `MAX_AUTO_MERGE_RETRIES` constants
- [ ] T002 Add `_pending_post_devops_retries: BoundedDict[int, dict[str, Any]] = BoundedDict(maxlen=200)` module-level tracking dict to `backend/src/services/copilot_polling/state.py` alongside the existing `_pending_auto_merge_retries` BoundedDict, using the same import from `src.utils`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the DevOps agent template and register it as a built-in agent — all user stories depend on the DevOps agent being discoverable and dispatchable

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 [P] Create DevOps agent template at `backend/templates/.github/agents/devops.agent.md` with YAML front-matter (`name: DevOps`, `description`, `mcp-servers` with context7 config) and markdown body defining persona (CI failure diagnosis, merge conflict resolution, push fixes to PR branch), capabilities, workflow steps, and completion marker instruction (`devops: Done!`). Follow the format of existing templates like `backend/templates/.github/agents/linter.agent.md` and reference the deployed version at `.github/agents/devops.agent.md` for content
- [ ] T004 [P] Register DevOps as built-in agent in `backend/src/services/github_projects/agents.py` — add `AvailableAgent(slug="devops", display_name="DevOps", description="CI failure diagnosis and resolution agent", avatar_url=None, icon_name=None, source=AgentSource.BUILTIN)` to `BUILTIN_AGENTS` list (count goes from 8 → 9) and add a DevOps sub-issue description template to the `AGENT_DESCRIPTIONS` mapping if one exists
- [ ] T005 Update agent registration assertions in `backend/tests/unit/test_github_agents.py` — update `BUILTIN_AGENTS` count from 8 to 9 and add `"devops"` to the expected slugs set in all relevant test assertions

**Checkpoint**: DevOps agent is registered and discoverable via `BUILTIN_AGENTS`. `dispatch_devops_agent()` can now resolve the agent slug successfully.

---

## Phase 3: User Story 1 — Pipeline Auto-Merges After All Agents Complete and CI Passes (Priority: P1) 🎯 MVP

**Goal**: Verify and ensure the existing auto-merge happy path works end-to-end: all agents complete → issue transitions to "In Review" → draft PR → ready-for-review → CI passes → squash-merge → issue status "Done"

**Independent Test**: Trigger a pipeline where all agents complete successfully and CI passes. The parent PR should transition from draft to ready-for-review and be squash-merged automatically, with the issue marked as "Done".

### Tests for User Story 1

- [ ] T006 [P] [US1] Add unit test in `backend/tests/unit/test_auto_merge.py` verifying `_attempt_auto_merge()` returns `AutoMergeResult(status="merged")` with `pr_number` and `merge_commit` when CI passes and PR is mergeable — mock `_discover_main_pr_for_review()`, `get_combined_check_runs()`, and GraphQL merge mutation
- [ ] T007 [P] [US1] Add unit test in `backend/tests/unit/test_auto_merge.py` verifying `_attempt_auto_merge()` returns `AutoMergeResult(status="retry_later")` when CI checks are still pending, and verify that `schedule_auto_merge_retry()` schedules retries with exponential backoff (base delay 60s, max 3 attempts)

### Implementation for User Story 1

- [ ] T008 [US1] Verify existing `_attempt_auto_merge()` flow in `backend/src/services/copilot_polling/auto_merge.py` converts draft PR to ready-for-review before merge, checks CI status via `get_combined_check_runs()`, checks mergeability state, and performs squash merge via GraphQL. Confirm issue status transitions to "Done" and a summary comment is posted after successful merge. No code changes expected — verification and minor fixes only if the happy path has gaps.

**Checkpoint**: US1 happy path confirmed working — all agents complete → CI passes → auto-merge → Done

---

## Phase 4: User Story 2 — DevOps Agent Resolves CI Failures and Merge Conflicts (Priority: P1)

**Goal**: When `_attempt_auto_merge()` returns `status="devops_needed"`, dispatch the DevOps agent with CI failure context, schedule a polling loop to detect the DevOps "Done!" completion marker, and re-attempt auto-merge. Cap DevOps at 2 total attempts per issue.

**Independent Test**: Mock `_attempt_auto_merge()` to return `devops_needed`, verify DevOps agent is dispatched via `assign_copilot_to_issue(custom_agent="devops")`, then mock a "Done!" comment appearing, and verify re-merge is attempted.

### Tests for User Story 2

- [ ] T009 [P] [US2] Add unit test in `backend/tests/unit/test_auto_merge.py` for `_check_devops_done_comment()` — verify it returns `True` when the most recent issue comments contain `"devops: Done!"` substring and `False` when they do not. Mock `github_service.list_issue_comments()` returning comment payloads
- [ ] T010 [P] [US2] Add unit test in `backend/tests/unit/test_auto_merge.py` for `schedule_post_devops_merge_retry()` — verify it creates an `asyncio` background task, polls at `POST_DEVOPS_POLL_INTERVAL` (120s) intervals via `_check_devops_done_comment()`, and calls `_attempt_auto_merge()` when "Done!" is found. Mock `asyncio.sleep()` to avoid real delays
- [ ] T011 [P] [US2] Add unit test in `backend/tests/unit/test_auto_merge.py` verifying that `dispatch_devops_agent()` calls `schedule_post_devops_merge_retry()` after successful dispatch (after `assign_copilot_to_issue()` returns True)
- [ ] T012 [P] [US2] Add unit test in `backend/tests/unit/test_auto_merge.py` verifying deduplication — `schedule_post_devops_merge_retry()` skips scheduling if `issue_number` is already a key in `_pending_post_devops_retries` and logs a skip message
- [ ] T013 [P] [US2] Add unit test in `backend/tests/unit/test_auto_merge.py` verifying DevOps retry cap — when `pipeline_metadata["devops_attempts"] >= 2`, `dispatch_devops_agent()` returns `False` without dispatching and the `devops_cap_reached` guard is hit

### Implementation for User Story 2

- [ ] T014 [US2] Implement `_check_devops_done_comment()` async helper function in `backend/src/services/copilot_polling/auto_merge.py` — accepts `access_token`, `owner`, `repo`, `issue_number`; calls GitHub REST API via `github_service.list_issue_comments()` with `per_page=10, direction="desc"` (newest first); returns `True` if any comment body contains `"devops: Done!"` substring (case-sensitive)
- [ ] T015 [US2] Implement `schedule_post_devops_merge_retry()` async function in `backend/src/services/copilot_polling/auto_merge.py` — accepts `access_token`, `owner`, `repo`, `issue_number`, `pipeline_metadata`, `project_id`; checks deduplication against `_pending_post_devops_retries` from `state.py`; creates `asyncio.create_task()` for `_post_devops_retry_loop()` inner coroutine that: (a) polls every `POST_DEVOPS_POLL_INTERVAL` up to `POST_DEVOPS_MAX_POLLS` times, (b) calls `_check_devops_done_comment()` each iteration, (c) on "Done!" found: sets `devops_active=False` in metadata, calls `_attempt_auto_merge()`, (d) if merge result is `"merged"`: broadcasts `post_devops_merge_completed` event and transitions to Done, (e) if merge result is `"devops_needed"`: re-dispatches DevOps via `dispatch_devops_agent()` (if under cap), (f) on timeout: broadcasts `auto_merge_failed` with reason `devops_timeout`, (g) always removes entry from `_pending_post_devops_retries` in finally block
- [ ] T016 [US2] Wire `schedule_post_devops_merge_retry()` call into `dispatch_devops_agent()` in `backend/src/services/copilot_polling/auto_merge.py` — after the existing successful dispatch logic (after `assign_copilot_to_issue()` returns True and metadata is updated), call `await schedule_post_devops_merge_retry(access_token, owner, repo, issue_number, pipeline_metadata, project_id)` before returning True

**Checkpoint**: US2 complete — DevOps dispatch triggers post-DevOps retry polling; "Done!" detection re-attempts merge; cap of 2 enforced

---

## Phase 5: User Story 3 — CI Events Proactively Trigger Merge and Recovery (Priority: P2)

**Goal**: Wire the existing stub webhook handlers so that `check_run` failure events proactively dispatch the DevOps agent and `check_suite` success events proactively trigger re-merge, providing a faster response path than polling alone.

**Independent Test**: Simulate a `check_suite` success webhook event for a PR linked to an auto-merge issue in "In Review" status. The system should call `_attempt_auto_merge()`. Simulate a `check_run` failure event — system should call `dispatch_devops_agent()`.

### Tests for User Story 3

- [ ] T017 [P] [US3] Add unit test in `backend/tests/unit/test_webhook_ci.py` verifying `handle_check_run_event()` calls `dispatch_devops_agent()` with failure context when `conclusion` is `"failure"` or `"timed_out"` and the PR is linked to an auto-merge issue. Mock PR-to-issue resolution and `dispatch_devops_agent()`.
- [ ] T018 [P] [US3] Add unit test in `backend/tests/unit/test_webhook_ci.py` verifying `handle_check_suite_event()` calls `_attempt_auto_merge()` when `conclusion` is `"success"` for a PR linked to an auto-merge issue in "In Review" status. Mock PR-to-issue resolution and `_attempt_auto_merge()`.
- [ ] T019 [P] [US3] Add unit test in `backend/tests/unit/test_webhook_ci.py` verifying both webhook handlers return `{"status": "ignored"}` with appropriate reason when the PR is not associated with any auto-merge issue or when the event is not actionable

### Implementation for User Story 3

- [ ] T020 [US3] Wire `handle_check_run_event()` in `backend/src/api/webhooks.py` (currently at ~line 750) — after the existing PR number extraction, add logic to: for each PR number, resolve the parent issue number (via pipeline state or `_issue_main_branches` cache reverse lookup), check if issue has auto-merge enabled in pipeline metadata, build `merge_result_context` from check_run data (`{"reason": "ci_failure", "failed_checks": [{"name": check_name, "conclusion": conclusion}]}`), and call `dispatch_devops_agent()` with the context. Add `devops_dispatched: bool` to the response dict per the `CheckRunHandlerResponse` contract schema
- [ ] T021 [US3] Wire `handle_check_suite_event()` in `backend/src/api/webhooks.py` (currently at ~line 784) — change the early-return guard from `conclusion != "failure"` to `conclusion not in ("failure", "success")` with reason `"conclusion_not_relevant"`. Add a new `conclusion == "success"` branch: for each PR, resolve parent issue number, check issue is "In Review" with auto-merge enabled, call `_attempt_auto_merge()`. Add `merge_attempted: bool` to response dict and use event `"check_suite_success"` per the `CheckSuiteHandlerResponse` contract schema

**Checkpoint**: US3 complete — CI failure webhook proactively dispatches DevOps; CI success webhook proactively triggers re-merge

---

## Phase 6: User Story 4 — System Recovers After Restart or Webhook Loss (Priority: P2)

**Goal**: Add a polling fallback in `check_in_review_issues()` that detects stalled "In Review" issues where a DevOps agent completed its work (posted "Done!") but the merge retry background task was lost due to server restart or webhook delivery failure.

**Independent Test**: Simulate a server restart scenario: set `devops_active=True` in pipeline metadata for an "In Review" issue, ensure no entry in `_pending_post_devops_retries`, mock a "Done!" comment on the issue. Run `check_in_review_issues()` and verify it calls `_attempt_auto_merge()`.

### Tests for User Story 4

- [ ] T022 [P] [US4] Create new test file `backend/tests/unit/test_pipeline_in_review_recovery.py` with unit tests verifying that `check_in_review_issues()` detects DevOps "Done!" comment for issues in "In Review" status with `devops_active=True` in pipeline metadata and no entry in `_pending_post_devops_retries`, then calls `_attempt_auto_merge()`. Mock `_check_devops_done_comment()`, pipeline state access, and `_attempt_auto_merge()`
- [ ] T023 [P] [US4] Add unit test in `backend/tests/unit/test_pipeline_in_review_recovery.py` verifying that `check_in_review_issues()` skips recovery for issues that do NOT have `devops_active=True` in metadata, or do NOT have auto-merge enabled, or already have an active entry in `_pending_post_devops_retries`

### Implementation for User Story 4

- [ ] T024 [US4] Add secondary DevOps recovery check in `check_in_review_issues()` in `backend/src/services/copilot_polling/pipeline.py` — after existing review checks, for each "In Review" issue: if `pipeline_metadata.get("devops_active")` is True AND `pipeline_metadata.get("auto_merge")` is True AND `issue_number` not in `_pending_post_devops_retries` (from `state.py`): call `_check_devops_done_comment()` (imported from `auto_merge.py`), if "Done!" found: set `devops_active=False`, call `_attempt_auto_merge()`, handle result (merged → Done, devops_needed → re-dispatch). This handles server restart recovery where background polling tasks are lost

**Checkpoint**: US4 complete — stalled "In Review" issues with completed DevOps work are recovered by periodic `check_in_review_issues()` polling

---

## Phase 7: User Story 5 — Failure Notifications for Unrecoverable Issues (Priority: P3)

**Goal**: Ensure clear, actionable failure notifications reach maintainers when all automated recovery options are exhausted — DevOps cap reached (2 attempts), polling timeout (~1 hour), or permanent merge failure.

**Independent Test**: Exhaust DevOps retry cap (2 failed attempts). Verify that a clear failure comment is posted on the issue and a `devops_cap_reached` broadcast event is sent.

### Tests for User Story 5

- [ ] T025 [P] [US5] Add unit test in `backend/tests/unit/test_auto_merge.py` verifying that when DevOps cap is reached (2 attempts), `dispatch_devops_agent()` broadcasts an `auto_merge_failed` event with reason `"devops_cap_reached"` via `connection_manager.broadcast_to_project()` and posts a failure comment on the issue explaining that human intervention is required
- [ ] T026 [P] [US5] Add unit test in `backend/tests/unit/test_auto_merge.py` verifying that when the post-DevOps polling loop reaches `POST_DEVOPS_MAX_POLLS` (30 cycles), `schedule_post_devops_merge_retry()` broadcasts an `auto_merge_failed` event with reason `"devops_timeout"` and posts a failure comment on the issue

### Implementation for User Story 5

- [ ] T027 [US5] Ensure `schedule_post_devops_merge_retry()` in `backend/src/services/copilot_polling/auto_merge.py` handles the timeout path: when `poll_count >= POST_DEVOPS_MAX_POLLS`, broadcast `auto_merge_failed` event with `{"type": "auto_merge_failed", "issue_number": issue_number, "reason": "devops_timeout"}` and post a descriptive issue comment explaining that the DevOps agent did not signal completion within the maximum polling window (~1 hour) and human intervention is required. This should be part of T015 implementation but verify/add if missing
- [ ] T028 [US5] Ensure `dispatch_devops_agent()` in `backend/src/services/copilot_polling/auto_merge.py` handles the cap-reached path: when `devops_attempts >= 2`, broadcast `auto_merge_failed` event with `{"type": "auto_merge_failed", "issue_number": issue_number, "reason": "devops_cap_reached"}` and post a descriptive issue comment explaining that the DevOps agent failed to resolve the issue after 2 attempts and human intervention is required. Verify existing guard logic and add broadcast/comment if missing

**Checkpoint**: US5 complete — maintainers receive clear notifications for all unrecoverable failure modes (cap reached, timeout, permanent merge failure)

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Linting, testing, diagram generation, and final validation across all modified files

- [ ] T029 [P] Run linting from `backend/`: `ruff check src/ tests/` and `ruff format --check src/ tests/` — fix any issues in modified files (`auto_merge.py`, `agents.py`, `webhooks.py`, `pipeline.py`, `state.py`, and all new/modified test files)
- [ ] T030 [P] Run full unit test suite from `backend/`: `uv run python -m pytest tests/unit/ -q` — verify no regressions across the ~4800 existing tests plus all new tests
- [ ] T031 [P] Run verification commands from `specs/770-auto-merge-devops-retry/quickstart.md`: targeted test runs for `test_auto_merge.py`, `test_webhook_ci.py`, `test_github_agents.py`, and `test_pipeline_in_review_recovery.py`
- [ ] T032 Run diagram generation script `./solune/scripts/generate-diagrams.sh` to check if agent registration changes in `agents.py` affect the backend-components.mmd or frontend-components.mmd architecture diagrams

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (constants used in registration context) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — verification of existing happy path
- **US2 (Phase 4)**: Depends on Phase 2 — core DevOps retry implementation
- **US3 (Phase 5)**: Depends on Phase 2 + Phase 4 (webhook handlers call `dispatch_devops_agent()` and `_attempt_auto_merge()`)
- **US4 (Phase 6)**: Depends on Phase 4 (uses `_check_devops_done_comment()` and `_pending_post_devops_retries`)
- **US5 (Phase 7)**: Depends on Phase 4 (adds failure notifications to retry functions)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Independent of other stories — verifies existing working code
- **US2 (P1)**: Depends only on Foundational (Phase 2) — can start immediately after
- **US3 (P2)**: Depends on US2 implementation (T014-T016 must be complete)
- **US4 (P2)**: Depends on US2 implementation (T014-T016 must be complete) — can proceed in parallel with US3
- **US5 (P3)**: Depends on US2 implementation (T015-T016 must be complete) — can proceed in parallel with US3/US4

### Within Each User Story

- Tests MUST be written FIRST and FAIL before implementation
- Helper functions before orchestration functions
- Core logic before wiring/integration
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1**: T001 and T002 modify different sections of `state.py` but are in the same file — execute sequentially
- **Phase 2**: T003 and T004 target different files — can run in parallel; T005 depends on T004
- **Phase 3**: T006 and T007 are independent test cases — can run in parallel
- **Phase 4**: T009-T013 (all tests) can run in parallel (same file but independent test functions); T014 → T015 → T016 must be sequential (each depends on the previous)
- **Phase 5**: T017-T019 (tests) can run in parallel; T020 and T021 modify different functions in the same file — can run in parallel
- **Phase 6**: T022 and T023 are in the same new file — can run in parallel; T024 depends on Phase 4
- **Phase 7**: T025 and T026 (tests) can run in parallel; T027 and T028 depend on Phase 4 implementation
- **Phase 8**: T029-T032 can all run in parallel

---

## Parallel Example: User Story 2 (DevOps Dispatch + Retry)

```bash
# Launch all tests for US2 together (they should FAIL before implementation):
Task: "T009 — Unit test for _check_devops_done_comment() in backend/tests/unit/test_auto_merge.py"
Task: "T010 — Unit test for schedule_post_devops_merge_retry() in backend/tests/unit/test_auto_merge.py"
Task: "T011 — Unit test for dispatch → retry wiring in backend/tests/unit/test_auto_merge.py"
Task: "T012 — Unit test for deduplication in backend/tests/unit/test_auto_merge.py"
Task: "T013 — Unit test for DevOps retry cap in backend/tests/unit/test_auto_merge.py"

# Then implement sequentially (each depends on the previous):
Task: "T014 — Implement _check_devops_done_comment() in auto_merge.py"
Task: "T015 — Implement schedule_post_devops_merge_retry() in auto_merge.py"  # depends on T014
Task: "T016 — Wire retry into dispatch_devops_agent() in auto_merge.py"       # depends on T015
```

---

## Parallel Example: User Story 3 (Webhook Wiring)

```bash
# Launch all tests together (they should FAIL before implementation):
Task: "T017 — Unit test for check_run failure → DevOps dispatch"
Task: "T018 — Unit test for check_suite success → re-merge"
Task: "T019 — Unit test for ignored events"

# Then implement (different functions, can be parallel):
Task: "T020 — Wire handle_check_run_event() in webhooks.py"
Task: "T021 — Wire handle_check_suite_event() in webhooks.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 + Foundational)

1. Complete Phase 1: Setup (constants + tracking structure)
2. Complete Phase 2: Foundational (DevOps template + registration)
3. Complete Phase 3: User Story 1 (verify happy path)
4. **STOP and VALIDATE**: Confirm existing auto-merge happy path works with DevOps agent registered
5. Deploy/demo if ready — auto-merge pipeline works end-to-end for the success path

### Incremental Delivery

1. Complete Setup + Foundational → DevOps agent exists and is registered
2. Add US1 → Verify happy path → **MVP achieved!**
3. Add US2 → DevOps dispatch + retry working → Test independently → Deploy
4. Add US3 + US4 (parallel) → Webhook fast-paths + recovery → Test independently → Deploy
5. Add US5 → Clear failure notifications → Test independently → Deploy
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 (quick verification) → then US2 (core implementation)
   - Developer B: waits for US2 T014-T016 → then US3 (webhook wiring)
   - Developer C: waits for US2 T014-T016 → then US4 (recovery fallback)
   - Developer D: waits for US2 T015-T016 → then US5 (failure notifications)
3. US3, US4, US5 can proceed in parallel once US2 implementation tasks are complete

---

## Notes

- [P] tasks = different files or independent test functions, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Write tests first, ensure they FAIL before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- The existing auto-merge code (happy path) is already working — verify, don't rewrite
- Follow existing code patterns: `BoundedDict` for deduplication, `asyncio.create_task()` for background tasks, `_cp` module-level imports for lazy dependencies
- All new async functions follow existing naming conventions: underscore-prefixed for internal helpers, `async def` throughout
- `AutoMergeResult` is a `@dataclass` — access attributes via `.status`, `.pr_number`, `.merge_commit` (not `.get()`)
- WebSocket broadcasts use `_cp.connection_manager.broadcast_to_project(project_id, {...})` pattern
