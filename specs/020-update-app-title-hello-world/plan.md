# Implementation Plan: Update App Title to "Hello World"

**Branch**: `copilot/update-app-title-hello-world` | **Date**: 2026-04-08 | **Spec**: [#1103](https://github.com/Boykai/solune/issues/1103)
**Input**: Parent issue #1103 — Update app title to "Hello World"

## Summary

Replace the Solune app title/brand name with "Hello World" across all UI-visible title locations: the HTML `<title>` tag (browser tab), the sidebar brand heading, and the login page heading. Update corresponding unit tests and e2e tests that assert the old title text.

## Technical Context

**Language/Version**: TypeScript 6.0 (frontend only)
**Primary Dependencies**: React 19.2.0, Vite, Vitest, Playwright (e2e)
**Storage**: N/A — no data layer changes
**Testing**: Vitest + Testing Library (unit), Playwright (e2e)
**Target Platform**: Modern browsers (frontend SPA)
**Project Type**: Web application (frontend monorepo under `solune/frontend/`)
**Performance Goals**: N/A — static text change, no runtime impact
**Constraints**: No breaking changes to non-title functionality; all existing tests must pass after title text updates
**Scale/Scope**: 3 source files, 2 unit test files, 4 e2e test files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Parent issue #1103 provides clear requirements with explicit file targets and acceptance criteria |
| II. Template-Driven Workflow | ✅ PASS | Using canonical plan template; artifacts in `specs/020-update-app-title-hello-world/` |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan phase produces plan.md, research.md, data-model.md, quickstart.md; handoff to tasks phase |
| IV. Test Optionality | ✅ PASS | No new tests needed; existing tests updated to match new title text |
| V. Simplicity and DRY | ✅ PASS | Direct string replacement — the simplest possible approach; no abstraction needed for 3 occurrences |

**Gate Result**: ✅ ALL PASS — proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/020-update-app-title-hello-world/
├── plan.md              # This file
├── research.md          # Phase 0: title reference inventory
├── data-model.md        # Phase 1: change map (source → target)
├── quickstart.md        # Phase 1: step-by-step verification guide
├── contracts/
│   └── title-changes.md # Contract for all title text replacements
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
solune/frontend/
├── index.html                                  # <title> tag: "Solune" → "Hello World"
├── src/
│   ├── layout/
│   │   ├── Sidebar.tsx                         # Brand heading: "Solune" → "Hello World"
│   │   └── Sidebar.test.tsx                    # Test assertions: "Solune" → "Hello World"
│   └── pages/
│       ├── LoginPage.tsx                       # Login heading: "Solune" → "Hello World"
│       └── LoginPage.test.tsx                  # Test description references (if asserting title)
├── e2e/
│   ├── auth.spec.ts                            # heading assertion: "Solune" → "Hello World"
│   ├── ui.spec.ts                              # h2 text assertion: "Solune" → "Hello World"
│   ├── integration.spec.ts                     # h2 text assertion: "Solune" → "Hello World"
│   └── protected-routes.spec.ts                # h2 text assertion: "Solune" → "Hello World"
```

**Structure Decision**: Web application (Option 2). This feature modifies only frontend source and test files — no new directories or dependencies.

## Execution Phases

### Phase 1 — Source Code: Update UI-Visible Title (CRITICAL)

| Step | Target | Change | Line |
|------|--------|--------|------|
| 1.1 | `solune/frontend/index.html` | `<title>Solune</title>` → `<title>Hello World</title>` | 7 |
| 1.2 | `solune/frontend/src/layout/Sidebar.tsx` | Brand text `Solune` → `Hello World` | 97 |
| 1.3 | `solune/frontend/src/pages/LoginPage.tsx` | Heading text `Solune` → `Hello World` | 102 |

### Phase 2 — Unit Tests: Update Assertions (HIGH)

| Step | Target | Change | Lines |
|------|--------|--------|-------|
| 2.1 | `solune/frontend/src/layout/Sidebar.test.tsx` | `getByText('Solune')` → `getByText('Hello World')` | 36 |
| 2.2 | `solune/frontend/src/layout/Sidebar.test.tsx` | `queryByText('Solune')` → `queryByText('Hello World')` | 41 |

### Phase 3 — E2E Tests: Update Assertions (HIGH)

| Step | Target | Change | Line |
|------|--------|--------|------|
| 3.1 | `solune/frontend/e2e/auth.spec.ts` | `heading 'Solune'` → `heading 'Hello World'` | 8 |
| 3.2 | `solune/frontend/e2e/ui.spec.ts` | `toContainText('Solune')` → `toContainText('Hello World')` | 47, 71 |
| 3.3 | `solune/frontend/e2e/integration.spec.ts` | `toContainText('Solune')` → `toContainText('Hello World')` | 82 |
| 3.4 | `solune/frontend/e2e/protected-routes.spec.ts` | `toContainText('Solune')` → `toContainText('Hello World')` | 12 |

### Phase 4 — Verification

| Step | Verification | Expected |
|------|-------------|----------|
| 4.1 | Frontend unit tests: `npx vitest run` | All pass (Sidebar.test.tsx assertions match new title) |
| 4.2 | Visual check: `<title>` in index.html | "Hello World" |
| 4.3 | Visual check: Sidebar brand text | "Hello World" |
| 4.4 | Visual check: Login page heading | "Hello World" |
| 4.5 | No remaining UI-visible "Solune" as app title | Confirmed via grep |

### Out of Scope

The following references to "Solune" are **product name mentions** in descriptive text, NOT the app title, and are explicitly excluded from this change:

- Help page FAQ answers (e.g., "Solune will sync your project board")
- Settings page description ("Configure your preferences for Solune")
- Onboarding tour steps ("Welcome to Solune", "Chat with Solune")
- API service comments and JSDoc
- Signal device name default (`deviceName = 'Solune'`)
- Clean-up modal text ("Solune-generated branches")
- Chat export header ("# Solune Chat Export")
- Create/Import app dialog text
- Test fixture mock data using "Solune" as sample project names

## Design Decisions

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| Direct string replacement (no centralized constant) | Only 3 source occurrences; a constant adds indirection without DRY benefit | Extract to constant: over-engineering for 3 static strings |
| Update e2e test assertions to match new title | E2e tests verify visible UI; must reflect actual displayed text | Skip e2e updates: tests would fail |
| Exclude product-name-in-prose references | Issue scope is "app title", not product name rebrand; prose references describe the product, not the title bar/header | Change all mentions: scope creep, different concern |

## Constitution Re-Check (Post Phase 1 Design)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Issue #1103 with clear acceptance criteria |
| II. Template-Driven Workflow | ✅ PASS | All artifacts follow canonical templates |
| III. Agent-Orchestrated Execution | ✅ PASS | Single-responsibility plan phase output |
| IV. Test Optionality | ✅ PASS | No new tests — existing tests updated to match changed text |
| V. Simplicity and DRY | ✅ PASS | Direct string replacement is the simplest correct approach |

**Gate Result**: ✅ ALL PASS — proceed to tasks phase

## Complexity Tracking

> No violations — this is a straightforward text replacement with no architectural complexity.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | — | — |
