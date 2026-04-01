# Feature Specification: Awesome Copilot Agent Catalog Import

**Feature Branch**: `003-agent-catalog-import`
**Created**: 2026-04-01
**Status**: Draft
**Input**: User description: "Import Awesome Copilot agents into Solune as project-scoped database snapshots with browse, import, and install lifecycle"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse Available Agents from Awesome Copilot Catalog (Priority: P1)

As a project administrator, I want to open a dedicated browse modal from the Agents page that lists all available agents from the Awesome Copilot catalog so that I can discover agents relevant to my project without leaving Solune.

**Why this priority**: Browsing is the entry point for the entire import-and-install workflow. Without a catalog view, users cannot discover or evaluate agents, making every downstream feature unreachable. This delivers immediate discovery value as a standalone slice.

**Independent Test**: Can be fully tested by opening the browse modal and verifying that agent entries from the cached catalog index are displayed with name, description, and category metadata. Delivers value by letting users evaluate available agents.

**Acceptance Scenarios**:

1. **Given** a user is on the Agents page for their current project, **When** they click the "Browse Catalog" button, **Then** a dedicated modal opens displaying a list of agents sourced from the cached Awesome Copilot catalog index.
2. **Given** the browse modal is open, **When** the user types a search query, **Then** the list is filtered to show only agents whose name or description matches the query.
3. **Given** the browse modal is open, **When** the catalog index has not been fetched before, **Then** the system fetches and caches the catalog index before displaying results, showing a loading indicator during the fetch.
4. **Given** the browse modal is open, **When** the cached catalog index is already available, **Then** the list renders immediately from cache without a network request.
5. **Given** the catalog index fetch fails (network error, upstream unavailable), **When** the user opens the browse modal, **Then** the modal displays a clear error message with a retry option and does not show an empty or broken list.

---

### User Story 2 - Import an Agent into the Project (Priority: P1)

As a project administrator, I want to select an agent from the browse modal and import it into my current project so that the agent definition is saved as a project-scoped snapshot I can review before installing it into a repository.

**Why this priority**: Import is the core persistence action that decouples discovery from installation. It stores the raw upstream agent definition so that later installs are not dependent on the upstream source still being available or unchanged. This is critical infrastructure for the install workflow.

**Independent Test**: Can be fully tested by browsing the catalog, clicking import on an agent, and verifying that the agent appears in the project's agent list with an "imported" status badge. The raw agent content is stored as a snapshot.

**Acceptance Scenarios**:

1. **Given** the browse modal is open and showing agents, **When** the user clicks "Import" on a specific agent, **Then** the system fetches the agent's raw markdown content from the upstream source and stores it as a project-scoped snapshot with catalog-origin metadata.
2. **Given** an agent has been successfully imported, **When** the user views the Agents page, **Then** the imported agent appears in the agent list with an "Imported" status badge, visually distinct from installed or custom agents.
3. **Given** a user tries to import an agent that has already been imported into this project, **When** they click "Import", **Then** the system notifies the user that the agent is already imported and offers to update the snapshot with the latest upstream content.
4. **Given** the upstream raw agent markdown fetch fails during import, **When** the user clicks "Import", **Then** the system displays a clear error message explaining the failure and the agent is not stored in an incomplete state.
5. **Given** the imported agent markdown contains frontmatter fields not currently modeled by Solune, **When** the import completes, **Then** the raw source snapshot preserves all original frontmatter and content verbatim without normalization or data loss.

---

### User Story 3 - Install an Imported Agent to a Repository (Priority: P1)

As a project administrator, I want to install an imported agent into a target repository so that Solune creates a parent GitHub issue, opens an immediate pull request that commits the agent's raw `.agent.md` file and a generated `.prompt.md` routing file, and the agent is ready to use.

**Why this priority**: Installation is the action that makes an imported agent operational in a repository. It bridges the gap between the project-scoped snapshot and the repository-level commit, and is the primary value delivery mechanism for the entire feature. Without install, imported agents remain inert data.

**Independent Test**: Can be fully tested by importing an agent, clicking "Install", confirming the action, and verifying that a GitHub issue is created, a pull request is opened containing the `.agent.md` and `.prompt.md` files, and the agent's status transitions to "installed".

