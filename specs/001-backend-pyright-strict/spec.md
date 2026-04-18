# Feature Specification: Tighten Backend Pyright (standard → strict, gradually)

**Feature Branch**: `001-backend-pyright-strict`
**Created**: 2026-04-18
**Status**: Draft
**Input**: User description: "Gradually raise backend type-checking to strict using a 3-phase approach: first add safety-net settings, then enforce a strict floor on the cleanest packages (src/api, src/models, src/services/agents), and finally flip the global default to strict with # pyright: basic pragmas as the documented escape hatch for legacy modules."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Safety-net settings catch sloppy typing today (Priority: P1)

A backend contributor opens a pull request that adds a function with an untyped parameter (e.g., `def foo(x):`) or a redundant `# type: ignore` comment. The CI Pyright job fails immediately with a clear diagnostic pointing at the exact line, before any reviewer has to notice it manually.

**Why this priority**: This phase is the lowest-risk, highest-leverage change. It introduces guardrails that prevent type-debt from growing while later phases pay it down. Without it, every subsequent phase is undermined by new untyped code landing on `main`.

**Independent Test**: Land Phase 1 alone, then push a canary commit containing a function with no parameter type annotation under `solune/backend/src/` and a redundant `# type: ignore` on a fully-typed line. Both must fail the Pyright job in CI; reverting the canary must turn the build green.

**Acceptance Scenarios**:

1. **Given** the Phase 1 settings are in `pyproject.toml`, **When** a contributor adds `def helper(x):` to any file under `solune/backend/src/`, **Then** `uv run pyright` exits non-zero with a `reportMissingParameterType` error referencing that line.
2. **Given** the Phase 1 settings are in `pyproject.toml`, **When** a contributor adds `# type: ignore` to a line that has no Pyright diagnostic, **Then** `uv run pyright` exits non-zero with a `reportUnnecessaryTypeIgnoreComment` error referencing that line.
3. **Given** the existing backend code on `main`, **When** Phase 1 settings are applied and any newly surfaced findings are fixed inline, **Then** `uv run pyright` exits zero on the resulting branch.
4. **Given** the tests config (`pyrightconfig.tests.json`), **When** Phase 1 lands, **Then** `typeCheckingMode` remains `"off"` for tests but `reportUnnecessaryTypeIgnoreComment = "error"` is mirrored so dead ignores in test files are still flagged.

---

### User Story 2 - Strict floor on the cleanest packages (Priority: P2)

A maintainer working in `src/api/`, `src/models/`, or `src/services/agents/` knows these trees are held to the highest type-checking bar. Any change that would weaken them — an `Any` leak through a `Depends()` return type, an untyped WebSocket payload, an `aiosqlite.Row` accessed by index without a typed wrapper — fails CI and cannot be merged without either fixing the type or explicitly carving the file out (which is disallowed inside the floor).

**Why this priority**: Establishes a contractual floor on the modules most likely to evolve into the public API surface, preventing regression as the rest of the codebase is upgraded. Depends on Phase 1's safety net to be effective.

**Independent Test**: After Phase 2 lands, push a canary commit adding `def foo(x):` to a file under `src/api/`. CI must fail with a strict-mode diagnostic. A second canary that adds `# pyright: basic` to a file inside the strict floor must also fail (via the burn-down gate from Phase 4, but the floor itself must reject the diagnostic that the pragma would have hidden).

**Acceptance Scenarios**:

1. **Given** Phase 2 lands with `strict = ["src/api", "src/models", "src/services/agents"]` in `[tool.pyright]`, **When** `uv run pyright` runs against the current backend tree, **Then** it exits zero.
2. **Given** the strict floor is active, **When** a contributor changes `src/api/chat.py` so a `Depends()`-injected dependency is typed as a bare callable instead of its concrete return type, **Then** Pyright reports an error and CI fails.
3. **Given** the strict floor is active, **When** a contributor accesses an `aiosqlite.Row` field by index without the typed accessor in a file under `src/services/agents/`, **Then** Pyright reports an error.
4. **Given** global `typeCheckingMode` is still `"standard"`, **When** Pyright runs, **Then** files outside the strict floor are still checked at standard level (Phase 2 does not regress them).

---

### User Story 3 - Global strict with auditable legacy opt-out (Priority: P3)

