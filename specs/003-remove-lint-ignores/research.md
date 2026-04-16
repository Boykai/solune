# Research: Remove Lint/Test Ignores & Fix Discovered Bugs

**Feature**: `003-remove-lint-ignores` | **Date**: 2026-04-16

## Research Task 1: Backend Suppression Inventory

### Decision: 50 total backend suppressions identified across 6 categories

### Findings

| Category | Count | Details |
|----------|-------|---------|
| `# type: ignore` | 5 | 2 in services (reportGeneralTypeIssues), 3 in test (frozen dataclass assignment) |
| `# noqa` | 34 | B008×12, B009×2, B010×4, E402×1, F401×9, PTH118×2, PTH119×2, RUF001×1 |
| `# pragma: no cover` | 4 | All in test files (test_main, test_database×2, test_chat_agent) |
| `@pytest.mark.skipif` | 1 | test_run_mutmut_shard.py (CI workflow file check) |
| Bandit skips | 2 | B104 (hardcoded temp dir), B608 (SQL injection) in pyproject.toml |
| Ruff ignore | 1 | E501 (line length) in pyproject.toml |

**Pyright config suppressions:**

- `reportMissingTypeStubs = false` (pyproject.toml)
- `reportMissingImports = "warning"` (pyproject.toml)
- `typeCheckingMode = "off"` (pyrightconfig.tests.json)

**Coverage exclusions (pyproject.toml):**

- `pragma: no cover`
- `if TYPE_CHECKING:`
- `if __name__ == .__main__.`

### Rationale

Full inventory was obtained by scanning all Python, TOML, and JSON config files in `solune/backend/`. No `.ruffignore` exists. The 34 `# noqa` markers dominate the count, with the 12 B008 (FastAPI `Depends()`) markers being architecturally required.

### Alternatives Considered

- Automated grep alone misses config-level suppressions; combined config + source scan was necessary.

---

## Research Task 2: Frontend Suppression Inventory

### Decision: 20 inline suppressions + 4 config-level suppressions identified

### Findings

