# Feature Specification: Awesome Copilot Agent Catalog Import

**Feature Branch**: `003-agent-catalog-import`
**Created**: 2026-04-01
**Status**: Draft
**Input**: User description: "Use Awesome Copilot's llms.txt as the cached browse index, import selected agents into Solune as project-scoped database snapshots first, then expose a separate Add to project/repo action that creates a parent GitHub issue and immediate PR. The install step should commit the imported raw agent markdown as the repo's .agent.md file and generate the matching .prompt.md routing file, so Solune preserves the upstream agent definition instead of reconstructing it loosely."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse the Awesome Copilot Agent Catalog (Priority: P1)

As a project administrator, I want to open a dedicated browse modal within the Agents page that displays the available Awesome Copilot agents so that I can discover and evaluate community agents without leaving Solune.

**Why this priority**: Browsing is the entry point for the entire import-install pipeline. Without a catalog view, users cannot discover or evaluate agents, making all downstream features impossible. This delivers immediate discovery value.

**Independent Test**: Can be fully tested by opening the browse modal from the Agents page and verifying that catalog entries load from the cached index, display agent names and descriptions, and support search filtering.

**Acceptance Scenarios**:

1. **Given** a user is on the Agents page for a project, **When** they click the "Browse Catalog" button, **Then** a modal opens displaying a searchable list of Awesome Copilot agents sourced from the cached catalog index.
2. **Given** the browse modal is open, **When** the user types a search term, **Then** the list filters to show only agents whose name or description matches the search term.
3. **Given** the browse modal is open, **When** catalog data has not been fetched yet, **Then** a loading indicator is shown until the data is ready.
4. **Given** the browse modal is open, **When** the catalog cannot be loaded (network error or missing cache), **Then** a user-friendly error message is displayed with a retry option.

---

### User Story 2 - Import an Agent as a Project-Scoped Snapshot (Priority: P1)

As a project administrator, I want to import a selected Awesome Copilot agent into my project as a local snapshot so that the agent definition is stored within Solune and does not depend on the upstream source remaining available or unchanged.

**Why this priority**: Import is the core data persistence step. It captures the raw upstream agent markdown at a point in time, ensuring that all downstream install operations work from a stable, local copy. Without import, install would depend on external availability.

**Independent Test**: Can be fully tested by selecting an agent in the browse modal, clicking "Import", and verifying that the agent appears in the project's agent list with an "Imported" status badge and that no GitHub commits or PRs are created.

**Acceptance Scenarios**:

1. **Given** the browse modal is open, **When** the user clicks "Import" on a catalog agent, **Then** the system fetches the raw agent markdown from the upstream source, stores it as a project-scoped snapshot, and the agent appears in the project's agent list with an "Imported" status.
2. **Given** a user imports an agent, **When** the import completes, **Then** no GitHub branch, commit, PR, or issue is created—the agent exists only in the local project database.
3. **Given** a user imports an agent, **When** the raw agent markdown contains frontmatter fields that Solune does not natively model, **Then** the entire raw content is stored verbatim without stripping or normalizing unknown fields.
4. **Given** a user has already imported the same agent for this project, **When** they attempt to import it again, **Then** the system informs them that the agent is already imported and does not create a duplicate record.
5. **Given** the upstream agent markdown cannot be fetched (network error or removed), **When** the user clicks "Import", **Then** an error message is shown and no partial record is created.

---

### User Story 3 - Install an Imported Agent to the Repository (Priority: P1)

As a project administrator, I want to install an imported agent into my repository so that the raw agent file is committed as a `.agent.md` file, a matching `.prompt.md` routing file is generated, a tracking GitHub issue is created, and a PR is opened—all preserving the original upstream content.

**Why this priority**: Install is the action that makes an imported agent operational in the repository. It bridges the local snapshot into the repository's GitHub workflow using the established branch-commit-PR-issue pipeline. Without install, imported agents remain dormant snapshots.

**Independent Test**: Can be fully tested by selecting an imported agent, confirming the install action, and verifying that a GitHub issue and PR are created with the raw `.agent.md` file and a generated `.prompt.md` file committed to the PR branch.

**Acceptance Scenarios**:

1. **Given** an agent is in "Imported" status, **When** the user clicks "Add to project", **Then** a confirmation dialog is displayed showing the agent name, description, and a summary of what will happen (issue creation, PR, files committed).
2. **Given** the user confirms the install, **When** the install process runs, **Then** a tracking GitHub issue is created, a branch is created, the raw agent markdown is committed as `.agent.md`, a `.prompt.md` routing file is generated and committed alongside it, and a PR is opened linking to the tracking issue.
3. **Given** the install completes, **When** the agent list refreshes, **Then** the agent's status changes from "Imported" to "Pending PR" and the PR URL is displayed.
4. **Given** the install process fails (e.g., permission error or API failure), **When** the error occurs, **Then** the agent remains in "Imported" status, an error message is shown, and no partial GitHub artifacts are left behind.
5. **Given** the raw agent markdown includes frontmatter with custom tools, MCP servers, or other fields, **When** the install commits the `.agent.md` file, **Then** the committed file is byte-for-byte identical to the stored raw snapshot—no fields are stripped, reordered, or normalized.

---

### User Story 4 - View and Manage Imported Agents (Priority: P2)

As a project administrator, I want to see imported agents in the project's agent list with a distinct "Imported" badge so that I can clearly distinguish them from custom agents I authored and from agents already installed to the repository.

**Why this priority**: Visibility of the imported-but-not-installed state is essential for managing the import-install lifecycle. Without clear status indicators, users cannot tell which agents are pending installation versus already active.

**Independent Test**: Can be fully tested by importing an agent and verifying that the Agents panel displays it with an "Imported" badge, that the badge changes to "Pending PR" after install, and that the agent card shows catalog-origin metadata (source catalog, import timestamp).

**Acceptance Scenarios**:

1. **Given** agents exist in multiple lifecycle states (Active, Pending PR, Imported, Pending Deletion), **When** the Agents page loads, **Then** each agent card displays the correct status badge with a visually distinct style for "Imported" agents.
2. **Given** an imported agent card is displayed, **When** the user views the card, **Then** the card shows the catalog origin (Awesome Copilot), the import date, and an "Add to project" action button.
3. **Given** an imported agent card is displayed, **When** the user attempts to edit the agent's prompt or configuration, **Then** editing is blocked and a message explains that imported agents must be installed or duplicated before they can be edited.
4. **Given** an imported agent exists, **When** the user decides they no longer want it, **Then** they can delete the imported snapshot from the project without any GitHub side effects.

---

### User Story 5 - Catalog Origin Tracking and Raw Source Preservation (Priority: P2)

As a project administrator, I want each imported agent to retain metadata about where it came from (catalog source, original URL, import timestamp) and preserve the exact raw markdown so that I can trace provenance and re-import if needed.

**Why this priority**: Provenance tracking ensures traceability—users need to know where an agent originated. Raw source preservation is a key risk mitigation: the raw `.agent.md` may contain frontmatter that Solune does not model, and discarding it would silently lose capabilities.

**Independent Test**: Can be fully tested by importing an agent, inspecting its stored record for catalog-origin fields, and verifying the raw source snapshot matches the originally fetched markdown byte-for-byte.

**Acceptance Scenarios**:

1. **Given** a user imports an agent, **When** the import is stored, **Then** the record includes the catalog source identifier ("awesome-copilot"), the original catalog entry URL, and the UTC timestamp of import.
2. **Given** an imported agent is stored, **When** the raw source snapshot is retrieved, **Then** it matches the upstream markdown exactly as fetched, including all frontmatter fields, whitespace, and formatting.
3. **Given** an imported agent exists, **When** the user views its details, **Then** catalog-origin metadata (source, original URL, import date) is visible in the agent card or detail view.

---

### User Story 6 - Duplicate Imported Agent into Custom Authoring Flow (Priority: P3)

As a project administrator, I want to duplicate an imported agent into the custom authoring flow so that I can modify the prompt, tools, or configuration while preserving the original imported snapshot for reference.

**Why this priority**: Duplication enables users to customize imported agents without altering the original snapshot. This is a lower priority because the core import-install pipeline works without it, but it completes the lifecycle by allowing adaptation.

