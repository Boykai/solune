# Data Model: Autonomous App Builder

**Feature**: 002-autonomous-app-builder | **Date**: 2026-03-31
**Input**: [spec.md](spec.md) Key Entities, [research.md](research.md) decisions

## Entity Definitions

### 1. AppTemplate

**Location**: `backend/src/models/app_template.py` (NEW)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | `str` | PK, unique, kebab-case | Template identifier (e.g., `saas-react-fastapi`) |
| `name` | `str` | Required, 2–64 chars | Human-readable name (e.g., "SaaS — React + FastAPI") |
| `description` | `str` | Required | Brief template description |
| `category` | `AppCategory` | Enum: `saas`, `api`, `cli`, `dashboard` | Template category for filtering |
| `difficulty` | `str` | One of: `S`, `M`, `L`, `XL` | Recommended complexity level |
| `tech_stack` | `list[str]` | Non-empty | Technology identifiers (e.g., `["react", "fastapi", "postgresql"]`) |
| `scaffold_type` | `ScaffoldType` | Enum: `skeleton`, `starter` | Minimal structure vs. working code |
| `files` | `list[TemplateFile]` | Non-empty | File manifest with source paths |
| `recommended_preset_id` | `str` | Valid preset ID | Default pipeline preset for this template |
| `iac_target` | `IaCTarget` | Enum: `none`, `azure`, `aws`, `docker` | Deployment target for IaC generation |

**Enums**:

```python
class AppCategory(StrEnum):
    SAAS = "saas"
    API = "api"
    CLI = "cli"
    DASHBOARD = "dashboard"

class ScaffoldType(StrEnum):
    SKELETON = "skeleton"
    STARTER = "starter"

class IaCTarget(StrEnum):
    NONE = "none"
    AZURE = "azure"
    AWS = "aws"
    DOCKER = "docker"
```

**Nested Models**:

```python
class TemplateFile(BaseModel):
    source: str       # Relative path in template dir (e.g., "files/backend/main.py.tmpl")
    target: str       # Relative output path (e.g., "backend/main.py")
    variables: list[str]  # Variable names used in this file (e.g., ["app_name", "port"])
```

**Validation Rules**:
- `id` must match pattern `[a-z0-9][a-z0-9-]*[a-z0-9]`
- `files[].target` must not contain `..` or start with `/`
- `recommended_preset_id` must exist in `PRESET_DEFINITIONS`
- `tech_stack` must have at least one entry

---

### 2. App (Extended)

**Location**: `backend/src/models/app.py` (EXTEND existing)

| Field | Type | Change | Description |
|-------|------|--------|-------------|
| `template_id` | `str \| None` | ADD | Originating template ID (null for non-template apps) |

**Extended `AppCreate`**:

| Field | Type | Change | Description |
|-------|------|--------|-------------|
| `template_id` | `str \| None` | ADD | Template to scaffold from |

**No other changes to App model** — `repo_type` already supports `EXTERNAL_REPO`, `external_repo_url` already exists, `github_project_url` and `github_project_id` already support Project V2 linking.

**State Transitions** (existing, unchanged):
```
CREATING → ACTIVE (successful scaffold)
CREATING → ERROR (scaffold failure)
ACTIVE → STOPPED (user action)
STOPPED → ACTIVE (user action)
```

---

### 3. BuildProgress

**Location**: `backend/src/models/build_progress.py` (NEW)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `app_name` | `str` | Required | Target app identifier |
| `phase` | `BuildPhase` | Enum | Current build phase |
| `agent_name` | `str \| None` | Optional | Currently active agent display name |
| `detail` | `str` | Required | Human-readable status text |
| `pct_complete` | `int` | 0–100 | Progress percentage |
| `started_at` | `str` | ISO 8601 | Build start timestamp |
| `updated_at` | `str` | ISO 8601 | Last update timestamp |

**Enums**:

```python
class BuildPhase(StrEnum):
    SCAFFOLDING = "scaffolding"         # Template rendering
    CONFIGURING = "configuring"         # Pipeline setup
    ISSUING = "issuing"                 # Parent issue creation
    BUILDING = "building"              # Pipeline execution
    DEPLOYING_PREP = "deploying_prep"  # IaC generation (architect agent)
    COMPLETE = "complete"              # All done
    FAILED = "failed"                  # Error state

class BuildMilestone(StrEnum):
    SCAFFOLDED = "scaffolded"      # Template files rendered
    WORKING = "working"            # Pipeline running
    REVIEW = "review"              # In review stage
    COMPLETE = "complete"          # All done
```

