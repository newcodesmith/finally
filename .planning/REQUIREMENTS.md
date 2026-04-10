# Requirements: FinAlly

**Defined:** 2026-04-09
**Core Value:** Users can interact with a real-time simulated trading environment through both manual controls and natural language AI commands

## v1 Requirements

### Market Data

- [ ] **MKT-01**: SSE endpoint streams live price updates for all watchlist tickers at ~500ms cadence
- [ ] **MKT-02**: Market simulator generates prices using geometric Brownian motion with configurable drift/volatility
- [ ] **MKT-03**: Correlated moves across tickers (tech stocks move together)
- [ ] **MKT-04**: Random "event" moves (2-5% sudden changes) for drama
- [ ] **MKT-05**: In-memory price cache stores latest price, previous price, session open price, timestamp per ticker
- [ ] **MKT-06**: Massive API client polls REST API on configurable interval (optional, env-var driven)
- [ ] **MKT-07**: Abstract interface shared by simulator and Massive client

### Watchlist

- [ ] **WATCH-01**: Default watchlist seeded with 10 tickers (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX)
- [ ] **WATCH-02**: User can add a ticker to the watchlist
- [ ] **WATCH-03**: User can remove a ticker from the watchlist
- [ ] **WATCH-04**: GET /api/watchlist returns tickers with latest prices

### Portfolio

- [ ] **PORT-01**: User starts with $10,000 virtual cash
- [ ] **PORT-02**: User can buy shares (market order, instant fill at current price)
- [ ] **PORT-03**: User can sell shares (market order, instant fill)
- [ ] **PORT-04**: Buying a ticker not on watchlist auto-adds it
- [ ] **PORT-05**: GET /api/portfolio returns positions, cash balance, total value, unrealized P&L
- [ ] **PORT-06**: GET /api/portfolio/history returns portfolio value snapshots for P&L chart
- [ ] **PORT-07**: Portfolio snapshots recorded every 30s and immediately after each trade
- [ ] **PORT-08**: Snapshots older than 24h are pruned

### AI Chat

- [x] **CHAT-01**: POST /api/chat accepts user message and returns structured JSON response
- [x] **CHAT-02**: LLM receives portfolio context (cash, positions, watchlist with prices, total value)
- [x] **CHAT-03**: LLM receives last 20 chat messages as conversation history
- [x] **CHAT-04**: Structured output includes message, optional trades array, optional watchlist_changes array
- [x] **CHAT-05**: Trades from LLM auto-execute without confirmation
- [x] **CHAT-06**: Watchlist changes from LLM auto-execute
- [x] **CHAT-07**: Failed trades include error in chat response
- [x] **CHAT-08**: LLM failures return fallback message (never 500)
- [x] **CHAT-09**: LLM mock mode returns deterministic responses when LLM_MOCK=true

### Frontend - Watchlist

- [x] **UI-WATCH-01**: Watchlist panel shows ticker, price, session change %, sparkline per ticker
- [x] **UI-WATCH-02**: Prices flash green (uptick) or red (downtick) with ~500ms CSS fade
- [x] **UI-WATCH-03**: Sparklines accumulate from SSE data since page load
- [x] **UI-WATCH-04**: Clicking a ticker selects it for the main chart

### Frontend - Charts & Portfolio

- [x] **UI-CHART-01**: Main chart area shows larger price chart for selected ticker
- [x] **UI-HEAT-01**: Portfolio heatmap (treemap) with positions sized by weight, colored by P&L
- [x] **UI-HEAT-02**: Empty state shows placeholder message when no positions
- [x] **UI-PNL-01**: P&L line chart shows portfolio value over time from snapshots
- [x] **UI-POS-01**: Positions table shows ticker, quantity, avg cost, current price, unrealized P&L, % change

### Frontend - Trading & Chat

- [x] **UI-TRADE-01**: Trade bar with ticker field, quantity field, buy button, sell button
- [x] **UI-CHAT-01**: Docked/collapsible AI chat panel with message history
- [x] **UI-CHAT-02**: Loading indicator while waiting for LLM response
- [x] **UI-CHAT-03**: Trade executions and watchlist changes shown inline as confirmations

### Frontend - Layout & Design

