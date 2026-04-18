# Tasks: Tighten Backend Pyright (Standard → Strict, Gradually)

**Input**: Design documents from `/specs/001-tighten-backend-pyright/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/pyright-policy.md, quickstart.md

**Tests**: Not requested. The spec does not mandate new unit/integration tests. Canary verification is performed via pyright CLI assertions within each phase, not dedicated test files. Test pyright config stays `typeCheckingMode = "off"`.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. User stories are sequential for this feature (each phase builds on the previous), but tasks within each story can be parallelized where marked.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/` — all changes scoped to the backend subtree
- **Config**: `solune/backend/pyproject.toml` `[tool.pyright]` is the single source of truth
- **Tests config**: `solune/backend/pyrightconfig.tests.json`
- **Type stubs**: `solune/backend/src/typestubs/`
- **CI**: `.github/workflows/ci.yml`
- **ADR**: `solune/backend/docs/decisions/`

---

## Phase 1: Setup

**Purpose**: Verify the current pyright baseline before making any changes

- [ ] T001 Verify current `[tool.pyright]` configuration and record existing settings in `solune/backend/pyproject.toml`
- [ ] T002 [P] Verify current test pyright configuration and record existing settings in `solune/backend/pyrightconfig.tests.json`
- [ ] T003 Run `uv run pyright src` in `solune/backend/` to confirm zero-error baseline at `standard` mode

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No shared blocking infrastructure is needed for this feature

**⚠️ NOTE**: This feature modifies an existing project's tooling configuration. User stories are inherently sequential (each phase builds on the previous phase's config changes), not because of shared foundational work but because the pyright strictness ladder requires each step to be green before the next. The baseline verification in Phase 1 is the only prerequisite.

**Checkpoint**: Baseline verified — user story implementation can now begin

---

## Phase 3: User Story 1 — Establish a Safer Baseline Without a Mega-PR (Priority: P1) 🎯 MVP

**Goal**: Add safety-net diagnostic rules (`reportUnnecessaryTypeIgnoreComment`, `reportMissingParameterType`, `reportUnknownParameterType`, `reportUnknownMemberType`) to catch avoidable typing mistakes while keeping `typeCheckingMode = "standard"`.

**Independent Test**: Run `uv run pyright src` after enabling the new rules — it must exit 0 with zero errors. A redundant `# type: ignore` on a clean line must be flagged as an error.

### Implementation for User Story 1

- [ ] T004 [P] [US1] Add four safety-net diagnostic rules to `[tool.pyright]` in `solune/backend/pyproject.toml`: `reportUnnecessaryTypeIgnoreComment = "error"`, `reportMissingParameterType = "error"`, `reportUnknownParameterType = "error"`, `reportUnknownMemberType = "warning"`
- [ ] T005 [P] [US1] Add `reportUnnecessaryTypeIgnoreComment = "error"` to `solune/backend/pyrightconfig.tests.json`
- [ ] T006 [US1] Run `uv run pyright src` in `solune/backend/`, capture all new diagnostics (≤~20 expected), and fix each finding inline — add missing type annotations, remove redundant suppressions, annotate unknown parameters
- [ ] T007 [US1] Re-verify the two existing `# type: ignore` comments in `solune/backend/src/services/agent_provider.py` (line ~501) and `solune/backend/src/services/plan_agent_provider.py` (line ~207) — remove if `reportUnnecessaryTypeIgnoreComment` flags them as redundant
- [ ] T008 [US1] Validate `uv run pyright src` exits 0 with zero errors in `solune/backend/`
- [ ] T009 [US1] Validate `uv run pyright -p pyrightconfig.tests.json` exits 0 with zero errors in `solune/backend/`

**Checkpoint**: Safety-net rules are active and green. Redundant suppressions and missing parameter types are now caught. MVP is deliverable.

---

## Phase 4: User Story 2 — Protect the Cleanest Backend Packages With a Strict Floor (Priority: P2)

**Goal**: Enforce `strict`-level checking on `src/api`, `src/models`, and `src/services/agents` via the `strict = [...]` config. No file-level downgrade is allowed inside these protected paths.

**Independent Test**: Add a canary `def foo(x):` (missing parameter type and return type) inside `src/api/` — pyright must reject it. Verify the protected package list is explicitly declared in `pyproject.toml`.

### Implementation for User Story 2

