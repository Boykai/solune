# Feature Specification: UX Fixes — Scrolling, Agents Page, Chat Streaming, Auto Model

**Feature Branch**: `003-ux-fixes`  
**Created**: 2026-04-05  
**Status**: Draft  
**Input**: User description: "UX Fixes — Scrolling, Agents Page, Chat Streaming, Auto Model. Fix 7 UX issues across scrolling, agents page, chat instant display, and model resolution. Approach: single-scroll-container pattern for layout, replace Browse Agents modal with inline tile section, wire streaming tokens through to the UI."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Smooth Page Scrolling (Priority: P1)

As a user navigating the Settings page, I want a single, consistent scroll experience so that I do not encounter competing scroll bars or jittery scrolling behavior.

Currently, the Settings page contains nested containers that each produce their own scrollbar. This means the user sees two scroll tracks and must figure out which one controls the content they want to scroll. The fix adopts a single-scroll-container pattern: one outer container owns the scrollbar and inner content flows naturally within it.

**Why this priority**: Broken scrolling is the most immediately visible and frustrating UX defect. It affects every user who visits the Settings page, undermining trust in the product's polish.

**Independent Test**: Can be fully tested by opening the Settings page, resizing the browser window to force overflow, and confirming only one scrollbar appears and all content is reachable by scrolling.

**Acceptance Scenarios**:

1. **Given** the Settings page is loaded, **When** the viewport is shorter than the content, **Then** exactly one vertical scrollbar is visible and all content is reachable by scrolling.
2. **Given** the Settings page is in a loading state, **When** the loading spinner is displayed, **Then** no unnecessary scrollbar appears on the loading container.
3. **Given** any full-page view (Settings, Agents, Pipeline), **When** content overflows the viewport, **Then** there is only a single scrollable region — never nested scroll tracks.

---

### User Story 2 — Inline Agent Discovery (Priority: P2)

As a user looking for new agents to add to my workspace, I want to browse available agents directly on the Agents page (as an inline tile section) instead of opening a separate modal, so that the discovery experience feels integrated and seamless.

Today, agent discovery is behind a "Browse Agents" modal dialog. Modals interrupt the user's context and feel disconnected from the page they are already on. Replacing the modal with an inline, searchable tile section keeps the user in flow and makes the catalog feel like a first-class part of the Agents page.

**Why this priority**: Agent discovery is a key engagement path. An inline experience reduces friction and increases the likelihood that users explore and adopt new agents.

**Independent Test**: Can be fully tested by navigating to the Agents page and confirming that catalog agents appear as tiles directly on the page, with search and import functionality, without opening any modal.

**Acceptance Scenarios**:

1. **Given** the user is on the Agents page, **When** the page loads, **Then** a section of browsable agent tiles is visible inline (no modal required).
2. **Given** the inline agent section is visible, **When** the user types a search query, **Then** the displayed tiles filter in real time to match the query.
3. **Given** an agent tile is displayed, **When** the user clicks the import action, **Then** the agent is added to their workspace and the tile updates to show "Imported" status.
4. **Given** the inline agent section is visible, **When** the user scrolls the Agents page, **Then** the agent tiles scroll with the rest of the page content (single scroll container, no independent scroll region for the tiles).

---

### User Story 3 — Live Chat Streaming Display (Priority: P2)

As a user chatting with an AI agent, I want to see the assistant's response appear token-by-token as it is generated, so that I have immediate feedback that the system is working and can begin reading the answer before it is fully complete.

Currently, the backend streams tokens via server-sent events and the frontend accumulates them in state, but the accumulated content is never passed through to the UI components. The user sees nothing until the entire response is finished, which feels slow and unresponsive. Wiring the streaming state through to the chat interface will give users a real-time, typewriter-style reading experience.

**Why this priority**: Tied with P2 (Agent Discovery) because streaming feedback dramatically improves perceived responsiveness — one of the most impactful UX improvements for AI-powered chat interfaces.

**Independent Test**: Can be fully tested by sending a message to an AI agent and observing tokens appearing progressively in the chat area before the final response is complete.

**Acceptance Scenarios**:

1. **Given** the user has sent a message, **When** the backend begins streaming its response, **Then** tokens appear in the chat area incrementally as they arrive.
2. **Given** tokens are streaming into the chat area, **When** the chat area overflows, **Then** the view auto-scrolls to keep the latest content visible.
3. **Given** the streaming response completes, **When** the final token arrives, **Then** the streaming bubble seamlessly transitions to a normal completed message without visual flicker or content duplication.
4. **Given** the streaming connection fails mid-response, **When** an error event is received, **Then** the partial content is preserved and an appropriate error indication is shown.

---

### User Story 4 — Auto Model Resolution (Priority: P3)

As a user who selects "Auto" for the model in a pipeline or chat interaction, I want the system to automatically choose the most appropriate model for the task so that I get good results without needing to understand model differences.

