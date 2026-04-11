# Feature Specification: Multi-Chat App Page

**Feature Branch**: `001-multi-chat-app-page`  
**Created**: 2026-04-11  
**Status**: Draft  
**Input**: User description: "Transform the AppPage (/) from a marketing landing page into the primary multi-chat experience with side-by-side resizable panels. Add full backend conversation support (new conversations table, conversation_id on messages, CRUD endpoints). Keep the global ChatPopup on other pages as-is."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start a Chat on the Home Page (Priority: P1)

An authenticated user navigates to the home page (/) and is immediately presented with a full-screen chat experience instead of the current marketing landing page. A single chat panel is open by default, ready for the user to type a message, receive streaming responses, create task proposals, upload files, use mentions, and execute commands — all existing chat functionality available today in the floating popup.

**Why this priority**: This is the core transformation — without it, the home page remains a marketing page. Every other story depends on the chat panel being functional on AppPage.

**Independent Test**: Can be fully tested by navigating to `/`, typing a message, and verifying a streaming response appears in the chat panel. Delivers immediate value as a dedicated chat workspace replacing the landing page.

**Acceptance Scenarios**:

1. **Given** an authenticated user, **When** they navigate to `/`, **Then** they see a full-viewport chat panel instead of the marketing landing page
2. **Given** an authenticated user on the home page, **When** they type a message and send it, **Then** the message is sent and a streaming response appears in real time
3. **Given** an authenticated user on the home page with a chat panel, **When** they use any existing chat feature (file upload, mentions, `/plan` command, proposals), **Then** the feature works identically to how it works in the current floating popup
4. **Given** an authenticated user on the home page, **When** the page loads, **Then** a new conversation is automatically created and associated with the panel

---

### User Story 2 - Open Multiple Chat Panels Side by Side (Priority: P2)

A user wants to work on multiple topics simultaneously. They click an "Add Chat" button to open a second chat panel next to the first one. Each panel operates independently — messages sent in one panel do not appear in the other. The user can have several panels open at once, each connected to its own conversation.

**Why this priority**: Multi-panel is the defining differentiator of this feature. Without it, the home page is just a bigger version of the existing popup. Side-by-side panels enable parallel workflows.

**Independent Test**: Can be tested by clicking "Add Chat," sending different messages in each panel, and confirming responses are independent. Delivers the core multi-tasking value.

**Acceptance Scenarios**:

1. **Given** a user on the home page with one chat panel, **When** they click the "Add Chat" button, **Then** a second chat panel appears side-by-side with the first
2. **Given** a user with two open panels, **When** they send a message in the left panel, **Then** the response appears only in the left panel and the right panel is unaffected
3. **Given** a user with two open panels, **When** they use `/plan` mode in one panel, **Then** plan thinking indicators and proposal flow occur only in that panel
4. **Given** a user with multiple panels, **When** they close a panel via the close button, **Then** that panel is removed and remaining panels resize to fill the space
5. **Given** a user with multiple panels open, **When** they add another panel, **Then** the new panel opens a fresh conversation and all panels share the available width

---

### User Story 3 - Resize Chat Panels (Priority: P3)

A user has two or more chat panels open and wants to allocate more space to one conversation. They drag a resize handle between two panels to adjust widths. Panels respect a minimum width to remain usable.

**Why this priority**: Resizing enhances the multi-panel experience but is not required for basic multi-chat functionality. Users can still use panels at equal default widths without resizing.

**Independent Test**: Can be tested by opening two panels, dragging the resize handle, and verifying width changes. Delivers layout customization value.

**Acceptance Scenarios**:

1. **Given** a user with two or more chat panels, **When** they drag the resize handle between panels, **Then** the panels resize proportionally following the drag position
2. **Given** a user resizing panels, **When** they drag a panel below the minimum width (320 pixels), **Then** the panel snaps to the minimum width and does not shrink further
3. **Given** a user with resized panels, **When** they add or remove a panel, **Then** the remaining panels redistribute width proportionally

---

### User Story 4 - Manage Conversations (Priority: P3)

A user wants to rename a conversation to remember its topic, or delete a conversation they no longer need. Each chat panel shows an editable title in its header. The system also supports listing and deleting conversations.

**Why this priority**: Conversation management improves organization but is not needed for the core chat experience. Default auto-generated titles provide a baseline without user intervention.

**Independent Test**: Can be tested by clicking the title in a panel header, editing it, and confirming it persists after a page refresh. Delivers organizational value.

**Acceptance Scenarios**:

1. **Given** a user with an open chat panel, **When** they click the conversation title in the panel header, **Then** the title becomes editable inline
2. **Given** a user editing a conversation title, **When** they confirm the edit (press Enter or click away), **Then** the new title is saved and persists across page refreshes
3. **Given** a user with a panel open, **When** they delete the conversation, **Then** the panel is closed and the conversation along with its messages is removed
4. **Given** a new conversation, **When** no title has been set, **Then** a default title is displayed (e.g., "New Chat" or derived from the first message)

