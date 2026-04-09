# External Integrations

**Analysis Date:** 2026-04-09

## APIs & External Services

**LLM Inference:**
- OpenRouter (inference provider)
  - What it's used for: Chat-based trading assistant, portfolio analysis, trade suggestions, structured output responses
  - SDK/Client: LiteLLM 1.0.0+ (abstraction layer)
  - Auth: `OPENROUTER_API_KEY` environment variable
  - Implementation: `app/api/chat.py:188` calls `completion()` with model `openrouter/openai/gpt-oss-120b` (Cerebras inference)
  - Model: Cerebras-optimized LLM via OpenRouter (specified in `app/api/chat.py:29-30`)
  - Structured Output: Uses Pydantic `LLMResponse` schema for JSON parsing (`app/api/chat.py:79-82`)

**Market Data (Optional):**
- Massive (Polygon.io REST API)
  - What it's used for: Live stock price data as alternative to built-in simulator
  - SDK/Client: `massive` 1.0.0+ (REST client)
  - Auth: `MASSIVE_API_KEY` environment variable
  - Polling: Configurable via `MARKET_POLL_INTERVAL_SECONDS` (default: 15 seconds)
  - Implementation: `app/market/massive_client.py` implements `MarketDataSource` interface
  - Endpoint: `GET /v2/snapshot/locale/us/markets/stocks/tickers` (snapshot API)
  - Behavior: Used only if `MASSIVE_API_KEY` is set and non-empty; otherwise simulator is used
  - Rate limits: Free tier ~5 req/min (15s polling), paid tiers support faster intervals

## Data Storage

**Databases:**
- SQLite 3
  - Connection: File-based at `./db/finally.db` (path configurable via `DB_PATH` env var)
  - Client: `aiosqlite` 0.20.0+ (async SQLite driver)
  - Mode: Lazy initialization — schema created on first request if missing
  - Configuration: WAL mode enabled (`PRAGMA journal_mode=WAL`) for concurrency
  - Foreign keys: Enabled (`PRAGMA foreign_keys=ON`)
  - Location: `app/db/connection.py:10-19`

**File Storage:**
- Local filesystem only
  - SQLite database file: `/app/db/finally.db` in container, persisted via Docker volume
  - Frontend static files: Served from `static/` directory by FastAPI (built Next.js export)
  - No cloud storage integration

**Caching:**
- In-memory price cache (non-persistent)
  - Implementation: `app/market/cache.py` — PriceCache class
  - Data: Latest prices, previous prices, session open prices, timestamps
  - Lifecycle: Populated by market data source, cleared/restarted on watchlist ticker changes
  - Access: Shared via `app.state.price_cache` to all API routes

## Authentication & Identity

**Auth Provider:**
- Custom JWT-based approach (not yet fully implemented)
  - `JWT_SECRET` environment variable present in `.env`
  - No user login/signup flow implemented
  - Single hardcoded user: `user_id="default"` in all database records
  - Future: Multi-user support enabled via schema (all tables have `user_id` column)

**LLM API Auth:**
- OpenRouter: Bearer token via `OPENROUTER_API_KEY`
- Massive API: API key passed to `RESTClient` constructor

**No database user authentication:**
- SQLite is file-based, no separate user/auth layer
- All access goes through FastAPI backend

## Monitoring & Observability

**Error Tracking:**
- Not detected (no Sentry, Rollbar, etc.)
- Errors logged to console/stdout via Python `logging` module (`app/main.py:24-28`)

**Logs:**
- Python logging framework
  - Format: `%(asctime)s %(levelname)s %(name)s — %(message)s`
  - Level: INFO by default
  - Destination: stdout/stderr (visible in Docker container logs)
  - Usage: Throughout backend (`app/api/*.py`, `app/market/*.py`, `app/db/*.py`)

**Performance Monitoring:**
- None detected (no APM, Datadog, etc.)

## CI/CD & Deployment

