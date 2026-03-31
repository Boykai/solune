# Tasks: Auto-generate Labels for GitHub Parent Issues

**Input**: Design documents from `/specs/001-auto-generate-labels/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/label-classification.yaml, quickstart.md

**Tests**: Not mandated by spec (Constitution Principle IV — Test Optionality). Recommended unit tests for the classifier service are included in the Polish phase.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. User Story 4 (Centralized Label Classification Service) is mapped to the Foundational phase since it is the blocking prerequisite for all other stories.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web application (backend monorepo)**: `solune/backend/src/`, `solune/backend/tests/`
- All changes are backend-only within `solune/backend/`
- Paths are relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the prompt template that the label classification service depends on. No new dependencies, schema changes, or project initialization needed — this is an existing project.

- [ ] T001 Create label classification prompt template in `solune/backend/src/prompts/label_classification.py`

> **T001 Details**: Define a prompt-building function that produces system and user messages for the AI completion provider. The system prompt MUST dynamically inject the full label taxonomy from `constants.LABELS` (FR-010 — no hardcoded label values in the prompt). Include classification rules: return a JSON object `{"labels": [...]}`, select exactly one type label from the type category, select all applicable scope and domain labels, always include `"ai-generated"`. The user message template accepts `title: str` and `description: str` parameters. Reference existing prompt modules in `solune/backend/src/prompts/` (e.g., `issue_generation.py`) for style conventions.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the centralized `LabelClassificationService` — the shared capability that all three issue creation paths will call. This phase fulfills **User Story 4** (Centralized Label Classification Service, P1).

**⚠️ CRITICAL**: No user story integration work (Phases 3–5) can begin until this phase is complete.

- [ ] T002 Implement `validate_labels()` pure function with category constants in `solune/backend/src/services/label_classifier.py`
- [ ] T003 Implement `classify_labels()` async function with CompletionProvider integration and graceful fallback in `solune/backend/src/services/label_classifier.py`

> **T002 Details**: Create the `label_classifier.py` module. Define category constants referenced in `data-model.md`: `TYPE_LABELS: set[str]` (feature, bug, enhancement, refactor, documentation, testing, infrastructure), `DEFAULT_TYPE_LABEL: str = "feature"`, `ALWAYS_INCLUDED_LABEL: str = "ai-generated"`. Implement `validate_labels(raw_labels: list[str]) -> list[str]` as a pure function (no AI call) that: (1) filters labels against `constants.LABELS` using case-insensitive match with lowercase output, (2) deduplicates via set conversion, (3) ensures `"ai-generated"` is present at index 0, (4) ensures exactly one type label exists — defaults to `"feature"` if zero, keeps first if multiple, (5) returns labels ordered: `"ai-generated"` → type label → scope/domain labels. See `contracts/label-classification.yaml` `validate_labels` specification for the full behavioral contract.

> **T003 Details**: In the same `label_classifier.py` module, implement `async def classify_labels(title: str, description: str = "", *, github_token: str) -> list[str]`. The function: (1) returns default labels `["ai-generated", "feature"]` immediately if both title and description are empty/whitespace (edge case from spec), (2) truncates description to 2,000 characters (RT-006), (3) builds messages using the prompt template from T001, (4) calls `CompletionProvider.complete()` with `temperature=0.3`, `max_tokens=200`, and the `github_token` — reference `src/services/completion_providers.py` for the provider interface, (5) parses the JSON response to extract the `labels` array, (6) passes raw labels through `validate_labels()`, (7) wraps the entire classification in `try/except Exception` — on ANY failure, logs at `WARNING` level and returns `["ai-generated", "feature"]` as fallback (RT-003, FR-008, FR-009). Must complete within 3 seconds (SC-006). See `contracts/label-classification.yaml` for the full behavioral contract.

**Checkpoint**: The label classification service is functional — `classify_labels()` can be called with any title/description and will always return a valid label set. User Story 4 acceptance scenarios can be verified:
- Provide sample titles/descriptions → receive valid taxonomy labels
- `"ai-generated"` is always present, exactly one type label present
- Multi-scope inputs return all applicable scope labels
- Service never raises exceptions

---

## Phase 3: User Story 1 — Pipeline-Launched Issues Get Content-Based Labels (Priority: P1) 🎯 MVP

**Goal**: Parent issues created via pipeline launch receive AI-classified content-based labels (type, scope, domain) instead of only hardcoded `"ai-generated"` + pipeline label.

**Independent Test**: Launch a pipeline with a descriptive issue title (e.g., "Optimize database query performance for the user dashboard") and verify the resulting parent issue contains content-appropriate labels (e.g., `"enhancement"`, `"backend"`, `"database"`, `"performance"`) in addition to `"ai-generated"` and the pipeline label.

### Implementation for User Story 1

- [ ] T004 [P] [US1] Integrate label classifier into `execute_pipeline_launch()` with pipeline label merging in `solune/backend/src/api/pipelines.py`

> **T004 Details**: In `execute_pipeline_launch()` (~line 346), replace the hardcoded `issue_labels = ["ai-generated"]` with a call to `classify_labels()`. The integration pattern (from quickstart.md):
> ```python
> from src.services.label_classifier import classify_labels
>
> issue_labels = await classify_labels(
>     title=issue_title_override or _derive_issue_title(issue_description),
>     description=issue_description,
>     github_token=session.access_token,
> )
> if _pipeline_name:
>     pipeline_label = build_pipeline_label(_pipeline_name)
>     if pipeline_label not in issue_labels:
>         issue_labels.append(pipeline_label)
> ```
> Key requirements: (1) classified labels MERGE with pipeline-specific label (FR-012), (2) pipeline label is preserved and deduplicated (FR-005, FR-011), (3) on classification failure, fallback is handled internally by `classify_labels()` — the pipeline label is still appended regardless (FR-009), (4) existing `create_issue()` call already accepts `labels=` parameter — no change needed there.

**Checkpoint**: Pipeline-launched issues now receive content-based labels. Verify with US1 acceptance scenarios 1–3. This is the MVP — stop and validate here before proceeding.

---

## Phase 4: User Story 2 — Task-Created Issues Get Content-Based Labels (Priority: P2)

**Goal**: Parent issues created through the task creation flow receive AI-classified content-based labels instead of zero labels.

**Independent Test**: Create a task with title "Fix login page accessibility issues" and a description detailing screen reader problems. Verify the resulting parent issue receives relevant labels such as `"bug"`, `"frontend"`, `"accessibility"` along with `"ai-generated"`.

### Implementation for User Story 2

- [ ] T005 [P] [US2] Integrate label classifier into `create_task()` and pass labels to `create_issue()` in `solune/backend/src/api/tasks.py`

> **T005 Details**: In `create_task()` (~line 103), add a `classify_labels()` call before the existing `create_issue()` call and pass the result as the `labels` parameter. The integration pattern (from quickstart.md):
> ```python
> from src.services.label_classifier import classify_labels
>
> issue_labels = await classify_labels(
>     title=request.title,
>     description=request.description or "",
>     github_token=session.access_token,
> )
>
> issue = await github_projects_service.create_issue(
>     access_token=session.access_token,
>     owner=owner,
>     repo=repo,
>     title=request.title,
>     body=request.description or "",
>     labels=issue_labels,
> )
> ```
> Key requirements: (1) `labels=issue_labels` parameter added to `create_issue()` call — currently not passed (FR-006), (2) on classification failure, fallback is handled internally by `classify_labels()` returning `["ai-generated", "feature"]` (FR-009), (3) title-only classification must work when description is empty (US2 scenario 2).

**Checkpoint**: Task-created issues now receive content-based labels. Verify with US2 acceptance scenarios 1–3.

---

## Phase 5: User Story 3 — Agent Tool Issues Support Label Generation (Priority: P3)

**Goal**: Issues created through the AI agent's tool support automatic label generation when the agent doesn't explicitly specify labels, while respecting agent-provided labels when present.

**Independent Test**: Invoke the agent's `create_project_issue` tool without specifying labels and verify that the resulting issue receives auto-generated content-based labels. Then invoke with explicit labels and verify agent labels take precedence.

### Implementation for User Story 3

- [ ] T006 [P] [US3] Add optional `labels` parameter and integrate label classifier into `create_project_issue()` in `solune/backend/src/services/agent_tools.py`

> **T006 Details**: Two changes in `create_project_issue()` (~line 388):
>
> **(a) Add optional labels parameter to function signature:**
> ```python
> async def create_project_issue(
>     context: FunctionInvocationContext,
>     title: str,
>     body: str,
>     labels: list[str] | None = None,  # NEW
> ) -> ToolResult:
> ```
>
> **(b) Add label classification before the `create_issue()` call (~line 449):**
> ```python
> from src.services.label_classifier import classify_labels
>
> if labels:
>     issue_labels = labels
> else:
>     issue_labels = await classify_labels(
>         title=title,
>         description=body,
>         github_token=github_token,
>     )
>
> issue = await service.create_issue(
>     access_token=github_token,
>     owner=owner,
>     repo=repo,
>     title=title,
>     body=body,
>     labels=issue_labels,
> )
> ```
> Key requirements: (1) agent-provided labels take precedence — no merging with auto-generated labels (FR-007, US3 scenarios 2–3), (2) when no labels provided, auto-classify (US3 scenario 1), (3) on classification failure, fallback is handled internally by `classify_labels()` (FR-009), (4) the `labels` parameter must be optional with default `None` to maintain backward compatibility with existing agent tool invocations.

**Checkpoint**: All three issue creation paths now use the shared label classification service. Verify with US3 acceptance scenarios 1–3. All user stories should be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that validate and harden the implementation across all user stories.

- [ ] T007 [P] Create unit tests for `validate_labels()` and `classify_labels()` in `solune/backend/tests/unit/test_label_classifier.py`
- [ ] T008 [P] Run linting (`ruff check`) and type checking (`pyright`) on all new and modified files
- [ ] T009 Validate implementation against `specs/001-auto-generate-labels/quickstart.md` verification steps

> **T007 Details** (Recommended — not mandated by spec): Test cases to cover: (1) valid classification with mocked AI response returns expected labels, (2) fallback on AI failure returns `["ai-generated", "feature"]`, (3) `validate_labels` filters out labels not in taxonomy, (4) `validate_labels` deduplicates labels, (5) `validate_labels` defaults to `"feature"` when no type label present, (6) `validate_labels` keeps first type label when multiple present, (7) `validate_labels` always includes `"ai-generated"` at index 0, (8) empty/whitespace input returns default labels without AI call. Use `pytest-asyncio` for async tests and mock the `CompletionProvider`. Reference existing test patterns in `solune/backend/tests/unit/`.

> **T008 Details**: Run the following commands (from quickstart.md verification section):
> ```bash
> cd solune/backend
> uv run ruff check src/services/label_classifier.py src/prompts/label_classification.py
> uv run pyright src/services/label_classifier.py
> ```
> Also run against modified files: `src/api/pipelines.py`, `src/api/tasks.py`, `src/services/agent_tools.py`.

> **T009 Details**: Execute the full verification checklist from quickstart.md: run unit tests (if T007 completed), run existing test suite to confirm no regressions (`uv run pytest tests/unit/ -v --tb=short`), and verify the implementation matches the quickstart.md code samples.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (T003 uses prompt template from T001) — **BLOCKS all user stories**
- **User Stories (Phases 3–5)**: All depend on Phase 2 completion (T003 must be done)
  - User stories can proceed **in parallel** (different files, no cross-dependencies)
  - Or sequentially in priority order (US1 → US2 → US3)
- **Polish (Phase 6)**: Depends on all desired user story phases being complete

### User Story Dependencies

- **User Story 4 (P1)** → Phase 2 (Foundational): No dependencies on other stories — this IS the foundation
- **User Story 1 (P1)** → Phase 3: Depends on Phase 2 only — no dependencies on US2 or US3
- **User Story 2 (P2)** → Phase 4: Depends on Phase 2 only — no dependencies on US1 or US3
- **User Story 3 (P3)** → Phase 5: Depends on Phase 2 only — no dependencies on US1 or US2

### Task Dependency Graph

```text
T001 (prompt template)
  │
  └──► T003 (classify_labels — depends on T001 for prompt, T002 for validate)
        │
