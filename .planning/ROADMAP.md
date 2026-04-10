# Roadmap: FinAlly

## Overview

FinAlly is built foundation-up: the market data engine and database form the base, backend APIs for watchlist and portfolio layer on top, AI chat integration connects to those APIs, then the frontend consumes everything through a terminal-inspired UI. Docker and testing wrap the completed application at the end.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation & Market Data Engine** - Database, market simulator, price cache, and SSE streaming
- [ ] **Phase 2: Watchlist & Portfolio APIs** - CRUD endpoints for watchlist and full trade execution pipeline
- [ ] **Phase 3: AI Chat Backend** - LLM integration with structured output, auto-execution, and mock mode
- [x] **Phase 4: Frontend Shell & Live Data** - Layout, theme, watchlist panel with streaming prices, charts (completed 2026-04-09)
- [ ] **Phase 5: Frontend Portfolio & Trading** - Portfolio views, trade bar, and AI chat panel
- [ ] **Phase 6: Infrastructure & Testing** - Docker containerization, scripts, and all test suites

## Phase Details

### Phase 1: Foundation & Market Data Engine
**Goal**: A running FastAPI server with a seeded database and live-streaming simulated market data
**Depends on**: Nothing (first phase)
**Requirements**: DB-01, DB-02, DB-03, MKT-01, MKT-02, MKT-03, MKT-04, MKT-05, MKT-06, MKT-07, INFRA-05, INFRA-06
**Success Criteria** (what must be TRUE):
  1. FastAPI server starts and GET /api/health returns a success response confirming database connectivity
  2. SQLite database is auto-created on first start with all six tables and seed data (default user with $10k, 10 watchlist tickers)
  3. Connecting to GET /api/stream/prices with curl or EventSource receives a continuous stream of SSE price events for all watchlist tickers at ~500ms cadence
  4. Price events include ticker, price, previous_price, session_open_price, timestamp, and change_direction fields with realistic values from the GBM simulator
  5. .env.example exists documenting all environment variables
**Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md — Restore environment, verify tests, create .env.example, upgrade health endpoint
- [x] 01-02-PLAN.md — Integration verification: server startup, DB init, SSE streaming end-to-end

### Phase 2: Watchlist & Portfolio APIs
**Goal**: Users can manage their watchlist and execute trades through REST API endpoints
**Depends on**: Phase 1
**Requirements**: WATCH-01, WATCH-02, WATCH-03, WATCH-04, PORT-01, PORT-02, PORT-03, PORT-04, PORT-05, PORT-06, PORT-07, PORT-08
**Success Criteria** (what must be TRUE):
  1. GET /api/watchlist returns the current watchlist with latest prices from the price cache
  2. POST /api/watchlist adds a ticker and DELETE /api/watchlist/{ticker} removes it, with the price cache updating accordingly
  3. POST /api/portfolio/trade executes a buy or sell at the current market price, updating cash balance and positions atomically
  4. GET /api/portfolio returns current positions with unrealized P&L calculated from live prices
  5. GET /api/portfolio/history returns time-series snapshots, with snapshots being recorded every 30 seconds and after each trade
**Plans:** 2 plans

Plans:
- [x] 02-01-PLAN.md — Verify watchlist API endpoints with integration tests
- [x] 02-02-PLAN.md — Verify portfolio trade execution, P&L, and snapshots with integration tests

### Phase 3: AI Chat Backend
**Goal**: Users can chat with an AI assistant that analyzes their portfolio and executes trades through natural language
**Depends on**: Phase 2
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, CHAT-08, CHAT-09
**Success Criteria** (what must be TRUE):
  1. POST /api/chat accepts a user message and returns a structured JSON response with message text, optional trades array, and optional watchlist_changes array
  2. The LLM receives current portfolio context (cash, positions, watchlist with live prices) and the last 20 chat messages as history
  3. Trades and watchlist changes specified in the LLM response are auto-executed, with results (including any validation errors) reflected in the response
  4. When LLM_MOCK=true, the endpoint returns deterministic mock responses without calling OpenRouter
  5. LLM failures (network errors, malformed responses) return a graceful fallback message with HTTP 200, never a 500
**Plans:** 1/2 plans executed

