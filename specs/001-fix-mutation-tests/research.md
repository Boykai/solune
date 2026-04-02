# Research: Fix Mutation Tests

**Feature**: 001-fix-mutation-tests
**Date**: 2026-04-02
**Status**: Complete

## Research Task 1: Backend Mutmut Workspace Parity — Missing App-Template Assets

### Context

Every backend mutation shard aborts on `test_agent_tools.py` because the mutant workspace is missing the `templates/app-templates/` directory. The template registry (`solune/backend/src/services/app_templates/registry.py`) resolves templates via `Path(__file__).resolve().parents[3] / "templates" / "app-templates"`, which under mutmut points into the mutant workspace rather than the real repo tree.

### Decision

Add `../templates/` to the `also_copy` list in `[tool.mutmut]` within `solune/backend/pyproject.toml`. Mutmut's `also_copy` copies paths relative to the backend directory into the mutant workspace, preserving the relative directory structure.

### Rationale

- `registry.py` resolves `Path(__file__).resolve().parents[3] / "templates" / "app-templates"`. Inside the normal repo, `__file__` is `solune/backend/src/services/app_templates/registry.py`, so `parents[3]` is `solune/backend/` → `solune/` → the parent that contains `templates/`. Inside the mutant workspace, the same traversal must find `templates/` at the corresponding level.
- `template_files.py` resolves `Path(__file__).resolve().parents[4]` (4 levels up from `src/services/template_files.py`) to reach the repo root for `.github/` and `.specify/` assets. This path also needs workspace parity: `.github/` and `.specify/` must be available (or the env var `TEMPLATE_SOURCE_DIR` must be set in tests).
- Mutmut's `also_copy` accepts relative paths from the directory containing `pyproject.toml` (i.e., `solune/backend/`). Using `../templates/` copies `solune/templates/` into the mutant workspace at the correct relative position.

### Alternatives Considered

1. **Set `TEMPLATE_SOURCE_DIR` env var in mutmut test runner**: Would fix `template_files.py` but not `registry.py`, which has no env var override. Rejected because it requires code changes to production code.
2. **Symlink templates into mutant workspace via a pre-mutation hook**: Mutmut has no official pre-mutation hook. Rejected as fragile and non-standard.
3. **Mock all template path resolution in tests**: Rejected because the spec explicitly requires that template paths resolve correctly inside the mutant workspace without mutation-tool-specific workarounds (FR-012).

---

## Research Task 2: Backend Shard Drift — 5 Defined vs 4 in CI

### Context

`run_mutmut_shard.py` defines five shards: `auth-and-projects`, `orchestration`, `app-and-data`, `agents-and-integrations`, and `api-and-middleware`. The CI workflow `mutation-testing.yml` only runs four, omitting `api-and-middleware`. The testing documentation also lists only four.

### Decision

Add the `api-and-middleware` shard to the CI workflow's matrix and update `testing.md` to document all five shards.

### Rationale

- The spec assumption (A4) states the shard was unintentionally omitted.
- The `api-and-middleware` shard covers `src/api/`, `src/middleware/`, and `src/utils.py` — meaningful backend code that should be mutation-tested.
- Adding a shard is a one-line matrix entry change plus artifact upload config.
- Documentation must match CI and shard runner per FR-003 and SC-006.

### Alternatives Considered

1. **Remove `api-and-middleware` from `run_mutmut_shard.py`**: Rejected because it deliberately reduces mutation coverage scope (violates FR-011).
2. **Merge `api-and-middleware` into an existing shard**: Rejected because the existing shards are already well-scoped and adding API/middleware modules would blur boundaries.

---

## Research Task 3: Frontend Stryker Sharding Strategy

### Context

The current Stryker configuration mutates `src/hooks/**/*.ts` and `src/lib/**/*.ts`, producing 6,580+ mutants from 73 source files. A single CI job times out at ~71% progress within the 3-hour limit.

### Decision

Split frontend mutation into 4 CI shards, each with its own mutate glob:

| Shard | Mutate Globs | Rationale |
|-------|-------------|-----------|
| `board-polling-hooks` | `src/hooks/useAdaptivePolling.ts`, `src/hooks/useBoardProjection.ts`, `src/hooks/useBoard*.ts`, `src/hooks/*Poll*.ts`, `src/hooks/*Board*.ts` | Performance-critical hooks with known survivor gaps |
| `data-query-hooks` | `src/hooks/useQuery*.ts`, `src/hooks/useMutation*.ts`, `src/hooks/use*Data*.ts`, `src/hooks/use*Fetch*.ts` | Data-fetching hooks with TanStack Query patterns |
| `general-hooks` | `src/hooks/**/*.ts` (minus the above) | Remaining hooks (UI, auth, state) |
| `lib-utils` | `src/lib/**/*.ts` | Utility functions, config builders, helpers |

Each shard uses a separate Stryker configuration override via `--mutate` CLI flags, avoiding multiple config files.

### Rationale

- 4 shards at ~1,645 mutants each should complete well within 3 hours based on the ~71% completion rate of the full run (meaning ~4,670 were processed in ~3 hours, so ~1,645 should take ~1 hour).
- Sharding by logical area makes reports actionable: a developer working on polling hooks only needs the `board-polling-hooks` report.
- Stryker supports `--mutate` CLI overrides, so the base `stryker.config.mjs` remains unchanged and each shard passes its own glob.

