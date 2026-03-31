# Quickstart: Fix Parallel Pipeline Execution Bugs

**Feature**: 001-fix-parallel-pipeline | **Date**: 2026-03-31

## Prerequisites

- Python ≥3.12
- Repository cloned: `solune/backend/`
- Dev dependencies installed: `cd solune/backend && pip install -e ".[dev]"`

## Verification Steps

### 1. Verify Model Layer Fixes

Run the model tests to confirm `current_agents` and `is_complete` behave correctly:

```bash
cd solune/backend
python -m pytest tests/unit/test_models.py -v -k "current_agents or sequential_complete"
```

**Expected**: All new tests pass. `current_agents` returns all parallel agents; `is_complete` detects sequential group completion.

### 2. Verify Polling Loop Fixes

Run the polling tests to confirm parallel agents are checked each cycle:

```bash
cd solune/backend
python -m pytest tests/unit/test_copilot_polling.py -v -k "parallel"
```

**Expected**: All parallel polling tests pass, including the new test that verifies all agents in a parallel group are checked per cycle.

### 3. Verify Property Invariants

Run property-based tests to ensure no invariants are broken:

```bash
cd solune/backend
python -m pytest tests/property/test_pipeline_state_machine.py -v
```

**Expected**: All property tests pass with no regressions.

### 4. Full Regression Suite

Run the complete test suite:

```bash
cd solune/backend
python -m pytest tests/unit/ tests/property/ -q
```

**Expected**: All existing tests pass. Zero regressions.

### 5. Manual Verification

Trigger a pipeline with a parallel group of 3 agents:

1. Create an issue with a workflow configuration that has a parallel group (e.g., `linter`, `archivist`, `judge`)
2. Move the issue to "In Progress" to trigger the pipeline
3. Observe the pipeline status — all 3 agents should show 🔄 Active simultaneously within one polling cycle
4. Verify agents complete independently and the group advances once all 3 are terminal

**Expected**: All agents in the parallel group show Active status simultaneously — NOT 1 Active + 2 Pending.

## Key Files

| File | What to Check |
|------|---------------|
| `src/services/workflow_orchestrator/models.py` | `current_agents` property and `is_complete` fix |
| `src/services/copilot_polling/pipeline.py` | `_process_pipeline_completion` parallel loop |
| `tests/unit/test_models.py` | New property tests |
| `tests/unit/test_copilot_polling.py` | New polling loop test |

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Only 1 agent Active in parallel group | `current_agents` not returning all agents | Check `agent_statuses` map is populated for the group |
| Sequential group never completes | `is_complete` still returns False | Verify `current_agent_index_in_group` is advancing past `len(group.agents)` |
| Recovery only dispatches first agent | Recovery path still using `current_agent` | Ensure recovery loop iterates `current_agents` |
