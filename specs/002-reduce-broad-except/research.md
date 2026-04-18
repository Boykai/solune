# Phase 0 Research: Reduce Broad-Except + Log + Continue Pattern

**Feature**: 002-reduce-broad-except
**Date**: 2026-04-18

This document resolves the open questions and validates the assumptions in `spec.md` and `plan.md` Technical Context. No `NEEDS CLARIFICATION` markers were present; the items below capture investigations that informed concrete design decisions.

---

## R1 — Ruff BLE001 rule behaviour and configuration

**Decision**: Add `"BLE"` as a new entry in the `select` list within `[tool.ruff.lint]` at `solune/backend/pyproject.toml:86`. BLE001 is the only rule in the `BLE` (flake8-blind-except) category. It flags `except Exception` and `except BaseException` handlers.

**Rationale**: BLE001 is not auto-fixable — `ruff check --fix` will list violations but not rewrite them. This is correct behaviour because the resolution (Narrow, Promote, or Tag) requires human judgement. The rule fires on `except Exception` regardless of what happens inside the handler (logging, re-raising, passing), so every existing handler will be flagged until explicitly suppressed with `# noqa: BLE001`. This aligns with FR-001 and FR-002.

**Alternatives considered**:

- Using `per-file-ignores` to phase in BLE001 file-by-file: rejected because the spec requires immediate CI visibility of all violations (SC-002). Phased suppression would hide the true violation count.
- Writing a custom Ruff plugin: rejected — BLE001 already covers the exact pattern. No new tooling needed (Constitution V — simplicity).

**Verification**: After adding `"BLE"` to select, run `cd solune/backend && uv run ruff check src/ --select BLE001 --statistics` to confirm the expected ~568 violations are reported.

---

## R2 — Existing `# noqa:` convention in the codebase

**Decision**: Adopt the inline suppression format already in use: `# noqa: BLE001 — reason: <human-readable explanation>`. Use the em-dash (`—`) separator as the primary convention.

**Rationale**: The codebase uses two dash variants:

- Em-dash (`—`): `src/api/chat.py:391`, `src/api/chat.py:937`, `src/api/cleanup.py` (B008 and PTH119 suppressions)
- ASCII hyphen (`-`): `src/api/health.py:84` (B009 suppressions)

The em-dash variant is more common in recently-written code and is the form specified in the issue description. Ruff itself only parses `# noqa: CODE` — everything after the rule code is ignored by the linter and exists purely for human/review consumption. The `— reason:` suffix is therefore safe to standardise on without affecting tool behaviour.

**Alternatives considered**:

- Force-rewriting all existing noqa comments to one canonical dash style: rejected — out of scope for this feature (the issue only concerns BLE001, not a repo-wide noqa audit).
- Using a custom Ruff plugin to enforce the `— reason:` suffix: rejected — over-engineering for a human-enforced convention. Code review policy is sufficient per spec Acceptance Scenario 3.2.

---

## R3 — Triage bucket distribution estimate

**Decision**: Based on manual sampling of ~100 handlers across the top files, the estimated triage distribution is:

| Bucket | Estimated % | Count (of ~568) | Primary exception types |
|---|---|---|---|
| **Narrow** | ~65% | ~369 | `aiosqlite.Error`, `httpx.HTTPStatusError`, `json.JSONDecodeError`, `OSError`, `KeyError`, `ValueError`, `asyncio.TimeoutError` |
| **Promote** | ~10% | ~57 | Handlers where the caller already has error handling or where the error should propagate |
| **Tagged** | ~25% | ~142 | Third-party callbacks, `asyncio.TaskGroup` drains, plugin/extension hooks, `_with_fallback()` chains |

**Rationale**: The sampling focused on the top 5 files by handler count. In `pipeline.py` (47 handlers), approximately 30 wrap `aiosqlite` calls and can be narrowed to `aiosqlite.Error | OSError`. In `chat.py` (41 handlers), approximately 25 wrap JSON parsing or database operations and can be narrowed. The `github_projects/` service files (~52 handlers) are predominantly Tagged because they implement the best-effort HTTP pattern that will be refactored in Workstream B — once the `best_effort()` helper is in place, the handler moves from `except Exception` to catching `httpx.HTTPStatusError | httpx.ConnectError | httpx.TimeoutException` inside the helper, and the call sites no longer need their own try/except at all.

