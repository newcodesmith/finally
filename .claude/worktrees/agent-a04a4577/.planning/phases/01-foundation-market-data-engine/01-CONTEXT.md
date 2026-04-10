# Phase 1: Foundation & Market Data Engine - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the FastAPI backend foundation: uv project setup, SQLite database with lazy initialization and seed data, market data simulator (GBM with correlated moves and random events), in-memory price cache, SSE streaming endpoint, and health check endpoint. Also create .env.example.

</domain>

<decisions>
## Implementation Decisions

### Backend Project Setup
- Python package structure: `backend/app/` with subpackages `market/`, `db/`, `api/` matching PLAN.md §4 and prior conventions
- Async DB via `aiosqlite` with async context manager in `app/db/connection.py`
- Import style: `from __future__ import annotations` + relative imports per CONVENTIONS.md
- Linting/formatting: Ruff with E, F, I, N, W rules, 100 char line length

### Market Data Simulator
- GBM correlation: Cholesky decomposition on correlation matrix (numpy) for correlated ticker moves
- Random events: ~1% chance per tick per ticker for 2-5% sudden move
- Seed prices: Hardcoded dict in `seed_prices.py` with realistic 2024-era prices
- Abstract interface: ABC `MarketDataSource` with `start()`, `stop()`, callback pattern

### SSE & Price Cache
- SSE format: `data: {json}\n\n` with fields: ticker, price, previous_price, session_open_price, timestamp, change_direction
- change_direction values: `"up"`, `"down"`, `"unchanged"` — first tick defaults to `"unchanged"`
- Price cache: asyncio Lock (single-threaded event loop, no threading needed)
- Watchlist pruning: Remove ticker from cache immediately on watchlist delete

### Claude's Discretion
- Specific GBM parameters (drift, volatility per ticker) — use realistic values
- Exact correlation matrix values between tickers
- Internal module organization within each subpackage

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- No existing code — greenfield build. Prior implementation was deleted.
- Codebase maps document the conventions and patterns from the prior implementation for consistency.

### Established Patterns
- Snake case naming, PascalCase classes, UPPER_SNAKE_CASE constants
- Module-level docstrings, class docstrings, method docstrings
- `from __future__ import annotations` as first import
- Async context managers for DB connections
- Ruff for linting (E, F, I, N, W rules)

### Integration Points
- FastAPI app entry point: `backend/app/main.py`
- Database: `backend/app/db/connection.py` → `db/finally.db`
- SSE endpoint: `GET /api/stream/prices`
- Health check: `GET /api/health`
- Environment: `.env` at project root, loaded via python-dotenv

</code_context>

<specifics>
## Specific Ideas

- Follow PLAN.md §6 exactly for market data architecture (two implementations, one interface)
- Follow PLAN.md §7 exactly for database schema (all 6 tables with user_id defaulting to "default")
- Massive API client should be a real implementation (not just a stub) per PLAN.md
- Price cache should support future multi-user scenarios per PLAN.md §6

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
