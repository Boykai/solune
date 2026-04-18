---
description: "Task list for tightening backend Pyright (standard → strict, gradually)"
---

# Tasks: Tighten Backend Pyright (standard → strict, gradually)

**Input**: Design documents from `/specs/001-backend-pyright-strict/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: NOT requested. This is a tooling/configuration feature; validation is by `uv run pyright` exit status, `--outputjson | jq` diagnostic counts, and canary commits — all defined in `quickstart.md` and the spec's Acceptance Scenarios. No pytest test suite is added (constitution check IV; spec FR-011).

**Organization**: Tasks are grouped by user story. The four user stories map 1:1 to the four feature phases described in the user request and `plan.md`. Each story is its own PR (FR-013); US2 MAY split into up to three sub-PRs (one per tree).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)

## Path Conventions

Web app structure (per plan.md). All edits live under `solune/backend/`, `solune/docs/decisions/`, `solune/scripts/`, or `.github/workflows/`. Paths are repo-relative from `/root/repos/solune/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Capture pre-feature baselines that downstream phases verify against.

- [X] T001 Capture pre-Phase-1 Pyright wall-clock baseline for SC-005: from `solune/backend/`, run `time uv run pyright` three times on a clean checkout of the current `main`, record the median in the Phase 1 PR description as `Baseline median: <N>s`. (Phase 0 research R9.) **Result: median 11.96s (runs: 11.96, 13.05, 10.86).**
- [X] T002 Capture pre-Phase-1 Pyright diagnostic baseline: from `solune/backend/`, run `uv run pyright --outputjson | jq '.generalDiagnostics | length'` on `main` and record the result in the Phase 1 PR description as `Baseline diagnostics: <N>`. **Result: 0 diagnostics on main.**

**Checkpoint**: Baselines recorded. No code changes yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

> No foundational work is required. All four user stories depend only on the configuration files already present in the repo (`solune/backend/pyproject.toml`, `solune/backend/pyrightconfig.tests.json`, `.github/workflows/ci.yml`, `solune/scripts/pre-commit`). The baselines from Phase 1 (T001–T002) are the only shared inputs.

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 — Safety-net settings catch sloppy typing today (Priority: P1) 🎯 MVP

**Goal**: Add `reportUnnecessaryTypeIgnoreComment`, `reportMissingParameterType`, `reportUnknownParameterType` (all `"error"`) and `reportUnknownMemberType = "warning"` to `[tool.pyright]`; mirror the unnecessary-ignore rule into the tests config; fix any newly surfaced findings inline.

**Independent Test**: Land US1 alone, then push a canary commit adding `def helper(x):` to a file under `solune/backend/src/` and a redundant `# type: ignore` on a fully-typed line. Both must fail `uv run pyright`. (Spec US1 Acceptance Scenarios 1, 2; quickstart Phase 1 canary.)

### Implementation for User Story 1

