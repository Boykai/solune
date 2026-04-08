# Quickstart: AI Stock Trading Simulation App

**Feature**: 020-ai-stock-trading-simulation | **Date**: 2026-04-08

> Step-by-step developer guide for implementing the AI stock trading simulation. Each step is independently verifiable — run the validation command after completing each step.

## Prerequisites

```bash
# Backend
cd solune/backend
PATH=$HOME/.local/bin:$PATH uv sync --extra dev

# Frontend
cd solune/frontend
npm ci

# Docker (for full stack)
docker compose up --build
```

## Environment Variables

Create or update `solune/.env` with:

```bash
# Azure OpenAI (required for agent orchestration)
AZURE_OPENAI_ENDPOINT=https://your-instance.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# Market data provider (optional — defaults to synthetic)
MARKET_DATA_PROVIDER=synthetic  # or "yahoo" for delayed real data

# Existing Solune config (already in .env.example)
SESSION_SECRET_KEY=your-session-secret
FRONTEND_URL=http://localhost:5173
```

## Validation Commands

```bash
# Backend lint + type check
cd solune/backend && uv run ruff check src tests && uv run pyright src

# Backend unit tests (run after each backend step)
cd solune/backend && uv run pytest tests/unit/ -x -q

# Frontend lint + type check
cd solune/frontend && npm run lint && npm run type-check

# Frontend tests (run after each frontend step)
cd solune/frontend && npx vitest run --reporter=verbose

# Full stack (Docker)
docker compose up --build
# Verify: http://localhost:8000/api/v1/health → 200
# Verify: http://localhost:5173 → Frontend loads
```

---

## Phase 1 — Project Scaffold & Infrastructure

### Step 1.1: Database Migrations

**Files**: `solune/backend/src/migrations/050_portfolios.sql` through `055_simulations.sql`

Create the 6 migration files as defined in `data-model.md`. Each migration uses `CREATE TABLE IF NOT EXISTS` for idempotency.

**Verify**: Backend starts without errors; tables created in SQLite.

### Step 1.2: Add New Dependencies

**Backend** (`solune/backend/pyproject.toml`):

```toml
# Add to [project.dependencies]:
"pyautogen>=0.2.35,<0.3",  # Microsoft AutoGen for multi-agent orchestration
```

**Frontend** (`solune/frontend/package.json`):

```bash
cd solune/frontend
npm install recharts
```

**Verify**: `cd solune/backend && uv sync --extra dev` and `cd solune/frontend && npm ci` succeed.

### Step 1.3: Register New API Routers

**File**: `solune/backend/src/main.py` (or wherever routers are registered)

Add new router imports and include statements for: `market`, `trading`, `agents_trading`, `simulation`, `analytics`.

**Verify**: Backend starts; new endpoints appear (404 until implemented).

---

## Phase 2 — Stock Data Service

### Step 2.1: Create Market Data Models

**File**: `solune/backend/src/models/market.py`

Define `Quote`, `OHLCV`, and `MarketTick` Pydantic models as specified in `data-model.md`.

**Verify**: `cd solune/backend && uv run python -c "from src.models.market import Quote, OHLCV, MarketTick; print('OK')"`

### Step 2.2: Implement Synthetic Data Provider

**File**: `solune/backend/src/services/market/synthetic_provider.py`

Implement Geometric Brownian Motion generator:

```python
# Key formula: S(t+dt) = S(t) * exp((μ - σ²/2)*dt + σ*√dt*Z)
# where Z ~ N(0,1)
```

Preset parameters for common symbols (AAPL, MSFT, GOOGL, TSLA, AMZN).

**Verify**: `cd solune/backend && uv run pytest tests/unit/test_market_service.py -x -q`

### Step 2.3: Implement Yahoo Finance Provider (Optional)

**File**: `solune/backend/src/services/market/yahoo_provider.py`

Wrap `yfinance` with graceful fallback to synthetic on import error or network failure.

**Verify**: Provider returns data or falls back silently.

### Step 2.4: Implement Market REST API

**File**: `solune/backend/src/api/market.py`

Endpoints:
- `GET /api/market/quote/{symbol}` → returns `Quote`
- `GET /api/market/history/{symbol}?days=30` → returns `list[OHLCV]`
- `GET /api/market/symbols` → returns watchlist symbols

