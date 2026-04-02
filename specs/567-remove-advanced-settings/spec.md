# Feature Specification: Remove Advanced Settings from Settings Page

**Feature Branch**: `567-remove-advanced-settings`  
**Created**: 2026-04-02  
**Status**: Draft  
**Input**: User description: "Remove Advanced Settings from Settings Page"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Remove AdvancedSettings from the Settings Page (Priority: P1)

A developer maintaining the Solune frontend removes the AdvancedSettings component and all global-settings-related code from SettingsPage so the page renders only PrimarySettings. After this change, users navigating to the Settings page see only the primary settings (AI Configuration and Signal Connection) with no collapsible "Advanced Settings" panel.

**Why this priority**: This is the blocking first step — all file deletions in Story 2 depend on references being removed from SettingsPage first. It also delivers the core user-visible change.

**Independent Test**: Navigate to the Settings page — only PrimarySettings renders, no Advanced Settings section appears, and there are no console errors or broken references.

**Acceptance Scenarios**:

1. **Given** the Settings page is loaded, **When** a user views the page, **Then** only the PrimarySettings section (AI Configuration and Signal Connection) is displayed.
2. **Given** the SettingsPage source file, **When** searched for references to AdvancedSettings, useGlobalSettings, GlobalSettingsUpdate, handleGlobalSave, or isGlobalUpdating, **Then** none of those references exist.
3. **Given** the SettingsPage test file, **When** tests are executed, **Then** all tests pass without mocking useGlobalSettings.
4. **Given** the unsaved-changes warning feature, **When** only user settings have pending changes, **Then** the warning still functions correctly without relying on global settings state.

---

### User Story 2 - Delete Exclusively-Owned Component Files (Priority: P2)

A developer deletes all source files that are exclusively owned by AdvancedSettings (i.e., not imported or used by any other part of the application). This removes dead code from the repository and reduces maintenance burden.

**Why this priority**: File deletion depends on Story 1 completing first (references removed). Removing dead code reduces cognitive load and prevents confusion about which components are active.

**Independent Test**: Verify the 11 target files no longer exist on disk, the project compiles without errors, and all remaining tests pass.

**Acceptance Scenarios**:

1. **Given** the following 11 files exist before the change:
   - `src/components/settings/AdvancedSettings.tsx`
   - `src/components/settings/DisplayPreferences.tsx`
   - `src/components/settings/WorkflowDefaults.tsx`
   - `src/components/settings/NotificationPreferences.tsx`
   - `src/components/settings/GlobalSettings.tsx`
   - `src/components/settings/AISettingsSection.tsx`
   - `src/components/settings/DisplaySettings.tsx`
   - `src/components/settings/WorkflowSettings.tsx`
   - `src/components/settings/NotificationSettings.tsx`
   - `src/components/settings/globalSettingsSchema.ts`
   - `src/components/settings/WorkflowSettings.test.tsx`

   **When** the deletion is complete, **Then** none of those 11 files exist on disk.

2. **Given** the remaining settings component files, **When** the project is type-checked, **Then** there are zero type errors.
3. **Given** the full test suite, **When** tests are run, **Then** all tests pass with no failures related to missing components.

---

### User Story 3 - Update Settings Page Documentation (Priority: P3)

A developer updates the settings documentation to reflect the removal of the Advanced Settings section, ensuring that documentation accurately describes the current Settings page layout.

**Why this priority**: Documentation accuracy is important but non-blocking. The page functions correctly without this update, but stale documentation causes confusion for future contributors.

**Independent Test**: Review the settings documentation page and confirm it describes only PrimarySettings with no mention of Advanced Settings, Display Preferences, Workflow Defaults, Notification Preferences, or Global Settings sections.

**Acceptance Scenarios**:

1. **Given** the settings documentation file, **When** it is reviewed after the change, **Then** it describes only the PrimarySettings section (AI Configuration and Signal Connection).
2. **Given** the settings documentation file, **When** searched for references to "Advanced Settings," "Display Preferences," "Workflow Defaults," "Notification Preferences," or "Global Settings," **Then** none of those references exist.

---

### Edge Cases

- What happens if a shared component (e.g., SettingsSection, DynamicDropdown) is only rendered inside AdvancedSettings? Verify it is still used elsewhere before deciding to keep it.
- What happens if the useGlobalSettings hook or GlobalSettingsUpdate type is imported by files outside of SettingsPage? Those external references must remain untouched.
- What happens if ProjectSettings is mistakenly deleted? It must be preserved because it is also used by ProjectsPage.
- What happens if the unsaved-changes warning breaks after removing isGlobalUpdating from its inputs? The warning logic must still function for user settings alone.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Settings page MUST render only PrimarySettings (AI Configuration and Signal Connection) with no AdvancedSettings panel.
- **FR-002**: The SettingsPage source file MUST NOT contain any imports or references to AdvancedSettings, useGlobalSettings, GlobalSettingsUpdate, handleGlobalSave, or isGlobalUpdating.
- **FR-003**: The unsaved-changes warning on the Settings page MUST continue to function correctly using only user settings state.
- **FR-004**: All 11 exclusively-owned files (listed in Story 2) MUST be deleted from the repository.
- **FR-005**: The project MUST compile without type errors after all removals and deletions.
- **FR-006**: All existing tests MUST pass after the changes, with test mocks for useGlobalSettings removed from SettingsPage tests.
- **FR-007**: The settings documentation MUST be updated to reflect only PrimarySettings content.
- **FR-008**: Shared components (SettingsSection, DynamicDropdown, SignalConnection, AIPreferences, McpSettings) and their tests MUST NOT be deleted.
- **FR-009**: ProjectSettings MUST NOT be deleted (it is used by ProjectsPage).
- **FR-010**: The useGlobalSettings hook definition in the hooks file and its dedicated tests MUST NOT be removed (they may have other consumers outside the Settings page).

### Assumptions

- The useGlobalSettings hook and GlobalSettingsUpdate type may be used by other parts of the application (e.g., API layer), so they are preserved in the hooks and types files.
- ProjectSettings is confirmed to be used by ProjectsPage and is therefore out of scope for deletion.
- No backend changes are required — this is a frontend-only change.
- The 11 files listed for deletion are exclusively owned by the AdvancedSettings component chain and have no other consumers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The Settings page loads successfully with only PrimarySettings visible and zero console errors.
- **SC-002**: The total number of files in the settings component directory is reduced by 11.
- **SC-003**: 100% of existing tests pass after the changes (excluding tests in deleted files).
- **SC-004**: The project compiles with zero type errors after all changes.
- **SC-005**: The settings documentation accurately reflects the simplified page layout with no stale references to removed features.
