# Research: Dependabot Updates

**Feature**: Dependabot Updates | **Date**: 2026-04-14 | **Status**: Complete

## R1: Open Dependabot PR Inventory

**Decision**: 14 open Dependabot PRs identified across two ecosystems (npm and pip/uv).

**Rationale**: Full discovery via GitHub API search (`author:app/dependabot is:open`). Each PR modifies exactly one dependency in one manifest file.

### Frontend (npm) — 4 PRs

| PR | Package | Current | Target | Bump | Type |
|----|---------|---------|--------|------|------|
| #1777 | happy-dom | 20.8.9 | 20.9.0 | Patch | devDependency |
| #1776 | typescript-eslint | 8.58.1 | 8.58.2 | Patch | devDependency |
| #1775 | react-router-dom | 7.14.0 | 7.14.1 | Patch | dependency |
| #1699 | @tanstack/react-query | 5.97.0 | 5.99.0 | Minor | dependency |

### Backend (pip/uv) — 10 PRs

| PR | Package | Current | Target | Bump | Type |
|----|---------|---------|--------|------|------|
| #1732 | pytest | >=9.0.0 | >=9.0.3 | Patch | dev |
| #1688 | pytest-cov | >=7.0.0 | >=7.1.0 | Minor | dev |
| #1695 | freezegun | >=1.4.0 | >=1.5.5 | Minor | dev |
| #1694 | pip-audit | >=2.9.0 | >=2.10.0 | Minor | dev |
| #1697 | mutmut | >=3.2.0 | >=3.5.0 | Minor | dev |
| #1690 | bandit | >=1.8.0 | >=1.9.4 | Minor | dev |
| #1692 | pynacl | >=1.5.0 | >=1.6.2 | Minor | runtime |
| #1696 | uvicorn | >=0.42.0 | >=0.44.0 | Minor | runtime |
| #1698 | agent-framework-core | >=1.0.0b1 | >=1.0.1 | Minor (beta→stable) | runtime |
| #1693 | pytest-randomly | >=3.16.0 | >=4.0.1 | **Major** | dev |

**Alternatives considered**: None — Dependabot provides the canonical dependency update source.

---

## R2: Overlap and Conflict Analysis

**Decision**: No overlapping version constraints detected among the 14 PRs.

**Rationale**: Each PR targets a distinct package. No two PRs modify the same transitive dependency or share version constraint boundaries. The frontend PRs modify `package.json`; the backend PRs modify `pyproject.toml`. The two ecosystems are independent and do not interact.

**Risk areas**:
- `agent-framework-core` (PR #1698): Moving from beta (`1.0.0b1`) to stable (`1.0.1`) may change API surface. Requires changelog inspection.
- `pytest-randomly` (PR #1693): Major version bump (`3.x → 4.x`). May have breaking changes to configuration or plugin API.
- `uvicorn` (PR #1696): Minor bump but runtime dependency — must verify server startup behavior.

**Alternatives considered**: Grouping PRs by shared transitive dependencies — not applicable here since all updates are independent.

---

## R3: Build and Test Commands

**Decision**: Use existing project tooling for verification.

**Rationale**: Both ecosystems have well-defined build and test pipelines already configured.

### Frontend Verification

```bash
cd solune/frontend
npm install          # Regenerates package-lock.json
npm run lint         # ESLint
npm run type-check   # TypeScript compiler
npm run test         # Vitest unit tests
npm run build        # Production build (tsc + vite)
```

### Backend Verification

```bash
cd solune/backend
uv sync --locked --extra dev    # Install with lock file
uv run ruff check src/ tests/   # Linter
uv run ruff format --check src/ tests/  # Formatter
uv run pyright src/              # Type checker
uv run pytest tests/unit/ -q    # Unit tests
```

**Note**: Backend uses `uv` package manager. Lock file is `uv.lock`. After modifying `pyproject.toml`, run `uv lock` to regenerate the lock file, then `uv sync --extra dev` to install.

**Alternatives considered**: Running only tests without lint/type-check — rejected because type errors could indicate breaking API changes.

---

## R4: pytest-randomly 3.x → 4.x Migration Analysis

**Decision**: Apply with caution — inspect changelog for breaking changes.

**Rationale**: Major version bumps warrant extra scrutiny. The `pytest-randomly` plugin controls test execution order randomization. A major bump could change:
- Configuration options in `pyproject.toml`
- Plugin hook signatures
- Default randomization behavior
- Compatibility with other pytest plugins

**Verification approach**: Apply the version change, run `uv lock`, `uv sync --extra dev`, then run the full test suite. If tests pass, the major bump is safe. If they fail with plugin errors, skip and document.

**Alternatives considered**: Pinning to latest 3.x — rejected because 4.x may contain important improvements, and the goal is to apply all safe updates.

---

## R5: agent-framework-core Beta → Stable Migration

**Decision**: Apply with changelog review — beta-to-stable transitions often stabilize APIs.

**Rationale**: The `agent-framework-core` package is moving from `1.0.0b1` (beta) to `1.0.1` (stable). This is generally a positive transition:
- Beta APIs become stable
- Bug fixes accumulated during beta period are included
- The stable release typically maintains backward compatibility with the last beta

**Risk**: If the beta API was experimental and changed significantly before stable release, imports or method signatures may break. The backend uses this package in `services/` for agent orchestration.

**Verification approach**: Apply the change, rebuild, run type checker (pyright), and run full test suite. Type errors or import failures would immediately surface breaking changes.

**Alternatives considered**: Staying on beta — rejected because stable releases are preferred for production dependencies.

---

## R6: Lock File Strategy

**Decision**: Regenerate lock files using ecosystem-native tools after each change.

**Rationale**:
- **Frontend**: `npm install` automatically updates `package-lock.json` when `package.json` changes.
- **Backend**: `uv lock` regenerates `uv.lock` from `pyproject.toml`. Then `uv sync --extra dev` installs the resolved versions.

Manual lock file editing is explicitly prohibited by the issue constraints. Each ecosystem tool handles lock file regeneration safely.

**Alternatives considered**: Editing lock files manually — explicitly prohibited by constraints.

---

## R7: Application Order Strategy

**Decision**: Process updates in the following order:
1. Backend patch bumps (least risk, independent ecosystem)
2. Frontend patch bumps
3. Backend minor bumps (dev dependencies first, then runtime)
4. Frontend minor bumps
5. Backend major bumps (most risk, most scrutiny)

**Rationale**: This order follows the issue's prioritization requirements (patch → minor → major) while also grouping by ecosystem to minimize context switching. Within each tier, dev dependencies are applied before runtime dependencies because dev dependency failures only affect the development workflow, not production behavior.

**Alternatives considered**: Interleaving ecosystems within each tier — rejected for efficiency; grouping by ecosystem reduces the number of install/build cycles.
