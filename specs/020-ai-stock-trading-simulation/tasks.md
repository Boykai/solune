# Tasks: AI Stock Trading Simulation App

**Input**: Design documents from `/specs/020-ai-stock-trading-simulation/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Step 9 of the parent issue (#1116) explicitly mandates tests — pytest for backend (trade engine, market service, agent tool calls, analytics, simulation) and vitest for frontend (TradingDashboard, StrategyConfig, Analytics, useSimulation hook, price formatting). Test tasks are included in Phase 10 (Polish).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `solune/backend/src/`, `solune/frontend/src/`
- Backend: FastAPI + aiosqlite (Python ≥3.12)
- Frontend: React 19 + Tailwind v4 + Vite (TypeScript 6.0)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization — database migrations, dependencies, service directory scaffolding, and router registration

- [ ] T001 Create database migration files for trading simulation tables in solune/backend/src/migrations/050_portfolios.sql through 055_simulations.sql per data-model.md SQLite schema
- [ ] T002 Add `pyautogen>=0.2.35,<0.3` dependency to solune/backend/pyproject.toml under [project.dependencies]
- [ ] T003 [P] Add `recharts` dependency to solune/frontend via `npm install recharts` in solune/frontend/
- [ ] T004 [P] Create `__init__.py` files for new service directories: solune/backend/src/services/market/__init__.py, solune/backend/src/services/trading/__init__.py, solune/backend/src/services/ai/__init__.py, solune/backend/src/services/agents/__init__.py, solune/backend/src/services/simulation/__init__.py, solune/backend/src/services/analytics/__init__.py
- [ ] T005 Register new API routers (market, trading, agents_trading, simulation, analytics) in solune/backend/src/main.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models, abstract providers, and shared infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 [P] Create market data Pydantic models (Quote, OHLCV, MarketTick) in solune/backend/src/models/market.py per data-model.md entity definitions
- [ ] T007 [P] Create trading Pydantic models (Portfolio, Holding, Order, Trade, CreatePortfolioRequest, SubmitOrderRequest) in solune/backend/src/models/trading.py per data-model.md and trading-api.yaml schemas
- [ ] T008 [P] Create agent session Pydantic models (AgentSession, AgentMessage, AgentSessionSummary, AgentSessionDetail, RunAgentRequest) in solune/backend/src/models/agent_session.py per data-model.md and agents-api.yaml schemas
- [ ] T009 [P] Create simulation Pydantic models (SimulationConfig, SimulationState, StartSimulationRequest, StopSimulationRequest, ResetSimulationRequest) in solune/backend/src/models/simulation.py per data-model.md and simulation-api.yaml schemas
- [ ] T010 Implement abstract market data provider base class (get_quote, get_history, get_symbols) in solune/backend/src/services/market/data_provider.py
- [ ] T011 Implement synthetic data provider using Geometric Brownian Motion in solune/backend/src/services/market/synthetic_provider.py per research.md R1 (preset params for AAPL, MSFT, GOOGL, TSLA, AMZN; seed per symbol for reproducibility)
- [ ] T012 [P] Implement Azure OpenAI client wrapper with streaming, token tracking, and cost estimation in solune/backend/src/services/ai/azure_openai.py per research.md R4 (env vars: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT_NAME; graceful degradation when unavailable)
- [ ] T013 Implement market REST API endpoints (GET /api/market/quote/{symbol}, GET /api/market/history/{symbol}, GET /api/market/symbols) in solune/backend/src/api/market.py per market-api.yaml contract

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Run an AI-Driven Trading Simulation (Priority: P1) 🎯 MVP

**Goal**: Users can create a virtual portfolio, trigger a multi-agent AI trading session for a stock symbol, and see agents collaborate to produce buy/sell/hold decisions with trades executed against the portfolio.

**Independent Test**: Create a portfolio with $100,000 virtual cash → trigger `POST /api/agents/run` for AAPL → verify agents produce a conversation log with a final decision → verify portfolio reflects any executed trades (cash updated, holdings changed, trade recorded).

### Implementation for User Story 1

- [ ] T014 [US1] Implement portfolio manager (create_portfolio, get_portfolio, list_portfolios, update_cash_balance) in solune/backend/src/services/trading/portfolio_manager.py
- [ ] T015 [P] [US1] Implement position sizer with risk parameter checks (max position percentage) in solune/backend/src/services/trading/position_sizer.py
- [ ] T016 [US1] Implement order executor with slippage model (market orders: 0.01–0.1% slippage; limit orders: fill at limit price) in solune/backend/src/services/trading/order_executor.py per research.md R7
- [ ] T017 [US1] Implement FIFO P&L calculator for sell trades in solune/backend/src/services/trading/pnl_calculator.py per research.md R7
- [ ] T018 [US1] Implement trading REST API endpoints (POST /api/portfolio, GET /api/portfolio/{id}, POST /api/orders, GET /api/orders, GET /api/trades) in solune/backend/src/api/trading.py per trading-api.yaml contract
- [ ] T019 [P] [US1] Implement MarketAnalystAgent (system prompt, tool functions: get_quote, get_history) in solune/backend/src/services/agents/market_analyst.py per plan.md Phase 5
- [ ] T020 [P] [US1] Implement RiskManagerAgent (system prompt, tool functions: check_position_size, check_portfolio_exposure) in solune/backend/src/services/agents/risk_manager.py per plan.md Phase 5
- [ ] T021 [P] [US1] Implement TraderAgent (system prompt, tool functions: submit_order, get_portfolio) in solune/backend/src/services/agents/trader.py per plan.md Phase 5
- [ ] T022 [US1] Implement GroupChat orchestrator (GroupChat + GroupChatManager with Azure OpenAI backbone, configurable max_turns, termination conditions) in solune/backend/src/services/agents/orchestrator.py per research.md R3
- [ ] T023 [US1] Implement session manager (persist conversation to SQLite, stream messages via WebSocket /ws/agents/{session_id}) in solune/backend/src/services/agents/session_manager.py
- [ ] T024 [US1] Implement agents REST API (POST /api/agents/run → 202, GET /api/agents/sessions/{id}) and WebSocket endpoint (/ws/agents/{session_id}) in solune/backend/src/api/agents_trading.py per agents-api.yaml contract

**Checkpoint**: User Story 1 complete — can create portfolio, run AI agent trading session, and see trades executed. Full agent conversation log persisted in SQLite.

---

## Phase 4: User Story 2 — View Real-Time Trading Dashboard (Priority: P2)

**Goal**: Users see a live dashboard with real-time stock prices via WebSocket, portfolio summary with P&L, agent activity feed showing reasoning in real time, trade history table, and symbol search.

**Independent Test**: Load dashboard page → verify price cards update automatically via WebSocket → verify portfolio summary shows correct values → verify agent messages stream in during an active session → verify trade history table displays all executed trades.

### Implementation for User Story 2

- [ ] T025 [US2] Implement market WebSocket feed (tick stream at configurable interval, initial snapshot, heartbeat) in solune/backend/src/services/market/websocket_feed.py per websocket-events.yaml MarketTick/MarketSnapshot/Heartbeat schemas
- [ ] T026 [US2] Create trading API service (REST client functions: getQuote, getHistory, getSymbols, createPortfolio, getPortfolio, submitOrder, listOrders, listTrades, runAgentSession, getAgentSession) in solune/frontend/src/services/tradingApi.ts
- [ ] T027 [P] [US2] Create useMarketFeed custom hook (WebSocket connection to /ws/market, reconnection logic, price state management) in solune/frontend/src/hooks/useMarketFeed.ts
- [ ] T028 [P] [US2] Create useTradingSession custom hook (WebSocket connection to /ws/agents/{session_id}, message state, session lifecycle) in solune/frontend/src/hooks/useTradingSession.ts
- [ ] T029 [P] [US2] Create PriceCard component (symbol, price, change %, volume, positive/negative coloring) in solune/frontend/src/components/trading/PriceCard.tsx
- [ ] T030 [US2] Create MarketOverview component (grid of PriceCards for watchlist symbols, real-time updates) in solune/frontend/src/components/trading/MarketOverview.tsx
- [ ] T031 [P] [US2] Create PnLChart component (P&L line chart using recharts with positive/negative coloring, ResponsiveContainer) in solune/frontend/src/components/trading/PnLChart.tsx
- [ ] T032 [US2] Create PortfolioSummary component (cash balance, total value, P&L, PnLChart integration) in solune/frontend/src/components/trading/PortfolioSummary.tsx
- [ ] T033 [US2] Create AgentActivityFeed component (live stream of agent reasoning, agent name badges, tool call display) in solune/frontend/src/components/trading/AgentActivityFeed.tsx
- [ ] T034 [US2] Create TradeHistory component (paginated table with symbol, side, quantity, price, timestamp, P&L columns) in solune/frontend/src/components/trading/TradeHistory.tsx
- [ ] T035 [US2] Create SymbolSearch component (search input, add/remove symbols from watchlist) in solune/frontend/src/components/trading/SymbolSearch.tsx
- [ ] T036 [US2] Create TradingDashboard page (grid layout composing MarketOverview, PortfolioSummary, AgentActivityFeed, TradeHistory, SymbolSearch) in solune/frontend/src/pages/TradingDashboard.tsx

**Checkpoint**: User Story 2 complete — live dashboard with real-time prices, portfolio summary, agent feed, trade history, and symbol search all functional.

---

## Phase 5: User Story 3 — Configure Trading Strategy in Natural Language (Priority: P3)

**Goal**: Users can describe their trading strategy in plain English and have AI agents follow it. Strategy text is sanitized before reaching agents and used as system context for the MarketAnalystAgent.

**Independent Test**: Enter a natural language strategy (e.g., "Buy tech stocks showing momentum, risk no more than 5% per trade") → start an agent session → verify the MarketAnalystAgent's reasoning references the strategy → verify the RiskManagerAgent enforces the specified risk limits.

### Implementation for User Story 3

- [ ] T037 [US3] Implement strategy text sanitizer (prevent prompt injection, strip dangerous patterns, validate max length 2000 chars) in solune/backend/src/services/agents/strategy_sanitizer.py per FR-023
- [ ] T038 [US3] Integrate strategy_text into MarketAnalystAgent system prompt and RiskManagerAgent risk parameters in solune/backend/src/services/agents/orchestrator.py (update existing orchestrator to accept and apply strategy_text)
- [ ] T039 [US3] Create StrategyInput component (textarea with character counter, validation, active strategy display) in solune/frontend/src/components/trading/StrategyInput.tsx

**Checkpoint**: User Story 3 complete — natural language strategies are sanitized, passed to agents as context, and enforced during trading sessions.

---

## Phase 6: User Story 4 — Control Simulation Execution (Priority: P3)

**Goal**: Users can start, pause, resume, and reset trading simulations with configurable speed (1x, 10x, 100x). The simulation engine advances market time, triggers agent sessions at intervals, and persists state for restart recovery.

**Independent Test**: Start a simulation → verify market data updates and agent sessions trigger at configured intervals → pause → verify no new activity → resume → verify activity resumes → reset → verify portfolio returns to initial state.

### Implementation for User Story 4

- [ ] T040 [US4] Implement simulation engine (asyncio background task, speed multiplier, interval-based agent session triggering, market time advancement) in solune/backend/src/services/simulation/engine.py per research.md R9
- [ ] T041 [US4] Implement simulation state manager (persist state to SQLite, state machine: idle→running→paused→stopped, resume support) in solune/backend/src/services/simulation/state_manager.py per research.md R9
- [ ] T042 [US4] Implement simulation REST API (POST /api/simulation/start, POST /api/simulation/stop, POST /api/simulation/reset, GET /api/simulation/status) in solune/backend/src/api/simulation.py per simulation-api.yaml contract
- [ ] T043 [P] [US4] Create SimulationControls component (start/stop/pause/reset buttons, speed selector dropdown, risk limit inputs) in solune/frontend/src/components/trading/SimulationControls.tsx
- [ ] T044 [P] [US4] Create useSimulation custom hook (simulation state polling, start/stop/reset actions, speed control) in solune/frontend/src/hooks/useSimulation.ts
- [ ] T045 [US4] Create StrategyConfig page (compose StrategyInput + SimulationControls + watchlist selector into configuration panel) in solune/frontend/src/pages/StrategyConfig.tsx

**Checkpoint**: User Story 4 complete — simulations can be started, paused, resumed, reset at configurable speeds with state persisted across restarts.

---

## Phase 7: User Story 5 — Analyze Trading Performance (Priority: P4)

**Goal**: Users can view portfolio performance analytics (total return, Sharpe ratio, max drawdown, win rate, average P&L, agent accuracy) with a buy-and-hold benchmark comparison and CSV trade log export.

**Independent Test**: Run a simulation with ≥10 trades → navigate to analytics page → verify all metrics are computed and displayed → verify charts render correctly → download CSV → verify CSV contains correct trade data → verify benchmark comparison shows buy-and-hold return.

### Implementation for User Story 5

- [ ] T046 [US5] Implement analytics metrics service (total_return_pct, sharpe_ratio, max_drawdown_pct, win_rate_pct, avg_trade_pnl, agent_accuracy_pct) in solune/backend/src/services/analytics/metrics.py per research.md R8 and data-model.md PortfolioAnalytics
- [ ] T047 [P] [US5] Implement buy-and-hold benchmark comparison in solune/backend/src/services/analytics/benchmark.py
- [ ] T048 [US5] Implement analytics REST API (GET /api/analytics/summary/{portfolio_id}, GET /api/analytics/export/{portfolio_id} CSV download, GET /api/analytics/daily-returns/{portfolio_id}) in solune/backend/src/api/analytics.py per analytics-api.yaml contract
- [ ] T049 [US5] Create Analytics page (metric cards, P&L chart, benchmark comparison chart, CSV export button, empty state handling) in solune/frontend/src/pages/Analytics.tsx

**Checkpoint**: User Story 5 complete — all analytics metrics computed, charts render on empty/small datasets, CSV export works, benchmark comparison displayed.

---

## Phase 8: User Story 6 — Operate Fully Offline with Synthetic Data (Priority: P4)

**Goal**: The application works fully offline using synthetic stock price data. When external data sources are unavailable, the system falls back to synthetic data automatically and indicates the data source to the user.

**Independent Test**: Disable network access → start the application → verify synthetic prices are generated → run a full simulation → verify all features (portfolio, agents, analytics) function identically → verify data source indicator shows "synthetic".

### Implementation for User Story 6

- [ ] T050 [US6] Implement Yahoo Finance provider with graceful fallback to synthetic on import error or network failure in solune/backend/src/services/market/yahoo_provider.py per research.md R2 (yfinance as optional dependency, MARKET_DATA_PROVIDER env var)
- [ ] T051 [US6] Add data source indicator to PriceCard component and fallback notification to MarketOverview in solune/frontend/src/components/trading/PriceCard.tsx and solune/frontend/src/components/trading/MarketOverview.tsx
- [ ] T052 [US6] Add provider auto-selection logic (synthetic default, yahoo if configured and available) to market service __init__.py in solune/backend/src/services/market/__init__.py

**Checkpoint**: User Story 6 complete — app works fully offline with synthetic data; Yahoo Finance integration available as optional enhancement; data source clearly indicated.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Testing, linting, type checking, security hardening, and production readiness across all user stories

### Backend Tests

- [ ] T053 [P] Write unit tests for synthetic data provider and market service in solune/backend/tests/unit/test_market_service.py (GBM output validation, quote/history endpoint responses, symbol list)
- [ ] T054 [P] Write unit tests for trade engine (portfolio CRUD, order execution, slippage model, FIFO P&L calculation) in solune/backend/tests/unit/test_trade_engine.py
- [ ] T055 [P] Write unit tests for agent tool calls (MarketAnalyst tools, RiskManager tools, Trader tools) in solune/backend/tests/unit/test_agent_tools.py
- [ ] T056 [P] Write unit tests for analytics metrics (total return, Sharpe ratio, max drawdown, win rate, avg P&L, agent accuracy, empty dataset handling) in solune/backend/tests/unit/test_analytics_metrics.py
- [ ] T057 [P] Write unit tests for simulation engine (state machine transitions, speed multiplier, pause/resume, state persistence) in solune/backend/tests/unit/test_simulation_engine.py

### Frontend Tests

- [ ] T058 [P] Write component tests for TradingDashboard (renders all sections, price card updates, trade table data) in solune/frontend/src/pages/TradingDashboard.test.tsx
- [ ] T059 [P] Write component tests for StrategyConfig (strategy input validation, simulation controls, watchlist selection) in solune/frontend/src/pages/StrategyConfig.test.tsx
- [ ] T060 [P] Write component tests for Analytics (metric display, empty state, chart rendering, CSV export trigger) in solune/frontend/src/pages/Analytics.test.tsx

### Linting, Type Checking & Security

- [ ] T061 Run backend lint and format check: `cd solune/backend && uv run ruff check src tests && uv run ruff format --check src tests`
- [ ] T062 Run backend type check: `cd solune/backend && uv run pyright src && uv run pyright -p pyrightconfig.tests.json`
- [ ] T063 Run frontend lint and type check: `cd solune/frontend && npm run lint && npm run type-check`
- [ ] T064 [P] Add rate limiting on agent run endpoint (POST /api/agents/run — max concurrent sessions per portfolio) in solune/backend/src/api/agents_trading.py per FR-024
- [ ] T065 [P] Add simulation disclaimer banner to TradingDashboard, StrategyConfig, and Analytics pages per FR-022
- [ ] T066 Validate all inputs on backend endpoints (symbol patterns, max lengths, numeric ranges) per FR-023

### Production Readiness

- [ ] T067 Verify `docker compose build` completes without errors
- [ ] T068 Run quickstart.md validation (backend health endpoint, frontend loads, migrations applied)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational phase completion — BLOCKS US2 (dashboard needs data), US3 (needs agent framework), US4 (needs simulation target)
- **US2 (Phase 4)**: Depends on US1 (needs trading endpoints and agent sessions to display)
- **US3 (Phase 5)**: Depends on US1 (needs agent framework to accept strategy text); can run in parallel with US2
- **US4 (Phase 6)**: Depends on US1 (needs trading/agent infrastructure); depends on US3 (StrategyConfig page includes StrategyInput)
- **US5 (Phase 7)**: Depends on US1 (needs trade history for metrics); can run backend in parallel with US2-US4
- **US6 (Phase 8)**: Can start after Foundational (Phase 2) — the synthetic provider is already foundational; Yahoo provider and fallback UI can run in parallel with US2+
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)** → Can start after Foundational (Phase 2) — No dependencies on other stories
- **US2 (P2)** → Depends on US1 for backend endpoints; frontend components can start once API contracts are stable
- **US3 (P3)** → Depends on US1 for agent framework; lightweight (3 tasks)
- **US4 (P3)** → Depends on US1 for trading/agent infra; depends on US3 for StrategyInput component
- **US5 (P4)** → Depends on US1 for trade history; backend analytics can start after US1
- **US6 (P4)** → Backend provider can start after Foundational; frontend indicator can start after US2

### Within Each User Story

- Models before services (already in Foundational phase)
- Services before API endpoints
- Backend before frontend (API must exist for frontend to consume)
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Foundational model tasks (T006–T009) can run in parallel (different files)
- Azure OpenAI client (T012) can run in parallel with market provider (T010–T011)
- All three agent definitions (T019–T021) can run in parallel (different files)
- Frontend hooks (T027–T028) can run in parallel (different files)
- Frontend components (T029, T031) can run in parallel (different files)
- All backend test files (T053–T057) can run in parallel (different files)
- All frontend test files (T058–T060) can run in parallel (different files)
- US3 backend (T037–T038) can run in parallel with US2 frontend (T025–T036)
- US5 backend analytics (T046–T048) can start once US1 is complete, in parallel with US2 frontend
- US6 backend (T050, T052) can run in parallel with US2–US4

---

## Parallel Example: User Story 1

```bash
# Launch all models in parallel (Phase 2 — different files, no dependencies):
Task T006: "Create market data Pydantic models in solune/backend/src/models/market.py"
Task T007: "Create trading Pydantic models in solune/backend/src/models/trading.py"
Task T008: "Create agent session Pydantic models in solune/backend/src/models/agent_session.py"
Task T009: "Create simulation Pydantic models in solune/backend/src/models/simulation.py"

