# Phase 1 Data Model: Tighten Backend Pyright

**Feature**: 001-backend-pyright-strict
**Date**: 2026-04-18

This feature changes configuration files, not runtime data. The "entities" below are configuration records and source-file annotations whose shape and lifecycle the implementation must preserve.

---

## E1 — `[tool.pyright]` block (in `solune/backend/pyproject.toml`)

**Storage**: TOML table starting at `pyproject.toml:119`.

**Fields**:

| Key | Type | Phase 0 (current) | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|---|---|---|---|---|---|---|
| `pythonVersion` | string | `"3.13"` | `"3.13"` | `"3.13"` | `"3.13"` | `"3.13"` |
| `typeCheckingMode` | string | `"standard"` | `"standard"` | `"standard"` | `"strict"` | `"strict"` |
| `include` | array[string] | `["src"]` | `["src"]` | `["src"]` | `["src"]` | `["src"]` |
| `exclude` | array[string] | `["**/__pycache__", "htmlcov"]` | unchanged | unchanged | unchanged | unchanged |
| `reportMissingTypeStubs` | bool | `false` | `false` | `false` | `false` | `false` |
| `reportMissingImports` | string | `"error"` | `"error"` | `"error"` | `"error"` | `"error"` |
| `stubPath` | string | `"src/typestubs"` | unchanged | unchanged | unchanged | unchanged |
| `reportUnnecessaryTypeIgnoreComment` | string | *(absent)* | `"error"` | `"error"` | `"error"` | `"error"` |
| `reportMissingParameterType` | string | *(absent)* | `"error"` | `"error"` | `"error"` | `"error"` |
| `reportUnknownParameterType` | string | *(absent)* | `"warning"` | `"warning"` | `"warning"` | `"error"` |
| `reportUnknownMemberType` | string | *(absent)* | `"warning"` | `"warning"` | `"warning"` | `"error"` |
| `strict` | array[string] | *(absent)* | *(absent)* | `["src/api", "src/models", "src/services/agents"]` | unchanged | unchanged |

**Validation rules**:

- `typeCheckingMode` ∈ {`"standard"`, `"strict"`} only (never `"basic"` or `"off"` at the project level).
- `strict` paths MUST be repo-relative and MUST exist on disk; Pyright silently ignores non-existent entries, which would defeat the floor contract.
- `include` MUST contain `"src"` so local no-arg `uv run pyright` invocations remain valid.

**State transitions**: Forward-only across phases. No phase removes a field that an earlier phase added. Rollback is by `git revert` of the phase PR.

---

## E2 — Tests Pyright config (`solune/backend/pyrightconfig.tests.json`)

**Storage**: JSON file at `solune/backend/pyrightconfig.tests.json`.

**Fields** (delta only — full file shown in `contracts/pyright-config-contract.md`):

| Key | Phase 0 | Phase 1 → 4 |
|---|---|---|
| `typeCheckingMode` | `"off"` | `"off"` (unchanged across all phases — FR-011) |
| `reportUnnecessaryTypeIgnoreComment` | *(absent)* | `"error"` (added in Phase 1) |

All other keys (`include`, `exclude`, `pythonVersion`, `reportInvalidTypeForm`, `stubPath`, `executionEnvironments`) are unchanged.

---

## E3 — Per-file `# pyright: basic` pragma (Phase 3 onward)

**Storage**: Two consecutive Python comment lines at the top of a downgraded module file, after any shebang, encoding declaration, or module docstring.

**Format** (per Phase 0 research R1):

```python
"""Optional module docstring (if present, stays first)."""

# pyright: basic
# reason: <one-line justification — same convention as # noqa and eslint-disable>

from __future__ import annotations  # imports follow the pragma
…
```

**Validation rules**:

- The pragma line MUST match the regex `^# pyright: basic\s*$` (no trailing text on the same line — see R1).
- The next non-blank line MUST be `# reason: …` so the burn-down gate's grep can correlate violations with their stated reason.
- The pragma MUST NOT appear inside any file under `solune/backend/src/api/`, `solune/backend/src/models/`, or `solune/backend/src/services/agents/` (FR-005, enforced by the burn-down gate).
- A file MUST NOT carry both `# pyright: basic` and `# pyright: off`; only `basic` is permitted as a downgrade (FR-007).

**Lifecycle**: A pragma is added when a file fails strict and removed when a follow-up PR has refactored the file to be strict-clean. The Phase 3 ADR (E5) is updated in the same PR that removes a pragma, so the file count in the ADR matches `grep -r '^# pyright: basic' solune/backend/src/ | wc -l`.

---

## E4 — Pre-existing `# type: ignore[<rule>]` comments

**Storage**: Trailing comments on individual statements.

**Known instances** (from Phase 0 grep):

| File | Line | Rule | Reason |
|---|---|---|---|
| `solune/backend/src/services/agent_provider.py` | 501 | `reportGeneralTypeIssues` | GitHubCopilotOptions TypedDict missing `reasoning_effort` |
| `solune/backend/src/services/plan_agent_provider.py` | 207 | `reportGeneralTypeIssues` | SessionConfig TypedDict missing `reasoning_effort` |

**Validation rules** (Phase 1 onward, via `reportUnnecessaryTypeIgnoreComment = "error"`):

- An existing `# type: ignore[<rule>]` is allowed if and only if removing it would cause Pyright to surface the named diagnostic.
- Phase 3 re-verifies both instances under strict (research R10). Removal happens in the Phase 3 PR if either becomes redundant.

---

## E5 — Phase 3 ADR (`solune/docs/decisions/007-backend-pyright-strict-downgrades.md`)

**Storage**: New markdown file under the existing repo ADR folder (R8).

**Required structure**:

- Standard ADR header (Status, Date, Context, Decision, Consequences) matching the format used by `001-githubkit-sdk.md` through `006-signal-sidecar.md`.
- A table enumerating every downgraded module with columns: `file path` | `reason` | `owner` | `target removal milestone`.
- The `file path` column MUST be the exhaustive set of files containing `# pyright: basic` under `solune/backend/src/` immediately after the Phase 3 PR.

**Validation rule**: The set of file paths in the ADR table MUST equal the output of `grep -rl '^# pyright: basic' solune/backend/src/` immediately after the Phase 3 PR merges. Drift between the two is a CI failure (informally enforced by the count line — Phase 4).

---

## E6 — Burn-down gate state (synthetic, computed per CI build)

**Storage**: None — computed on the fly; printed to the CI log.

**Computed value**: `# pyright: basic count: N` where `N = count of files under solune/backend/src/ matching the pragma line regex from E3`.

**Validation rules**:

- `N` MUST be monotonically non-increasing on the default branch (SC-006).
- A PR adding a pragma MUST also remove one elsewhere, OR add a corresponding row to the E5 ADR table; reviewer-enforced, surfaced by the count diff in PR CI vs. base branch CI.

---

## Cross-entity invariants

1. **Floor exclusivity**: `count(files under strict floor with E3 pragma) == 0` after Phase 2 onward.
2. **ADR consistency**: `set(E5.file_paths) == set(files matching E3 pragma)` after Phase 3 onward.
3. **Tests-config inertness**: `E2.typeCheckingMode == "off"` across all phases.
4. **Existing-ignore validity**: For every entry in E4, either Pyright surfaces the suppressed rule when the ignore is hypothetically removed, or the ignore was removed in Phase 3.
