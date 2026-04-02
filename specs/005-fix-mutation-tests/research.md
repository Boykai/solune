# Research: Fix Mutation Testing Infrastructure

**Feature**: 005-fix-mutation-tests
**Date**: 2026-04-02
**Status**: Complete

## Research Task 1: Backend mutmut workspace parity — why templates/ is missing

### Context

Every backend mutation shard aborts because `registry.py` cannot find `templates/app-templates/` inside the mutmut-generated `mutants/` workspace. The `also_copy` list in `pyproject.toml` does not include the `templates/` directory.

### Findings

- `registry.py` line 11 resolves the template directory via `Path(__file__).resolve().parents[3] / "templates" / "app-templates"`. When running inside the mutmut workspace, `__file__` is at `mutants/.../src/services/app_templates/registry.py`, and `parents[3]` resolves to the `mutants/` root (which mirrors `backend/`).
- mutmut's `also_copy` controls which files/directories are duplicated into the `mutants/` tree beyond `paths_to_mutate`. The current list includes `src/api/`, `src/models/`, etc., but omits `templates/`.
- `test_agent_tools.py` imports and exercises `list_app_templates`, `get_app_template`, and related functions that trigger `registry.py`'s template discovery. Without `templates/app-templates/` in the workspace, `discover_templates()` logs a warning and returns empty, causing test failures or "not checked" noise.

### Decision

Add `"templates/"` to the `also_copy` list in `[tool.mutmut]` section of `pyproject.toml`.

### Rationale

This is the minimal fix that mirrors the real backend directory structure inside the mutant workspace. No code changes to `registry.py` are needed — the path resolution is correct; only the workspace copy list is incomplete.

### Alternatives Considered