**Acceptance Scenarios**:

1. **Given** an agent is in "imported" state on the Agents page, **When** the user clicks "Install", **Then** a confirmation dialog appears showing the agent name, target repository, and a summary of what will be created (issue, PR, files).
2. **Given** the user confirms the install action, **When** the system processes the install, **Then** a parent GitHub issue is created describing the agent installation, and an immediate pull request is opened against the target repository.
3. **Given** the install pull request is created, **When** its contents are examined, **Then** it contains the imported raw agent markdown committed as the repository's `.agent.md` file with all original frontmatter preserved verbatim.
4. **Given** the install pull request is created, **When** its contents are examined, **Then** it also contains a generated `.prompt.md` routing file that references the `.agent.md` definition.
5. **Given** the install completes successfully, **When** the user views the Agents page, **Then** the agent's status badge transitions from "Imported" to "Installed" and shows a link to the created GitHub issue and pull request.
6. **Given** the install process encounters a GitHub error (permissions, rate limit, network), **When** the system attempts to create the issue or PR, **Then** a clear error message is displayed, the agent remains in "imported" state, and no partial artifacts (orphan issues without PRs) are left behind.

---

### User Story 4 - View and Manage Imported Agents Separately from Custom Agents (Priority: P2)

As a project administrator, I want imported agents to appear distinctly from custom-authored agents on the Agents page so that I can differentiate between externally sourced agent snapshots and agents I have created or edited myself.

**Why this priority**: Clear separation prevents confusion between externally sourced agents (read-only snapshots) and user-authored agents (editable). This supports the design decision that imported agents are treated as external snapshots, not editable custom agents, until explicitly duplicated. It is P2 because it is a UX refinement that depends on import and install already working.

**Independent Test**: Can be fully tested by having both imported and custom agents in a project and verifying that they are visually grouped or badged differently, with different available actions for each type.

**Acceptance Scenarios**:

1. **Given** a project has both imported and custom agents, **When** the user views the Agents page, **Then** imported agents display an "Imported" or "Installed" badge and custom agents display no such badge or display a "Custom" badge.
2. **Given** an imported agent is displayed on the Agents page, **When** the user inspects available actions, **Then** the edit action is not available (imported agents are read-only snapshots); only "Install" (if imported) or "View" actions are shown.
3. **Given** a project has no imported agents, **When** the user views the Agents page, **Then** the existing custom agent creation workflow remains unchanged and fully functional.

---

### User Story 5 - Agent Lifecycle State Persistence (Priority: P2)

As a project administrator, I want the system to persist an agent's lifecycle state (imported-but-not-installed vs. installed) along with catalog-origin metadata and the raw source snapshot so that the agent's provenance and current status are always available, even if the upstream catalog changes.

**Why this priority**: Lifecycle persistence is the data foundation that enables the import/install separation. Without it, the system cannot distinguish between agents at different stages or preserve the upstream content for later install. It is P2 because the backend data model needs to be in place before the UI features in P1 stories fully work end-to-end, but the P1 stories define the user-facing value.

**Independent Test**: Can be fully tested by importing an agent, verifying its stored state is "imported" with catalog-origin metadata and raw snapshot, then installing it and verifying the state transitions to "installed" with associated issue/PR references.

**Acceptance Scenarios**:

1. **Given** an agent is imported, **When** its data is retrieved, **Then** the record includes a lifecycle state of "imported", the catalog source identifier, import timestamp, and the full raw markdown content as a snapshot.
2. **Given** an imported agent is installed, **When** its data is retrieved, **Then** the lifecycle state is "installed" and the record additionally includes the GitHub issue number and pull request reference.
3. **Given** the upstream catalog removes or modifies an agent after it was imported, **When** the user views the imported agent, **Then** the stored raw snapshot remains unchanged and the agent is still installable from the local snapshot.

---

### User Story 6 - Catalog Index Caching and Refresh (Priority: P3)

As a project administrator, I want the system to cache the Awesome Copilot catalog index locally so that browse and search operations are fast, and I want the ability to manually refresh the cache to pick up newly added agents.

