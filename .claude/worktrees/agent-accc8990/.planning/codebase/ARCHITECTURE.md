# Architecture

**Analysis Date:** 2026-04-09

## Pattern Overview

**Overall:** Layered async backend (FastAPI + SQLite) with pluggable market data sources and real-time SSE streaming

**Key Characteristics:**
- Single origin server: FastAPI handles both API routes and static frontend serving
- Pluggable market data abstraction: simulator by default, Massive API on config
- Shared in-memory price cache driving SSE streaming and portfolio valuation
- Async/await throughout: SQLite via `aiosqlite`, background tasks as coroutines
- Lazy database initialization: schema + seed data created on first request if missing
- State injected into FastAPI app.state for handler access, not global singletons

## Layers

**Presentation Layer:**
- Location: `backend/app/api/*.py` (health, watchlist, portfolio, chat)
- Purpose: HTTP endpoints exposing business logic as REST resources
- Contains: Pydantic request/response models, route handlers, request validation
- Depends on: Database queries, market data cache, LLM integration
- Used by: Frontend client (static export served from root), CLI tools, E2E tests

**Market Data Layer:**
- Location: `backend/app/market/*.py`
- Purpose: Abstract interface for price updates; implementations (simulator, Massive API) push to shared cache
- Contains: `MarketDataSource` ABC, `SimulatorDataSource`, `MassiveDataSource`, `PriceCache`, `PriceUpdate` models, SSE endpoint factory
- Depends on: NumPy (simulator GBM), httpx (Massive API client), aiosqlite (seed data from DB)
- Used by: Main app startup (lifespan handler), API routes (price lookups), SSE streaming

**Data Layer:**
- Location: `backend/app/db/*.py` (schema, connection, queries)
- Purpose: SQLite persistence — single file at `./db/finally.db`, initialized lazily
- Contains: Schema SQL, async query functions, connection management, transaction logic
- Depends on: aiosqlite, Python stdlib (uuid, datetime)
- Used by: All API endpoints, chat history, portfolio snapshots

**Integration Layer:**
- LLM via LiteLLM → OpenRouter (Cerebras inference)
- Location: `backend/app/api/chat.py`
- Purpose: Structured chat with auto-execution of trades and watchlist changes
- Context: Portfolio state, chat history (last 20 messages), live prices from cache

## Data Flow

**Price Update & Streaming (Real-time):**

1. Market data source (`SimulatorDataSource` or `MassiveDataSource`) generates/fetches prices on its cadence (~500ms simulator, ~15s Massive poller)
2. Source calls `price_cache.update(ticker, price, ...)` → returns `PriceUpdate`
3. PriceCache increments internal version counter (monotonic)
4. SSE endpoint (`/api/stream/prices`) polls cache version; on change, serializes all tickers to JSON and yields SSE event
5. Browser EventSource receives all prices every 500ms; frontend accumulates mini-chart data
6. Frontend displays price flash animations on direction changes

**Trade Execution (User → Buy/Sell):**

1. POST `/api/portfolio/trade` receives `{ticker, side, quantity}`
2. If ticker not in watchlist, auto-add via `add_watchlist_ticker()` and `market_source.add_ticker()`
3. Fetch current price from cache: `price_cache.get_price(ticker)`
4. Call `execute_trade()` → validates cash/shares, updates positions table, updates cash_balance, records trade row
5. Record immediate portfolio snapshot with new total value
6. Return execution details to frontend

**Chat with LLM (Stateful):**

1. POST `/api/chat` receives user message
2. Load portfolio context: cash, positions with P&L, watchlist, prices from cache
3. Load last 20 chat messages from DB
4. Build LLM prompt with system message + portfolio context + history + new message
5. Call LiteLLM → OpenRouter with structured output schema → receive `{message, trades[], watchlist_changes[]}`
6. Auto-execute each trade in sequence (validates, updates DB, updates cache)
7. Auto-execute watchlist changes (add/remove tickers, sync with market source)
8. Record post-trade portfolio snapshot if any trades succeeded
9. Save user + assistant messages (with actions) to DB
10. Return final response with executed trades, errors, and watchlist changes

**Portfolio Valuation (On-Demand & Periodic):**

1. GET `/api/portfolio` fetches all positions from DB
2. For each position: `current_price = price_cache.get_price(ticker) or avg_cost`
3. Compute unrealized P&L, % change, position value
4. Sum cash + positions_value → total portfolio value
5. Background task (tied to market data source) records portfolio snapshot every ~30s
6. GET `/api/portfolio/history` returns all snapshots (up to 24h old) for P&L chart

