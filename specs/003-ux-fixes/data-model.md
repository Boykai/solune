# Data Model: UX Fixes — Scrolling, Agents Page, Chat Streaming, Auto Model

**Branch**: `003-ux-fixes` | **Date**: 2026-04-05

## Entities

### 1. FullPageScrollShell (UI-only)

Represents the top-level layout contract for full-page views such as Settings, Agents, and Pipeline.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| page_key | enum | `settings` \| `agents` \| `pipeline` | View identifier |
| shell_path | string | Required | Absolute source path to the page component |
| scroll_owner | string | Required | CSS/class selector for the only vertical scroll container |
| loading_state_selector | string \| null | Nullable | Selector for loading wrapper if present |
| nested_scroll_selectors | string[] | Default `[]` | Any descendant selectors that currently own scroll |
| header_region | string \| null | Nullable | Non-scrolling hero/header region if present |

**Validation Rules**:
- Each `page_key` must have exactly one `scroll_owner`.
- `nested_scroll_selectors` must be empty after implementation.
- Loading states must not introduce an extra vertical scrollbar.

### 2. CatalogAgentTile (API-backed UI entity)

Inline representation of an importable agent from the Awesome Copilot catalog.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | string | Required | Catalog identifier from `/agents/{project_id}/catalog` |
| name | string | Required | Display label |
| description | string | Required | Searchable summary |
| source_url | string | Required, URL | Upstream catalog source |
| already_imported | boolean | Default `false` | Comes from backend catalog response |
| import_state | enum | `available` \| `importing` \| `imported` \| `error` | Frontend rendering state |
| error_message | string \| null | Nullable | Inline import/retry message |

**Validation Rules**:
- Search filtering matches `name` or `description`.
- If `already_imported` is `true`, the UI must render imported status and disable duplicate import.
- `import_state=error` must preserve the tile and show a retryable failure state.

### 3. ImportedAgentSnapshot (existing persisted relationship)

Represents the project-local agent record returned after catalog import.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| agent_id | string | Required | Backing agent config identifier |
| project_id | string | Required | Owning project |
| catalog_agent_id | string | Required for imported tiles | Links back to `CatalogAgentTile.id` |
| default_model_name | string \| null | Nullable | Existing agent default model display |
| status | string | Existing backend semantics | Must continue to support imported/error visibility |

**Relationships**:
- `CatalogAgentTile.id` → `ImportedAgentSnapshot.catalog_agent_id`
- One project may import many catalog agents; a catalog agent can appear as imported at most once per project.

### 4. ChatStreamingSession (transient frontend state)

Tracks a single active streamed assistant response in the chat viewport.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| session_id | string | Required | Chat session identifier |
| pending_user_message_id | string | Required | Temp user message currently awaiting completion |
| content_buffer | string | Required, may be empty at start | Concatenated token stream |
| is_streaming | boolean | Required | True between first token and `done`/`error` |
| has_error | boolean | Required | True when an `error` event ends the stream |
| error_message | string \| null | Nullable | User-visible stream failure text |
| auto_scroll_mode | enum | `follow` \| `paused` | Whether new tokens should scroll into view |

**Validation Rules**:
- `content_buffer` grows monotonically while `is_streaming=true`.
- On `done`, `content_buffer` must hand off to the persisted final assistant message without duplication.
- On `error`, partial `content_buffer` remains visible and `has_error` becomes `true`.

### 5. StreamedAssistantMessage (existing persisted chat entity, extended)

Final assistant message delivered by `/chat/messages/stream` or `/chat/messages`.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| message_id | string | Required | Existing message identifier |
| session_id | string | Required | Existing chat session |
| sender_type | enum | Existing | Assistant/system/user semantics unchanged |
| content | string | Required | Final rendered content |
| timestamp | string | Required, ISO 8601 | Existing field |
| resolved_model | ResolvedModelInfo \| null | Nullable, additive | New metadata for Auto model visibility |

**Validation Rules**:
- `content` must equal the completed streamed output once `done` arrives.
- `resolved_model` is optional for explicit model selection and required when the user chose Auto and a model was successfully resolved.

### 6. ResolvedModelInfo (additive API/UI entity)

Normalized metadata for FR-013 through FR-015.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| selection_mode | enum | `auto` \| `explicit` | Whether Auto was used |
| model_id | string \| null | Nullable on failure | Internal/provider identifier |
| model_name | string \| null | Nullable on failure | User-facing label |
| source | enum | `pipeline_override` \| `agent_default` \| `user_default` \| `provider_default` \| `unknown` | Where the resolved model came from |
| resolution_status | enum | `resolved` \| `failed` | Outcome of Auto resolution |
| guidance | string \| null | Nullable | Actionable fallback text when resolution fails |

**Validation Rules**:
- `resolution_status=resolved` requires `model_name`.
- `resolution_status=failed` requires `guidance`.
- `selection_mode=explicit` may omit `guidance`.

### 7. PipelineLaunchResult (existing API entity, extended)

Existing workflow result used by pipeline launch flows, with optional resolved-model metadata.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| success | boolean | Required | Existing |
| issue_number | integer \| null | Nullable | Existing |
| issue_url | string \| null | Nullable | Existing |
| message | string | Required | Existing human-readable status |
| resolved_model | ResolvedModelInfo \| null | Nullable, additive | New UI display field for Auto launches |

## State Transitions

### Full-page scroll ownership

```text
loading_shell
  └── ready_shell

Invariant: exactly one scroll owner in both states
```

### Catalog agent import lifecycle

```text
available ──→ importing ──→ imported
    │             │
    │             └──→ error ──→ importing
    └──────────────────────────────→ imported (already_imported on initial load)
```

### Chat streaming lifecycle

```text
idle ──→ streaming(follow)
           │        │
           │        └──→ streaming(paused)
           │                 └──→ streaming(follow)
           ├──→ completed
           └──→ failed (partial buffer preserved)
```

### Auto model resolution lifecycle

```text
selected:auto ──→ resolving ──→ resolved
                      │
                      └──→ failed (guidance shown, manual selection suggested)
```

## Relationships

```text
FullPageScrollShell (1 per page)
  ├── governs CatalogAgentTile list presentation on Agents page
  └── governs ChatStreamingSession viewport behavior on chat/pipeline views

CatalogAgentTile (N) ──→ (0..1) ImportedAgentSnapshot
ChatStreamingSession (1) ──→ (1) StreamedAssistantMessage
StreamedAssistantMessage (0..1) ──→ (1) ResolvedModelInfo
PipelineLaunchResult (0..1) ──→ (1) ResolvedModelInfo
```

## Implementation Touchpoints

- Scroll shell ownership: `/home/runner/work/solune/solune/solune/frontend/src/pages/SettingsPage.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPage.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/pages/AgentsPipelinePage.tsx`
- Catalog tile data: `/home/runner/work/solune/solune/solune/backend/src/models/agents.py`, `/home/runner/work/solune/solune/solune/backend/src/api/agents.py`, `/home/runner/work/solune/solune/solune/frontend/src/hooks/useAgents.ts`
- Streaming state: `/home/runner/work/solune/solune/solune/frontend/src/hooks/useChat.ts`, `/home/runner/work/solune/solune/solune/frontend/src/components/chat/ChatInterface.tsx`, `/home/runner/work/solune/solune/solune/frontend/src/services/api.ts`
- Resolved model metadata: `/home/runner/work/solune/solune/solune/backend/src/models/chat.py`, `/home/runner/work/solune/solune/solune/backend/src/models/workflow.py`, `/home/runner/work/solune/solune/solune/frontend/src/types/index.ts`
