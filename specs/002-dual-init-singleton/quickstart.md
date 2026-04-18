# Quickstart: Verifying Each User Story

**Feature**: 002-dual-init-singleton
**Audience**: implementer of the per-story PRs and reviewers.

This document gives copy-pasteable verification recipes for each of the four user stories. Each recipe is the minimum sequence required to satisfy the spec's Acceptance Scenarios and Success Criteria.

All commands assume `pwd == /home/runner/work/solune/solune` (the workspace root) unless stated otherwise.

---

## Story 1 — Single Source of Truth for All Service Singletons (P1)

### Apply

1. In `main.py` lifespan: add `ChatAgentService`, `PipelineRunService`, and `GitHubAuthService` to `app.state`.
2. In `dependencies.py`: remove fallback-to-global logic from `get_github_service`, `get_connection_manager`, `get_database`; add new accessors for `get_chat_agent_service`, `get_pipeline_run_service`, `get_github_auth_service`, `get_alert_dispatcher`.
3. In API modules: replace direct global imports with `Depends(get_X)` in route handler signatures.
4. In `alert_dispatcher.py`: remove `set_dispatcher()` and `get_dispatcher()`.
5. In `main.py` lifespan: remove `set_dispatcher(_alert_dispatcher)` call.

### Verify

```bash
cd solune/backend

# 1. No fallback-to-global logic remains in accessors
grep -n 'getattr.*app.state' src/dependencies.py
# MUST return zero matches

# 2. No module-level global imports of singletons in API modules
grep -rn 'from src.services.github_projects import github_projects_service' src/api/
grep -rn 'from src.services.websocket import connection_manager' src/api/
grep -rn 'from src.services.github_auth import github_auth_service' src/api/
grep -rn 'from src.services.chat_agent import get_chat_agent_service' src/api/
# ALL MUST return zero matches

# 3. set_dispatcher / get_dispatcher removed
grep -rn 'set_dispatcher\|get_dispatcher' src/services/alert_dispatcher.py
# MUST return zero matches (except comments, if any)

# 4. All tests pass
uv run pytest --timeout=120 -x -q
# MUST exit 0
```

### Canary (Acceptance Scenario US1.1)

```bash
# Start the app and verify all singletons are on app.state
cd solune/backend
python -c "
import asyncio
from src.main import create_app

app = create_app()

async def check():
    async with app.router.lifespan_context(app):
        for attr in [
            'github_service', 'connection_manager', 'chat_agent_service',
            'pipeline_run_service', 'github_auth_service', 'alert_dispatcher', 'db',
        ]:
            val = getattr(app.state, attr, 'MISSING')
            assert val != 'MISSING' and val is not None, f'{attr} is {val}'
            print(f'  ✅ app.state.{attr} = {type(val).__name__}')
    print('All singletons registered on app.state.')

asyncio.run(check())
"
# MUST print ✅ for all seven services and exit 0
```

---

## Story 2 — Resettable State Registry for Test Isolation (P2)

### Apply

1. Create `src/services/resettable_state.py` with `register_resettable()` and `reset_all()`.
2. In each module with mutable state: add `register_resettable()` calls for every variable currently cleared in `_clear_test_caches()`.
3. Replace `_clear_test_caches()` body in `conftest.py` with `reset_all()` calls.

### Verify

```bash
cd solune/backend

# 1. Registry module exists
python -c "from src.services.resettable_state import register_resettable, reset_all; print('OK')"
# MUST print OK

# 2. Count registered entries (should match or exceed the ~50 manual clears)
python -c "
from src.services.resettable_state import _registry
# Force-import all modules that register state
import src.services.copilot_polling.state
import src.services.template_files
import src.services.pipeline_state_store
# ... etc
print(f'Registered entries: {len(_registry)}')
"

# 3. All tests pass with registry-based cleanup
uv run pytest --timeout=120 -x -q
# MUST exit 0

# 4. conftest.py no longer has manual clear lines
grep -c '\.clear()' tests/conftest.py
# SHOULD be significantly reduced (ideally 0 inside _clear_test_caches)
```

### Canary (Acceptance Scenario US2.1 — state auto-resets between tests)

```bash
cd solune/backend
cat > /tmp/test_resettable_canary.py << 'EOF'
"""Canary: verify that resettable state auto-resets between tests."""
import src.services.copilot_polling.state as ps

def test_mutate_devops_tracking():
    """Populate devops tracking — next test must find it empty."""
    ps._devops_tracking["canary"] = {"key": "value"}
    assert len(ps._devops_tracking) == 1

def test_devops_tracking_is_empty():
    """If the registry works, this dict was cleared by the autouse fixture."""
    assert len(ps._devops_tracking) == 0
EOF
uv run pytest /tmp/test_resettable_canary.py -v
# MUST pass both tests
rm /tmp/test_resettable_canary.py
```