The "Auto" model option is already surfaced in the UI. This story ensures that the end-to-end resolution — from the user selecting "Auto" through to the backend picking and applying the correct model — works correctly and transparently.

**Why this priority**: Auto-model is a convenience feature. Most users can manually pick a model, so this is lower urgency than the broken-scroll and missing-streaming issues.

**Independent Test**: Can be fully tested by selecting "Auto" in the model selector, initiating a pipeline or chat action, and confirming the system successfully completes the action using a resolved model.

**Acceptance Scenarios**:

1. **Given** the user selects "Auto" in the model selector, **When** a pipeline step or chat request is initiated, **Then** the system resolves and applies an appropriate model without requiring further user input.
2. **Given** "Auto" is selected, **When** the action completes, **Then** the user can see which model was actually used (e.g., in a response header, tooltip, or log).
3. **Given** "Auto" is selected and no suitable model is available, **When** the request is initiated, **Then** the user receives a clear, actionable error message rather than a silent failure.

---

### Edge Cases

- What happens when the user rapidly resizes the browser while the Settings page is open? The single-scroll-container should remain stable without layout thrashing.
- What happens when the agent catalog is empty or the catalog service is unavailable? The inline tile section should show a clear empty state or error message with a retry option.
- What happens when a streaming response contains an extremely long unbroken token (e.g., a large code block)? The chat display should handle horizontal overflow gracefully (e.g., horizontal scroll or word-wrap within the bubble).
- What happens when the user navigates away from the chat page mid-stream and then returns? The partial content should either be preserved or the user should see the completed message if it finished while they were away.
- What happens when multiple agents are streaming responses simultaneously in different chat sessions? Each session must independently track and display its own streaming state without cross-contamination.
- What happens when the user scrolls up during streaming to read earlier content? Auto-scroll should pause and resume only when the user scrolls back to the bottom.

## Requirements *(mandatory)*

### Functional Requirements

**Scrolling & Layout**

- **FR-001**: The Settings page MUST display exactly one vertical scrollbar when content overflows the viewport.
- **FR-002**: The Settings page loading state MUST NOT create an independent scrollable region.
- **FR-003**: All full-page views (Settings, Agents, Pipeline) MUST follow a single-scroll-container pattern — one scrollable parent with fixed header/footer regions as needed.

**Agents Page — Inline Discovery**

- **FR-004**: The Agents page MUST display a browsable catalog of available agents as an inline tile section, directly on the page.
- **FR-005**: The inline agent catalog MUST support real-time search filtering by agent name or description.
- **FR-006**: Each agent tile MUST provide an import action that adds the agent to the user's workspace.
- **FR-007**: Each agent tile MUST display the agent's current status (available, imported, error).
- **FR-008**: The existing Browse Agents modal MUST be retired and replaced by the inline tile section.

**Chat Streaming Display**

- **FR-009**: The chat interface MUST display assistant response tokens incrementally as they are received from the streaming source.
- **FR-010**: The chat area MUST auto-scroll to keep the latest streamed content visible, unless the user has manually scrolled up.
- **FR-011**: When streaming completes, the streamed content MUST transition to a finalized message without visual duplication or flicker.
- **FR-012**: If the streaming connection fails, the chat interface MUST preserve any partial content and display an error indicator.

**Auto Model Resolution**

- **FR-013**: When the user selects "Auto" for the model, the system MUST resolve and apply an appropriate model without additional user input.
- **FR-014**: After an action completes with "Auto" model, the system MUST surface the name of the model that was actually used.
- **FR-015**: If "Auto" model resolution fails, the system MUST present a clear, user-facing error with guidance on how to proceed (e.g., select a model manually).

### Assumptions

- The backend already streams tokens via server-sent events; no backend protocol changes are required.
- The agent catalog data source (useCatalogAgents hook) already provides the data needed for the inline tile section.
- Auto-model resolution logic exists or can be extended on the backend; the frontend simply needs to surface the resolved model name.
- The single-scroll-container pattern will be applied consistently to Settings, Agents, and Pipeline pages. Other pages are out of scope unless specifically identified.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every full-page view affected (Settings, Agents, Pipeline) displays at most one vertical scrollbar regardless of viewport size — zero instances of nested scroll tracks.
- **SC-002**: Users can discover, search, and import agents from the Agents page without opening any modal dialog.
- **SC-003**: 100% of streamed assistant responses display tokens progressively in the chat area; users see the first token within 1 second of the backend starting to stream.
- **SC-004**: The transition from streaming to completed message produces no visible content duplication or layout jump.
- **SC-005**: When "Auto" model is selected, 100% of completed actions surface the resolved model name to the user.
- **SC-006**: User-perceived response time for AI chat improves — time from pressing "Send" to seeing the first visible content in the chat area is under 2 seconds (compared to waiting for the full response today).
- **SC-007**: Zero regression in existing functionality — all pre-existing tests continue to pass after these changes.
