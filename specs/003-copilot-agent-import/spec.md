# Feature Specification: Awesome Copilot Agent Import

**Feature Branch**: `003-copilot-agent-import`
**Created**: 2026-04-01
**Status**: Draft
**Input**: User description: "Support easy 1-click import of Awesome Copilot Agents from the Agents page. Should also allow for browsing/searching of agents from the Agents page. When an agent is imported it is saved to Solune database. When an agent is added to a project/repo a GitHub Parent Issue is created to create a PR with related agent/prompt md files needed for the agent."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse Available Agents (Priority: P1)

A user navigates to the Agents page and opens a dedicated browse modal to discover available Awesome Copilot agents. The modal presents a searchable, filterable catalog of agents sourced from Awesome Copilot's cached index. The user can scan agent names, descriptions, and categories to find agents that match their needs.

**Why this priority**: Browsing is the entry point for the entire import workflow. Without the ability to discover agents, no downstream actions (import, install) are possible. This story delivers immediate value by giving users visibility into what agents are available.

**Independent Test**: Can be fully tested by opening the browse modal and verifying that agents are listed, searchable, and filterable. Delivers value by letting users explore the Awesome Copilot catalog without leaving Solune.

**Acceptance Scenarios**:

1. **Given** a user is on the Agents page, **When** they click the "Browse Agents" button, **Then** a dedicated modal opens displaying a list of available Awesome Copilot agents with their names and descriptions.
2. **Given** the browse modal is open, **When** the user types a search term, **Then** the agent list filters to show only agents whose name or description matches the search term.
3. **Given** the browse modal is open, **When** the catalog data has not been fetched yet, **Then** the modal displays a loading indicator until agents are available.
4. **Given** the browse modal is open, **When** the catalog cannot be reached or parsed, **Then** the modal displays a clear error message with a retry option.

---

### User Story 2 - Import an Agent to Project (Priority: P1)

From the browse modal, a user selects an agent and imports it into the current Solune project with a single click. The import saves the agent's raw source content and catalog metadata to the Solune database as a project-scoped snapshot. The agent appears on the Agents page with an "Imported" badge, indicating it is available but not yet installed to a repository.

**Why this priority**: Import is the core action that captures agent data into Solune. It must work reliably before install can be built on top. This story delivers value by letting users curate a collection of agents within their project without any GitHub side effects.

**Independent Test**: Can be fully tested by importing an agent from the browse modal, then verifying it appears on the Agents page with the correct badge and metadata. No GitHub interaction is required.

**Acceptance Scenarios**:

1. **Given** the browse modal is open and agents are listed, **When** the user clicks the "Import" button on a specific agent, **Then** the agent's raw source content and metadata are saved to the Solune database under the current project.
2. **Given** an agent has been imported, **When** the user views the Agents page, **Then** the imported agent appears with an "Imported" status badge, visually distinct from custom agents and installed agents.
3. **Given** a user attempts to import an agent that has already been imported into the same project, **When** they click "Import," **Then** the system notifies the user that the agent is already imported and does not create a duplicate.
4. **Given** the import process fails (e.g., network error while fetching raw content), **When** the error occurs, **Then** the user sees a clear error message and the agent is not left in a partial state.

---

### User Story 3 - Install Agent to Repository (Priority: P2)

A user selects a previously imported agent and chooses to install it to a specific repository. A confirmation step is presented before any GitHub changes are made. Upon confirmation, the system creates a parent GitHub issue and an immediate pull request that commits the agent's raw markdown as the repository's `.agent.md` file and generates a matching `.prompt.md` routing file.

**Why this priority**: Install is the action that delivers the agent to the user's GitHub repository, completing the end-to-end workflow. It depends on import (P1) being functional first. This story delivers value by automating the multi-step process of setting up an agent in a repository.

**Independent Test**: Can be fully tested by installing a previously imported agent, confirming the confirmation step appears, and verifying the GitHub issue and PR are created with the correct file contents.

**Acceptance Scenarios**:

1. **Given** an agent with "Imported" status exists on the Agents page, **When** the user clicks "Add to project/repo," **Then** a confirmation dialog appears showing the agent name, target repository, and a summary of what will be created (issue, PR, files).
2. **Given** the confirmation dialog is displayed, **When** the user confirms the install, **Then** the system creates a parent GitHub issue and an immediate PR containing the raw `.agent.md` file and a generated `.prompt.md` routing file.
3. **Given** the confirmation dialog is displayed, **When** the user cancels, **Then** no GitHub resources are created and the agent remains in "Imported" status.
4. **Given** the install process is in progress, **When** the GitHub issue and PR are successfully created, **Then** the agent's status changes to "Installed" and the Agents page reflects the updated state with links to the created issue and PR.
5. **Given** the install process encounters a GitHub error (e.g., insufficient permissions), **When** the error occurs, **Then** the user sees a clear error message and the agent remains in "Imported" status.

---

### User Story 4 - View Imported Agent Details (Priority: P3)

A user can view the full details of an imported agent, including its raw source content, catalog origin metadata, and current status (imported or installed). Imported agents are treated as read-only external snapshots and cannot be edited directly.

**Why this priority**: Viewing details supports transparency and trust in the import process. Users need to verify what they imported before installing. This story builds on the import flow and adds information depth.

**Independent Test**: Can be fully tested by importing an agent and then viewing its detail view to confirm all metadata and raw content are displayed correctly.