- [ ] T010 [US2] Baseline strict-mode error count per protected tree — run `uv run pyright --typeCheckingMode strict` scoped to `src/api`, `src/models`, `src/services/agents` individually in `solune/backend/` and record error counts
- [ ] T011 [P] [US2] Fix strict-mode errors in `solune/backend/src/api/` — add explicit return-type annotations to `Depends()` dependency functions in `src/api/chat.py`, type WebSocket `receive_json()` payloads in `src/api/projects.py`, and fix all remaining strict diagnostics across `src/api/` files
- [ ] T012 [P] [US2] Fix strict-mode errors in `solune/backend/src/models/` — add missing type annotations, explicit return types, and strict-compatible patterns across all model files
- [ ] T013 [P] [US2] Fix strict-mode errors in `solune/backend/src/services/agents/` — cast or wrap `aiosqlite.Row` results with typed accessor in `service.py` (line ~71), and fix all remaining strict diagnostics
- [ ] T014 [US2] Augment type stubs in `solune/backend/src/typestubs/` as needed for strict compatibility — add missing member declarations for `githubkit`, `copilot`, or `agent_framework_github_copilot` stubs that produce strict-mode errors in protected trees
- [ ] T015 [US2] Add `strict = ["src/api", "src/models", "src/services/agents"]` to `[tool.pyright]` in `solune/backend/pyproject.toml`
- [ ] T016 [US2] Validate `uv run pyright src` exits 0 with strict floor active in `solune/backend/` — confirm all protected-tree files are checked at strict level

**Checkpoint**: Strict floor is active. Any weak or missing typing in `src/api`, `src/models`, or `src/services/agents` is rejected by pyright. No per-file downgrade is allowed inside the floor.

---

## Phase 5: User Story 3 — Make Remaining Downgrades Visible and Auditable (Priority: P3)

**Goal**: Flip the global `typeCheckingMode` to `"strict"`, add `# pyright: basic` pragmas to legacy modules that cannot yet pass, and create an ADR documenting every downgraded file with ownership. Install CI gates to prevent new pragmas in the strict floor and report downgrade count per build.

**Independent Test**: Run `uv run pyright src` under global strict — it must exit 0. Every `# pyright: basic` file must appear in the ADR. No pragma may exist inside `src/api/`, `src/models/`, or `src/services/agents/`.

### Implementation for User Story 3

- [ ] T017 [US3] Set `typeCheckingMode = "strict"` in `[tool.pyright]` in `solune/backend/pyproject.toml` (keep `strict = [...]` as floor contract)
- [ ] T018 [US3] Run `uv run pyright src` in `solune/backend/` and identify all failing legacy modules — expected candidates: `src/services/github_projects/**`, `src/services/copilot_polling/**`, `src/main.py`, `src/services/chat_agent.py`
- [ ] T019 [US3] Add `# pyright: basic  — reason: <justification>` pragma at line 1 of each failing legacy file in `solune/backend/src/` — use `# pyright: basic` (not `# pyright: off`) per repo suppression convention
- [ ] T020 [US3] Re-verify `# type: ignore` comments in `solune/backend/src/services/agent_provider.py` (line ~501) and `solune/backend/src/services/plan_agent_provider.py` (line ~207) under strict mode — remove if `reportUnnecessaryTypeIgnoreComment` flags them as redundant
- [ ] T021 [P] [US3] Create ADR at `solune/backend/docs/decisions/001-pyright-strict-legacy-opt-outs.md` — include title, date, status (Accepted), context, decision, table of every downgraded module with path, owner, reason, and date added
- [ ] T022 [US3] Validate `uv run pyright src` exits 0 under global strict mode in `solune/backend/` — confirm 100% of source files run at strict unless they carry `# pyright: basic`

**Checkpoint**: Global strict mode is active. All legacy downgrades are explicit, documented in the ADR, and auditable. The strict floor continues to protect `src/api`, `src/models`, `src/services/agents`.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: CI enforcement, burn-down tracking, and final validation across all phases

