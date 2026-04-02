# Feature Specification: Remove Advanced Settings from Settings Page

**Issue**: [#566](https://github.com/Boykai/solune/issues/566)
**Branch**: `566-remove-advanced-settings`
**Date**: 2026-04-02

## Summary

Remove the `AdvancedSettings` component and all exclusively-owned sub-components from the Settings page. Delete the corresponding source files. The Settings page should render only `PrimarySettings` after this change.

## User Stories

### P1: Remove AdvancedSettings from SettingsPage

**As a** developer maintaining the Solune frontend,
**I want** the AdvancedSettings component and all global-settings-related code removed from SettingsPage,
**So that** the settings page is simplified and no longer references unused functionality.

**Acceptance Criteria (Given-When-Then):**

- **Given** the SettingsPage component,
  **When** it renders,
  **Then** only PrimarySettings is displayed (no AdvancedSettings block).

- **Given** the SettingsPage component,
  **When** the `useGlobalSettings` hook, `GlobalSettingsUpdate` type, `handleGlobalSave`, and `isGlobalUpdating` references are searched,
  **Then** none exist in SettingsPage.tsx.

- **Given** the SettingsPage test file,
  **When** it runs,
  **Then** it no longer mocks `useGlobalSettings`.

**Independent Test**: Navigate to `/settings` in dev mode — only PrimarySettings renders, no console errors.

### P2: Delete exclusively-owned component files

**As a** developer maintaining the Solune frontend,
**I want** all files exclusively owned by AdvancedSettings and GlobalSettings deleted,
**So that** dead code is removed from the repository.

**Acceptance Criteria (Given-When-Then):**

- **Given** the following 11 files exist before the change:
  1. `src/components/settings/AdvancedSettings.tsx`
  2. `src/components/settings/DisplayPreferences.tsx`
  3. `src/components/settings/WorkflowDefaults.tsx`
  4. `src/components/settings/NotificationPreferences.tsx`
  5. `src/components/settings/GlobalSettings.tsx`
  6. `src/components/settings/AISettingsSection.tsx`
  7. `src/components/settings/DisplaySettings.tsx`
  8. `src/components/settings/WorkflowSettings.tsx`
  9. `src/components/settings/NotificationSettings.tsx`
  10. `src/components/settings/globalSettingsSchema.ts`
  11. `src/components/settings/WorkflowSettings.test.tsx`
  **When** the deletion is complete,
  **Then** none of those 11 files exist on disk.

- **Given** the remaining files in `src/components/settings/`,
  **When** `npx tsc --noEmit` runs,
  **Then** there are zero type errors.

- **Given** the remaining test files,
  **When** `npm test` runs,
  **Then** all tests pass.

**Independent Test**: `ls src/components/settings/` shows only the retained files (PrimarySettings, SettingsSection, ProjectSettings, DynamicDropdown, McpSettings, SignalConnection, AIPreferences, and their tests).

## Scope Boundaries

### In Scope
- Editing `SettingsPage.tsx` to remove AdvancedSettings usage and global settings code
- Editing `SettingsPage.test.tsx` to remove `useGlobalSettings` mock
- Deleting 11 exclusively-owned files
- Updating `docs/pages/settings.md` to remove Advanced Settings documentation

### Out of Scope
- Removing `useGlobalSettings` from `useSettings.ts` hook (still exported, may have other consumers)
- Removing `GlobalSettingsUpdate` or `GlobalSettings` types from `types/index.ts` (used by API layer)
- Backend API changes
- Removing `ProjectSettings.tsx` (used by `ProjectsPage.tsx`)
- Removing shared components (`SettingsSection`, `DynamicDropdown`, etc.)
