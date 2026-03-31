# Feature Specification: Auto-generate Labels for GitHub Parent Issues

**Feature Branch**: `001-auto-generate-labels`  
**Created**: 2026-03-31  
**Status**: Draft  
**Input**: User description: "Auto-generate labels for GitHub Parent Issues — There are three code paths that create parent issues, but only one (recommendation confirmation) auto-generates labels from content. The pipeline launch path hardcodes ["ai-generated"] + pipeline: labels, and the task creation path applies zero labels. The fix is a standalone AI label classifier that all paths can call."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pipeline-Launched Issues Get Content-Based Labels (Priority: P1)

As a project manager who launches work through pipelines, I want parent issues created via pipeline launch to automatically receive content-based labels (type, scope, domain) so that my project board is consistently organized without manual label triage.

Currently, when a pipeline creates a parent issue, the issue only receives a hardcoded "ai-generated" label plus the pipeline name label. This means all pipeline-created issues look identical on the project board regardless of whether they involve frontend work, backend changes, security fixes, or new features. Project managers must manually apply labels after every pipeline launch, creating extra toil and inconsistency.

**Why this priority**: Pipeline launch is a high-frequency path for issue creation and currently produces the most poorly labeled issues. Fixing this delivers the highest impact for project organization.

**Independent Test**: Can be fully tested by launching a pipeline with a descriptive issue and verifying that the resulting parent issue contains content-appropriate labels (e.g., a frontend performance issue receives "frontend", "performance", and "enhancement" labels in addition to "ai-generated" and the pipeline label).

**Acceptance Scenarios**:

1. **Given** a user launches a pipeline with a description like "Optimize database query performance for the user dashboard," **When** the parent issue is created, **Then** the issue receives content-derived labels (e.g., "enhancement", "backend", "performance", "database") in addition to the existing "ai-generated" and pipeline labels.
2. **Given** a user launches a pipeline with a minimal description, **When** the parent issue is created, **Then** the issue still receives at minimum the "ai-generated" label, a default type label ("feature"), and the pipeline label — maintaining backward compatibility.
3. **Given** the label classification process fails (e.g., AI service unavailable), **When** the parent issue is created, **Then** the system falls back to the current hardcoded labels ("ai-generated" + pipeline label) and the issue is created successfully without any disruption.

---

### User Story 2 - Task-Created Issues Get Content-Based Labels (Priority: P2)

As a team member creating tasks directly, I want parent issues created through the task creation flow to automatically receive content-based labels so that they are findable, filterable, and consistently categorized on the project board.

Currently, the task creation path produces parent issues with zero labels. This means tasks created through this path are invisible to any label-based filter, making them hard to triage, prioritize, and organize alongside issues created through other paths.

**Why this priority**: Task creation currently applies no labels at all, making it the most broken path. However, it is a lower-frequency path compared to pipeline launch, so it ranks P2.

**Independent Test**: Can be fully tested by creating a task with a title like "Fix login page accessibility issues" and verifying that the resulting parent issue receives relevant labels such as "bug", "frontend", and "accessibility" along with "ai-generated."

**Acceptance Scenarios**:

1. **Given** a user creates a task with title "Fix login page accessibility issues" and a description detailing screen reader problems, **When** the parent issue is created, **Then** the issue receives content-derived labels (e.g., "bug", "frontend", "accessibility") plus the "ai-generated" label.
2. **Given** a user creates a task with only a title and no description, **When** the parent issue is created, **Then** the system classifies labels from the title alone and applies at minimum "ai-generated" and a default type label ("feature").
3. **Given** the label classification process fails, **When** the parent issue is created, **Then** the system falls back to applying only the "ai-generated" label and the issue is created successfully.

---

### User Story 3 - Agent Tool Issues Support Label Generation (Priority: P3)

As a user interacting with the AI agent, I want issues created through the agent's issue recommendation tool to support automatic label generation so that even when the agent does not explicitly specify labels, the created issue is still properly categorized.

The agent framework currently has no label parameter for issue creation. When the agent creates issues, they receive whatever labels the recommendation confirmation path provides — but only if the agent goes through that flow. A direct agent tool call produces no labels.

**Why this priority**: This is a parallel enhancement that extends label coverage to the agent tool path. It has lower priority because the agent often routes through the recommendation confirmation path which already generates labels.

**Independent Test**: Can be fully tested by invoking the agent's issue creation tool without specifying labels and verifying that the resulting issue receives auto-generated content-based labels.

**Acceptance Scenarios**:

1. **Given** the AI agent creates an issue recommendation without specifying labels, **When** the issue is created, **Then** the system auto-generates labels from the issue title and description and applies them.
2. **Given** the AI agent creates an issue recommendation and explicitly provides labels, **When** the issue is created, **Then** the agent-provided labels are used instead of auto-generated labels.
3. **Given** the AI agent provides some labels but the auto-generated set includes additional valid labels, **When** the issue is created, **Then** the agent-provided labels take precedence and no additional auto-generated labels are merged (to respect agent intent).

---

### User Story 4 - Centralized Label Classification Service (Priority: P1)

As a system maintainer, I want a single, reusable label classification capability that all issue creation paths share so that label governance is consistent, maintainable, and not duplicated across multiple code paths.

Currently, the label validation logic exists in only one place (the recommendation confirmation path). The pipeline launch and task creation paths have no access to this capability. A shared service ensures every path produces labels using the same taxonomy, validation rules, and fallback behavior.

**Why this priority**: This is the foundational building block that enables all other user stories. Without a centralized classification capability, each path would need its own duplicate logic, increasing maintenance burden and inconsistency risk.

**Independent Test**: Can be fully tested by providing sample issue titles and descriptions to the classification capability and verifying it returns valid, relevant labels from the predefined taxonomy.

**Acceptance Scenarios**:

1. **Given** an issue title and description are provided to the label classifier, **When** classification completes, **Then** the result contains only labels from the predefined label taxonomy (type, scope, domain categories).
2. **Given** the label classifier returns results, **When** the labels are checked, **Then** exactly one type label is always present (defaulting to "feature" if no type could be determined) and the "ai-generated" label is always included.
3. **Given** the label classifier receives input containing terms matching multiple scope labels (e.g., "Update the API endpoint and the frontend form"), **When** classification completes, **Then** all applicable scope labels are returned (e.g., both "backend" and "frontend" and "api").

---

### Edge Cases

- What happens when the issue title and description are empty or contain only whitespace? The classifier should return the minimum default labels: "ai-generated" and "feature."
- What happens when the AI returns labels not in the predefined taxonomy? Invalid labels must be filtered out; only labels matching the predefined set are applied.
- What happens when the AI returns duplicate labels? Duplicates must be removed before applying labels to the issue.
- What happens when network or AI service errors occur during classification? The system must fall back gracefully to the pre-existing behavior for that path (hardcoded labels or no labels) and must never block issue creation.
- What happens when the AI returns no type label? The system must default to "feature" as the type label.
- What happens when the predefined label taxonomy is updated with new labels? The classifier must dynamically reference the current taxonomy rather than a hardcoded copy, so new labels are automatically available.
- What happens when an issue description is extremely long? The classifier should handle descriptions up to the maximum issue body size without failure, truncating input to the classifier if needed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a centralized label classification capability that accepts an issue title and optional description and returns a set of labels from the predefined taxonomy.
- **FR-002**: System MUST validate all classifier output against the predefined label set, discarding any labels not in the taxonomy.
- **FR-003**: System MUST ensure the "ai-generated" label is always present in the returned label set.
- **FR-004**: System MUST ensure exactly one type label is present in the returned label set, defaulting to "feature" if no type label is classified.
- **FR-005**: System MUST integrate label classification into the pipeline launch path, merging classified labels with the existing pipeline-specific labels.
- **FR-006**: System MUST integrate label classification into the task creation path, applying classified labels to newly created issues.
- **FR-007**: System MUST support an optional labels parameter on the agent issue creation tool, using auto-generated labels when none are provided.
- **FR-008**: System MUST wrap label classification in error handling so that classification failure never blocks or delays issue creation.
- **FR-009**: System MUST fall back to path-specific default labels when classification fails (e.g., pipeline path falls back to "ai-generated" + pipeline label; task path falls back to "ai-generated").
- **FR-010**: System MUST dynamically reference the current predefined label taxonomy rather than hardcoding label values in the classification prompt.
- **FR-011**: System MUST deduplicate labels before applying them to an issue.
- **FR-012**: System MUST preserve all existing labels that a path already applies (e.g., pipeline labels) when merging with classified labels.

### Key Entities

- **Label Taxonomy**: The predefined set of valid labels organized by category (type, scope, domain, auto-applied). This is the single source of truth for what labels the classifier may return. Categories include type labels (feature, bug, enhancement, refactor, documentation, testing, infrastructure), scope labels (frontend, backend, database, api), and domain labels (security, performance, accessibility, ux).
- **Label Classification Request**: An input consisting of an issue title and optional description, submitted to the classifier for label inference.
- **Label Classification Result**: The output of the classifier containing a validated, deduplicated list of labels guaranteed to include "ai-generated" and exactly one type label.
- **Issue Creation Path**: One of three distinct flows that produce parent issues — pipeline launch, task creation, or agent recommendation. Each path calls the shared label classifier and merges the result with any path-specific labels.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of parent issues created via pipeline launch receive at least one content-derived label beyond "ai-generated" and the pipeline label, when the classification service is available.
- **SC-002**: 100% of parent issues created via task creation receive at least "ai-generated" and a type label, compared to zero labels today.
- **SC-003**: Label classification failure never blocks issue creation — 100% of issue creation attempts succeed regardless of classifier availability.
- **SC-004**: All three issue creation paths (pipeline launch, task creation, agent tool) use the same classification capability, reducing label logic duplication to a single shared component.
- **SC-005**: 90% or more of auto-generated labels are contextually accurate when reviewed against the issue title and description (measured by spot-checking a sample of 20 issues).
- **SC-006**: Label classification adds no more than 3 seconds of additional latency to the issue creation flow under normal conditions.
- **SC-007**: The predefined label taxonomy can be updated in a single location without requiring changes to any of the three issue creation paths.

## Assumptions

- The existing AI completion provider (used by the recommendation confirmation path) is available and suitable for the label classification capability. No new AI service or provider is required.
- The predefined label taxonomy in the constants module is the authoritative source and does not need to be extended for this feature (though the system should accommodate future additions automatically).
- The recommendation confirmation path already produces satisfactory label quality and does not need changes — this feature focuses on bringing the other two paths to parity.
- Label classification results do not need to be persisted or cached; each classification is a one-time operation during issue creation.
- Sub-issue labels (e.g., "sub-issue") are out of scope for this feature — only parent issue labels are affected.
- Repository-specific labels (fetched from GitHub) are out of scope for the initial implementation. The classifier validates against the predefined constant taxonomy only, with the option to extend to repo-specific labels in the future.
