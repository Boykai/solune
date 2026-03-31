# Research: Bug Basher — Full Codebase Review & Fix

**Feature**: 002-bug-basher
**Date**: 2026-03-31
**Status**: Complete

## Research Tasks

### RT-001: Bug Category Prioritization and Review Order

**Context**: The spec defines five bug categories with explicit priority order. Need to confirm whether a single-pass or multi-pass review strategy is more effective for a ~62,800 LOC codebase.

**Decision**: Use a single-pass review organized by module (not by category). Each module is reviewed for all five categories in one pass. Findings are tagged with their category and sorted by priority in the final summary.

**Rationale**: A single-pass-per-module approach is more efficient for AI-assisted review because context switching between files is more expensive than context switching between bug categories within the same file. The reviewer already has the file's logic model loaded when checking for security, runtime, and logic issues simultaneously.

**Alternatives considered**:
- **Five separate passes (one per category)**: Five full-codebase scans would be prohibitively slow and redundant — the reviewer reads the same code five times.
- **Category-first with file dedup**: Reduces redundancy but requires maintaining a "visited files" registry that adds process overhead without value.
- **Random/unstructured review**: No prioritization means critical security issues might be found late; the priority order ensures the most dangerous bugs are addressed first within each module.

---

### RT-002: Backend Linting and Static Analysis Tooling

**Context**: The spec requires all existing linting/formatting checks to pass after fixes (FR-007). Need to confirm which tools are configured and how to run them.

**Decision**: Use the existing CI-verified toolchain for backend validation:
1. `ruff check src tests` — Linting (includes security rules, UP046/UP047 PEP 695 enforcement)
2. `ruff format --check src tests` — Formatting
3. `uv run pyright src` — Type checking (standard mode)
4. `pytest tests/unit/` — Unit test suite

All commands run from `solune/backend/` with the project's virtual environment.

**Rationale**: These are the exact commands run in CI (`.github/workflows/ci.yml` lines 35–54). Using the same toolchain ensures no drift between local validation and CI gates.

**Alternatives considered**:
- **bandit for security linting**: Configured in `pyproject.toml` but not in CI critical path; run it as supplementary check for security-category findings.
- **mutmut for mutation testing**: Configured but heavyweight; not needed for bug bash validation — standard pytest coverage is sufficient.
- **mypy instead of pyright**: Project uses pyright in standard mode; mypy would produce different results and is not configured.

---

### RT-003: Frontend Linting and Testing Tooling

**Context**: Need to confirm frontend validation toolchain for FR-007 compliance.

**Decision**: Use the existing frontend toolchain:
1. `npm run lint` — ESLint (configured in `eslint.config.js`)
2. `npx prettier --check src/` — Formatting
3. `npm run test` — Vitest unit tests
4. `npm run test:e2e` — Playwright E2E tests (optional, for smoke testing)

All commands run from `solune/frontend/`.

**Rationale**: Matches the CI pipeline configuration. ESLint + Prettier cover TypeScript-specific issues and formatting consistency.

**Alternatives considered**:
- **Stryker mutation testing**: Configured but not in CI critical path; skip for bug bash efficiency.
- **tsc --noEmit**: Type checking via TypeScript compiler; overlaps with ESLint type-aware rules but can catch additional issues. Use as supplementary check.

---

### RT-004: Regression Test Strategy

**Context**: FR-003 mandates "at least one new regression test per bug fix." Need to determine where tests should be placed and what patterns to follow.

**Decision**: Place regression tests in the existing test directories following established patterns:
- **Backend bugs**: Add tests to `solune/backend/tests/unit/` using pytest + pytest-asyncio. Follow existing naming convention: `test_<module_name>.py` with `test_<description>` functions.
- **Frontend bugs**: Add tests alongside components using Vitest. Follow existing pattern: `*.test.tsx` / `*.test.ts` files co-located with source.
- Each regression test should: (a) reproduce the precondition that triggered the bug, (b) verify the fix produces correct behavior, (c) include a docstring explaining which bug it guards against.

**Rationale**: Using existing test infrastructure and patterns ensures consistency and avoids introducing new test organization. Co-locating frontend tests with components matches the established pattern.

**Alternatives considered**:
- **Separate `tests/regression/` directory**: Adds a new organizational pattern; rejected per "preserve existing code style" constraint (FR-012).
- **Property-based tests via hypothesis**: More thorough but higher development cost per test; use only when the bug involves boundary conditions well-suited to property testing.
- **Integration tests for all fixes**: Too heavyweight; unit tests are sufficient for most bug fixes and run faster.

---

### RT-005: High-Risk Module Identification

**Context**: With 170+ backend modules, prioritization within the single-pass is important. Need to identify which modules are highest-risk based on size, complexity, and criticality.

**Decision**: Prioritize review order by risk tier:

**Tier 1 — Critical (review first)**:
- `src/config.py` — Security-critical settings validation, encryption keys
- `src/api/auth.py` — OAuth flow, session management
- `src/api/webhooks.py` — Webhook signature verification, external input handling
- `src/services/encryption.py` — Encryption key management, data protection
- `src/dependencies.py` — Dependency injection, startup validation
- `src/main.py` — FastAPI app setup, CORS, middleware (736 LOC)