---

## Story 3 — Tests Mock at the FastAPI Boundary Only (P3)

### Apply

1. Remove all service-singleton `patch()` calls from `conftest.py`'s `client` fixture.
2. Keep only `app.dependency_overrides` entries for mocking.
3. Update individual test files that had their own `patch()` calls for singletons.

### Verify

```bash
cd solune/backend

# 1. No service-singleton patch() calls in conftest.py
grep -n 'patch.*github_projects_service' tests/conftest.py
grep -n 'patch.*connection_manager' tests/conftest.py
grep -n 'patch.*github_auth_service' tests/conftest.py
grep -n 'patch.*get_chat_agent_service' tests/conftest.py
# ALL MUST return zero matches

# 2. dependency_overrides covers all services
grep -n 'dependency_overrides' tests/conftest.py
# SHOULD show entries for get_github_service, get_connection_manager,
# get_database, get_chat_agent_service, get_pipeline_run_service,
# get_github_auth_service, get_alert_dispatcher

# 3. Total patch count for service singletons across test suite
grep -rn "patch.*github_projects_service\|patch.*connection_manager\|patch.*github_auth_service\|patch.*get_chat_agent_service\|patch.*_run_service_instance" tests/
# SHOULD return zero matches (all replaced by dependency_overrides)

# 4. All tests pass
uv run pytest --timeout=120 -x -q
# MUST exit 0
```

### Canary (Acceptance Scenario US3.1 — single override replaces all patches)

```bash
cd solune/backend
cat > /tmp/test_override_canary.py << 'EOF'
"""Canary: single dependency_overrides entry mocks the service everywhere."""
import pytest
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient
from src.main import create_app
from src.dependencies import get_github_service

@pytest.mark.asyncio
async def test_override_reaches_all_routes():
    """Setting dependency_overrides[get_github_service] mocks every route."""
    app = create_app()
    mock = AsyncMock()
    mock.get_last_rate_limit.return_value = None
    app.dependency_overrides[get_github_service] = lambda: mock

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Any endpoint that uses Depends(get_github_service) receives the mock
        # (specific endpoint and expected response depend on the route)
        pass  # Replace with an actual endpoint call

    del app.dependency_overrides[get_github_service]
EOF
# This is a template — fill in the specific endpoint for the actual canary test
rm /tmp/test_override_canary.py
```

---

## Story 4 — Module-Level Caches and Mutable Dicts Centralised (P4)

### Apply

1. Register `_cached_files`, `_cached_warnings` (template_files.py) with resettable registry.
2. Register `_devops_tracking` and all other `copilot_polling/state.py` collections.
3. Move AlertDispatcher fully to `app.state`; remove module-level `set_dispatcher()`/`get_dispatcher()`.
4. Register all remaining ad-hoc-cleared state from `_clear_test_caches()`.

### Verify

```bash
cd solune/backend

# 1. Template files cache is registered
grep -n 'register_resettable.*template_files' src/services/template_files.py
# MUST return at least 2 matches (_cached_files, _cached_warnings)

# 2. Devops tracking is registered
grep -n 'register_resettable.*devops_tracking' src/services/copilot_polling/state.py
# MUST return at least 1 match

# 3. set_dispatcher / get_dispatcher removed
grep -rn 'def set_dispatcher\|def get_dispatcher' src/services/alert_dispatcher.py
# MUST return zero matches

# 4. All tests pass
uv run pytest --timeout=120 -x -q
# MUST exit 0
```

### Canary (Acceptance Scenario US4.1 — template cache auto-resets)

```bash
cd solune/backend
cat > /tmp/test_cache_canary.py << 'EOF'
"""Canary: template file cache resets automatically between tests."""
import src.services.template_files as tf

def test_populate_template_cache():
    """Set _cached_files to a non-None value."""
    tf._cached_files = [{"name": "canary.yaml", "content": "test"}]
    assert tf._cached_files is not None

def test_template_cache_is_none():
    """If the registry works, _cached_files was reset to None."""
    assert tf._cached_files is None
EOF
uv run pytest /tmp/test_cache_canary.py -v
# MUST pass both tests
rm /tmp/test_cache_canary.py
```

---

## Success Criteria mapping

| Story | Success Criteria covered |
|---|---|
| 1 | SC-001 (single source of truth), SC-007 (no startup degradation) |
| 2 | SC-003 (80% reduction in manual cleanup), SC-005 (zero test-isolation failures), SC-006 (single registration point) |
| 3 | SC-002 (zero singleton patch paths), SC-004 (single override line for mocking) |
| 4 | SC-003 (continued), SC-005 (continued) |
| All | SC-005 (full test suite passes), FR-012 (backward compatibility) |