T002 (validate_labels)
  │    │
  └──► T003
        │
        ├──► T004 [US1] (pipelines.py)  ─┐
        ├──► T005 [US2] (tasks.py)       ├──► T007, T008, T009 (polish)
        └──► T006 [US3] (agent_tools.py) ─┘
```

### Within Each User Story

- Models before services (N/A — no new models for this feature)
- Services before endpoints (Phase 2 before Phases 3–5)
- Core implementation before integration (validate → classify → integrate)
- Story complete before moving to next priority (or parallelize across stories)

### Parallel Opportunities

- **Phase 2**: T001 and T002 are in different files and can be developed in parallel; T003 depends on both
- **Phases 3–5**: T004, T005, T006 are in different files with no cross-dependencies — all three can run in parallel once Phase 2 is complete
- **Phase 6**: T007 and T008 can run in parallel

---

## Parallel Example: User Story Integrations (Phases 3–5)

```bash
# After Phase 2 (Foundational) is complete, launch all integrations together:
Task T004: "Integrate label classifier into execute_pipeline_launch() in solune/backend/src/api/pipelines.py"
Task T005: "Integrate label classifier into create_task() in solune/backend/src/api/tasks.py"
Task T006: "Add labels parameter and integrate classifier into create_project_issue() in solune/backend/src/services/agent_tools.py"
```

## Parallel Example: Foundation (Phase 2)

```bash
# T001 and T002 can be developed in parallel (different files):
Task T001: "Create prompt template in solune/backend/src/prompts/label_classification.py"
Task T002: "Create validate_labels() in solune/backend/src/services/label_classifier.py"

