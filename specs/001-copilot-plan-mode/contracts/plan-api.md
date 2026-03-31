# Plan API Contracts

## Base URL

All plan endpoints are under the chat router prefix: `/api/v1/chat`

## Authentication

All endpoints require an active session (session cookie). The `get_session_dep` dependency resolves the `UserSession` with `session_id`, `access_token`, and `selected_project_id`.

---

## Endpoints

### 1. POST /messages/plan — Enter Plan Mode

Initiates plan mode for the selected project. The user's message (feature description) is sent to the plan agent, which researches context and generates a structured plan.

**Request:**
```json
{
  "content": "Add user authentication with OAuth2",
  "ai_enhance": true,
  "file_urls": []
}
```

**Response (non-streaming):** `200 OK`
```json
{
  "message_id": "uuid",
  "session_id": "uuid",
  "sender_type": "assistant",
  "content": "I've created an implementation plan for your feature...",
  "action_type": "plan_create",
  "action_data": {
    "plan_id": "uuid",
    "title": "Add User Authentication with OAuth2",
    "summary": "Implement OAuth2-based authentication...",
    "status": "draft",
    "project_id": "PVT_...",
    "project_name": "My App",
    "repo_owner": "octocat",
    "repo_name": "my-app",
    "steps": [
      {
        "step_id": "uuid",
        "position": 0,
        "title": "Set up OAuth2 provider configuration",
        "description": "Create configuration module for OAuth2...",
        "dependencies": []
      },
      {
        "step_id": "uuid",
        "position": 1,
        "title": "Implement token exchange endpoint",
        "description": "Create /auth/callback endpoint...",
        "dependencies": ["<step_id of step 0>"]
      }
    ]
  },
  "timestamp": "2026-03-31T15:00:00.000Z"
}
```

**Errors:**
- `400 Bad Request` — No description provided (`content` empty or only `/plan` prefix).
- `400 Bad Request` — No project selected.
- `500 Internal Server Error` — Agent processing failure.

---

### 2. POST /messages/plan/stream — Enter Plan Mode (Streaming)

Same as above but returns an SSE stream with thinking events.

**Request:** Same as `POST /messages/plan`.

**Response:** `200 OK` (SSE stream)

```
event: thinking
data: {"phase": "researching", "detail": "Analyzing repository structure and existing issues..."}

event: thinking
data: {"phase": "planning", "detail": "Drafting implementation plan with 6 steps..."}

event: token
data: {"content": "I've created an "}

event: token
data: {"content": "implementation plan..."}

event: done
data: {"message_id": "uuid", "session_id": "uuid", "sender_type": "assistant", "content": "...", "action_type": "plan_create", "action_data": {...}, "timestamp": "..."}
```

**SSE Event Types:**

| Event      | Data Schema                                           | Description                         |
|------------|-------------------------------------------------------|-------------------------------------|
| `thinking` | `{"phase": string, "detail": string}`                 | Phase indicator (new for plan mode) |
| `token`    | `{"content": string}`                                 | Partial text content                |
| `tool_call`| `{"name": string, "arguments": object}`               | Agent tool invocation               |
| `tool_result`| `{"name": string, "result": string}`                | Tool result                         |
| `done`     | `ChatMessage` (full JSON)                             | Final complete message              |
| `error`    | `{"error": string}`                                   | Error event                         |

**Thinking Phases:**

| Phase         | Meaning                                   | UI Label                            |
|---------------|-------------------------------------------|--------------------------------------|
| `researching` | Agent analyzing project context           | "Researching project context…"       |
| `planning`    | Agent drafting the implementation plan    | "Drafting implementation plan…"      |
| `refining`    | Agent incorporating user feedback         | "Incorporating your feedback…"       |

---

### 3. GET /plans/{plan_id} — Retrieve Plan

Returns the full plan with all steps.

**Response:** `200 OK`
```json
{
  "plan_id": "uuid",
  "session_id": "uuid",
  "title": "Add User Authentication with OAuth2",
  "summary": "Implement OAuth2-based authentication...",
  "status": "draft",
  "project_id": "PVT_...",
  "project_name": "My App",
  "repo_owner": "octocat",
  "repo_name": "my-app",
  "parent_issue_number": null,
  "parent_issue_url": null,
  "steps": [
    {
      "step_id": "uuid",
      "position": 0,
      "title": "Set up OAuth2 provider configuration",
      "description": "Create configuration module for OAuth2...",
      "dependencies": [],
      "issue_number": null,
      "issue_url": null
    }
  ],
  "created_at": "2026-03-31T15:00:00.000Z",
  "updated_at": "2026-03-31T15:00:00.000Z"
}
```

**Errors:**
- `404 Not Found` — Plan does not exist or belongs to a different session.

---

### 4. PATCH /plans/{plan_id} — Update Plan

Allows manual metadata updates (title, summary). Step changes are handled by the agent via `save_plan` tool.

