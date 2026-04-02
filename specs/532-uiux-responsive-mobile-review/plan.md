# Implementation Plan: UI/UX Responsive & Mobile Review

**Branch**: `532-uiux-responsive-mobile-review` | **Date**: 2026-04-02 | **Spec**: Parent issue #531
**Input**: Parent issue #531 — Systematic responsive & mobile audit of Solune frontend

## Summary

Systematic audit and fix of all Solune frontend surfaces for responsive, mobile-friendly design. The codebase audit identified 1 high-severity gap (virtual keyboard overlap in ChatPopup), 6 medium-severity issues (fixed widths on mobile previews, settings padding, notification dropdown width, board column heights, pipeline stage sizing, touch target undersizing), and 12+ low-severity cosmetic issues across board, chat, pipeline, settings, and shared layout components. The existing foundation (Tailwind v4.2, shadcn/ui, celestial theme, dark mode, `useMediaQuery` hook, 3 responsive E2E test files) is solid — this plan targets concrete gaps using only existing patterns: Tailwind responsive prefixes and the `useMediaQuery` hook. No new libraries required.

## Technical Context

**Language/Version**: TypeScript ~6.0.2, React 19.2.0
**Primary Dependencies**: Tailwind CSS ^4.2.0, @radix-ui (popover, tooltip, hover-card), @dnd-kit (core ^6.3.1, sortable ^10.0.0), class-variance-authority ^0.7.1, tailwind-merge ^3.5.0, lucide-react ^1.7.0
**Storage**: N/A (frontend-only scope)
**Testing**: Playwright ^1.58.2 (E2E), @testing-library/react ^16.3.2 (unit), Vitest (runner), @axe-core/playwright ^4.10.1 (a11y)
**Target Platform**: Web — all modern browsers, mobile Safari/Chrome at 375px–1280px
**Project Type**: Web application — frontend only (backend out of scope)
**Performance Goals**: Lighthouse mobile ≥ 90 Performance, ≥ 95 Accessibility on /, /projects, /pipeline, /settings
**Constraints**: No horizontal overflow at 375px; all interactive elements ≥ 44×44px on mobile; virtual keyboard must not obscure chat input; prefers-reduced-motion respected
**Scale/Scope**: ~30 component files, ~13 modals, 5 major page surfaces, 3→7 E2E test files, 3→5 viewport definitions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | Parent issue #531 serves as detailed specification with phased requirements, acceptance criteria, and clear scope |
| II. Template-Driven Workflow | ✅ PASS | Using canonical plan-template.md; all artifacts follow prescribed structure |
| III. Agent-Orchestrated Execution | ✅ PASS | speckit.plan agent produces plan.md, research.md, data-model.md, quickstart.md, contracts/ |
| IV. Test Optionality | ✅ PASS | Tests explicitly requested in Phase 5 of the specification; E2E responsive test expansion is in scope |
| V. Simplicity and DRY | ✅ PASS | Reuses existing patterns (useMediaQuery, Tailwind prefixes); no new libraries; z-index centralization reduces duplication |
| Branch Naming | ✅ PASS | `532-uiux-responsive-mobile-review` follows `###-short-name` pattern |
| Phase-Based Execution | ✅ PASS | Plan phase produces required artifacts; tasks phase follows separately |

