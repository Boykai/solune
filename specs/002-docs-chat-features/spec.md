# Feature Specification: Update Documentation with New Chat Features

**Feature Branch**: `002-docs-chat-features`  
**Created**: 2026-03-31  
**Status**: Draft  
**Input**: User description: "Update Documentation with New Chat Features"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - New Developer Learns Chat Features (Priority: P1)

As a new developer onboarding to Solune, I want a single, comprehensive chat feature guide so I can understand how the chat panel works — including messaging, AI Enhance, @mention pipelines, file uploads, voice input, streaming responses, and markdown rendering — without having to read the source code.

**Why this priority**: Documentation of the chat panel is the highest-impact deliverable because the chat is the primary interaction surface of the product. Without this guide, new developers and end users must reverse-engineer behavior from code. A dedicated chat page is the foundation for all other documentation updates.

**Independent Test**: Can be fully tested by navigating to the chat page guide and confirming that every major chat feature (sending messages, AI Enhance toggle, @mention pipelines, voice input, file attachments, history navigation, slash commands, AI proposals, streaming, markdown rendering, message actions) is documented with clear descriptions and behavioral details. Delivers value by enabling self-service onboarding.

**Acceptance Scenarios**:

1. **Given** a new developer opens the chat page guide, **When** they read through the document, **Then** they find documented sections for all 12 major chat capabilities (text messaging, AI Enhance, @mention, voice input, file attachments, history navigation, slash commands, AI proposals, streaming, markdown, message types, message actions).
2. **Given** a developer needs to understand the AI Enhance toggle, **When** they read the chat page guide, **Then** they find a clear explanation of the two modes (Agent Framework vs metadata-only), how the toggle persists via localStorage, and what behavior changes between the modes.
3. **Given** an end user wants to learn how to attach files, **When** they read the chat page guide, **Then** they find the file limits (5 files max, 10 MB each), allowed and blocked file types, and automatic transcript detection behavior for .vtt/.srt files.
4. **Given** a developer needs to understand the @mention pipeline feature, **When** they read the chat page guide, **Then** they find documentation covering the @ trigger, autocomplete behavior, inline token display, and the one-active-pipeline-per-message constraint.

---

### User Story 2 - Developer Integrates with Chat API (Priority: P2)

As a developer building on the Solune platform, I want the API reference to accurately document the streaming chat endpoint, file upload constraints, and new request parameters so I can integrate with the chat system without trial-and-error.

**Why this priority**: The API reference is the contract between the backend and any consumer (frontend, third-party integrations). Missing or inaccurate endpoint documentation leads to integration bugs and wasted developer time. This directly supports platform extensibility beyond the built-in frontend.

**Independent Test**: Can be tested by reviewing the API reference page and confirming that the streaming endpoint (POST /chat/messages/stream), its SSE event types, rate limits, file upload constraints, and new request/response parameters are all documented. Each endpoint entry should include method, path, parameters, response format, and constraints.

**Acceptance Scenarios**:

1. **Given** a developer reads the API reference, **When** they look up chat endpoints, **Then** they find the streaming endpoint (POST /chat/messages/stream) with SSE event types (token, tool_call, tool_result, done, error), its rate limit (10 requests per minute), and the requirement that ai_enhance must be true.
2. **Given** a developer reads the API reference, **When** they look up file upload constraints, **Then** they find allowed/blocked file types, the 10 MB per-file limit, the 5-file maximum, and .vtt/.srt transcript auto-detection behavior documented.
3. **Given** a developer reads the API reference, **When** they review the POST /chat/messages endpoint, **Then** they find documentation for the ai_enhance, file_urls, and pipeline_id request parameters, and pagination details for the GET endpoint.

---

### User Story 3 - Developer Understands Chat Architecture (Priority: P3)

As a developer maintaining or extending the Solune backend, I want the architecture documentation to describe the ChatAgentService, its session management, tool registration, dual dispatch model, and related frontend components so I can understand the system's design without reading implementation details.

**Why this priority**: Architecture documentation provides the conceptual map for maintainers and contributors. Without documenting the ChatAgentService, new contributors must trace code paths to understand session management, tool registration, and the dual dispatch model. This is essential for sustainable development but lower priority than user-facing docs and API contracts.

**Independent Test**: Can be tested by reviewing the architecture page and confirming that the ChatAgentService subsection exists with descriptions of session management, tool registration, dual dispatch, and streaming. The frontend component table should include all chat-related components, and the hooks section should list chat-related hooks.

**Acceptance Scenarios**:

1. **Given** a developer reads the architecture page, **When** they look for the ChatAgentService, **Then** they find a subsection describing the Agent Framework wrapper, session management (TTL eviction, 100 max concurrent sessions), tool registration with MCP, dual dispatch (enhance on → Agent Framework, enhance off → fallback), and streaming behavior.
2. **Given** a developer reads the architecture page, **When** they review the frontend component table, **Then** they find entries for MentionInput, MentionAutocomplete, FilePreviewChips, MarkdownRenderer, ChatMessageSkeleton, PipelineWarningBanner, and PipelineIndicator.
3. **Given** a developer reads the architecture page, **When** they review the hooks section, **Then** they find entries for useFileUpload, useMentionAutocomplete, and useChatProposals.

