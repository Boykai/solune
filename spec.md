# Feature Specification: Harden Phase 1 — Critical Bug Fixes

**Feature Branch**: `001-harden-phase1-bugfixes`  
**Created**: 2026-04-10  
**Status**: Draft  
**Input**: User description: "Harden Phase 1 — Critical Bug Fixes: Fix memory leak in pipeline\_state\_store, fix update\_agent lifecycle status, fix \_extract\_agent\_preview malformed configs"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bounded Lock Dictionary Prevents Memory Leak (Priority: P1)

A platform operator runs Solune as a long-lived service handling many projects over days or weeks. The per-project launch-lock dictionary must not grow without bound; once a configurable capacity is reached, the oldest (least-recently-used) entries are evicted so the process's memory footprint stays stable.

**Why this priority**: An unbounded dictionary that accumulates one lock per unique project ID is a memory leak. In production this degrades performance over time and can eventually exhaust available memory, making it the highest-priority fix.

**Independent Test**: Create locks for more unique project IDs than the configured maximum and verify the dictionary size never exceeds that maximum. Confirm that recently-used entries survive eviction while idle entries are removed first.

**Acceptance Scenarios**:

1. **Given** the lock dictionary has reached its maximum capacity, **When** a lock is requested for a new project ID, **Then** the dictionary evicts the least-recently-used entry and creates a new lock without exceeding the capacity limit.
2. **Given** a lock already exists for a project ID, **When** that lock is requested again, **Then** the same lock instance is returned and the entry is refreshed to the most-recently-used position.
3. **Given** locks have been evicted due to capacity, **When** a lock is requested for an evicted project ID, **Then** a new lock is transparently created without errors.
4. **Given** the service has been running for an extended period with many unique project IDs, **When** the dictionary reaches capacity, **Then** memory consumption remains stable and does not continue growing.

---

### User Story 2 - Updated Local Agents Show Correct Lifecycle Status (Priority: P1)

A developer updates an existing local agent's configuration (name, description, system prompt, or tools). After the update PR is opened, the agent's lifecycle status must reflect that a PR is pending so the UI and downstream logic treat the agent as "awaiting merge" rather than "active".

**Why this priority**: Showing an updated agent as still active misleads users into thinking the change is live. This can cause confusion, incorrect behaviour during chat refinement, and breaks the expected create → pending → merge → active lifecycle. It is a correctness bug with direct user-facing impact.

**Independent Test**: Update an existing local agent's configuration, verify the returned agent object has lifecycle status set to "pending PR", and confirm the persisted database row reflects the same status along with the new PR number and branch name.

**Acceptance Scenarios**:

1. **Given** an existing local agent with "active" status, **When** its configuration is updated and a PR is opened, **Then** the agent's lifecycle status is set to "pending PR" in both the response and the database.
2. **Given** a repo-sourced agent (ID starting with "repo:"), **When** it is updated for the first time, **Then** a new local record is inserted with lifecycle status "pending PR".
3. **Given** an agent with "pending deletion" status, **When** an update is attempted, **Then** the update is rejected with an appropriate error message.
4. **Given** only runtime preferences are changed (model, icon), **When** the update is saved, **Then** no PR is opened and the lifecycle status remains unchanged.

---

### User Story 3 - Malformed Agent Configs Are Rejected During Chat Refinement (Priority: P1)

During the multi-turn agent chat refinement flow, the AI may produce a config block with structurally invalid fields (e.g., `tools: "read"` as a string instead of a list, or `tools: [123, null, {}]` with non-string elements). The extraction logic must detect these malformed-but-JSON-parseable configs and return nothing rather than passing invalid data to downstream validation or the UI.

**Why this priority**: Malformed configs that escape validation break the chat refinement experience — users see errors or broken previews. Since this sits in a critical interactive flow, it has equal priority with the other fixes.

**Independent Test**: Supply various malformed config payloads (tools as a string, tools containing non-string elements, missing required fields, non-dict top-level JSON) and verify that each one is rejected by returning no preview rather than propagating invalid data.

**Acceptance Scenarios**:

1. **Given** an AI response containing `tools: "read"` (string instead of list), **When** the config is extracted, **Then** the result is empty (no preview returned).
2. **Given** an AI response containing `tools: [123, null, {}]` (list with non-string elements), **When** the config is extracted, **Then** the result is empty (no preview returned).
3. **Given** an AI response with a valid config block, **When** the config is extracted, **Then** the preview is returned with all fields correctly populated.
4. **Given** an AI response with missing or empty `name` field, **When** the config is extracted, **Then** the result is empty.
5. **Given** an AI response with no config block at all, **When** extraction is attempted, **Then** the result is empty.

---

### Edge Cases

- What happens when the lock dictionary capacity is exactly 1? The dictionary should still function correctly, evicting the single entry when a new one is added.
- What happens when two concurrent requests try to create a lock for the same new project ID? Only one lock should be created; the second request should receive the same lock instance.
- What happens when an agent update PR workflow fails after the local record has been partially modified? The update should fail atomically — no partial lifecycle status change should be persisted.
- What happens when the AI response contains multiple `agent-config` code blocks? Only the first match should be processed.
- What happens when tools contain mixed valid and invalid entries like `["read", 123, "write"]`? The entire config should be rejected rather than silently dropping invalid entries.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The per-project launch-lock collection MUST enforce a maximum capacity; when the limit is reached, the least-recently-used entry MUST be evicted before adding a new one.
- **FR-002**: Accessing an existing lock MUST refresh it to the most-recently-used position so that actively-used projects are not prematurely evicted.
- **FR-003**: When a local agent's configuration is updated and a PR is opened, the system MUST set the agent's lifecycle status to "pending PR" in both the returned object and the persisted record.
- **FR-004**: When a repo-sourced agent is updated for the first time, the system MUST insert a new local record with lifecycle status "pending PR", the new PR number, and the branch name.
- **FR-005**: The agent config extraction logic MUST reject configs where the `tools` field is not a list.
- **FR-006**: The agent config extraction logic MUST reject configs where any element in the `tools` list is not a non-empty string.
- **FR-007**: The agent config extraction logic MUST reject configs where the `name` field is missing or empty.
- **FR-008**: The agent config extraction logic MUST return nothing (rather than raising an exception) for any structurally invalid config.

### Key Entities

- **BoundedDict**: A dictionary with a maximum size that evicts least-recently-used entries when capacity is exceeded. Used to store per-project launch locks.
- **Agent Lifecycle Status**: The state machine governing an agent's progression through create → pending PR → active (after merge) → pending deletion. The "pending PR" status indicates an open PR that has not yet been merged.
- **AgentPreview**: The intermediate representation of an AI-generated agent configuration extracted from a chat response. Must pass structural validation before being presented to the user.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The per-project lock collection never exceeds its configured maximum size, regardless of how many unique projects are processed — verified by creating entries beyond the limit and asserting the count stays bounded.
- **SC-002**: Memory consumption of the lock collection stabilises after reaching capacity and does not continue to grow over time.
- **SC-003**: 100% of agent updates that open a PR result in the agent's lifecycle status being persisted as "pending PR" — verified by database inspection after each update path (existing local agent, first-time repo agent).
- **SC-004**: 100% of malformed agent config payloads (non-list tools, non-string list elements, missing name) are rejected without exceptions — verified by unit tests covering each invalid variant.
- **SC-005**: All existing tests continue to pass after the fixes, confirming no regressions are introduced.
- **SC-006**: The chat refinement flow completes successfully with valid agent configs and gracefully handles invalid ones without user-visible errors.

## Assumptions

- The bounded dictionary implementation (BoundedDict) already exists in the codebase and provides `touch()` for LRU refresh and automatic eviction on insert when at capacity.
- A maximum capacity of 10,000 entries for the lock dictionary is appropriate for production workloads — this is large enough to avoid premature eviction in typical deployments while preventing unbounded growth.
- The three SQL paths for agent updates (update existing local, insert new from repo, runtime-only preferences) are the complete set of update scenarios.
- The `_extract_agent_preview` method is the single extraction point for agent configs from AI responses in the chat refinement flow.
- Rejecting the entire config when any tools element is invalid (rather than filtering out bad entries) is the correct behaviour to force the AI to produce a fully valid config on retry.
