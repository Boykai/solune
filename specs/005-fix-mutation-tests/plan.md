# Implementation Plan: Fix Mutation Testing Infrastructure

**Branch**: `005-fix-mutation-tests` | **Date**: 2026-04-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-fix-mutation-tests/spec.md`

## Summary

Backend mutation testing is broken: every shard aborts because mutmut's workspace is missing `templates/` assets required by `registry.py` and exercised by `test_agent_tools.py`. Additionally, `run_mutmut_shard.py` defines 5 shards but CI only runs 4 (missing `api-and-middleware`). Frontend mutation is too large for one 3-hour job (6,580 mutants, times out at ~71%). This plan fixes backend workspace parity, aligns backend shards, splits frontend mutation into CI shards, fixes the `test-utils.tsx` double-render bug, adds developer-facing focused commands, and updates documentation.

## Technical Context

**Language/Version**: Python ≥3.12 (target 3.13) for backend; TypeScript ~6.0.2 / Node 22 for frontend
**Primary Dependencies**: FastAPI, mutmut ≥3.2.0 (backend mutation); Stryker ≥9.6.0, Vitest ≥4.0.18 (frontend mutation); GitHub Actions (CI)
**Storage**: N/A (configuration and CI infrastructure changes only)
**Testing**: pytest (backend), Vitest + React Testing Library (frontend), mutmut (backend mutation), Stryker (frontend mutation)
**Target Platform**: GitHub Actions CI (ubuntu-latest); local developer machines
**Project Type**: Web application (backend + frontend monorepo under `solune/`)
**Performance Goals**: Each CI mutation shard must complete well under 180-minute timeout
**Constraints**: No mutation threshold lowering; no permanent scope reduction; CI artifact upload per shard
**Scale/Scope**: Backend: 5 shards covering `src/services/`, `src/api/`, `src/middleware/`, `src/utils.py`. Frontend: 4 shards covering `src/hooks/**/*.ts` and `src/lib/**/*.ts` (~73 source files, ~6,580 mutants total)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Issue #518 serves as the specification; spec.md created from issue context |
| II. Template-Driven Workflow | ✅ PASS | All artifacts follow canonical templates |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan phase produces plan.md, research.md, data-model.md, quickstart.md, contracts/ |
| IV. Test Optionality | ✅ PASS | Tests are explicitly in scope (mutation testing infrastructure is the feature itself) |
| V. Simplicity and DRY | ✅ PASS | Changes are minimal configuration/workflow edits; no new abstractions introduced |

**Gate result**: PASS — no violations. Proceed to Phase 0.

### Post-Phase 1 Re-Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | All design artifacts trace back to spec requirements |
| II. Template-Driven Workflow | ✅ PASS | Plan, research, data-model, quickstart follow templates |
| III. Agent-Orchestrated Execution | ✅ PASS | Clear handoff to tasks phase |
| IV. Test Optionality | ✅ PASS | Mutation testing is the feature; test infrastructure changes are the deliverable |
| V. Simplicity and DRY | ✅ PASS | Shard configs reuse existing Stryker/mutmut patterns; `test-utils.tsx` fix removes duplication |

**Post-design gate result**: PASS — no violations.

## Project Structure

### Documentation (this feature)

```text
specs/005-fix-mutation-tests/
├── plan.md              # This file
├── spec.md              # Feature specification (from issue context)
├── research.md          # Phase 0: research findings
├── data-model.md        # Phase 1: configuration data model
├── quickstart.md        # Phase 1: developer quickstart
└── contracts/
    └── shard-matrix.md  # Phase 1: shard layout contract
