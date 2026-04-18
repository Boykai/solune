# Specification Analysis Report

**Feature**: 002-reduce-broad-except
**Date**: 2026-04-18
**Artifacts Analysed**: spec.md, plan.md, tasks.md, constitution.md, contracts/ (3 contracts), data-model.md

---

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F1 | Inconsistency | HIGH | spec.md:FR-007, contracts/best-effort-helper-contract.md:B2–B3 | FR-007 says helper "MUST only catch expected failure types (network errors, HTTP errors)" but contract B2–B3 catches `except Exception` (all Exception subclasses). The parenthetical "(network errors, HTTP errors)" implies narrow catching; the contract implements broad catching. | Amend FR-007 to say "MUST only catch `Exception` subclasses (not `BaseException`)" to match the contract, or narrow the contract to specific httpx types if the spec intent is strict. |
| F2 | Inconsistency | HIGH | plan.md:L68, contracts/best-effort-helper-contract.md:B1 L4, data-model.md:E4 | Plan, contract, and data-model all state `_best_effort()` belongs on `_ServiceMixin` in `service.py`. In reality, `_ServiceMixin` is a TYPE_CHECKING-only stub in `_mixin_base.py` (L20). The implementation of `_with_fallback()` lives on `GitHubProjectsService` in `service.py` (L223). The same two-file pattern must be followed for `_best_effort()`. | Update plan/contracts to specify: (1) runtime implementation on `GitHubProjectsService` in `service.py`, (2) type stub on `_ServiceMixin` in `_mixin_base.py`. Add `_mixin_base.py` to the project structure listing. |
| F3 | Underspecification | HIGH | plan.md:L68, tasks.md:T029 | Neither plan nor tasks mention `_mixin_base.py`, yet adding `_best_effort()` requires a type stub there so mixin files (copilot.py, issues.py, etc.) can call `self._best_effort()` without pyright errors. No task covers this file edit. | Add a task (e.g., T029b) to add the `_best_effort` method stub to `_ServiceMixin` in `_mixin_base.py`, following the existing `_with_fallback` stub pattern at line 63. |
| F4 | Inconsistency | MEDIUM | spec.md:L14, plan.md:L20 | Spec says "~570 occurrences across ~76 files"; plan says "~568 across ~87 files". Actual count is 568 handlers across 87 files. Spec's file count (~76) is inaccurate; plan's figures are correct. | Update spec.md to use "~568 across ~87 files" consistently, matching the verified baseline. |
| F5 | Ambiguity | MEDIUM | spec.md:FR-007 | FR-007's "MUST NOT silently swallow unexpected exceptions" is ambiguous. Does "unexpected" mean non-network/HTTP exceptions (interpretation A → narrow catch), or BaseException subclasses like KeyboardInterrupt (interpretation B → broad catch with Exception)? The contract follows interpretation B, but the spec wording supports interpretation A. | Rewrite FR-007 to explicitly state: "MUST catch `Exception` subclasses only. `BaseException` subclasses (`KeyboardInterrupt`, `SystemExit`) MUST propagate uncaught." |
| F6 | Underspecification | MEDIUM | spec.md:FR-008 | FR-008 says "pull-request and project service layers" but plan and tasks also target `copilot.py` (14 handlers) and `issues.py` (15 handlers). These two files are not "pull-request" or "project" layers — they are separate service mixins. | Amend FR-008 to say "in the GitHub-projects service layer" (or explicitly list all four files) to match the plan's scope. |
| F7 | Terminology | MEDIUM | spec.md (throughout), plan.md, tasks.md, contracts/ | Spec consistently calls it "domain-error helper"; plan, tasks, and contracts consistently call it `_best_effort()`. These are the same entity. A developer reading the spec and then the tasks might not immediately connect them. | Add a parenthetical to FR-006 on first use: "a shared helper (`_best_effort()`) for the 'best-effort HTTP call' pattern". |
| F8 | Coverage Gap | MEDIUM | spec.md:L79 (Edge Case EC2) | Edge case "justification becomes outdated" has no associated task or verification mechanism. No periodic review cadence or tooling is specified. | Add a LOW-priority recommendation in the tag convention documentation (T025) noting that tagged handlers should be reviewed periodically (e.g., during dependency upgrades). No new task needed — fold into T025 scope. |
| F9 | Underspecification | LOW | tasks.md:T018–T020 | Catch-all triage tasks ("remaining files") don't enumerate specific files or handler counts. An implementer cannot verify completeness without running `grep` first. | Add a clarifying note that T018–T020 are discovered dynamically via `grep -rl "except Exception"` minus already-covered files. Current wording is acceptable but could benefit from the explicit discovery command. |
| F10 | Inconsistency | LOW | plan.md:L64, data-model.md:E1 | Plan says "pyproject.toml at line 85"; data-model says "starting at pyproject.toml:85". The `[tool.ruff.lint]` header is at line 85, but `select` starts at line 86. Both references are functionally correct but could confuse a line-level search. | No action needed — the block reference is sufficient. |
| F11 | Inconsistency | LOW | spec.md (Assumptions), tasks.md (Implementation Strategy) | Spec assumption says handlers "will be triaged across multiple pull requests." Tasks list all triage as separate tasks within a single tasks.md but the Implementation Strategy section (tasks.md L255–258) correctly decomposes into ~8–12 PRs. Minor tension between task-level granularity and PR-level delivery. | No action needed — the Implementation Strategy section resolves the tension. Task-level and PR-level are different decomposition axes. |

