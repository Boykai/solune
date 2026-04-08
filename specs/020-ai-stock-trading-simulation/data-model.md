# Data Model: AI Stock Trading Simulation App

**Feature**: 020-ai-stock-trading-simulation | **Date**: 2026-04-08

## Overview

This document defines all data entities for the AI stock trading simulation. The system uses SQLite (via aiosqlite) following existing Solune database conventions (WAL mode, migration files in `src/migrations/`). Pydantic models serve as the API layer; SQLite tables serve as the persistence layer.

## Entity Relationship Diagram

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│  Simulation  │──1:1──│  Portfolio   │──1:N──│   Holding    │
└──────────────┘       └──────────────┘       └──────────────┘
       │                      │
       │                      │ 1:N
       │               ┌──────────────┐
       │               │    Order     │
       │               └──────────────┘
       │                      │ 1:1
       │               ┌──────────────┐
       │               │    Trade     │
       │               └──────────────┘
       │
       │ 1:N
┌──────────────┐       ┌──────────────┐
│ AgentSession │──1:N──│ AgentMessage │
└──────────────┘       └──────────────┘
```

## Backend Pydantic Models

### Entity: Quote (`models/market.py`)

Represents a real-time or simulated stock quote.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `symbol` | `str` | Ticker symbol (e.g., "AAPL") | `min_length=1, max_length=10, pattern=^[A-Z0-9.]+$` |
| `price` | `float` | Current price | `gt=0` |
| `change` | `float` | Price change from previous close | — |
| `change_percent` | `float` | Percentage change | — |
| `volume` | `int` | Trading volume | `ge=0` |
| `timestamp` | `datetime` | Quote timestamp | — |
| `source` | `Literal["synthetic", "yahoo"]` | Data source | — |

### Entity: OHLCV (`models/market.py`)

Represents a single candlestick bar of historical price data.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `symbol` | `str` | Ticker symbol | `min_length=1, max_length=10` |
| `date` | `date` | Trading date | — |
| `open` | `float` | Opening price | `gt=0` |
| `high` | `float` | Highest price | `gt=0` |
| `low` | `float` | Lowest price | `gt=0` |
| `close` | `float` | Closing price | `gt=0` |
| `volume` | `int` | Trading volume | `ge=0` |

**Validation**: `high >= max(open, close)` and `low <= min(open, close)`

### Entity: MarketTick (`models/market.py`)

WebSocket message for real-time price updates.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `type` | `Literal["market_tick"]` | Event type discriminator | — |
| `symbol` | `str` | Ticker symbol | — |
| `price` | `float` | Current price | `gt=0` |
| `change_percent` | `float` | Change from session open | — |
| `volume` | `int` | Cumulative session volume | `ge=0` |
| `timestamp` | `datetime` | Tick timestamp | — |

### Entity: Portfolio (`models/trading.py`)

Represents a virtual trading portfolio.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `id` | `str` | UUID primary key | — |
| `name` | `str` | Portfolio name | `min_length=1, max_length=100` |
| `initial_cash` | `float` | Starting cash balance | `gt=0, le=10_000_000` |
| `cash_balance` | `float` | Current available cash | `ge=0` |
| `created_at` | `datetime` | Creation timestamp | — |
| `updated_at` | `datetime` | Last update timestamp | — |

**Derived fields** (computed, not stored):
- `total_value`: `cash_balance + sum(holding.market_value for holding in holdings)`
- `total_pnl`: `total_value - initial_cash`
- `total_pnl_percent`: `total_pnl / initial_cash × 100`

### Entity: Holding (`models/trading.py`)

Represents a stock position within a portfolio.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `id` | `str` | UUID primary key | — |
| `portfolio_id` | `str` | FK to Portfolio | — |
| `symbol` | `str` | Ticker symbol | `min_length=1, max_length=10` |
| `quantity` | `int` | Number of shares held | `gt=0` |
| `avg_cost_basis` | `float` | Average cost per share (FIFO) | `gt=0` |
| `market_value` | `float` | Current market value (`quantity × current_price`) | — |
| `unrealized_pnl` | `float` | `market_value - (quantity × avg_cost_basis)` | — |
| `updated_at` | `datetime` | Last update timestamp | — |

**Constraints**: Unique on `(portfolio_id, symbol)` — one holding per symbol per portfolio.

### Entity: Order (`models/trading.py`)

Represents a buy or sell order.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `id` | `str` | UUID primary key | — |
| `portfolio_id` | `str` | FK to Portfolio | — |
| `symbol` | `str` | Ticker symbol | `min_length=1, max_length=10` |
| `side` | `Literal["buy", "sell"]` | Order direction | — |
| `order_type` | `Literal["market", "limit"]` | Order type | — |
| `quantity` | `int` | Number of shares | `gt=0` |
| `limit_price` | `float \| None` | Limit price (required for limit orders) | `gt=0` if set |
| `status` | `Literal["pending", "filled", "cancelled", "rejected"]` | Order status | — |
| `reject_reason` | `str \| None` | Reason if rejected (e.g., by RiskManager) | — |
| `created_at` | `datetime` | Order creation timestamp | — |
| `filled_at` | `datetime \| None` | Fill timestamp | — |
| `agent_session_id` | `str \| None` | FK to AgentSession if agent-initiated | — |

**State transitions**:
```
pending → filled    (order executed successfully)
pending → cancelled (user or simulation cancelled)
pending → rejected  (RiskManager veto or insufficient funds)
```

### Entity: Trade (`models/trading.py`)

Represents an executed trade (fill record).

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `id` | `str` | UUID primary key | — |
| `order_id` | `str` | FK to Order | — |
| `portfolio_id` | `str` | FK to Portfolio | — |
| `symbol` | `str` | Ticker symbol | — |
| `side` | `Literal["buy", "sell"]` | Trade direction | — |
| `quantity` | `int` | Shares traded | `gt=0` |
| `price` | `float` | Execution price (after slippage) | `gt=0` |
| `slippage` | `float` | Slippage amount | — |
| `total_cost` | `float` | `quantity × price` | — |
| `realized_pnl` | `float \| None` | P&L for sell trades (FIFO) | — |
| `executed_at` | `datetime` | Execution timestamp | — |

### Entity: AgentSession (`models/agent_session.py`)

Represents a multi-agent trading session (one GroupChat conversation).

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `id` | `str` | UUID primary key | — |
| `portfolio_id` | `str` | FK to Portfolio | — |
| `simulation_id` | `str \| None` | FK to Simulation (if part of a sim) | — |
| `symbol` | `str` | Symbol being analyzed | — |
| `strategy_text` | `str` | Natural language strategy from user | `max_length=2000` |
| `status` | `Literal["running", "completed", "failed", "cancelled"]` | Session status | — |
| `outcome` | `Literal["buy", "sell", "hold"] \| None` | Final decision | — |
| `total_tokens` | `int` | Total tokens consumed | `ge=0` |
| `estimated_cost_usd` | `float` | Estimated API cost | `ge=0` |
| `created_at` | `datetime` | Session start | — |
| `completed_at` | `datetime \| None` | Session end | — |

### Entity: AgentMessage (`models/agent_session.py`)

Represents a single message in an agent conversation.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `id` | `str` | UUID primary key | — |
| `session_id` | `str` | FK to AgentSession | — |
| `agent_name` | `str` | Agent identifier (MarketAnalyst, RiskManager, Trader, Manager) | — |
| `role` | `Literal["system", "assistant", "function"]` | Message role | — |
| `content` | `str` | Message content | — |
| `tool_calls` | `list[dict] \| None` | Tool call details (JSON) | — |
| `token_count` | `int` | Tokens in this message | `ge=0` |
| `turn_number` | `int` | Conversation turn number | `ge=0` |
| `created_at` | `datetime` | Message timestamp | — |

### Entity: SimulationConfig (`models/simulation.py`)

Configuration for a trading simulation run.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `id` | `str` | UUID primary key | — |
| `portfolio_id` | `str` | FK to Portfolio | — |
| `strategy_text` | `str` | Natural language trading strategy | `min_length=1, max_length=2000` |
| `watchlist` | `list[str]` | Symbols to monitor | `min_length=1` |
| `speed_multiplier` | `float` | Simulation speed (1.0 = real-time, 10.0 = 10x) | `ge=1.0, le=100.0` |
| `max_position_pct` | `float` | Max portfolio % per position | `gt=0, le=100` |
| `daily_loss_limit_pct` | `float` | Max daily loss before stopping | `gt=0, le=100` |
| `status` | `Literal["idle", "running", "paused", "stopped"]` | Simulation state | — |
| `simulated_time` | `datetime` | Current simulated market time | — |
| `created_at` | `datetime` | Creation timestamp | — |
| `updated_at` | `datetime` | Last state change | — |

**State transitions**:
```
idle → running    (POST /api/simulation/start)
running → paused  (POST /api/simulation/stop with pause=true)
running → stopped (POST /api/simulation/stop)
paused → running  (POST /api/simulation/start — resume)
stopped → idle    (POST /api/simulation/reset)
any → idle        (POST /api/simulation/reset)
```

## SQLite Schema

### Migration 050: Portfolios

```sql
CREATE TABLE IF NOT EXISTS portfolios (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    initial_cash REAL NOT NULL DEFAULT 100000.0,
    cash_balance REAL NOT NULL DEFAULT 100000.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### Migration 051: Holdings

```sql
CREATE TABLE IF NOT EXISTS holdings (
    id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    avg_cost_basis REAL NOT NULL CHECK (avg_cost_basis > 0),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(portfolio_id, symbol)
);

CREATE INDEX IF NOT EXISTS idx_holdings_portfolio ON holdings(portfolio_id);
```

### Migration 052: Orders

```sql
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    order_type TEXT NOT NULL CHECK (order_type IN ('market', 'limit')),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    limit_price REAL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'filled', 'cancelled', 'rejected')),
    reject_reason TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    filled_at TEXT,
    agent_session_id TEXT REFERENCES agent_sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_orders_portfolio ON orders(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
```

### Migration 053: Trades

```sql
CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(id),
    portfolio_id TEXT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price REAL NOT NULL CHECK (price > 0),
    slippage REAL NOT NULL DEFAULT 0.0,
    total_cost REAL NOT NULL,
    realized_pnl REAL,
    executed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_trades_portfolio ON trades(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_executed ON trades(executed_at);
```

### Migration 054: Agent Sessions & Messages

```sql
CREATE TABLE IF NOT EXISTS agent_sessions (
    id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    simulation_id TEXT,
    symbol TEXT NOT NULL,
    strategy_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
    outcome TEXT CHECK (outcome IN ('buy', 'sell', 'hold')),
    total_tokens INTEGER NOT NULL DEFAULT 0,
    estimated_cost_usd REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_sessions_portfolio ON agent_sessions(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_simulation ON agent_sessions(simulation_id);

CREATE TABLE IF NOT EXISTS agent_messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('system', 'assistant', 'function')),
    content TEXT NOT NULL,
    tool_calls TEXT,
    token_count INTEGER NOT NULL DEFAULT 0,
    turn_number INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_agent_messages_session ON agent_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_messages_turn ON agent_messages(session_id, turn_number);
```

### Migration 055: Simulations

```sql
CREATE TABLE IF NOT EXISTS simulations (
    id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    strategy_text TEXT NOT NULL,
    watchlist TEXT NOT NULL,
    speed_multiplier REAL NOT NULL DEFAULT 1.0,
    max_position_pct REAL NOT NULL DEFAULT 5.0,
    daily_loss_limit_pct REAL NOT NULL DEFAULT 10.0,
    status TEXT NOT NULL DEFAULT 'idle' CHECK (status IN ('idle', 'running', 'paused', 'stopped')),
    simulated_time TEXT NOT NULL DEFAULT (datetime('now')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_simulations_portfolio ON simulations(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_simulations_status ON simulations(status);
```

## Analytics Computed Fields

These fields are computed on-demand from trade history, not stored in the database.

### Entity: PortfolioAnalytics (`services/analytics/metrics.py`)

| Field | Type | Description | Formula |
|-------|------|-------------|---------|
| `total_return_pct` | `float` | Total portfolio return | `(current_value - initial_cash) / initial_cash × 100` |
| `sharpe_ratio` | `float` | Risk-adjusted return | `(mean_daily_return - risk_free_rate) / std_daily_return × √252` |
| `max_drawdown_pct` | `float` | Maximum peak-to-trough decline | `max((peak - trough) / peak × 100)` for all peaks |
| `win_rate_pct` | `float` | Percentage of profitable trades | `profitable_trades / total_closed_trades × 100` |
| `avg_trade_pnl` | `float` | Average P&L per closed trade | `sum(realized_pnl) / total_closed_trades` |
| `agent_accuracy_pct` | `float` | Agent signal accuracy | `profitable_agent_trades / total_agent_trades × 100` |
| `total_trades` | `int` | Number of executed trades | Count of trades |
| `buy_hold_return_pct` | `float` | Benchmark buy-and-hold return | `(end_price - start_price) / start_price × 100` |