**Verify**: `curl http://localhost:8000/api/market/quote/AAPL` returns JSON with price data.

### Step 2.5: Implement Market WebSocket Feed

**File**: `solune/backend/src/services/market/websocket_feed.py`

WebSocket endpoint `/ws/market` that pushes `MarketTick` events at configurable interval.

**Verify**: Connect with `websocat ws://localhost:8000/ws/market` — receive tick updates.

---

## Phase 3 — Portfolio & Trade Engine

### Step 3.1: Create Trading Models

**File**: `solune/backend/src/models/trading.py`

Define `Portfolio`, `Holding`, `Order`, `Trade` Pydantic models.

**Verify**: Models import and validate correctly.

### Step 3.2: Implement Portfolio Manager

**File**: `solune/backend/src/services/trading/portfolio_manager.py`

CRUD operations: create_portfolio, get_portfolio, list_portfolios, update_cash_balance.

**Verify**: `cd solune/backend && uv run pytest tests/unit/test_trade_engine.py::test_create_portfolio -x -q`

### Step 3.3: Implement Order Executor

**File**: `solune/backend/src/services/trading/order_executor.py`

Execute market/limit orders with slippage model. Update holdings and cash balance.

**Verify**: `cd solune/backend && uv run pytest tests/unit/test_trade_engine.py::test_buy_order -x -q`

### Step 3.4: Implement P&L Calculator

**File**: `solune/backend/src/services/trading/pnl_calculator.py`

FIFO cost basis P&L calculation for sell trades.

**Verify**: `cd solune/backend && uv run pytest tests/unit/test_trade_engine.py::test_pnl_calculation -x -q`

### Step 3.5: Implement Trading REST API

**File**: `solune/backend/src/api/trading.py`

Endpoints:
- `POST /api/portfolio` → create portfolio
- `GET /api/portfolio/{id}` → get portfolio with holdings
- `POST /api/orders` → submit order
- `GET /api/orders?portfolio_id=X` → list orders
- `GET /api/trades?portfolio_id=X` → list trades

**Verify**: Create portfolio, buy shares, verify holdings updated.

---

## Phase 4 — Azure OpenAI Integration

### Step 4.1: Implement Azure OpenAI Client

**File**: `solune/backend/src/services/ai/azure_openai.py`

Wrapper around `openai.AsyncAzureOpenAI` with:
- Environment variable configuration
- Streaming support
- Token usage tracking
- Cost estimation

**Verify**: Client initializes without errors (even if API key is invalid — test graceful degradation).

---

## Phase 5 — Multi-Agent Framework

### Step 5.1: Implement Agent Definitions

**Files**: `solune/backend/src/services/agents/market_analyst.py`, `risk_manager.py`, `trader.py`

Each agent:
- Has a specific system prompt defining its role
- Has registered tool functions (e.g., MarketAnalyst can call `get_quote`, `get_history`)
- Uses Azure OpenAI via the client wrapper

**Verify**: Agents can be instantiated and respond to test prompts.

### Step 5.2: Implement Orchestrator

**File**: `solune/backend/src/services/agents/orchestrator.py`

GroupChat + GroupChatManager setup. Configurable max turns, termination conditions.

**Verify**: `cd solune/backend && uv run pytest tests/unit/test_agent_tools.py -x -q`

### Step 5.3: Implement Session Manager

**File**: `solune/backend/src/services/agents/session_manager.py`

Persist conversation to SQLite. Stream messages via WebSocket.

**Verify**: Session created, messages stored, WebSocket receives messages.

### Step 5.4: Implement Agent REST API

**File**: `solune/backend/src/api/agents_trading.py`

Endpoints:
- `POST /api/agents/run` → trigger trading session (returns session_id)
- `GET /api/agents/sessions/{id}` → get session with messages

WebSocket: `/ws/agents/{session_id}` → stream agent messages

**Verify**: POST creates session; GET returns session data; WebSocket streams messages.

---

## Phase 6 — Trading Dashboard (Frontend)

### Step 6.1: Create Trading API Service

**File**: `solune/frontend/src/services/tradingApi.ts`

