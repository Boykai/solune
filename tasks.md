---
description: "Task list for reducing broad-except + log + continue pattern"
---

# Tasks: Reduce Broad-Except + Log + Continue Pattern

**Input**: Design documents from `/specs/002-reduce-broad-except/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Requested for Workstream B only. The `_best_effort()` helper is novel code and requires a unit test covering 5 cases per `contracts/best-effort-helper-contract.md` § B6. Workstream A is validated by `uv run ruff check` exit status and canary experiments — no pytest tests are added.

**Organization**: Tasks are grouped by user story. US1–US3 form Workstream A (lint policy); US4 forms Workstream B (domain-error helper). The two workstreams are independently deliverable (FR-010). Within Workstream A, stories are sequential (US1 → US2 → US3). US4 depends only on the Foundational phase and can run in parallel with US2/US3.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)

## Path Conventions

Web app structure (per plan.md). All edits live under `solune/backend/`. Paths are repo-relative from the workspace root `/home/runner/work/solune/solune/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Capture pre-feature baselines that downstream phases verify against.

- [ ] T001 Capture baseline `except Exception` handler count across `solune/backend/src/`: run `grep -rc "except Exception" solune/backend/src/ | awk -F: '{s+=$2} END{print s}'` from the workspace root and record the result in the PR description as `Baseline except Exception count: <N>` (spec estimates ~568 across ~87 files).
- [ ] T002 [P] Capture baseline file count: run `grep -rl "except Exception" solune/backend/src/ | wc -l` and record as `Baseline files with except Exception: <N>` (spec estimates ~87 files).

**Checkpoint**: Baselines recorded. No code changes yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

> No foundational work is required. The Ruff linter is already configured in `solune/backend/pyproject.toml` and runs in CI via `.github/workflows/ci.yml`. The existing test suite, type checker, and linter infrastructure are all in place. Adding `"BLE"` to the `select` list (US1) is the first code change.

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 — Enable Lint Rule for Broad Exception Handlers (Priority: P1) 🎯 MVP

**Goal**: Add `"BLE"` to the Ruff `select` list so that every unjustified `except Exception` handler is reported as a BLE001 violation. CI immediately blocks new violations.

**Independent Test**: After US1 lands, run the linter on a canary file containing an untagged `except Exception` handler — it must fail. Run it on a canary file with the approved `# noqa: BLE001 — reason:` tag — it must pass. (Spec US1 Acceptance Scenarios 1, 2, 3.)

### Implementation for User Story 1

- [ ] T003 [US1] Add `"BLE",  # flake8-blind-except (ban broad except Exception handlers)` to the `select` list in `[tool.ruff.lint]` of [solune/backend/pyproject.toml](solune/backend/pyproject.toml) — insert after `"B"` and before `"C4"` per `contracts/ruff-config-contract.md` § C1. Verify no entry is added to `ignore` or `per-file-ignores` for BLE001 (§ C2).
- [ ] T004 [US1] Run `cd solune/backend && uv run ruff check src/ --select BLE001 --statistics` to confirm violations are reported; record the total violation count and top-10 files in the PR description. Expected: ~568 violations across ~87 files (research R3).
- [ ] T005 [US1] Verify canary (Acceptance Scenario US1.2): create a temporary file with an untagged `except Exception` handler, run `uv run ruff check` against it with `--select BLE001`; confirm exit non-zero. Delete the canary file. Record output in PR description.
- [ ] T006 [US1] Verify canary (Acceptance Scenario US1.3): create a temporary file with `except Exception:  # noqa: BLE001 — reason: test canary`, run `uv run ruff check` against it with `--select BLE001`; confirm exit 0. Delete the canary file. Record output in PR description.

**Checkpoint**: BLE001 is active. CI now blocks new unjustified broad-except handlers (SC-002). Full lint will fail until US2 triage is complete — this is expected.

---