1. **Symlink templates/ into mutants/**: Rejected — mutmut does not support symlinks in also_copy; fragile across CI platforms.
2. **Change registry.py to use environment variable for template path**: Rejected — over-engineering for a config issue; introduces a new code path that must also be tested.
3. **Skip app-template tests during mutation**: Rejected — violates the "no threshold lowering" principle.

---

## Research Task 2: Backend shard drift — why api-and-middleware is missing from CI

### Context

`run_mutmut_shard.py` defines 5 shards: `auth-and-projects`, `orchestration`, `app-and-data`, `agents-and-integrations`, `api-and-middleware`. The CI workflow `mutation-testing.yml` only runs 4 (omits `api-and-middleware`).

### Findings

- The `api-and-middleware` shard covers `src/api/`, `src/middleware/`, and `src/utils.py` — these are significant backend modules.
- The CI matrix in `mutation-testing.yml` was likely left incomplete when the 5th shard was added to the Python script.
- `testing.md` documents "four shard jobs" which matches the current (incomplete) CI matrix.

### Decision

Add `api-and-middleware` to the `mutation-testing.yml` backend matrix and update `testing.md` to document all 5 shards.

### Rationale

The shard is already defined and tested in the script. Removing it from CI is an accidental omission, not an intentional scope reduction. Adding it maintains complete mutation coverage.

### Alternatives Considered

1. **Remove api-and-middleware from run_mutmut_shard.py**: Rejected — this would reduce mutation coverage of API routes and middleware, which are high-value targets.
2. **Merge api-and-middleware into another shard**: Rejected — the existing shards are already well-scoped; adding more paths would increase shard runtime.

---

## Research Task 3: Frontend Stryker sharding strategy

### Context

The monolithic Stryker run produces 6,580 mutants from 73 source files, times out at ~71%, and yields 2,893 survivors plus 4 timed-out mutants. This needs splitting into manageable CI shards.

### Findings

- Current `stryker.config.mjs` mutates `src/hooks/**/*.ts` and `src/lib/**/*.ts` (excluding test files).
- Frontend hooks can be logically grouped by domain:
  - **Board/polling hooks**: `useAdaptivePolling.ts`, `useBoardProjection.ts`, `useBoardRefresh.ts`, `useProjectBoard.ts`, `useRealTimeSync.ts` — these are the most survivor-heavy and most important to shard separately.
  - **Data/query hooks**: `useProjects.ts`, `useChat.ts`, `useChatHistory.ts`, `useCommands.ts`, `useWorkflow.ts`, `useSettingsForm.ts`, `useAuth.ts` — data-fetching and state management hooks.
  - **General hooks**: remaining hooks not in the above two groups (e.g., `useConfirmation.ts`, `useKeyboardShortcuts.ts`, etc.).
  - **Lib/utils**: `src/lib/**/*.ts` — utility functions, command registry, config builders.
- Stryker supports `--mutate` overrides and per-config files. Each shard can use its own `stryker-<shard>.config.mjs` that imports the base config and overrides only the `mutate` globs.
- GitHub Actions matrix can parallelize frontend shards like backend shards.

### Decision

Create 4 shard-specific Stryker configs and add a 4-shard matrix to the frontend mutation CI job. Add corresponding `package.json` scripts for local focused runs.

### Rationale

4 shards of ~1,600 mutants each should complete well under the 3-hour timeout. Logical grouping by domain makes reports actionable (survivors cluster around related behavior).

### Alternatives Considered

1. **2 shards (hooks + lib)**: Rejected — hooks alone produce ~4,000+ mutants, still too large for a single 3-hour job.
2. **6+ shards (one per file group)**: Rejected — excessive CI matrix complexity; 4 provides sufficient parallelism.
3. **Dynamic sharding by file count**: Rejected — Stryker doesn't natively support file-count-based sharding; explicit configs are simpler and more predictable.

---

## Research Task 4: test-utils.tsx double-render bug

### Context

`renderWithProviders()` in `test-utils.tsx` renders `children` inside both `ConfirmationDialogProvider` and `TooltipProvider` as siblings, causing the component under test to appear twice in the DOM.

### Findings

- Current code:
  ```tsx
  <QueryClientProvider client={queryClient}>
    <ConfirmationDialogProvider>{children}</ConfirmationDialogProvider>
    <TooltipProvider delayDuration={0}>{children}</TooltipProvider>
  </QueryClientProvider>
  ```
- `{children}` is referenced twice as direct children of two sibling providers. React renders both, so the UI element appears twice.
- The fix is to nest the providers so children passes through all of them once:
  ```tsx
  <QueryClientProvider client={queryClient}>
    <ConfirmationDialogProvider>
      <TooltipProvider delayDuration={0}>{children}</TooltipProvider>
    </ConfirmationDialogProvider>
  </QueryClientProvider>
  ```

### Decision

Nest `TooltipProvider` inside `ConfirmationDialogProvider` (both wrapping `children` once).

### Rationale

This matches the expected provider nesting pattern. Both providers are context-based and don't conflict when nested. The fix halves unnecessary DOM elements and test runtime.

### Alternatives Considered

1. **Remove TooltipProvider from renderWithProviders**: Rejected — components using `<Tooltip>` would fail without the provider.
2. **Create separate render functions for each provider combo**: Rejected — violates DRY; the nested approach provides all providers universally.

---

## Research Task 5: Stryker best practices for CI sharding

### Context

How to structure Stryker configs for multi-shard CI execution.

### Findings

- Stryker supports `--mutate` CLI override to narrow scope per run.
- Per-shard config files can use JavaScript spread/import to extend a base config.
- `htmlReporter.fileName` should differ per shard to avoid artifact collisions.
- CI matrix can pass shard name as a variable to select the config file.
- Each shard should upload its own artifact with a unique name.

### Decision

Use separate `stryker-<shard>.config.mjs` files that spread the base config and override `mutate` and `htmlReporter.fileName`. CI matrix passes shard name to select the config.

### Rationale

Explicit config files are self-documenting, easy to review, and don't require Stryker CLI flag chaining. Each file clearly shows its scope.

### Alternatives Considered

1. **Single config with CLI `--mutate` override per shard**: Works but harder to document and more error-prone in CI matrix definitions.
2. **Stryker's built-in `--incremental` mode**: Doesn't solve the sharding problem; it only skips unchanged mutants.
