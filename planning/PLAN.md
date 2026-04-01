# FinAlly — AI Trading Workstation

## Project Specification

## 1. Vision

FinAlly (Finance Ally) is a visually stunning AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot.

This is the capstone project for an agentic AI coding course. It is built entirely by Coding Agents demonstrating how orchestrated AI agents can produce a production-quality full-stack application. Agents interact through files in `planning/`.

## 2. User Experience

### First Launch

The user runs a single Docker command (or a provided start script). A browser opens to `http://localhost:8000`. No login, no signup. They immediately see:

- A watchlist of 10 default tickers with live-updating prices in a grid
- $10,000 in virtual cash
- A dark, data-rich trading terminal aesthetic
- An AI chat panel ready to assist

### What the User Can Do

- **Watch prices stream** — prices flash green (uptick) or red (downtick) with subtle CSS animations that fade
- **View sparkline mini-charts** — price action beside each ticker in the watchlist, accumulated on the frontend from the SSE stream since page load (sparklines fill in progressively)
- **Click a ticker** to see a larger detailed chart in the main chart area
- **Buy and sell shares** — market orders only, instant fill at current price, no fees, no confirmation dialog
- **Monitor their portfolio** — a heatmap (treemap) showing positions sized by weight and colored by P&L, plus a P&L chart tracking total portfolio value over time
- **View a positions table** — ticker, quantity, average cost, current price, unrealized P&L, % change
- **Chat with the AI assistant** — ask about their portfolio, get analysis, and have the AI execute trades and manage the watchlist through natural language
- **Manage the watchlist** — add/remove tickers manually or via the AI chat

### Visual Design

- **Dark theme**: backgrounds around `#0d1117` or `#1a1a2e`, muted gray borders, no pure black
- **Price flash animations**: brief green/red background highlight on price change, fading over ~500ms via CSS transitions
- **Connection status indicator**: a small colored dot (green = connected, yellow = reconnecting, red = disconnected) visible in the header
- **Professional, data-dense layout**: inspired by Bloomberg/trading terminals — every pixel earns its place
- **Responsive but desktop-first**: optimized for wide screens, functional on tablet

### Color Scheme
- Accent Yellow: `#ecad0a`
- Blue Primary: `#209dd7`
- Purple Secondary: `#753991` (submit buttons)

## 3. Architecture Overview

### Single Container, Single Port

```
┌─────────────────────────────────────────────────┐
│  Docker Container (port 8000)                   │
│                                                 │
│  FastAPI (Python/uv)                            │
│  ├── /api/*          REST endpoints             │
│  ├── /api/stream/*   SSE streaming              │
│  └── /*              Static file serving         │
│                      (Next.js export)            │
│                                                 │
│  SQLite database (volume-mounted)               │
│  Background task: market data polling/sim        │
└─────────────────────────────────────────────────┘
```

- **Frontend**: Next.js with TypeScript, built as a static export (`output: 'export'`), served by FastAPI as static files
- **Backend**: FastAPI (Python), managed as a `uv` project
- **Database**: SQLite, single file at `db/finally.db`, volume-mounted for persistence
- **Real-time data**: Server-Sent Events (SSE) — simpler than WebSockets, one-way server→client push, works everywhere
- **AI integration**: LiteLLM → OpenRouter (Cerebras for fast inference), with structured outputs for trade execution
- **Market data**: Environment-variable driven — simulator by default, real data via Massive API if key provided

### Why These Choices

| Decision | Rationale |
|---|---|
| SSE over WebSockets | One-way push is all we need; simpler, no bidirectional complexity, universal browser support |
| Static Next.js export | Single origin, no CORS issues, one port, one container, simple deployment |
| SQLite over Postgres | No auth = no multi-user = no need for a database server; self-contained, zero config |
| Single Docker container | Students run one command; no docker-compose for production, no service orchestration |
| uv for Python | Fast, modern Python project management; reproducible lockfile; what students should learn |
| Market orders only | Eliminates order book, limit order logic, partial fills — dramatically simpler portfolio math |

---

## 4. Directory Structure