## Phase 4: User Story 2 — Triage and Narrow Existing Broad Handlers (Priority: P2)

**Goal**: Resolve every existing `except Exception` handler into one of three buckets: **Narrow** (replace with specific exception types), **Promote** (remove handler entirely), or **Tagged** (retain with `# noqa: BLE001 — reason:` justification). After triage, `uv run ruff check` passes with zero BLE001 violations.

**Independent Test**: Run `uv run ruff check src/ --select BLE001` after triage — must exit 0. Run the full test suite — must pass with zero regressions. Verify tagged handler count is below the 15% ceiling (~85 of ~568). (Spec US2 Acceptance Scenarios 1–4.)

### Triage: Large files (dedicated PRs per research R8)

> Each large file (>30 handlers) gets its own triage task. Use `data-model.md` § E6 for narrowing targets. Common patterns: `aiosqlite.Error` for database calls, `httpx.HTTPStatusError | httpx.ConnectError | httpx.TimeoutException` for HTTP calls, `json.JSONDecodeError` for JSON parsing, `OSError` for filesystem operations, `KeyError`/`ValueError` for data access.

- [ ] T007 [US2] Triage all `except Exception` handlers in [solune/backend/src/services/copilot_polling/pipeline.py](solune/backend/src/services/copilot_polling/pipeline.py) (~47 handlers). Narrow database operations to `aiosqlite.Error`, HTTP calls to `httpx.HTTPStatusError | httpx.TimeoutException`, and JSON parsing to `json.JSONDecodeError`. Tag genuinely unbounded handlers with `# noqa: BLE001 — reason:`. Run `uv run ruff check src/services/copilot_polling/pipeline.py --select BLE001`; MUST exit 0.
- [ ] T008 [P] [US2] Triage all `except Exception` handlers in [solune/backend/src/api/chat.py](solune/backend/src/api/chat.py) (~41 handlers). Narrow JSON/database/HTTP operations to specific types per `data-model.md` § E6. Tag unbounded handlers (e.g., plugin hooks, third-party callbacks). Run `uv run ruff check src/api/chat.py --select BLE001`; MUST exit 0.
- [ ] T009 [P] [US2] Triage all `except Exception` handlers in [solune/backend/src/services/workflow_orchestrator/orchestrator.py](solune/backend/src/services/workflow_orchestrator/orchestrator.py) (~32 handlers). Narrow to specific types. Tag genuinely unbounded handlers. Run `uv run ruff check src/services/workflow_orchestrator/orchestrator.py --select BLE001`; MUST exit 0.

### Triage: Medium files (batched by directory)

- [ ] T010 [P] [US2] Triage all `except Exception` handlers in [solune/backend/src/services/app_service.py](solune/backend/src/services/app_service.py) (~19 handlers). Narrow to specific types per `data-model.md` § E6. Run `uv run ruff check src/services/app_service.py --select BLE001`; MUST exit 0.
- [ ] T011 [P] [US2] Triage all `except Exception` handlers in [solune/backend/src/main.py](solune/backend/src/main.py) (~18 handlers). Narrow database operations to `aiosqlite.Error | OSError`, HTTP calls to specific httpx types. Run `uv run ruff check src/main.py --select BLE001`; MUST exit 0.
- [ ] T012 [P] [US2] Triage all `except Exception` handlers in [solune/backend/src/services/copilot_polling/helpers.py](solune/backend/src/services/copilot_polling/helpers.py) (~16 handlers) and [solune/backend/src/services/copilot_polling/recovery.py](solune/backend/src/services/copilot_polling/recovery.py) (~15 handlers). Narrow to specific types. Run `uv run ruff check src/services/copilot_polling/ --select BLE001`; MUST exit 0 for both files.

### Triage: GitHub-projects service files (Tagged → refactored in US4)