# Launch Azure OpenAI client in parallel with market provider:
Task T011: "Implement synthetic data provider in solune/backend/src/services/market/synthetic_provider.py"
Task T012: "Implement Azure OpenAI client wrapper in solune/backend/src/services/ai/azure_openai.py"

# Launch all three agent definitions in parallel (different files):
Task T019: "Implement MarketAnalystAgent in solune/backend/src/services/agents/market_analyst.py"
Task T020: "Implement RiskManagerAgent in solune/backend/src/services/agents/risk_manager.py"
Task T021: "Implement TraderAgent in solune/backend/src/services/agents/trader.py"
```

## Parallel Example: User Story 2

```bash
# Launch WebSocket hooks in parallel (different files):
Task T027: "Create useMarketFeed hook in solune/frontend/src/hooks/useMarketFeed.ts"
Task T028: "Create useTradingSession hook in solune/frontend/src/hooks/useTradingSession.ts"

# Launch independent components in parallel (different files):
Task T029: "Create PriceCard component in solune/frontend/src/components/trading/PriceCard.tsx"
Task T031: "Create PnLChart component in solune/frontend/src/components/trading/PnLChart.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T005)
2. Complete Phase 2: Foundational (T006–T013) — **CRITICAL: blocks all stories**
3. Complete Phase 3: User Story 1 (T014–T024)
4. **STOP and VALIDATE**: Create portfolio → run agent session → verify trades executed
5. Deploy/demo if ready — this is the core simulation loop

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (T014–T024) → Test independently → **Deploy/Demo (MVP!)**
3. Add User Story 2 (T025–T036) → Test independently → Deploy/Demo (live dashboard)
4. Add User Story 3 (T037–T039) → Test independently → Deploy/Demo (NL strategy)
5. Add User Story 4 (T040–T045) → Test independently → Deploy/Demo (simulation controls)
6. Add User Story 5 (T046–T049) → Test independently → Deploy/Demo (analytics)
7. Add User Story 6 (T050–T052) → Test independently → Deploy/Demo (offline mode)
8. Complete Phase 9: Polish (T053–T068) → Production-ready

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (backend trading + agents)
   - Developer B: User Story 1 frontend prep (start API service and hooks once contracts are defined)
3. Once US1 is complete:
   - Developer A: User Story 3 + 4 (strategy + simulation backend)
   - Developer B: User Story 2 (dashboard frontend)
   - Developer C: User Story 5 (analytics backend)
4. Stories complete and integrate independently
5. Team collaborates on Phase 9 (Polish) — each developer writes tests for their stories

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All simulated data is clearly labeled — no real financial data is ever misrepresented (FR-022)
- Strategy text MUST be sanitized before reaching AI agents (FR-023)
- Rate limiting MUST be enforced on agent and simulation endpoints (FR-024)
- The application is single-user — no auth required (Assumptions in spec.md)
- Azure OpenAI endpoint required for agent orchestration; graceful degradation when unavailable