**Why this priority**: Caching is a performance optimization for the browse experience. The core browse functionality works without sophisticated caching (it can fetch on demand), but caching makes repeated searches fast and reduces load on the upstream source. This is P3 because it enhances performance rather than enabling new capabilities.

**Independent Test**: Can be fully tested by opening the browse modal (triggering a cache fill), closing it, reopening it (verifying instant load from cache), then clicking a refresh button and verifying that the cache is updated with any upstream changes.

**Acceptance Scenarios**:

1. **Given** the catalog index has never been fetched, **When** the user opens the browse modal, **Then** the system fetches and caches the index, and subsequent opens load from cache.
2. **Given** the catalog index is cached, **When** the user clicks a "Refresh" button in the browse modal, **Then** the system re-fetches the index from upstream, updates the cache, and the displayed list reflects any changes.
3. **Given** the cache refresh fails, **When** the user clicks "Refresh", **Then** the system shows an error message and continues displaying the previously cached data.

---

### Edge Cases

- What happens when the Awesome Copilot catalog index (llms.txt) is empty or contains no parseable agent entries? The browse modal displays a "No agents available" message and the import action is disabled.
- What happens when a user imports an agent whose raw markdown is extremely large (over 1 MB)? The system enforces a reasonable size limit and rejects the import with a clear message indicating the file exceeds the maximum allowed size.
- What happens when the same agent is imported into multiple projects? Each project stores its own independent snapshot. Changes to one project's imported agent do not affect another project's snapshot.
- What happens when an installed agent's PR is merged or closed externally? The agent's installed status remains in Solune; Solune does not sync back PR merge state automatically in this initial version.
- What happens when the user tries to install an agent but does not have write permissions to the target repository? The install fails with a clear permissions error message and the agent remains in "imported" state.
- What happens when a user opens the browse modal while offline or with no network connectivity? The modal displays cached results if available, or shows a "Cannot connect to catalog" error if no cache exists.
- What happens when the raw agent markdown contains invalid or malformed frontmatter? The import stores the content verbatim regardless of frontmatter validity; validation of frontmatter is deferred to the install step or is the user's responsibility.
- What happens when two users simultaneously import the same agent into the same project? The second import detects the existing record and offers to update the snapshot, avoiding duplicate entries.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a dedicated "Browse Catalog" entry point on the Agents page that opens a modal for discovering Awesome Copilot agents.
- **FR-002**: System MUST parse the Awesome Copilot catalog index (llms.txt) to extract agent names, descriptions, and category metadata for display in the browse modal.
- **FR-003**: System MUST support text-based search and filtering within the browse modal to narrow the catalog list by agent name or description.
- **FR-004**: System MUST cache the parsed catalog index locally using the existing cache infrastructure so that repeated browse and search operations do not require re-fetching from the upstream source.
- **FR-005**: System MUST fetch the raw agent markdown content from the upstream source only when a user explicitly imports a specific agent, not during browse or search.
- **FR-006**: System MUST store imported agents as project-scoped records, not as global records accessible across all projects.
- **FR-007**: System MUST persist the full raw agent markdown (including all frontmatter) as an immutable snapshot at import time, preserving the upstream content verbatim without normalization.
- **FR-008**: System MUST store catalog-origin metadata (source URL, catalog identifier, import timestamp) alongside each imported agent record.
- **FR-009**: System MUST support an agent lifecycle with at least two distinct states: "imported" (stored but not installed) and "installed" (committed to a repository).
- **FR-010**: System MUST prevent editing of imported agents; imported agents are treated as read-only external snapshots until explicitly duplicated into a custom agent flow.
- **FR-011**: System MUST detect and handle duplicate imports, notifying the user when an agent has already been imported into the current project and offering to update the snapshot.
- **FR-012**: System MUST display distinct visual badges ("Imported", "Installed") on the Agents page to differentiate agent lifecycle states from custom agents.
- **FR-013**: System MUST show a confirmation dialog before executing the install action, displaying the agent name, target repository, and a summary of artifacts to be created.
- **FR-014**: System MUST create a parent GitHub issue describing the agent installation when the install action is confirmed.
- **FR-015**: System MUST create an immediate pull request against the target repository as part of the install action.
- **FR-016**: The install pull request MUST commit the imported raw agent markdown as the repository's `.agent.md` file, preserving all original content and frontmatter verbatim.
- **FR-017**: The install pull request MUST include a generated `.prompt.md` routing file that references the committed `.agent.md` definition.
- **FR-018**: System MUST update the agent's lifecycle state from "imported" to "installed" upon successful creation of the GitHub issue and pull request, and store references to both.
- **FR-019**: System MUST handle install failures gracefully: if the GitHub issue is created but the PR fails, the system must clean up the orphan issue or clearly indicate the partial state to the user.
- **FR-020**: System MUST keep the existing custom agent authoring workflow (AddAgentModal) fully functional and separate from the catalog import workflow.
- **FR-021**: System MUST enforce a maximum raw agent markdown size limit to prevent storage of excessively large files during import.
- **FR-022**: System MUST provide a cache refresh mechanism in the browse modal so users can manually update the catalog index.