> These files contain the "best-effort HTTP wrapper" pattern targeted by Workstream B. Simple best-effort handlers are **Tagged** now (temporary `# noqa: BLE001 — reason: best-effort HTTP wrapper; will migrate to _best_effort() in Workstream B`) and will be replaced by `_best_effort()` calls in US4. Non-HTTP handlers in these files should be **Narrowed** to specific types.

- [ ] T013 [P] [US2] Triage `except Exception` handlers in [solune/backend/src/services/github_projects/copilot.py](solune/backend/src/services/github_projects/copilot.py) (~14 handlers). Tag best-effort HTTP wrappers; Narrow non-HTTP handlers to specific types. Run `uv run ruff check src/services/github_projects/copilot.py --select BLE001`; MUST exit 0.
- [ ] T014 [P] [US2] Triage `except Exception` handlers in [solune/backend/src/services/github_projects/issues.py](solune/backend/src/services/github_projects/issues.py) (~15 handlers). Tag best-effort HTTP wrappers; Narrow non-HTTP handlers. Run `uv run ruff check src/services/github_projects/issues.py --select BLE001`; MUST exit 0.
- [ ] T015 [P] [US2] Triage `except Exception` handlers in [solune/backend/src/services/github_projects/pull_requests.py](solune/backend/src/services/github_projects/pull_requests.py) (~12 handlers). Tag best-effort HTTP wrappers; Narrow non-HTTP handlers. Run `uv run ruff check src/services/github_projects/pull_requests.py --select BLE001`; MUST exit 0.
- [ ] T016 [P] [US2] Triage `except Exception` handlers in [solune/backend/src/services/github_projects/projects.py](solune/backend/src/services/github_projects/projects.py) (~11 handlers). Tag best-effort HTTP wrappers; Narrow non-HTTP handlers. Run `uv run ruff check src/services/github_projects/projects.py --select BLE001`; MUST exit 0.
- [ ] T017 [P] [US2] Triage `except Exception` handlers in [solune/backend/src/services/github_projects/service.py](solune/backend/src/services/github_projects/service.py) — specifically the `_with_fallback()` internals and any other handlers. Tag `_with_fallback()` broad catches with `# noqa: BLE001 — reason: _with_fallback() strategy chain catches arbitrary callee exceptions`. Narrow others. Run `uv run ruff check src/services/github_projects/service.py --select BLE001`; MUST exit 0.

### Triage: Remaining files

- [ ] T018 [P] [US2] Triage all `except Exception` handlers in remaining files under [solune/backend/src/api/](solune/backend/src/api/) (excluding `chat.py` from T008). Batch by file; Narrow or Tag each handler. Run `uv run ruff check src/api/ --select BLE001`; MUST exit 0.
- [ ] T019 [P] [US2] Triage all `except Exception` handlers in remaining files under [solune/backend/src/services/](solune/backend/src/services/) (excluding files already covered in T007, T009–T017). Batch by file; Narrow or Tag each handler. Run `uv run ruff check src/services/ --select BLE001`; MUST exit 0.
- [ ] T020 [P] [US2] Triage all `except Exception` handlers in remaining files under [solune/backend/src/](solune/backend/src/) not yet covered by T007–T019 (e.g., `src/dependencies.py`, `src/exceptions.py`, `src/utils.py`, and any other top-level modules). Narrow or Tag each handler. Run `uv run ruff check src/ --select BLE001`; MUST exit 0 for each file.

### Verification (after all triage tasks complete)

- [ ] T021 [US2] Run `cd solune/backend && uv run ruff check src/ --select BLE001`; MUST exit 0 (SC-001, FR-003). Zero unresolved BLE001 violations across the entire backend.
- [ ] T022 [US2] Verify tagged handler ceiling (SC-003): run `grep -rc "noqa: BLE001" solune/backend/src/ | awk -F: '{s+=$2} END{print s}'` and confirm the count is fewer than 85 (15% of ~568). Record the count in the PR description.
- [ ] T023 [US2] Run full lint `cd solune/backend && uv run ruff check`; MUST exit 0. No regressions in any other lint rules.
- [ ] T024 [US2] Run test suite `cd solune/backend && uv run pytest`; MUST pass with zero failures (FR-011, SC-006). No production behaviour changes.