The codebase as a whole is type-checked at strict level. A small, named set of legacy modules (e.g., `src/services/github_projects/**`, `src/services/copilot_polling/**`, `src/main.py`, `src/services/chat_agent.py`) carries a single, visible `# pyright: basic` pragma at the top of each file with the same `reason:` convention the repo uses for `# noqa` and `eslint-disable`. An ADR enumerates these modules and their owners so the type-debt is tracked, not hidden.

**Why this priority**: This is the payoff phase — strict becomes the default — but it depends on Phases 1 and 2 to be safe and on Phase 4's burn-down gate to prevent backsliding. Lowest priority because the value is realised incrementally as legacy modules are cleaned and their pragmas removed.

**Independent Test**: After Phase 3 lands, `uv run pyright` exits zero. Removing the `# pyright: basic` pragma from any single legacy module surfaces strict-mode errors in just that module. Adding `# pyright: basic` to a new module under `src/api/`, `src/models/`, or `src/services/agents/` fails CI via the burn-down gate.

**Acceptance Scenarios**:

1. **Given** Phase 3 lands with `typeCheckingMode = "strict"`, **When** `uv run pyright` runs, **Then** it exits zero.
2. **Given** Phase 3 lands, **When** a reader opens any downgraded legacy module, **Then** the first non-shebang/non-encoding line (or the line immediately after the module docstring) is `# pyright: basic — reason: <short justification>`.
3. **Given** Phase 3 lands, **When** a reader opens the repo's `docs/decisions/` directory, **Then** an ADR exists naming each downgraded module and its responsible owner.
4. **Given** Phase 3 lands and `reportUnnecessaryTypeIgnoreComment = "error"` is still active, **When** Pyright runs, **Then** the two pre-existing `# type: ignore` comments at `solune/backend/src/services/agent_provider.py:501` and `solune/backend/src/services/plan_agent_provider.py:207` either remain necessary (no diagnostic) or have been removed in the same PR.

---

### User Story 4 - Burn-down gate prevents regression and tracks debt (Priority: P3)

A reviewer can trust that type-debt only goes down. A pre-commit hook and CI step refuse any PR that adds `# pyright: basic` to a file inside the strict floor, and every CI build prints the current `# pyright: basic` count so the trend is visible.

**Why this priority**: Makes the gains from Phases 2 and 3 durable. Same priority as Phase 3 because it is what protects Phase 3's contract.

**Independent Test**: Push a branch adding `# pyright: basic` to a file under `src/api/`. The pre-commit hook must reject the commit locally; if bypassed, CI must fail. A separate branch adding the pragma to a non-floor module must succeed but the CI log must show an incremented `# pyright: basic` count.

**Acceptance Scenarios**:

1. **Given** the burn-down gate is wired into pre-commit and CI, **When** a contributor adds `# pyright: basic` anywhere under `src/api/`, `src/models/`, or `src/services/agents/`, **Then** the gate fails with a message naming the offending file and the floor it violates.
2. **Given** the gate is wired in, **When** any CI build runs, **Then** the build log contains a single line of the form `# pyright: basic count: N` reflecting the current count under `solune/backend/src/`.
3. **Given** the backlog of legacy `# pyright: basic` modules has been worked down, **When** a maintainer promotes `reportUnknownMemberType` from `"warning"` to `"error"` in `[tool.pyright]`, **Then** `uv run pyright` still exits zero.

---

### Edge Cases

