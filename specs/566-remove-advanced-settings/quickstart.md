# Quickstart: Remove Advanced Settings from Settings Page

**Feature**: 566-remove-advanced-settings
**Date**: 2026-04-02

## Prerequisites

- Node.js and npm installed
- Repository cloned with frontend dependencies installed (`cd solune/frontend && npm install`)

## Implementation Steps

### Phase 1: Edit SettingsPage (blocking — do first)

1. **Edit `solune/frontend/src/pages/SettingsPage.tsx`**:
   - Remove import of `AdvancedSettings` component
   - Remove `useGlobalSettings` from the `useSettings` import (keep `useUserSettings`)
   - Remove `GlobalSettingsUpdate` type import
   - Remove the entire `useGlobalSettings()` hook call and its destructured variables
   - Remove `isGlobalUpdating` from `useUnsavedChangesWarning(isUserUpdating || isGlobalUpdating)` → `useUnsavedChangesWarning(isUserUpdating)`
   - Remove `handleGlobalSave` function
   - Remove `globalLoading` from the loading condition → `if (userLoading)`
   - Remove the global settings loading phase from `CelestialLoadingProgress`
   - Remove the entire `<AdvancedSettings ... />` JSX block
   - Update the docstring to reflect the simplified page

2. **Edit `solune/frontend/src/pages/SettingsPage.test.tsx`**:
   - Remove the `useGlobalSettings` mock from the `vi.mock` block

### Phase 2: Delete files (after Phase 1)

Delete these 11 files:

```bash
cd solune/frontend/src/components/settings

# AdvancedSettings and exclusive children
rm AdvancedSettings.tsx
rm DisplayPreferences.tsx
rm WorkflowDefaults.tsx
rm NotificationPreferences.tsx

# GlobalSettings and exclusive children
rm GlobalSettings.tsx
rm AISettingsSection.tsx
rm DisplaySettings.tsx
rm WorkflowSettings.tsx
rm NotificationSettings.tsx
rm globalSettingsSchema.ts
rm WorkflowSettings.test.tsx
```

### Phase 3: Update documentation

3. **Edit `solune/docs/pages/settings.md`**:
   - Remove the "Advanced Settings" subsection under "What You See"
   - Update any references to the removed functionality

## Verification

```bash
# Type check — must pass with zero errors
cd solune/frontend && npx tsc --noEmit

# Run tests — all must pass
cd solune/frontend && npm test

# Visual check — navigate to /settings, confirm only PrimarySettings renders
cd solune/frontend && npm run dev
# Open http://localhost:5173/settings in browser
```

## Files Changed Summary

| Action | File | Description |
|--------|------|-------------|
| EDIT | `src/pages/SettingsPage.tsx` | Remove AdvancedSettings usage and global settings code |
| EDIT | `src/pages/SettingsPage.test.tsx` | Remove useGlobalSettings mock |
| DELETE | `src/components/settings/AdvancedSettings.tsx` | Collapsible wrapper component |
| DELETE | `src/components/settings/DisplayPreferences.tsx` | User display preferences |
| DELETE | `src/components/settings/WorkflowDefaults.tsx` | User workflow defaults |
| DELETE | `src/components/settings/NotificationPreferences.tsx` | User notification preferences |
| DELETE | `src/components/settings/GlobalSettings.tsx` | Global settings form |
| DELETE | `src/components/settings/AISettingsSection.tsx` | Global AI settings sub-section |
| DELETE | `src/components/settings/DisplaySettings.tsx` | Global display settings sub-section |
| DELETE | `src/components/settings/WorkflowSettings.tsx` | Global workflow settings sub-section |
| DELETE | `src/components/settings/NotificationSettings.tsx` | Global notification settings sub-section |
| DELETE | `src/components/settings/globalSettingsSchema.ts` | Zod schema for global settings form |
| DELETE | `src/components/settings/WorkflowSettings.test.tsx` | Tests for deleted WorkflowSettings |
| EDIT | `docs/pages/settings.md` | Remove Advanced Settings documentation |
