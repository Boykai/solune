# Feature Specification: Reduce Broad-Except + Log + Continue Pattern

**Feature Branch**: `002-reduce-broad-except`
**Created**: 2026-04-18
**Status**: Draft
**Input**: User description: "Reduce Broad-Except + Log + Continue Pattern"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Enable Lint Rule for Broad Exception Handlers (Priority: P1)

A developer opens the project, runs the linter, and receives clear violations for every overly-broad `except Exception` handler that has not been explicitly justified. This gives the team immediate, automated visibility into which error handlers are intentionally broad versus accidentally silencing failures.

**Why this priority**: This is the foundation for both workstreams. Without an enforced lint rule, broad-except handlers will continue to accumulate unchecked. Enabling the rule surfaces the full scope of the problem (~570 occurrences across ~76 files today) and prevents new violations from landing in the codebase.

**Independent Test**: Can be fully tested by running the linter on the current codebase and confirming it reports all unjustified broad-except handlers. Delivers value by establishing the guardrail that prevents regression.

**Acceptance Scenarios**:

1. **Given** the lint configuration has the broad-exception rule enabled, **When** a developer runs the linter on the backend, **Then** every `except Exception` handler without a justification tag is reported as a violation.
2. **Given** the lint configuration has the broad-exception rule enabled, **When** a developer adds a new `except Exception` handler without a justification tag, **Then** the linter blocks the change (or reports a violation in CI).
3. **Given** the lint configuration has the broad-exception rule enabled, **When** a developer adds a new `except Exception` handler with the approved justification tag, **Then** the linter accepts it without reporting a violation.

---

### User Story 2 — Triage and Narrow Existing Broad Handlers (Priority: P2)

A developer reviews each existing broad-except handler and assigns it to one of three resolution buckets: **Narrow** (replace with a specific exception type), **Promote** (remove the handler entirely so the caller handles the error), or **Tagged** (keep the broad handler with an explicit justification). After triage, every handler in the codebase is intentional, documented, and auditable.

**Why this priority**: The lint rule (P1) surfaces the violations; this story resolves them. Until triage is complete the codebase cannot pass lint cleanly. This story is intentionally decoupled from the lint enablement so the rule can ship first (fail-open or per-file suppressed) without waiting for every handler to be resolved.

**Independent Test**: Can be tested by running the linter after triage and confirming zero unresolved violations remain. Each handler resolution can be verified individually through code review.

**Acceptance Scenarios**:

1. **Given** a broad-except handler that wraps a known operation (e.g., a database call or a JSON parse), **When** a developer triages it as "Narrow," **Then** the handler is replaced with the specific exception type(s) for that operation and the lint rule passes.
2. **Given** a broad-except handler where the caller already has error-handling logic, **When** a developer triages it as "Promote," **Then** the handler is removed entirely and the error propagates to the caller.
3. **Given** a broad-except handler that wraps genuinely unbounded calls (e.g., third-party callbacks, task-group drains), **When** a developer triages it as "Tagged," **Then** the handler retains `except Exception` with the approved justification tag and the lint rule passes.
4. **Given** all existing handlers have been triaged, **When** the linter runs on the full backend codebase, **Then** zero broad-except violations are reported.

---

### User Story 3 — Adopt a Justification Tag Convention (Priority: P3)

A developer who genuinely needs a broad-except handler follows a documented convention to tag it with a reason. The tag is machine-readable (the linter recognises it as a suppression) and human-readable (a reviewer can understand why the broad handler exists). This mirrors the existing inline-suppression convention already used elsewhere in the codebase.

**Why this priority**: Without a clear convention, developers will suppress the lint rule inconsistently (or not at all). This story establishes the standard and ensures long-term maintainability. It is lower priority because the convention can be communicated informally while P1 and P2 are in progress.

**Independent Test**: Can be tested by searching the codebase for all justification tags and confirming each one follows the documented format. A reviewer can verify any single tagged handler in isolation.

**Acceptance Scenarios**:

1. **Given** a developer needs to keep a broad-except handler, **When** they add the justification tag following the documented convention, **Then** the linter accepts the handler and the tag includes a human-readable reason.
2. **Given** a developer adds a justification tag with an empty or missing reason, **When** the linter runs, **Then** the suppression still applies (the linter does not parse the reason text), but code review policy requires a meaningful reason.
3. **Given** the project documentation, **When** a new contributor looks up how to handle a necessary broad-except, **Then** they find clear instructions on the tag format, when it is appropriate, and examples of valid reasons.

---

### User Story 4 — Introduce a Domain-Error Helper for Best-Effort HTTP Calls (Priority: P4)

A developer working on code that calls external services (particularly GitHub APIs) uses a shared helper instead of writing ad-hoc try/except blocks for "best-effort" HTTP calls. The helper encapsulates the pattern of "attempt the call, log any failure, return a safe fallback" — reducing the roughly 50+ repetitive wrappers concentrated in the pull-request and project service layers.

**Why this priority**: This is the refactor workstream and is intentionally independent of the lint-policy workstream. It delivers value by reducing code duplication and making the best-effort pattern consistent, but it is lower priority because the lint rule (P1–P3) can ship independently without waiting for the refactor.

**Independent Test**: Can be tested by verifying that callers using the helper produce the same observable behaviour (logging, fallback values) as the original ad-hoc handlers, and that new best-effort calls use the helper instead of raw try/except.

