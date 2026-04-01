# Quickstart: Awesome Copilot Agent Import

**Feature**: 003-copilot-agent-import
**Date**: 2026-04-01
**Prerequisites**: [plan.md](./plan.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

## Overview

This feature adds one-click import of Awesome Copilot agents into Solune projects and a separate install action that commits agents to GitHub repositories. The implementation adds a database migration for import metadata, a catalog reader service, import/install methods on the agents service, three new API endpoints, and frontend components for browsing, importing, and installing agents. Custom-agent authoring is completely unaffected.

## New Files

### 1. `solune/backend/src/migrations/030_agent_import.sql`

Database migration adding import lifecycle columns to `agent_configs`:

```sql
ALTER TABLE agent_configs ADD COLUMN agent_type TEXT NOT NULL DEFAULT 'custom';
ALTER TABLE agent_configs ADD COLUMN catalog_source_url TEXT;
ALTER TABLE agent_configs ADD COLUMN catalog_agent_id TEXT;
ALTER TABLE agent_configs ADD COLUMN raw_source_content TEXT;
ALTER TABLE agent_configs ADD COLUMN imported_at TEXT;

CREATE INDEX IF NOT EXISTS idx_agent_configs_catalog
    ON agent_configs(catalog_agent_id, project_id);
```

### 2. `solune/backend/src/services/agents/catalog.py`

Awesome Copilot catalog reader. Fetches and caches the `llms.txt` index, parses agent entries, and provides raw content fetching.

```python
from src.models.agents import CatalogAgent
from src.services.cache import cache, cached_fetch

CATALOG_URL = "https://awesome-copilot.github.com/agents/llms.txt"
CATALOG_CACHE_KEY = "awesome_copilot_catalog"
CATALOG_TTL = 3600  # 1 hour


async def list_catalog_agents(
    *,
    project_id: str,
    db,
) -> list[CatalogAgent]:
    """Browse the Awesome Copilot agent catalog with import status."""
    # Fetch and cache the catalog index
    raw_catalog = await cached_fetch(
        cache,
        CATALOG_CACHE_KEY,
        _fetch_catalog_index,
        ttl_seconds=CATALOG_TTL,
        stale_fallback=True,
    )
    agents = _parse_catalog_index(raw_catalog)

    # Mark already-imported agents
    cursor = await db.execute(
        "SELECT catalog_agent_id FROM agent_configs WHERE project_id = ? AND catalog_agent_id IS NOT NULL",
        (project_id,),
    )
    imported_ids = {row[0] for row in await cursor.fetchall()}

    for agent in agents:
        agent.already_imported = agent.id in imported_ids

    return agents


async def fetch_agent_raw_content(source_url: str) -> str:
    """Fetch raw markdown content from a catalog agent source URL."""
    # HTTP GET to static raw content URL
    # Returns full markdown content as string
    # Raises on failure (status >= 400 or network error)
    ...


async def _fetch_catalog_index() -> str:
    """Fetch the llms.txt catalog index from Awesome Copilot."""
    ...


def _parse_catalog_index(raw_text: str) -> list[CatalogAgent]:
    """Parse llms.txt text into CatalogAgent objects."""
    # Each entry in the index contains: name, description, source URL
    # Parse line-by-line or section-by-section based on format
    ...
```

### 3. `solune/frontend/src/components/agents/BrowseAgentsModal.tsx`

Dedicated modal for browsing and searching Awesome Copilot agents. Opened from a "Browse Agents" button in `AgentsPanel.tsx`.

Key features:
- Search input for filtering agents by name/description (client-side)
- Agent list with name, description, and "Import" button per row
- Loading, error, and empty states
- "Import" button disabled for already-imported agents (shows "Imported ✓")
- Modal stays open after import (supports importing multiple agents)
- Uses `useCatalogAgents(projectId)` for data fetching
- Uses `useImportAgent(projectId)` mutation for import action

### 4. `solune/frontend/src/components/agents/InstallConfirmDialog.tsx`

Confirmation dialog shown before installing an imported agent to a repository.

Key features:
- Displays agent name, description, target repository
- Shows summary: "This will create a GitHub issue and PR"
- Lists files to be committed (`.agent.md` and `.prompt.md`)
- "Install" and "Cancel" buttons
- Loading state during install
- Uses `useInstallAgent(projectId)` mutation

### 5. `solune/backend/tests/unit/test_catalog.py`

Unit tests for the catalog reader:
- Test parsing of llms.txt format into CatalogAgent objects
- Test already_imported flag marking
- Test stale fallback behavior
- Test raw content fetch error handling

## Modified Files

### Backend

### 1. `solune/backend/src/models/agents.py` — Extend models

Add new Pydantic models and extend existing ones:

```python
# New enum values
class AgentStatus(str, Enum):
    ACTIVE = "active"
    PENDING_PR = "pending_pr"
    PENDING_DELETION = "pending_deletion"
    IMPORTED = "imported"
    INSTALLED = "installed"

# New models
class CatalogAgent(BaseModel):
    id: str
    name: str
    description: str
    source_url: str
    already_imported: bool = False

class ImportAgentRequest(BaseModel):
    catalog_agent_id: str
    name: str
    description: str
    source_url: str

class ImportAgentResult(BaseModel):
    agent: Agent
    message: str

class InstallAgentResult(BaseModel):
    agent: Agent
    pr_url: str
    pr_number: int
    issue_number: int | None
    branch_name: str

# Extend existing Agent model
class Agent(BaseModel):
    # ... existing fields ...
    agent_type: str = "custom"
    catalog_source_url: str | None = None
    catalog_agent_id: str | None = None
    imported_at: str | None = None
```

### 2. `solune/backend/src/api/agents.py` — Add new endpoints

Add three new route handlers:

```python
@router.get("/{project_id}/catalog")
async def browse_catalog(
    project_id: str,
    request: Request,
    session: Annotated[UserSession, Depends(get_session_dep)],
    db=Depends(get_database),
) -> dict:
    """Browse available Awesome Copilot agents."""
    await verify_project_access(request, project_id, session)
    agents = await catalog.list_catalog_agents(project_id=project_id, db=db)
    return {"agents": agents, "cached_at": ...}


@router.post("/{project_id}/import")
async def import_agent(
    project_id: str,
    body: ImportAgentRequest,
    request: Request,
    session: Annotated[UserSession, Depends(get_session_dep)],
    db=Depends(get_database),
) -> ImportAgentResult:
    """Import a catalog agent into the project."""
    await verify_project_access(request, project_id, session)
    # Delegate to service.import_agent()
    ...


@router.post("/{project_id}/{agent_id}/install")
async def install_agent(
    project_id: str,
    agent_id: str,
    request: Request,
    session: Annotated[UserSession, Depends(get_session_dep)],
    db=Depends(get_database),
) -> InstallAgentResult:
    """Install an imported agent to the repository."""
    await verify_project_access(request, project_id, session)
    # Delegate to service.install_agent()
    ...
```

### 3. `solune/backend/src/services/agents/service.py` — Add import/install methods

Add two new methods to `AgentsService`:

```python
async def import_agent(
    self,
    *,
    project_id: str,
    body: ImportAgentRequest,
    owner: str,
    repo: str,
    github_user_id: str,
) -> ImportAgentResult:
    """Import a catalog agent (database only, no GitHub writes)."""
    # 1. Check for duplicate: catalog_agent_id + project_id
    # 2. Fetch raw content from source URL
    # 3. Generate UUID, use catalog_agent_id as slug
    # 4. INSERT into agent_configs with agent_type='imported', lifecycle_status='imported'
    # 5. Return ImportAgentResult
    ...


async def install_agent(
    self,
    *,
    project_id: str,
    agent_id: str,
    owner: str,
    repo: str,
    access_token: str,
    github_user_id: str,
) -> InstallAgentResult:
    """Install an imported agent to a GitHub repository."""
    # 1. Load agent from DB, validate status is 'imported'
    # 2. Build files:
    #    - .github/agents/{slug}.agent.md → raw_source_content (verbatim)
    #    - .github/prompts/{slug}.prompt.md → generated routing file
    # 3. Call commit_files_workflow()
    # 4. Update agent_configs: lifecycle_status='installed', PR/issue numbers
    # 5. Return InstallAgentResult
    ...
```

### 4. `solune/backend/src/services/agents/service.py` — Extend `_list_local_agents`

Update the `_list_local_agents` method to include the new import fields when constructing `Agent` objects:

```python
agents.append(
    Agent(
        # ... existing fields ...
        agent_type=r.get("agent_type", "custom"),
        catalog_source_url=r.get("catalog_source_url"),
        catalog_agent_id=r.get("catalog_agent_id"),
        imported_at=r.get("imported_at"),
    )
)
```

### Frontend

### 5. `solune/frontend/src/services/api.ts` — Add API methods

```typescript
export const catalogApi = {
  browse(projectId: string): Promise<{ agents: CatalogAgent[]; cached_at: string | null }> {
    return apiClient.get(`/agents/${projectId}/catalog`);
  },
};

// Extend agentsApi
export const agentsApi = {
  // ... existing methods ...
  import(projectId: string, data: ImportAgentRequest): Promise<ImportAgentResult> {
    return apiClient.post(`/agents/${projectId}/import`, data);
  },
  install(projectId: string, agentId: string): Promise<InstallAgentResult> {
    return apiClient.post(`/agents/${projectId}/${agentId}/install`);
  },
};
```

### 6. `solune/frontend/src/services/api.ts` — Add types

```typescript
export interface CatalogAgent {
  id: string;
  name: string;
  description: string;
  source_url: string;
  already_imported: boolean;
}

export interface ImportAgentRequest {
  catalog_agent_id: string;
  name: string;
  description: string;
  source_url: string;
}

export interface ImportAgentResult {
  agent: AgentConfig;
  message: string;
}

export interface InstallAgentResult {
  agent: AgentConfig;
  pr_url: string;
  pr_number: number;
  issue_number: number | null;
  branch_name: string;
}

// Extend existing AgentConfig
export interface AgentConfig {
  // ... existing fields ...
  agent_type: 'custom' | 'imported';
  catalog_source_url: string | null;
  catalog_agent_id: string | null;
  imported_at: string | null;
}

// Extend AgentStatus
export type AgentStatus = 'active' | 'pending_pr' | 'pending_deletion' | 'imported' | 'installed';
```

### 7. `solune/frontend/src/hooks/useAgents.ts` — Add new hooks

```typescript
export function useCatalogAgents(projectId: string | undefined) {
  return useQuery({
    queryKey: ['catalog', 'agents', projectId],
    queryFn: () => catalogApi.browse(projectId!),
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes client-side cache
  });
}

export function useImportAgent(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ImportAgentRequest) => agentsApi.import(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.list(projectId) });
      queryClient.invalidateQueries({ queryKey: ['catalog', 'agents', projectId] });
    },
  });
}

export function useInstallAgent(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (agentId: string) => agentsApi.install(projectId, agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.list(projectId) });
    },
  });
}
```

### 8. `solune/frontend/src/components/agents/AgentsPanel.tsx` — Add browse button

Add a "Browse Agents" button alongside the existing "Add Agent" button. Open `BrowseAgentsModal` when clicked. Render imported agents with appropriate badges in the agent grid.

### 9. `solune/frontend/src/components/agents/AgentCard.tsx` — Add import status

Extend the card to:
- Show "Imported" badge (amber) when `agent.status === 'imported'`
- Show "Installed" badge (green) when `agent.status === 'installed'`
- Show "Add to repo" button when `agent.agent_type === 'imported' && agent.status === 'imported'`
- Hide edit/system-prompt controls when `agent.agent_type === 'imported'` (read-only, FR-015)
- Show PR/issue links when `agent.status === 'installed'`

## Implementation Order

1. **Database migration** (`030_agent_import.sql`) — Add import columns to `agent_configs`
2. **Backend models** (`models/agents.py`) — Add CatalogAgent, ImportAgentRequest/Result, InstallAgentResult; extend Agent, AgentStatus
3. **Catalog reader** (`services/agents/catalog.py`) — Parse llms.txt, fetch raw content
4. **Catalog reader tests** (`tests/unit/test_catalog.py`) — Test parsing, import flag, error handling
5. **Import service method** (`services/agents/service.py`) — `import_agent()` with duplicate check
6. **Install service method** (`services/agents/service.py`) — `install_agent()` with commit workflow
7. **Extend `_list_local_agents`** (`services/agents/service.py`) — Include new fields in Agent objects
8. **API endpoints** (`api/agents.py`) — `/catalog`, `/import`, `/install` routes
9. **Backend tests** (`test_agents_service.py`, `test_api_agents.py`, `test_github_agents.py`) — Import/install service and API tests
10. **Frontend types** (`api.ts`) — CatalogAgent, ImportAgentRequest/Result, InstallAgentResult, extend AgentConfig
11. **Frontend API methods** (`api.ts`) — catalogApi.browse, agentsApi.import, agentsApi.install
12. **Frontend hooks** (`useAgents.ts`) — useCatalogAgents, useImportAgent, useInstallAgent
13. **BrowseAgentsModal** component — Browse/search/import UI
14. **InstallConfirmDialog** component — Confirmation before install
15. **AgentsPanel** updates — Browse button, imported agent rendering
16. **AgentCard** updates — Import/installed status badges, install action, read-only mode
17. **Frontend tests** (`AgentsPanel.test.tsx`, `useAgents.test.tsx`, `AgentsPage.test.tsx`) — Browse modal, import, install tests
18. **Contract validation** — Run contract tests to verify API shape changes

## Verification

After implementation, verify each component:

```bash
# Run backend unit tests (agent import/install + existing agent tests)
cd solune/backend
uv run pytest tests/unit/test_agents_service.py tests/unit/test_api_agents.py tests/unit/test_github_agents.py tests/unit/test_catalog.py -q

# Run full backend test suite
uv run pytest tests/unit/ -q --tb=short

# Lint backend
uv run ruff check src tests
uv run ruff format --check src tests
uv run pyright src

# Frontend tests
cd solune/frontend
npx vitest run

# Lint frontend
npm run lint
npx tsc --noEmit

# Integration verification (Docker)
# docker compose up → Agents page shows "Browse Agents" button
# Click "Browse Agents" → Modal opens with catalog agents
# Search for an agent → List filters client-side
# Import an agent → Agent appears on page with "Imported" badge
# Try duplicate import → Error message shown
# Click "Add to repo" → Confirmation dialog appears
# Confirm install → GitHub issue + PR created, status changes to "Installed"
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Extend `agent_configs` table (not new table) | Keeps agent model unified; existing list/pagination/cleanup logic includes imported agents naturally. New columns are nullable and backward-compatible |
| `ALTER TABLE ADD COLUMN` migration | SQLite-safe; existing rows get `agent_type='custom'` default. No table recreation needed |
| Catalog cache via `InMemoryCache` (1h TTL) | Reuses existing cache infrastructure; stale-fallback handles temporary catalog unavailability |
| Client-side search/filtering | Catalog is small (<500 agents); avoids server round-trips per keystroke |
| Raw content stored verbatim | Preserves all upstream frontmatter (tools, MCP servers, custom metadata) that Solune doesn't model. Key risk mitigation per spec |
| `.prompt.md` generated from slug only | Simple routing file; doesn't depend on or modify the raw agent content |
| Import = DB only, Install = DB + GitHub | Clean separation per spec; zero GitHub calls during import (SC-006) |
| Separate BrowseAgentsModal (not extending AddAgentModal) | Keeps custom-agent authoring separate from import workflow (FR-016) |
| Imported agents are read-only in UI | Prevents accidental modification of external snapshots (FR-015) |
| Confirmation dialog before install | Explicit user consent before creating GitHub resources (FR-010) |
| Reuse `commit_files_workflow()` for install | Battle-tested pipeline handles branch → commit → PR → issue (no new GitHub integration) |