```
finally/
├── frontend/                 # Next.js TypeScript project (static export)
├── backend/                  # FastAPI uv project (Python)
│   └── schema/               # Schema definitions, seed data, migration logic
├── planning/                 # Project-wide documentation for agents
│   ├── PLAN.md               # This document
│   └── ...                   # Additional agent reference docs
├── scripts/
│   ├── start_mac.sh          # Launch Docker container (macOS/Linux)
│   ├── stop_mac.sh           # Stop Docker container (macOS/Linux)
│   ├── start_windows.ps1     # Launch Docker container (Windows PowerShell)
│   └── stop_windows.ps1      # Stop Docker container (Windows PowerShell)
├── test/                     # Playwright E2E tests + docker-compose.test.yml
├── db/                       # Volume mount target (SQLite file lives here at runtime)
│   └── .gitkeep              # Directory exists in repo; finally.db is gitignored
├── Dockerfile                # Multi-stage build (Node → Python)
├── docker-compose.yml        # Optional convenience wrapper
├── .env                      # Environment variables (gitignored, .env.example committed)
└── .gitignore
```

### Key Boundaries

- **`frontend/`** is a self-contained Next.js project. It knows nothing about Python. It talks to the backend via `/api/*` endpoints and `/api/stream/*` SSE endpoints. Internal structure is up to the Frontend Engineer agent.
- **`backend/`** is a self-contained uv project with its own `pyproject.toml`. It owns all server logic including database initialization, schema, seed data, API routes, SSE streaming, market data, and LLM integration. Internal structure is up to the Backend/Market Data agents.
- **`backend/schema/`** contains schema SQL definitions and seed logic. The backend lazily initializes the database on first request — creating tables and seeding default data if the SQLite file doesn't exist or is empty.
- **`db/`** at the top level is the runtime volume mount point. The SQLite file (`db/finally.db`) is created here by the backend and persists across container restarts via Docker volume.
- **`planning/`** contains project-wide documentation, including this plan. All agents reference files here as the shared contract.
- **`test/`** contains Playwright E2E tests and supporting infrastructure (e.g., `docker-compose.test.yml`). Unit tests live within `frontend/` and `backend/` respectively, following each framework's conventions.
- **`scripts/`** contains start/stop scripts that wrap Docker commands.

---

## 5. Environment Variables

```bash
# Required: OpenRouter API key for LLM chat functionality
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Optional: Massive (Polygon.io) API key for real market data
# If not set, the built-in market simulator is used (recommended for most users)
MASSIVE_API_KEY=

# Optional: Polling interval in seconds when using Massive API (default: 15)
# Free tier supports ~15s; paid tiers can use lower values (e.g. 5)
MARKET_POLL_INTERVAL_SECONDS=15

# Optional: Set to "true" for deterministic mock LLM responses (testing)
LLM_MOCK=false
```

### Behavior

- If `MASSIVE_API_KEY` is set and non-empty → backend uses Massive REST API for market data, polling every `MARKET_POLL_INTERVAL_SECONDS` seconds
- If `MASSIVE_API_KEY` is absent or empty → backend uses the built-in market simulator
- If `LLM_MOCK=true` → backend returns deterministic mock LLM responses (for E2E tests)
- The backend reads `.env` from the project root (mounted into the container or read via docker `--env-file`)

---

## 6. Market Data

### Two Implementations, One Interface

Both the simulator and the Massive client implement the same abstract interface. The backend selects which to use based on the environment variable. All downstream code (SSE streaming, price cache, frontend) is agnostic to the source.

### Simulator (Default)

- Generates prices using geometric Brownian motion (GBM) with configurable drift and volatility per ticker
- Updates at ~500ms intervals
- Correlated moves across tickers (e.g., tech stocks move together)
- Occasional random "events" — sudden 2-5% moves on a ticker for drama
- Starts from realistic seed prices (e.g., AAPL ~$190, GOOGL ~$175, etc.) — these seed prices are retained as the session "open price" for computing session change %
- Runs as an in-process background task — no external dependencies

### Massive API (Optional)