```

### Source Code (files modified by this feature)

```text
solune/
├── backend/
│   ├── pyproject.toml                          # Add templates/ to [tool.mutmut].also_copy
│   ├── scripts/run_mutmut_shard.py             # Reference only (already correct)
│   ├── src/services/app_templates/registry.py  # Reference only (path resolution verified)
│   ├── src/services/template_files.py          # Reference only (path resolution verified)
│   └── templates/app-templates/                # Assets that must be copied to mutant workspace
├── frontend/
│   ├── package.json                            # Add focused mutation scripts
│   ├── stryker.config.mjs                      # Base config (may become shared)
│   ├── stryker-hooks-board.config.mjs          # New: board/polling hooks shard
│   ├── stryker-hooks-data.config.mjs           # New: data/query hooks shard
│   ├── stryker-hooks-general.config.mjs        # New: general hooks shard
│   ├── stryker-lib.config.mjs                  # New: lib/utils shard
│   └── src/test/test-utils.tsx                 # Fix double-render bug
├── docs/testing.md                             # Update shard documentation
├── CHANGELOG.md                                # Add infrastructure change entries
└── .github/workflows/mutation-testing.yml      # Add api-and-middleware shard + frontend shards
```

**Structure Decision**: Existing web application structure (backend + frontend under `solune/`). No new directories created beyond per-shard Stryker configs in `frontend/`.

## Execution Phases

### Phase A: Backend Workspace Parity (P1 — blocks everything)

1. **Add `templates/` to `[tool.mutmut].also_copy`** in `pyproject.toml`
   - This single line ensures `templates/app-templates/` is copied into the mutant workspace
   - `registry.py` resolves via `Path(__file__).resolve().parents[3] / "templates" / "app-templates"` — parents[3] from `mutants/.../src/services/app_templates/registry.py` must land on a directory containing `templates/`
   - Verify `template_files.py` still resolves correctly (it uses `parents[4]` which goes to workspace root — unaffected by also_copy)

2. **Verify locally**: Run pytest on `test_agent_tools.py` to confirm normal operation, then run a mutmut shard to confirm the template warning disappears

### Phase B: Backend Shard Drift (P1)

1. **Add `api-and-middleware` to `mutation-testing.yml`** backend matrix
2. **Update `testing.md`** to list all 5 shards

### Phase C: Frontend Stryker Sharding (P2)

1. **Create 4 shard-specific Stryker configs** that extend/override the base `stryker.config.mjs`:
   - `stryker-hooks-board.config.mjs`: `src/hooks/useAdaptivePolling.ts`, `src/hooks/useBoardProjection.ts`, `src/hooks/useBoardRefresh.ts`, `src/hooks/useProjectBoard.ts`
   - `stryker-hooks-data.config.mjs`: `src/hooks/useProjects.ts`, `src/hooks/useChat.ts`, `src/hooks/useChatHistory.ts`, related data/query hooks
   - `stryker-hooks-general.config.mjs`: remaining hooks (`useAuth.ts`, `useCommands.ts`, `useSettingsForm.ts`, `useWorkflow.ts`, etc.)
   - `stryker-lib.config.mjs`: `src/lib/**/*.ts`

2. **Add shard matrix to `mutation-testing.yml`** frontend section
3. **Add focused `package.json` scripts**: `test:mutate:hooks-board`, `test:mutate:hooks-data`, `test:mutate:hooks-general`, `test:mutate:lib`

### Phase D: Frontend test-utils Fix (P2)

1. **Fix `renderWithProviders()` Wrapper** to nest providers instead of rendering children twice:
   ```tsx
   // Before (bug): children rendered twice
   <QueryClientProvider client={queryClient}>
     <ConfirmationDialogProvider>{children}</ConfirmationDialogProvider>
     <TooltipProvider delayDuration={0}>{children}</TooltipProvider>
   </QueryClientProvider>

   // After (fix): providers nested correctly
   <QueryClientProvider client={queryClient}>
     <ConfirmationDialogProvider>
       <TooltipProvider delayDuration={0}>{children}</TooltipProvider>
     </ConfirmationDialogProvider>
   </QueryClientProvider>
   ```

### Phase E: Documentation (P3)

1. **Update `testing.md`**: document all 5 backend shards, 4 frontend shards, focused commands
2. **Update `CHANGELOG.md`**: add entries under `[Unreleased]` for infrastructure changes

## Dependency Order

```text
Phase A (backend parity) ──┐
                           ├── Phase B (backend shard drift) ── Phase E (docs)
Phase D (test-utils fix)   │
                           │
Phase C (frontend sharding) ┘
```

- Phase A must complete first (blocks all backend mutation work)
- Phases B, C, D can proceed in parallel after A
- Phase E depends on B and C being finalized

## Complexity Tracking

> No constitution violations detected. No complexity justifications required.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
