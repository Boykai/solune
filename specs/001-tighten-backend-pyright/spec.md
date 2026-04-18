# Feature Specification: Tighten Backend Pyright (Standard → Strict, Gradually)

**Feature Branch**: `001-tighten-backend-pyright`  
**Created**: 2026-04-18  
**Status**: Draft  
**Input**: User description: "[speckit.specify] Tighten Backend Pyright (standard → strict, gradually)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Establish a safer baseline without a mega-PR (Priority: P1)

As a backend maintainer, I want the backend type-checking baseline to catch avoidable typing mistakes and redundant suppressions while keeping the rollout small enough to review confidently.

**Why this priority**: This delivers immediate safety value with the lowest rollout risk and creates the foundation for all later strictness increases.

**Independent Test**: Enable the baseline checks, run the existing backend type-check gate, and verify it fails on redundant suppressions or missing parameter typing until the findings are fixed.

**Acceptance Scenarios**:

1. **Given** the backend source contains a redundant type suppression, **When** the baseline checks run, **Then** the quality gate rejects the change until the redundant suppression is removed.
2. **Given** a backend function is introduced with missing or unknown parameter typing, **When** the baseline checks run, **Then** the quality gate reports the issue as blocking feedback.

---

### User Story 2 - Protect the cleanest backend packages with a strict floor (Priority: P2)

As a backend maintainer, I want the cleanest backend packages to operate under a stricter minimum checking level so new code in those areas cannot quietly regress.

**Why this priority**: This contains the stricter rollout to the most ready packages first, keeping reviews focused while preventing backsliding in high-value modules.

**Independent Test**: Apply a canary weak-typing change inside a protected package and verify the existing quality gate rejects it, while the protected package list remains explicitly defined.

**Acceptance Scenarios**:

1. **Given** a change in a protected backend package introduces weak or missing typing, **When** the type-check gate runs, **Then** the change is rejected before merge.
2. **Given** a file inside a protected backend package attempts to declare a file-level downgrade, **When** the quality gate runs, **Then** the downgrade is rejected because the strict floor cannot be bypassed within protected scope.

---

### User Story 3 - Make remaining downgrades visible and auditable (Priority: P3)

As a reviewer or technical lead, I want any remaining backend downgrade to be explicit, documented, and counted so legacy debt stays visible and can be reduced over time.

**Why this priority**: The final global rollout is only sustainable if exceptions are obvious, reviewable, and prevented from spreading into protected areas.

**Independent Test**: Raise the default backend checking level, verify each remaining downgraded file carries the approved file-level downgrade marker, and confirm the debt record and CI reporting stay in sync.

**Acceptance Scenarios**:

1. **Given** a legacy backend file still cannot satisfy the stricter default, **When** it is temporarily downgraded, **Then** the downgrade is declared at file scope and listed in the visible debt record with ownership.
2. **Given** continuous integration runs after the global rollout, **When** the build reports downgrade status, **Then** reviewers can see the current downgrade count and any forbidden downgrade added inside protected scope causes the run to fail.

---

### Edge Cases

- Third-party or generated typing gaps may produce noisy member-level unknowns that should be tracked early without blocking the first rollout phase.
- A suppression that was previously necessary may become redundant after surrounding code changes and must be removed rather than silently preserved.
- A legacy file may require temporary reduced checking after the global rollout, but protected packages must never use that escape hatch.
- When a downgraded legacy file is later cleaned up, its downgrade marker and debt-record entry must be removed together so the reported count stays accurate.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The backend type-checking rollout MUST be delivered in phased, reviewable increments rather than as a single all-or-nothing change.
- **FR-002**: Phase 1 MUST add baseline checks that detect redundant type suppressions and missing or unknown parameter typing across backend source files while keeping the overall backend default checking level unchanged.
- **FR-003**: The separate tests type-check configuration MUST remain outside strict enforcement, except that redundant type suppressions in that configuration MUST still be detectable.
- **FR-004**: Phase 1 MUST be considered complete only when the backend type-check gate reports zero blocking diagnostics after the baseline checks are enabled.
- **FR-005**: Phase 2 MUST enforce a stricter minimum checking level for the backend API, model, and agent-service package trees, and that protected package set MUST be explicitly declared in project configuration.
- **FR-006**: Files inside the protected package set MUST NOT use file-level downgrades, silent exclusions, or equivalent bypasses to avoid the stricter minimum.
- **FR-007**: Phase 2 MUST be considered complete only when newly introduced weak or missing typing inside the protected package set is rejected by the existing quality gate.
- **FR-008**: Phase 3 MUST raise the default backend checking level for backend source files as a whole.
- **FR-009**: Any backend file that still requires reduced checking after Phase 3 MUST declare that downgrade at file scope using the repository’s approved suppression style, and each downgraded file MUST be listed in a visible debt record that includes ownership.
- **FR-010**: The ongoing burn-down phase MUST prevent newly added file-level downgrades inside the protected package set from being merged.
- **FR-011**: The ongoing burn-down phase MUST publish the current count of downgraded backend files on every continuous-integration run.
- **FR-012**: Diagnostics caused primarily by incomplete third-party member typing MUST begin as non-blocking feedback and MUST not become blocking until the documented backlog is ready to be burned down.
- **FR-013**: Existing reviewed type suppressions in backend source files MUST be re-validated during the rollout and removed if they are no longer required.

### Key Entities *(include if feature involves data)*

- **Backend Type-Checking Policy**: The documented rule set that defines the default checking level, the protected strict-floor scope, and which diagnostic categories are blocking versus non-blocking at each phase.
- **Protected Package Set**: The explicit list of backend package trees that must always enforce the stricter minimum checking level.
- **Legacy Downgrade Record**: The visible documentation artifact that lists each temporarily downgraded backend file, its owner, and its reason for remaining below the stricter default.
- **Type-Checking Diagnostic**: A reported typing issue that may block a merge or be tracked as non-blocking feedback depending on the rollout phase and severity.

### Assumptions

- The existing backend type-check and CI workflows remain the authoritative enforcement paths for this feature.
- The rollout will land as multiple small pull requests aligned to phases or protected package trees, not as one mega-change.
- Test files remain exempt from strict checking because heavy mocking would create low-value noise relative to production backend modules.

### Out of Scope

- Expanding this rollout to frontend or non-backend code.
- Eliminating all legacy downgrades in the same feature; ongoing reduction happens after the global rollout is in place.
- Replacing the current type-checking toolchain or introducing a separate enforcement product.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The baseline phase reaches zero blocking backend type-check diagnostics after the new baseline checks are enabled.
- **SC-002**: After the strict-floor phase, any canary change that introduces weak or missing typing inside the protected backend package set is rejected before merge.
- **SC-003**: After the global phase, 100% of backend source files run under the stricter default unless they carry an explicit file-level downgrade that is also recorded in the visible debt record.
- **SC-004**: Every continuous-integration run reports the current count of downgraded backend files, and 100% of attempts to add a downgrade inside the protected package set fail automatically.
