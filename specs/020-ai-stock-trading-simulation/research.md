# Research: AI Stock Trading Simulation App

**Feature**: 020-ai-stock-trading-simulation | **Date**: 2026-04-08

## R1: Synthetic Market Data Generation — Geometric Brownian Motion

**Context**: The app must work fully offline with realistic stock price data. Real market data APIs (Yahoo Finance, Alpha Vantage) require internet access and have rate limits. A synthetic data generator is needed for the default/fallback mode.

**Decision**: Use Geometric Brownian Motion (GBM) to generate synthetic OHLCV time-series data. GBM models stock prices as: `dS = μS dt + σS dW` where μ is drift (expected return), σ is volatility, and dW is a Wiener process increment. Implement in pure Python using `random` module (no NumPy required for single-path generation).

**Rationale**: GBM is the standard model used in quantitative finance (Black-Scholes foundation). It produces realistic-looking price series with configurable volatility and drift. The simulation can preset parameters per symbol to mimic different stock behaviors (e.g., AAPL: low volatility tech, TSLA: high volatility growth). No external dependencies needed.

**Alternatives considered**:
- **Random walk**: Rejected — produces unrealistic price patterns (no drift, symmetric moves)
- **Historical replay**: Rejected — requires bundling large datasets; not configurable
- **ARIMA/GARCH models**: Rejected — unnecessarily complex for simulation purposes; GBM sufficient
- **NumPy-based generation**: Rejected — adds heavyweight dependency for simple single-path generation; Python `random` module suffices

**Implementation notes**:
- Seed per symbol for reproducible simulations
- Configurable parameters: `initial_price`, `annual_drift`, `annual_volatility`, `trading_days`
- Generate OHLCV from GBM close prices: Open = prev close ± small noise, High/Low = max/min of intraday simulation, Volume = base volume × price change factor

## R2: Yahoo Finance Integration via yfinance

**Context**: For users with internet access, the app should support delayed real market data to make simulations more engaging and educational.

**Decision**: Use `yfinance` library as an optional dependency for fetching delayed Yahoo Finance data. Wrap in a provider that falls back to synthetic data on import error or network failure.

**Rationale**: yfinance is the most popular free Python library for Yahoo Finance data (50M+ downloads). It provides OHLCV history, current quotes, and fundamentals. The library handles rate limiting internally. No API key required.

**Alternatives considered**:
- **Alpha Vantage**: Rejected — requires API key registration; 5 requests/minute on free tier
- **Polygon.io**: Rejected — paid service ($29/month for delayed data)
- **IEX Cloud**: Rejected — paid after free tier exhausted
- **Finnhub**: Rejected — requires API key; rate limited
- **Direct Yahoo Finance scraping**: Rejected — fragile; yfinance handles API changes

**Configuration notes**:
- `yfinance` added as optional dependency: `pip install solune-backend[yahoo]`
- Provider selection via `MARKET_DATA_PROVIDER` env var: `synthetic` (default) or `yahoo`
- Auto-fallback: if yfinance import fails or network request fails, silently fall back to synthetic

## R3: Microsoft AutoGen for Multi-Agent Orchestration

**Context**: The core feature requires three specialized AI agents (MarketAnalyst, RiskManager, Trader) to collaborate in a structured conversation, where each agent has different tools and responsibilities. The issue specifies Microsoft AutoGen.

**Decision**: Use `pyautogen` (AutoGen 0.2.x) with `AssistantAgent` for each specialized agent and `GroupChat` + `GroupChatManager` for orchestration. Each agent gets custom system prompts and tool functions registered via `register_function()`. The GroupChatManager uses Azure OpenAI to decide which agent speaks next.

**Rationale**: AutoGen's GroupChat pattern directly maps to the analyst→risk→trader workflow. The framework handles:
- Turn-taking logic (manager decides next speaker based on conversation context)
- Tool execution (agents can call registered Python functions)
- Conversation history management
- Configurable max turns and termination conditions