**Gate Result**: ✅ ALL GATES PASS — proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/532-uiux-responsive-mobile-review/
├── plan.md              # This file
├── research.md          # Phase 0: Technology decisions, z-index strategy, keyboard handling research
├── data-model.md        # Phase 1: Component audit matrix and responsive breakpoint model
├── quickstart.md        # Phase 1: Developer quick-reference for applying responsive fixes
├── contracts/           # Phase 1: Responsive behavior contracts per component
│   └── responsive-behavior.md
└── tasks.md             # Phase 2 output (NOT created by speckit.plan)
```

### Source Code (repository root)

```text
solune/frontend/
├── src/
│   ├── index.css                              # z-index centralization in @theme block
│   ├── hooks/
│   │   └── useMediaQuery.ts                   # Existing responsive hook (no changes needed)
│   ├── layout/
│   │   ├── Sidebar.tsx                        # Mobile overlay: aria-modal, focus trap audit
│   │   ├── TopBar.tsx                         # Help button touch target 36→44px
│   │   ├── Breadcrumb.tsx                     # Truncation + overflow handling
│   │   ├── NotificationBell.tsx               # Viewport-aware panel width, z-index token
│   │   └── RateLimitBar.tsx                   # Verify no content push below fold
│   ├── components/
│   │   ├── board/
│   │   │   ├── BoardColumn.tsx                # md: breakpoint for mobile column height
│   │   │   ├── BoardColumnSkeleton.tsx        # Match BoardColumn responsive heights
│   │   │   ├── ProjectBoard.tsx               # Mobile grid width, scroll-snap, scroll affordance
│   │   │   └── IssueCard.tsx                  # Truncation + drag handle audit
│   │   ├── chat/
│   │   │   ├── ChatPopup.tsx                  # 🔴 Virtual keyboard fix, mobile size constants
│   │   │   ├── ChatInterface.tsx              # History popover mobile positioning
│   │   │   ├── ChatToolbar.tsx                # Button sizes 32→44px on mobile
│   │   │   ├── MentionInput.tsx               # inputMode="text" attribute
│   │   │   ├── TaskPreview.tsx                # max-w-[90vw] md:max-w-[500px]
│   │   │   └── PlanPreview.tsx                # max-w-[90vw] md:max-w-[600px]
│   │   ├── command-palette/
│   │   │   └── CommandPalette.tsx             # Mobile full-width usability audit
│   │   ├── pipeline/
│   │   │   ├── PipelineBoard.tsx              # Stage min-width 12rem on mobile, font scaling
│   │   │   └── PipelineFlowGraph.tsx          # Touch scroll/zoom audit at 375px
│   │   ├── agents/
│   │   │   └── AgentsPanel.tsx                # Card reflow single-column audit
│   │   ├── chores/
│   │   │   └── ChoresGrid.tsx                 # Gap scaling audit
│   │   └── [13 modal components]              # max-h-[85vh], tap-dismiss, full-width inputs
│   └── pages/
│       ├── SettingsPage.tsx                   # p-4 md:p-8 responsive padding
│       ├── ActivityPage.tsx                   # Timeline readability audit
│       └── HelpPage.tsx                       # FAQ accordion overflow audit
└── e2e/
    ├── viewports.ts                           # Add iPhone XR (414×896), iPad Air (820×1180)
    ├── responsive-board.spec.ts               # Expand: scroll affordance, scroll-snap assertions
    ├── responsive-home.spec.ts                # Expand: sidebar collapse, touch targets
    ├── responsive-settings.spec.ts            # Expand: modal scrollability, padding
    ├── responsive-pipeline.spec.ts            # NEW: pipeline responsive tests
    ├── responsive-agents.spec.ts              # NEW: agents panel responsive tests
    ├── responsive-chores.spec.ts              # NEW: chores grid responsive tests
    └── responsive-chat.spec.ts                # NEW: chat responsive + keyboard tests
```

**Structure Decision**: Frontend-only modification within existing `solune/frontend/` structure. All changes are to existing files (CSS class modifications, attribute additions) or new E2E test files. No new directories, packages, or architectural changes required.

## Complexity Tracking

No constitution violations to justify. All changes use existing patterns:
- Tailwind responsive prefixes (`sm:`, `md:`, `lg:`, `xl:`)
- Existing `useMediaQuery` hook for JS-level responsive behavior
- Existing E2E test infrastructure with `VIEWPORTS` constant
- Existing `@theme` block in index.css for centralized tokens