- [ ] T023 [P] Add CI strict-floor integrity gate step in `.github/workflows/ci.yml` — fail if `grep -rn "pyright: basic" src/api/ src/models/ src/services/agents/` finds any pragma inside the protected packages
- [ ] T024 [P] Add CI downgrade count reporter step in `.github/workflows/ci.yml` — print `Pyright downgrades remaining: $(grep -rn 'pyright: basic' src/ | wc -l)` per build
- [ ] T025 Validate pre-commit hook stays green — run `uv tool run pre-commit run -c solune/.pre-commit-config.yaml --all-files` from repo root
- [ ] T026 Run quickstart.md validation steps end-to-end in `solune/backend/` — execute all verify, phase, and troubleshooting commands from `specs/001-tighten-backend-pyright/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: N/A — no shared blocking infrastructure for this feature
- **User Story 1 (Phase 3)**: Depends on Setup (Phase 1) baseline verification
- **User Story 2 (Phase 4)**: Depends on User Story 1 (Phase 3) — safety-net rules must be active before strict floor
- **User Story 3 (Phase 5)**: Depends on User Story 2 (Phase 4) — strict floor must be green before global flip
- **Polish (Phase 6)**: Depends on User Story 3 (Phase 5) — CI gates enforce the final strict state

### User Story Dependencies

- **User Story 1 (P1)**: Sequential prerequisite — safety-net rules are the foundation for all later strictness
- **User Story 2 (P2)**: Depends on US1 — fixing inline findings first keeps the strict-floor diff focused on new strict errors only
- **User Story 3 (P3)**: Depends on US2 — the strict floor must be established before flipping the global default; otherwise protected packages would need pragmas too

### Within Each User Story

- Config changes before fix-up work
- Fix-up work before declaring the new config level
- Validation as the final task in each story

### Parallel Opportunities

- **Phase 1**: T001 and T002 can run in parallel (different config files)
- **Phase 3 (US1)**: T004 and T005 can run in parallel (pyproject.toml vs pyrightconfig.tests.json)
- **Phase 4 (US2)**: T011, T012, T013 can run in parallel (different source trees: src/api, src/models, src/services/agents)
- **Phase 5 (US3)**: T021 (ADR creation) can run in parallel with T019–T020 (pragma + re-verify work)
- **Phase 6**: T023 and T024 can run in parallel (independent CI steps)

---

## Parallel Example: User Story 2

```bash
# After T010 baseline is captured, launch tree fixes in parallel:
Task: "Fix strict-mode errors in solune/backend/src/api/"           # T011
Task: "Fix strict-mode errors in solune/backend/src/models/"        # T012
Task: "Fix strict-mode errors in solune/backend/src/services/agents/" # T013

# After all three complete, augment stubs if needed (T014), then declare floor (T015)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup — verify baseline
2. Complete Phase 3: User Story 1 — add safety-net rules + fix findings
3. **STOP and VALIDATE**: `uv run pyright src` exits 0; redundant suppressions are caught
4. Land as one small PR (minimal code churn, maximum safety gain)

### Incremental Delivery

1. US1 lands → safety-net rules active (MVP)
2. US2 lands (1–3 PRs, one per tree) → strict floor on cleanest packages
3. US3 lands (1 PR) → global strict + ADR + CI gates
4. Phase 6 lands → burn-down tracking active
5. Each phase adds strictness without breaking previous phases

### Parallel Team Strategy

With multiple developers after US1 lands:

1. Developer A: Fix `src/api/` strict errors (T011)
2. Developer B: Fix `src/models/` strict errors (T012)
3. Developer C: Fix `src/services/agents/` strict errors (T013)
4. Merge all three → declare strict floor (T015)

---

## Summary

| Metric | Value |
|--------|-------|
| **Total tasks** | 26 |
| **Setup tasks** | 3 (T001–T003) |
| **US1 tasks** | 6 (T004–T009) |
| **US2 tasks** | 7 (T010–T016) |
| **US3 tasks** | 6 (T017–T022) |
| **Polish tasks** | 4 (T023–T026) |
| **Parallel opportunities** | 5 groups (T001∥T002, T004∥T005, T011∥T012∥T013, T019–T020∥T021, T023∥T024) |
| **Suggested MVP scope** | User Story 1 only (Phase 3: T004–T009) |
| **Format validated** | ✅ All 26 tasks follow `- [ ] [TaskID] [P?] [Story?] Description with file path` |

---

## Notes

- [P] tasks = different files, no dependencies between them
- [Story] label maps each task to its user story for traceability
- User stories are sequential for this feature (US1 → US2 → US3) because each phase builds on the previous config level
- Within US2, the three protected trees (src/api, src/models, src/services/agents) can be fixed in parallel
- No new test files are generated — the spec does not request tests; canary checks are pyright CLI validations
- `reportUnknownMemberType` starts at `"warning"` (Phase 1) and is promoted to `"error"` only when the backlog is clear (Phase 4 ongoing burn-down, outside task scope)
- The `strict = [...]` declaration persists after the Phase 3 global flip as a floor contract, not a redundant setting
- Commit after each task or logical group; stop at any checkpoint to validate independently
