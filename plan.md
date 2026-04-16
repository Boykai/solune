# Implementation Plan: Remove Lint/Test Ignores & Fix Discovered Bugs

**Branch**: `003-remove-lint-ignores` | **Date**: 2026-04-16 | **Spec**: `/specs/003-remove-lint-ignores/spec.md`
**Input**: Feature specification from `/specs/003-remove-lint-ignores/spec.md`

## Summary

Systematically remove lint, type-check, test-skip, coverage, and mutation ignores across the Solune repository. Research identified 50 backend suppressions, 20 frontend inline suppressions, 4 frontend config-level suppressions, 6 E2E dynamic test skips, and 3 infrastructure Bicep suppressions. The plan removes all non-essential suppressions, fixes bugs surfaced by removal, and adds a CI guard to prevent future unjustified suppressions. Approximately 80% of current suppressions can be removed; the remaining ~20% are architecturally required (FastAPI dependency injection, frozen dataclass test patterns, Bicep cross-module secret passing) and will be retained with documented `reason:` justifications.

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript 6.x / React 19.x (frontend), Bicep (infra)
**Primary Dependencies**: FastAPI, Ruff, Pyright, Bandit, pytest (backend); ESLint, Vitest, Stryker, Playwright (frontend); Azure Bicep CLI (infra)
**Storage**: N/A — no schema or data changes
**Testing**: `uv run pytest` (backend), `npm run test` / `npm run lint` (frontend), `npx playwright test` (E2E), `az bicep build` (infra)
**Target Platform**: Solune web application (monorepo: `solune/backend`, `solune/frontend`, `infra/`)
**Project Type**: Web application (frontend + backend monorepo + infrastructure)
**Performance Goals**: No performance changes — all checks must pass at equal or stricter settings versus baseline
**Constraints**: No new suppressions without `reason:` justification; retain only architecturally required suppressions
**Scale/Scope**: ~70 inline suppressions + ~8 config-level suppressions across ~40 files; 6 implementation phases

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Gate | Pre-Research | Post-Design |
|---|---|---|
| I. Specification-First Development | PASS — plan is derived directly from the approved `spec.md` with 6 prioritized user stories, Given-When-Then acceptance scenarios, and clear scope boundaries. | PASS — all plan phases map to FR-001 through FR-035 and the 6 user stories. Research resolved all unknowns. |
| II. Template-Driven Workflow | PASS — `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, and `contracts/` follow Speckit artifact expectations. | PASS — all required Phase 0/1 artifacts are generated in `specs/003-remove-lint-ignores/`. |
| III. Agent-Orchestrated Execution | PASS — this plan defines a clean handoff from planning to task generation and implementation across 6 phases with explicit dependencies. | PASS — research/design outputs provide explicit inputs for `/speckit.tasks` and `/speckit.implement`. |
| IV. Test Optionality with Clarity | PASS — tests are required: the specification explicitly mandates running all existing test suites at stricter settings and adding tests for discovered bugs. | PASS — verification steps are scoped to existing CI commands with tightened configuration. |
| V. Simplicity and DRY | PASS — the approach is direct removal/fixing of suppressions with no new abstractions. The CI guard is a single shell script, not a framework. | PASS — no unjustified complexity introduced. The only new artifact is the suppression guard script. |

**Gate Result**: PASS — no constitution violations identified; `Complexity Tracking` remains empty.

## Project Structure

### Documentation (this feature)

```text
specs/003-remove-lint-ignores/
├── plan.md                                  # This file
├── research.md                              # Phase 0: suppression audit & best practices
├── data-model.md                            # Phase 1: suppression entity model
├── quickstart.md                            # Phase 1: verification commands
├── contracts/
│   └── suppression-guard.openapi.yaml       # Phase 1: CI guard behavior contract
└── tasks.md                                 # Created later by /speckit.tasks
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── pyproject.toml                  # Config: Ruff, Bandit, Pyright, coverage
│   ├── pyrightconfig.tests.json        # Config: test type checking
│   ├── src/
│   │   ├── api/
│   │   │   ├── chat.py                 # noqa: B008, PTH118, PTH119
│   │   │   ├── activity.py             # noqa: B008
│   │   │   └── cleanup.py              # noqa: B008
│   │   ├── models/
│   │   │   └── chat.py                 # noqa: F401 (re-exports)
│   │   └── services/
│   │       ├── agent_provider.py       # type: ignore
│   │       ├── plan_agent_provider.py  # type: ignore
│   │       ├── copilot_polling/
│   │       │   └── __init__.py         # noqa: F401 (re-exports)
│   │       └── github_projects/
│   │           └── __init__.py         # noqa: E402
│   └── tests/
│       └── unit/
│           ├── test_mcp_server/
│           │   └── test_context.py     # type: ignore (frozen dataclass tests)
│           ├── test_run_mutmut_shard.py # pytest.mark.skipif, noqa: B009
│           ├── test_main.py            # pragma: no cover
│           ├── test_database.py        # pragma: no cover
│           ├── test_chat_agent.py      # pragma: no cover
│           ├── test_build_smoke.py     # noqa: F401
│           ├── test_polling_loop.py    # noqa: B010
│           ├── test_label_classifier.py       # noqa: B010
│           ├── test_transcript_detector.py    # noqa: B010
│           ├── test_agent_output.py           # noqa: B010
│           └── test_recommendation_models.py  # noqa: RUF001
├── frontend/
│   ├── eslint.config.js                # ESLint rule configuration
│   ├── stryker.config.mjs             # ignoreStatic: true
│   ├── tsconfig.test.json             # noUnusedLocals/Parameters: false
│   ├── e2e/
│   │   ├── fixtures.ts                # eslint-disable rules-of-hooks
│   │   ├── integration.spec.ts        # test.skip() ×2
│   │   └── project-load-performance.spec.ts  # test.skip() ×4
│   ├── playwright.config.ts           # testIgnore, forbidOnly
│   └── src/
│       ├── components/
│       │   ├── agents/
│       │   │   ├── AgentChatFlow.tsx          # exhaustive-deps
│       │   │   ├── AgentIconPickerModal.tsx   # jsx-a11y
│       │   │   └── AddAgentModal.tsx          # jsx-a11y ×3
│       │   ├── board/
│       │   │   ├── AddAgentPopover.tsx        # jsx-a11y
│       │   │   └── AgentPresetSelector.tsx    # jsx-a11y ×2
│       │   ├── chat/
│       │   │   └── ChatInterface.tsx          # exhaustive-deps
│       │   ├── chores/
│       │   │   ├── AddChoreModal.tsx          # jsx-a11y
│       │   │   └── ChoreChatFlow.tsx          # exhaustive-deps
│       │   ├── pipeline/
│       │   │   └── ModelSelector.tsx          # exhaustive-deps
│       │   └── tools/
│       │       └── UploadMcpModal.tsx         # exhaustive-deps
│       ├── hooks/
│       │   ├── useChatPanels.ts       # set-state-in-effect
│       │   ├── useRealTimeSync.ts     # exhaustive-deps (with reason)
│       │   └── useVoiceInput.ts       # no-explicit-any
│       ├── lib/
│       │   └── lazyWithRetry.ts       # no-explicit-any
│       └── test/
│           └── setup.ts               # @ts-expect-error ×2
└── docs/                              # Policy note target

