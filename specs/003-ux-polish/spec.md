# Feature Specification: UX Fixes — Scrolling, Agents Page, Chat Streaming, Auto Model

**Feature Branch**: `003-ux-polish`  
**Created**: 2026-04-05  
**Status**: Draft  
**Input**: User description: "UX Fixes — Scrolling, Agents Page, Chat Streaming, Auto Model"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Smooth Single-Scroll Page Navigation (Priority: P1)

A user navigates between pages in Solune (Settings, Agents, Chores, Tools). Every page scrolls from a single, predictable scroll container — the application shell. There are no competing scroll bars, no "stuck" scrollable regions, and no clipped content. When the user navigates to a new page, the view automatically scrolls to the top so they always see the beginning of the page content. The experience feels native and consistent regardless of which page the user is on.

**Why this priority**: Broken scrolling is the most immediately visible UX defect. Users cannot reach content, see duplicate scrollbars, and lose their place on navigation. Fixing this unblocks comfortable use of every page in the application.

**Independent Test**: Navigate to each page (Settings, Agents, Agents Pipeline, Chores, Tools) and scroll to the bottom. Verify exactly one scrollbar is visible, all content is reachable, and no content is clipped. Navigate away and back — verify the page starts at the top.

**Acceptance Scenarios**:

1. **Given** the user is on the Settings page, **When** they scroll down, **Then** exactly one scrollbar is visible and all page content is reachable without a nested inner scrollbar
2. **Given** the user is on any page and has scrolled down, **When** they navigate to a different page via the sidebar, **Then** the new page is displayed starting from the top
3. **Given** the user is on the Agents page, **When** they scroll the page, **Then** the page scrolls within the application shell's single scroll container — no competing inner scroll regions exist
4. **Given** the user is on the Chores or Tools page, **When** they view the page, **Then** no page-level containers have their own scroll behavior; all scrolling is handled by the application shell

---

### User Story 2 - Inline Agent Catalog Browsing (Priority: P1)

A user wants to discover and import new agents. Instead of opening a separate modal that blocks the page, they scroll down the Agents page to find an inline "Browse Catalog" section with tile cards. They can search the catalog, see which agents are already imported (marked with a badge), and import new agents with a single click — all without leaving the page context or losing their scroll position.

**Why this priority**: The modal-based browse experience interrupts the user's workflow and creates a context switch. An inline catalog section keeps the user in flow, makes agent discovery feel like natural page exploration, and eliminates the scroll/focus issues associated with modal overlays.

**Independent Test**: Open the Agents page. Scroll past the current agents list to the Browse Catalog section. Search for an agent by name. Import an unimported agent and verify the badge updates to "Imported ✓". Confirm no modal or overlay appears at any point.

**Acceptance Scenarios**:

1. **Given** the user is on the Agents page, **When** they scroll past the current agents section, **Then** an inline "Browse Catalog" section is visible with tile cards matching the existing agent card styling
2. **Given** the Browse Catalog section is visible, **When** the user types in the search filter, **Then** the catalog tiles filter in real time to show matching agents
3. **Given** a catalog agent is not yet imported, **When** the user clicks the "Import" button on that agent's tile, **Then** the agent is imported and the button changes to an "Imported ✓" badge
4. **Given** the user is on the Agents page, **When** they look for a "Browse Agents" button or modal trigger, **Then** no such modal trigger exists — all browsing is done inline

---

### User Story 3 - Correct Agents Page Labels (Priority: P2)

A user visits the Agents page and sees labels that accurately describe the content. The refresh button says "Refresh agents" (not "Refresh models"), and the catalog heading reads "Current agents" with a descriptive subtitle. The language is consistent and avoids confusing terminology that mixes "models" with "agents."

**Why this priority**: Incorrect labels create confusion about what the user is interacting with. Fixing label accuracy is low-effort but high-impact for reducing user cognitive load and building trust in the interface.

**Independent Test**: Open the Agents page. Verify the refresh button text is "Refresh agents." Verify the catalog section heading reads "Current agents" and the subtitle reads "Stars of the constellation."

**Acceptance Scenarios**:

1. **Given** the user is on the Agents page, **When** they look at the refresh button, **Then** the button text reads "Refresh agents" (not "Refresh models")
2. **Given** the user is on the Agents page, **When** they view the catalog section heading, **Then** the heading reads "Current agents" and the subtitle reads "Stars of the constellation"

