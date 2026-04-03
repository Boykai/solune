# Implementation Plan: Fix Issues Systematically

**Branch**: `615-fix-issues-systematically` | **Date**: 2026-04-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/615-fix-issues-systematically/spec.md`

## Summary

Seven systematic fixes addressing critical bugs and UX improvements across Settings (model persistence), Chat (instant rendering, AI Enhance removal, task confirm/reject), Pipeline/Chores (user-scoped storage), and Activity (hyperlinked references). The backend uses Python/FastAPI with SQLite (aiosqlite); the frontend uses React/TypeScript with Vite. Changes span database migrations, API endpoints, service layer logic, and frontend components.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.x (frontend)
**Primary Dependencies**: FastAPI, aiosqlite, React 18, TanStack Query, Tailwind CSS, shadcn/ui
**Storage**: SQLite via aiosqlite (settings, pipelines, chores, activity, chat)
**Testing**: Vitest + React Testing Library (frontend), pytest (backend)
**Target Platform**: Web application (Linux server backend, browser frontend)
**Project Type**: Web application (frontend + backend)
**Performance Goals**: Instant message rendering (<50ms optimistic update), settings save <200ms
**Constraints**: No breaking API changes; backward-compatible database migrations
**Scale/Scope**: Single-user desktop app with GitHub integration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | spec.md created with prioritized user stories and acceptance criteria |
| II. Template-Driven Workflow | ✅ PASS | Following canonical plan template structure |
| III. Agent-Orchestrated Execution | ✅ PASS | Single-responsibility plan agent producing plan artifacts |
| IV. Test Optionality | ✅ PASS | Tests not explicitly required; existing test infrastructure covers regression |
| V. Simplicity and DRY | ✅ PASS | Each fix is minimal and surgical; no premature abstraction |

**Gate Result**: ✅ ALL PASS — Proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/615-fix-issues-systematically/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research findings
├── data-model.md        # Phase 1 data model changes
├── quickstart.md        # Phase 1 implementation quickstart
├── contracts/           # Phase 1 API contract changes
│   └── settings-api.yaml
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
solune/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── chat.py              # Chat endpoints (AI Enhance removal)
│   │   │   ├── pipelines.py         # Pipeline endpoints (user-scoped)
│   │   │   ├── chores.py            # Chores endpoints (user-scoped, remove templates)
│   │   │   └── activity.py          # Activity endpoints (no changes needed)
│   │   ├── models/
│   │   │   ├── settings.py          # Settings models (add reasoning_effort)
│   │   │   ├── pipeline.py          # Pipeline models (add github_user_id)
│   │   │   ├── chores.py            # Chores models (add github_user_id, remove template fields)
│   │   │   └── chat.py              # Chat models (simplify ai_enhance)
│   │   ├── services/
│   │   │   ├── settings_store.py    # Settings persistence (add reasoning_effort column)
│   │   │   ├── chores/
│   │   │   │   └── template_builder.py  # Template generation (remove)
│   │   │   └── activity_logger.py   # Activity logging (ensure PR/Issue URLs in detail)
│   │   └── migrations/
│   │       └── 038_fix_issues.sql   # New migration for all schema changes
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   │   ├── ChatInterface.tsx    # Remove AI Enhance state/storage
│   │   │   │   ├── ChatToolbar.tsx      # Remove AI Enhance toggle button
│   │   │   │   ├── TaskPreview.tsx      # Verify confirm/reject buttons (already exists)
│   │   │   │   └── IssueRecommendationPreview.tsx  # Verify (already exists)
│   │   │   ├── settings/
│   │   │   │   └── PrimarySettings.tsx  # Verify reasoning_effort save (already sends it)
│   │   │   ├── pipeline/
│   │   │   │   └── SavedWorkflowsList.tsx  # Update to show cross-project pipelines
│   │   │   └── chores/
│   │   │       └── ChoreCard.tsx        # Remove template generation UI
│   │   ├── pages/
│   │   │   └── ActivityPage.tsx         # Add hyperlinked PR#/Issue# rendering
│   │   ├── hooks/
│   │   │   └── useChat.ts              # Remove ai_enhance parameter
│   │   ├── services/
│   │   │   └── api.ts                  # Update pipeline/chores API paths
│   │   └── types/
│   │       └── index.ts                # Update pipeline/chores types
│   └── tests/
```