**Checkpoint**: All existing broad-except handlers resolved. Lint passes clean. Test suite green. Workstream A triage complete.

---

## Phase 5: User Story 3 — Adopt a Justification Tag Convention (Priority: P3)

**Goal**: Document the `# noqa: BLE001 — reason:` tag convention so that contributors know the format, when to use it, and can find the documentation within 2 minutes (SC-005).

**Independent Test**: Search `solune/backend/README.md` for "BLE001" — must find format specification, decision flowchart, and ≥3 examples. Verify all existing tags in the codebase follow the documented format. (Spec US3 Acceptance Scenarios 1–3.)

### Implementation for User Story 3

- [ ] T025 [US3] Add a "Broad Exception Handling Convention" section to [solune/backend/README.md](solune/backend/README.md) per `contracts/tag-convention-contract.md` § T4. Include: (1) the canonical `# noqa: BLE001 — reason:` format specification, (2) the decision flowchart from § T3 (Narrow → Promote → Tag), (3) at least 3 examples covering common Tagged scenarios (third-party callback, asyncio.TaskGroup drain, best-effort helper, startup resilience), and (4) a cross-reference to `specs/002-reduce-broad-except/contracts/tag-convention-contract.md` for full details.
- [ ] T026 [US3] Verify all existing `# noqa: BLE001` tags follow the convention: run `grep -rn "noqa: BLE001" solune/backend/src/ | grep -v "reason:"` — MUST return empty output (FR-004). Every suppression has a `— reason:` suffix with non-empty justification text.
- [ ] T027 [US3] Verify convention findability (SC-005): confirm `grep -c "BLE001" solune/backend/README.md` returns ≥1, and that the section contains format, when-to-use, and examples. A new contributor should find the convention within 2 minutes of opening the backend README.

**Checkpoint**: Tag convention documented and verified. Workstream A complete.

---

## Phase 6: User Story 4 — Introduce a Domain-Error Helper for Best-Effort HTTP Calls (Priority: P4)

**Goal**: Add a `_best_effort()` async helper to `_ServiceMixin` and refactor the ~50 ad-hoc "try → call → log → return fallback" handlers in the GitHub-projects service files to use it. Reduce duplicated error-handling code by ≥80% in those files (SC-004).

**Independent Test**: After US4 lands, verify that callers using the helper produce identical logging output and fallback values. Run the full test suite — must pass. Verify no `except Exception` handlers remain in the target files outside `_with_fallback()` internals. (Spec US4 Acceptance Scenarios 1–4.)

### Tests for User Story 4

> Tests per `contracts/best-effort-helper-contract.md` § B6. The helper is novel code; tests validate the contract before refactoring call sites.

- [ ] T028 [US4] Create unit test file [solune/backend/tests/unit/test_best_effort.py](solune/backend/tests/unit/test_best_effort.py) with 5 test cases per § B6: (1) success path — `fn` returns a value, `_best_effort` returns it; (2) failure path — `fn` raises `ValueError`, `_best_effort` returns `fallback` and logs at the specified level; (3) non-catchable — `fn` raises `KeyboardInterrupt`, exception propagates; (4) custom log level — `log_level=logging.WARNING`, log emitted at WARNING; (5) kwargs forwarding — `fn` receives the correct `*args` and `**kwargs`.

### Implementation for User Story 4