---

### User Story 4 - Real-Time Chat Streaming Display (Priority: P2)

A user sends a message in the chat. Their message appears instantly (optimistic display). The AI assistant's response then streams in token by token — the user sees a live, growing assistant message bubble rather than a loading indicator followed by a full message. This gives the user immediate feedback that the system is working and lets them start reading the response before it finishes generating.

**Why this priority**: Streaming display is a core chat UX expectation. Users familiar with ChatGPT, Copilot Chat, and similar tools expect to see tokens appear progressively. A loading spinner followed by a wall of text feels slow and unresponsive, even if the total wait time is the same.

**Independent Test**: Send a message in the chat. Verify the user message appears immediately. Verify the assistant response appears as a growing text bubble with tokens streaming in progressively. Verify no bouncing dots or static loading indicator is shown during streaming.

**Acceptance Scenarios**:

1. **Given** the user types a message and sends it, **When** the message is submitted, **Then** the user message appears immediately in the chat without waiting for a server response
2. **Given** an AI response is being generated, **When** streaming tokens arrive from the backend, **Then** a live assistant message bubble grows in real time as each token is appended
3. **Given** the AI response is streaming, **When** the user observes the chat, **Then** they see progressive text appearing (not a loading spinner or bouncing dots)
4. **Given** the streaming response completes, **When** all tokens have been received, **Then** the streaming bubble transitions seamlessly to a final assistant message with no visual glitch or duplicate content

---

### User Story 5 - Reliable Scroll Lock for Modals and Overlays (Priority: P3)

A user triggers a summary overlay (e.g., the clean-up summary). The background page scroll is locked so the user cannot accidentally scroll the page behind the overlay. When the overlay is dismissed — whether by user action or component unmount — the scroll lock is released immediately and the user can scroll the page normally again. There is never a scenario where the page remains scroll-locked after an overlay is gone.

**Why this priority**: Scroll lock bugs are rare but highly disruptive when they occur. A user who cannot scroll the page must refresh, losing context and trust. This is a preventive fix for an edge case in component unmount timing.

**Independent Test**: Trigger the clean-up summary overlay. Verify the background page cannot scroll. Dismiss the overlay and verify scrolling is restored. Force-unmount the component during loading state and verify scroll is still released.

**Acceptance Scenarios**:

1. **Given** the clean-up summary overlay is displayed, **When** the user attempts to scroll the background page, **Then** the page does not scroll
2. **Given** the clean-up summary overlay is displayed, **When** the overlay is dismissed, **Then** page scrolling is immediately restored
3. **Given** the clean-up summary component unmounts while still in loading state, **When** the component is removed from the DOM, **Then** the scroll lock is released and the page scrolls normally

---

### User Story 6 - Auto Model Resolution (Priority: P3)

A user configures a pipeline and leaves the model selection set to "Auto." The system automatically resolves the correct model without any user intervention using a priority chain: pipeline-configured model, then user settings model, then a sensible system default. The user does not need to understand the resolution logic — they simply see the right model being used.

**Why this priority**: Auto model resolution is already implemented in the backend. This story documents the expected behavior and confirms no additional code changes are needed. It is included for completeness and verification purposes.

**Independent Test**: Create a pipeline with model set to "Auto." Run the pipeline and verify the model used matches the user's settings preference. Remove the user setting and verify the system default is used.

**Acceptance Scenarios**:

1. **Given** a pipeline is configured with model set to "Auto" and the user has a model preference in Settings, **When** the pipeline runs, **Then** the user's settings model is used
2. **Given** a pipeline is configured with model set to "Auto" and the user has no model preference, **When** the pipeline runs, **Then** a sensible system default model is used
3. **Given** a pipeline is configured with a specific model (not "Auto"), **When** the pipeline runs, **Then** the pipeline-configured model is used regardless of user settings

---

### Edge Cases

