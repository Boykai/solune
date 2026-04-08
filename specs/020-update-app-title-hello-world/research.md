# Research: Update App Title to "Hello World"

**Feature**: 020-update-app-title-hello-world | **Date**: 2026-04-08

## R1: Complete Inventory of UI-Visible "Solune" Title References

**Decision**: Three source files contain the app title displayed as a prominent heading/tab title.

**Findings**:

| File | Line | Context | Type |
|------|------|---------|------|
| `solune/frontend/index.html` | 7 | `<title>Solune</title>` | Browser tab title |
| `solune/frontend/src/layout/Sidebar.tsx` | 97 | `Solune` (brand heading in sidebar) | Navbar/header brand |
| `solune/frontend/src/pages/LoginPage.tsx` | 102 | `Solune` (h2 heading on login page) | Login page heading |

**Rationale**: These three locations are the only places where "Solune" appears as a standalone app title/brand heading. All other occurrences are product name references in descriptive prose, comments, or API parameters.

**Alternatives considered**: Changing all "Solune" mentions (60+ occurrences) — rejected as scope creep; the issue targets "app title", not a full product rebrand.

## R2: Test Files Requiring Assertion Updates

**Decision**: Six test files assert the old title text and must be updated.

**Findings**:

| File | Lines | Assertion |
|------|-------|-----------|
| `solune/frontend/src/layout/Sidebar.test.tsx` | 36, 41 | `getByText('Solune')`, `queryByText('Solune')` |
| `solune/frontend/e2e/auth.spec.ts` | 8 | `getByRole('heading', { name: 'Solune' })` |
| `solune/frontend/e2e/ui.spec.ts` | 47, 71 | `toContainText('Solune')` |
| `solune/frontend/e2e/integration.spec.ts` | 82 | `toContainText('Solune')` |
| `solune/frontend/e2e/protected-routes.spec.ts` | 12 | `toContainText('Solune')` |

**Rationale**: These tests verify the visible UI text. Failing to update them would cause test failures after the source change.

**Alternatives considered**: None — test assertions must match the rendered text.

## R3: Excluded "Solune" References (Product Name in Prose)

**Decision**: The following are product name mentions in descriptive/functional text, NOT the app title. They are excluded from this change.

**Findings**:

- **Help page FAQ** (`HelpPage.tsx`): 8 occurrences in answer text (e.g., "Solune will sync your project board")
- **Settings page** (`SettingsPage.tsx:76`): "Configure your preferences for Solune"
- **Onboarding tour** (`SpotlightTour.tsx:29,38,53`): "Welcome to Solune", "Chat with Solune"
- **Login page prose** (`LoginPage.tsx:35`): Descriptive paragraph about Solune
- **API client** (`api.ts:2,973`): JSDoc comment, Signal device name default
- **Clean-up modal** (`CleanUpConfirmModal.tsx:214,486`): "Solune-generated"
- **Chat export** (`monitoring.ts:34`): Markdown header "# Solune Chat Export"
- **App dialogs** (`CreateAppDialog.tsx:511`, `ImportAppDialog.tsx:42`): Feature descriptions
- **Tooltip content** (`tooltip-content.ts:32`): Clean-up tooltip text
- **Test fixtures**: Mock data using "Solune" as project name in `ProjectsPage.test.tsx`, `AgentsPipelinePage.test.tsx`, `ProjectIssueLaunchPanel.test.tsx`, `SavedWorkflowsList.test.tsx`
- **Code comments/JSDoc**: File-level documentation in multiple files
- **Custom event name** (`TopBar.tsx:33`): `solune:open-command-palette` (internal event, not UI text)

**Rationale**: These references describe the product, not the app title. Changing them would be a product rebrand, which is out of scope for issue #1103.

## R4: Implementation Approach

**Decision**: Direct string replacement in 3 source files + assertion updates in 6 test files.

**Rationale**: With only 3 source occurrences of the app title, extracting to a centralized constant (e.g., `APP_TITLE`) would add indirection without meaningful DRY benefit. The occurrences are in different contexts (HTML, React component, login page) and are unlikely to need frequent changes.

**Alternatives considered**:
- Extract `APP_TITLE` constant to `constants.ts` and import everywhere — over-engineering for 3 static strings in a one-time change
- Use environment variable / config — unnecessary complexity for a static display name
