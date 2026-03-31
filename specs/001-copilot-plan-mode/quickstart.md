# Quickstart: Copilot-Style Planning Mode (v2)

**Branch**: `001-copilot-plan-mode` | **Date**: 2026-03-31

## Prerequisites

- Solune backend running (`cd solune/backend && uv run uvicorn src.main:app`)
- Solune frontend running (`cd solune/frontend && npm run dev`)
- Active GitHub session with a selected project linked to a repository
- Repository write access (required for issue creation on approval)

## User Flow

### 1. Enter Plan Mode

Type `/plan` followed by a feature description in the chat input:

```
/plan Add user authentication with OAuth2 support
```

**What happens:**
1. The backend detects the `/plan` prefix and routes to the plan agent.
2. Thinking indicators appear: 🔍 "Researching project context…"
3. The agent analyzes the repository structure and existing issues.
4. Indicator transitions to 📋 "Drafting implementation plan…"
5. A structured plan appears as a rich preview card in the chat.

### 2. Review the Plan

The plan preview card shows:
- **Header**: Project badge (`owner/repo`) + status badge (`Draft`)
- **Steps**: Ordered list with titles, descriptions, and dependency annotations
- **Actions**: "Request Changes" and "Approve & Create Issues" buttons

### 3. Iterate and Refine

Send follow-up messages to refine the plan. No `/plan` prefix needed — the system stays in plan mode:

```
Split step 3 into two smaller steps — one for the database migration and one for the API endpoint
```

**What happens:**
1. Indicator shows ✏️ "Incorporating your feedback…"
2. The plan updates in-place with the changes.
3. Previous plan versions remain visible in the conversation trail.

### 4. Approve and Create Issues

Click **"Approve & Create Issues"** on the plan card.

**What happens:**
1. A progress spinner appears.
2. The system creates a parent GitHub issue with the plan title, summary, and a checklist of all steps.
3. Individual sub-issues are created for each step, linked to the parent.
4. The plan card updates to show ✅ "Completed" status.
5. Each step displays a badge linking to its GitHub issue.
6. A "View Parent Issue" link appears.

### 5. Exit Plan Mode

Click **"Exit Plan Mode"** to return to normal chat.

## Implementation Phases

### Phase 1: Backend — Data Model & Storage
- Add `PLAN_CREATE` action type to `ActionType` enum in `backend/src/models/chat.py`
- Create `Plan` / `PlanStep` Pydantic models in `backend/src/models/plan.py`
- Add `chat_plans` + `chat_plan_steps` SQLite tables via migration `035_chat_plans.sql`
- Add plan CRUD functions to `backend/src/services/chat_store.py`

### Phase 2: Backend — Plan Agent Mode & Thinking SSE
- Create plan-mode system prompt in `backend/src/prompts/plan_instructions.py`
- Add `save_plan` tool + `register_plan_tools()` to `backend/src/services/agent_tools.py`
- Implement `run_plan()` + `run_plan_stream()` on `ChatAgentService`
- Add thinking SSE events (`{"event": "thinking", "data": {"phase": "...", "detail": "..."}}`)
- Add plan API routes to `backend/src/api/chat.py`

### Phase 3: Backend — Plan Issue Service
- Create `backend/src/services/plan_issue_service.py`
- On approve: create parent issue → sub-issues → update plan with issue numbers/URLs

### Phase 4: Frontend — Types, API & Thinking UX
- Add `Plan`, `PlanStep`, `ThinkingEvent` types to `frontend/src/types/index.ts`
- Extend SSE parser in `frontend/src/services/api.ts` with `onThinking` callback
- Create `ThinkingIndicator.tsx` component

### Phase 5: Frontend — Plan UI
- Create `PlanPreview.tsx` component
- Create `usePlan.ts` hook
- Wire `PlanPreview` into `MessageBubble.tsx`
- Wire `ThinkingIndicator` into `ChatInterface.tsx`
- Add plan mode banner above chat input

## Key Files

### Backend (New)
| File | Purpose |
|------|---------|
| `backend/src/models/plan.py` | Plan + PlanStep Pydantic models |
| `backend/src/prompts/plan_instructions.py` | Plan-mode system prompt |
| `backend/src/services/plan_issue_service.py` | GitHub issue creation on approval |
| `backend/src/migrations/035_chat_plans.sql` | Database migration |

### Backend (Modified)
| File | Change |
|------|--------|
| `backend/src/models/chat.py` | Add `PLAN_CREATE` to `ActionType` |
| `backend/src/services/chat_store.py` | Add plan CRUD functions |
| `backend/src/services/agent_tools.py` | Add `save_plan` tool + `register_plan_tools()` |
| `backend/src/services/chat_agent.py` | Add `run_plan()` + `run_plan_stream()` |
| `backend/src/api/chat.py` | Add plan mode routes |

### Frontend (New)
| File | Purpose |
|------|---------|
| `frontend/src/components/chat/PlanPreview.tsx` | Rich plan display card |
| `frontend/src/components/chat/ThinkingIndicator.tsx` | Phase-aware loading indicator |
| `frontend/src/hooks/usePlan.ts` | Plan state management hook |

### Frontend (Modified)
| File | Change |
|------|--------|
| `frontend/src/types/index.ts` | Add Plan, PlanStep, ThinkingEvent types |
| `frontend/src/services/api.ts` | Extend SSE parser, add plan API methods |
| `frontend/src/components/chat/MessageBubble.tsx` | Render PlanPreview for plan_create actions |
| `frontend/src/components/chat/ChatInterface.tsx` | ThinkingIndicator + plan mode banner |

## Testing Strategy

### Backend Tests
- **Unit**: Plan CRUD in chat_store, save_plan tool, plan model validation
- **Unit**: run_plan/run_plan_stream dispatch logic
- **Unit**: Plan issue service (mocked GitHub API)
- **E2E**: Plan mode endpoints (create, iterate, approve, exit)

### Frontend Tests
- **Unit**: PlanPreview rendering (draft, completed, failed states)
- **Unit**: ThinkingIndicator phase transitions
- **Unit**: usePlan hook state management
- **Unit**: SSE parser thinking event handling