- **Generated/vendored code under `src/`**: If any file under `solune/backend/src/` is generated (e.g., by OpenAPI export tooling), the strict floor and global strict apply to it the same as hand-written code; the project must either keep the generator's output strict-clean or relocate generated code outside `include = ["src"]`.
- **Stub gaps in third-party libraries**: `githubkit`, `aiosqlite`, and `copilot` have incomplete type information. Phase 1 deliberately keeps `reportUnknownMemberType` at `"warning"` to avoid drowning in noise; Phase 2 may require augmenting `solune/backend/src/typestubs/` rather than littering `# type: ignore` calls inside the floor.
- **Tests pulling from `src/`**: Tests run under `pyrightconfig.tests.json` with `typeCheckingMode = "off"`, but they import from `src/`. Strict-mode changes to `src/` must not require tests to add type annotations to keep working.
- **`# pyright: basic` placement collisions**: Files that already start with module docstrings or `from __future__ import annotations` need the pragma placed in a position Pyright recognises. The Phase 3 work must verify each pragma actually takes effect (i.e., the file no longer surfaces strict errors after the pragma is added).
- **Pre-existing `# type: ignore` comments**: The two known ignores at `agent_provider.py:501` and `plan_agent_provider.py:207` reference SDK preview fields. If a future SDK release fills in the missing TypedDict fields, `reportUnnecessaryTypeIgnoreComment` will fail CI; the contract is that the redundant ignore must then be removed in the same PR that bumps the SDK.
- **Mid-phase `main` drift**: If new untyped code lands on `main` between the Phase 2 baseline measurement and the Phase 2 PR, the floor must be re-measured before merge; partial floor application (e.g., only `src/models` first) is acceptable as a Phase 2a/2b/2c split.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The backend Pyright configuration in `solune/backend/pyproject.toml` MUST set `reportUnnecessaryTypeIgnoreComment = "error"`, `reportMissingParameterType = "error"`, `reportUnknownParameterType = "warning"`, and `reportUnknownMemberType = "warning"` after Phase 1, while keeping `typeCheckingMode = "standard"`. (`reportUnknownParameterType` was originally planned at `"error"` in the user request; baseline measurement during implementation surfaced 381 return-type-unknown errors in FastAPI handlers, far above the spec's anticipated ≤~20-finding budget, so it is demoted to `"warning"` for Phase 1 and inherits the strict-mode promotion via `strict = [...]` in Phase 2.)
- **FR-002**: After Phase 1, `solune/backend/pyrightconfig.tests.json` MUST set `reportUnnecessaryTypeIgnoreComment = "error"` while keeping `typeCheckingMode = "off"`.
- **FR-003**: After each phase, `cd solune/backend && uv run pyright` MUST exit with status zero on the resulting branch.
- **FR-004**: After Phase 2, `[tool.pyright]` MUST contain `strict = ["src/api", "src/models", "src/services/agents"]`, and Pyright MUST treat every file under those trees at strict level regardless of any per-file pragma.
- **FR-005**: After Phase 2, no file inside `src/api/`, `src/models/`, or `src/services/agents/` may carry a `# pyright: basic` or `# pyright: off` pragma.
- **FR-006**: After Phase 3, `[tool.pyright]` MUST set `typeCheckingMode = "strict"`.
- **FR-007**: After Phase 3, every legacy module that fails strict checking MUST carry a `# pyright: basic — reason: <short justification>` pragma at the top of the file (after any shebang, encoding declaration, or module docstring as required by Pyright), and no module may use `# pyright: off` as the downgrade mechanism.
- **FR-008**: After Phase 3, the repo's `docs/decisions/` directory MUST contain an Architecture Decision Record listing every downgraded module and the owner accountable for clearing its pragma.
- **FR-009**: After Phase 4, the pre-commit hook chain MUST fail any commit that introduces `# pyright: basic` to a file inside the strict floor, and the CI Pyright job MUST perform the same check (so a `--no-verify` bypass is still caught).
- **FR-010**: The CI Pyright job MUST emit a single-line, greppable count of `# pyright: basic` occurrences under `solune/backend/src/` on every build.
- **FR-011**: The change MUST NOT modify `solune/backend/pyrightconfig.tests.json`'s `typeCheckingMode` away from `"off"` in any phase.
- **FR-012**: The two pre-existing `# type: ignore[reportGeneralTypeIssues]` comments at `solune/backend/src/services/agent_provider.py:501` and `solune/backend/src/services/plan_agent_provider.py:207` MUST be re-verified at the end of Phase 3; if they have become redundant under strict, they MUST be removed in the same PR.
- **FR-013**: Each phase MUST land as its own pull request (Phase 2 MAY be split into up to three PRs, one per tree), and no single PR may both flip the global mode and apply per-file pragmas to more than the modules enumerated in the Phase 3 ADR.
- **FR-014**: After the legacy backlog is cleared, a single PR MAY promote `reportUnknownMemberType` from `"warning"` to `"error"` in `[tool.pyright]`; that PR MUST leave `uv run pyright` at exit status zero.

### Key Entities *(include if feature involves data)*

- **Pyright configuration block** (`[tool.pyright]` in `solune/backend/pyproject.toml`): Single source of truth for backend type-checking. Holds the global mode, per-tree `strict` floor, and per-rule severity overrides.
- **Tests Pyright configuration** (`solune/backend/pyrightconfig.tests.json`): Separate, intentionally permissive configuration for the test tree. Mode stays `"off"` across all phases; only the unnecessary-ignore rule is mirrored.
- **Strict floor**: The set of trees `src/api`, `src/models`, `src/services/agents` that are contractually held at strict regardless of global mode and may not contain per-file downgrade pragmas.
- **Legacy downgraded module**: A file outside the strict floor that carries `# pyright: basic — reason: …` because it has not yet been brought up to strict. Tracked by the Phase 3 ADR and counted by the Phase 4 CI line.
- **Type-stub augmentation** (`solune/backend/src/typestubs/`): Project-local stub package used to fill gaps in `githubkit`, `copilot`, and similar third-party libraries. Phase 2 may add to it rather than introducing per-file ignores inside the floor.
- **ADR for downgraded modules** (new file under `solune/docs/decisions/`): Names every legacy downgrade and assigns an owner.
- **Burn-down gate**: A grep-based check enforced in both the pre-commit hook and CI that (a) refuses new `# pyright: basic` inside the strict floor and (b) prints the global pragma count.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After Phase 1 ships, the number of unannotated function parameters and unused `# type: ignore` comments newly introduced to the backend in any subsequent PR is zero, measured by CI Pyright failures attributable to `reportMissingParameterType`, `reportUnknownParameterType`, or `reportUnnecessaryTypeIgnoreComment`.
- **SC-002**: After Phase 2 ships, 100% of files under `src/api/`, `src/models/`, and `src/services/agents/` are checked at strict level, and the count of files in those trees carrying any per-file Pyright downgrade pragma is zero.
- **SC-003**: After Phase 3 ships, the global `typeCheckingMode` is `strict`, and the number of files under `solune/backend/src/` carrying `# pyright: basic` is fully enumerated in an ADR with a named owner per file.
- **SC-004**: At every phase boundary, `uv run pyright --outputjson | jq '.generalDiagnostics | length'` reports zero error-severity diagnostics on the resulting branch (warning-severity from `reportUnknownMemberType` is allowed until Phase 4 promotes it).
- **SC-005**: The total elapsed time for the local backend developer feedback loop (`uv run pyright` on a clean checkout) does not increase by more than 25% between the pre-Phase-1 baseline and the post-Phase-3 state.
- **SC-006**: After the burn-down gate is in place, every CI build records the current `# pyright: basic` count in its log so the trend is visible across at least the last 30 builds, and that count is monotonically non-increasing on the default branch.
- **SC-007**: After Phase 4 promotes `reportUnknownMemberType` to `"error"`, `uv run pyright` continues to exit zero on the default branch with no rollback to `"warning"` required.

## Assumptions

- The repository's Pyright runner is `uv run pyright` invoked from `solune/backend/`, as stated in the user description; CI is assumed to invoke the same command (or a wrapper that ultimately calls it) so configuration changes in `pyproject.toml` and `pyrightconfig.tests.json` take effect without further CI edits.
- The `# noqa: <code> — reason: <text>` and `// eslint-disable-next-line <rule> — reason: <text>` patterns described as "the repo's reason convention" exist; Phase 3 pragmas follow the same `— reason:` syntax for consistency.
- ADRs live under `solune/docs/decisions/` (visible in the workspace structure); the Phase 3 ADR is added there unless a more specific backend-only decisions folder is preferred at implementation time.
- The four named legacy hotspots (`src/services/github_projects/**`, `src/services/copilot_polling/**`, `src/main.py`, `src/services/chat_agent.py`) are *expected* candidates for `# pyright: basic`; the Phase 3 PR enumerates the actual set after measurement and may include or exclude any of them.
- The strict floor is exactly `src/api`, `src/models`, `src/services/agents` for the initial rollout; expanding it to `src/middleware/` or `src/dependencies.py` is explicitly deferred to a follow-up after Phase 2 lands.
- Test files retain `typeCheckingMode = "off"` indefinitely; this feature does not propose tightening the test config beyond mirroring `reportUnnecessaryTypeIgnoreComment`.
- "Per-tree" in Phase 2 means the three named subtrees may ship as separate PRs in any order; ordering is left to the implementer based on observed error counts during the Phase 2 baseline measurement.