**Structure Decision**: Web application with `solune/backend/` and `solune/frontend/` directories. All changes are modifications to existing files plus one new migration file.

## Implementation Phases

### Phase A: Settings Model Selection Fix (P1)

**Root Cause**: `ai_reasoning_effort` column missing from database schema, `USER_PREFERENCE_COLUMNS`, column mapping, and merge logic in `settings_store.py`.

**Changes Required**:

1. **New migration** `038_fix_issues.sql`:
   - `ALTER TABLE user_preferences ADD COLUMN ai_reasoning_effort TEXT`
   - `ALTER TABLE global_settings ADD COLUMN ai_reasoning_effort TEXT`

2. **`settings_store.py`**:
   - Add `"ai_reasoning_effort"` to `USER_PREFERENCE_COLUMNS` tuple
   - Add `"reasoning_effort": "ai_reasoning_effort"` to column mapping in `flatten_user_preferences_update()`
   - Add `reasoning_effort=str(_pick("ai_reasoning_effort") or "")` to `_merge_user_settings()` AIPreferences

3. **`models/settings.py`**:
   - Add `ai_reasoning_effort: str | None = None` to `UserPreferencesRow`
   - Add `ai_reasoning_effort: str | None = None` to `GlobalSettingsRow`

4. **Frontend** (already working — sends `reasoning_effort` in save payload)

**Dependencies**: None (standalone fix)

### Phase B: Chat UX Improvements (P1)

#### B1: Instant User Message Rendering

**Current State**: `useChat.ts` already implements optimistic updates (lines 103-124). User messages appear immediately with `status: 'pending'` and are removed/updated on API response.

**Verification Needed**: Confirm `ChatInterface.tsx` renders `localMessages` alongside server messages. If messages from `localMessages` are rendered with pending status, this is already working. If not, ensure `allMessages` merge includes `localMessages`.

**Changes Required**: Verify existing implementation; fix if `localMessages` are not being rendered in the message list.

#### B2: Remove AI Enhance from App Chat

**Changes Required**:

1. **`ChatToolbar.tsx`**:
   - Remove `aiEnhance` prop and `onAiEnhanceChange` callback
   - Remove the AI Enhance toggle button (Sparkles icon section)

2. **`ChatInterface.tsx`**:
   - Remove `AI_ENHANCE_STORAGE_KEY` constant
   - Remove `aiEnhance` state and `handleAiEnhanceChange` handler
   - Remove localStorage persistence for AI Enhance
   - Remove `aiEnhance` prop from `<ChatToolbar>` usage
   - Always pass `aiEnhance: true` (or remove the option) when calling `sendMessage`

3. **`useChat.ts`**:
   - Remove `aiEnhance` from `sendMessage` options
   - Always send `ai_enhance: true` to API (or remove the field)

4. **Backend `chat.py`**:
   - Remove the `ai_enhance=False` bypass branch (lines ~1080-1112)
   - Route all messages through ChatAgentService
   - Keep `ai_enhance` field in `ChatMessageRequest` for backward compatibility but ignore it

5. **Backend `models/chat.py`**:
   - Mark `ai_enhance` as deprecated or default to `True`

**Dependencies**: None (standalone fix)

#### B3: Task Recommendation Confirm/Reject Buttons

**Current State**: Already implemented! `TaskPreview.tsx` has Cancel/Create Task buttons, `IssueRecommendationPreview.tsx` has Confirm/Reject buttons, `StatusChangePreview.tsx` has Cancel/Update buttons.

**Verification Needed**: Confirm these components render correctly when the chat agent provides recommendations. The `ChatInterface.tsx` renders them conditionally based on `message.action_type`.

**Changes Required**: Verify existing implementation works end-to-end. If task recommendations from the chat agent don't trigger the preview components, investigate the `action_type` mapping.

### Phase C: User-Scoped Pipeline Storage (P2)

**Current State**: Pipelines stored with `project_id` (project-scoped). Unique constraint: `UNIQUE(name, project_id)`.

**Changes Required**:

1. **Migration `038_fix_issues.sql`**:
   - Add `github_user_id TEXT` column to `pipeline_configs`
   - Backfill existing rows with a default user ID or NULL
   - Update unique constraint to `UNIQUE(name, github_user_id)` instead of `UNIQUE(name, project_id)`

2. **Backend `models/pipeline.py`**:
   - Add `github_user_id: str` field to `PipelineConfig`
   - Keep `project_id` as optional for backward compatibility