**Independent Test**: Can be fully tested by duplicating an imported agent and verifying that a new editable agent is created in the custom authoring flow while the original imported snapshot remains unchanged.

**Acceptance Scenarios**:

1. **Given** an imported agent exists, **When** the user selects "Duplicate as Custom", **Then** a new agent is created in the custom authoring flow, pre-populated with the imported agent's name (suffixed with "Copy"), description, and prompt content.
2. **Given** the duplication completes, **When** the user views the agent list, **Then** both the original imported agent and the new custom copy exist independently—editing the copy does not affect the original.

---

### Edge Cases

- What happens when the upstream catalog index (llms.txt) is empty or malformed? The system displays an empty catalog with a message indicating no agents are available, and logs the parsing issue for diagnostics.
- What happens when a user imports an agent and then the upstream source changes? The stored snapshot is unaffected—import captures a point-in-time copy. The user can re-import to capture a newer version, which creates a new snapshot.
- What happens when the install step encounters a name collision (an agent with the same slug already exists in `.github/agents/`)? The system warns the user about the conflict before proceeding and allows them to rename or cancel.
- What happens when the raw agent markdown is extremely large (e.g., over 100 KB)? The system enforces a reasonable size limit consistent with GitHub file size constraints and rejects imports that exceed it, showing a clear error message.
- What happens if the user deletes an imported agent that was partially through an install attempt? The imported record is removed cleanly. If a partial branch or commit exists from a failed install, it is not cleaned up automatically—the user is informed.
- What happens when the catalog index references an agent whose raw markdown URL returns a 404? The import fails gracefully with a message that the agent source is no longer available.
- What happens if two users try to import the same agent simultaneously for the same project? The uniqueness constraint prevents duplicate records—one succeeds and the other receives a "already imported" notification.

## Requirements *(mandatory)*

### Functional Requirements

#### Catalog Browsing

- **FR-001**: System MUST provide a catalog browse endpoint that returns a list of available Awesome Copilot agents parsed from the cached catalog index.
- **FR-002**: System MUST cache the catalog index locally and serve browse/search requests from the cache, not from the upstream source on every request.
- **FR-003**: The browse endpoint MUST return at minimum: agent name, short description, and a reference identifier for each catalog entry.
- **FR-004**: System MUST support text-based search filtering over the cached catalog entries by agent name and description.
- **FR-005**: System MUST fetch the raw agent markdown from the upstream source only when a user explicitly imports a specific agent—not during browse or search.

#### Import Lifecycle

- **FR-006**: System MUST support an "imported" lifecycle state for agents, distinct from "active", "pending_pr", and "pending_deletion".
- **FR-007**: Import MUST store the complete raw agent markdown as a verbatim snapshot without stripping, normalizing, or reordering any content, including unknown frontmatter fields.
- **FR-008**: Import MUST store catalog-origin metadata alongside the agent record: source catalog identifier, original catalog entry reference, and UTC import timestamp.
- **FR-009**: Import MUST be a project-scoped operation—imported agents belong to a specific project and are not shared globally across Solune.
- **FR-010**: Import MUST NOT create any GitHub artifacts (branches, commits, PRs, or issues).
- **FR-011**: System MUST prevent duplicate imports of the same catalog agent within the same project.
- **FR-012**: System MUST validate the fetched raw agent markdown before storing (non-empty, valid text content).

#### Install Lifecycle

- **FR-013**: Install MUST be a separate action from import, triggered explicitly by the user after reviewing the imported agent.
- **FR-014**: Install MUST display a confirmation dialog before proceeding, showing the agent name, a summary of actions (issue creation, PR, files to commit), and a cancel option.
- **FR-015**: Install MUST create a tracking GitHub issue for the agent.
- **FR-016**: Install MUST create a branch, commit the raw agent markdown as the `.agent.md` file, generate and commit a matching `.prompt.md` routing file, and open a PR linked to the tracking issue.
- **FR-017**: The committed `.agent.md` file MUST be byte-for-byte identical to the stored raw snapshot—no content transformation is applied during install.
- **FR-018**: The `.prompt.md` routing file MUST be generated using the existing prompt-routing generation logic, deriving routing metadata from the raw agent content.
- **FR-019**: On successful install, the agent's lifecycle status MUST transition from "imported" to "pending_pr".
- **FR-020**: On failed install, the agent MUST remain in "imported" status and the user MUST be shown an error message.

