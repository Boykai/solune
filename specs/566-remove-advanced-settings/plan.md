# Implementation Plan: Remove Advanced Settings from Settings Page

**Branch**: `566-remove-advanced-settings` | **Date**: 2026-04-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/566-remove-advanced-settings/spec.md`

## Summary

Remove the `AdvancedSettings` component and all exclusively-owned sub-components from the Settings page. Edit `SettingsPage.tsx` to drop the AdvancedSettings JSX block and all global-settings-related imports/hooks/handlers. Edit `SettingsPage.test.tsx` to remove the `useGlobalSettings` mock. Delete 11 files that are exclusively owned by AdvancedSettings and its child GlobalSettings component. Update documentation (`docs/pages/settings.md`) to remove the Advanced Settings section.

## Technical Context

**Language/Version**: TypeScript ~6.0.2, React 19.2.0
**Primary Dependencies**: React, TanStack Query, Vitest, Tailwind CSS
**Storage**: N/A (no data model changes — this is a pure UI/component removal)
**Testing**: Vitest (`npm test` in `solune/frontend`)
**Target Platform**: Web browser (SPA)
**Project Type**: Web application (frontend + backend monorepo)
**Performance Goals**: N/A (removal-only change)
**Constraints**: Must not break type checking (`tsc --noEmit`) or existing tests
**Scale/Scope**: 2 files edited, 11 files deleted, 1 doc file updated

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First Development | ✅ PASS | spec.md created with prioritized user stories and GWT acceptance criteria |
| II. Template-Driven Workflow | ✅ PASS | All artifacts follow canonical templates |
| III. Agent-Orchestrated Execution | ✅ PASS | speckit.plan agent producing plan artifacts |
| IV. Test Optionality with Clarity | ✅ PASS | No new tests required — this is a deletion/removal feature. Existing tests are updated to remove dead mocks. |
| V. Simplicity and DRY | ✅ PASS | Pure simplification — removing dead code and unused components |

**Gate Result**: ✅ ALL PASS — no violations, no complexity justification needed.

## Project Structure

### Documentation (this feature)

```text
specs/566-remove-advanced-settings/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── not-applicable.yaml
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
solune/frontend/
├── src/
│   ├── pages/
│   │   ├── SettingsPage.tsx          # EDIT: remove AdvancedSettings usage
│   │   └── SettingsPage.test.tsx     # EDIT: remove useGlobalSettings mock
│   └── components/settings/
│       ├── AdvancedSettings.tsx       # DELETE
│       ├── DisplayPreferences.tsx     # DELETE
│       ├── WorkflowDefaults.tsx       # DELETE
│       ├── NotificationPreferences.tsx # DELETE
│       ├── GlobalSettings.tsx         # DELETE
│       ├── AISettingsSection.tsx       # DELETE
│       ├── DisplaySettings.tsx        # DELETE
│       ├── WorkflowSettings.tsx       # DELETE
│       ├── WorkflowSettings.test.tsx  # DELETE
│       ├── NotificationSettings.tsx   # DELETE
│       └── globalSettingsSchema.ts    # DELETE
│
│   # RETAINED (not exclusively owned):
│       ├── PrimarySettings.tsx        # KEEP
│       ├── SettingsSection.tsx        # KEEP (shared)
│       ├── SettingsSection.test.tsx   # KEEP
│       ├── ProjectSettings.tsx        # KEEP (used by ProjectsPage)
│       ├── DynamicDropdown.tsx        # KEEP (shared)
│       ├── DynamicDropdown.test.tsx   # KEEP
│       ├── McpSettings.tsx            # KEEP
│       ├── McpSettings.test.tsx       # KEEP
│       ├── SignalConnection.tsx       # KEEP
│       └── AIPreferences.tsx          # KEEP
└── ...

solune/docs/pages/
    └── settings.md                    # EDIT: remove Advanced Settings section
```

**Structure Decision**: Web application (Option 2). Changes are frontend-only, affecting `solune/frontend/src/` and `solune/docs/pages/settings.md`.

## Complexity Tracking

> No violations detected — table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none)* | — | — |