**Not persisted to database** — in-memory only (see R5 in research.md). Emitted as WebSocket events and used to generate chat messages and Signal notifications.

**WebSocket Event Schema**:
```json
{
  "type": "build_progress",
  "app_name": "my-dashboard",
  "phase": "building",
  "agent_name": "speckit.implement",
  "detail": "Implementing user stories...",
  "pct_complete": 65,
  "updated_at": "2026-03-31T22:00:00Z"
}
```

---

### 4. PipelinePresetConfiguration

**Location**: `backend/src/services/pipelines/pipeline_config.py` (NEW)

This is a mapping utility, not a persisted entity. It determines the pipeline preset based on template metadata.

| Input | Type | Description |
|-------|------|-------------|
| `template` | `AppTemplate` | Template being used |
| `difficulty_override` | `str \| None` | User/agent difficulty override |

| Output | Type | Description |
|--------|------|-------------|
| `preset_id` | `str` | Selected preset identifier |
| `include_architect` | `bool` | Whether to insert architect agent |

**Mapping Logic**:
```
difficulty = difficulty_override or template.difficulty
preset_id = DIFFICULTY_PRESET_MAP[difficulty]

include_architect = template.iac_target != IaCTarget.NONE
```

When `include_architect` is true, the pipeline creation process inserts a "deploy-prep" `ExecutionGroup` in the "In progress" stage containing a single `PipelineAgentNode` with `agent_slug="architect"`, placed after the implementation groups.

---

### 5. ImportAppRequest

**Location**: `backend/src/api/apps.py` (inline request model)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `url` | `str` | Required, GitHub URL format | Repository URL to import |
| `pipeline_id` | `str \| None` | Optional, valid pipeline ID | Pipeline to attach |
| `create_project` | `bool` | Default: `true` | Whether to create Project V2 board |

**Validation Rules**:
- `url` must match `https://github.com/{owner}/{repo}` pattern
- Repository must be accessible with the user's GitHub token
- Repository must not already be imported (unique external_repo_url)

---

## Entity Relationship Diagram

```
┌──────────────────┐       creates from        ┌──────────────────┐
│   AppTemplate     │◄──────────────────────────│       App        │
│                   │       template_id          │  (extended)      │
│  id               │                            │                  │
│  name             │                            │  name            │
│  category         │                            │  template_id ────┤
│  difficulty        │                            │  repo_type       │
│  tech_stack       │                            │  status          │
│  scaffold_type    │                            │  pipeline_id ────┤
│  files[]          │                            │  external_repo   │
│  preset_id        │                            │                  │
│  iac_target       │                            └───────┬──────────┘
└──────────────────┘                                     │
                                                         │ has active
                                                         ▼
                                              ┌──────────────────┐
                                              │  BuildProgress   │
                                              │  (in-memory)     │
                                              │                  │
                                              │  app_name        │
                                              │  phase           │
                                              │  agent_name      │
                                              │  detail          │
                                              │  pct_complete    │
                                              └──────────────────┘

┌──────────────────┐
│ PipelineConfig   │       configured by       ┌──────────────────────┐
│ (existing)       │◄─────────────────────────│ PipelinePresetConfig │
│                  │                           │ (mapping utility)    │
│  id              │                           │                      │
│  stages[]        │                           │  template → preset   │
│  preset_id       │                           │  difficulty → preset │
│  is_preset       │                           │  iac_target → arch.  │
└──────────────────┘                           └──────────────────────┘
```

## Cross-References

- **FR-001, FR-002**: AppTemplate entity covers all required metadata fields
- **FR-003, FR-004**: TemplateFile + renderer handles variable substitution and path validation
- **FR-006**: ImportAppRequest + extended App (EXTERNAL_REPO) covers import
- **FR-008**: App.template_id links created apps to their template
- **FR-009, FR-010**: PipelinePresetConfiguration handles template→preset mapping and architect insertion
- **FR-015**: BuildProgress entity covers all required progress fields
- **FR-016**: WebSocket event schema defines the broadcast format
- **SC-010**: TemplateFile.target validation rules enforce path-traversal blocking
