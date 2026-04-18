# Research: Tighten Backend Pyright (Standard → Strict, Gradually)

**Feature**: 001-tighten-backend-pyright | **Date**: 2026-04-18

## Research Tasks

### R1: Pyright `strict` vs `standard` — diagnostic delta

**Decision**: Use phased rollout (`standard` → safety-net rules → `strict` floor → global `strict`).

**Rationale**: Pyright's `strict` mode enables ~30 additional diagnostic rules beyond `standard`. Enabling them all at once across 183 source files would produce a large, hard-to-review diff. A phased approach lets each PR stay focused on a specific diagnostic category or package scope.

**Alternatives considered**:

- *Single mega-PR*: Faster to land but reviewer-hostile; a single regression blocks the entire change. Rejected.
- *Per-file opt-in*: Too granular; hundreds of `# pyright: strict` pragmas would be needed. Rejected.

### R2: `reportUnknownMemberType` severity level

**Decision**: Start at `"warning"` in Phase 1; promote to `"error"` in Phase 4.

**Rationale**: The `githubkit` and `aiosqlite` libraries have incomplete type stubs. Under `reportUnknownMemberType = "error"`, Phase 1 would produce dozens of errors in code that correctly uses these libraries. Setting it to `"warning"` makes the diagnostics visible without blocking CI. The repo's `src/typestubs/` directory already contains partial stubs for `githubkit`, `copilot`, and `agent_framework_github_copilot`, which can be augmented over time.

**Alternatives considered**:

- *Error immediately*: Blocks Phase 1 with stub-quality issues unrelated to the feature's own code. Rejected.
- *Ignore entirely*: Hides real issues in first-party code. Rejected.

### R3: Pyright `strict = [...]` configuration behaviour

**Decision**: Use `strict = ["src/api", "src/models", "src/services/agents"]` as a floor contract.

**Rationale**: Pyright supports `strict = [...]` in `pyproject.toml` `[tool.pyright]` to apply strict-mode checking to specific paths. This acts as a floor: even when the global mode is `standard`, files matching these paths are checked at `strict` level. When the global mode later flips to `strict`, the `strict = [...]` declaration remains as an explicit contract that these paths may never be downgraded. This is not redundant — it serves as documentation and a guard rail.

**Alternatives considered**:

- *Per-file `# pyright: strict` pragmas*: Does not aggregate into a single config declaration; easy to miss a file. Rejected.
- *Remove `strict = [...]` after global flip*: Loses the floor contract; a future `# pyright: basic` in a protected file would go unnoticed. Rejected.

### R4: Legacy opt-out mechanism

**Decision**: Use `# pyright: basic` file-level pragmas (not `# pyright: off`).

**Rationale**: The `# pyright: basic` pragma preserves baseline type-checking on legacy files (import resolution, basic type errors) while opting out of the stricter diagnostics that `strict` adds. Using `# pyright: off` would disable all checking, hiding real bugs. The repo convention already requires `reason:` comments on suppressions (`# noqa`, `eslint-disable`), and the same convention applies to pyright pragmas.

**Alternatives considered**:

- *`# pyright: off`*: Too aggressive; disables all checking. Rejected.
- *`exclude = [...]` in pyproject.toml*: Silent exclusion; not visible in the file itself. Rejected.
- *No opt-out (fix everything)*: Unrealistic for 25+ files in `github_projects` and `copilot_polling` with incomplete third-party stubs. Rejected.

### R5: Test configuration under strict mode

**Decision**: Keep `pyrightconfig.tests.json` at `typeCheckingMode = "off"`; only mirror `reportUnnecessaryTypeIgnoreComment = "error"`.

**Rationale**: Test files use heavy mocking (`MagicMock`, `AsyncMock`, `patch`) that produces false-positive strict diagnostics. The value of strict checking on test files is low relative to the noise. However, catching redundant `# type: ignore` comments in tests is still valuable and has no false-positive risk.

**Alternatives considered**:

- *Tests at `basic` mode*: Would require annotating mock factories and fixtures extensively. Cost outweighs benefit. Rejected.
- *Tests at `strict`*: Counter-productive given mock-heavy patterns. Rejected.

### R6: CI enforcement for strict floor integrity

**Decision**: Use `grep -rn "pyright: basic" src/api/ src/models/ src/services/agents/` as a CI gate.

**Rationale**: This is the simplest enforcement mechanism that requires no new tooling. If any file inside the strict floor contains a `# pyright: basic` pragma, the grep returns non-zero and CI fails. This prevents accidental or lazy downgrades in protected packages.

**Alternatives considered**:

- *Custom pre-commit hook*: More complex; the grep one-liner is sufficient. Rejected for now.
- *Pyright plugin/wrapper*: Overkill for a simple containment check. Rejected.

### R7: Existing `type: ignore` comment validity

**Decision**: Re-verify `agent_provider.py:501` and `plan_agent_provider.py:207` during each phase.

**Rationale**: Both comments suppress `reportGeneralTypeIssues` for SDK preview fields (`reasoning_effort`) not yet declared in TypedDict stubs. Under `strict` mode, the diagnostic category may change or the stubs may be updated. `reportUnnecessaryTypeIgnoreComment = "error"` will automatically flag them if they become redundant, so manual re-verification is a safety check rather than a required action.

**Alternatives considered**:

- *Remove proactively*: Risky if the SDK stubs have not been updated. Rejected.
- *Leave without re-checking*: The error rule handles this automatically, but documenting the intent is good practice. Rejected as sole approach.

### R8: ADR format and location

**Decision**: Create ADR at `solune/backend/docs/decisions/001-pyright-strict-legacy-opt-outs.md`.

**Rationale**: The `docs/decisions/` directory follows the standard Architecture Decision Record pattern. The ADR lists each downgraded module with its owner and reason, making the debt visible to reviewers and enabling targeted burn-down.

**Alternatives considered**:

- *Comment in `pyproject.toml`*: Not enough structure for a table of modules and owners. Rejected.
- *GitHub issue*: Issues can be closed/lost; a committed ADR is versioned and reviewable. Rejected as sole location.

## All NEEDS CLARIFICATION — Resolved

No items remain unresolved. All technical decisions are captured above.