- [ ] T029 [US4] Implement `_best_effort()` method on `_ServiceMixin` in [solune/backend/src/services/github_projects/service.py](solune/backend/src/services/github_projects/service.py) per `contracts/best-effort-helper-contract.md` § B1–B3. Include the `# noqa: BLE001 — reason: canonical best-effort wrapper; callers pass context` tag on the `except Exception` line. Add required imports (`logging`, `Callable`, `Awaitable`, `TypeVar`, `Any`).
- [ ] T030 [US4] Run type check `cd solune/backend && uv run pyright src/services/github_projects/service.py`; MUST exit 0. Run lint `uv run ruff check src/services/github_projects/service.py`; MUST exit 0.
- [ ] T031 [US4] Run unit tests `cd solune/backend && uv run pytest tests/unit/test_best_effort.py -v`; all 5 test cases MUST pass.

### Refactor: Replace ad-hoc handlers with `_best_effort()` calls

> For each file, replace simple "try → call → log → return fallback" handlers with `_best_effort()` per `contracts/best-effort-helper-contract.md` § B4. DO NOT migrate: handlers using `_with_fallback()`, cascading fallback logic, conservative assumption returns, or retry/backoff logic (§ B5). Remove the temporary `# noqa: BLE001` tags from migrated handlers — they no longer have `except Exception` clauses.

- [ ] T032 [P] [US4] Refactor eligible `except Exception` handlers in [solune/backend/src/services/github_projects/pull_requests.py](solune/backend/src/services/github_projects/pull_requests.py) (~12 handlers) to use `_best_effort()`. Preserve existing log messages as `context` parameters and fallback values. Remove `# noqa: BLE001` tags from migrated call sites.
- [ ] T033 [P] [US4] Refactor eligible `except Exception` handlers in [solune/backend/src/services/github_projects/projects.py](solune/backend/src/services/github_projects/projects.py) (~11 handlers) to use `_best_effort()`. Preserve logging behaviour and fallback values.
- [ ] T034 [P] [US4] Refactor eligible `except Exception` handlers in [solune/backend/src/services/github_projects/copilot.py](solune/backend/src/services/github_projects/copilot.py) (~14 handlers) to use `_best_effort()`. Preserve logging behaviour and fallback values.
- [ ] T035 [P] [US4] Refactor eligible `except Exception` handlers in [solune/backend/src/services/github_projects/issues.py](solune/backend/src/services/github_projects/issues.py) (~15 handlers) to use `_best_effort()`. Preserve logging behaviour and fallback values.

### Verification (after all refactoring complete)

- [ ] T036 [US4] Verify reduction in `except Exception` handlers in target files: for each of `pull_requests.py`, `projects.py`, `copilot.py`, `issues.py`, run `grep -c "except Exception" <file>` and confirm significant reduction (zero for simple best-effort handlers; only `_with_fallback()` internals and non-eligible patterns may remain).
- [ ] T037 [US4] Run lint `cd solune/backend && uv run ruff check src/services/github_projects/`; MUST exit 0.
- [ ] T038 [US4] Run full test suite `cd solune/backend && uv run pytest`; MUST pass with zero failures (SC-006, FR-011). No production behaviour changes — logging output and fallback values are preserved.

**Checkpoint**: `_best_effort()` helper live. Ad-hoc handlers consolidated. Workstream B complete.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across both workstreams and cross-cutting verification.

- [ ] T039 Run full lint `cd solune/backend && uv run ruff check`; MUST exit 0. Confirm zero BLE001 violations and no regressions in other rules.
- [ ] T040 Run full test suite `cd solune/backend && uv run pytest`; MUST pass with zero failures.
- [ ] T041 Run quickstart.md end-to-end validation per [specs/002-reduce-broad-except/quickstart.md](specs/002-reduce-broad-except/quickstart.md): execute Steps A1–A4 verification commands and Steps B1–B3 verification commands. All checks must pass.
- [ ] T042 Verify cross-workstream independence (FR-010): confirm that Workstream A changes (pyproject.toml config, handler triage, README docs) and Workstream B changes (_best_effort helper, service refactors) are in separate commits/PRs with no circular dependencies.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** — T001, T002 — no dependencies; run anytime before opening the US1 PR.
- **Foundational (Phase 2)** — none.
- **User Story 1 (Phase 3)** — depends on Setup baselines for reporting only (T001, T002 values recorded in PR description).
- **User Story 2 (Phase 4)** — depends on US1 having merged (BLE001 must be active so triage tags are validated by the linter).
- **User Story 3 (Phase 5)** — depends on US2 having merged (the convention documentation references the tags applied during triage; tags must exist to verify against).
- **User Story 4 (Phase 6)** — depends on US1 having merged (BLE001 must be active). Does NOT depend on US2 or US3 — the `_best_effort()` helper can be implemented and tested independently. However, if US2 has already tagged the github_projects/ handlers, US4 replaces those tags with helper calls.
- **Polish (Phase 7)** — depends on all desired user stories being complete.

