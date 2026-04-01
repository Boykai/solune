# Data Model: Awesome Copilot Agent Import

**Feature**: 003-copilot-agent-import
**Date**: 2026-04-01
**Prerequisites**: [research.md](./research.md)

## Entities

### AgentConfig (Existing — Extended with Import Columns)

The `agent_configs` table stores all agent configuration records. New columns are added via migration `030_agent_import.sql` to support the imported agent lifecycle. Existing rows are unaffected — they receive `agent_type='custom'` via the default value.

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `id` | `TEXT PRIMARY KEY` | `agent_configs.id` | UUID, auto-generated |
| `name` | `TEXT NOT NULL` | `agent_configs.name` | Agent display name |
| `slug` | `TEXT NOT NULL` | `agent_configs.slug` | Kebab-case identifier |
| `description` | `TEXT NOT NULL` | `agent_configs.description` | Short description |
| `system_prompt` | `TEXT NOT NULL` | `agent_configs.system_prompt` | Full system prompt text (empty for imported agents until install) |
| `status_column` | `TEXT NOT NULL` | `agent_configs.status_column` | Board status column assignment |
| `tools` | `TEXT NOT NULL DEFAULT '[]'` | `agent_configs.tools` | JSON array of tool names |
| `project_id` | `TEXT NOT NULL` | `agent_configs.project_id` | Project scope |
| `owner` | `TEXT NOT NULL` | `agent_configs.owner` | Repository owner |
| `repo` | `TEXT NOT NULL` | `agent_configs.repo` | Repository name |
| `created_by` | `TEXT NOT NULL` | `agent_configs.created_by` | User who created/imported |
| `github_issue_number` | `INTEGER` | `agent_configs.github_issue_number` | Tracking issue (set on install) |
| `github_pr_number` | `INTEGER` | `agent_configs.github_pr_number` | PR number (set on install) |
| `branch_name` | `TEXT` | `agent_configs.branch_name` | PR branch (set on install) |
| `created_at` | `TEXT NOT NULL DEFAULT now` | `agent_configs.created_at` | Row creation timestamp |
| `lifecycle_status` | `TEXT NOT NULL DEFAULT 'pending_pr'` | `agent_configs.lifecycle_status` | Extended: `'imported'`, `'installed'` added |
| `default_model_id` | `TEXT NOT NULL DEFAULT ''` | `agent_configs.default_model_id` | AI model ID |
| `default_model_name` | `TEXT NOT NULL DEFAULT ''` | `agent_configs.default_model_name` | AI model display name |
| `icon_name` | `TEXT` | `agent_configs.icon_name` | Celestial icon name |
| **`agent_type`** | **`TEXT NOT NULL DEFAULT 'custom'`** | **`agent_configs.agent_type`** | **NEW**: `'custom'` or `'imported'` — discriminator |
| **`catalog_source_url`** | **`TEXT`** | **`agent_configs.catalog_source_url`** | **NEW**: Awesome Copilot catalog URL |
| **`catalog_agent_id`** | **`TEXT`** | **`agent_configs.catalog_agent_id`** | **NEW**: Catalog slug for deduplication |
| **`raw_source_content`** | **`TEXT`** | **`agent_configs.raw_source_content`** | **NEW**: Verbatim raw markdown snapshot |
| **`imported_at`** | **`TEXT`** | **`agent_configs.imported_at`** | **NEW**: ISO 8601 import timestamp |

**New Lifecycle Status Values**:

| lifecycle_status | agent_type | Meaning |
|------------------|------------|---------|
| `pending_pr` | `custom` | Custom agent — PR opened, waiting for merge (existing) |
| `active` | `custom` | Custom agent — merged and active on repo (existing) |
| `pending_deletion` | `custom` | Custom agent — deletion PR opened (existing) |
| **`imported`** | **`imported`** | **NEW**: Imported from catalog, not yet installed to a repo |
| **`installed`** | **`imported`** | **NEW**: Installed to repo via GitHub issue + PR |

**New Index**:
- `idx_agent_configs_catalog ON agent_configs(catalog_agent_id, project_id)` — Efficient duplicate detection (FR-008)

---

### CatalogAgent (Transient — Not Persisted)

