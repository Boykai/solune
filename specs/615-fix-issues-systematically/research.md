# Research: Fix Issues Systematically

**Feature**: 615-fix-issues-systematically | **Date**: 2026-04-03

## Research Task 1: Settings Model reasoning_effort Persistence

### Decision
Add `ai_reasoning_effort` column to both `user_preferences` and `global_settings` tables, and wire it through the full save/load pipeline in `settings_store.py`.

### Rationale
The frontend already sends `reasoning_effort` in the save payload (`PrimarySettings.tsx` line ~55). The backend model `AIPreferences` already has a `reasoning_effort` field. The gap is entirely in the storage layer:
1. No database column exists
2. `USER_PREFERENCE_COLUMNS` tuple omits it
3. `flatten_user_preferences_update()` column mapping omits it
4. `_merge_user_settings()` doesn't read it from DB

### Alternatives Considered
- **Store in localStorage only**: Rejected — agents run on the backend and need the setting.
- **Encode in model name** (e.g., "o3-xhigh"): Rejected — breaks model lookup, doesn't match API model IDs.
- **Separate settings table for AI config**: Rejected — over-engineering; adding one column is simpler.

### Files to Modify
- `solune/backend/src/migrations/038_fix_issues.sql` (NEW)
- `solune/backend/src/services/settings_store.py` (3 locations)
- `solune/backend/src/models/settings.py` (2 model classes)

---

## Research Task 2: Chat Optimistic Updates (Instant Message Rendering)

### Decision
The existing implementation in `useChat.ts` (lines 103-124) already provides optimistic updates. User messages are added to `localMessages` state immediately with `status: 'pending'`. Verify that `ChatInterface.tsx` merges `localMessages` into the rendered message list.

### Rationale
Code inspection reveals:
- `useChat.ts` creates a temp message with `generateId()` and adds it to `localMessages` before the API call
- On success, the temp message is removed (server response replaces it)
- On failure, the temp message is marked `status: 'failed'`
- `ChatInterface.tsx` should render both server messages and local messages

### Alternatives Considered
- **WebSocket for real-time sync**: Rejected — optimistic updates provide instant UX without infrastructure changes.
- **Server-Sent Events for message echo**: Rejected — SSE is already used for streaming responses, not message echo.

### Verification Steps
1. Check `ChatInterface.tsx` renders `localMessages` from `useChat` hook
2. Confirm pending messages show a loading/pending indicator
3. Test that failed messages show retry option

---

## Research Task 3: AI Enhance Feature Removal

### Decision
Remove the AI Enhance toggle from the frontend and the conditional bypass in the backend. All messages will be routed through `ChatAgentService` (the v0.2.0 agent-powered path).

### Rationale
The AI Enhance toggle was a legacy feature that allowed users to bypass the full agent pipeline for simpler title/description generation. With ChatAgentService (v0.2.0), all messages should go through the agent for consistent behavior. The toggle creates user confusion and two divergent code paths.

### Alternatives Considered
- **Keep toggle but default to ON**: Rejected — still maintains two code paths and user confusion.
- **Convert to "Quick Mode" toggle**: Rejected — adds complexity without clear value.
- **Remove backend field entirely**: Rejected — keep for backward compatibility; just always treat as `True`.

### Files to Modify
- Frontend: `ChatToolbar.tsx`, `ChatInterface.tsx`, `useChat.ts`
- Backend: `chat.py` (remove bypass branch), `models/chat.py` (default `ai_enhance=True`)

---

## Research Task 4: Task Recommendation Confirm/Reject Buttons

### Decision
No changes needed — the feature is already implemented. `TaskPreview.tsx`, `IssueRecommendationPreview.tsx`, and `StatusChangePreview.tsx` all have confirm/reject buttons. `ChatInterface.tsx` renders them based on `message.action_type`.

### Rationale
Code inspection confirms:
- `TaskPreview.tsx`: "Cancel" and "Create Task" buttons (lines 51-64)
- `IssueRecommendationPreview.tsx`: "Confirm & Create Issue" and "Reject" buttons (lines 299-312)
- `StatusChangePreview.tsx`: "Cancel" and "Update Status" buttons (lines 41-52)
- `ChatInterface.tsx`: Renders previews conditionally (lines 520-552)