- REST API polling (not WebSocket) — simpler, works on all tiers
- Polls for all tickers currently in the watchlist on a configurable interval (see `MARKET_POLL_INTERVAL_SECONDS` in §5)
- Parses REST response into the same format as the simulator
- The first price received per ticker on startup is retained as the session "open price" for computing session change %

### Shared Price Cache

- A single background task (simulator or Massive poller) writes to an in-memory price cache
- The cache holds the latest price, previous price, session open price, and timestamp for each ticker
- The cache only tracks tickers currently in the watchlist; tickers removed from the watchlist are pruned from the cache
- SSE streams read from this cache and push updates to connected clients
- This architecture supports future multi-user scenarios without changes to the data layer

### SSE Streaming

- Endpoint: `GET /api/stream/prices`
- Long-lived SSE connection; client uses native `EventSource` API
- Server pushes price updates for all tickers currently in the watchlist at a regular cadence (~500ms)
- Each SSE event contains: `ticker`, `price`, `previous_price`, `session_open_price`, `timestamp`, `change_direction`
- Client handles reconnection automatically (EventSource has built-in retry)

---

## 7. Database

### SQLite with Lazy Initialization

The backend checks for the SQLite database on startup (or first request). If the file doesn't exist or tables are missing, it creates the schema and seeds default data. This means:

- No separate migration step
- No manual database setup
- Fresh Docker volumes start with a clean, seeded database automatically

### Schema

All tables include a `user_id` column defaulting to `"default"`. This is hardcoded for now (single-user) but enables future multi-user support without schema migration.

**users_profile** — User state (cash balance)
- `id` TEXT PRIMARY KEY (default: `"default"`)
- `cash_balance` REAL (default: `10000.0`)
- `created_at` TEXT (ISO timestamp)

**watchlist** — Tickers the user is watching
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `added_at` TEXT (ISO timestamp)
- UNIQUE constraint on `(user_id, ticker)`

**positions** — Current holdings (one row per ticker per user)
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `quantity` REAL (fractional shares supported)
- `avg_cost` REAL
- `updated_at` TEXT (ISO timestamp)
- UNIQUE constraint on `(user_id, ticker)`

**trades** — Trade history (append-only log)
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `side` TEXT (`"buy"` or `"sell"`)
- `quantity` REAL (fractional shares supported)
- `price` REAL
- `executed_at` TEXT (ISO timestamp)

**portfolio_snapshots** — Portfolio value over time (for P&L chart). Recorded every 30 seconds by a background task, and immediately after each trade execution. Rows older than 24 hours are pruned by the background task to prevent unbounded growth.
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `total_value` REAL
- `recorded_at` TEXT (ISO timestamp)

**chat_messages** — Conversation history with LLM
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `role` TEXT (`"user"` or `"assistant"`)
- `content` TEXT
- `actions` TEXT (JSON — trades executed, watchlist changes made; null for user messages)
- `created_at` TEXT (ISO timestamp)

### Default Seed Data

- One user profile: `id="default"`, `cash_balance=10000.0`
- Ten watchlist entries: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX

---

## 8. API Endpoints

### Market Data
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stream/prices` | SSE stream of live price updates |

### Portfolio
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/portfolio` | Current positions, cash balance, total value, unrealized P&L |
| POST | `/api/portfolio/trade` | Execute a trade: `{ticker, quantity, side}`. If the ticker is not in the watchlist, it is automatically added. |
| GET | `/api/portfolio/history` | Portfolio value snapshots over time (for P&L chart) |