### Key Entities

- **Catalog Agent Entry**: A lightweight record from the parsed catalog index. Key attributes: name, description, category, source URL. Used for browse and search only; does not contain the full agent content.
- **Imported Agent**: A project-scoped snapshot of an Awesome Copilot agent. Key attributes: lifecycle state (imported/installed), raw markdown content (full verbatim snapshot), catalog-origin metadata (source URL, catalog identifier, import timestamp), associated project identifier. Transitions to "installed" state upon successful repository commit.
- **Installed Agent Reference**: Extension of the imported agent record after installation. Additional attributes: GitHub issue number, pull request URL, target repository, install timestamp. Links the project-scoped snapshot to the repository-level artifacts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can discover and browse available Awesome Copilot agents from within Solune in under 3 seconds after opening the browse modal (from cache).
- **SC-002**: Users can import an agent into their project with a single click from the browse modal, and the imported agent appears on the Agents page within 5 seconds.
- **SC-003**: Users can complete the full import-to-install workflow (browse, import, confirm, install) in under 2 minutes for a single agent.
- **SC-004**: 100% of imported agent snapshots preserve the original upstream raw markdown content verbatim, including all frontmatter fields, with zero data loss.
- **SC-005**: Every successful install action produces both a parent GitHub issue and an immediate pull request containing the `.agent.md` and `.prompt.md` files.
- **SC-006**: The existing custom agent authoring workflow continues to function without any regressions after the catalog import feature is added.
- **SC-007**: Users can visually distinguish imported agents from custom agents and installed agents from not-yet-installed agents at a glance on the Agents page.
- **SC-008**: The browse modal handles catalog fetch errors and empty catalogs gracefully, displaying clear messages without broken UI or unhandled errors.
- **SC-009**: Imported agents remain fully available and installable even if the upstream Awesome Copilot catalog is modified or becomes unavailable after import.
- **SC-010**: Install failures do not leave orphan artifacts (issues without PRs) in the target repository, or clearly communicate partial state to the user.

## Assumptions

- The Awesome Copilot catalog uses an `llms.txt` format that can be parsed to extract agent names, descriptions, and source URLs without requiring authentication.
- The existing cache infrastructure in Solune is sufficient for storing and retrieving the parsed catalog index without requiring new caching mechanisms.
- The existing GitHub commit workflow can be reused for creating issues and pull requests during the install step without significant modification.
- The existing prompt-routing generation logic can produce a valid `.prompt.md` file from an imported agent's metadata without requiring the full custom agent creation flow.
- Project-scoped storage is already supported by the existing database schema for agents, and the new lifecycle state and catalog-origin fields can be added via a schema extension.
- The browse modal is a new UI component but follows existing modal patterns in the Solune frontend.
- Imported agents are read-only snapshots; editing requires explicitly duplicating the agent into the custom agent flow (duplication is out of scope for this feature).
- The initial version does not synchronize PR merge/close state back into Solune; the installed status is set at PR creation time.
- The maximum raw agent markdown size limit is set at a reasonable default (e.g., 1 MB) based on typical agent definition sizes.