**Alternatives considered**:
- **AutoGen 0.4.x (AgentChat)**: Rejected — API is still in preview/breaking changes; 0.2.x is stable and well-documented
- **LangChain agents**: Rejected — more complex setup for multi-agent; agents don't natively converse with each other
- **CrewAI**: Rejected — less mature; fewer production deployments; not Microsoft-backed
- **Semantic Kernel**: Rejected — better for single-agent orchestration; less natural for multi-agent conversation
- **Custom implementation**: Rejected — reinventing conversation management, turn-taking, tool execution

**Integration pattern**:
```
User Request → POST /api/agents/run
  → Create GroupChat(agents=[analyst, risk_manager, trader])
  → GroupChatManager orchestrates conversation (Azure OpenAI)
  → Each turn: agent speaks → message stored → WebSocket broadcast
  → TraderAgent calls trade engine tools when approved
  → Session complete → final summary returned
```

## R4: Azure OpenAI Client Configuration

**Context**: The app uses Azure OpenAI as the LLM backbone for all agent interactions. The existing Solune backend already has `openai` SDK as a dependency.

**Decision**: Create a thin wrapper in `services/ai/azure_openai.py` that configures the `openai.AsyncAzureOpenAI` client with environment variables. Support both streaming and non-streaming completions. Add token usage tracking per session.

**Rationale**: The `openai` SDK (already in pyproject.toml as `openai>=2.26.0,<3`) natively supports Azure OpenAI endpoints via `AsyncAzureOpenAI`. No additional SDK needed. The wrapper centralizes configuration and adds:
- Token counting per request/session
- Cost estimation (configurable per-token pricing)
- Retry logic with exponential backoff
- Graceful degradation when API is unavailable

**Alternatives considered**:
- **azure-ai-inference SDK**: Rejected — already in deps but the `openai` SDK's Azure support is more mature and better documented for AutoGen integration
- **LiteLLM**: Rejected — unnecessary abstraction layer; direct SDK is simpler
- **Raw HTTP requests**: Rejected — reinventing error handling, retries, streaming

**Environment variables**:
- `AZURE_OPENAI_ENDPOINT`: Required. e.g., `https://myinstance.openai.azure.com/`
- `AZURE_OPENAI_API_KEY`: Required. API key for authentication
- `AZURE_OPENAI_DEPLOYMENT_NAME`: Required. e.g., `gpt-4o`
- `AZURE_OPENAI_API_VERSION`: Optional. Default: `2024-12-01-preview`

## R5: Frontend Charting Library — recharts

**Context**: The dashboard needs P&L charts, price history charts, and analytics visualizations. The existing Solune frontend does not include a charting library.

**Decision**: Add `recharts` as a new frontend dependency for all chart components (P&L line chart, portfolio value area chart, analytics bar charts).

**Rationale**: recharts is the most popular React charting library (25K+ GitHub stars). It's built on D3 but provides a declarative React component API. Benefits:
- Pure React components (LineChart, AreaChart, BarChart, etc.)
- Responsive by default with `ResponsiveContainer`
- Lightweight (~150KB gzipped) compared to full D3
- Active maintenance and large community

**Alternatives considered**:
- **D3.js directly**: Rejected — too low-level; requires imperative DOM manipulation incompatible with React patterns
- **Chart.js + react-chartjs-2**: Rejected — canvas-based (not SVG); less React-native API
- **Nivo**: Rejected — heavier bundle size; more opinionated styling
- **TradingView Lightweight Charts**: Rejected — specialized for financial charts but heavy; licensing concerns
- **Victory**: Rejected — less popular; API more complex

## R6: WebSocket Architecture — Dual Streams

**Context**: The app needs two distinct real-time data streams: market price ticks and agent conversation messages. The existing Solune backend uses FastAPI WebSocket (`websocket.py`).

**Decision**: Implement two WebSocket endpoints following the existing Solune pattern:
1. `/ws/market` — broadcasts price tick updates for all watchlist symbols
2. `/ws/agents/{session_id}` — streams agent conversation turns for a specific trading session

**Rationale**: Separate endpoints provide clean separation of concerns. Market data is broadcast to all connected clients; agent messages are scoped to a specific session. This matches the existing `websocket.py` pattern in Solune.