Represents an agent listing from the Awesome Copilot catalog index. Exists only in memory during browse modal sessions. Parsed from the cached `llms.txt` index.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `str` | Yes | Slug-based identifier from the catalog (e.g., `"security-reviewer"`) |
| `name` | `str` | Yes | Display name of the agent |
| `description` | `str` | Yes | Short description from the catalog |
| `source_url` | `str` | Yes | URL to the raw agent markdown file |
| `already_imported` | `bool` | Yes | Whether this agent is already imported in the current project |

**Backend Pydantic Model** (to be added to `src/models/agents.py`):

```python
class CatalogAgent(BaseModel):
    """Agent listing from the Awesome Copilot catalog."""

    id: str
    name: str
    description: str
    source_url: str
    already_imported: bool = False
```

**Frontend TypeScript Type** (to be added to `api.ts`):

```typescript
export interface CatalogAgent {
  id: string;
  name: string;
  description: string;
  source_url: string;
  already_imported: boolean;
}
```

---

### ImportAgentRequest (Request Model)

Request body for importing a catalog agent into the current project.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `catalog_agent_id` | `str` | Yes | Catalog identifier (slug) |
| `name` | `str` | Yes | Display name |
| `description` | `str` | Yes | Short description |
| `source_url` | `str` | Yes | URL to the raw agent markdown |

**Backend Pydantic Model**:

```python
class ImportAgentRequest(BaseModel):
    """Request to import a catalog agent into a project."""

    catalog_agent_id: str
    name: str
    description: str
    source_url: str
```

---

### ImportAgentResult (Response Model)

Response after a successful import.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agent` | `Agent` | Yes | The imported agent record |
| `message` | `str` | Yes | Success message |

**Backend Pydantic Model**:

```python
class ImportAgentResult(BaseModel):
    """Response from importing a catalog agent."""

    agent: Agent
    message: str
```

---

### InstallAgentResult (Response Model)

Response after a successful install to a repository.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agent` | `Agent` | Yes | The updated agent record (status = installed) |
| `pr_url` | `str` | Yes | URL of the created pull request |
| `pr_number` | `int` | Yes | PR number |
| `issue_number` | `int \| None` | Yes | Tracking issue number |
| `branch_name` | `str` | Yes | Git branch name |

**Backend Pydantic Model**:

```python
class InstallAgentResult(BaseModel):
    """Response from installing an imported agent to a repository."""

    agent: Agent
    pr_url: str
    pr_number: int
    issue_number: int | None
    branch_name: str
```

---

### Agent (Existing — Extended)

The existing `Agent` response model is extended with new fields for the frontend to display import-related metadata.

| New Field | Type | Description |
|-----------|------|-------------|
| `agent_type` | `str` | `'custom'` or `'imported'` |
| `catalog_source_url` | `str \| None` | Catalog origin URL |
| `catalog_agent_id` | `str \| None` | Catalog slug |
| `imported_at` | `str \| None` | ISO 8601 import timestamp |

**Extended Backend Model Fields** (added to existing `Agent` in `src/models/agents.py`):

```python
class Agent(BaseModel):
    # ... existing fields ...
    agent_type: str = "custom"
    catalog_source_url: str | None = None
    catalog_agent_id: str | None = None
    imported_at: str | None = None
```

**Extended Frontend Type** (added to existing `AgentConfig` in `api.ts`):

```typescript
export interface AgentConfig {
  // ... existing fields ...
  agent_type: 'custom' | 'imported';
  catalog_source_url: string | null;
  catalog_agent_id: string | null;
  imported_at: string | null;
}
```

---

### AgentStatus (Existing — Extended)

The existing `AgentStatus` enum is extended with new values.

```python
class AgentStatus(str, Enum):
    ACTIVE = "active"
    PENDING_PR = "pending_pr"
    PENDING_DELETION = "pending_deletion"
    IMPORTED = "imported"       # NEW
    INSTALLED = "installed"     # NEW
```

```typescript
export type AgentStatus = 'active' | 'pending_pr' | 'pending_deletion' | 'imported' | 'installed';
```

---

## Relationships

