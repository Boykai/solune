# Tasks: Auto-generate Labels for GitHub Parent Issues

**Input**: Design documents from `/specs/001-auto-generate-labels/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Unit tests for the classifier service are recommended (plan.md §Test Optionality) but not mandated by the spec. Test tasks are included and marked OPTIONAL.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: All changes are backend-only under `solune/backend/`
- Source: `solune/backend/src/`
- Tests: `solune/backend/tests/unit/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new files and directory structure required by the feature

- [ ] T001 [P] Create label classification prompt template with dynamic taxonomy injection in `solune/backend/src/prompts/label_classification.py`. The module must expose a function that builds the system prompt by importing `LABELS` from `src.constants` (satisfying FR-010) and instructing the model to return a JSON object with a `labels` array. Truncate description input to 2,000 characters per RT-006.
- [ ] T002 [P] Implement category constants and `validate_labels()` pure function in `solune/backend/src/services/label_classifier.py`. Define `TYPE_LABELS`, `DEFAULT_TYPE_LABEL = "feature"`, and `ALWAYS_INCLUDED_LABEL = "ai-generated"`. Implement the post-processing pipeline from RT-004: filter against `constants.LABELS`, then perform order-preserving deduplication on the model-returned sequence (do not use unordered set-based deduplication that can reorder labels). Apply a deterministic ordering rule to the final `labels` array: (1) `ALWAYS_INCLUDED_LABEL` (`"ai-generated"`) must be present and at index 0; (2) ensure exactly one type label from `TYPE_LABELS` (if none remain after filtering, insert `DEFAULT_TYPE_LABEL = "feature"`), placing that type label immediately after `"ai-generated"` while preserving its first-seen position relative to other candidates; and (3) append all remaining non-type labels after these, in the order of their first occurrence in the model response after filtering and deduplication.

---

## Phase 2: Foundational — US4: Centralized Label Classification Service (Priority: P1)

**Goal**: Deliver the shared `classify_labels()` async function that all three issue creation paths will call. This is the foundational building block described in User Story 4.

**Independent Test**: Provide sample issue titles and descriptions to `classify_labels()` and verify it returns valid, relevant labels from the predefined taxonomy. Also test `validate_labels()` in isolation with various edge-case inputs.

**⚠️ CRITICAL**: No user story integration work (Phase 3–5) can begin until this phase is complete.

### Tests for US4 (OPTIONAL — recommended by plan.md) ⚠️

> **NOTE: Write these tests FIRST if following TDD; ensure they FAIL before implementation**

- [ ] T003 [P] [US4] Create unit tests for `validate_labels()` in `solune/backend/tests/unit/test_label_classifier.py`. Cover: taxonomy filtering (invalid labels removed), deduplication, `"ai-generated"` always present, exactly one type label (default `"feature"`), empty input returns `["ai-generated", "feature"]`, multiple type labels keeps first only, label ordering invariant: output labels MUST always be ordered by category as `[ "ai-generated", <type>, ...scope/domain labels ]`, with all non-type labels (scope/domain) appearing after the single type label in the deterministic order defined by `constants.LABELS`.
- [ ] T004 [P] [US4] Create unit tests for `classify_labels()` in `solune/backend/tests/unit/test_label_classifier.py`. Cover: successful classification with mocked `CompletionProvider` returning valid JSON, fallback to `["ai-generated", "feature"]` on AI failure (exception), fallback on invalid JSON response, fallback on empty/whitespace title and description, verify description truncation to 2,000 chars.

### Implementation for US4

- [ ] T005 [US4] Implement `classify_labels()` async function in `solune/backend/src/services/label_classifier.py`. Use the existing `CompletionProvider` abstraction (per RT-001) to make a single-shot AI call using the prompt from `label_classification.py`. Parse JSON response, pass through `validate_labels()`, and return the result. Wrap the entire call in try/except to catch all exceptions — on any failure, log at WARNING level and return `["ai-generated", "feature"]` as fallback (per RT-003). Accept `github_token` as a keyword argument for provider authentication.

**Checkpoint**: At this point, `classify_labels()` and `validate_labels()` should be fully functional and independently testable via unit tests.

---

## Phase 3: User Story 1 — Pipeline-Launched Issues Get Content-Based Labels (Priority: P1) 🎯 MVP

**Goal**: Parent issues created via pipeline launch receive content-based labels (type, scope, domain) instead of only hardcoded `["ai-generated"]` + `pipeline:<name>`.

**Independent Test**: Launch a pipeline with a descriptive issue title (e.g., "Optimize database query performance for the user dashboard") and verify the resulting parent issue contains content-appropriate labels (e.g., `"enhancement"`, `"backend"`, `"performance"`) in addition to `"ai-generated"` and the pipeline label. Verify fallback: if classification fails, issue still gets `["ai-generated"]` + pipeline label.

### Implementation for User Story 1

- [ ] T006 [US1] Integrate label classifier into `execute_pipeline_launch()` in `solune/backend/src/api/pipelines.py`. Replace the hardcoded `issue_labels = ["ai-generated"]` with a call to `classify_labels(title=..., description=..., github_token=session.access_token)`. After classification, append the `pipeline:<name>` label if not already present. On classification failure, fall back to current behavior: `["ai-generated"]` + pipeline label. Ensure existing pipeline-specific labels are preserved (FR-012).

**Checkpoint**: Pipeline-launched issues now receive content-derived labels. Verify with acceptance scenarios from spec.md US1.

---

## Phase 4: User Story 2 — Task-Created Issues Get Content-Based Labels (Priority: P2)

**Goal**: Parent issues created through the task creation flow receive content-based labels instead of zero labels.