### Watchlist
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/watchlist` | Current watchlist tickers with latest prices |
| POST | `/api/watchlist` | Add a ticker: `{ticker}` |
| DELETE | `/api/watchlist/{ticker}` | Remove a ticker |

### Chat
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Send a message, receive complete JSON response (message + executed actions) |

### System
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check (for Docker/deployment) |

---

## 9. LLM Integration

When writing code to make calls to LLMs, use cerebras-inference skill to use LiteLLM via OpenRouter to the `openrouter/openai/gpt-oss-120b` model with Cerebras as the inference provider. Structured Outputs should be used to interpret the results.

There is an OPENROUTER_API_KEY in the .env file in the project root.

### How It Works

When the user sends a chat message, the backend:

1. Loads the user's current portfolio context (cash, positions with P&L, watchlist with live prices, total portfolio value)
2. Loads the most recent 20 messages from the `chat_messages` table (10 user/assistant pairs)
3. Constructs a prompt with a system message, portfolio context, conversation history, and the user's new message
4. Calls the LLM via LiteLLM → OpenRouter, requesting structured output, using the cerebras-inference skill
5. Parses the complete structured JSON response
6. Auto-executes any trades or watchlist changes specified in the response
7. Stores the message and executed actions in `chat_messages`
8. Returns the complete JSON response to the frontend (no token-by-token streaming — Cerebras inference is fast enough that a loading indicator is sufficient)

### Structured Output Schema

The LLM is instructed to respond with JSON matching this schema:

```json
{
  "message": "Your conversational response to the user",
  "trades": [
    {"ticker": "AAPL", "side": "buy", "quantity": 10}
  ],
  "watchlist_changes": [
    {"ticker": "PYPL", "action": "add"},
    {"ticker": "TSLA", "action": "remove"}
  ]
}
```

- `message` (required): The conversational text shown to the user
- `trades` (optional): Array of trades to auto-execute. Each trade goes through the same validation as manual trades (sufficient cash for buys, sufficient shares for sells). If the ticker is not currently in the watchlist, it is automatically added when the trade executes.
- `watchlist_changes` (optional): Array of watchlist modifications. `action` must be `"add"` or `"remove"`.

### Auto-Execution

Trades specified by the LLM execute automatically — no confirmation dialog. This is a deliberate design choice:
- It's a simulated environment with fake money, so the stakes are zero
- It creates an impressive, fluid demo experience
- It demonstrates agentic AI capabilities — the core theme of the course

If a trade fails validation (e.g., insufficient cash), the error is included in the chat response so the LLM can inform the user.

If the LLM call itself fails (network error, rate limit, malformed response), the backend returns HTTP 200 with a fallback `message` such as "Sorry, I'm having trouble connecting right now. Please try again." — never a 500 — so the chat panel remains functional.

### System Prompt Guidance

The LLM should be prompted as "FinAlly, an AI trading assistant" with instructions to:
- Analyze portfolio composition, risk concentration, and P&L
- Suggest trades with reasoning
- Execute trades when the user asks or agrees
- Manage the watchlist proactively
- Be concise and data-driven in responses
- Always respond with valid structured JSON

### LLM Mock Mode

When `LLM_MOCK=true`, the backend returns deterministic mock responses instead of calling OpenRouter. This enables:
- Fast, free, reproducible E2E tests
- Development without an API key
- CI/CD pipelines

---

## 10. Frontend Design

### Layout

The frontend is a single-page application with a dense, terminal-inspired layout. The specific component architecture and layout system is up to the Frontend Engineer, but the UI should include these elements:

- **Watchlist panel** — grid/table of watched tickers with: ticker symbol, current price (flashing green/red on change), session change % (vs. the session open price provided in each SSE event), and a sparkline mini-chart (accumulated from SSE since page load — resets on page reload, this is intentional)
- **Main chart area** — larger chart for the currently selected ticker, with at minimum price over time. Clicking a ticker in the watchlist selects it here.
- **Portfolio heatmap** — treemap visualization where each rectangle is a position, sized by portfolio weight, colored by P&L (green = profit, red = loss). When there are no open positions, show a placeholder message ("No positions yet — buy something to get started") rather than an empty treemap.
- **P&L chart** — line chart showing total portfolio value over time, using data from `portfolio_snapshots`
- **Positions table** — tabular view of all positions: ticker, quantity, avg cost, current price, unrealized P&L, % change
- **Trade bar** — simple input area: ticker field, quantity field, buy button, sell button. Market orders, instant fill.
- **AI chat panel** — docked/collapsible sidebar. Message input, scrolling conversation history, loading indicator while waiting for LLM response. Trade executions and watchlist changes shown inline as confirmations.
- **Header** — portfolio total value (updating live), connection status indicator, cash balance

### Technical Notes

- Use `EventSource` for SSE connection to `/api/stream/prices`
- Canvas-based charting library preferred (Lightweight Charts or Recharts) for performance
- Price flash effect: on receiving a new price, briefly apply a CSS class with background color transition, then remove it
- All API calls go to the same origin (`/api/*`) — no CORS configuration needed
- Tailwind CSS for styling with a custom dark theme

---

## 11. Docker & Deployment

### Multi-Stage Dockerfile

```
Stage 1: Node 20 slim
  - Copy frontend/
  - npm install && npm run build (produces static export)

Stage 2: Python 3.12 slim
  - Install uv
  - Copy backend/
  - uv sync (install Python dependencies from lockfile)
  - Copy frontend build output into a static/ directory
  - Expose port 8000
  - CMD: uvicorn serving FastAPI app
```

FastAPI serves the static frontend files and all API routes on port 8000.

### Docker Volume

The SQLite database persists via a named Docker volume:

```bash
docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally
```

The `db/` directory in the project root maps to `/app/db` in the container. The backend writes `finally.db` to this path.

### Start/Stop Scripts

**`scripts/start_mac.sh`** (macOS/Linux):
- Builds the Docker image if not already built (or if `--build` flag passed)
- Runs the container with the volume mount, port mapping, and `.env` file
- Prints the URL to access the app
- Optionally opens the browser

**`scripts/stop_mac.sh`** (macOS/Linux):
- Stops and removes the running container
- Does NOT remove the volume (data persists)

**`scripts/start_windows.ps1`** / **`scripts/stop_windows.ps1`**: PowerShell equivalents for Windows.

All scripts should be idempotent — safe to run multiple times.

### Optional Cloud Deployment

The container is designed to deploy to AWS App Runner, Render, or any container platform. A Terraform configuration for App Runner may be provided in a `deploy/` directory as a stretch goal, but is not part of the core build.

---

## 12. Testing Strategy

### Unit Tests (within `frontend/` and `backend/`)

**Backend (pytest)**:
- Market data: simulator generates valid prices, GBM math is correct, Massive API response parsing works, both implementations conform to the abstract interface
- Portfolio: trade execution logic, P&L calculations, edge cases (selling more than owned, buying with insufficient cash, selling at a loss)
- LLM: structured output parsing handles all valid schemas, graceful handling of malformed responses, trade validation within chat flow
- API routes: correct status codes, response shapes, error handling

**Frontend (React Testing Library or similar)**:
- Component rendering with mock data
- Price flash animation triggers correctly on price changes
- Watchlist CRUD operations
- Portfolio display calculations
- Chat message rendering and loading state

### E2E Tests (in `test/`)

**Infrastructure**: A separate `docker-compose.test.yml` in `test/` that spins up the app container plus a Playwright container. This keeps browser dependencies out of the production image.

**Environment**: Tests run with `LLM_MOCK=true` by default for speed and determinism.

**Key Scenarios**:
- Fresh start: default watchlist appears, $10k balance shown, prices are streaming
- Add and remove a ticker from the watchlist
- Buy shares: cash decreases, position appears, portfolio updates
- Sell shares: cash increases, position updates or disappears
- Portfolio visualization: heatmap renders with correct colors, P&L chart has data points
- AI chat (mocked): send a message, receive a response, trade execution appears inline
- SSE resilience: disconnect and verify reconnection

---

## 13. Review Notes — Questions, Clarifications, and Simplification Opportunities

This section captures open questions and potential improvements identified during plan review. Items are grouped by theme. Overlaps with the separate `REVIEW.md` document are avoided; this section focuses on gaps not covered there.

---

### Questions That Need Answers Before Building

**Q1. What model/version is `openrouter/openai/gpt-oss-120b`?**
The LLM model string `openrouter/openai/gpt-oss-120b` is not a currently documented OpenRouter model name. Confirm the exact model identifier to use (e.g. `openrouter/openai/gpt-4o`, `openrouter/cerebras/llama-3.3-70b`) before the backend agent writes the LiteLLM call. A wrong model string will result in a runtime error on every chat request.

**Q2. How should the trade bar handle unknown tickers in the simulator?**
Section 8 notes that buying a ticker not on the watchlist automatically adds it. Under the simulator, any ticker string becomes a valid price stream. Should the trade bar accept any string, or only tickers already on the watchlist? Accepting arbitrary strings risks polluting the watchlist with typos. Suggested rule: the trade bar validates that the ticker exists in the watchlist before submitting, and shows a validation error if not. The chat path can still add-then-buy as a two-step operation.

**Q3. Is fractional share quantity allowed in the trade bar UI?**
The schema supports fractional shares (`quantity REAL`). Should the manual trade bar allow fractional input (e.g. `0.5` shares of AAPL)? Or only whole numbers for simplicity? The LLM path can always use fractional quantities regardless. This is a UX decision that affects input validation on both frontend and backend.

**Q4. What is the `GET /api/portfolio/history` time window?**
The endpoint returns portfolio snapshots for the P&L chart. Does it return all snapshots (up to 24 hours of data as implied by the pruning rule), or a fixed window (e.g. last 1 hour, last 4 hours)? What is the response shape — an array of `{recorded_at, total_value}` objects? Define this so the frontend chart agent and backend agent agree.

**Q5. Does `GET /api/health` check database connectivity?**
A health check that only returns `{"status": "ok"}` unconditionally is not useful for Docker's `HEALTHCHECK` instruction. Should it verify that the SQLite file is accessible and at least one table exists? Define the success and failure response shapes.

**Q6. What happens when the watchlist is empty?**
A user could remove all 10 default tickers. The SSE stream pushes updates for watchlist tickers — with an empty watchlist, the stream emits nothing. The watchlist panel would be blank. The trade bar would (under Q2's suggested rule) reject all tickers. Should removing the last ticker be blocked, or is an empty watchlist a valid state the UI handles gracefully?

---

### Clarifications That Prevent Divergence Between Agents

**C1. `session_open_price` in SSE events vs. the positions table**
Section 6 defines the SSE event as including `session_open_price` (the first price seen at startup for computing session change %). Section 2 says the watchlist shows "session change %." However, positions show "unrealized P&L, % change" — where "% change" is computed from `avg_cost`, not `session_open_price`. Make this distinction explicit to avoid the frontend agent computing the wrong % in the wrong panel.

**C2. Chat history context: does it include the new user message?**
Section 9, step 2 says "load the most recent 20 messages." Step 3 adds "the user's new message" to the prompt. Is the new message appended after the 20 loaded messages, making the effective context window 21 messages? Clarify the exact construction so the context is neither over-counted nor accidentally duplicated.

**C3. Auto-snapshot after trade: before or after the trade executes?**
Section 7 says a portfolio snapshot is recorded "immediately after each trade execution." The snapshot includes `total_value`. If the snapshot is taken after the trade, it reflects the new position. If taken before, it captures the state the user is moving away from. The intended behavior (after, reflecting the new state) should be stated explicitly since "immediately after" is ambiguous about timing relative to the DB write.

**C4. The `change_direction` field in SSE events**
The SSE payload includes `change_direction` but its allowed values are not specified. Presumed values: `"up"`, `"down"`, or `"unchanged"`. Define the three values (including what happens on the very first tick when there is no previous price to compare against).

**C5. Watchlist `GET` response shape for the price fields**
Section 8 says `GET /api/watchlist` returns "current watchlist tickers with latest prices." Does it return the full SSE payload fields (`price`, `previous_price`, `session_open_price`, `change_direction`, `timestamp`) or a subset? The frontend needs the session change % for the watchlist panel, so `session_open_price` must be included. Define the exact response object shape.

**C6. Trade request: is `quantity` in the request body always positive?**
`POST /api/portfolio/trade` takes `{ticker, quantity, side}`. If `side` is `"sell"`, is `quantity` expected to be positive (and the backend infers the sign from `side`), or can it be negative? Clarify that `quantity` is always a positive number and direction is determined solely by `side`.

---

### Simplification Opportunities

**S1. Drop the Massive API integration for the initial build**
The plan includes two market data implementations behind an interface, plus `MARKET_POLL_INTERVAL_SECONDS` and associated behavior. The Massive API path adds approximately 20% more backend surface area (HTTP client, response parser, poll loop, error handling, rate limiting) with zero benefit for students who have no Massive API key. Recommendation: build and test only the simulator. Stub the Massive path as a single file with a `NotImplementedError` and a comment, leaving the interface contract intact for a stretch goal. This keeps Section 6 architecturally honest without requiring the additional implementation work.

**S2. Remove the `MARKET_POLL_INTERVAL_SECONDS` environment variable**
If S1 is adopted, this variable becomes unused. Even if the Massive path is kept, it adds a configuration surface that most users will never touch. Consider hard-coding 15 seconds for the Massive poller and removing the env var. One fewer variable to document, explain, and test.

**S3. Simplify chat history to a fixed count, not "10 user/assistant pairs"**
Section 9 specifies "the most recent 20 messages (10 user/assistant pairs)." The parenthetical implies enforcing pair structure, which requires extra logic if the most recent 20 rows include an unbalanced count of user vs. assistant messages (e.g., if a failed LLM call left a user message without a response). Simplify to: "load the most recent 20 rows from `chat_messages` ordered by `created_at` descending" — no pair-balancing needed.

**S4. Collapse the portfolio snapshot background task into the price update loop**
The plan describes two background tasks: the market data task (simulator, running every 500ms) and the portfolio snapshot task (running every 30 seconds). Both are async loops. Rather than two separate tasks, the market data task can simply count its own ticks and write a snapshot every 60 ticks (at 500ms cadence, 60 ticks = 30 seconds). This eliminates one independently-scheduled coroutine and one potential source of `aiosqlite` write contention.

**S5. Defer the Windows PowerShell scripts**
`start_windows.ps1` and `stop_windows.ps1` are mentioned in the directory structure and scripts section. Docker Desktop on Windows runs the same `docker run` command as macOS. A single `start.sh` works in Git Bash / WSL2 on Windows. Providing PowerShell scripts is a nice-to-have but adds implementation and testing overhead. Defer to a stretch goal unless there is a specific reason Windows-native PowerShell support is required for the course audience.

**S6. The `docker-compose.yml` at the root is described as "optional convenience wrapper"**
If it is optional and the start scripts are the primary interface, consider removing it from the directory structure entirely to avoid confusion about which launch method to use. Alternatively, make it the primary method and remove the start scripts. Two parallel ways to launch the app creates ambiguity in instructions and tests.

**S7. Reduce the default watchlist from 10 to 5 tickers**
The simulator tracks 10 tickers from the first tick. The SSE stream emits updates for all 10 at 500ms intervals. That is 20 price events per second flowing through the price cache and into every connected `EventSource`. For a demo app with no real-time latency requirements, 5 tickers would produce a visually equivalent result with half the event volume. The default tickers list can remain 10 in the seed data; only the initial watchlist entries need reduction.

---

### Minor Wording Issues

- Section 7 says "all tables include a `user_id` column" but `users_profile` uses `id` as its primary key, not `user_id`. The prose is misleading. Suggest: "all tables other than `users_profile` include a `user_id` foreign key referencing `users_profile.id`."
- Section 11 says "`db/` directory in the project root maps to `/app/db` in the container" immediately after showing a `docker run` command using a named volume (`-v finally-data:/app/db`). A named volume does not map to the project's `db/` directory. One of these two statements is wrong — they describe different persistence models. Pick one and remove the other.
- Section 4's directory tree shows `backend/schema/` but the Key Boundaries prose in the same section references it consistently as `backend/schema/`. However, Section 7 prose says the backend "lazily initializes the database on first request." These two statements do not conflict, but the location of the initialization code (`backend/schema/` vs. `backend/` root vs. `backend/db/`) should be pinned to avoid agents placing schema files in different locations.