#### Agent Management

- **FR-021**: Imported agents MUST be displayed in the project's agent list alongside custom and repository agents.
- **FR-022**: Imported agents MUST display a visually distinct "Imported" status badge in the agent card.
- **FR-023**: Imported agents MUST NOT be editable in-place. Editing is only available after the agent is installed or duplicated into the custom authoring flow.
- **FR-024**: Users MUST be able to delete an imported agent snapshot from the project without any GitHub side effects.
- **FR-025**: Users MUST be able to duplicate an imported agent into the custom authoring flow, creating an independent editable copy.
- **FR-026**: The custom agent authoring flow (AddAgentModal) MUST remain separate and unaffected by catalog import features.

### Key Entities

- **Catalog Entry**: A single agent listing from the Awesome Copilot catalog index. Key attributes: name, description, reference identifier (unique within the catalog), and the URL or path to the raw agent markdown.
- **Imported Agent**: A project-scoped snapshot of an Awesome Copilot agent. Key attributes: all existing agent fields (name, slug, description, prompt, tools, status), plus catalog-origin metadata (source catalog identifier, original catalog entry reference, import timestamp) and the raw source snapshot (complete verbatim markdown as fetched from upstream). Lifecycle status: "imported".
- **Installed Agent**: An imported agent that has been committed to the repository. Transitions from "imported" to "pending_pr" upon successful install. Retains all catalog-origin metadata and the raw snapshot for provenance tracking.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can browse the full Awesome Copilot agent catalog and find a specific agent via search within 5 seconds of opening the browse modal.
- **SC-002**: Users can import a catalog agent into their project in under 10 seconds (from clicking "Import" to seeing the "Imported" badge appear in the agent list).
- **SC-003**: Users can install an imported agent (creating a GitHub issue and PR with the correct files) in under 30 seconds from clicking "Add to project" through the confirmation step.
- **SC-004**: 100% of installed agents have a committed `.agent.md` file that is byte-for-byte identical to the originally fetched upstream raw markdown.
- **SC-005**: 100% of installed agents have a generated `.prompt.md` routing file committed alongside the `.agent.md` file in the same PR.
- **SC-006**: Users can visually distinguish imported, active, pending PR, and pending deletion agents at a glance via distinct status badges.
- **SC-007**: The existing custom agent authoring flow (create, edit, delete via AddAgentModal) continues to function identically with no behavioral changes.
- **SC-008**: Imported agent records include complete catalog-origin metadata (source, reference, import timestamp) that is visible to the user and traceable to the upstream source.

## Assumptions

- The Awesome Copilot catalog publishes a structured index (llms.txt or equivalent) that can be fetched and parsed to enumerate available agents with names, descriptions, and references to raw markdown files.
- The existing in-memory cache service (cache.py) is suitable for caching the catalog index with an appropriate TTL (e.g., 1 hour) and stale-while-revalidate pattern.
- The existing `commit_files_workflow()` function in `github_commit_workflow.py` can be reused for the install step without modification to its interface.
- The existing prompt-routing generation logic in `agent_creator.py` (`generate_config_files()`) can derive a valid `.prompt.md` from the raw agent markdown content.
- The `agent_configs` table schema can be extended with new columns for catalog-origin metadata and raw source snapshot without breaking existing queries or requiring a disruptive migration.
- The "imported" lifecycle status can be added to the existing `lifecycle_status` column as a new string value, following the established pattern (the column already stores "pending_pr", "active", "pending_deletion").
- Awesome Copilot agents may contain frontmatter fields (tools, MCP servers, model preferences) that Solune does not currently model in its agent schema; these are preserved in the raw snapshot and committed verbatim.
- Browse and search operate exclusively on the cached catalog index metadata. The system never fetches raw agent markdown during browse or search.
- Project-scoped isolation means imported agents for Project A are not visible to Project B, consistent with how existing agents are scoped.
- The existing frontend uses TanStack Query for data fetching; new hooks and API methods follow the established `useAgents` / `agentsApi` patterns.