**Acceptance Scenarios**:

1. **Given** a service function that makes a best-effort HTTP call with an ad-hoc try/except, **When** a developer replaces it with the domain-error helper, **Then** the function produces identical logging output and returns the same fallback value on failure.
2. **Given** the domain-error helper is available, **When** a developer writes a new best-effort HTTP call, **Then** they use the helper instead of writing a raw try/except and the code review process enforces this.
3. **Given** the domain-error helper handles a network failure, **When** the call fails, **Then** the failure is logged at the appropriate severity level and the helper returns the configured fallback value without raising an exception.
4. **Given** the domain-error helper handles an unexpected non-network error, **When** the call fails with a non-HTTP exception, **Then** the error propagates to the caller (is not silently swallowed).

---

### Edge Cases

- What happens when a broad-except handler catches `KeyboardInterrupt` or `SystemExit`? These should never be silently swallowed; the lint rule should surface them, and triage should narrow or promote them.
- What happens when a tagged handler's justification becomes outdated (e.g., a third-party library adds typed exceptions)? Periodic review of tagged handlers should be part of maintenance.
- What happens when the domain-error helper is used for a call that should NOT be best-effort (i.e., the caller needs to know about the failure)? The helper must only be used where silent fallback is the correct behaviour; misuse should be caught in code review.
- What happens when multiple exception types need to be caught in a single handler? The "Narrow" triage bucket should produce union exception types (e.g., catching both database and OS errors) rather than falling back to a broad handler.
- What happens when a file has dozens of handlers to triage? Large files (e.g., pipeline.py with ~47 occurrences, chat.py with ~41) should be triaged incrementally to keep pull requests reviewable.

## Requirements *(mandatory)*

### Functional Requirements

#### Workstream A — Lint Policy

- **FR-001**: The lint configuration MUST include a rule that flags every `except Exception` handler that lacks an approved justification tag.
- **FR-002**: The lint rule MUST run as part of the existing CI pipeline so that new unjustified broad-except handlers fail the build.
- **FR-003**: Every existing broad-except handler in the backend codebase MUST be triaged into exactly one of three buckets: **Narrow** (replaced with specific exception types), **Promote** (removed so error propagates), or **Tagged** (retained with justification).
- **FR-004**: Each tagged (retained) broad-except handler MUST include an inline justification tag that follows the project's existing suppression convention — specifically: an inline comment with the rule code, an em-dash separator, `reason:`, and a human-readable explanation.
- **FR-005**: The project MUST document the justification tag convention (format, when to use it, examples) so that contributors know how to handle legitimate broad-except cases.

#### Workstream B — Domain-Error Helper

- **FR-006**: The project MUST provide a shared helper for the "best-effort HTTP call" pattern that encapsulates: attempting the call, logging failures at a configurable severity, and returning a caller-specified fallback value.
- **FR-007**: The domain-error helper MUST only catch expected failure types (network errors, HTTP errors) and MUST NOT silently swallow unexpected exceptions.
- **FR-008**: Existing ad-hoc best-effort HTTP wrappers in the pull-request and project service layers MUST be replaced with the shared helper.
- **FR-009**: The domain-error helper MUST preserve the existing logging behaviour (severity level, message format) of the ad-hoc wrappers it replaces.

#### Cross-Cutting

- **FR-010**: Workstream A (lint policy) and Workstream B (domain-error helper) MUST be deliverable independently — neither workstream's completion should be gated on the other.
- **FR-011**: All changes MUST pass the existing test suite without regressions.

## Assumptions

- The existing CI pipeline already runs the linter on every pull request; enabling the new rule will automatically integrate without additional CI configuration.
- The ~570 existing broad-except handlers will be triaged across multiple pull requests to keep changes reviewable, not in a single monolithic change.
- The majority of broad-except handlers in `main.py` (e.g., around database and file-system operations) will collapse to specific exception types (database errors, OS errors), reducing the tagged-handler count significantly.
- The existing inline-suppression convention (rule code + em-dash + `reason:`) already in use elsewhere in the codebase is the standard to follow for justification tags.
- The domain-error helper targets HTTP/network call wrappers specifically and is not intended as a general-purpose exception-handling utility.
- "Best-effort" means the caller explicitly accepts that the call may fail and has defined a fallback; the helper is not appropriate for calls where failure must be surfaced to the user.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of backend broad-except handlers are either narrowed to specific types, promoted (removed), or tagged with a documented justification — zero unresolved lint violations remain.
- **SC-002**: The lint rule runs on every pull request and blocks merging of new unjustified broad-except handlers, preventing regression from the first day of enablement.
- **SC-003**: The number of broad-except handlers retained with justification tags is reduced to fewer than 15% of the original count (~570), meaning at least 85% are narrowed or promoted.
- **SC-004**: All ad-hoc best-effort HTTP wrappers in the pull-request and project service layers (estimated 50+ occurrences) are consolidated into calls to the shared domain-error helper, reducing duplicated error-handling code by at least 80% in those files.
- **SC-005**: Developer onboarding friction related to exception handling is eliminated — a new contributor can find the justification tag convention and the domain-error helper documented within 2 minutes.
- **SC-006**: No production behaviour changes — all narrowed, promoted, and refactored handlers produce the same observable behaviour (logging output, fallback values, error propagation) as the original handlers.