**Alternatives considered**:
- **Single multiplexed WebSocket**: Rejected — mixing market data and agent messages in one stream complicates client-side demuxing; harder to manage subscriptions
- **Server-Sent Events (SSE)**: Rejected — unidirectional; can't support client-to-server simulation control messages
- **Long polling**: Rejected — high latency; wasteful for frequent market updates
- **Socket.io**: Rejected — heavy dependency; WebSocket native to FastAPI is sufficient

## R7: Trade Execution Model — Slippage Simulation

**Context**: The trade engine must simulate realistic order execution. In real markets, orders don't always execute at the quoted price due to slippage, market impact, and bid-ask spreads.

**Decision**: Implement a configurable slippage model:
- **Market orders**: Execute at current price ± random slippage (0.01% to 0.1% of price)
- **Limit orders**: Execute only if market price crosses limit price; fill at limit price
- **Position sizing**: Enforce maximum position size based on risk parameters (e.g., max 5% of portfolio per trade)
- **Cost basis**: FIFO (First In, First Out) for P&L calculation

**Rationale**: A simple slippage model adds realism without overcomplicating the simulation. Users learn that real trading has execution costs. FIFO is the standard accounting method and simplest to implement correctly.

**Alternatives considered**:
- **No slippage**: Rejected — unrealistic; gives false impression of trading performance
- **Market microstructure model**: Rejected — overkill for educational simulation; adds complexity without proportional value
- **LIFO cost basis**: Rejected — less common accounting method; harder to explain
- **Average cost basis**: Rejected — hides individual trade performance; less educational

## R8: Analytics Metrics Implementation

**Context**: The analytics page must compute financial performance metrics from trade history.

**Decision**: Implement the following metrics in `services/analytics/metrics.py`:
1. **Total Return %**: `(final_value - initial_value) / initial_value × 100`
2. **Sharpe Ratio**: `(mean_daily_return - risk_free_rate) / std_daily_return × √252`
3. **Max Drawdown**: Maximum peak-to-trough decline in portfolio value
4. **Win Rate**: Percentage of trades with positive P&L
5. **Average Trade P&L**: Mean P&L across all closed trades
6. **Agent Decision Accuracy**: Percentage of agent signals that resulted in profitable trades

**Rationale**: These are standard portfolio performance metrics used in quantitative finance. The risk-free rate for Sharpe ratio defaults to 0 for simulation purposes (configurable). √252 annualizes daily returns (252 trading days/year).

**Alternatives considered**:
- **Sortino Ratio instead of Sharpe**: Rejected — Sharpe is more widely known; Sortino can be added later
- **Calmar Ratio**: Rejected — less commonly used; can be added later
- **Alpha/Beta vs benchmark**: Rejected — requires benchmark data not always available offline

## R9: Simulation Engine Design

**Context**: Users need to start, stop, pause, and reset trading simulations with configurable speed (real-time, 10x, 100x).

**Decision**: Implement the simulation as an asyncio background task that:
1. Advances synthetic market time at the configured speed multiplier
2. Triggers agent sessions at configurable intervals (e.g., every simulated trading hour)
3. Updates market prices via the synthetic provider
4. Persists state to SQLite so simulations survive backend restarts

**Rationale**: asyncio background tasks are the standard pattern in FastAPI for long-running operations. The simulation loop is lightweight (just advancing time and triggering events). State persistence enables resume after restart.

**Alternatives considered**:
- **Celery task queue**: Rejected — overkill for single-user simulation; adds Redis/RabbitMQ dependency
- **APScheduler**: Rejected — unnecessary dependency; asyncio `create_task` is sufficient
- **Thread-based simulation**: Rejected — mixing threads with asyncio adds complexity; pure async is cleaner

**State machine**:
```
IDLE → [start] → RUNNING → [pause] → PAUSED → [resume] → RUNNING
                     ↓                                        ↓
                  [stop]                                   [stop]
                     ↓                                        ↓
                   IDLE ← ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  IDLE
                     ↑
                  [reset] (clears portfolio and trade history)
```