- [x] **UI-LAYOUT-01**: Dark terminal-inspired theme (backgrounds ~#0d1117 or #1a1a2e)
- [x] **UI-LAYOUT-02**: Header with portfolio total value, connection status indicator, cash balance
- [x] **UI-LAYOUT-03**: Connection status dot (green/yellow/red)
- [x] **UI-LAYOUT-04**: Accent colors: yellow #ecad0a, blue #209dd7, purple #753991

### Database

- [ ] **DB-01**: SQLite database with lazy initialization on first request
- [ ] **DB-02**: Schema: users_profile, watchlist, positions, trades, portfolio_snapshots, chat_messages
- [ ] **DB-03**: Default seed data (user profile with $10k, 10 watchlist tickers)

### Infrastructure

- [x] **INFRA-01**: Multi-stage Dockerfile (Node build → Python runtime)
- [x] **INFRA-02**: FastAPI serves static frontend + API on port 8000
- [x] **INFRA-03**: Docker volume mount for SQLite persistence
- [x] **INFRA-04**: Start/stop scripts for macOS/Linux
- [ ] **INFRA-05**: GET /api/health endpoint
- [ ] **INFRA-06**: .env.example with all environment variables documented

### Testing

- [x] **TEST-01**: Backend pytest tests for market data (simulator, GBM, Massive parsing, interface)
- [x] **TEST-02**: Backend pytest tests for portfolio (trade execution, P&L, edge cases)
- [x] **TEST-03**: Backend pytest tests for LLM (structured output parsing, error handling)
- [x] **TEST-04**: Backend pytest tests for API routes
- [x] **TEST-05**: Frontend component tests
- [x] **TEST-06**: E2E Playwright tests with docker-compose.test.yml and LLM_MOCK=true

## v2 Requirements

### Cloud Deployment

- **DEPLOY-01**: Terraform configuration for AWS App Runner
- **DEPLOY-02**: CI/CD pipeline for automated deployment

### Windows Support

- **WIN-01**: PowerShell start/stop scripts for Windows

## Out of Scope

| Feature | Reason |
|---------|--------|
| User authentication/login | Single-user app, no auth needed |
| Limit orders / order book | Market orders only for simplicity |
| WebSocket real-time | SSE sufficient for one-way push |
| Multi-user concurrent access | Hardcoded "default" user; schema supports future expansion |
| Mobile-first responsive design | Desktop-first; functional on tablet |
| OAuth / social login | No auth at all in v1 |
| Fractional share UI validation | Schema supports it; UI decision deferred |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| MKT-01 | Phase 1 | Pending |
| MKT-02 | Phase 1 | Pending |
| MKT-03 | Phase 1 | Pending |
| MKT-04 | Phase 1 | Pending |
| MKT-05 | Phase 1 | Pending |
| MKT-06 | Phase 1 | Pending |
| MKT-07 | Phase 1 | Pending |
| WATCH-01 | Phase 2 | Pending |
| WATCH-02 | Phase 2 | Pending |
| WATCH-03 | Phase 2 | Pending |
| WATCH-04 | Phase 2 | Pending |
| PORT-01 | Phase 2 | Pending |
| PORT-02 | Phase 2 | Pending |
| PORT-03 | Phase 2 | Pending |
| PORT-04 | Phase 2 | Pending |
| PORT-05 | Phase 2 | Pending |
| PORT-06 | Phase 2 | Pending |
| PORT-07 | Phase 2 | Pending |
| PORT-08 | Phase 2 | Pending |
| CHAT-01 | Phase 3 | Complete |
| CHAT-02 | Phase 3 | Complete |
| CHAT-03 | Phase 3 | Complete |
| CHAT-04 | Phase 3 | Complete |
| CHAT-05 | Phase 3 | Complete |
| CHAT-06 | Phase 3 | Complete |
| CHAT-07 | Phase 3 | Complete |
| CHAT-08 | Phase 3 | Complete |
| CHAT-09 | Phase 3 | Complete |
| UI-WATCH-01 | Phase 4 | Complete |
| UI-WATCH-02 | Phase 4 | Complete |
| UI-WATCH-03 | Phase 4 | Complete |
| UI-WATCH-04 | Phase 4 | Complete |
| UI-CHART-01 | Phase 4 | Complete |
| UI-HEAT-01 | Phase 5 | Complete |
| UI-HEAT-02 | Phase 5 | Complete |
| UI-PNL-01 | Phase 5 | Complete |
| UI-POS-01 | Phase 5 | Complete |
| UI-TRADE-01 | Phase 5 | Complete |
| UI-CHAT-01 | Phase 5 | Complete |
| UI-CHAT-02 | Phase 5 | Complete |
| UI-CHAT-03 | Phase 5 | Complete |
| UI-LAYOUT-01 | Phase 4 | Complete |
| UI-LAYOUT-02 | Phase 4 | Complete |
| UI-LAYOUT-03 | Phase 4 | Complete |
| UI-LAYOUT-04 | Phase 4 | Complete |
| DB-01 | Phase 1 | Pending |
| DB-02 | Phase 1 | Pending |
| DB-03 | Phase 1 | Pending |
| INFRA-01 | Phase 6 | Complete |
| INFRA-02 | Phase 6 | Complete |
| INFRA-03 | Phase 6 | Complete |
| INFRA-04 | Phase 6 | Complete |
| INFRA-05 | Phase 1 | Pending |
| INFRA-06 | Phase 1 | Pending |
| TEST-01 | Phase 6 | Complete |
| TEST-02 | Phase 6 | Complete |
| TEST-03 | Phase 6 | Complete |
| TEST-04 | Phase 6 | Complete |
| TEST-05 | Phase 6 | Complete |
| TEST-06 | Phase 6 | Complete |

**Coverage:**
- v1 requirements: 55 total
- Mapped to phases: 55
- Unmapped: 0

---
*Requirements defined: 2026-04-09*
*Last updated: 2026-04-09 after roadmap creation*
