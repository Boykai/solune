# Contract: Backend Central Autouse Fixture

**Feature**: 019-test-isolation-remediation | **Date**: 2026-04-07

## Purpose

Defines the contract for the expanded `_clear_test_caches` autouse fixture in `solune/backend/tests/conftest.py`.

## Fixture Signature

```python
@pytest.fixture(autouse=True)
def _clear_test_caches() -> Iterator[None]:
    """Clear all global caches and mutable module state between tests."""
```

## Behavior Contract

### Pre-Test (Setup)

The fixture MUST clear ALL of the following before each test:

#### Collections (`.clear()`)

| Module | Variable | Type |
|--------|----------|------|
| `src.api.chat` | `_messages` | `dict` |
| `src.api.chat` | `_proposals` | `dict` |
| `src.api.chat` | `_recommendations` | `dict` |
| `src.api.chat` | `_locks` | `dict` |
| `src.services.pipeline_state_store` | `_pipeline_states` | `BoundedDict` |
| `src.services.pipeline_state_store` | `_issue_main_branches` | `BoundedDict` |
| `src.services.pipeline_state_store` | `_issue_sub_issue_map` | `BoundedDict` |
| `src.services.pipeline_state_store` | `_project_launch_locks` | `dict` |
| `src.services.workflow_orchestrator` | `_transitions` | `list` |
| `src.services.workflow_orchestrator` | `_workflow_configs` | `BoundedDict` |
| `src.services.workflow_orchestrator.transitions` | `_agent_trigger_inflight` | `BoundedDict` |
| `src.services.workflow_orchestrator.orchestrator` | `_tracking_table_cache` | `BoundedDict` |
| `src.services.copilot_polling.state` | 15 collections | `BoundedDict/BoundedSet/dict/set` |
| `src.services.settings_store` | `_queue_mode_cache` | `dict` |
| `src.services.settings_store` | `_auto_merge_cache` | `dict` |
| `src.services.signal_chat` | `_signal_pending` | `dict` |
| `src.services.github_auth` | `_oauth_states` | `BoundedDict` |
| `src.services.agent_creator` | `_agent_sessions` | `BoundedDict` |

#### Locks (reset to `None`)

| Module | Variable | Reason |
|--------|----------|--------|
| `src.services.pipeline_state_store` | `_store_lock` | Lazy-init — reset to `None` |
| `src.services.websocket` | `_ws_lock` | Lazy-init — reset to `None` |
| `src.services.copilot_polling.state` | `_polling_state_lock` | Direct use — reset to `asyncio.Lock()` |
| `src.services.copilot_polling.state` | `_polling_startup_lock` | Direct use — reset to `asyncio.Lock()` |

#### Optional/Singleton Values (reset to `None`)

| Module | Variable | Type |
|--------|----------|------|
| `src.services.workflow_orchestrator.orchestrator` | `_orchestrator_instance` | `WorkflowOrchestrator \| None` |
| `src.services.pipeline_state_store` | `_db` | `aiosqlite.Connection \| None` |
| `src.services.copilot_polling.state` | `_polling_task` | `asyncio.Task \| None` |
| `src.services.template_files` | `_cached_files` | `list \| None` |
| `src.services.template_files` | `_cached_warnings` | `list \| None` |
| `src.services.app_templates.registry` | `_cache` | `dict \| None` |
| `src.services.done_items_store` | `_db` | `aiosqlite.Connection \| None` |
| `src.services.session_store` | `_encryption_service` | `EncryptionService \| None` |

#### Scalars (reset to default)

| Module | Variable | Default |
|--------|----------|---------|
| `src.services.copilot_polling.state` | `_consecutive_idle_polls` | `0` |
| `src.services.copilot_polling.state` | `_adaptive_tier` | `"medium"` |
| `src.services.copilot_polling.state` | `_consecutive_poll_failures` | `0` |

#### Stateful Objects (reset to fresh instance)

| Module | Variable | Reset Expression |
|--------|----------|-----------------|
| `src.services.copilot_polling.state` | `_polling_state` | `PollingState()` |
| `src.services.copilot_polling.state` | `_activity_window` | `.clear()` |

#### Function Caches

| Module | Method | Type |
|--------|--------|------|
| `src.config` | `clear_settings_cache()` | `@lru_cache` invalidation |
| `src.services.cache` | `cache.clear()` | In-memory dict cache |

### Post-Test (Teardown)

The fixture MUST repeat the same cleanup after the `yield` to ensure teardown isolation.

## Invariants

1. **Completeness**: Every module-level mutable variable in `src/` that is not a constant MUST be cleared
2. **Lock Safety**: asyncio locks MUST be reset to `None`, NEVER to `asyncio.Lock()`
3. **Idempotency**: Calling `_reset()` twice in a row has no additional effect
4. **No Production Changes**: The fixture imports and resets values but does not modify any production code
5. **Defense-in-Depth**: The integration conftest fixture remains as a secondary safety layer
