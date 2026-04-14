# Feature Specification: MCP Catalog on Tools Page

**Feature Branch**: `006-mcp-catalog-tools-page`  
**Created**: 2026-04-14  
**Status**: Draft  
**Input**: User description: "Add an MCP Catalog section to the Tools page, mirroring the existing Agents Catalog pattern. Users browse 21,000+ external MCP servers via the Glama API, import them as tool configs, and sync to their repo's mcp.json."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse MCP Server Catalog (Priority: P1)

A user navigates to the Tools page and scrolls to the new "Browse MCP Catalog" section. They see a searchable, categorized catalog of 21,000+ external MCP servers sourced from the Glama API. They can type a search query (e.g., "github") or select a category chip (e.g., "Developer Tools", "Cloud", "Database") to filter results. Each server card displays its name, description, quality score (A/B/C), and server type badge (local/remote). The user can quickly find MCP servers relevant to their project needs.

**Why this priority**: Browsing the catalog is the foundational user journey — without it, no other feature (import, sync) is possible. It delivers immediate discovery value and makes the 21,000+ server ecosystem accessible to users.

**Independent Test**: Can be fully tested by navigating to the Tools page, viewing the catalog section, performing search queries, and applying category filters. Delivers value by letting users discover MCP servers even before importing them.

**Acceptance Scenarios**:

1. **Given** a user is on the Tools page, **When** they scroll to the "Browse MCP Catalog" section, **Then** they see a search input, category filter chips, and a grid of MCP server cards with name, description, quality score, and type badge.
2. **Given** the catalog section is visible, **When** the user types "github" into the search input, **Then** the server card grid updates to show only servers matching "github" in their name or description.
3. **Given** the catalog section is visible, **When** the user selects the "Database" category chip, **Then** the server card grid filters to show only servers in the Database category.
4. **Given** the catalog section is visible, **When** the user combines a search query with a category filter, **Then** the results reflect both the text query and the selected category.
5. **Given** a search query returns no results, **When** the user views the catalog, **Then** a clear "No servers found" message is displayed with suggestions to adjust the query.

---

### User Story 2 - Import MCP Server from Catalog (Priority: P1)

A user finds an MCP server they want to use and clicks the "Import" button on its catalog card. The system creates a new MCP tool configuration in the project using the server's install configuration data. After import, the card updates to show an "Installed" badge instead of the "Import" button, and the imported server appears in the project's existing tool list. The import process automatically maps the server's configuration to the correct format based on its type (HTTP, stdio, or SSE).

**Why this priority**: Import is the core action that converts browsing into value — users need to be able to add discovered servers to their project. Without import, the catalog is read-only and delivers limited utility.

**Independent Test**: Can be fully tested by browsing the catalog, clicking "Import" on a server card, verifying the card shows "Installed", and confirming the new tool configuration appears in the project's tool list.

**Acceptance Scenarios**:

1. **Given** a user sees an MCP server card with an "Import" button, **When** they click "Import", **Then** a new tool configuration is created in the project and the card updates to display an "Installed" badge.
2. **Given** the user imports an HTTP-type server, **When** the import completes, **Then** the tool configuration contains a properly formatted HTTP configuration snippet.
3. **Given** the user imports a stdio-type server, **When** the import completes, **Then** the tool configuration contains a properly formatted command-based configuration snippet.
4. **Given** the user imports an SSE-type server, **When** the import completes, **Then** the tool configuration contains a properly formatted SSE configuration snippet.
5. **Given** a server is already imported (shows "Installed" badge), **When** the user views that server's card, **Then** the "Import" button is not available and the "Installed" badge is shown instead.
6. **Given** the import process encounters an error, **When** the user clicks "Import", **Then** a user-friendly error message is displayed and the card returns to its original state.

---

### User Story 3 - Sync Imported MCP Server to Repository (Priority: P2)

After importing an MCP server, the user can sync it to their repository's `mcp.json` file using the existing "Sync to Repo" functionality. This ensures that the next agent execution automatically picks up the new MCP server without manual configuration file editing.

**Why this priority**: Syncing completes the end-to-end workflow from discovery to activation. It builds on existing "Sync to Repo" infrastructure and requires import (P1) to be functional first.

**Independent Test**: Can be tested by importing an MCP server, triggering "Sync to Repo" on the imported tool, and verifying the server's configuration appears in the repository's `mcp.json` file.

**Acceptance Scenarios**:

1. **Given** the user has imported an MCP server from the catalog, **When** they click "Sync to Repo" on the imported tool, **Then** the server's configuration is written to the repository's `mcp.json` file.
2. **Given** the `mcp.json` file already contains other tool configurations, **When** the user syncs a newly imported server, **Then** the new configuration is added alongside existing entries without overwriting them.
3. **Given** the sync operation fails (e.g., permission error), **When** the user attempts to sync, **Then** a user-friendly error message explains the issue.

---

### User Story 4 - Already-Installed Detection (Priority: P2)

When browsing the catalog, servers that have already been imported into the current project display an "Installed" badge on their catalog card. This prevents duplicate imports and provides at-a-glance awareness of which servers are already configured.

**Why this priority**: Duplicate prevention improves the user experience by providing clear visual feedback about project state, but it is an enhancement to the core browse/import flow.

**Independent Test**: Can be tested by importing one or more servers, then browsing or searching the catalog and verifying that imported servers show the "Installed" badge while non-imported servers show the "Import" button.

**Acceptance Scenarios**:

1. **Given** the user has previously imported server "GitHub MCP", **When** they browse the catalog or search for "GitHub", **Then** the "GitHub MCP" card shows an "Installed" badge.
2. **Given** the user has not imported server "Slack MCP", **When** they browse the catalog, **Then** the "Slack MCP" card shows an "Import" button.
3. **Given** the user removes a previously imported server from the tool list, **When** they browse the catalog, **Then** the removed server's card reverts to showing the "Import" button.

---

### Edge Cases

- What happens when the external catalog data source is temporarily unavailable? The system displays cached results (if available) with a notice that results may not be current, or a clear error message with a retry option if no cache is available.
- What happens when the user searches with special characters or extremely long queries? The system sanitizes input and either returns relevant results or a "No servers found" message without errors.
- What happens when the catalog returns a server with an unrecognized server type? The system skips the unrecognized server or displays it without an import option, logging a warning for administrators.
- What happens when two users simultaneously import the same server for the same project? The system handles the duplicate gracefully — either preventing the second import or treating it as idempotent.
- What happens when a catalog server's install configuration is missing or malformed? The import button is disabled or the system shows an informative error explaining the server cannot be imported at this time.
- What happens when the catalog has thousands of results for a broad query? The system paginates results or loads them incrementally to maintain performance.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display a "Browse MCP Catalog" section on the Tools page, positioned between the presets gallery and the tool archive section.
- **FR-002**: System MUST retrieve MCP server listings from the Glama API, including server name, description, repository URL, category, server type, install configuration, and quality score.
- **FR-003**: System MUST provide a text search input that filters catalog servers by name and description.
- **FR-004**: System MUST provide category filter chips (e.g., Developer Tools, Cloud, Database, Search) to filter catalog servers by category.
- **FR-005**: System MUST display each catalog server as a card showing: name, description, quality score (A/B/C), and server type badge (local/remote/HTTP).
- **FR-006**: System MUST provide an "Import" button on each server card that creates a new MCP tool configuration in the project.
- **FR-007**: System MUST map imported server configurations to the correct format based on server type:
  - HTTP type → HTTP configuration format
  - stdio type → command-based configuration format
  - SSE type → SSE configuration format
- **FR-008**: System MUST display an "Installed" badge on catalog cards for servers that have already been imported into the current project.
- **FR-009**: System MUST allow imported MCP servers to be synced to the repository's `mcp.json` file using the existing "Sync to Repo" flow.
- **FR-010**: System MUST cache catalog data with a 1-hour time-to-live (TTL) to reduce external API calls, with stale-fallback behavior when the cache expires and the external source is unavailable.
- **FR-011**: System MUST validate all external URLs to prevent server-side request forgery (SSRF) attacks when proxying catalog data.
- **FR-012**: System MUST handle external API failures gracefully by displaying cached results when available, or showing a user-friendly error message with a retry option.
- **FR-013**: System MUST support pagination or incremental loading for large catalog result sets to maintain responsive performance.
- **FR-014**: System MUST prevent duplicate imports of the same catalog server within a single project.

### Key Entities

- **CatalogMcpServer**: Represents an external MCP server from the catalog. Key attributes: unique identifier, name, description, repository URL, category, server type (local/remote/HTTP), install configuration (structured data), quality score (A/B/C), and whether it is already installed in the current project.
- **McpToolConfig** (existing): Represents an MCP tool configuration within a project. The import process creates a new McpToolConfig from a CatalogMcpServer's install configuration. Existing CRUD, sync-to-repo, and UI infrastructure is reused.

### Assumptions

- The Glama API (`GET https://glama.ai/api/mcp/v1/servers?query=`) remains free, publicly accessible, and does not require authentication.
- The Glama API response includes all necessary fields: server name, description, repository URL, category, server type, install configuration, and quality score.
- Microsoft's ~25 MCP servers (Azure, GitHub, Playwright, Foundry, etc.) are included in the Glama API dataset and can be surfaced via category or tag filtering rather than as a separate data source.
- The existing "Sync to Repo" flow and McpToolConfig CRUD infrastructure are stable and do not require modification to support imported catalog servers.
- Per-agent MCP assignment (attaching specific MCPs to specific agent configuration files) is explicitly out of scope for this feature and will be addressed in a future enhancement.
- No scraping of mcpservers.org, mcp.so, or opentools.com — only the Glama API is used as the data source.
- Standard web application performance expectations apply (page loads under 3 seconds, search results under 2 seconds).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can discover and browse 21,000+ MCP servers from the catalog section on the Tools page.
- **SC-002**: Users can find relevant MCP servers using text search with results appearing in under 2 seconds.
- **SC-003**: Users can filter servers by category using filter chips, with filtered results appearing in under 2 seconds.
- **SC-004**: Users can import an MCP server from the catalog into their project in under 3 clicks (navigate to catalog → find server → click Import).
- **SC-005**: Imported servers are correctly formatted based on their type (HTTP, stdio, SSE) and appear in the project's tool list immediately after import.
- **SC-006**: Already-imported servers display an "Installed" badge in the catalog, preventing unintentional duplicate imports.
- **SC-007**: Imported MCP servers can be synced to the repository's `mcp.json` file using the existing sync flow, and subsequent agent executions automatically pick up the new server.
- **SC-008**: The catalog remains functional when the external data source experiences intermittent outages, by serving cached results within the TTL window.
- **SC-009**: 90% of users who browse the catalog can successfully import at least one MCP server on their first attempt without assistance.