- What happens when the user rapidly navigates between pages — does scroll-to-top fire reliably for each transition?
- What happens when a streaming response encounters a network error mid-stream — does the partial content remain visible with an error indicator?
- What happens when the user scrolls the Agents page while an agent import is in progress — does the import complete and badge update correctly?
- What happens when the clean-up summary component receives both a result and an error simultaneously — does the scroll lock behave correctly?
- What happens when the Browse Catalog section has zero results matching the search query — is an empty state shown?
- What happens when the user has a very long list of agents — does the inline catalog section remain scrollable within the single scroll container?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The application shell MUST provide exactly one scroll container for page content; no page-level child container may introduce its own scroll behavior
- **FR-002**: When the user navigates to a new route, the application MUST scroll the main content area to the top before displaying the new page
- **FR-003**: The Settings page MUST NOT have nested scroll containers; loading and main content states MUST rely on the application shell for scrolling
- **FR-004**: The Agents, Agents Pipeline, Chores, and Tools pages MUST NOT have page-level overflow-auto or overflow-y-auto on inner containers
- **FR-005**: The Agents page MUST display an inline Browse Catalog section below the current agents list, using the same tile card styling as existing agent cards
- **FR-006**: The Browse Catalog section MUST include a real-time search filter for catalog agents
- **FR-007**: Each catalog agent tile MUST display either an "Import" action or an "Imported ✓" badge based on the agent's import status
- **FR-008**: The modal-based Browse Agents dialog MUST be removed from the Agents page; all browsing MUST happen inline
- **FR-009**: The Agents page refresh button MUST read "Refresh agents" (not "Refresh models")
- **FR-010**: The Agents page catalog heading MUST read "Current agents" with subtitle "Stars of the constellation"
- **FR-011**: When the user sends a chat message, the user's message MUST appear immediately in the conversation without waiting for server acknowledgment
- **FR-012**: AI assistant responses MUST stream token-by-token into a live message bubble that grows progressively as tokens arrive
- **FR-013**: During active streaming, the chat MUST NOT display a static loading indicator (e.g., bouncing dots); the growing message bubble itself serves as the activity indicator
- **FR-014**: When streaming completes, the live bubble MUST transition to a finalized assistant message with no visual duplication or flicker
- **FR-015**: The clean-up summary component MUST lock page scroll unconditionally when rendered and release the lock when unmounted, regardless of loading/error state
- **FR-016**: Model resolution for pipelines MUST follow a three-tier priority: (1) pipeline-configured model, (2) user settings model, (3) system default — with no user intervention required for "Auto" mode

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every page in the application (Settings, Agents, Agents Pipeline, Chores, Tools) displays exactly one scrollbar — zero instances of double-scroll across all pages
- **SC-002**: After navigating between any two pages, the destination page is visible from the top within 100 milliseconds of route change completion
- **SC-003**: Users can discover and import catalog agents entirely inline on the Agents page with zero modal dialogs opened during the browse-and-import workflow
- **SC-004**: User-sent chat messages appear in the conversation within 50 milliseconds of submission (before any server response)
- **SC-005**: AI assistant response tokens are visible to the user within 200 milliseconds of arriving from the backend — no buffering delay before display
- **SC-006**: The streaming message bubble displays content progressively (token by token) for 100% of streamed responses, with no fallback to load-then-display behavior
- **SC-007**: Page scroll is never locked after a modal or overlay has been dismissed — zero instances of orphaned scroll locks across all user flows
- **SC-008**: All label text on the Agents page accurately refers to "agents" (not "models") — zero instances of incorrect terminology
- **SC-009**: Existing automated test suite passes with no regressions introduced by these changes
- **SC-010**: The application builds successfully with no new linting errors or type-check failures

### Assumptions

- The application shell layout (`AppLayout`) already provides a single scroll container at the top level. The fix involves removing competing scroll containers from child pages, not restructuring the shell.
- The `useChat` hook already exposes `streamingContent` and `isStreaming` state. The fix involves wiring these values through the component chain to the chat interface for display.
- The `useCatalogAgents()` and `useImportAgent()` hooks already exist and provide data and actions for the catalog feature. The fix involves using these in an inline section instead of a modal.
- Auto model resolution is already implemented in the backend orchestrator. No backend code changes are expected.
- The `useScrollLock` hook already exists and works correctly; the fix is limited to changing how it is called in `CleanUpSummary.tsx`.
- Scope is limited to frontend changes. No backend modifications, E2E test additions, or mobile-specific scroll fixes beyond the single-scroll-container pattern are included.