infra/
└── modules/
    ├── monitoring.bicep               # disable-next-line outputs-should-not-contain-secrets
    ├── openai.bicep                   # disable-next-line outputs-should-not-contain-secrets
    └── storage.bicep                  # disable-next-line outputs-should-not-contain-secrets

solune/
├── scripts/
│   └── check-suppressions.sh          # NEW: CI suppression guard script
└── .pre-commit-config.yaml            # Hook: suppression guard integration
```

**Structure Decision**: This feature spans the full monorepo (backend, frontend, infra, CI). No new directories are created except `solune/scripts/` for the CI guard script. All changes modify existing files in their current locations.

## Phase 0: Research Outline

Completed in `research.md`. All unknowns resolved:

1. **Backend suppression inventory**: 50 total (5 type-ignore, 34 noqa, 4 pragma, 1 skip, 2 bandit, 1 ruff config, 3 pyright config)
2. **Frontend suppression inventory**: 20 inline + 4 config-level
3. **E2E test skip inventory**: 6 dynamic skips, 3 Playwright config entries
4. **Infrastructure suppression inventory**: 3 Bicep disable-next-line
5. **FastAPI B008 best practice**: Retain with reason (framework pattern)
6. **Frozen dataclass test pattern**: Retain with reason (intentional type violation)
7. **Pathlib migration**: Evaluate security semantics per-instance
8. **CI guard patterns**: Shell-based cross-language regex scanner

## Phase 1: Design Plan

1. **Suppression entity model** documented in `data-model.md` — tracks each suppression through IDENTIFIED → EVALUATED → REMOVED/RETAINED/DEFERRED lifecycle.
2. **CI guard contract** documented in `contracts/suppression-guard.openapi.yaml` — defines input (changed files), output (pass/fail with violation details), and pattern definitions.
3. **Verification commands** documented in `quickstart.md` — per-phase commands at progressively stricter settings.
4. **Agent context** updated after plan finalization.

## Phase 2: Implementation Planning Preview

### Phase 0 — Baseline (User Story 6)

1. Capture baseline check results for backend, frontend, E2E, and infra.
2. Record suppression counts per category.

### Phase 1 — Backend (User Story 1)

#### 1.1 — Bandit B608 Removal (HIGH PRIORITY — security)

- Remove `B608` from `skips` in `solune/backend/pyproject.toml`
- Run `bandit -r src/ -ll -ii --skip B104` to find all flagged SQL paths
- Audit and parameterize any unsafe queries
- Verify: `bandit -r src/` passes

#### 1.2 — Type Ignore Removal

- `agent_provider.py:501` and `plan_agent_provider.py:207`: Replace `config["reasoning_effort"] = reasoning_effort  # type: ignore[reportGeneralTypeIssues]` with a properly typed approach (e.g., TypedDict with `reasoning_effort` key, or `cast()`)
- `test_context.py:95,100,105`: Retain `# type: ignore[misc]` with `reason:` — intentional frozen dataclass mutation inside `pytest.raises(FrozenInstanceError)` test
- Verify: `pyright src` passes

