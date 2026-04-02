# Data Model: Remove Advanced Settings from Settings Page

**Feature**: 566-remove-advanced-settings
**Date**: 2026-04-02

## Overview

This feature does not introduce or modify any data models. It is a pure frontend component removal. The underlying data types (`GlobalSettings`, `GlobalSettingsUpdate`, etc.) remain in `types/index.ts` and the backend — they are still used by the API layer and the `useGlobalSettings` hook which is out of scope for deletion.

## Entities

### No New Entities

This feature removes UI components only. No entities are created, modified, or deleted.

### Unchanged Entities (for reference)

The following types remain in the codebase but are no longer referenced from `SettingsPage.tsx`:

| Type | Location | Status |
|------|----------|--------|
| `GlobalSettings` | `frontend/src/types/index.ts` | RETAINED — used by API services and hooks |
| `GlobalSettingsUpdate` | `frontend/src/types/index.ts` | RETAINED — used by API services and hooks |
| `EffectiveUserSettings` | `frontend/src/types/index.ts` | RETAINED — used by SettingsPage (user settings still active) |
| `UserPreferencesUpdate` | `frontend/src/types/index.ts` | RETAINED — used by SettingsPage |

## State Transitions

N/A — no state machines affected by this change.

## Validation Rules

N/A — no validation rules changed. The deleted components' form validation schemas (`globalSettingsSchema.ts`) are removed with the components.