**Hosting:**
- Docker (containerized, runs anywhere Docker is available)
- Port: 8000
- Single container runs both frontend (static files) and backend (FastAPI)
- Volume: Named Docker volume `finally-data` maps to `/app/db` for SQLite persistence

**CI Pipeline:**
- Not detected (no GitHub Actions, GitLab CI, Jenkins, etc.)
- Docker build is manual (via `docker build -t finally .`)

**Start Scripts:**
- Referenced in `planning/PLAN.md` but not found in repository:
  - `scripts/start_mac.sh` — Build and run container (macOS/Linux)
  - `scripts/start_windows.ps1` — Build and run container (Windows PowerShell)
  - `scripts/stop_mac.sh` — Stop container (macOS/Linux)
  - `scripts/stop_windows.ps1` — Stop container (Windows PowerShell)

## Environment Configuration

**Required Environment Variables:**
| Variable | Used By | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | `app/api/chat.py` | LLM API authentication |

**Optional Environment Variables:**
| Variable | Used By | Default | Purpose |
|---|---|---|---|
| `MASSIVE_API_KEY` | `app/market/factory.py` | (empty) | Polygon.io API key; if set, uses real market data instead of simulator |
| `MARKET_POLL_INTERVAL_SECONDS` | `app/market/massive_client.py` | 15 | Polling interval for Massive API (seconds) |
| `LLM_MOCK` | `app/api/chat.py:178` | false | If "true", returns deterministic mock LLM responses (testing) |
| `DB_PATH` | `app/db/connection.py:10` | ./db/finally.db | SQLite database file location |
| `JWT_SECRET` | (not used yet) | — | Placeholder for future auth implementation |

**Secrets Location:**
- `.env` file at project root (gitignored)
- Not checked into version control
- Passed to Docker via `--env-file .env` flag
- No separate secrets manager (Vault, AWS Secrets Manager, etc.)

## Webhooks & Callbacks

**Incoming:**
- Not detected
- No webhook endpoints defined

**Outgoing:**
- None implemented
- LLM responses trigger automatic trade execution via `execute_trade()` in `app/api/chat.py:223`
- Portfolio snapshot callback: `_snapshot_callback()` called periodically by market data source

**Auto-Actions via LLM:**
- Trades auto-execute based on LLM structured output (`app/api/chat.py:203-232`)
- Watchlist changes auto-execute based on LLM response (`app/api/chat.py:234-249`)
- Trade failures captured and reported back to user (not external webhook)

## External API Integration Details

**OpenRouter/LiteLLM Integration:**
- Location: `app/api/chat.py:185-196`
- Model: `openrouter/openai/gpt-oss-120b` (Cerebras inference)
- Extra body: `{"provider": {"order": ["cerebras"]}}` (forces Cerebras provider)
- Request: Messages array with system prompt + portfolio context + chat history + user message
- Response: Structured JSON with `message`, `trades`, `watchlist_changes` fields
- Error handling: Falls back to canned message if LLM call fails, returns HTTP 200 (not 500)
- Mock mode: If `LLM_MOCK=true`, returns hardcoded response (`app/api/chat.py:179-184`)

**Massive/Polygon.io Integration:**
- Location: `app/market/massive_client.py:45-57`
- Endpoint: Snapshot API for all tickers in single call
- Polling: Async loop polling at configurable interval (default 15s)
- Response parsing: Converts Massive response format to internal `PriceUpdate` format
- Fallback: If Massive API unavailable or key not set, system uses built-in GBM simulator instead
- No WebSocket support (uses REST polling only)

**Database Integration:**
- Location: `app/db/connection.py`
- Connection: `aiosqlite.connect(DB_PATH)` with async context manager
- WAL mode: Enables concurrent readers/writers
- Foreign keys: Enforced via pragma
- Row factory: `aiosqlite.Row` for dict-like access

---

*Integration audit: 2026-04-09*