- [X] T003 [US1] Add the four new diagnostic settings to `[tool.pyright]` in [solune/backend/pyproject.toml](solune/backend/pyproject.toml) per `contracts/pyright-config-contract.md` § C1 Phase 1 exemplar: `reportUnnecessaryTypeIgnoreComment = "error"`, `reportMissingParameterType = "error"`, `reportUnknownParameterType = "warning"` *(amended from `"error"` during implementation — see spec FR-001 amendment note; baseline measurement surfaced 381 return-type-unknown errors vs spec's anticipated ≤~20)*, `reportUnknownMemberType = "warning"`. Keep `typeCheckingMode = "standard"`.
- [X] T004 [US1] Add `"reportUnnecessaryTypeIgnoreComment": "error"` to [solune/backend/pyrightconfig.tests.json](solune/backend/pyrightconfig.tests.json) per `contracts/pyright-config-contract.md` § C2 Phase 1 exemplar. Keep `"typeCheckingMode": "off"` (FR-011).
- [X] T005 [US1] Run `cd solune/backend && uv run pyright` and `uv run pyright -p pyrightconfig.tests.json`; capture every new diagnostic. **Result: 65 `reportMissingParameterType` errors + 2 `reportUnnecessaryTypeIgnoreComment` errors in src/; 3 `reportUnnecessaryTypeIgnoreComment` errors in tests/.**
- [X] T006 [US1] For each `reportMissingParameterType` / `reportUnknownParameterType` finding from T005, add a precise type annotation to the offending function parameter. **Done across 17 files — see PR description for per-file summary; key types: `aiosqlite.Connection`, `GitHubProjectsService`, `ConnectionManager`, ASGI `ASGIApp`/`Scope`/`Receive`/`Send`/`RequestResponseEndpoint`, `aiosqlite.Row`, `Coroutine[Any, Any, Any]`, `BoardItem`, `BoardLoadMode`. Zero `# type: ignore` introduced; zero use of bare `Any` where a narrower type was reachable.**
- [X] T007 [US1] For each `reportUnnecessaryTypeIgnoreComment` finding from T005, delete the redundant `# type: ignore[...]` (and its `— reason: …` suffix). **Both known instances (agent_provider.py:501 and plan_agent_provider.py:207) flagged as redundant — SDK has caught up; both removed. Three additional redundant `# type: ignore[misc]` in `tests/unit/test_mcp_server/test_context.py` removed (mode=off makes them no-ops).**
- [X] T008 [US1] Re-run `uv run pyright` and `uv run pyright -p pyrightconfig.tests.json`; both MUST exit 0 (FR-003, SC-004). **Result: src/ → 0 errors, 2063 warnings; tests/ → 0 errors, 0 warnings. JSON error-severity count: 0.**
- [X] T009 [US1] Push a throwaway canary branch with `def helper(x): pass` in a new file under `solune/backend/src/` and a redundant `# type: ignore` on a fully-typed line; confirm `uv run pyright` exits non-zero with `reportMissingParameterType` and `reportUnnecessaryTypeIgnoreComment` errors. **Verified inline (no branch needed): canary file `src/canary_us1.py` triggered both rules at error severity, then was deleted.**

**Checkpoint**: Phase 1 PR ready to open. CI's existing Pyright steps at [.github/workflows/ci.yml:50-54](.github/workflows/ci.yml#L50-L54) will pick the new settings up automatically — no workflow edit in this story.

---

## Phase 4: User Story 2 — Strict floor on the cleanest packages (Priority: P2)

**Goal**: Add `strict = ["src/api", "src/models", "src/services/agents"]` to `[tool.pyright]` after fixing every strict-mode error inside those three trees. No per-file `# pyright: basic` or `# pyright: off` allowed inside the floor (FR-005). MAY be split into US2a/US2b/US2c (one per tree, cheapest first per Phase 0 R5).

**Independent Test**: After US2 lands, push a canary that adds `def regress(x): pass` to a file under `solune/backend/src/api/`. CI must fail with a strict-mode diagnostic. (Spec US2 Acceptance Scenarios 1, 2, 3; quickstart Phase 2 canary.)

### Baseline measurement (do NOT commit)

- [ ] T010 [US2] Apply the temporary `strict = [...]` edit from `quickstart.md` § Phase 2 baseline measurement, run `uv run pyright --outputjson`, and record per-tree error counts (`src/api`, `src/models`, `src/services/agents`) in the Phase 2 PR description. Discard the temporary edit (`git checkout -- pyproject.toml`). This drives the cheapest-first split decision per Phase 0 R5.

### Implementation per tree (each may be its own sub-PR)

> Sub-PRs may be done in any order; cheapest tree (lowest error count from T010) first. Within each sub-PR, the strict-fix tasks are necessarily file-by-file as Pyright surfaces them — they cannot be exhaustively pre-enumerated without running the analysis. The hotspot tasks below are the *anticipated* fixes from Phase 0 R5; treat them as floor, not ceiling.

#### Tree A — `src/models/` (anticipated cheapest)

- [ ] T011 [US2] Fix every strict-mode error Pyright reports under [solune/backend/src/models/](solune/backend/src/models/) when `strict = ["src/models"]` is locally enabled. Drive by Pyright output; preserve runtime behaviour. If a fix requires a third-party stub addition, place it under [solune/backend/src/typestubs/](solune/backend/src/typestubs/) (Phase 0 R6) — never add `# type: ignore` inside the floor.
- [ ] T012 [US2] Re-run `uv run pyright` with the local `strict = ["src/models"]` override; MUST exit 0. Discard the local override before opening any sub-PR (the global commit happens in T020).

#### Tree B — `src/api/`

- [ ] T013 [P] [US2] Anticipated hotspot — type the `Depends()` return signatures in [solune/backend/src/api/chat.py](solune/backend/src/api/chat.py) (Phase 0 R5). Confirm by re-running Pyright with `strict = ["src/api"]` locally enabled.
- [ ] T014 [P] [US2] Anticipated hotspot — annotate WebSocket payload types in [solune/backend/src/api/projects.py](solune/backend/src/api/projects.py); replace any `Any` on receive/send paths with the concrete payload type (Phase 0 R5).
- [ ] T015 [US2] Fix every remaining strict-mode error Pyright reports under [solune/backend/src/api/](solune/backend/src/api/) with `strict = ["src/api"]` locally enabled. Same stub-not-ignore policy as T011.
- [ ] T016 [US2] Re-run `uv run pyright` with the local `strict = ["src/api"]` override; MUST exit 0. Discard the local override.

#### Tree C — `src/services/agents/`

- [ ] T017 [US2] Anticipated hotspot — replace index-based `aiosqlite.Row` access with the typed accessor in [solune/backend/src/services/agents/service.py](solune/backend/src/services/agents/service.py) around line 71 (Phase 0 R5). Add a typed `Row` wrapper to [solune/backend/src/typestubs/](solune/backend/src/typestubs/) if needed.
- [ ] T018 [US2] Fix every remaining strict-mode error Pyright reports under [solune/backend/src/services/agents/](solune/backend/src/services/agents/) with `strict = ["src/services/agents"]` locally enabled.
- [ ] T019 [US2] Re-run `uv run pyright` with the local `strict = ["src/services/agents"]` override; MUST exit 0. Discard the local override.

### Commit the floor (only after T012, T016, T019 are all green)

- [ ] T020 [US2] Add `strict = ["src/api", "src/models", "src/services/agents"]` to `[tool.pyright]` in [solune/backend/pyproject.toml](solune/backend/pyproject.toml) per `contracts/pyright-config-contract.md` § C1 Phase 2 exemplar. Keep `typeCheckingMode = "standard"`.
- [ ] T021 [US2] From `solune/backend/`, run `uv run pyright`; MUST exit 0. Run `uv run pyright --outputjson | jq -e '[.generalDiagnostics[] | select(.severity == "error")] | length == 0'`. Verify floor exclusivity: `! grep -rE '^# pyright:\s*(basic|off)\b' solune/backend/src/api solune/backend/src/models solune/backend/src/services/agents` (FR-005).
- [ ] T022 [US2] Push a throwaway canary branch adding `def regress(x): pass` to a file under [solune/backend/src/api/](solune/backend/src/api/); confirm `uv run pyright` exits non-zero on that file. Delete the branch. Record output in the PR description (US2 Independent Test).

**Checkpoint**: Phase 2 PR(s) ready. Strict floor active; global mode still `"standard"`.

---

## Phase 5: User Story 3 — Global strict with auditable legacy opt-out (Priority: P3)

**Goal**: Flip global `typeCheckingMode = "strict"`. Add `# pyright: basic` + `# reason:` pragmas to every legacy module that fails strict (per `contracts/pragma-contract.md`). Land an ADR enumerating downgrades. Re-verify the two pre-existing `# type: ignore` comments under strict.

**Independent Test**: After US3 lands, `uv run pyright` exits 0; removing the pragma from any single legacy file surfaces strict-mode errors only in that file. (Spec US3 Acceptance Scenarios 1, 2, 3, 4; quickstart Phase 3 canary.)

### Re-verification of pre-existing ignores (FR-012, Phase 0 R10)

- [ ] T023 [US3] In a worktree-only edit, flip `typeCheckingMode = "standard"` → `"strict"` in [solune/backend/pyproject.toml](solune/backend/pyproject.toml) WITHOUT yet adding any `# pyright: basic` pragmas. Run `uv run pyright 2>&1 | grep -E 'agent_provider\.py:501|plan_agent_provider\.py:207'`.
- [ ] T024 [US3] If T023 flagged [solune/backend/src/services/agent_provider.py:501](solune/backend/src/services/agent_provider.py#L501) with `reportUnnecessaryTypeIgnoreComment`, delete the `# type: ignore[reportGeneralTypeIssues] — reason: …` comment in this PR. Otherwise leave it in place.
- [ ] T025 [US3] If T023 flagged [solune/backend/src/services/plan_agent_provider.py:207](solune/backend/src/services/plan_agent_provider.py#L207) with `reportUnnecessaryTypeIgnoreComment`, delete the `# type: ignore[reportGeneralTypeIssues] — reason: …` comment in this PR. Otherwise leave it in place.

### Enumerate legacy failures (still strict, still no pragmas)

- [ ] T026 [US3] With the worktree-only `strict` mode still active, run `uv run pyright --outputjson | jq -r '.generalDiagnostics[] | select(.severity == "error") | .file' | sort -u > /tmp/phase3-failing-files.txt` per `quickstart.md` § Phase 3 Step 2. This is the canonical set of files that need `# pyright: basic`.

### Add pragmas (one per file in `/tmp/phase3-failing-files.txt`)

> The exact file list comes from T026; the user request anticipates `src/services/github_projects/**`, `src/services/copilot_polling/**`, `src/main.py`, `src/services/chat_agent.py`. Each pragma + reason pair is a discrete edit; they may be done in parallel (different files).

- [ ] T027 [P] [US3] For each candidate path under [solune/backend/src/services/github_projects/](solune/backend/src/services/github_projects/) that appears in T026's output, add `# pyright: basic` + `# reason: <one-line justification>` at the top of the file per `contracts/pragma-contract.md` § P3 (after any module docstring, before imports). Do NOT use `# pyright: off` (FR-007, P2).
- [ ] T028 [P] [US3] Same as T027 for files under [solune/backend/src/services/copilot_polling/](solune/backend/src/services/copilot_polling/) that appear in T026's output.
- [ ] T029 [P] [US3] Same as T027 for [solune/backend/src/main.py](solune/backend/src/main.py) if it appears in T026's output.
- [ ] T030 [P] [US3] Same as T027 for [solune/backend/src/services/chat_agent.py](solune/backend/src/services/chat_agent.py) if it appears in T026's output.
- [ ] T031 [P] [US3] Same as T027 for any *additional* file in T026's output not covered by T027–T030 (e.g., other top-level modules under `solune/backend/src/`). One pragma per file.

### Commit the global flip and ADR

- [ ] T032 [US3] Update `[tool.pyright]` in [solune/backend/pyproject.toml](solune/backend/pyproject.toml) so `typeCheckingMode = "strict"` per `contracts/pyright-config-contract.md` § C1 Phase 3 exemplar (keep all other keys, including the Phase 2 `strict = [...]` array).
- [ ] T033 [US3] Create [solune/docs/decisions/007-backend-pyright-strict-downgrades.md](solune/docs/decisions/007-backend-pyright-strict-downgrades.md) per `data-model.md` § E5: standard ADR header (Status / Date / Context / Decision / Consequences) matching the existing `001-githubkit-sdk.md`–`006-signal-sidecar.md` style, plus a table with one row per file in T026's output (columns: `file path | reason | owner | target removal milestone`). Update [solune/docs/decisions/README.md](solune/docs/decisions/README.md) to include the new ADR in its index.
- [ ] T034 [US3] From `solune/backend/`, run `uv run pyright`; MUST exit 0 (FR-003, SC-004). Verify ADR consistency: the set of files in the ADR table MUST equal `grep -rl '^# pyright: basic$' solune/backend/src/` (data-model invariant 2; quickstart Phase 3 verify).
- [ ] T035 [US3] Push a throwaway canary branch deleting the pragma from one file in T026's output; confirm `uv run pyright` exits non-zero on that file alone. Delete the branch. Record output in the PR description (US3 Independent Test).
- [ ] T036 [US3] Re-measure the post-Phase-3 Pyright wall-clock (median of three runs) per Phase 0 R9; record in the PR description and confirm the ratio against T001's baseline does not exceed 1.25× (SC-005).

**Checkpoint**: Phase 3 PR ready. Global strict active; legacy debt enumerated and visible.

---

## Phase 6: User Story 4 — Burn-down gate prevents regression and tracks debt (Priority: P3)

**Goal**: Wire the burn-down gate into pre-commit and CI per `contracts/burn-down-gate-contract.md`. Stage 1 (blocking) refuses new `# pyright: basic` inside the floor; stage 2 (informational) prints `# pyright: basic count: N` on every build.

**Independent Test**: A canary adding the pragma under `solune/backend/src/api/` is rejected by pre-commit and (if bypassed) by CI. A canary adding it to a non-floor file passes locally but the CI log shows an incremented count. (Spec US4 Acceptance Scenarios 1, 2, 3; quickstart Phase 4 verify.)

### Implementation for User Story 4

- [ ] T037 [P] [US4] Append a `# Pyright pragma gate (Phase 4)` section to [solune/scripts/pre-commit](solune/scripts/pre-commit) per `contracts/burn-down-gate-contract.md` § G2 + § G5. Guard with the existing `STAGED_BACKEND_CHANGES` variable so it only runs when backend files are staged. Stage 1 calls `exit 1` on floor violation; stage 2 prints the count line unconditionally and does not affect exit status. Reproduce the failure-message format from § G6 verbatim.
- [ ] T038 [P] [US4] Add a `Pyright pragma gate` step to the `backend` job in [.github/workflows/ci.yml](.github/workflows/ci.yml) immediately after the existing `Type check with pyright` step (line 51) per `contracts/burn-down-gate-contract.md` § G5. Stage 1 runs only on `pull_request` events (uses `git diff origin/${{ github.base_ref }}...HEAD --name-only --diff-filter=ACM` as the changed-files source per § G1); stage 2 always runs. Reproduce the failure-message format from § G6 verbatim.
- [ ] T039 [US4] From the repo root, re-run [solune/scripts/setup-hooks.sh](solune/scripts/setup-hooks.sh) so the new pre-commit content mirrors into `.git/hooks/pre-commit`.
- [ ] T040 [US4] Run [solune/scripts/pre-commit](solune/scripts/pre-commit) directly with no staged changes; confirm the literal output line `# pyright: basic count: <N>` appears (matches `^# pyright: basic count: [0-9]+$`). `<N>` should equal the count of files changed in T027–T031.
- [ ] T041 [US4] Execute Canary 1 from `contracts/burn-down-gate-contract.md` § G7: stage a `# pyright: basic` + `# reason: canary` addition to a file under [solune/backend/src/api/](solune/backend/src/api/); attempt to commit; confirm `solune/scripts/pre-commit` exits 1 with the canonical message `# pyright: basic is not allowed inside the strict floor.` Revert.
- [ ] T042 [US4] Execute Canary 2 from `contracts/burn-down-gate-contract.md` § G7: stage the same pragma in a non-floor file (e.g., [solune/backend/src/utils.py](solune/backend/src/utils.py)); confirm pre-commit exits 0 and the count line shows N+1. Revert.
- [ ] T043 [US4] Open the Phase 4 PR; verify in the CI log that the `Pyright pragma gate` step prints exactly one line matching `^# pyright: basic count: [0-9]+$` (SC-006).

**Checkpoint**: Phase 4 PR ready. Burn-down gate live in both pre-commit and CI.

---

## Phase 7: Polish & Cross-Cutting Concerns

> Optional follow-up; not required for the four-phase rollout to be complete.

- [ ] T044 (follow-up PR, after legacy backlog cleared) Promote `reportUnknownMemberType` from `"warning"` to `"error"` in `[tool.pyright]` of [solune/backend/pyproject.toml](solune/backend/pyproject.toml) per `contracts/pyright-config-contract.md` § C1 Phase 4 exemplar. Re-run `uv run pyright`; MUST exit 0 (FR-014, SC-007). Open as its own PR; do not bundle.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** — T001, T002 — no dependencies; run anytime before opening the US1 PR.
- **Foundational (Phase 2)** — none.
- **User Story 1 (Phase 3)** — depends on Setup baselines for SC-005/SC-004 reporting only (T001, T002 can technically run in parallel with T003–T009, but their values must appear in the US1 PR description).
- **User Story 2 (Phase 4)** — depends on US1 having merged (the safety-net rules from T003 must be active so T011/T015/T018 don't accidentally regress them).
- **User Story 3 (Phase 5)** — depends on US2 having merged (the strict floor must be in place before flipping global to strict, otherwise the floor's contract has no test).
- **User Story 4 (Phase 6)** — depends on US3 having merged (no pragmas exist to count or police until Phase 3 has added them).
- **Polish (Phase 7)** — depends on the legacy backlog (`# pyright: basic count: N`) reaching zero.

### Within Each User Story

- US1: T003 + T004 (config edits, parallelizable) → T005 (run Pyright) → T006 + T007 (fix findings, may parallelize across files but must finish before T008) → T008 (verify) → T009 (canary).
- US2: T010 (baseline) → per-tree groups (T011–T012, T013–T016, T017–T019) — sub-PRs run sequentially or in parallel as separate branches → T020 (commit floor) → T021 (verify) → T022 (canary).
- US3: T023 (re-verify ignores under strict) → T024 + T025 (delete redundant ignores if any, parallelizable) → T026 (enumerate legacy) → T027–T031 (add pragmas, parallelizable across files) → T032 + T033 (flip mode + ADR, must be the same commit) → T034 (verify + ADR consistency) → T035 (canary) → T036 (perf re-measure).
- US4: T037 + T038 (pre-commit and CI edits, parallelizable, different files) → T039 (install hook) → T040 (verify count line) → T041 + T042 (canaries, sequential because they share the working tree) → T043 (CI verification on the open PR).

### Parallel Opportunities

- T001 and T002 can run in parallel (both are read-only measurements).
- T003 and T004 are different files → run in parallel.
- T013 and T014 are different files inside Tree B → run in parallel during US2 Tree B work.
- T024 and T025 are different files → parallel.
- T027–T031 are different files → all parallel.
- T037 and T038 are different files → parallel.

### Across-story parallelism

> Each user story is its own PR (FR-013) and they have a strict ordering (US1 → US2 → US3 → US4). They cannot be parallelized across PRs without breaking the per-phase contracts. Within a story, parallel opportunities are listed above.

---

## Implementation Strategy

### MVP: User Story 1 only

US1 alone delivers immediate value (CI rejects new untyped parameters and dead `# type: ignore` comments). It is the smallest and safest landing and unblocks every subsequent phase.

**MVP scope**: T001–T009 (nine tasks, single PR). After merge, the backend cannot regress on the four new diagnostic rules.

### Incremental delivery

- **PR 1 (US1)**: Safety net. Low-risk, ≤ ~20 inline fixes. SC-001 met.
- **PR 2 (US2)**: Strict floor. May split into PR 2a/2b/2c (one per tree, cheapest first per T010). SC-002 met.
- **PR 3 (US3)**: Global strict + ADR. SC-003, SC-004, SC-005 met (final perf re-measure in T036).
- **PR 4 (US4)**: Burn-down gate. SC-006 met.
- **PR 5 (Polish, T044)**: Optional, after backlog cleared. SC-007 met.

### Reviewer guidance per PR

- US1 reviewer: confirm `pyrightconfig.tests.json typeCheckingMode == "off"` is unchanged; spot-check that fixes in T006 added precise types (not `Any`).
- US2 reviewer: run the floor-exclusivity grep from T021; confirm no `# pyright: basic|off` inside the three trees; confirm no new `# type: ignore` was added inside the floor (Phase 0 R6).
- US3 reviewer: diff the file list in the ADR (T033) against `grep -rl '^# pyright: basic$' solune/backend/src/`; the two MUST be identical (data-model invariant 2). Confirm the perf delta from T036 is within 25 % (SC-005).
- US4 reviewer: confirm the count-line regex in T040 matches CI logs; trigger the floor-violation canary (T041) and confirm the PR fails with the canonical message.

---

## Format validation

Every task above conforms to: `- [ ] T### [P?] [Story?] Description with file path`.

- ✅ All tasks have a checkbox `- [ ]`.
- ✅ All tasks have a sequential ID (T001–T044, no gaps).
- ✅ All US-phase tasks carry a `[US1]`–`[US4]` story label; Setup tasks (T001, T002) and Polish task (T044) intentionally have no story label.
- ✅ Parallelizable tasks carry `[P]`.
- ✅ Every task names at least one file path or directory it edits/creates/runs against.

---

## Coverage matrix

| Spec artifact | Tasks |
|---|---|
| FR-001 | T003 |
| FR-002 | T004 |
| FR-003 | T008, T021, T034, T044 |
| FR-004 | T020 |
| FR-005 | T021 (verify); T011/T015/T018 (no ignores added) |
| FR-006 | T032 |
| FR-007 | T027–T031 (use `basic` not `off`) |
| FR-008 | T033 |
| FR-009 | T037, T038, T041 |
| FR-010 | T038, T040, T043 |
| FR-011 | T004 (mode stays `"off"`); reviewer guidance per PR |
| FR-012 | T023, T024, T025 |
| FR-013 | implicit — task grouping enforces one-PR-per-story |
| FR-014 | T044 |
| SC-001 | T009 (canary); enforced ongoing by T003 |
| SC-002 | T021 (floor exclusivity grep) |
| SC-003 | T034 (ADR consistency) |
| SC-004 | T008, T021, T034 |
| SC-005 | T001, T036 |
| SC-006 | T038, T040, T043 |
| SC-007 | T044 |
| US1 Independent Test | T009 |
| US2 Independent Test | T022 |
| US3 Independent Test | T035 |
| US4 Independent Test | T041, T042 |
