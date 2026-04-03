# Feature Specification: Fix Issues Systematically

**Issue**: #615 | **Branch**: `615-fix-issues-systematically` | **Date**: 2026-04-03

## Summary

A set of seven systematic fixes addressing Settings model persistence, chat UX improvements, storage architecture for pipelines/chores, and Activity page hyperlinks.

## User Stories

### P1 — Settings Model Selection Fix

**As a** user configuring AI model preferences,
**I want** all model variants (including reasoning effort levels like GPT5.4 XHigh) to be selectable and saved,
**So that** my chosen model configuration persists across sessions and is used by agents.

**Acceptance Criteria:**
- Given I select a model with reasoning effort (e.g., "o3 (XHigh)") on the Settings page
- When I click Save and reload the page
- Then the selected model and reasoning effort are preserved
- And agents use the saved reasoning effort level during execution

### P1 — Instant User Message Rendering in App Chat

**As a** user sending a message in the app chat,
**I want** my message to appear immediately in the chat window,
**So that** I have instant feedback before the AI agent responds.

**Acceptance Criteria:**
- Given I type a message and press Send
- When the message is submitted
- Then it renders instantly in the chat as a user bubble (optimistic update)
- And a loading indicator shows while the agent processes

### P1 — Remove AI Enhance from App Chat

**As a** user of the app chat,
**I want** all messages to be handled uniformly by the chat agent,
**So that** there is no confusing toggle and all messages get full agent processing.

**Acceptance Criteria:**
- Given I open the chat interface
- When I view the toolbar
- Then there is no AI Enhance toggle
- And all messages are routed through ChatAgentService

### P2 — Task Recommendation Confirm/Reject Buttons

**As a** user receiving task recommendations from the chat agent,
**I want** confirm and reject buttons to appear with each recommendation,
**So that** I can approve or dismiss suggestions directly in the chat.

**Acceptance Criteria:**
- Given the chat agent provides a task recommendation
- When the recommendation message renders
- Then Confirm and Reject buttons are visible
- And clicking Confirm creates the task
- And clicking Reject dismisses the recommendation

### P2 — User-Scoped Agent Pipeline Storage

**As a** user managing agent pipelines,
**I want** pipeline configurations stored per-user (not per-project),
**So that** any pipeline can be reused across all my projects.

**Acceptance Criteria:**
- Given I create or edit a pipeline
- When I switch to a different project
- Then the pipeline is still available
- And pipelines are stored at user level in the database

### P2 — User-Scoped Chores Storage (Remove PR/Issue Templates)

**As a** user managing chores,
**I want** chore configurations stored per-user and the PR/Issue template generation removed,
**So that** chores are reusable across projects without repository side-effects.

**Acceptance Criteria:**
- Given I create or edit a chore
- When I switch projects
- Then the chore is still available
- And no GitHub PR or Issue template is generated

### P2 — Activity Page Hyperlinked PR#s and Issue#s

**As a** user viewing the Activity page,
**I want** PR numbers and Issue numbers to be clickable hyperlinks,
**So that** I can navigate directly to the relevant GitHub resource.

**Acceptance Criteria:**
- Given an activity event references a PR# or Issue#
- When the event renders on the Activity page
- Then the PR# and Issue# are rendered as clickable hyperlinks to GitHub