### Within Each User Story

- **US1**: T003 (config edit) → T004 (verify violations) → T005 + T006 (canaries, sequential — share temp files).
- **US2**: T007–T020 (triage tasks, all parallelizable across files) → T021 (verify zero violations) → T022 (verify tag ceiling) → T023 (full lint) → T024 (test suite).
- **US3**: T025 (write documentation) → T026 (verify tag compliance) → T027 (verify findability).
- **US4**: T028 (write tests) → T029 (implement helper) → T030 (type check + lint) → T031 (run tests) → T032–T035 (refactor files, parallelizable) → T036 (verify reduction) → T037 (lint) → T038 (test suite).

### Parallel Opportunities

- T001 and T002 are read-only measurements → run in parallel.
- T007–T020 are different files → all triage tasks can run in parallel within US2.
- T032–T035 are different files → all refactor tasks can run in parallel within US4.
- **Across workstreams**: US4 (Workstream B) can start as soon as US1 merges, running in parallel with US2/US3 (Workstream A). This is the primary parallelism opportunity — two developers can work on the two workstreams simultaneously.

### Across-Story Parallelism

> Workstream A stories (US1 → US2 → US3) have a strict sequential ordering. Workstream B (US4) is fully independent after US1 merges. The maximum parallelism is:
>
> - Developer A: US1 → US2 → US3
> - Developer B: (waits for US1) → US4
>
> Or single-developer: US1 → US2 (parallel with US4 start) → US3 → US4 completion → Polish.

---

## Parallel Example: User Story 2 (Triage)

```text
# All triage tasks edit different files — launch in parallel:
Task T007: "Triage pipeline.py (~47 handlers)"
Task T008: "Triage chat.py (~41 handlers)"
Task T009: "Triage orchestrator.py (~32 handlers)"
Task T010: "Triage app_service.py (~19 handlers)"
Task T011: "Triage main.py (~18 handlers)"
Task T012: "Triage helpers.py + recovery.py (~31 handlers)"
Task T013: "Triage copilot.py (~14 handlers)"
Task T014: "Triage issues.py (~15 handlers)"
Task T015: "Triage pull_requests.py (~12 handlers)"
Task T016: "Triage projects.py (~11 handlers)"
Task T017: "Triage service.py (_with_fallback internals)"
Task T018: "Triage remaining src/api/ files"
Task T019: "Triage remaining src/services/ files"
Task T020: "Triage remaining src/ top-level files"

# After ALL triage tasks complete:
Task T021: "Verify zero BLE001 violations"
Task T022: "Verify tagged count < 85"
```

## Parallel Example: User Story 4 (Refactor)

```text
# After T029 (helper implementation) and T031 (tests pass):
Task T032: "Refactor pull_requests.py to _best_effort()"
Task T033: "Refactor projects.py to _best_effort()"
Task T034: "Refactor copilot.py to _best_effort()"
Task T035: "Refactor issues.py to _best_effort()"
```

---

## Implementation Strategy

### MVP: User Story 1 only

US1 alone delivers immediate value: CI blocks new unjustified `except Exception` handlers from landing. It is a single-line config change with two canary verifications — the smallest possible PR.

