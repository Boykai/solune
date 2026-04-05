# Quickstart: Increase Test Coverage with Meaningful Tests

## Goal

Implement the coverage feature described in `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/spec.md` by adding meaningful backend and frontend tests, fixing inline defects those tests expose, and verifying the required thresholds without changing test infrastructure.

## Prerequisites

- Repository root: `/home/runner/work/solune/solune`
- Backend package root: `/home/runner/work/solune/solune/solune/backend`
- Frontend package root: `/home/runner/work/solune/solune/solune/frontend`
- Python/UV and Node/npm already available in the development environment

## 1. Backend targeted workflow

```bash
cd /home/runner/work/solune/solune/solune/backend
uv run pytest \
  tests/unit/test_api_chat.py \
  tests/unit/test_api_board.py \
  tests/unit/test_api_apps.py \
  tests/unit/test_utils.py \
  tests/unit/test_api_settings.py \
  tests/unit/test_api_onboarding.py \
  tests/unit/test_api_templates.py \
  tests/unit/test_pipeline_estimate.py \
  tests/unit/test_completion_providers.py
```

## 2. Backend coverage verification

```bash
cd /home/runner/work/solune/solune/solune/backend
uv run pytest tests/unit --cov=src --cov-report=term-missing
uv run ruff check src tests
uv run pyright src
```

Verify:
- backend aggregate line coverage is at least 87%
- backend aggregate branch coverage is at least 78%
- target modules meet the thresholds from `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/spec.md`

## 3. Frontend targeted workflow

```bash
cd /home/runner/work/solune/solune/solune/frontend
npm run test -- \
  src/components/agents/__tests__/AgentsPanel.test.tsx \
  src/components/agents/__tests__/AddAgentModal.test.tsx \
  src/components/agents/__tests__/AgentChatFlow.test.tsx \
  src/components/pipeline/ExecutionGroupCard.test.tsx \
  src/components/pipeline/PipelineModelDropdown.test.tsx \
  src/components/pipeline/PipelineRunHistory.test.tsx \
  src/lib/route-suggestions.test.ts \
  src/lib/commands/registry.test.ts \
  src/context/SyncStatusContext.test.tsx
```

## 4. Frontend coverage verification

```bash
cd /home/runner/work/solune/solune/solune/frontend
npm run test:coverage
npm run lint
npm run type-check
npm run type-check:test
```

Verify:
- frontend statement coverage is at least 63%
- each new or expanded test file covers primary user flows, error states, and edge cases

## 5. Implementation guardrails

- Keep fixes and tests in the same module-focused change.
- Reuse `/home/runner/work/solune/solune/solune/backend/tests/conftest.py` fixtures and `/home/runner/work/solune/solune/solune/frontend/src/test/setup.ts` helpers.
- Prefer API-boundary and user-behavior assertions over implementation-detail assertions.
- Do not add e2e, integration, property, or fuzz tests for this feature.

## 6. Artifact checklist

- `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/plan.md`
- `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/research.md`
- `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/data-model.md`
- `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/quickstart.md`
- `/home/runner/work/solune/solune/specs/003-test-coverage-meaningful/contracts/test-coverage-surfaces.openapi.yaml`