**Alternatives considered**:

- Narrowing all GitHub-projects handlers individually (without the helper): rejected — this would leave ~50 duplicate try/except blocks, violating DRY (Constitution V). The helper consolidation is the better path for these handlers.
- Running `ruff check` with BLE001 to get exact counts before design: informative but not design-changing. The distribution estimate is sufficient for planning triage batch sizes.

---

## R4 — Domain-error helper: API shape

**Decision**: Implement `best_effort()` as an async function on the `_ServiceMixin` base class in `solune/backend/src/services/github_projects/service.py`. Signature:

```python
async def _best_effort(
    self,
    fn: Callable[..., Awaitable[T]],
    *args: Any,
    fallback: T,
    context: str,
    log_level: int = logging.ERROR,
    **kwargs: Any,
) -> T:
```

**Rationale**: The function is placed on the mixin rather than as a standalone utility because:

1. It needs access to the logger instance (each service has its own `logger = logging.getLogger(__name__)`).
2. All call sites are already methods on classes that inherit from `_ServiceMixin`.
3. Making it a method avoids threading `self.logger` through every call.

The `context` parameter replaces the ad-hoc log message string (e.g., `"REST PR search error for issue #%d"`). The `fallback` parameter replaces the hard-coded return values (`[]`, `None`, `False`, `""`). The `log_level` parameter preserves the existing logging severity (some sites use `logger.error()`, others `logger.warning()` or `logger.debug()`).

**Caught exceptions**: The helper catches `Exception` internally — this is intentional and receives a `# noqa: BLE001 — reason: best-effort helper is the canonical wrapper; callers pass specific context` tag. This is one of the explicitly Tagged handlers per FR-004.

**Alternatives considered**:

- A decorator instead of a callable: rejected — decorators cannot easily parameterise the fallback value and log message per call site.
- A standalone function in `utils.py`: rejected — would require passing the logger instance and would be less discoverable for service-layer developers.
- Catching only `httpx.HTTPStatusError | httpx.ConnectError | httpx.TimeoutException` instead of `Exception`: rejected — the services call `_rest()` and `_graphql()` which may raise `GitHubAPIError`, `asyncio.TimeoutError`, or SDK-internal exceptions. Narrowing to httpx types would miss legitimate failure modes. The helper's purpose is to be the single controlled point of broad catching, with explicit logging (FR-006, FR-007).

---

## R5 — Interaction between Workstream A and Workstream B

**Decision**: Workstream A (lint enablement + triage) ships first and independently. Workstream B (helper + refactor) ships second. When Workstream B lands, it removes Tagged handlers from the `github_projects/` files by replacing them with `_best_effort()` calls — this reduces the Tagged handler count by ~50 and eliminates the corresponding `# noqa: BLE001` suppressions.

**Rationale**: The spec explicitly requires independence (FR-010). The sequencing above is natural because:

1. Workstream A must enable the lint rule before any suppressions are meaningful.
2. Workstream B's refactor eliminates handlers — it does not suppress them, so it has no dependency on the tag convention.
3. If Workstream B lands first, the ~50 handler sites would still need individual `# noqa: BLE001` tags during the window before the helper is applied, then the tags would be removed. Shipping A first avoids this churn.

**Alternatives considered**:

- Shipping B first: rejected — creates temporary churn (add tags, then remove them).
- Shipping A and B in the same PR: rejected — violates FR-010 and makes review harder.

---

## R6 — CI integration for BLE001

**Decision**: No CI configuration changes required. The existing CI step at `.github/workflows/ci.yml` runs `uv run ruff check` which will automatically pick up the new `"BLE"` select entry from `pyproject.toml`. BLE001 violations will fail the lint check immediately, satisfying FR-002.

