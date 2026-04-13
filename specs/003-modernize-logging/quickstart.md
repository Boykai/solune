# Quickstart: Modernize Logging Practices

## Prerequisites

1. Backend environment:

   ```bash
   cd solune/backend
   uv sync --extra dev
   ```

2. Frontend environment:

   ```bash
   cd solune/frontend
   npm install
   ```

## Phase 1 — Verify Backend Structured Logging Fields

```bash
cd solune/backend

# Run backend tests
uv run pytest tests/ -q

# Lint and type-check
uv run ruff check src/ tests/
uv run pyright src/

# Spot-check structured fields in JSON output
STRUCTURED_LOGGING=true uv run python -c "
import logging
from src.logging_utils import setup_structured_logging, STRUCTURED_FIELDS
print('Canonical fields:', STRUCTURED_FIELDS)
setup_structured_logging()
logger = logging.getLogger('test')
logger.info('test operation', extra={'operation': 'quickstart_test', 'duration_ms': 42.5})
"
```

**Expected**: JSON log line includes `"operation": "quickstart_test"` and `"duration_ms": 42.5`.

## Phase 2 — Verify Noisy Logger Silencing

```bash
cd solune/backend

# Start backend at DEBUG level and verify suppressed loggers
LOG_LEVEL=DEBUG uv run python -c "
from src.config import setup_logging
import logging
setup_logging()
for name in ['uvicorn', 'uvicorn.access', 'uvicorn.error', 'asyncio', 'watchfiles']:
    level = logging.getLogger(name).level
    assert level >= logging.WARNING, f'{name} is at {logging.getLevelName(level)}, expected WARNING+'
    print(f'  ✓ {name}: {logging.getLevelName(level)}')
print('All noisy loggers silenced.')
"
```

## Phase 3 — Verify OTel Logs Bridge

```bash
cd solune/backend

# Without OTel (default) — no LoggingHandler attached
uv run python -c "
from src.services.otel_setup import init_otel
import logging
tracer, meter = init_otel()
handlers = [h for h in logging.root.handlers if 'LoggingHandler' in type(h).__name__]
assert len(handlers) == 0, 'LoggingHandler should not be attached when OTEL_ENABLED is not set'
print('  ✓ No LoggingHandler when OTEL_ENABLED is unset')
"

# With OTel enabled + local collector (requires running collector on :4317)
# OTEL_ENABLED=true uv run python -c "
#   from src.services.otel_setup import init_otel
#   import logging
#   tracer, meter = init_otel()
#   handlers = [h for h in logging.root.handlers if 'LoggingHandler' in type(h).__name__]
#   assert len(handlers) == 1, 'Expected exactly one LoggingHandler'
#   print('  ✓ LoggingHandler attached with OTel enabled')
# "
```

## Phase 4 — Verify Frontend Logger Utility

```bash
cd solune/frontend

# Run logger tests
npm run test -- --run src/lib/logger.test.ts

# Verify test coverage
npm run test -- --run --coverage src/lib/logger.test.ts
```

## Phase 5 — Verify Console Call Replacement

```bash
cd solune/frontend

# Audit: zero raw console.* calls outside tests and logger.ts
grep -rn 'console\.\(log\|debug\|warn\|error\)' src/ \
  --include='*.ts' --include='*.tsx' \
  --exclude='*.test.*' \
  --exclude='logger.ts' \
  | grep -v 'node_modules' || echo "  ✓ Zero raw console calls found"

# Full test suite
npm run test
npm run lint
npm run type-check
```

## Phase 6 — Verify Error Utility Consolidation

```bash
cd solune/frontend

# Verify errorUtils.ts exists and exports getErrorMessage
grep -n 'export function getErrorMessage' src/utils/errorUtils.ts

# Verify usePipelineConfig imports from errorUtils (no local errMsg)
grep -n 'errMsg' src/hooks/usePipelineConfig.ts && echo "FAIL: local errMsg still exists" || echo "  ✓ No local errMsg"

# Verify useApps imports from errorUtils
grep -n "from '@/utils/errorUtils'" src/hooks/useApps.ts && echo "  ✓ useApps imports from errorUtils"

# Run affected tests
npm run test -- --run src/hooks/useApps.test.tsx
```

## Full Verification (All Phases)

```bash
# Backend
cd solune/backend
uv run ruff check src/ tests/
uv run pyright src/
uv run pytest tests/ -q

# Frontend
cd ../frontend
npm run lint
npm run type-check
npm run test

# Docker (optional)
cd ../..
docker compose build
```