Plans:
- [x] 03-01-PLAN.md — Integration tests for chat endpoint baseline: structured response, context, history, schema, mock mode
- [x] 03-02-PLAN.md — Integration tests for auto-execution pipeline and LLM error handling

### Phase 4: Frontend Shell & Live Data
**Goal**: Users see a dark, terminal-inspired interface with a live-updating watchlist, sparklines, and a main chart area
**Depends on**: Phase 1
**Requirements**: UI-LAYOUT-01, UI-LAYOUT-02, UI-LAYOUT-03, UI-LAYOUT-04, UI-WATCH-01, UI-WATCH-02, UI-WATCH-03, UI-WATCH-04, UI-CHART-01
**Success Criteria** (what must be TRUE):
  1. The app renders a dark terminal-inspired layout with correct accent colors, header showing portfolio value and cash balance, and connection status indicator
  2. The watchlist panel displays all tickers with current price, session change %, and sparkline mini-charts that fill in progressively from SSE data
  3. Prices flash green on uptick and red on downtick with a ~500ms CSS fade animation
  4. Clicking a ticker in the watchlist displays a larger detailed price chart in the main chart area
**Plans:** 3/3 plans complete

Plans:
- [x] 04-01-PLAN.md — Scaffold Next.js, Tailwind dark theme, layout shell with header and connection dot
- [x] 04-02-PLAN.md — Zustand price store, SSE hook, watchlist panel with flash animations and sparklines
- [x] 04-03-PLAN.md — Main chart area with Lightweight Charts, visual verification checkpoint

### Phase 5: Frontend Portfolio & Trading
**Goal**: Users can trade, view portfolio visualizations, and interact with the AI assistant through the UI
**Depends on**: Phase 3, Phase 4
**Requirements**: UI-HEAT-01, UI-HEAT-02, UI-PNL-01, UI-POS-01, UI-TRADE-01, UI-CHAT-01, UI-CHAT-02, UI-CHAT-03
**Success Criteria** (what must be TRUE):
  1. The trade bar allows entering a ticker and quantity, with buy/sell buttons that execute trades and update the portfolio display
  2. The portfolio heatmap (treemap) renders positions sized by weight and colored by P&L, with a placeholder message when no positions exist
  3. The P&L line chart displays portfolio value over time from snapshot data, and the positions table shows all holdings with unrealized P&L
  4. The AI chat panel is docked/collapsible, shows conversation history with a loading indicator during LLM calls, and displays trade executions and watchlist changes inline
**Plans:** 2 plans

Plans:
- [x] 05-01-PLAN.md — Portfolio store, visualizations (heatmap, P&L chart, positions table), trade bar, and layout wiring
- [x] 05-02-PLAN.md — AI chat panel with conversation history, loading state, and inline action confirmations

### Phase 6: Infrastructure & Testing
**Goal**: The entire application runs from a single Docker container with comprehensive test coverage
**Depends on**: Phase 5
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06
**Success Criteria** (what must be TRUE):
  1. A single docker run command builds and starts the app, serving the frontend and all APIs on port 8000 with SQLite persisted via volume mount
  2. Start/stop scripts for macOS/Linux work idempotently (safe to run multiple times)
  3. Backend pytest suite passes covering market data, portfolio logic, LLM integration, and API routes
  4. Frontend component tests pass for key UI behaviors
  5. E2E Playwright tests pass against the containerized app with LLM_MOCK=true, verifying the core user flows
**Plans:** 3 plans

Plans:
- [x] 06-01-PLAN.md — Multi-stage Dockerfile and start/stop scripts
- [ ] 06-02-PLAN.md — Backend test gap (health endpoint) and frontend Vitest component tests
- [ ] 06-03-PLAN.md — E2E Playwright tests with docker-compose.test.yml

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6
Note: Phase 4 depends on Phase 1 (not Phase 3), so Phases 3 and 4 could theoretically execute in parallel.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Market Data Engine | 2/2 | Complete | - |
| 2. Watchlist & Portfolio APIs | 2/2 | Complete | - |
| 3. AI Chat Backend | 1/2 | In Progress|  |
| 4. Frontend Shell & Live Data | 3/3 | Complete   | 2026-04-09 |
| 5. Frontend Portfolio & Trading | 0/2 | Not started | - |
| 6. Infrastructure & Testing | 0/3 | Not started | - |