**Rationale**: Ruff reads `pyproject.toml` at invocation time. Adding `"BLE"` to `select` is the only configuration change needed. The CI job already runs `uv run ruff check` (verified via ci.yml).

**Alternatives considered**:

- Adding a separate CI step for BLE001: rejected — redundant. The existing lint step covers all selected rules.
- Running BLE001 in warning mode first: rejected — the spec requires immediate blocking (SC-002). Warnings would allow new violations to merge.

---

## R7 — `except Exception` vs `except BaseException` scope

**Decision**: BLE001 flags both `except Exception` and `except BaseException`. The codebase uses `except Exception` exclusively (no `except BaseException` handlers found). The triage scope is therefore limited to `except Exception` handlers only.

**Rationale**: `BaseException` subclasses like `KeyboardInterrupt` and `SystemExit` should never be caught silently (edge case from spec). Since no `except BaseException` handlers exist in the codebase, this is a non-issue, but BLE001 would catch any future introduction — a bonus safety net.

**Alternatives considered**: None — BLE001's scope is correct as-is.

---

## R8 — Triage batch strategy for large files

**Decision**: Large files (`pipeline.py` with 47 handlers, `chat.py` with 41, `orchestrator.py` with 32) should be triaged in dedicated PRs — one PR per file. Smaller files can be batched by directory (e.g., all files under `src/api/` except `chat.py` in one PR, all files under `src/services/github_projects/` in another).

**Rationale**: The spec's edge case section notes that "large files should be triaged incrementally to keep pull requests reviewable." A PR touching 47 handlers in one file is already substantial; combining it with other files would create an unreviewable diff. The per-directory batching for smaller files keeps PR count manageable (~8–12 triage PRs total).

**Alternatives considered**:

- One monolithic triage PR: rejected — explicitly called out as undesirable in the spec's Assumptions section.
- Per-handler PRs: rejected — excessive overhead. Per-file or per-directory is the right granularity.

---

## R9 — Tag convention documentation location

**Decision**: Document the `# noqa: BLE001 — reason:` convention in a new section within the existing `solune/backend/README.md` or as a dedicated `CONTRIBUTING.md` section. The documentation should include: format specification, when to use it, and 3–4 examples covering the most common Tagged scenarios (third-party callback, asyncio.TaskGroup, best-effort helper, plugin hook).

**Rationale**: FR-005 requires that the convention be findable by a new contributor "within 2 minutes" (SC-005). The backend README is the natural discovery point. A dedicated ADR is not warranted because this is a convention, not an architectural decision.

**Alternatives considered**:

- ADR in `solune/docs/decisions/`: rejected — the convention is a coding standard, not an architectural decision. ADRs are for irreversible or high-impact technical choices.
- Inline comments in `pyproject.toml`: rejected — insufficient for the level of documentation required (format, when-to-use, examples).

---

## R10 — `_with_fallback()` interaction with `_best_effort()`

**Decision**: The existing `_with_fallback()` method in `service.py` (lines 223–314) is a different pattern from `_best_effort()` and should be kept as-is. `_with_fallback()` implements a primary → verify → fallback strategy chain and already handles its own exception logging. `_best_effort()` targets the simpler "single call → log → return fallback" pattern.

**Rationale**: The two patterns serve different purposes:

- `_with_fallback()`: orchestrates multi-step resilience (GraphQL → verify → REST fallback). Used for critical operations where a fallback strategy exists.
- `_best_effort()`: wraps a single call where failure is acceptable. Used for non-critical "nice-to-have" operations.

Merging them would create a Swiss-army-knife abstraction that violates Constitution V (simplicity). Keeping them separate means each has a clear, single purpose.

**Alternatives considered**:

- Refactoring `_with_fallback()` to use `_best_effort()` internally: rejected — `_with_fallback()` has a different control flow (verify step, fallback function) that does not map onto a simple try/except wrapper.
- Replacing `_with_fallback()` with `_best_effort()`: rejected — would lose the verify step and fallback strategy, which are critical for project-management operations.

---

## Open questions

None. All Technical Context entries resolved with concrete defaults above. No `NEEDS CLARIFICATION` markers remain.