---

### User Story 5 - Restore Panel Layout on Return (Priority: P3)

A user has arranged multiple chat panels and then closes the browser or refreshes the page. When they return, the previously open panels and their associated conversations are restored to the same layout.

**Why this priority**: Layout persistence prevents frustration when accidentally refreshing or returning to the app, but is a convenience feature that enhances rather than enables the core experience.

**Independent Test**: Can be tested by opening multiple panels, refreshing the browser, and verifying the same panels reappear with correct conversations. Delivers continuity value.

**Acceptance Scenarios**:

1. **Given** a user with multiple chat panels arranged, **When** they refresh the browser, **Then** the same panels reopen with the same conversations and layout widths
2. **Given** a user with a saved layout, **When** a previously saved conversation has been deleted, **Then** the panel opens with a new empty conversation instead
3. **Given** a first-time user with no saved layout, **When** they navigate to `/`, **Then** a single default panel is shown

---

### User Story 6 - Mobile Chat Experience (Priority: P4)

A user on a mobile device navigates to the home page. Since side-by-side panels do not fit on small screens, the system displays panels one at a time with tab-based switching. The user can switch between conversations using tabs and add new conversations.

**Why this priority**: Mobile support is important for accessibility but secondary to the desktop multi-panel experience which is the primary use case.

**Independent Test**: Can be tested by accessing `/` on a mobile-width viewport, verifying single-panel display with tab switching. Delivers mobile-friendly value.

**Acceptance Scenarios**:

1. **Given** a user on a mobile device (viewport under 768 pixels wide), **When** they navigate to `/`, **Then** they see a single chat panel with conversation tabs at the top
2. **Given** a mobile user with multiple conversations, **When** they tap a tab, **Then** the view switches to show that conversation's panel
3. **Given** a mobile user, **When** they tap "Add Chat," **Then** a new conversation tab is created and automatically selected

---

### User Story 7 - Chat Popup Continues Working on Other Pages (Priority: P1)

Users on pages other than the home page (e.g., `/projects`, `/pipeline`, `/agents`) continue to use the existing floating chat popup exactly as before. The popup is not affected by any multi-chat changes and does not use conversation IDs.

**Why this priority**: Backward compatibility is critical — breaking the existing chat popup would regress functionality for all users across the entire application.

**Independent Test**: Can be tested by navigating to `/projects`, opening the chat popup, sending a message, and confirming it works identically to before. Delivers regression safety.

**Acceptance Scenarios**:

1. **Given** a user on any page other than `/`, **When** they open the floating chat popup, **Then** it works exactly as it does today with no behavior changes
2. **Given** a user who has conversations on the home page, **When** they use the chat popup on another page, **Then** the popup messages are independent and not associated with any conversation
3. **Given** the existing chat popup, **When** the multi-chat feature is deployed, **Then** all existing messages remain accessible and no data is lost

---

### Edge Cases

- What happens when a user opens more panels than the viewport width can accommodate at minimum width (320px each)? The system should prevent adding panels beyond the maximum that can fit at minimum width.
- What happens when a user sends a message in a panel whose conversation was deleted by another browser tab? The system should display an error and offer to create a new conversation.
- What happens if the backend is unreachable when creating a conversation? The panel should show an error state with a retry option.
- What happens when a user has a very long conversation title? The title should be truncated with an ellipsis in the panel header while the full title remains editable.
- What happens when localStorage is full or unavailable? The layout defaults to a single panel without persistence, and no error is shown to the user.
- What happens when a user rapidly clicks "Add Chat" multiple times? The system should debounce creation to prevent duplicate panels.
- What happens when a streaming response is in progress and the user closes that panel? The stream should be cancelled gracefully without leaving orphaned connections.

## Requirements *(mandatory)*

### Functional Requirements

#### Conversation Management

- **FR-001**: System MUST support creating a new conversation associated with a user session
- **FR-002**: System MUST support listing all conversations for the current user session, ordered by most recently updated
- **FR-003**: System MUST support updating a conversation's title
- **FR-004**: System MUST support deleting a conversation and all its associated messages, proposals, and recommendations
- **FR-005**: Each conversation MUST have a unique identifier, a reference to the owning session, a title, and creation/update timestamps
- **FR-006**: The conversation identifier MUST be optional (nullable) on messages, proposals, and recommendations to maintain backward compatibility with the existing chat popup

#### Message Association

- **FR-007**: System MUST support associating messages with a specific conversation when a conversation identifier is provided
- **FR-008**: System MUST support retrieving messages filtered by conversation identifier
- **FR-009**: System MUST continue to support retrieving all messages for a session when no conversation identifier is provided (backward compatibility)
- **FR-010**: System MUST support clearing messages scoped to a specific conversation without affecting other conversations
- **FR-011**: Proposals and recommendations MUST also support optional conversation identifier association

#### Agent Isolation