**Acceptance Scenarios**:

1. **Given** an imported agent exists on the Agents page, **When** the user clicks to view its details, **Then** the system displays the agent's name, description, catalog origin, import date, and raw source content.
2. **Given** an imported agent detail view is open, **When** the user looks for edit controls, **Then** no edit functionality is available — the agent is presented as a read-only snapshot.

---

### Edge Cases

- What happens when the upstream Awesome Copilot catalog is temporarily unavailable? The system should use cached data and show a notice if the cache is stale.
- How does the system handle agents whose raw markdown contains frontmatter fields that Solune does not model? The raw content is stored verbatim; only the `.prompt.md` routing file is generated by Solune.
- What happens if a user tries to install an agent to a repository where the same agent file already exists? The system should warn the user and allow them to choose whether to overwrite or cancel.
- What happens if the imported agent's upstream source changes after import? The import is a point-in-time snapshot. Later installs use the stored snapshot, not the current upstream version.
- How are imported agents handled when a project is deleted? Imported agent records should be removed along with the project data.
- What happens if the user has no repositories connected to the project? The install action should be disabled or hidden, with a message explaining that a repository connection is required.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a dedicated browse modal accessible from the Agents page for discovering Awesome Copilot agents.
- **FR-002**: System MUST support searching and filtering agents within the browse modal by name and description.
- **FR-003**: System MUST use a cached catalog index (Awesome Copilot's llms.txt) for browsing and searching, fetching raw agent markdown only when a user imports a specific agent.
- **FR-004**: System MUST allow users to import an agent into the current project with a single click from the browse modal.
- **FR-005**: System MUST store imported agents as project-scoped database records, including the raw source markdown snapshot, catalog-origin metadata, and import timestamp.
- **FR-006**: System MUST NOT create any GitHub resources (issues, PRs, file commits) during the import step.
- **FR-007**: System MUST display imported agents on the Agents page with a distinct "Imported" status badge, visually differentiated from custom agents and installed agents.
- **FR-008**: System MUST prevent duplicate imports of the same agent within the same project.
- **FR-009**: System MUST provide an "Add to project/repo" action for imported agents that triggers the install workflow.
- **FR-010**: System MUST display a confirmation dialog before executing the install, showing the agent name, target repository, and a summary of changes.
- **FR-011**: System MUST create a parent GitHub issue and an immediate pull request during install.
- **FR-012**: System MUST commit the imported raw agent markdown as the repository's `.agent.md` file during install, preserving all upstream frontmatter and content.
- **FR-013**: System MUST generate a matching `.prompt.md` routing file during install, without altering the raw agent content.
- **FR-014**: System MUST update the agent's status from "Imported" to "Installed" after a successful install, including references to the created issue and PR.
- **FR-015**: System MUST keep imported agents as read-only external snapshots — they are not editable as custom agents unless explicitly duplicated into a custom flow.
- **FR-016**: System MUST keep custom-agent authoring completely separate from the imported-agent workflow.
- **FR-017**: System MUST support agents existing in an "imported-but-not-installed" state in the database, with catalog-origin metadata and raw source snapshot fields alongside existing repo/PR fields.
- **FR-018**: System MUST handle errors gracefully during both import and install, displaying clear messages to the user and not leaving data in an inconsistent state.

### Key Entities

- **Catalog Agent**: An agent listing from the Awesome Copilot catalog index. Represents a discoverable agent with name, description, and a reference to its raw source. Exists only within the browse modal context.
- **Imported Agent**: A project-scoped database record of an agent that has been imported from the catalog. Contains the raw source markdown snapshot, catalog-origin metadata (source URL, catalog version), import timestamp, and current lifecycle status (imported or installed). Related to a single project.
- **Installed Agent**: An imported agent that has been deployed to a repository via a GitHub issue and PR. Extends the imported agent record with references to the created GitHub issue, PR, and target repository.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can discover and browse available Awesome Copilot agents within 3 seconds of opening the browse modal.
- **SC-002**: Users can import an agent into their project with a single click, completing the import in under 5 seconds.
- **SC-003**: Users can complete the full install flow (confirmation through GitHub issue and PR creation) in under 30 seconds.
- **SC-004**: 100% of imported agents retain their complete raw source content, including all frontmatter, through both the import and install lifecycle.
- **SC-005**: The browse modal search returns filtered results within 1 second of the user typing a query.
- **SC-006**: Zero GitHub API calls are made during the import step — only during install.
- **SC-007**: Users can distinguish between imported, installed, and custom agents at a glance on the Agents page through clear visual status indicators.
- **SC-008**: 95% of users can complete the import-to-install workflow without requiring external documentation or guidance.

## Assumptions

- The Awesome Copilot llms.txt catalog format is stable and parseable. If the format changes, the catalog reader will need updating.
- Solune already has authenticated GitHub access for the current user, which is reused for creating issues and PRs during install.
- The existing cache helpers in the backend are sufficient for caching the llms.txt catalog data.
- The existing GitHub commit workflow and prompt-routing generation utilities can be reused for the install step without significant modification.
- Agent import is limited to Awesome Copilot agents only — no other external catalogs are supported in this feature.
- Imports are project-scoped; there is no global agent library across Solune projects.
- Standard web application performance expectations apply (sub-second UI interactions, reasonable timeout handling).
- Users have appropriate GitHub permissions to create issues and PRs in the target repository during install.
