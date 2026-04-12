# Research: Simplify Page Headers for Focused UI

**Feature**: `001-simplify-page-headers`  
**Date**: 2026-04-12  
**Status**: Complete

## R1. Shared header implementation strategy

**Decision**: Standardize all six affected pages on the existing `CompactPageHeader` component at `/home/runner/work/solune/solune/solune/frontend/src/components/common/CompactPageHeader.tsx`.

**Rationale**: Repo evidence already shows a reusable compact header component plus targeted tests in `/home/runner/work/solune/solune/solune/frontend/src/components/common/CompactPageHeader.test.tsx`. Reusing that component satisfies the spec’s DRY requirement, preserves a single prop contract, and keeps the migration frontend-only.

**Alternatives considered**:
- Rebuild a second compact header variant per page — rejected because it duplicates layout logic and increases drift risk.
- Keep the prior hero layout and trim styles only — rejected because the feature explicitly removes decorative hero behavior and reclaims vertical space.

## R2. Mobile stats behavior

**Decision**: Keep stats inline on larger viewports and hide them behind a toggle on mobile, matching the current `CompactPageHeader` behavior.

**Rationale**: The spec requires mobile stats to be hidden by default and accessible via a toggle. The current component already implements this with a local disclosure state, an accessible button, and a responsive layout that avoids crowding narrow screens.

**Alternatives considered**:
- Always show stats on mobile — rejected because it increases crowding and risks breaking the compact height goal.
- Remove stats entirely on mobile — rejected because it drops useful context and conflicts with the feature requirements.

## R3. CSS cleanup boundary

**Decision**: Remove only hero-specific selectors and references that become orphaned after migration; retain shared classes such as `.moonwell`, `.hanging-stars`, and reusable `celestial-*` animation utilities when they are still referenced elsewhere.

**Rationale**: Repo search shows `.moonwell` is used broadly across tools, chores, agents, board, and pipeline views. `celestial-*` animation utilities are also used outside page headers (for example in layout, loader, login, and error-related components), so broad deletion would cause regressions unrelated to this feature.

**Alternatives considered**:
- Delete all celestial visual utility classes with the hero — rejected because those utilities are shared.
- Skip CSS cleanup completely — rejected because the spec explicitly requires dead-code removal when safe.

## R4. Regression-validation strategy

**Decision**: Treat frontend tests and static validation as required for implementation even though the constitution makes tests optional by default.

**Rationale**: The spec includes success criteria for passing frontend tests, linting, and type-checking with no regressions. The existing stack in `/home/runner/work/solune/solune/solune/frontend/package.json` already supports the needed validation via `vitest`, `eslint`, and `tsc --noEmit`, so no new tooling is required.

**Alternatives considered**:
- Rely only on manual visual review — rejected because regression-free behavior is a stated requirement.
- Add a new dedicated testing framework — rejected because the existing stack is sufficient.

## R5. Scope and rollout

**Decision**: Plan for a single shared-component rollout across Projects, Agents, Agents Pipeline, Tools, Chores, and Help, with no backend or contract/API server changes.

**Rationale**: The feature is presentation-only, all affected pages live under `/home/runner/work/solune/solune/solune/frontend/src/pages`, and the component contract is common across the pages. A big-bang rollout is simpler than partial migration because there is no data-model or persistence migration to stage.

**Alternatives considered**:
- Incremental page-by-page rollout — rejected because it would prolong duplicate header patterns without reducing implementation risk.
- Feature-flag the compact header — rejected because the change is local to one frontend surface and does not warrant runtime configuration.