**MVP scope**: T001–T006 (six tasks, single PR). After merge, the lint rule is active and prevents regression (SC-002).

### Incremental Delivery

- **PR 1 (US1)**: Enable BLE001. Low-risk, one-line config change. CI immediately blocks new violations.
- **PR 2–N (US2)**: Triage handlers. Split into multiple PRs per research R8 — one PR per large file (pipeline.py, chat.py, orchestrator.py), one PR per directory batch for smaller files. ~8–12 triage PRs total.
- **PR N+1 (US3)**: Document tag convention in README. Single PR.
- **PR N+2 (US4)**: Implement `_best_effort()` helper + refactor github_projects/ service files. May ship as one PR or split into helper + per-file refactors.
- **PR N+3 (Polish)**: Final cross-workstream validation.

### Reviewer Guidance per PR

- **US1 reviewer**: Confirm `"BLE"` is in `select` after `"B"` and before `"C4"`. Confirm no `ignore` or `per-file-ignores` entries for BLE001. Confirm canary results in PR description.
- **US2 reviewer**: For each triage PR, run `uv run ruff check <file> --select BLE001` — must exit 0. Spot-check that Narrow handlers use the correct specific exception types per `data-model.md` § E6. Verify Tagged handlers have meaningful `— reason:` text (not boilerplate).
- **US3 reviewer**: Confirm README section contains format, flowchart, and ≥3 examples. Run the tag compliance grep from T026.
- **US4 reviewer**: Confirm `_best_effort()` signature matches `contracts/best-effort-helper-contract.md` § B1. Verify unit tests cover all 5 cases from § B6. Spot-check that refactored call sites preserve the original log severity and fallback value (SC-006).

---

## Format Validation

Every task above conforms to: `- [ ] T### [P?] [Story?] Description with file path`.

- ✅ All tasks have a checkbox `- [ ]`.
- ✅ All tasks have a sequential ID (T001–T042, no gaps).
- ✅ All US-phase tasks carry a `[US1]`–`[US4]` story label; Setup tasks (T001, T002) and Polish tasks (T039–T042) intentionally have no story label.
- ✅ Parallelisable tasks carry `[P]`.
- ✅ Every task names at least one file path or command it edits/creates/runs against.

---

## Coverage Matrix

| Spec Artifact | Tasks |
|---|---|
| FR-001 (lint rule flags unjustified broad-except) | T003, T004 |
| FR-002 (lint rule runs in CI) | T003 (CI picks up pyproject.toml automatically; research R6) |
| FR-003 (every handler triaged) | T007–T020, T021 |
| FR-004 (tagged handlers have justification) | T013–T017, T026 |
| FR-005 (convention documented) | T025, T027 |
| FR-006 (shared best-effort helper) | T029 |
| FR-007 (helper catches only Exception) | T029, T028 (test case 3 — KeyboardInterrupt propagates) |
| FR-008 (ad-hoc wrappers replaced) | T032–T035, T036 |
| FR-009 (logging behaviour preserved) | T032–T035 (preserve context + severity), T028 (test cases 2, 4) |
| FR-010 (workstreams independent) | T042; phase structure (US4 has no dependency on US2/US3) |
| FR-011 (test suite passes) | T024, T038, T040 |
| SC-001 (zero unresolved violations) | T021 |
| SC-002 (CI blocks new violations) | T003, T005 (canary) |
| SC-003 (tagged < 15%) | T022 |
| SC-004 (80% reduction in duplicate handlers) | T036 |
| SC-005 (convention discoverable in < 2 min) | T025, T027 |
| SC-006 (no behaviour changes) | T024, T038, T040 |
| US1 Independent Test | T005, T006 |
| US2 Independent Test | T021, T022, T024 |
| US3 Independent Test | T026, T027 |
| US4 Independent Test | T031, T036, T038 |
