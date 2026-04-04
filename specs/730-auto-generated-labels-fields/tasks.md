# Tasks: Auto-Generated Project Labels & Fields on Pipeline Launch

**Input**: Design documents from `/specs/730-auto-generated-labels-fields/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Included — plan.md specifies unit tests for the heuristic estimator and classifier extension.

**Organization**: Tasks are grouped by user story (P1 → P2 → P3) to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/src/`, `solune/backend/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new module skeleton required for the pipeline estimate feature

- [ ] T001 Create pipeline_estimate.py module with imports and constants in solune/backend/src/services/pipeline_estimate.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ No blocking prerequisites needed** — all required models (`IssueMetadata`, `IssuePriority`, `IssueSize` in `src/models/recommendation.py`) and services (`set_issue_metadata()` in `src/services/github_projects/projects.py`) already exist. Phase 1 completion unblocks all user stories.

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Auto-Set Project Fields on Pipeline Launch (Priority: P1) 🎯 MVP

**Goal**: When a pipeline is launched, automatically compute Priority, Size, Estimate, Start date, and Target date from the agent count and set them on the project board item via `set_issue_metadata()`.

**Independent Test**: Launch a pipeline with 3 configured agents. Verify the parent issue's project fields show Estimate ≈ 0.75 h, Size = S, Priority = P2, Start date = today, Target date = today + 1 day.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T002 [P] [US1] Write unit tests for size_from_hours() boundary cases and estimate_from_agent_count() with agent counts 0, 1, 2, 3, 4, 5, 8, 9, 16, 17, 20 in solune/backend/tests/unit/test_pipeline_estimate.py
- [ ] T003 [P] [US1] Write unit tests for metadata integration in pipeline launch verifying set_issue_metadata() is called after add_to_project_with_backlog() and failures are logged without raising exceptions in solune/backend/tests/unit/test_api_pipelines.py

### Implementation for User Story 1

- [ ] T004 [US1] Implement size_from_hours() pure function mapping estimate hours to IssueSize enum (XS ≤ 0.5, S ≤ 1.0, M ≤ 2.0, L ≤ 4.0, XL > 4.0) in solune/backend/src/services/pipeline_estimate.py
- [ ] T005 [US1] Implement estimate_from_agent_count() returning IssueMetadata with estimate_hours from formula max(0.5, min(8.0, agent_count * 0.25)), size from size_from_hours(), priority P2, start_date today UTC, target_date today + ceil(hours/8) days in solune/backend/src/services/pipeline_estimate.py
- [ ] T006 [US1] Integrate estimate computation and set_issue_metadata() call with non-blocking try/except error handling after add_to_project_with_backlog() in solune/backend/src/api/pipelines.py

**Checkpoint**: At this point, User Story 1 should be fully functional — every pipeline launch auto-populates project fields with heuristic-derived metadata. Testable independently.

---

## Phase 4: User Story 2 — AI-Driven Priority Override for Urgent Issues (Priority: P2)

**Goal**: Extend the AI label classifier to optionally detect urgency signals (e.g., "critical security vulnerability", "production outage") and return a priority suggestion (P0 or P1) that overrides the default P2.

**Independent Test**: Submit an issue with the title "Critical security vulnerability in authentication module" through the classifier. Verify that the returned priority is P0 or P1 rather than the default P2.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T007 [P] [US2] Write unit tests for ClassificationResult dataclass and classify_labels_with_priority() covering urgency detection, no-urgency fallback, AI timeout fallback, and invalid priority value handling in solune/backend/tests/unit/test_label_classifier.py

### Implementation for User Story 2

- [ ] T008 [P] [US2] Add frozen ClassificationResult dataclass with labels list and optional IssuePriority priority field to solune/backend/src/services/label_classifier.py
- [ ] T009 [P] [US2] Extend label classification system prompt with optional priority key and urgency detection rules (P0 for production outage/data loss/security breach, P1 for critical bug/security vulnerability/major functionality broken, null for all others) in solune/backend/src/prompts/label_classification.py
- [ ] T010 [US2] Implement classify_labels_with_priority() async function that wraps the AI provider call, parses both labels and optional priority from JSON response, validates priority against IssuePriority enum, and returns ClassificationResult with priority=None on any failure or missing priority in solune/backend/src/services/label_classifier.py
- [ ] T011 [US2] Replace classify_labels() with classify_labels_with_priority() in the pipeline launch path and merge AI-suggested priority into heuristic metadata (override P2 default when AI returns a valid priority) in solune/backend/src/api/pipelines.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently — pipeline launch auto-populates metadata and urgent issues get elevated priority.

---

## Phase 5: User Story 3 — Verify Existing Label Lifecycle Integrity (Priority: P3)

**Goal**: Confirm that existing label lifecycles (agent assignment, stalled detection/removal, pipeline labels) continue to function correctly alongside the new metadata-setting behavior with zero regressions.

**Independent Test**: Run the existing label lifecycle test suite (agent swap tests, stalled label tests, pipeline label tests) after integrating the metadata-setting changes and verify all tests pass without modification.

### Verification for User Story 3

- [ ] T012 [P] [US3] Verify existing agent label swap tests (_swap_agent_labels) pass unchanged after metadata integration in solune/backend/tests/
- [ ] T013 [P] [US3] Verify existing stalled label detection and removal tests pass unchanged after metadata integration in solune/backend/tests/
- [ ] T014 [P] [US3] Verify existing pipeline label persistence tests pass unchanged after metadata integration in solune/backend/tests/
- [ ] T015 [US3] Run full backend test suite and confirm all existing label lifecycle tests pass without modification using uv run pytest in solune/backend/

**Checkpoint**: All user stories are independently functional — metadata auto-population, AI priority override, and label lifecycle integrity all verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T016 [P] Add observability logging for computed metadata values (priority, size, estimate, start_date, target_date, agent_count) in solune/backend/src/services/pipeline_estimate.py
- [ ] T017 Run quickstart.md verification steps to validate end-to-end flow in specs/730-auto-generated-labels-fields/quickstart.md
- [ ] T018 Run full backend test suite with coverage check (target ≥ 75%) using uv run pytest --cov=src --cov-report=json in solune/backend/

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Skipped — no blocking prerequisites needed
- **User Story 1 (Phase 3)**: Depends on Setup (Phase 1) completion
- **User Story 2 (Phase 4)**: Depends on User Story 1 completion (needs the metadata integration point in pipelines.py)
- **User Story 3 (Phase 5)**: Depends on User Story 1 and User Story 2 completion (verification of final state)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 1 — no dependencies on other stories
- **User Story 2 (P2)**: Depends on US1 completion — uses the metadata integration point created by T006 in pipelines.py to merge AI priority
- **User Story 3 (P3)**: Depends on US1 and US2 — verifies all changes together produce no regressions

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Pure functions (size_from_hours) before composite functions (estimate_from_agent_count)
- Data structures (ClassificationResult) before service logic (classify_labels_with_priority)
- Service logic before integration (pipelines.py modifications)
- Story complete and verified before moving to next priority

### Parallel Opportunities

- **Phase 1**: Single task (T001)
- **Phase 3 Tests**: T002 and T003 can run in parallel (different test files)
- **Phase 4 Tests**: T007 can run in parallel with any Phase 3 implementation task
- **Phase 4 Implementation**: T008 and T009 can run in parallel (label_classifier.py and label_classification.py are different files)
- **Phase 5**: T012, T013, and T014 can all run in parallel (independent verification tasks)
- **Phase 6**: T016 can run in parallel with T017

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "T002 - Unit tests for size_from_hours() and estimate_from_agent_count() in tests/unit/test_pipeline_estimate.py"
Task: "T003 - Unit tests for metadata integration in tests/unit/test_api_pipelines.py"
```