---

### User Story 4 - Developer Locates Chat Source Files (Priority: P4)

As a developer navigating the codebase, I want the project structure documentation to list all chat-related source files, components, and hooks so I can find the right file to modify without searching the entire tree.

**Why this priority**: The project structure page is a quick reference map. Incomplete listings send developers on unnecessary searches. While important, this is lower priority because developers can fall back to searching the codebase directly.

**Independent Test**: Can be tested by reviewing the project structure page and confirming that services/chat_agent.py appears in the backend services listing, all 7 missing chat components appear in the frontend components listing, and all 3 missing hooks appear in the hooks listing.

**Acceptance Scenarios**:

1. **Given** a developer reads the project structure page, **When** they look up backend services, **Then** they find services/chat_agent.py listed with a description of its role (ChatAgentService — Agent Framework wrapper).
2. **Given** a developer reads the project structure page, **When** they look up frontend chat components, **Then** they find all chat-related components listed, including the 7 previously missing components.
3. **Given** a developer reads the project structure page, **When** they look up frontend hooks, **Then** they find useFileUpload, useMentionAutocomplete, and useChatProposals listed.

---

### User Story 5 - Stakeholder Tracks Feature Progress (Priority: P5)

As a project stakeholder, I want the roadmap to reflect that v0.2.0 chat features are implemented so I can accurately assess current capabilities and plan future work.

**Why this priority**: The roadmap sets expectations for stakeholders and contributors. Outdated status information creates confusion about what is available versus planned. This is important for project transparency but has the lowest direct impact on daily developer workflows.

**Independent Test**: Can be tested by reviewing the roadmap page and confirming that all v0.2.0 chat features are marked as implemented (✅) and the architecture evolution diagram reflects v0.2.0 as the current version.

**Acceptance Scenarios**:

1. **Given** a stakeholder reads the roadmap, **When** they review v0.2.0 milestones, **Then** they see all chat features marked as implemented (✅): Agent Framework, streaming, file uploads, @mention, AI Enhance, history navigation, and markdown rendering.
2. **Given** a contributor reads the roadmap, **When** they review the architecture evolution diagram, **Then** they see v0.2.0 reflected as the current production version, not v0.1.0.

---

### User Story 6 - Reader Navigates Between Related Docs (Priority: P6)

As a documentation reader, I want cross-reference links between the chat page guide and related pages (layout.md, pages/README.md) so I can discover related content without dead ends.

**Why this priority**: Cross-references are the connective tissue of documentation. Without them, the new chat page is an island. This is the lowest priority because it adds discoverability rather than new content, but is required for documentation completeness.

**Independent Test**: Can be tested by checking that layout.md contains a link to chat.md, pages/README.md includes the chat page in its index, and all internal markdown links resolve correctly.

**Acceptance Scenarios**:

1. **Given** a reader views the layout page, **When** they read the Chat Panel section, **Then** they find a link to the dedicated chat page guide (chat.md).
2. **Given** a reader views the pages index (README.md), **When** they scan the page listing, **Then** they find the chat page guide listed with a link and brief description.
3. **Given** a reader follows any internal link in the updated documentation, **When** the link target is checked, **Then** the link resolves to an existing document without 404 errors.

---

### Edge Cases

- What happens if a documentation page referenced by a cross-link does not exist yet? All cross-reference links must point to files that exist in the repository after the update is complete. Broken links must be caught during verification.
- How does the documentation handle features that are partially implemented or have known limitations? Features should be documented as they currently work, with any known limitations noted inline rather than omitted.
- What if the existing documentation structure or section headings have changed since the plan was written? Authors should match the current document structure rather than blindly following the plan — verify actual headings and tables before updating.
- What if a feature described in the plan does not exist in the codebase (e.g., a component was renamed or removed)? Authors should verify that each documented component, hook, or service actually exists in the codebase. Document what exists, not what was planned.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Documentation MUST include a new dedicated chat page guide (docs/pages/chat.md) covering all 12 major chat capabilities: text messaging, AI Enhance toggle, @mention pipeline selection, voice input, file attachments, chat history navigation, slash commands, AI proposals, streaming responses, markdown rendering, message types, and message actions.
- **FR-002**: Documentation MUST update the API reference (docs/api-reference.md) with the streaming chat endpoint (POST /chat/messages/stream), including SSE event types, rate limits, and the ai_enhance prerequisite.
- **FR-003**: Documentation MUST update the API reference with file upload constraints: allowed/blocked types, 10 MB per-file limit, 5-file maximum, and .vtt/.srt transcript auto-detection.
- **FR-004**: Documentation MUST update the API reference with new request parameters (ai_enhance, file_urls, pipeline_id) for POST /chat/messages and pagination details for the GET endpoint.
- **FR-005**: Documentation MUST update the architecture page (docs/architecture.md) with a ChatAgentService subsection describing the Agent Framework wrapper, session management, tool registration with MCP, dual dispatch, and streaming.
- **FR-006**: Documentation MUST update the architecture page frontend component table with 7 missing chat components: MentionInput, MentionAutocomplete, FilePreviewChips, MarkdownRenderer, ChatMessageSkeleton, PipelineWarningBanner, and PipelineIndicator.
- **FR-007**: Documentation MUST update the architecture page hooks section with 3 chat hooks: useFileUpload, useMentionAutocomplete, and useChatProposals.
- **FR-008**: Documentation MUST update the project structure page (docs/project-structure.md) to list services/chat_agent.py, the 7 missing chat components, and the 3 missing hooks.
- **FR-009**: Documentation MUST update the roadmap page (docs/roadmap.md) to mark all v0.2.0 chat features as implemented (✅) and update the architecture evolution diagram to reflect v0.2.0 as current.
- **FR-010**: Documentation MUST add cross-reference links: layout.md Chat Panel section must link to chat.md, and pages/README.md must include the chat page in its index.
- **FR-011**: All internal markdown links across updated documentation MUST resolve to existing files — no broken links.
- **FR-012**: Documentation MUST follow existing conventions: markdown tables, bullet lists, callouts, and "What's next?" footers where applicable.
- **FR-013**: Documentation MUST be written for both developers and end users, using clear language that non-technical stakeholders can understand.