```text
Awesome Copilot Catalog (external)
    │
    ├── Fetched by: catalog.list_catalog_agents() [cached via InMemoryCache]
    │   └── api/agents.py GET /{project_id}/catalog (browse endpoint)
    │       └── Frontend: BrowseAgentsModal.tsx (via useCatalogAgents hook)
    │
    └── Raw content fetched by: catalog.fetch_agent_raw_content(url)
        └── services/agents/service.py import_agent() [on demand]

agent_configs table (source of truth)
    │
    ├── IMPORT path (no GitHub writes):
    │   ├── api/agents.py POST /{project_id}/import
    │   └── service.py import_agent()
    │       ├── Validates: duplicate check via catalog_agent_id + project_id
    │       ├── Fetches: raw markdown from catalog source URL
    │       ├── Stores: agent_type='imported', lifecycle_status='imported',
    │       │           raw_source_content=<verbatim>, catalog metadata
    │       └── Returns: ImportAgentResult
    │
    ├── INSTALL path (creates GitHub resources):
    │   ├── api/agents.py POST /{project_id}/{agent_id}/install
    │   └── service.py install_agent()
    │       ├── Loads: imported agent from agent_configs
    │       ├── Generates: .agent.md (raw_source_content verbatim)
    │       │              .prompt.md (routing file from slug)
    │       ├── Calls: github_commit_workflow.commit_files_workflow()
    │       │   ├── Creates: tracking issue
    │       │   ├── Creates: branch + commit + PR
    │       │   └── Returns: CommitWorkflowResult
    │       ├── Updates: lifecycle_status='installed', github_issue_number, github_pr_number
    │       └── Returns: InstallAgentResult
    │
    ├── LIST path (existing — extended):
    │   ├── service.py list_agents() / _list_local_agents()
    │   │   └── Now includes imported agents with agent_type='imported'
    │   └── Frontend: AgentsPanel.tsx renders imported agents with status badges
    │
    └── CUSTOM path (existing — unchanged):
        ├── service.py create_agent() / update_agent() / delete_agent()
        ├── agent_creator.py handle_agent_command()
        └── Frontend: AddAgentModal.tsx (completely separate)
```

## State Transitions

### Import Lifecycle

```text
[User clicks "Import" in BrowseAgentsModal]
    │
    ├── POST /api/v1/agents/{project_id}/import
    │   ├── Check: catalog_agent_id not already imported in project
    │   │   ├── Already exists → 409 Conflict ("Agent already imported")
    │   │   └── Not found → continue
    │   ├── Fetch: raw markdown from catalog source URL
    │   │   ├── Success → continue
    │   │   └── Failure → 502 Bad Gateway ("Could not fetch agent content")
    │   └── Insert: agent_configs row
    │       ├── agent_type = 'imported'
    │       ├── lifecycle_status = 'imported'
    │       ├── raw_source_content = <fetched content>
    │       └── imported_at = now()
    │
    └── Response: ImportAgentResult (agent with status='imported')
```

### Install Lifecycle

```text
[User clicks "Add to repo" → confirms in InstallConfirmDialog]
    │
    ├── POST /api/v1/agents/{project_id}/{agent_id}/install
    │   ├── Load: agent from agent_configs WHERE id = agent_id
    │   │   ├── Not found → 404
    │   │   ├── Not imported → 400 ("Agent is not in imported state")
    │   │   └── Found + imported → continue
    │   ├── Generate files:
    │   │   ├── .github/agents/{slug}.agent.md → raw_source_content (verbatim)
    │   │   └── .github/prompts/{slug}.prompt.md → generated routing file
    │   ├── Call: commit_files_workflow()
    │   │   ├── Create tracking issue
    │   │   ├── Create branch
    │   │   ├── Commit files
    │   │   ├── Open PR (closes issue)
    │   │   └── Returns: CommitWorkflowResult
    │   │       ├── Success → continue
    │   │       └── Failure → 500 ("Install failed: {errors}")
    │   └── Update: agent_configs row
    │       ├── lifecycle_status = 'installed'
    │       ├── github_issue_number = result.issue_number
    │       ├── github_pr_number = result.pr_number
    │       └── branch_name = result.branch_name
    │
    └── Response: InstallAgentResult (agent with status='installed', PR URL, issue number)
```

## Migration SQL

```sql
-- Migration 030: Agent Import Support
-- Adds import lifecycle columns to agent_configs

ALTER TABLE agent_configs ADD COLUMN agent_type TEXT NOT NULL DEFAULT 'custom';
ALTER TABLE agent_configs ADD COLUMN catalog_source_url TEXT;
ALTER TABLE agent_configs ADD COLUMN catalog_agent_id TEXT;
ALTER TABLE agent_configs ADD COLUMN raw_source_content TEXT;
ALTER TABLE agent_configs ADD COLUMN imported_at TEXT;

-- Index for duplicate detection (FR-008)
CREATE INDEX IF NOT EXISTS idx_agent_configs_catalog
    ON agent_configs(catalog_agent_id, project_id);
```