REST client functions using `fetch` or existing API patterns:
- `getQuote(symbol)`, `getHistory(symbol)`, `getSymbols()`
- `createPortfolio(config)`, `getPortfolio(id)`, `submitOrder(order)`
- `runAgentSession(config)`, `getAgentSession(id)`

**Verify**: TypeScript compiles without errors.

### Step 6.2: Create WebSocket Hooks

**Files**: `solune/frontend/src/hooks/useMarketFeed.ts`, `useTradingSession.ts`

Custom hooks managing WebSocket connections, reconnection, and state.

**Verify**: `npm run type-check` passes.

### Step 6.3: Create Trading Components

**Files**: `solune/frontend/src/components/trading/*.tsx`

Components: `PriceCard`, `MarketOverview`, `PortfolioSummary`, `PnLChart`, `AgentActivityFeed`, `TradeHistory`, `SymbolSearch`.

Use existing UI primitives (Card, Button, Input) and Tailwind v4 for styling.

**Verify**: `cd solune/frontend && npx vitest run src/pages/TradingDashboard.test.tsx`

### Step 6.4: Create TradingDashboard Page

**File**: `solune/frontend/src/pages/TradingDashboard.tsx`

Grid layout composing all trading components.

**Verify**: Frontend loads at localhost:5173; navigate to trading dashboard.

---

## Phase 7 — Strategy Configuration & Simulation Controls

### Step 7.1: Backend Simulation Engine

**Files**: `solune/backend/src/services/simulation/engine.py`, `state_manager.py`

asyncio background task for simulation loop with speed control.

**Verify**: `cd solune/backend && uv run pytest tests/unit/test_simulation_engine.py -x -q`

### Step 7.2: Simulation REST API

**File**: `solune/backend/src/api/simulation.py`

Endpoints:
- `POST /api/simulation/start` → start/resume simulation
- `POST /api/simulation/stop` → pause/stop simulation
- `GET /api/simulation/status` → get simulation state

**Verify**: Start/stop simulation via API; state persisted.

### Step 7.3: Frontend Strategy Config Page

**Files**: `solune/frontend/src/pages/StrategyConfig.tsx`, components

Strategy textarea, watchlist selector, speed control, risk limits.

**Verify**: `cd solune/frontend && npx vitest run src/pages/StrategyConfig.test.tsx`

---

## Phase 8 — Performance Analytics

### Step 8.1: Backend Analytics Service

**Files**: `solune/backend/src/services/analytics/metrics.py`, `benchmark.py`

Compute: total return, Sharpe ratio, max drawdown, win rate, avg P&L, agent accuracy.

**Verify**: `cd solune/backend && uv run pytest tests/unit/test_analytics_metrics.py -x -q`

### Step 8.2: Analytics REST API

**File**: `solune/backend/src/api/analytics.py`

Endpoints:
- `GET /api/analytics/summary/{portfolio_id}` → returns `PortfolioAnalytics`
- `GET /api/analytics/export/{portfolio_id}` → CSV download

**Verify**: `curl http://localhost:8000/api/analytics/summary/{id}` returns metrics.

### Step 8.3: Frontend Analytics Page

**File**: `solune/frontend/src/pages/Analytics.tsx`

Charts for metrics, buy-and-hold comparison, CSV export button.

**Verify**: `cd solune/frontend && npx vitest run src/pages/Analytics.test.tsx`

---

## Phase 9 — Testing & Production Hardening

### Step 9.1: Backend Lint & Type Check

```bash
cd solune/backend
uv run ruff check src tests
uv run ruff format --check src tests
uv run pyright src
uv run pyright -p pyrightconfig.tests.json
```

### Step 9.2: Backend Unit Tests

```bash
cd solune/backend
uv run pytest tests/unit/ -x -q --cov=src --cov-report=term-missing
```

### Step 9.3: Frontend Lint & Type Check

```bash
cd solune/frontend
npm run lint
npm run type-check
```

### Step 9.4: Frontend Tests

```bash
cd solune/frontend
npx vitest run --reporter=verbose
```

### Step 9.5: Security Checks

```bash
cd solune/backend
uv run bandit -r src/ -ll -ii --skip B104,B608
```

### Step 9.6: Docker Build

```bash
docker compose build
docker compose up
# Verify all services start and health checks pass
```
