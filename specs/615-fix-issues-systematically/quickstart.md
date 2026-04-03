# Quickstart: Fix Issues Systematically

**Feature**: 615-fix-issues-systematically | **Date**: 2026-04-03

## Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- SQLite3
- Git

## Development Setup

```bash
# Clone and checkout
git checkout 615-fix-issues-systematically

# Backend setup
cd solune/backend
pip install -e ".[dev]"

# Frontend setup
cd ../frontend
npm install
```

## Implementation Order

### Step 1: Database Migration (5 min)

Create `solune/backend/src/migrations/038_fix_issues.sql`:

```sql
ALTER TABLE user_preferences ADD COLUMN ai_reasoning_effort TEXT;
ALTER TABLE global_settings ADD COLUMN ai_reasoning_effort TEXT;
ALTER TABLE pipeline_configs ADD COLUMN github_user_id TEXT;
ALTER TABLE chores ADD COLUMN github_user_id TEXT;
```

### Step 2: Settings Fix — Backend (15 min)

**File**: `solune/backend/src/services/settings_store.py`

1. Add `"ai_reasoning_effort"` to `USER_PREFERENCE_COLUMNS`
2. Add `"reasoning_effort": "ai_reasoning_effort"` to `flatten_user_preferences_update()` column map under `"ai"`
3. Add `reasoning_effort=str(_pick("ai_reasoning_effort") or "")` to `_merge_user_settings()` AIPreferences construction

**File**: `solune/backend/src/models/settings.py`

1. Add `ai_reasoning_effort: str | None = None` to `UserPreferencesRow`
2. Add `ai_reasoning_effort: str | None = None` to `GlobalSettingsRow`

### Step 3: Chat UX — Remove AI Enhance (20 min)

**Frontend**:

1. `ChatToolbar.tsx`: Remove `aiEnhance` prop, `onAiEnhanceChange` callback, and Sparkles toggle button
2. `ChatInterface.tsx`: Remove `AI_ENHANCE_STORAGE_KEY`, `aiEnhance` state, localStorage logic, and toolbar prop
3. `useChat.ts`: Remove `aiEnhance` from `sendMessage` options; always send `ai_enhance: true`

**Backend**:

4. `api/chat.py`: Remove the `if not chat_request.ai_enhance` bypass branch; always route to ChatAgentService
5. `models/chat.py`: Change `ai_enhance` default description to "Deprecated"

### Step 4: Pipeline User-Scoped Storage (30 min)

**Backend**:

1. `models/pipeline.py`: Add `github_user_id: str | None = None` to `PipelineConfig`
2. `api/pipelines.py`: Extract `session.github_user_id` and pass to store; update list query
3. Pipeline store: Update SQL queries to filter by `github_user_id`

**Frontend**:

4. `SavedWorkflowsList.tsx`: Update to list pipelines without project filter
5. API calls: Update pipeline list to pass user context

### Step 5: Chores User-Scoped Storage + Remove Templates (30 min)

**Backend**:

1. `models/chores.py`: Add `github_user_id: str | None = None`
2. `api/chores.py`: Remove `commit_template_to_repo()` calls; extract user ID from session
3. `services/chores/template_builder.py`: Deprecate template commit functions (keep for reference)

**Frontend**:

4. `ChoreCard.tsx`: Remove PR/Issue template tracking display
5. `AddChoreModal.tsx`: Remove template path requirement

### Step 6: Activity Page Hyperlinks (20 min)

**Frontend only**:

1. `ActivityPage.tsx`: Create `LinkedValue` component for detail rendering
2. Detect `_url` keys → render as `<a>` links
3. Detect `_number` keys with companion `_url` → render as `#N` links
4. Parse summary text for `#\d+` patterns → linkify with repo URL

## Validation

```bash
# Frontend lint and type check
cd solune/frontend
npm run lint
npx tsc --noEmit

# Frontend tests
npx vitest run

# Manual verification
npm run dev  # Start frontend
# Open Settings → select "o3 (XHigh)" → Save → Reload → verify persisted
# Open Chat → verify no AI Enhance toggle
# Open Activity → verify PR#/Issue# are clickable
```

## Files Changed Summary

| File | Change Type | Phase |
|------|------------|-------|
| `backend/src/migrations/038_fix_issues.sql` | NEW | 1 |
| `backend/src/services/settings_store.py` | MODIFIED | 2 |
| `backend/src/models/settings.py` | MODIFIED | 2 |
| `frontend/src/components/chat/ChatToolbar.tsx` | MODIFIED | 3 |
| `frontend/src/components/chat/ChatInterface.tsx` | MODIFIED | 3 |
| `frontend/src/hooks/useChat.ts` | MODIFIED | 3 |
| `backend/src/api/chat.py` | MODIFIED | 3 |
| `backend/src/models/chat.py` | MODIFIED | 3 |
| `backend/src/models/pipeline.py` | MODIFIED | 4 |
| `backend/src/api/pipelines.py` | MODIFIED | 4 |
| `frontend/src/components/pipeline/SavedWorkflowsList.tsx` | MODIFIED | 4 |
| `backend/src/models/chores.py` | MODIFIED | 5 |
| `backend/src/api/chores.py` | MODIFIED | 5 |
| `frontend/src/components/chores/ChoreCard.tsx` | MODIFIED | 5 |
| `frontend/src/pages/ActivityPage.tsx` | MODIFIED | 6 |