### Verification Steps
1. Confirm chat agent responses set appropriate `action_type` values
2. Test that preview components render when expected
3. Verify confirm/reject API calls work end-to-end

---

## Research Task 5: User-Scoped Pipeline Storage

### Decision
Add `github_user_id` column to `pipeline_configs` table. Change the primary ownership model from project-scoped to user-scoped. Keep `project_id` as an optional association for filtering context.

### Rationale
Current schema: `UNIQUE(name, project_id)` means pipelines are tied to projects. Users who switch projects lose access to their custom pipelines. The fix adds user-level ownership so pipelines travel with the user.

### Alternatives Considered
- **Copy pipelines between projects**: Rejected — creates sync issues and data duplication.
- **Global pipelines (no owner)**: Rejected — multi-user scenarios need ownership.
- **Project-scoped with sharing links**: Rejected — over-engineering for the current use case.

### Migration Strategy
1. `ALTER TABLE pipeline_configs ADD COLUMN github_user_id TEXT`
2. Backfill: existing pipelines get the user ID from the current session context (or NULL for presets)
3. New unique constraint: Pipeline names unique per user
4. API changes: List endpoint returns user's pipelines across all projects

---

## Research Task 6: User-Scoped Chores Storage & Template Removal

### Decision
Add `github_user_id` column to `chores` table. Remove the PR/Issue template generation workflow. Keep chore definitions as user-scoped configurations.

### Rationale
The template generation process (`template_builder.py`) creates branches, commits, PRs, and tracking issues in the GitHub repository. This is a heavyweight side-effect for what should be a simple configuration. Removing it simplifies the chore lifecycle and eliminates repository pollution.

### Alternatives Considered
- **Keep template generation as opt-in**: Rejected — adds complexity and the issue specifically requests removal.
- **Move templates to local storage only**: Rejected — still maintains template code paths.
- **Archive template fields instead of removing**: Preferred — keep columns as nullable but don't populate them. Allows rollback.

### Migration Strategy
1. `ALTER TABLE chores ADD COLUMN github_user_id TEXT`
2. Keep existing template columns (nullable) for backward compatibility
3. Remove template generation code paths from `api/chores.py` create/update handlers
4. Remove `commit_template_to_repo()` calls
5. Frontend: Remove template-related UI and PR tracking display

---

## Research Task 7: Activity Page Hyperlinked PR#s and Issue#s

### Decision
Enhance `ActivityPage.tsx` `DetailView` component to detect and hyperlink PR and Issue references. Parse both structured `detail` fields (keys containing `pr_number`, `issue_number`, `pr_url`, `issue_url`) and summary text (`#123` patterns).

### Rationale
Activity events already store PR/Issue numbers in the `detail` JSON field. The current `DetailView` renders them as plain text. Adding hyperlinks is a frontend-only change for structured detail fields. For summary text, a regex-based linkifier handles `#N` patterns.

### Alternatives Considered
- **Backend renders HTML in summary**: Rejected — violates separation of concerns; summary should be plain text.
- **Add dedicated `links` array to activity event model**: Rejected — over-engineering; detail JSON already contains the data.
- **Only linkify detail fields, not summary**: Considered — but `#N` patterns in summary are common and should be linkified too.

### Implementation Approach
1. Create `LinkedDetailView` component that wraps `DetailView`
2. For detail fields: Check if key contains `url` and value is a string URL → render as `<a>`
3. For detail fields: Check if key contains `number` and companion `url` exists → render as linked `#N`
4. For summary text: Regex match `#(\d+)` and replace with `<a href="{repo_url}/issues/{N}">#{N}</a>`
5. Get repository URL from project context or settings

---

## Summary of All Decisions

| Issue | Decision | Complexity |
|-------|----------|-----------|
| Settings model fix | Add `ai_reasoning_effort` column + wire through store | Low |
| Instant message rendering | Verify existing optimistic updates work | Minimal |
| Remove AI Enhance | Remove toggle UI + bypass code path | Medium |
| Task confirm/reject | Already implemented — verify only | Minimal |
| User-scoped pipelines | Add `github_user_id`, change ownership model | Medium |
| User-scoped chores + remove templates | Add `github_user_id`, remove template generation | Medium-High |
| Activity hyperlinks | Enhance `DetailView` to linkify PR/Issue refs | Low |
