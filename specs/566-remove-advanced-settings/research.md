# Research: Remove Advanced Settings from Settings Page

**Feature**: 566-remove-advanced-settings
**Date**: 2026-04-02

## Overview

This is a code removal/deletion feature. Research focused on verifying component ownership and confirming safe deletion boundaries.

## Research Tasks

### R1: Identify exclusively-owned components of AdvancedSettings

**Decision**: The following 4 components are exclusively imported by `AdvancedSettings.tsx` and are safe to delete:
- `DisplayPreferences.tsx`
- `WorkflowDefaults.tsx`
- `NotificationPreferences.tsx`
- `GlobalSettings.tsx`

**Rationale**: Grep across the entire frontend codebase confirms these components are imported only in `AdvancedSettings.tsx`. No barrel exports or re-exports exist.

**Alternatives considered**: Keeping components in case of future use — rejected because dead code increases maintenance burden and YAGNI principle applies.

### R2: Identify exclusively-owned sub-components of GlobalSettings

**Decision**: The following 6 files are exclusively owned by `GlobalSettings.tsx` and are safe to delete:
- `AISettingsSection.tsx`
- `DisplaySettings.tsx`
- `WorkflowSettings.tsx`
- `NotificationSettings.tsx`
- `globalSettingsSchema.ts`
- `WorkflowSettings.test.tsx`

**Rationale**: Grep confirms these are imported only by `GlobalSettings.tsx` (or its own test file). Once `GlobalSettings.tsx` is deleted, these become unreachable.

**Alternatives considered**: None — transitive ownership is clear.

### R3: Verify shared components are NOT deleted

**Decision**: The following components must NOT be deleted:
- `ProjectSettings.tsx` — also imported by `ProjectsPage.tsx`
- `SettingsSection.tsx` — shared reusable wrapper used by PrimarySettings, McpSettings, and other retained components
- `DynamicDropdown.tsx` — shared utility component
- `useGlobalSettings` hook in `useSettings.ts` — still exported and used by its own module; removal is out of scope

**Rationale**: Confirmed via codebase-wide import search. Deleting these would break other pages/components.

**Alternatives considered**: N/A — these are clearly still referenced.

### R4: SettingsPage.tsx edit requirements

**Decision**: Remove the following from `SettingsPage.tsx`:
1. Import of `AdvancedSettings` component
2. Import of `useGlobalSettings` from hooks — keep only `useUserSettings`
3. Import of `GlobalSettingsUpdate` type
4. The entire `useGlobalSettings()` hook call and destructuring
5. `isGlobalUpdating` from the `useUnsavedChangesWarning` call
6. `handleGlobalSave` function
7. The `<AdvancedSettings>` JSX block
8. The `globalLoading` check in the loading condition
9. The loading phase for global settings in `CelestialLoadingProgress`

**Rationale**: These are all the references to global settings and AdvancedSettings within SettingsPage.tsx. Removing them cleanly separates the page from the deleted components.

**Alternatives considered**: Keeping `useGlobalSettings` import for future use — rejected per YAGNI.

### R5: SettingsPage.test.tsx edit requirements

**Decision**: Remove the `useGlobalSettings` mock (lines 14-19) from the test file's `vi.mock` block.

**Rationale**: The mock corresponds to a hook that is no longer called in the component under test.

**Alternatives considered**: None — the mock would reference unused code.

### R6: Documentation updates

**Decision**: Update `solune/docs/pages/settings.md` to remove the "Advanced Settings" section and any references to display, workflow, notification, project, and global settings that are specific to the deleted components.

**Rationale**: Documentation should reflect the current state of the UI.

**Alternatives considered**: Leaving docs unchanged — rejected because stale docs confuse users.

## Summary

All NEEDS CLARIFICATION items have been resolved. No unknowns remain. The feature is a straightforward deletion with well-defined boundaries confirmed by codebase analysis.