### Alternatives Considered

1. **3 shards (hooks, lib, large-hooks-split)**: Rejected because hooks alone may still exceed 3 hours given the ~4,500 hook mutants estimated.
2. **Splitting by file size**: Rejected because it produces arbitrary groupings that aren't meaningful for developer triage.
3. **Multiple stryker config files per shard**: Rejected as overly complex; CLI `--mutate` overrides are simpler and DRY.

---

## Research Task 4: Stryker CLI Shard Invocation Pattern

### Context

Need to verify how Stryker supports per-shard mutate globs via CLI without requiring separate config files.

### Decision

Use `npx stryker run --mutate 'glob1,glob2'` syntax. Stryker's `--mutate` CLI flag accepts comma-separated globs that override the config file's `mutate` array. The exclusion pattern `!src/**/*.test.ts` from the base config is preserved.

### Rationale

- Stryker documentation confirms `--mutate` CLI flag overrides config-level `mutate` array.
- This approach keeps a single `stryker.config.mjs` as the source of truth for reporters, thresholds, timeouts, and other shared settings.
- Each shard only needs to specify its inclusion globs; the test-file exclusion can be appended to each shard's glob list.

### Alternatives Considered

1. **Environment variable to select shard config**: Stryker doesn't support config selection via env vars natively. Rejected.
2. **JavaScript config with conditional logic**: Possible but adds complexity. Rejected per constitution principle V (simplicity).

---

## Research Task 5: Frontend test-utils.tsx Double-Render Bug

### Context

The `renderWithProviders` function in `solune/frontend/src/test/test-utils.tsx` renders `{children}` twice: once inside `<ConfirmationDialogProvider>` and once inside `<TooltipProvider>`. These are siblings within `<QueryClientProvider>`, not nested.

### Decision

Fix by properly nesting providers so `{children}` appears exactly once:

```tsx
function Wrapper({ children }: WrapperProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfirmationDialogProvider>
        <TooltipProvider delayDuration={0}>
          {children}
        </TooltipProvider>
      </ConfirmationDialogProvider>
    </QueryClientProvider>
  );
}
```

### Rationale

- The current implementation renders the component under test twice in the DOM, which can cause doubled side effects, doubled DOM queries, and incorrect assertion counts.
- Nesting providers is the standard React pattern. Provider order (outermost to innermost): QueryClientProvider → ConfirmationDialogProvider → TooltipProvider.
- Tests relying on the double-render are either non-existent or will surface as obvious failures that are easily corrected (spec assumption A7).

### Alternatives Considered

1. **Keep double render and adjust tests**: Rejected because it masks a real bug and wastes test runtime.
2. **Remove one provider from the wrapper**: Rejected because both providers are needed for comprehensive test coverage.

---

## Research Task 6: Focused Mutation Commands Best Practices

### Context

Developers need file-level or area-level mutation commands for both frontend (Stryker) and backend (mutmut) without running the full suite.

### Decision

**Frontend**: Add `package.json` scripts for each shard plus a single-file command:

```json
"test:mutate:file": "stryker run --mutate",
"test:mutate:hooks-board": "stryker run --mutate 'src/hooks/useAdaptivePolling.ts,...'",
"test:mutate:hooks-data": "stryker run --mutate 'src/hooks/useQuery*.ts,...'",
"test:mutate:hooks-general": "stryker run --mutate 'src/hooks/**/*.ts,...'",
"test:mutate:lib": "stryker run --mutate 'src/lib/**/*.ts,...'"
```

**Backend**: The existing `run_mutmut_shard.py --shard <name>` pattern already supports per-shard runs. Document it more prominently.

### Rationale

- Named shard scripts in `package.json` are discoverable via `npm run` tab-completion.
- A single-file command (`test:mutate:file`) accepts a file path argument, enabling ad-hoc focused runs.
- Backend already has the shard runner; documentation is the gap, not tooling.

### Alternatives Considered

1. **Makefile targets**: Rejected because the project uses npm scripts for frontend and Python scripts for backend; Makefile would add a third command surface.
2. **Custom Stryker plugin for shard selection**: Over-engineered for this use case. Rejected.

---

## Research Task 7: Survivor Prioritization Strategy

### Context

After sharding, the first successful reports will reveal real survivors. The spec identifies `useAdaptivePolling.ts` and `useBoardProjection.ts` as confirmed priority targets, plus utility files covered by property tests.

### Decision

Prioritize survivor cleanup in this order:

1. **useAdaptivePolling.ts**: Tier transition boundaries, visibility-triggered immediate polls, failure backoff thresholds
2. **useBoardProjection.ts**: Projection expansion ranges, batch sizes, observer cleanup
3. **Utility files with property tests**: `buildGitHubMcpConfig`, `pipelineMigration`, `utils` — add deterministic edge-case assertions alongside existing property tests

### Rationale

- Hooks 1 and 2 drive core user-facing behavior (polling frequency and lazy-loading); survivors here are highest risk.
- Property tests provide broad coverage but may miss specific boundary conditions that mutation testing targets. Deterministic assertions complement rather than replace them.
- This order matches the spec's explicit priority guidance.

### Alternatives Considered

1. **Tackle by shard report order**: Rejected because it doesn't account for business risk.
2. **Only add property tests**: Rejected per FR-008 which mandates deterministic assertions for specific behavioral gaps.