**Independent Test**: Create a task with title "Fix login page accessibility issues" and verify the resulting parent issue receives labels such as `"bug"`, `"frontend"`, `"accessibility"`, and `"ai-generated"`. Verify fallback: if classification fails, issue still gets `["ai-generated"]`.

### Implementation for User Story 2

- [ ] T007 [US2] Integrate label classifier into `create_task()` in `solune/backend/src/api/tasks.py`. Before the `create_issue()` call, invoke `classify_labels(title=request.title, description=request.description or "", github_token=session.access_token)`. Pass the resulting labels to `create_issue()` via the `labels` parameter. On classification failure, fall back to `["ai-generated"]` (FR-009).

**Checkpoint**: Task-created issues now receive content-derived labels. Verify with acceptance scenarios from spec.md US2.

---

## Phase 5: User Story 3 — Agent Tool Issues Support Label Generation (Priority: P3)

**Goal**: Issues created through the AI agent's `create_project_issue` tool support automatic label generation when the agent does not explicitly specify labels, while respecting agent-provided labels when present.

**Independent Test**: Invoke the agent's issue creation tool without specifying labels and verify auto-generated content-based labels are applied. Then invoke it with explicit labels and verify agent-provided labels are used instead.

### Implementation for User Story 3

- [ ] T008 [US3] Add optional `labels: list[str] | None = None` parameter to `create_project_issue()` in `solune/backend/src/services/agent_tools.py`. Before the `create_issue()` call: if `labels` is provided (truthy), use agent-provided labels directly (per spec US3 scenario 2–3); otherwise, call `classify_labels(title=title, description=body, github_token=github_token)` to auto-generate labels. Pass the resulting labels to `create_issue()`. On classification failure, fall back to `["ai-generated"]` (FR-009).

**Checkpoint**: All three issue creation paths now use the shared label classifier. Verify with acceptance scenarios from spec.md US3.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and code quality checks across all changes

- [ ] T009 [P] Run linting and type checking on all new and modified files: `uv run ruff check src/services/label_classifier.py src/prompts/label_classification.py src/api/pipelines.py src/api/tasks.py src/services/agent_tools.py` and `uv run pyright src/services/label_classifier.py src/prompts/label_classification.py` from `solune/backend/`
- [ ] T010 [P] Run existing test suite to confirm no regressions: `uv run pytest tests/unit/ -v --tb=short` from `solune/backend/`
- [ ] T011 [P] Verify quickstart.md scenarios: Confirm all three integration points work end-to-end per the verification steps in `specs/001-auto-generate-labels/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — T001 and T002 can start immediately and run in parallel
- **Foundational / US4 (Phase 2)**: T005 depends on T001 (prompt template) and T002 (validate_labels). T003 and T004 (tests) can be written in parallel with T001/T002
- **User Stories (Phase 3–5)**: All depend on Phase 2 completion (T005 — classify_labels must be functional)
  - US1 (T006), US2 (T007), US3 (T008) can proceed **in parallel** — they modify different files
  - Or sequentially in priority order: P1 → P2 → P3
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **US4 (P1 — Foundational)**: Depends on Setup only. BLOCKS all other stories.
- **US1 (P1 — Pipeline)**: Depends on US4 completion. No dependencies on US2/US3.
- **US2 (P2 — Task)**: Depends on US4 completion. No dependencies on US1/US3.
- **US3 (P3 — Agent Tool)**: Depends on US4 completion. No dependencies on US1/US2.

### Within Each User Story

- Tests (if included) should be written first and FAIL before implementation
- Prompt template (T001) and validation logic (T002) before classify_labels (T005)
- Core service before integration points
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1**: T001 (prompt) and T002 (validate_labels) — different files, no dependencies
- **Phase 2 tests**: T003 and T004 — same file but independent test functions, can be written together
- **Phase 3–5**: T006, T007, T008 — all modify different files, can run fully in parallel after Phase 2
- **Phase 6**: T009 and T010 — independent validation commands

---

## Parallel Example: Setup Phase

```text
# Launch both setup tasks together (different files):
Task T001: "Create prompt template in solune/backend/src/prompts/label_classification.py"
Task T002: "Implement validate_labels() in solune/backend/src/services/label_classifier.py"
```

## Parallel Example: User Story Integration (Phase 3–5)

```text
# After Phase 2 (classify_labels) is complete, launch all integrations together:
Task T006: "Integrate classifier into pipelines.py"
Task T007: "Integrate classifier into tasks.py"
Task T008: "Integrate classifier into agent_tools.py"
```

---

## Implementation Strategy

### MVP First (User Story 4 + User Story 1)

1. Complete Phase 1: Setup (T001, T002) — parallel
2. Complete Phase 2: Foundational / US4 (T003–T005) — classifier service ready
3. Complete Phase 3: User Story 1 / Pipeline (T006)
4. **STOP and VALIDATE**: Test pipeline launch with descriptive issue → content-based labels appear
5. Deploy/demo if ready — pipeline path is the highest-impact fix

### Incremental Delivery

1. Setup + US4 → Classifier service ready (independently testable)
2. Add US1 (Pipeline) → Test independently → Deploy/Demo (**MVP!**)
3. Add US2 (Task) → Test independently → Deploy/Demo
4. Add US3 (Agent Tool) → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup (T001 ∥ T002) together
2. One developer completes US4 (T005) + tests (T003, T004)
3. Once US4 is done:
   - Developer A: US1 (T006 — pipelines.py)
   - Developer B: US2 (T007 — tasks.py)
   - Developer C: US3 (T008 — agent_tools.py)
4. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable after Phase 2
- US4 (Centralized Service) is labeled as Foundational because all other stories depend on it
- No new dependencies required — uses existing `CompletionProvider` and `constants.LABELS`
- No frontend changes — all modifications are in `solune/backend/`
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