| Category | Count | Details |
|----------|-------|---------|
| `eslint-disable` (react-hooks/rules-of-hooks) | 1 | File-wide in e2e/fixtures.ts |
| `eslint-disable` (react-hooks/exhaustive-deps) | 6 | ChatInterface, useRealTimeSync, UploadMcpModal, ModelSelector, ChoreChatFlow, AgentChatFlow |
| `eslint-disable` (react-hooks/set-state-in-effect) | 1 | useChatPanels.ts |
| `eslint-disable` (@typescript-eslint/no-explicit-any) | 2 | useVoiceInput.ts, lazyWithRetry.ts |
| `eslint-disable` (jsx-a11y/*) | 8 | AddChoreModal (1), AddAgentPopover (1), AgentIconPickerModal (1), AgentPresetSelector (2), AddAgentModal (3) |
| `@ts-expect-error` | 2 | setup.ts (crypto shim, WebSocket mock) |

**Config-level:**

- Stryker `ignoreStatic: true` (stryker.config.mjs)
- `noUnusedLocals: false` (tsconfig.test.json)
- `noUnusedParameters: false` (tsconfig.test.json)
- ESLint `security/detect-object-injection: 'off'` (eslint.config.js)
- ESLint test/e2e security rule overrides (justified for test contexts)

**Corrected file paths (spec referenced outdated paths):**

| Spec Path | Actual Path |
|-----------|------------|
| `components/chat/UploadMcpModal.tsx` | `components/tools/UploadMcpModal.tsx` |
| `components/chat/ModelSelector.tsx` | `components/pipeline/ModelSelector.tsx` |

### Rationale

The 6 `react-hooks/exhaustive-deps` suppressions are the highest-risk items — stale closures can cause subtle runtime bugs. The `useRealTimeSync.ts` instance already has a reason comment, but the suppression should still be evaluated. The jsx-a11y suppressions are numerous (8) but relatively low risk.

### Alternatives Considered

- Some jsx-a11y suppressions on modal dialogs with `role="dialog"` and `onClick={stopPropagation}` are borderline; full removal requires adding `onKeyDown` handlers to every interactive overlay.

---

## Research Task 3: E2E Test Skip Inventory

### Decision: 6 dynamic skips and 3 Playwright config suppressions identified

### Findings

**Dynamic `test.skip()` calls:**

| File | Line | Reason |
|------|------|--------|
| `e2e/project-load-performance.spec.ts` | 47 | Auth state file not found |
| `e2e/project-load-performance.spec.ts` | 50 | `E2E_PROJECT_ID` env var not set |
| `e2e/project-load-performance.spec.ts` | 65 | Frontend not reachable |
| `e2e/project-load-performance.spec.ts` | 114 | Frontend not reachable |
| `e2e/integration.spec.ts` | 62 | Backend not running (CI) |
| `e2e/integration.spec.ts` | 73 | Backend not running (CI) |

**Playwright config suppressions:**

| Setting | Value | File | Justified? |
|---------|-------|------|-----------|
| `testIgnore` | `['**/save-auth-state.ts']` | playwright.config.ts:10 | Yes — auth helper is not a test |
| `forbidOnly` | `!!process.env.CI` | playwright.config.ts:14 | Yes — standard CI safety check |
| `ignoreSnapshots` | `true` (Firefox only) | playwright.config.ts:44 | Yes — Chromium is the snapshot baseline |

### Rationale

All 6 dynamic skips are environment-precondition checks — they skip when the test environment is not fully provisioned. The spec proposes replacing these with tag-driven project setup. The Playwright config entries are all justified and should be retained with documentation.

### Alternatives Considered

- Tag-based filtering: Use Playwright's `@tag` annotations with `--grep` flags to conditionally include/exclude tests
- Project-based filtering: Use separate Playwright projects for different environment configurations
- Environment-based wiring: Use `playwright.config.ts` to conditionally define test suites based on `process.env`

---

## Research Task 4: Infrastructure Suppression Inventory

### Decision: 3 Bicep linter suppressions, all for secret outputs

### Findings

| File | Output | Purpose |
|------|--------|---------|
| `infra/modules/monitoring.bicep:42` | `workspaceSharedKey` | Log Analytics shared key → Container Apps Environment |
| `infra/modules/openai.bicep:75` | `openAiKey` | Azure OpenAI access key → stored in Key Vault |
| `infra/modules/storage.bicep:75` | `storageAccountKey` | Storage account key → Azure Files volume mounts |

### Rationale

All three outputs are consumed by downstream Bicep modules and ultimately stored in Key Vault. The Bicep linter rule `outputs-should-not-contain-secrets` is designed to prevent accidental secret exposure in deployment outputs, but these are intentional cross-module parameter passing patterns. Moving them behind Key Vault secret references within the module would require restructuring the deployment graph.

### Alternatives Considered

- **Key Vault reference refactoring**: Store secrets in Key Vault within each module and pass only Key Vault secret URIs. This is architecturally cleaner but requires all consumers to support Key Vault references, which Container Apps Environment does not natively support for shared keys.
- **Keep with justification**: Retain the suppressions with documented reasons. This is the recommended approach given the deployment constraints.

---

## Research Task 5: Best Practices for FastAPI Dependency Injection (B008)

### Decision: Keep `# noqa: B008` for FastAPI `Depends()` calls with `reason:` justification

### Rationale

Ruff B008 flags mutable default arguments in function signatures. FastAPI's `Depends()` pattern intentionally uses function calls as defaults — they are evaluated per-request, not at import time. This is a well-known false positive documented in the FastAPI ecosystem. All 12 instances follow this pattern.

### Alternatives Considered

- Disabling B008 globally: Too broad; the rule catches real bugs outside of FastAPI endpoints.
- Using a Ruff per-file ignore for API modules: Possible but less transparent than inline markers.

---

## Research Task 6: Best Practices for Frozen Dataclass Test Suppression (type: ignore[misc])

### Decision: Keep `# type: ignore[misc]` for frozen dataclass mutation tests with `reason:` justification

### Rationale

The 3 test instances in `test_context.py` intentionally assign to frozen dataclass fields inside `pytest.raises(FrozenInstanceError)` blocks. The type checker correctly flags these as errors — the test is verifying that the error is raised. Using `cast()` or `object.__setattr__()` would work around the type system but make the test intent less clear.

### Alternatives Considered

- `object.__setattr__(ctx, "github_token", "ghp_new")`: Bypasses the type check but also bypasses the frozen guard, defeating the test purpose.
- `cast()` with intermediate variable: Adds indirection without improving clarity.

---

## Research Task 7: Best Practices for Pathlib Migration (PTH118/PTH119)

### Decision: Evaluate each `os.path` usage for pathlib replacement, with security considerations

### Rationale

The 4 PTH118/PTH119 instances in `chat.py` use `os.path.basename()` and `os.path.normpath()` for filename sanitization in file upload handlers. One instance already has a comment `— CodeQL sanitizer` indicating it is part of a security path-traversal defense. Pathlib equivalents (`PurePosixPath.name`, `Path.resolve()`) exist but must preserve the sanitization semantics exactly.

### Alternatives Considered

- Replace with `pathlib.PurePosixPath(raw_name).name` for basename
- Replace with `pathlib.Path(candidate).resolve()` for normpath
- Keep with justification if the pathlib equivalent changes security behavior

---

## Research Task 8: CI Suppression Guard Patterns

### Decision: Shell-based grep guard with known suppression regex patterns

### Rationale

A CI guard script can scan changed files for suppression patterns using regex. Known patterns include:

- Python: `# noqa`, `# type: ignore`, `# pragma: no cover`, `@pytest.mark.skip`
- TypeScript: `eslint-disable`, `@ts-expect-error`, `@ts-ignore`
- Bicep: `#disable-next-line`
- Config: tool-level ignore/skip lists

Each match must be checked for a `reason:` marker (in a comment on the same or preceding line). The guard should be a pre-commit hook or CI step that exits non-zero on violations.

### Alternatives Considered

- ESLint plugin: Only covers JS/TS, not Python or Bicep.
- Ruff plugin: Only covers Python.
- Cross-language script: Shell script with grep patterns covers all languages. Recommended.

---

## Summary

All NEEDS CLARIFICATION items are resolved. Key decisions:

1. **Backend**: 50 suppressions — ~26 can be removed, 12 B008 markers retained with reasons, frozen-dataclass test markers retained with reasons.
2. **Frontend**: 20 inline + 4 config suppressions — all 6 exhaustive-deps to be fixed, jsx-a11y to be fixed, config items to be tightened.
3. **E2E**: 6 dynamic skips to be replaced with environment-based wiring.
4. **Infra**: 3 Bicep suppressions retained with documented justification.
5. **Policy**: Shell-based CI guard script for cross-language suppression enforcement.
