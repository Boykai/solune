# Phase 0 Research: Tighten Backend Pyright (standard → strict, gradually)

**Feature**: 001-backend-pyright-strict
**Date**: 2026-04-18

This document resolves the open questions and validates the assumptions in `spec.md` and `plan.md` Technical Context. No `NEEDS CLARIFICATION` markers were present; the items below capture investigations that informed concrete defaults.

---

## R1 — Pyright pragma syntax with trailing reason text

**Decision**: Place the pragma on its own line and the reason on the *next* line:

```python
# pyright: basic
# reason: githubkit Issue model uses untyped attribute access; tracked in ADR-007
```

**Rationale**: Pyright's source-file pragma parser reads the value token after `pyright:` and ignores trailing text on the same line, but only when the trailing text is a separate comment. To eliminate any risk of the parser rejecting the pragma when it sees unexpected characters between `basic` and a hash, the safest portable form is two adjacent comment lines. This also keeps the `reason:` token greppable with the same regex used for `noqa` and `eslint-disable` reasons elsewhere in the repo.

**Alternatives considered**:

- `# pyright: basic — reason: …` (em-dash, as written in the user's plan): not used in the repo today (repo uses `--` ASCII). Rejected to keep grep patterns ASCII-only.
- `# pyright: basic -- reason: …` (single line, ASCII double-dash, matching `solune/frontend/src/lib/lazyWithRetry.ts` style): works for ESLint because ESLint explicitly parses `--` as a separator, but Pyright has no documented contract about trailing text on the pragma line. Rejected as fragile.
- `# pyright: ignore[<rule>]` per-line: defeats the purpose of a per-file downgrade and would scatter noise. Rejected.

**Verification step (executed in Phase 3)**: After adding the pragma to one legacy file, re-run `uv run pyright`; the file's strict-mode errors must disappear. If they do not, the pragma was placed incorrectly (e.g., below the first import) and must be moved to the top.

---

## R2 — Repo "reason:" convention

**Decision**: Use the token `reason:` (lowercase, with colon) preceded by `--` *or* on its own comment line. Match what already exists in the codebase rather than introducing the em-dash variant from the user's plan.

**Rationale**: Existing patterns observed in the repo:

- `solune/scripts/export-openapi.py`: `# noqa: E402 — reason: …` (em-dash here)
- `solune/frontend/src/lib/lazyWithRetry.ts`: `// eslint-disable-next-line … -- reason: …` (ASCII `--`)
- `solune/frontend/src/components/tools/UploadMcpModal.tsx`: `// eslint-disable … -- reason: …` (ASCII `--`)

The ASCII `--` form is more common and easier to grep. Per R1, Phase 3 pragmas land on a dedicated line (`# reason: …`) so the dash question is moot for the pragma itself; the existing `# type: ignore` re-verifications in FR-012 keep their original em-dash for source-stability (changing them would touch lines not otherwise modified).

**Alternatives considered**: Force-rewrite all existing `noqa`/`eslint-disable` reasons to one canonical dash style. Rejected — out of scope for this feature.

---

## R3 — CI invocation form and `[tool.pyright] include`

**Decision**: Treat `include = ["src"]` in `[tool.pyright]` as redundant but harmless. Do not remove it. The CI step at `.github/workflows/ci.yml:51` is `uv run pyright src` (positional arg), which overrides `include`. Local invocations of `uv run pyright` (no args) honour `include`. Both paths must continue to work.

**Rationale**: Removing `include` would break local-no-arg invocations. Removing the positional `src` from CI would force CI to honour `include` and is unnecessary churn. The `strict = [...]` setting we add in Phase 2 is path-relative to the project root and is honoured regardless of how Pyright is invoked.

**Alternatives considered**: Standardise to one invocation form. Rejected — the user's verification recipe explicitly uses `cd solune/backend && uv run pyright` (no args), and CI's positional form has been stable; both paths are kept.

---

## R4 — `reportUnknownMemberType` severity choice in Phase 1

**Decision**: Set to `"warning"` in Phase 1, promote to `"error"` in Phase 4 only after the legacy backlog is cleared.

**Rationale**: `githubkit` and `aiosqlite` return a high volume of partially-typed members. Raising this rule to `"error"` in Phase 1 would block Phase 1 entirely (the spec's goal of "≤~20 new findings inline" would be violated). The other three new rules (`reportUnnecessaryTypeIgnoreComment`, `reportMissingParameterType`, `reportUnknownParameterType`) target patterns that are sparse in the current codebase and safe to set at `"error"` immediately.

**Alternatives considered**:

- All four rules at `"error"` in Phase 1 (Option A in the user's plan): rejected per user recommendation B.
- `reportUnknownMemberType` deferred to Phase 5: rejected — the spec's SC-007 explicitly closes the loop in Phase 4.

---

## R5 — Phase 2 baseline measurement protocol

**Decision**: Before opening the Phase 2 PR, run Pyright with a *temporary local* `strict = ["src/api", "src/models", "src/services/agents"]` setting (do not commit it) and record per-tree error counts in the PR description. Tree ordering for split PRs (2a/2b/2c) is by ascending error count: cheapest tree first. The `strict = [...]` line is only committed when all three trees produce zero errors at strict.

**Rationale**: The spec allows splitting Phase 2 into up to three PRs (FR-013). Cheapest-first ordering minimises the time the floor is partial and gives the team early wins.

**Anticipated hotspots** (from the user's plan, to be confirmed at measurement time):

- `src/api/chat.py`: `Depends()` return types unbound → `reportGeneralTypeIssues`/`reportUnknownVariableType`.
- `src/api/projects.py`: WebSocket payloads typed as `Any` → `reportUnknownArgumentType`.
- `src/services/agents/.../service.py:71`: `aiosqlite.Row` accessed by index → `reportUnknownMemberType` at strict.

**Alternatives considered**: Add the floor and exclude failing files via per-file pragma. Rejected — explicitly forbidden by FR-005.

---

## R6 — Type-stub augmentation vs. per-file ignores inside the floor

**Decision**: When the floor surfaces errors that originate from incomplete third-party stubs (chiefly `githubkit` and `agent_framework_github_copilot`), prefer extending `solune/backend/src/typestubs/` over adding `# type: ignore` calls inside floor files.

**Rationale**: `# type: ignore` inside the floor sets a bad precedent and survives review only as a one-off. A typestub addition is reusable across all floor files that touch the same SDK surface. Existing typestub structure (verified via file search) already covers `githubkit/`, `agent_framework_github_copilot/`, and `copilot/`, so additions are extensions, not new packages.

**Alternatives considered**: File issues upstream against `githubkit` and wait. Rejected — non-deterministic timeline; we still need the floor green now.

---

## R7 — Burn-down gate: implementation site

**Decision**: Implement the gate as a small block inside the existing `solune/scripts/pre-commit` hook (which is mirrored to `.git/hooks/pre-commit` by `solune/scripts/setup-hooks.sh`) and as an inline `grep`-based step inside `.github/workflows/ci.yml` immediately after the existing Pyright step. The CI count line is emitted by the same step.

**Rationale**: Spec FR-009 requires both pre-commit *and* CI enforcement (so `--no-verify` cannot bypass it). The spec's "Pragma gate enforced via grep; no new tool added" decision rules out introducing a separate static-analysis tool.

**Gate algorithm** (executed twice — once locally, once in CI):

```bash
# Reject new pragma in floor
violations=$(git diff --cached --name-only --diff-filter=ACM \
  | grep -E '^solune/backend/src/(api|models|services/agents)/' \
  | xargs -r grep -lE '^# pyright: basic\b' 2>/dev/null || true)
if [ -n "$violations" ]; then
  echo "ERROR: # pyright: basic is not allowed inside the strict floor:"
  echo "$violations"
  exit 1
fi
```

The CI variant uses `git diff origin/main...HEAD` instead of `--cached`. Both paths print `# pyright: basic count: $(grep -rEc '^# pyright: basic\b' solune/backend/src | awk -F: '{s+=$2} END{print s}')` after the gate.

**Alternatives considered**: A standalone Python script under `solune/scripts/`. Rejected as more code than necessary for a 5-line grep.

---

## R8 — ADR location

**Decision**: Add the Phase 3 ADR as `solune/docs/decisions/007-backend-pyright-strict-downgrades.md` (next number after the existing `006-signal-sidecar.md`). Keep the existing repo numbering scheme.

**Rationale**: The folder already exists with six ADRs and a `README.md` index. No new directory needed. The ADR title aligns with the feature branch name for easy traceability.

**Alternatives considered**: Backend-scoped ADR folder (`solune/backend/docs/decisions/`). Rejected — no such folder exists today; introducing one duplicates the index.

---

## R9 — Local feedback-loop baseline (SC-005)

**Decision**: Capture the baseline by running `cd solune/backend && time uv run pyright` *three times* on a clean checkout of the pre-Phase-1 commit, recording the median wall-clock. Re-run the same protocol on the post-Phase-3 branch. Budget: post must be ≤ 1.25× baseline (SC-005).

**Rationale**: Three samples eliminate first-run cold-cache outliers. Pyright caches in-memory only; no on-disk cache to clear between runs.

**Alternatives considered**: `pyright --stats` JSON parsing. Rejected — overkill for a 25 % budget check.

---

## R10 — Pre-existing `# type: ignore` re-verification (FR-012)

**Decision**: At the end of Phase 3, run `uv run pyright` with the new strict mode. If `reportUnnecessaryTypeIgnoreComment` flags either of the two known ignores, remove that ignore in the same Phase 3 PR. If both are still required, leave them untouched.

**Sites to check**:

- `solune/backend/src/services/agent_provider.py:501` — `# type: ignore[reportGeneralTypeIssues] — reason: GitHubCopilotOptions TypedDict doesn't declare reasoning_effort yet; SDK preview field`
- `solune/backend/src/services/plan_agent_provider.py:207` — `# type: ignore[reportGeneralTypeIssues] — reason: SessionConfig TypedDict doesn't declare reasoning_effort yet; SDK preview field`

**Rationale**: Both files are *outside* the strict floor (they live in `src/services/`, not `src/services/agents/`), so they will receive a `# pyright: basic` pragma in Phase 3 unless they happen to be strict-clean. Under `# pyright: basic`, `reportGeneralTypeIssues` is still on, so the `# type: ignore` may still be needed; but the *strict* re-verification happens before pragmas are added, so the canonical check is during the Phase 3 baseline measurement (R5 analogue for Phase 3).

**Alternatives considered**: Defer re-verification to Phase 4. Rejected — FR-012 is explicit that this happens at the end of Phase 3.

---

## Open questions

None. All Technical Context entries resolved with concrete defaults above. No `NEEDS CLARIFICATION` markers remain.