#### 1.3 — Noqa Removal

- **B008 (12 instances)**: Retain all with `reason: FastAPI Depends() pattern — evaluated per-request, not at import time`
- **B009 (2 instances)**: `test_run_mutmut_shard.py` — evaluate if `getattr` can be replaced with direct attribute access
- **B010 (4 instances)**: Test files — evaluate if `setattr` on frozen models can use `object.__setattr__` or a test helper
- **E402 (1 instance)**: `github_projects/__init__.py` — restructure to avoid late import (the class it depends on is defined above)
- **F401 (9 instances)**: Replace with explicit `__all__` lists in `models/chat.py`, `copilot_polling/__init__.py`, `test_build_smoke.py`
- **PTH118/PTH119 (4 instances)**: `api/chat.py` — evaluate pathlib replacement preserving security sanitization semantics (one is marked as CodeQL sanitizer)
- **RUF001 (1 instance)**: `test_recommendation_models.py` — retain with `reason:` — intentional Unicode test data
- Verify: `ruff check src tests` passes

#### 1.4 — Pragma No Cover Removal

- `test_main.py:174`: Add test coverage for the `RuntimeError` branch or delete dead code
- `test_database.py:367,404`: Add coverage for the `patched_execute` callback paths
- `test_chat_agent.py:614`: Retain with `reason:` — `yield` makes function an async generator; unreachable by design
- Verify: `pytest --cov` shows improved coverage

#### 1.5 — Skipif Replacement

- `test_run_mutmut_shard.py:138-143`: Replace `@pytest.mark.skipif` with a fixture that ensures the CI workflow file exists (copy from repo or create a minimal fixture)
- Verify: Test runs successfully

#### 1.6 — Config Tightening

- Remove `E501` from Ruff `ignore` list in pyproject.toml
- Change `reportMissingImports` from `"warning"` to `"error"` in pyproject.toml
- Dry-run `reportMissingTypeStubs = true` — if too many stubs needed, defer with documentation
- Review coverage `exclude_lines` — keep `if TYPE_CHECKING:` and `if __name__ == .__main__.` (both are standard)
- Verify: All backend checks pass at stricter settings

### Phase 2 — Frontend (User Story 2)

#### 2.1 — React Hooks Exhaustive Deps (6 instances)

- `ChatInterface.tsx:437`: Add `mentionValidationError` to deps or use `useCallback` for the setter
- `AgentChatFlow.tsx:74`: Replace empty `[]` dep with proper dependencies or wrap in `useCallback`
- `ChoreChatFlow.tsx:62`: Same pattern as AgentChatFlow — replace empty dep array
- `ModelSelector.tsx:114`: Add `recentModelKeysRef` or restructure the `useMemo` dependency list
- `UploadMcpModal.tsx:215`: Add missing dependencies to the effect
- `useRealTimeSync.ts:236`: Already has reason comment — evaluate if the reason is still valid, retain if so

#### 2.2 — No Explicit Any (2 instances)

- `useVoiceInput.ts:42-43`: Replace `window as any` with a typed interface for `SpeechRecognition` / `webkitSpeechRecognition`
- `lazyWithRetry.ts:13-14`: Replace `ComponentType<any>` with `ComponentType<Record<string, unknown>>` or a proper generic bound

