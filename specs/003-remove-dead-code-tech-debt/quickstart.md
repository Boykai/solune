# Quickstart: Remove Dead Code & Tech Debt

## Prerequisites

1. Python 3.12+ with `uv` package manager:

   ```bash
   cd solune/backend
   uv sync --extra dev
   ```

2. Node.js 20+ with npm:

   ```bash
   cd solune/frontend
   npm ci
   ```

3. Verify baseline passes before making changes:

   ```bash
   # Backend
   cd solune/backend
   uv run ruff check src/ tests/
   uv run pyright src/
   uv run pytest tests/ --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency -q

   # Frontend
   cd solune/frontend
   npm run lint
   npm run type-check
   npm run test
   ```

## Phase 1 — Remove Deprecated Prompt Modules

```bash
cd solune/backend

# Delete deprecated prompt files
rm src/prompts/issue_generation.py
rm src/prompts/task_generation.py
rm src/prompts/transcript_analysis.py

# Delete corresponding tests
rm tests/unit/test_issue_generation_prompt.py
rm tests/unit/test_task_generation_prompt.py
rm tests/unit/test_transcript_analysis_prompt.py

# Verify no re-exports in prompts/__init__.py
grep -n "issue_generation\|task_generation\|transcript_analysis" src/prompts/__init__.py

# Run tests (ai_agent.py will fail — expected until Phase 2)
uv run pytest tests/ --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency -q
```

## Phase 2 — Remove AIAgentService

```bash
cd solune/backend

# Step 1: Migrate each consumer (see plan.md for file-by-file details)
# - api/chat.py: get_ai_agent_service → get_chat_agent_service
# - services/app_service.py: replace lazy import
# - services/chores/chat.py: _call_completion → ChatAgentService.run()
# - services/agents/service.py: _call_completion → ChatAgentService.run()
# - api/pipelines.py: analyze_transcript → new utility
# - services/workflow_orchestrator/orchestrator.py: type + factory
# - services/agent_creator.py: generate_agent_config → new method
# - services/signal_chat.py: existence check → config check

# Step 2: Update test infrastructure
# - tests/conftest.py: remove AIAgentService import and mock_ai_agent_service fixture
# - Update any tests depending on mock_ai_agent_service

# Step 3: Delete deprecated files
rm src/services/ai_agent.py
rm tests/unit/test_ai_agent.py

# Step 4: Verify clean removal
grep -rn "ai_agent" src/ tests/  # Should return zero hits

# Step 5: Full validation
uv run ruff check src/ tests/
uv run pyright src/
uv run pytest tests/ --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency -q
```

## Phase 3 — Remove completion_providers.py

```bash
cd solune/backend

# Step 1: Relocate CopilotClientPool + get_copilot_client_pool to agent_provider.py
# (Move ~75 lines of code from completion_providers.py to agent_provider.py)

# Step 2: Update consumers
# - agent_provider.py: local import
# - plan_agent_provider.py: import from agent_provider
# - model_fetcher.py: import from agent_provider
# - label_classifier.py: replace create_completion_provider with agent_provider pattern

# Step 3: Delete deprecated files
rm src/services/completion_providers.py
rm tests/unit/test_completion_providers.py

# Step 4: Verify clean removal
grep -rn "completion_providers" src/ tests/  # Should return zero hits

# Step 5: Full validation
uv run ruff check src/ tests/
uv run pyright src/
uv run pytest tests/ --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency -q
```

## Phase 4 — Minor Backend Cleanup

```bash
cd solune/backend

# Evaluate pipeline_metadata (decision: DEFER — see research.md Decision 6)
# The field is actively mutated in the retry flow at auto_merge.py L540

# Check for singleton TODO markers
grep -rn "TODO.*singleton\|TODO-018" src/services/chores/service.py src/services/agents/service.py

# If found: convert to tracked issue reference
# If not found at specified lines: document discrepancy and skip

uv run ruff check src/
uv run pyright src/
```

## Phase 5 — Frontend Logging Cleanup

```bash
cd solune/frontend

# api.ts: Wrap console.debug calls in DEV guard
# L462: if (import.meta.env.DEV) { console.debug('[SSE] Failed to parse...'); }
# L477: if (import.meta.env.DEV) { console.debug('[SSE] Unexpected error...'); }
# L641: if (import.meta.env.DEV) { console.debug('[SSE] Failed to parse plan...'); }

# tooltip.tsx: Already guarded — NO CHANGE NEEDED
# L51-52: if (import.meta.env.DEV) { console.warn(...) }

# usePipelineConfig.ts: Wrap console.warn in DEV guard
# L170: if (import.meta.env.DEV) { console.warn('Pipeline assignment failed:', err); }

# Validate
npm run lint
npm run type-check
npm run test
```

## Phase 6 — Repository Organization

```bash
# Move root-level spec files to mono-spec directory
mkdir -p specs/000-simplify-page-headers
mv plan.md specs/000-simplify-page-headers/
mv spec.md specs/000-simplify-page-headers/
mv tasks.md specs/000-simplify-page-headers/
mv data-model.md specs/000-simplify-page-headers/
mv research.md specs/000-simplify-page-headers/
mv quickstart.md specs/000-simplify-page-headers/

# Verify structure matches mono-spec pattern
ls -la specs/000-simplify-page-headers/
ls -la specs/001-fleet-dispatch-pipelines/
```

## Final Verification

```bash
# Full dead-code grep (should return ZERO hits after Phase 3)
grep -rn "ai_agent\|completion_providers\|issue_generation\|task_generation\|transcript_analysis" \
  solune/backend/src/ solune/backend/tests/

# Backend full suite
cd solune/backend
uv run pytest tests/ --ignore=tests/property --ignore=tests/fuzz --ignore=tests/chaos --ignore=tests/concurrency

# Frontend full suite
cd solune/frontend
npm run test

# OpenAPI schema validation
./validate-contracts.sh

# Docker builds
docker compose build
```