# Then T003 (depends on both T001 and T002):
Task T003: "Implement classify_labels() in solune/backend/src/services/label_classifier.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001 — prompt template)
2. Complete Phase 2: Foundational (T002, T003 — classification service) → **Fulfills US4**
3. Complete Phase 3: User Story 1 (T004 — pipeline integration) → **Fulfills US1**
4. **STOP and VALIDATE**: Test US1 independently — launch a pipeline, verify content-based labels
5. Deploy/demo if ready — pipeline issues now have intelligent labels

### Incremental Delivery

1. Complete Setup + Foundational → Classification service ready (US4 ✓)
2. Add US1 (pipeline launch) → Test independently → Deploy/Demo (**MVP!**)
3. Add US2 (task creation) → Test independently → Deploy/Demo
4. Add US3 (agent tool) → Test independently → Deploy/Demo
5. Polish phase → Tests, linting, validation
6. Each story adds label coverage to a new issue creation path without breaking others

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (3 tasks)
2. Once Foundational is done:
   - Developer A: User Story 1 (T004 — `pipelines.py`)
   - Developer B: User Story 2 (T005 — `tasks.py`)
   - Developer C: User Story 3 (T006 — `agent_tools.py`)
3. Stories complete and integrate independently — no merge conflicts (different files)

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- US4 (Centralized Service) is mapped to Phase 2 (Foundational) since it is the prerequisite for all other stories
- Each user story integration (US1, US2, US3) is independently completable and testable
- All changes are backend-only — no frontend changes expected
- No new dependencies required — uses existing `CompletionProvider` infrastructure
- No database schema changes needed — label classification is stateless
- Classification failure NEVER blocks issue creation (FR-008, SC-003) — graceful fallback is built into `classify_labels()`
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Total new code: ~200–300 lines across 2 new files + 3 modified files
