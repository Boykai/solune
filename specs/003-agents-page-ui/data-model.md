# Data Model: Agents Page UI Improvements

## Overview

This feature does not introduce or modify backend/domain entities. The relevant model changes are limited to frontend view-state and layout behavior in the Agents UI.

## Entities

### 1. AgentsSectionVisibility
- **Purpose**: Controls whether a collapsible Agents page section body is visible.
- **Fields**:
  - `sectionKey` (`'pending' | 'catalog' | 'awesomeCatalog'`) — stable identifier for the section.
  - `collapsed` (`boolean`) — whether the section body is hidden.
  - `defaultCollapsed` (`false`) — initial value on first render/page refresh.
- **Validation rules**:
  - Each section maintains its own boolean state.
  - Default value must be `false` for all three sections.
  - Toggling one section must not mutate the others.
- **State transitions**:
  - `expanded -> collapsed` when the header chevron is clicked.
  - `collapsed -> expanded` when the same header chevron is clicked again.

### 2. AgentsPageLoadedLayout
- **Purpose**: Describes the required section order in the loaded state.
- **Fields**:
  - `quickActionsVisible` (`true`) — always rendered.
  - `saveBannerVisible` (`boolean`) — conditional on save results.
  - `pendingChangesVisible` (`boolean`) — conditional on no page error plus pending content/loading.
  - `catalogControlsVisible` (`boolean`) — guarded by `!isLoading && !error && agents?.length > 0`.
  - `awesomeCatalogVisible` (`true`) — always rendered regardless of agent list state.
  - `loadedSectionOrder` (`string[]`) — `['quick-actions', 'save-banner', 'pending-changes', 'catalog-controls', 'awesome-catalog']` when all applicable sections are present.
- **Validation rules**:
  - Catalog Controls must stay inside the existing loaded/non-error/has-agents guard.
  - Awesome Catalog must remain outside that guard.
  - Featured Agents must not appear anywhere in the layout.

### 3. AddAgentModalViewportLayout
- **Purpose**: Defines the scroll/positioning behavior of the Add Agent modal.
- **Fields**:
  - `overlayAlignment` (`'items-start'`) — alignment on the full-screen overlay container.
  - `overlayScrollBehavior` (`'overflow-y-auto'`) — allows scrolling through tall modal content.
  - `dialogVerticalMargin` (`'my-auto'`) — preserves centering for shorter content.
  - `contentHeightMode` (`'short' | 'tall'`) — conceptual rendering mode based on viewport fit.
- **Validation rules**:
  - Tall content must expose the modal top within the overlay scroll area.
  - Short content must continue to appear visually centered.

## Relationships

- `AgentsPageLoadedLayout` contains three independently managed `AgentsSectionVisibility` instances.
- `AddAgentModalViewportLayout` is independent of the page collapse state and only affects modal rendering.
- No backend entities, API payloads, or persistence schemas are affected.