### Key Entities

- **Chat Page Guide**: A new dedicated documentation page (docs/pages/chat.md) that serves as the single source of truth for all chat panel features, targeted at both developers and end users.
- **API Endpoint Documentation**: Updated entries in the API reference describing chat-related endpoints, their parameters, response formats, constraints, and rate limits.
- **Architecture Subsection**: A new subsection in the architecture page describing the ChatAgentService, its design patterns, and integration points.
- **Component/Hook Registry**: Updated tables in the architecture and project structure pages that list all chat-related frontend components and hooks.
- **Roadmap Milestone**: Updated v0.2.0 milestone entries reflecting the implemented status of chat features.
- **Cross-reference Links**: Hyperlinks connecting the new chat page to existing documentation pages for discoverability.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer new to the project can find documentation for any of the 12 major chat capabilities within 2 minutes by navigating from the pages index to the chat page guide.
- **SC-002**: All 6 documentation files (1 new, 5 updated) are complete, internally consistent, and follow existing documentation conventions.
- **SC-003**: 100% of internal markdown links across updated documentation resolve to existing files — zero broken links.
- **SC-004**: The API reference contains complete documentation for the streaming endpoint, including all SSE event types, rate limits, parameters, and constraints.
- **SC-005**: The architecture page accurately reflects the current v0.2.0 system design, including the ChatAgentService subsection and all chat-related frontend components and hooks.
- **SC-006**: The roadmap accurately reflects v0.2.0 as the current implemented version, with all chat features marked as complete.
- **SC-007**: A developer reading the project structure page can locate any chat-related source file (backend service, frontend component, or hook) in under 1 minute.
- **SC-008**: Documentation updates introduce no new environment variables, configuration changes, or code changes — this is a documentation-only effort.

## Assumptions

- The existing documentation structure (docs/ directory with pages/, api-reference.md, architecture.md, project-structure.md, roadmap.md) is stable and will not be reorganized during this update.
- All chat features described in the plan (streaming SSE, Agent Framework integration, @mention, file uploads, voice input, history navigation, AI Enhance, markdown rendering) are currently implemented and functional in the codebase.
- The documentation follows existing conventions (markdown tables, bullet lists, callouts, "What's next?" footers) without introducing new formatting patterns.
- No screenshots, ADRs, CHANGELOG entries, or testing documentation are included — this is limited to the 6 files specified in the plan.
- Style and tone follow what is already established in existing documentation pages.
- Rate limit values (10/min for streaming) and constraints (5 files, 10 MB) reflect the current implementation and will not change before documentation is published.

## Dependencies

- Existing documentation pages: docs/api-reference.md, docs/architecture.md, docs/project-structure.md, docs/roadmap.md, docs/pages/layout.md, docs/pages/README.md.
- Current codebase implementation of chat features (for accuracy verification).
- Existing documentation style conventions established in current pages.

## Scope Boundaries

**In Scope**:
- Creating docs/pages/chat.md — new dedicated chat feature guide.
- Updating docs/api-reference.md — streaming endpoint, file constraints, rate limits, new parameters.
- Updating docs/architecture.md — ChatAgentService subsection, frontend component table, hooks.
- Updating docs/project-structure.md — chat_agent.py, missing components, missing hooks.
- Updating docs/roadmap.md — v0.2.0 implemented status, architecture evolution diagram.
- Updating docs/pages/layout.md — cross-reference link to chat.md.
- Updating docs/pages/README.md — chat page in index.
- Verifying all internal markdown links resolve correctly.

**Out of Scope**:
- Screenshots or visual assets.
- Architecture Decision Records (ADRs).
- CHANGELOG updates.
- Testing documentation.
- New environment variables or configuration changes.
- Code changes of any kind.
- Documentation for features not yet implemented.
- Restructuring or reorganizing the existing documentation layout.