#### 2.3 — Set State in Effect

- `useChatPanels.ts:93`: Refactor the initialization pattern to use lazy state initialization (`useState(() => ...)`) or `useRef` + sync update instead of `setState` inside `useEffect`

#### 2.4 — JSX A11y (8 instances)

- `AddChoreModal.tsx:266` and `AddAgentPopover.tsx:114`: Replace `autoFocus` with imperative `useRef` + `useEffect(() => ref.current?.focus())` pattern
- `AgentIconPickerModal.tsx:59`, `AgentPresetSelector.tsx:70,100`, `AddAgentModal.tsx:263,313,357`: Replace click-on-non-interactive suppressions by adding `onKeyDown` handlers (Enter/Space) to the `<div>` elements or converting them to `<button>` elements

#### 2.5 — TS Expect Error (2 instances)

- `setup.ts:14`: Replace `// @ts-expect-error` with a typed partial crypto shim: `globalThis.crypto = {} as Crypto`
- `setup.ts:58`: Replace `// @ts-expect-error` with proper WebSocket type: declare `MockWebSocket` as implementing the `WebSocket` interface

#### 2.6 — Rules of Hooks Disable

- `e2e/fixtures.ts:1`: Remove file-wide `/* eslint-disable react-hooks/rules-of-hooks */` by renaming helper functions so they don't start with `use` prefix (Playwright fixtures are not React hooks)

#### 2.7 — Stryker Config

- `stryker.config.mjs:19`: Change `ignoreStatic: true` to `ignoreStatic: false`
- Run mutation testing, identify surviving mutants, and close gaps with additional tests

#### 2.8 — TSConfig Test Strictness

- `tsconfig.test.json:5-6`: Change both `noUnusedLocals` and `noUnusedParameters` to `true`
- Fix all resulting unused variable/parameter errors (prefix with `_` or remove)

#### 2.9 — ESLint Config Audit

- `eslint.config.js`: Evaluate `security/detect-object-injection: 'off'` — this is commonly a false-positive rule; document reason for keeping off
- Test-file security rule overrides are justified — retain with comments
- Verify: `npm run lint -- --max-warnings=0` passes

### Phase 3 — E2E (User Story 3)

#### 3.1 — Replace Dynamic Skips

- `integration.spec.ts:62,73`: Replace `test.skip()` with Playwright project configuration that only runs integration tests when the backend is available (use `process.env.CI` check in `playwright.config.ts` project setup)
- `project-load-performance.spec.ts:47,50,65,114`: Replace with tag-driven filtering or a dedicated Playwright project with `testMatch` and prerequisites

#### 3.2 — Document Playwright Config

- `playwright.config.ts:10`: Add comment explaining why `save-auth-state.ts` is in `testIgnore` (it's a setup utility, not a test)
- `playwright.config.ts:14`: `forbidOnly` already has an explanatory comment — verify it's sufficient

### Phase 4 — Infrastructure (User Story 4)

#### 4.1 — Bicep Secret Output Review

- `monitoring.bicep:42`: Retain `#disable-next-line outputs-should-not-contain-secrets` with documented reason — Container Apps Environment requires the shared key directly; Key Vault reference not supported
- `openai.bicep:75`: Retain with documented reason — key is passed to Key Vault in the parent module
- `storage.bicep:75`: Retain with documented reason — key is required for Azure Files volume mount configuration
- Add `reason:` comment on the preceding `@description` line for each

#### 4.2 — Verify Infrastructure

- Run `az bicep build --file main.bicep` to confirm compilation

### Phase 5 — Policy & Enforcement (User Story 5)

#### 5.1 — Create CI Suppression Guard

- Create `solune/scripts/check-suppressions.sh` that:
  - Accepts a list of changed files (or scans git diff)
  - Matches known suppression patterns (Python, TypeScript, Bicep)
  - Checks each match for a `reason:` or `--` justification
  - Exits non-zero with a report of unjustified suppressions

#### 5.2 — Integrate Guard into CI

- Add guard as a step in `.github/workflows/ci.yml` or as a pre-commit hook in `.pre-commit-config.yaml`

#### 5.3 — Review Ignore Files

- Audit `.gitignore` for stale entries (research found none)
- Audit `.prettierignore` for stale entries (research found none)
- Confirm no `.eslintignore` or `.ruffignore` conflicts (research confirmed none exist)

#### 5.4 — Add Policy Documentation

- Add a short policy note to `solune/docs/` explaining suppression standards

## Complexity Tracking

No constitution exceptions or additional complexity are required for this feature.