3. **Backend `api/pipelines.py`**:
   - Change list endpoint to filter by `github_user_id` from session
   - Change create/update to store `github_user_id`
   - Keep `project_id` in URL but make it optional for filtering

4. **Backend pipeline store**:
   - Update queries to use `github_user_id` for ownership
   - Allow pipelines to be listed across projects

5. **Frontend `SavedWorkflowsList.tsx`**:
   - Update to show all user pipelines regardless of current project

**Dependencies**: Requires session/auth to provide `github_user_id`

### Phase D: User-Scoped Chores Storage & Remove Template Generation (P2)

**Current State**: Chores stored with `project_id`. Template generation creates branches, commits, PRs, and tracking issues in GitHub.

**Changes Required**:

1. **Migration `038_fix_issues.sql`**:
   - Add `github_user_id TEXT` column to `chores`
   - Remove or deprecate template-related columns: `template_path`, `template_content`, `current_issue_number`, `current_issue_node_id`, `pr_number`, `pr_url`, `tracking_issue_number`
   - Update unique constraint to `UNIQUE(name, github_user_id)`

2. **Backend `models/chores.py`**:
   - Add `github_user_id: str` field
   - Mark template fields as optional/deprecated

3. **Backend `api/chores.py`**:
   - Change list/create/update to use `github_user_id`
   - Remove template generation calls from create/update endpoints
   - Remove or deprecate `GET /chores/{project_id}/templates` endpoint

4. **Backend `services/chores/template_builder.py`**:
   - Remove or deprecate `commit_template_to_repo()` and `update_template_in_repo()`
   - Keep `build_template()` if still needed for chore content display

5. **Frontend chores components**:
   - Remove template-related UI elements from `ChoreCard.tsx`
   - Remove PR/Issue tracking display
   - Update `AddChoreModal.tsx` to not require template path

**Dependencies**: Requires session/auth to provide `github_user_id`

### Phase E: Activity Page Hyperlinked PR#s and Issue#s (P2)

**Current State**: Activity events store PR/Issue numbers in `detail` JSON field. `DetailView` renders them as plain text key-value pairs.

**Changes Required**:

1. **Frontend `ActivityPage.tsx`**:
   - Create a `HyperlinkDetail` component that detects PR/Issue references
   - Parse `detail` fields for keys like `pr_number`, `issue_number`, `pr_url`, `issue_url`
   - Render them as `<a>` tags linking to GitHub
   - Also parse summary text for `#123` patterns and linkify them

2. **Backend `activity_logger.py`**:
   - Ensure `log_event()` calls include `pr_url`/`issue_url` in the `detail` dict when available
   - Add a utility to construct GitHub URLs from repo + number

3. **Backend callers of `log_event()`**:
   - Audit chores, pipelines, and other services to ensure they pass PR/Issue URLs in activity events

**Dependencies**: Requires knowing the GitHub repository URL (available from project settings)

## Execution Order

```
Phase A (Settings Fix) ──┐
Phase B (Chat UX)     ───┤── Can run in parallel (independent)
Phase E (Activity)    ───┘
                          │
Phase C (Pipelines)  ─────┤── Depends on migration from Phase A
Phase D (Chores)     ─────┘   (shared migration file 038_fix_issues.sql)
```

**Recommended Order**: A → B → E → C → D (sequential for safety, C/D share migration patterns)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Migration breaks existing data | Low | High | Use `ALTER TABLE ADD COLUMN` (safe for SQLite) |
| Removing AI Enhance breaks chat flow | Medium | Medium | Keep `ai_enhance` field, just always route through ChatAgentService |
| User-scoped storage breaks existing pipelines/chores | Medium | High | Backfill `github_user_id` from existing project owner; keep `project_id` for filtering |
| Activity hyperlinks break for events without URLs | Low | Low | Graceful fallback to plain text when URL not in detail |

## Complexity Tracking

> No constitution violations identified. All changes follow YAGNI and DRY principles.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

## Post-Design Constitution Re-Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | All 7 fixes have user stories with acceptance criteria |
| II. Template-Driven Workflow | ✅ PASS | Plan follows canonical template |
| III. Agent-Orchestrated Execution | ✅ PASS | Plan agent produces all required artifacts |
| IV. Test Optionality | ✅ PASS | Existing tests cover regression; no new tests mandated |
| V. Simplicity and DRY | ✅ PASS | Minimal changes per fix; shared migration file |