**Tier 2 — High (large/complex modules)**:
- `src/services/copilot_polling/pipeline.py` — 3,403 LOC, complex state machine
- `src/services/workflow_orchestrator/orchestrator.py` — 2,747 LOC, workflow engine
- `src/api/chat.py` — 2,335 LOC, real-time communication
- `src/services/agents/service.py` — 1,795 LOC, agent lifecycle
- `src/services/copilot_polling/completion.py` — 1,601 LOC, AI provider
- `src/services/copilot_polling/helpers.py` — 1,434 LOC, polling utilities
- `src/services/cleanup_service.py` — 1,191 LOC, pipeline cleanup
- `src/services/copilot_polling/recovery.py` — 1,187 LOC, failure recovery
- `src/services/agent_creator.py` — 1,187 LOC, agent instantiation

**Tier 3 — Standard (remaining modules)**:
- All other `src/` modules in alphabetical order within their directories

**Rationale**: Security-critical modules are reviewed first regardless of size. Large modules have higher bug density due to complexity. The tiered approach ensures the most impactful areas get the most attention.

**Alternatives considered**:
- **Alphabetical order**: Simple but ignores risk; a trivial utility module gets the same priority as the auth layer.
- **LOC-descending order**: Correlates with complexity but misses small-but-critical modules like `encryption.py` (only 4,889 bytes but security-critical).
- **Git blame (most recently changed)**: Good for finding regressions but misses long-standing bugs in stable code.

---

### RT-006: Handling Ambiguous Findings

**Context**: FR-005 requires flagging ambiguous issues with `# TODO(bug-bash):` comments rather than fixing them. Need to define clear criteria for what constitutes "ambiguous."

**Decision**: A finding is ambiguous and should be flagged (not fixed) when ANY of the following apply:
1. The fix would change the public API surface or module interface
2. The fix involves a trade-off between two valid approaches with different performance/correctness characteristics
3. The intended behavior is unclear from context (no spec, no comments, multiple valid interpretations)
4. The fix would require changing more than ~20 lines or touching more than 2 files (exceeds "minimal and focused" per FR-013)
5. The fix could have cascading effects on downstream behavior that cannot be fully validated with unit tests

**Rationale**: These criteria operationalize the spec's "ambiguous or trade-off situations" into concrete, measurable conditions. The 20-line and 2-file heuristics prevent scope creep while allowing meaningful fixes.

**Alternatives considered**:
- **Fix everything possible**: Risks introducing new bugs in complex changes; violates the conservative spirit of FR-013.
- **Flag everything uncertain**: Too conservative; would result in mostly-TODO output with few actual fixes.
- **Reviewer discretion only**: Subjective and inconsistent; concrete criteria enable reproducible decisions.

---

### RT-007: Summary Report Format and Tooling

**Context**: FR-009 requires a summary table with specific columns. Need to determine how to generate and maintain this report during the review.

**Decision**: Generate the summary report as a markdown table appended to each commit message and consolidated into a final report at review completion. Format per spec:

```markdown
| # | File | Line(s) | Category | Description | Status |
|---|------|---------|----------|-------------|--------|
| 1 | `path/to/file.py` | 42-45 | Security | Description of bug | ✅ Fixed |
| 2 | `path/to/file.py` | 100 | Logic | Description of ambiguity | ⚠️ Flagged (TODO) |
```

The report is maintained incrementally: each task (in `/speckit.tasks`) produces its findings, and the final task consolidates all findings into the summary.

**Rationale**: Incremental generation prevents loss of findings. The markdown table format matches the spec exactly (FR-009). Consolidation at the end ensures completeness (SC-006).

**Alternatives considered**:
- **JSON findings file**: Machine-parseable but less readable for human review; the spec explicitly requires a table format.
- **Per-file reports**: Granular but hard to get a holistic view; a single consolidated table is more useful for decision-making.
- **GitHub issue comments**: Ephemeral and hard to version; a file in the specs directory is version-controlled and auditable.

---

### RT-008: Known Security Posture Baseline

**Context**: A previous security review (specs/002-security-review) already remediated 21 OWASP findings. Need to understand the current baseline to avoid duplicate work.

**Decision**: Acknowledge the existing security posture as a baseline. The bug bash focuses on:
1. Verifying that previously remediated findings are still intact (regression check)
2. Identifying NEW security issues not covered by the OWASP audit (e.g., business logic vulnerabilities, race conditions in auth, information leakage)
3. Checking for security regressions introduced after the audit (new code added since the audit)

**Rationale**: The OWASP audit was comprehensive but focused on the OWASP Top 10 categories. A bug bash casts a wider net, including implementation-specific vulnerabilities that may not map to OWASP categories (e.g., MagicMock leaking into production paths, type confusion in Pydantic models).

**Alternatives considered**:
- **Skip security category entirely**: The previous audit was thorough, but new code has been added since then. Skipping would miss regressions.
- **Full re-audit**: Redundant with the previous effort; focus on delta and new patterns instead.
- **Automated SAST only (bandit, semgrep)**: Good supplementary tool but cannot catch logic-level security issues; manual review is still needed.