---

## Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001 (lint-flags-unjustified-broad-except) | ✅ | T003, T004 | |
| FR-002 (lint-rule-runs-in-ci) | ✅ | T003 | CI picks up pyproject.toml automatically |
| FR-003 (every-handler-triaged) | ✅ | T007–T020, T021 | |
| FR-004 (tagged-handlers-have-justification) | ✅ | T013–T017, T026 | |
| FR-005 (convention-documented) | ✅ | T025, T027 | |
| FR-006 (shared-best-effort-helper) | ✅ | T029 | Missing `_mixin_base.py` stub task (see F3) |
| FR-007 (helper-catch-scope) | ⚠️ | T029, T028 | Ambiguous requirement wording (see F1, F5) |
| FR-008 (ad-hoc-wrappers-replaced) | ⚠️ | T032–T035, T036 | Scope underspecified — omits copilot.py/issues.py (see F6) |
| FR-009 (logging-behaviour-preserved) | ✅ | T032–T035, T028 | |
| FR-010 (workstreams-independent) | ✅ | T042 | Phase structure enforces independence |
| FR-011 (test-suite-passes) | ✅ | T024, T038, T040 | |
| SC-001 (zero-unresolved-violations) | ✅ | T021 | |
| SC-002 (ci-blocks-new-violations) | ✅ | T003, T005 | |
| SC-003 (tagged-below-15-percent) | ✅ | T022 | |
| SC-004 (80%-duplication-reduction) | ✅ | T036 | |
| SC-005 (convention-discoverable) | ✅ | T025, T027 | |
| SC-006 (no-behaviour-changes) | ✅ | T024, T038, T040 | |

---

## Constitution Alignment Issues

No CRITICAL constitution violations detected.

| Principle | Status | Notes |
|---|---|---|
| I. Specification-First Development | ✅ PASS | Prioritised user stories (P1–P4), GWT acceptance scenarios, independent test sections, edge cases, bounded scope. |
| II. Template-Driven Workflow | ✅ PASS | All artifacts follow `.specify/templates/`. No ad-hoc sections. |
| III. Agent-Orchestrated Execution | ✅ PASS | Clear phase handoffs: specify → plan → tasks → (analyze) → implement. |
| IV. Test Optionality with Clarity | ✅ PASS | Tests requested for Workstream B only (novel code). Workstream A validated by linter exit status. Explicitly justified. |
| V. Simplicity and DRY | ✅ PASS | BLE001 is an existing Ruff rule — no new tool. `_best_effort()` is intentionally narrow (github_projects only). Complexity Tracking is empty (no violations to justify). |
| Phase-Based Execution | ✅ PASS | Tasks follow strict Phases 1–7. Phase dependencies documented. |
| Independent User Stories | ✅ PASS | Each story deliverable alone; shared infrastructure in Phase 1–2. |