- **FR-012**: Each conversation MUST have its own independent agent context so that messages in one conversation do not influence responses in another
- **FR-013**: The existing chat popup (without conversation identifier) MUST continue to use its own independent agent context
- **FR-014**: Agent context MUST be isolated using a composite key of session identifier and conversation identifier

#### Home Page Chat Experience

- **FR-015**: The home page (`/`) MUST display a full-viewport multi-panel chat experience instead of the current marketing landing page
- **FR-016**: The home page MUST open with a single chat panel by default when no saved layout exists
- **FR-017**: Each chat panel MUST support all existing chat functionality: sending messages, streaming responses, file upload, mentions, commands, task proposals, issue recommendations, and plan mode
- **FR-018**: Users MUST be able to add new chat panels via an "Add Chat" button

#### Multi-Panel Layout

- **FR-019**: Multiple chat panels MUST be displayed side-by-side in a horizontal layout on desktop viewports
- **FR-020**: Users MUST be able to resize panels by dragging a handle between adjacent panels
- **FR-021**: Each panel MUST have a minimum width of 320 pixels
- **FR-022**: Users MUST be able to close any panel via a close button in the panel header
- **FR-023**: When a panel is added or removed, remaining panels MUST redistribute width proportionally

#### Panel Header

- **FR-024**: Each panel MUST display the conversation title in its header
- **FR-025**: The conversation title MUST be editable inline by clicking on it
- **FR-026**: The panel header MUST include a close button to remove the panel

#### Layout Persistence

- **FR-027**: The system MUST persist the current panel layout (which conversations are open and their width percentages) to the browser's local storage
- **FR-028**: On page load, the system MUST restore the previously saved panel layout
- **FR-029**: If a previously saved conversation no longer exists, the system MUST replace it with a new empty conversation

#### Mobile Support

- **FR-030**: On viewports narrower than 768 pixels, the system MUST display one panel at a time with tab-based conversation switching
- **FR-031**: Mobile users MUST be able to switch between conversations using tabs
- **FR-032**: Mobile users MUST be able to add new conversations

#### Backward Compatibility

- **FR-033**: The existing floating chat popup on all pages other than `/` MUST continue to function without any behavior changes
- **FR-034**: All existing messages (without conversation identifiers) MUST remain accessible and queryable
- **FR-035**: All existing chat endpoints MUST continue to work when no conversation identifier is provided

### Key Entities

- **Conversation**: Represents a distinct chat thread. Key attributes: unique identifier, owning session reference, user-editable title, creation timestamp, last-updated timestamp. A conversation belongs to one session and contains zero or more messages, proposals, and recommendations.
- **Chat Message** (extended): Existing message entity extended with an optional reference to a conversation. When the reference is present, the message belongs to that conversation; when absent, the message is an unscoped session-level message (backward compatible with the popup).
- **Chat Panel**: A UI-only concept representing an open conversation viewport on the home page. Key attributes: panel identifier, associated conversation reference, width percentage. Panels are not persisted on the server — only in the browser's local storage.

### Assumptions

- The existing sidebar navigation provides adequate access to projects, pipelines, agents, and chores — the quick-link cards currently on the AppPage marketing landing page are redundant and can be safely removed.
- A reasonable maximum number of simultaneous open panels is determined by viewport width divided by the 320-pixel minimum width (e.g., ~6 panels on a 1920px screen). The system does not need a hard-coded panel limit beyond the minimum width constraint.
- Conversation titles default to "New Chat" and can optionally be auto-updated with a summary of the first user message in a future iteration. For this feature, manual title editing is sufficient.
- The conversation deletion is a hard delete (not soft delete). Deleted conversations and their messages are permanently removed.
- The mobile breakpoint of 768 pixels aligns with the existing application's responsive breakpoints.
- Performance for conversation listing is acceptable up to hundreds of conversations per session. Pagination or virtual scrolling of the conversation list is out of scope for this feature but can be added later.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can start a new chat conversation on the home page within 2 seconds of page load
- **SC-002**: Users can open up to 4 side-by-side chat panels on a standard desktop viewport (1920px wide) with each panel remaining fully functional
- **SC-003**: Messages sent in one panel never appear in or influence responses in another panel
- **SC-004**: 100% of existing chat features (streaming, file upload, mentions, commands, proposals, plan mode) work in each chat panel without degradation
- **SC-005**: Panel layout (open conversations and widths) is restored correctly after a browser refresh in under 1 second
- **SC-006**: The existing floating chat popup on non-home pages continues to pass all current tests with zero regressions
- **SC-007**: All existing messages created before this feature remain accessible and queryable without data migration issues
- **SC-008**: On mobile devices, users can switch between conversation tabs in under 500 milliseconds
- **SC-009**: Resizing panels via drag handle provides smooth, real-time visual feedback without layout jank
- **SC-010**: Creating, renaming, and deleting a conversation each complete within 1 second from the user's perspective
