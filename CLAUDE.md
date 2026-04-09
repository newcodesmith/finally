# FinAlly Project - the Finance Ally

All project documentation is in the `planning` directory.

The key document is PLAN.md included in full below; the market data component has been completed and is summarized in the file `planning/MARKET_DATA_SUMMARY.md` with more details in the `planning/archive` folder. Consult these docs only when required. The remainder of the platform is still to be developed.

@planning/PLAN.md

<!-- GSD:project-start source:PROJECT.md -->
## Project

**FinAlly — AI Trading Workstation**

FinAlly (Finance Ally) is a visually stunning AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot. Built as a capstone project for an agentic AI coding course, demonstrating how orchestrated AI agents can produce a production-quality full-stack application.

**Core Value:** Users can interact with a real-time simulated trading environment through both manual controls and natural language AI commands — the seamless fusion of live market data, portfolio management, and AI assistance in a single polished interface.

### Constraints

- **Single container**: Everything served on port 8000 — no CORS, no service orchestration
- **No external DB**: SQLite only, volume-mounted for persistence
- **Static frontend**: Next.js `output: 'export'` — no SSR, no API routes in Next.js
- **Market orders only**: No order book, no partial fills, no fees
- **No confirmation dialogs**: Trades execute instantly (simulated money, zero stakes)
- **LLM model**: Must use LiteLLM via OpenRouter with Cerebras inference provider
- **Environment-driven**: Simulator vs Massive API selected by `MASSIVE_API_KEY` env var presence
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- TypeScript — Frontend (Next.js project, not currently deployed)
- Python 3.12+ — Backend (FastAPI, active)
- JavaScript/JSX — Frontend build artifacts
## Runtime
- Python 3.12 (backend runtime, specified in `pyproject.toml`)
- Node 20 (frontend build only, not runtime; static export served by FastAPI)
- `uv` (Python) — Version managed via project, replacements for pip/pipenv. Lockfile: `uv.lock` (present at `backend/uv.lock`)
- `npm` (Node) — Used during Docker build stage, not runtime
## Frameworks
- FastAPI 0.115.0+ — REST API server, SSE streaming, static file serving (Python)
- Uvicorn [standard] 0.32.0+ — ASGI server runtime for FastAPI
- Next.js — Frontend framework (TypeScript, static export mode), not currently active in deployment
- asyncio (Python stdlib) — Built-in async runtime for FastAPI and background tasks
- aiosqlite 0.20.0+ — Async SQLite client for non-blocking database operations
- pytest 8.3.0+ — Python unit test framework (dev dependency, `backend/tests/`)
- pytest-asyncio 0.24.0+ — Async test support for pytest
- pytest-cov 5.0.0+ — Coverage reporting
- ruff 0.7.0+ — Python linter/formatter (dev dependency)
## Key Dependencies
- `fastapi` 0.115.0+ — Request handling, OpenAPI schema generation
- `aiosqlite` 0.20.0+ — Async database access (no thread pool needed)
- `litellm` 1.0.0+ — LLM client abstraction layer (handles OpenRouter API calls with structured outputs)
- `massive` 1.0.0+ — Polygon.io REST client for real market data (optional via MASSIVE_API_KEY)
- `numpy` 2.0.0+ — Numerical computing; used in GBM simulator for correlated random number generation (`app/market/simulator.py`)
- `rich` 13.0.0+ — Terminal formatting (logging, demo CLI tool)
- `httpx` 0.27.0+ — HTTP client (via LiteLLM dependency chain for API calls)
- `python-dotenv` 1.0.0+ — Environment variable loading from `.env` files
## Configuration
- `.env` file at project root (gitignored, not committed)
- Loaded by backend on startup via `python-dotenv` at `backend/app/main.py:14`
- Backend looks for `.env` one level above `backend/` directory
- See "Environment Configuration" section below
- `backend/pyproject.toml` — Python project metadata, dependencies, test config, linter/formatter settings
- `backend/uv.lock` — Reproducible lockfile for all Python dependencies
- Frontend project presumed to have `package.json` (not currently deployed; empty `frontend/` directory)
- `backend/app/db/schema.py` — SQLite schema definition (created lazily on first run)
## Platform Requirements
- Python 3.12+
- Node 20+ (for frontend builds, though not currently used)
- Docker (for containerized deployment)
- SQLite 3 (bundled with Python)
- Docker runtime (single image serves both frontend and backend)
- Port 8000 (HTTP)
- SQLite database file with write access to volume mount (`/app/db/finally.db`)
- Network access to OpenRouter API for LLM calls
- Optional: Network access to Massive/Polygon.io API for real market data
## Environment Configuration
- `OPENROUTER_API_KEY` — API key for LLM inference via OpenRouter (used in `app/api/chat.py:29`)
- `JWT_SECRET` — (present in current .env, purpose/usage not yet documented in code)
- `MASSIVE_API_KEY` — Polygon.io API key; if empty or unset, market simulator is used instead (`app/market/factory.py`)
- `MARKET_POLL_INTERVAL_SECONDS` — Polling interval for Massive API (default: 15 seconds)
- `LLM_MOCK` — Set to "true" for deterministic mock LLM responses (testing mode)
- `DB_PATH` — SQLite database file location (default: `./db/finally.db`, set in `app/db/connection.py:10`)
- `.env` file at repository root (gitignored)
- Docker: passed via `--env-file .env` at runtime
- No separate secrets manager configured; all secrets in single .env file
## Build Pipeline
- Single Docker image with both frontend and backend
- Frontend served as static files from `static/` directory
- Backend runs FastAPI on port 8000
- `backend/uv.lock` — Committed, ensures reproducible builds
- Frontend `package-lock.json` — Not currently used (frontend not deployed)
## Project Dependencies Summary
| Dependency | Version | Purpose | Category |
|---|---|---|---|
| fastapi | ≥0.115.0 | API framework | Core |
| uvicorn[standard] | ≥0.32.0 | ASGI server | Core |
| numpy | ≥2.0.0 | Numerical computing for GBM | Market Data |
| massive | ≥1.0.0 | Polygon.io REST client | Market Data (optional) |
| aiosqlite | ≥0.20.0 | Async SQLite client | Database |
| litellm | ≥1.0.0 | LLM client abstraction | LLM Integration |
| httpx | ≥0.27.0 | HTTP client | Networking |
| rich | ≥13.0.0 | Terminal formatting | Utilities |
| python-dotenv | ≥1.0.0 | .env file loading | Configuration |
| pytest | ≥8.3.0 | Unit testing | Dev |
| pytest-asyncio | ≥0.24.0 | Async test support | Dev |
| pytest-cov | ≥5.0.0 | Coverage reporting | Dev |
| ruff | ≥0.7.0 | Linting/formatting | Dev |
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Lowercase with underscores: `cache.py`, `seed_prices.py`, `test_models.py`
- API route files grouped by feature: `api/chat.py`, `api/watchlist.py`, `api/portfolio.py`
- Test files mirror source structure: `tests/market/test_simulator.py` mirrors `app/market/simulator.py`
- Snake case: `get_watchlist_tickers()`, `execute_trade()`, `_generate_events()`
- Private/internal functions prefixed with single underscore: `_snapshot_callback()`, `_iso_now()`, `_now()`
- Async functions named with verb: `start()`, `stop()`, `add_ticker()`, `remove_ticker()`
- Snake case: `price_cache`, `market_source`, `cash_balance`
- Constants in UPPER_SNAKE_CASE: `DEFAULT_DT`, `TRADING_SECONDS_PER_YEAR`, `DEFAULT_WATCHLIST`
- Dictionary keys in camelCase or lowercase depending on JSON context: `{"ticker": "AAPL", "price": 190.50}`
- Classes in PascalCase: `PriceUpdate`, `PriceCache`, `MarketDataSource`, `SimulatorDataSource`, `TradeRequest`, `LLMResponse`
- Type hints use `|` union syntax (Python 3.10+): `ticker: str | None`, `dict[str, float]`
## Code Style
- Line length: 100 characters (see `tool.ruff` in `pyproject.toml`)
- Ruff handles formatting and linting
- No explicit formatter config (Ruff is all-in-one for Python)
- Ruff configured with rules: `E` (pycodestyle errors), `F` (Pyflakes), `I` (isort imports), `N` (pep8 naming), `W` (warnings)
- Line length violations (`E501`) ignored per config
- Run via: `uv run --extra dev ruff check app/ tests/`
- Module-level docstring at top of each file: `"""Market data API modules."""`
- Class docstrings describe purpose and key state: See `PriceCache` in `app/market/cache.py` (lines 10-15)
- Method docstrings document inputs, behavior, and return value: See `cache.update()` (lines 23-46)
- Inline comments explain non-obvious logic, e.g., Cholesky decomposition reasoning in `simulator.py` (lines 29-44)
## Import Organization
- No path aliases configured; all imports are explicit relative or absolute
- Example: `from ..db import get_cash_balance` (relative from `app/api/portfolio.py` to `app/db`)
- `app/db/__init__.py` exports main functions: `get_db`, `init_db`, `get_watchlist_tickers`, etc.
- `app/market/__init__.py` exports key types and factory: `PriceCache`, `PriceUpdate`, `MarketDataSource`, `create_market_data_source`, `create_stream_router`
- Reduces verbosity: `from app.db import get_positions` instead of `from app.db.queries import get_positions`
## Error Handling
- HTTP errors via `HTTPException` from FastAPI with explicit status codes and detail messages
- Database errors (constraint violations) caught with broad `except Exception` and logged
- Async task failures logged without raising (crash-resistant):
- Fallback responses for LLM failures (graceful degradation):
## Logging
- Module-level logger: `logger = logging.getLogger(__name__)`
- Use logger throughout module for info/warning/exception calls
- Log important lifecycle events (startup, shutdown, ticker changes):
- Configured in `app/main.py` with:
## Comments
- Explain WHY, not WHAT. If code is self-documenting, skip the comment.
- Complex algorithms: see GBM explanation in `app/market/simulator.py` (lines 29-44)
- Non-obvious design decisions: see `cache.py` comments on Cholesky (line 65), session open immutability (lines 43-46)
- Data format details: SSE event structure documented in `app/market/stream.py`
- Sparse; used only for tricky math or state transitions
- Example: `# Set session open price on first update; never overwrite it` in `cache.py` line 43
- Required at top of every file
- Brief, one-sentence or short paragraph describing the module's purpose
- Examples: `"""Thread-safe in-memory price cache."""`, `"""Database schema creation and seed data."""`
## Function Design
- Keep functions focused: single responsibility
- Examples: `update()` in `PriceCache` handles one price update, `execute_trade()` handles one trade with clear return dict structure
- Async methods are allowed to be longer to avoid callback nesting; see `execute_trade()` in `queries.py` (~60 lines)
- Positional for required args: `def update(self, ticker: str, price: float)`
- Optional args via default or keyword: `session_open_price: float | None = None`
- Pass Request object to access shared state in FastAPI routes: `async def get_portfolio(request: Request)`
- Use Pydantic models for request bodies: `async def trade(body: TradeRequest, request: Request)`
- Functions return dicts with explicit keys for complex results:
- Single values when simple: `return bool`, `return float`, `return list[dict]`
- Immutable dataclasses for value objects: `PriceUpdate` is frozen with `@dataclass(frozen=True, slots=True)`
## Module Design
- Barrel files (`__init__.py`) collect and re-export public APIs:
- Private functions start with `_` (e.g., `_iso_now()`, `_snapshot_callback()`) and are not exported
- `MarketDataSource` is an ABC (Abstract Base Class) in `app/market/interface.py`
- Two implementations: `SimulatorDataSource` and `MassiveDataSource`
- Factory pattern: `create_market_data_source()` returns one or the other based on env vars
- See `app/market/factory.py` for factory function
- Shared state (price cache, market source) passed via FastAPI `app.state`:
- Avoids globals; makes testing easier
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Single origin server: FastAPI handles both API routes and static frontend serving
- Pluggable market data abstraction: simulator by default, Massive API on config
- Shared in-memory price cache driving SSE streaming and portfolio valuation
- Async/await throughout: SQLite via `aiosqlite`, background tasks as coroutines
- Lazy database initialization: schema + seed data created on first request if missing
- State injected into FastAPI app.state for handler access, not global singletons
## Layers
- Location: `backend/app/api/*.py` (health, watchlist, portfolio, chat)
- Purpose: HTTP endpoints exposing business logic as REST resources
- Contains: Pydantic request/response models, route handlers, request validation
- Depends on: Database queries, market data cache, LLM integration
- Used by: Frontend client (static export served from root), CLI tools, E2E tests
- Location: `backend/app/market/*.py`
- Purpose: Abstract interface for price updates; implementations (simulator, Massive API) push to shared cache
- Contains: `MarketDataSource` ABC, `SimulatorDataSource`, `MassiveDataSource`, `PriceCache`, `PriceUpdate` models, SSE endpoint factory
- Depends on: NumPy (simulator GBM), httpx (Massive API client), aiosqlite (seed data from DB)
- Used by: Main app startup (lifespan handler), API routes (price lookups), SSE streaming
- Location: `backend/app/db/*.py` (schema, connection, queries)
- Purpose: SQLite persistence — single file at `./db/finally.db`, initialized lazily
- Contains: Schema SQL, async query functions, connection management, transaction logic
- Depends on: aiosqlite, Python stdlib (uuid, datetime)
- Used by: All API endpoints, chat history, portfolio snapshots
- LLM via LiteLLM → OpenRouter (Cerebras inference)
- Location: `backend/app/api/chat.py`
- Purpose: Structured chat with auto-execution of trades and watchlist changes
- Context: Portfolio state, chat history (last 20 messages), live prices from cache
## Data Flow
## Key Abstractions
- Purpose: Contract for price producers (simulator or real API)
- Examples: `SimulatorDataSource` (`backend/app/market/simulator.py`), `MassiveDataSource` (`backend/app/market/massive_client.py`)
- Pattern: Abstract base class with `start()`, `stop()`, `add_ticker()`, `remove_ticker()`, `get_tickers()`
- Implementation: Both push to shared `PriceCache` on their own schedule; FastAPI doesn't know or care which is active
- Purpose: Thread-safe in-memory store of latest prices and session open prices
- Examples: `backend/app/market/cache.py`
- Pattern: Mutable dict-based cache with lock; increments version on every update for SSE change detection
- Access: Read-only from API handlers and SSE endpoint; write-only from market data source
- Purpose: Immutable snapshot of a ticker's price at a moment
- Examples: `backend/app/market/models.py`
- Pattern: Frozen dataclass with computed properties (`change`, `change_percent`, `direction`, `to_dict()`)
- Use: Returned from cache, serialized to JSON for SSE + `/api/watchlist`
- Purpose: Atomic trade logic with cash/share validation
- Examples: `backend/app/db/queries.py::execute_trade()`
- Pattern: Single async function, transactional (all-or-nothing), updates positions + cash_balance + trades log
- Invariants: Can never overdraw cash; can never sell more shares than owned; positions delete when qty reaches 0
## Entry Points
- Location: `backend/app/main.py`
- Triggers: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Responsibilities:
- Location: `backend/app/api/watchlist.py`
- GET `/api/watchlist` — return tickers with current prices from cache
- POST `/api/watchlist` — add ticker (validates, updates DB, syncs with market source)
- DELETE `/api/watchlist/{ticker}` — remove ticker (updates DB, removes from cache, syncs with market source)
- Location: `backend/app/api/portfolio.py`
- GET `/api/portfolio` — return cash, positions with P&L, total value
- POST `/api/portfolio/trade` — execute market order (validates, updates DB, records snapshot)
- GET `/api/portfolio/history` — return portfolio snapshots for P&L chart
- Location: `backend/app/api/chat.py`
- POST `/api/chat` — process message, call LLM, auto-execute trades/watchlist changes, return response
- Location: `backend/app/market/stream.py` (factory), `backend/app/api/` (route registration)
- GET `/api/stream/prices` — SSE endpoint, yields price updates on version change
- Location: `backend/app/api/health.py`
- GET `/api/health` — simple status check for container orchestration
## Error Handling
- **Trade validation errors:** Return HTTP 200 with `{success: false, error: "reason"}` to let user retry
- **LLM failures:** Catch exception, return fallback message `"Sorry, I'm having trouble connecting..."`, never raise 500
- **Missing prices:** Use avg_cost as fallback for P&L calculation; return error only if price never arrives
- **Market data source errors:** Log exception, continue running, next tick may succeed
- **Database connection errors:** Raised as exceptions in route handlers (500 responses) — intentional, indicates infrastructure failure
## Cross-Cutting Concerns
- Tickers: Uppercase, non-empty string; validated before DB write
- Quantities: Positive floats (fractional shares allowed)
- Trade side: Must be "buy" or "sell" (case-insensitive)
- Messages: Pydantic models enforce required fields
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

| Skill | Description | Path |
|-------|-------------|------|
| cerebras-inference | Use this to write code to call an LLM using LiteLLM and OpenRouter with the Cerebras inference provider | `.claude/skills/cerebras/SKILL.md` |
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