## Key Abstractions

**MarketDataSource:**
- Purpose: Contract for price producers (simulator or real API)
- Examples: `SimulatorDataSource` (`backend/app/market/simulator.py`), `MassiveDataSource` (`backend/app/market/massive_client.py`)
- Pattern: Abstract base class with `start()`, `stop()`, `add_ticker()`, `remove_ticker()`, `get_tickers()`
- Implementation: Both push to shared `PriceCache` on their own schedule; FastAPI doesn't know or care which is active

**PriceCache:**
- Purpose: Thread-safe in-memory store of latest prices and session open prices
- Examples: `backend/app/market/cache.py`
- Pattern: Mutable dict-based cache with lock; increments version on every update for SSE change detection
- Access: Read-only from API handlers and SSE endpoint; write-only from market data source

**PriceUpdate:**
- Purpose: Immutable snapshot of a ticker's price at a moment
- Examples: `backend/app/market/models.py`
- Pattern: Frozen dataclass with computed properties (`change`, `change_percent`, `direction`, `to_dict()`)
- Use: Returned from cache, serialized to JSON for SSE + `/api/watchlist`

**Trade Validation & Execution:**
- Purpose: Atomic trade logic with cash/share validation
- Examples: `backend/app/db/queries.py::execute_trade()`
- Pattern: Single async function, transactional (all-or-nothing), updates positions + cash_balance + trades log
- Invariants: Can never overdraw cash; can never sell more shares than owned; positions delete when qty reaches 0

## Entry Points

**FastAPI App:**
- Location: `backend/app/main.py`
- Triggers: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Responsibilities:
  - Lifespan management: on startup, initialize DB and start market data source; on shutdown, stop source
  - Inject shared state (price_cache, market_source) into FastAPI.app.state
  - Register all route routers (health, watchlist, portfolio, chat, stream)
  - Serve static frontend files from `./static/` directory

**Watchlist API:**
- Location: `backend/app/api/watchlist.py`
- GET `/api/watchlist` — return tickers with current prices from cache
- POST `/api/watchlist` — add ticker (validates, updates DB, syncs with market source)
- DELETE `/api/watchlist/{ticker}` — remove ticker (updates DB, removes from cache, syncs with market source)

**Portfolio API:**
- Location: `backend/app/api/portfolio.py`
- GET `/api/portfolio` — return cash, positions with P&L, total value
- POST `/api/portfolio/trade` — execute market order (validates, updates DB, records snapshot)
- GET `/api/portfolio/history` — return portfolio snapshots for P&L chart

**Chat API:**
- Location: `backend/app/api/chat.py`
- POST `/api/chat` — process message, call LLM, auto-execute trades/watchlist changes, return response

**Streaming API:**
- Location: `backend/app/market/stream.py` (factory), `backend/app/api/` (route registration)
- GET `/api/stream/prices` — SSE endpoint, yields price updates on version change

**Health Check:**
- Location: `backend/app/api/health.py`
- GET `/api/health` — simple status check for container orchestration

## Error Handling

**Strategy:** Fail open for real-time paths (SSE, price lookups), graceful degradation for stateful paths (trades, chat)

**Patterns:**

- **Trade validation errors:** Return HTTP 200 with `{success: false, error: "reason"}` to let user retry
- **LLM failures:** Catch exception, return fallback message `"Sorry, I'm having trouble connecting..."`, never raise 500
- **Missing prices:** Use avg_cost as fallback for P&L calculation; return error only if price never arrives
- **Market data source errors:** Log exception, continue running, next tick may succeed
- **Database connection errors:** Raised as exceptions in route handlers (500 responses) — intentional, indicates infrastructure failure

## Cross-Cutting Concerns

**Logging:** `logging.basicConfig()` in `backend/app/main.py` sets level to INFO; all modules use `logger = logging.getLogger(__name__)` and log at info/warning/error levels. Key events: DB init, market source start/stop, SSE client connect/disconnect, trade execution, LLM calls.

**Validation:**
- Tickers: Uppercase, non-empty string; validated before DB write
- Quantities: Positive floats (fractional shares allowed)
- Trade side: Must be "buy" or "sell" (case-insensitive)
- Messages: Pydantic models enforce required fields

**Authentication:** None. Single hardcoded user `user_id="default"` throughout. Database schema has `user_id` column for future multi-user support.

**Rate Limiting:** None implemented. Massive API respects free tier polling limits via `MARKET_POLL_INTERVAL_SECONDS` env var; simulator has no external rate limits.

---

*Architecture analysis: 2026-04-09*