**Request:**
```json
{
  "title": "Updated Plan Title",
  "summary": "Updated summary..."
}
```

**Response:** `200 OK` — Updated plan (same schema as GET).

**Errors:**
- `400 Bad Request` — Plan is not in `draft` status.
- `404 Not Found` — Plan not found.

---

### 5. POST /plans/{plan_id}/approve — Approve & Create Issues

Triggers GitHub issue creation: parent issue + one sub-issue per step.

**Request:** Empty body.

**Response:** `200 OK`
```json
{
  "plan_id": "uuid",
  "status": "completed",
  "parent_issue_number": 42,
  "parent_issue_url": "https://github.com/octocat/my-app/issues/42",
  "steps": [
    {
      "step_id": "uuid",
      "position": 0,
      "title": "Set up OAuth2 provider configuration",
      "issue_number": 43,
      "issue_url": "https://github.com/octocat/my-app/issues/43"
    },
    {
      "step_id": "uuid",
      "position": 1,
      "title": "Implement token exchange endpoint",
      "issue_number": 44,
      "issue_url": "https://github.com/octocat/my-app/issues/44"
    }
  ]
}
```

**Errors:**
- `400 Bad Request` — Plan is not in `draft` status, or plan has zero steps.
- `404 Not Found` — Plan not found.
- `502 Bad Gateway` — GitHub API failure (partial creation). Response includes:
  ```json
  {
    "error": "Partial issue creation failure",
    "plan_id": "uuid",
    "status": "failed",
    "created_issues": [
      {"step_id": "uuid", "issue_number": 43, "issue_url": "..."}
    ],
    "failed_steps": [
      {"step_id": "uuid", "position": 1, "title": "...", "error": "GitHub API rate limit exceeded"}
    ]
  }
  ```

---

### 6. POST /plans/{plan_id}/exit — Exit Plan Mode

Deactivates plan mode, returning the chat to standard operation. The plan is preserved.

**Request:** Empty body.

**Response:** `200 OK`
```json
{
  "message": "Plan mode deactivated",
  "plan_id": "uuid",
  "plan_status": "draft"
}
```

**Errors:**
- `404 Not Found` — Plan not found.

---

## Pydantic Models (Backend)

### Request Models

```python
class PlanUpdateRequest(BaseModel):
    title: str | None = None
    summary: str | None = None
```

### Response Models

```python
class PlanStepResponse(BaseModel):
    step_id: str
    position: int
    title: str
    description: str
    dependencies: list[str]
    issue_number: int | None = None
    issue_url: str | None = None

class PlanResponse(BaseModel):
    plan_id: str
    session_id: str
    title: str
    summary: str
    status: str  # "draft" | "approved" | "completed" | "failed"
    project_id: str
    project_name: str
    repo_owner: str
    repo_name: str
    parent_issue_number: int | None = None
    parent_issue_url: str | None = None
    steps: list[PlanStepResponse]
    created_at: str
    updated_at: str

class PlanApprovalResponse(BaseModel):
    plan_id: str
    status: str
    parent_issue_number: int | None = None
    parent_issue_url: str | None = None
    steps: list[PlanStepResponse]

class PlanExitResponse(BaseModel):
    message: str
    plan_id: str
    plan_status: str
```

---

## Frontend API Methods

```typescript
// In frontend/src/services/api.ts

// Enter plan mode (streaming)
sendPlanMessageStream(
  data: ChatMessageRequest,
  onToken: (content: string) => void,
  onThinking: (event: ThinkingEvent) => void,
  onDone: (message: ChatMessage) => void,
  onError: (error: Error) => void
): Promise<void>

// Retrieve a plan
getPlan(planId: string): Promise<PlanResponse>

// Approve a plan and create issues
approvePlan(planId: string): Promise<PlanApprovalResponse>

// Exit plan mode
exitPlanMode(planId: string): Promise<PlanExitResponse>
```

---

## TypeScript Types

```typescript
type PlanStatus = 'draft' | 'approved' | 'completed' | 'failed';
type ThinkingPhase = 'researching' | 'planning' | 'refining';

interface ThinkingEvent {
  phase: ThinkingPhase;
  detail: string;
}

interface PlanStep {
  step_id: string;
  position: number;
  title: string;
  description: string;
  dependencies: string[];
  issue_number?: number;
  issue_url?: string;
}

interface Plan {
  plan_id: string;
  session_id: string;
  title: string;
  summary: string;
  status: PlanStatus;
  project_id: string;
  project_name: string;
  repo_owner: string;
  repo_name: string;
  parent_issue_number?: number;
  parent_issue_url?: string;
  steps: PlanStep[];
  created_at: string;
  updated_at: string;
}

interface PlanCreateActionData {
  plan_id: string;
  title: string;
  summary: string;
  status: PlanStatus;
  project_id: string;
  project_name: string;
  repo_owner: string;
  repo_name: string;
  steps: PlanStep[];
}
```
