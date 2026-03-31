# Quickstart: Increase Backend Test Coverage & Fix Bugs

**Feature**: `002-backend-test-coverage` | **Date**: 2026-03-31

## Prerequisites

- Python >=3.12
- `uv` package manager (for local development)
- Docker & Docker Compose (optional, for containerized runs)

## Development Setup

### 1. Install Dependencies

```bash
cd solune/backend

# Install all dependencies including test extras
uv sync --prerelease=allow
```

### 2. Run Existing Test Suite (Verify Green Baseline)

Before adding any new tests, confirm the existing suite passes:

```bash
cd solune/backend

# Run full unit test suite
uv run pytest tests/unit/ -q

# Expected output: all tests passed, 0 failures
```

### 3. Run Targeted Tests for a Specific Module

```bash
# Phase 2: Project management tests
uv run pytest tests/unit/test_api_projects.py -v

# Phase 3: Agent creator tests
uv run pytest tests/unit/test_agent_creator.py -v

# Phase 4: Agent service tests
uv run pytest tests/unit/test_agents_service.py -v

# Phase 5: Chores service tests
uv run pytest tests/unit/test_chores_service.py -v
```

### 4. Run with Per-File Coverage

```bash
# Coverage for all 4 target files
uv run pytest tests/unit/ \
  --cov=src.api.projects \
  --cov=src.services.agent_creator \
  --cov=src.services.agents.service \
  --cov=src.services.chores.service \
  --cov-report=term-missing \
  -q

# Coverage for a single target file (faster iteration)
uv run pytest tests/unit/test_api_projects.py \
  --cov=src.api.projects \
  --cov-report=term-missing \
  -v
```

### 5. Verify No Regressions

After adding new tests, run the full suite to confirm zero failures:

```bash
uv run pytest tests/unit/ --tb=short -q
```

## Implementation Order

### Phase 2: src/api/projects.py (37.7% → ~70%)

**Test file**: `tests/unit/test_api_projects.py`
**Estimated new tests**: ~30

Add tests for:
1. Rate limit detection (403 + X-RateLimit-Remaining: "0" vs empty dict)
2. `get_project_tasks` fallback to `get_done_items()` on exception
3. `list_projects` cache edge cases (empty list vs None, non-rate-limit errors)
4. `get_project` cache miss (project not in list, refresh=True with error)
5. WebSocket `websocket_subscribe` (stale revalidation, hash diffing, disconnect)

### Phase 3: src/services/agent_creator.py (39.4% → ~65%)

**Test file**: `tests/unit/test_agent_creator.py`
**Estimated new tests**: ~25

Add tests for:
1. Admin auth edge cases (debug auto-promote, ADMIN_GITHUB_USER_ID env var, DB exception)
2. Status resolution (fuzzy empty input, normalized match, out-of-range selection, new column)
3. Creation pipeline steps 3–7 (duplicate name, column creation, issue/PR creation, cleanup)
4. AI service failures (generate_agent_config failure, edit retry, non-list tools)

### Phase 4: src/services/agents/service.py (47.4% → ~70%) — parallel with Phase 3

**Test file**: `tests/unit/test_agents_service.py`
**Estimated new tests**: ~35

Add tests for:
1. Cache/stale data (list_agents cached + preference overlay, stale fallback, session pruning)
2. Agent source mixing (bulk_update_models REPO+LOCAL, partial failure, tombstones)
3. YAML frontmatter (missing fields, parse errors → fallback, no frontmatter)
4. Tool resolution (MCP normalization, wildcard vs explicit, dedup, invalid configs)
5. Create agent (slug from special chars, AI failure fallback, raw vs enhanced mode)

### Phase 5: src/services/chores/service.py (51.3% → ~75%) — parallel with Phase 4

**Test file**: `tests/unit/test_chores_service.py`
**Estimated new tests**: ~30

Add tests for:
1. Preset seeding (idempotent re-seed, file read failure, all 3 presets, uniqueness)
2. Update validation (schedule consistency, boolean→int, invalid column rejection)
3. Trigger state CAS (NULL first trigger, matching old value, mismatch double-fire prevention, clear_current_issue)

### Phase 6: Verification

```bash
# Full suite — must be 0 failures
uv run pytest tests/unit/ --tb=short -q

# Per-file coverage comparison
uv run pytest tests/unit/ \
  --cov=src.api.projects \
  --cov=src.services.agent_creator \
  --cov=src.services.agents.service \
  --cov=src.services.chores.service \
  --cov-report=term-missing \
  -q
```

## Key Testing Patterns

### Async Test Functions

All tests are automatically async — no decorator needed:

```python
async def test_rate_limit_detection(mock_db, mock_settings, auth_client):
    """Test that 403 + rate limit header triggers stale cache fallback."""
    ...
```

### Mocking aiosqlite

Use `MagicMock` (not `AsyncMock`) for `db.execute()`:

```python
mock_cursor = MagicMock()
mock_cursor.fetchone.return_value = {"id": "123", "name": "test"}

ctx = AsyncMock()
ctx.__aenter__.return_value = mock_cursor
mock_db.execute = MagicMock(return_value=ctx)
```

### Patching Service Singletons

Patch at the import location, not the definition:

```python
@patch("src.api.projects.github_projects_service")
async def test_list_projects(mock_service, auth_client):
    mock_service.list_user_projects = AsyncMock(return_value=[...])
    ...
```

### WebSocket Testing

```python
async def test_websocket_disconnect(auth_client):
    with auth_client.websocket_connect("/api/v1/projects/123/subscribe") as ws:
        # Simulate disconnect
        ...
```

## Troubleshooting

### Test Discovery Issues

If new tests aren't discovered, check:
- File naming: `test_*.py`
- Function naming: `test_*` or `async def test_*`
- `asyncio_mode = "auto"` in `pyproject.toml`

### Mock Patching Failures

If patches don't take effect, verify:
- Patch target is the import location (e.g., `src.api.projects.github_projects_service`)
- Not the definition location (e.g., `src.services.github_projects.GitHubProjectsService`)

### Coverage Below Target

If coverage isn't reaching targets:
- Run with `--cov-report=term-missing` to see uncovered lines
- Focus on error/exception branches (these have the highest uncovered ratio)
- Check that mocked exceptions are actually raised in test context