---

## Unmapped Tasks

All tasks (T001–T042) are mapped to at least one requirement, success criterion, or user story acceptance scenario in the Coverage Matrix (tasks.md L284–306).

No orphan tasks detected.

---

## Metrics

| Metric | Value |
|--------|-------|
| Total Functional Requirements | 11 (FR-001 through FR-011) |
| Total Success Criteria | 6 (SC-001 through SC-006) |
| Total User Stories | 4 (US1–US4) |
| Total Tasks | 42 (T001–T042) |
| Coverage % (requirements with ≥1 task) | 100% (11/11) |
| Coverage % (success criteria with ≥1 task) | 100% (6/6) |
| Ambiguity Count | 2 (F1/F5 — FR-007 wording; F7 — terminology drift) |
| Duplication Count | 0 |
| Critical Issues Count | 0 |
| HIGH Issues Count | 3 (F1, F2, F3) |
| MEDIUM Issues Count | 5 (F4, F5, F6, F7, F8) |
| LOW Issues Count | 3 (F9, F10, F11) |
| Verified Baseline — `except Exception` handlers | 568 (matches plan/tasks; spec says ~570) |
| Verified Baseline — files with handlers | 87 (matches plan/tasks; spec says ~76) |

---

## Next Actions

### HIGH findings — resolve before `/speckit.implement`

1. **F1 + F5 (FR-007 ambiguity)**: Run `/speckit.specify` with refinement to reword FR-007. The contract's `except Exception` approach is pragmatically correct (best-effort means catching all recoverable errors). Align the spec to the contract, not the other way around. Suggested wording: *"The domain-error helper MUST catch `Exception` subclasses only. `BaseException` subclasses (`KeyboardInterrupt`, `SystemExit`) MUST propagate uncaught. The helper MUST NOT silently discard failures — every caught exception MUST be logged."*

2. **F2 + F3 (`_mixin_base.py` gap)**: Run `/speckit.plan` to add `_mixin_base.py` to the project structure and update the contract owner field. Then run `/speckit.tasks` to add a task for adding the `_best_effort` type stub to `_ServiceMixin` in `_mixin_base.py`. Alternatively, manually edit `tasks.md` to insert a task between T029 and T030: *"T029b [US4] Add `_best_effort` method stub to `_ServiceMixin` in `solune/backend/src/services/github_projects/_mixin_base.py` (following the existing `_with_fallback` stub pattern at line 63). Run `uv run pyright src/services/github_projects/_mixin_base.py`; MUST exit 0."*

### MEDIUM findings — recommended but not blocking

1. **F4 (handler count)**: Update spec.md references from "~570 across ~76 files" to "~568 across ~87 files" for consistency.

2. **F6 (FR-008 scope)**: Amend FR-008 wording to "in the GitHub-projects service layer" to cover all four target files.

3. **F7 (terminology)**: Add a parenthetical `(_best_effort())` on first mention of "domain-error helper" in FR-006.

4. **F8 (outdated justification edge case)**: Fold a "periodic review" note into T025's README documentation scope.

### LOW findings — no action needed

F9, F10, F11 are cosmetic or self-resolving. No changes required.

---

## Remediation Offer

Would you like me to suggest concrete remediation edits for the top 3 HIGH issues (F1, F2, F3)? These would be specific text changes to spec.md, plan.md, contracts/best-effort-helper-contract.md, and tasks.md. I will NOT apply them automatically — you must explicitly approve before any edits are made.