## Parallel Example: User Story 2

```bash
# Launch tests and data structure creation together:
Task: "T007 - Unit tests for ClassificationResult and classify_labels_with_priority() in tests/unit/test_label_classifier.py"

# Then launch parallel implementation:
Task: "T008 - Add ClassificationResult dataclass in src/services/label_classifier.py"
Task: "T009 - Extend prompt with priority rules in src/prompts/label_classification.py"
```

## Parallel Example: User Story 3

```bash
# Launch all verification tasks together:
Task: "T012 - Verify agent label swap tests"
Task: "T013 - Verify stalled label tests"
Task: "T014 - Verify pipeline label tests"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 3: User Story 1 (T002–T006)
3. **STOP and VALIDATE**: Test User Story 1 independently
4. Every pipeline launch now auto-populates project fields — deploy/demo ready

### Incremental Delivery

1. T001 → Setup complete
2. T002–T006 → User Story 1 complete → Test independently → **MVP deployed!**
3. T007–T011 → User Story 2 complete → Test independently → Urgent issues auto-prioritized
4. T012–T015 → User Story 3 complete → Label lifecycle verified
5. T016–T018 → Polish complete → Observability and coverage validated
6. Each story adds value without breaking previous stories

### Key Files Changed

| File | Change | Story | Description |
|------|--------|-------|-------------|
| `src/services/pipeline_estimate.py` | NEW | US1 | Heuristic estimate from agent count |
| `src/services/label_classifier.py` | MODIFIED | US2 | ClassificationResult + classify_labels_with_priority() |
| `src/prompts/label_classification.py` | MODIFIED | US2 | Extended prompt with optional priority |
| `src/api/pipelines.py` | MODIFIED | US1, US2 | Metadata integration + AI priority override |
| `tests/unit/test_pipeline_estimate.py` | NEW | US1 | Heuristic tests |
| `tests/unit/test_label_classifier.py` | MODIFIED | US2 | Priority parsing tests |
| `tests/unit/test_api_pipelines.py` | MODIFIED | US1 | Metadata integration tests |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing (TDD)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Metadata failures MUST NOT abort pipeline launch — log and continue
- No new external dependencies required
- No frontend changes needed — project fields render automatically from GitHub Projects API
