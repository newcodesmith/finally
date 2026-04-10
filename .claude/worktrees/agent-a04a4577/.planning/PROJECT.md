# FinAlly — AI Trading Workstation

## What This Is

FinAlly (Finance Ally) is a visually stunning AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot. Built as a capstone project for an agentic AI coding course, demonstrating how orchestrated AI agents can produce a production-quality full-stack application.

## Core Value

Users can interact with a real-time simulated trading environment through both manual controls and natural language AI commands — the seamless fusion of live market data, portfolio management, and AI assistance in a single polished interface.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Live-updating price watchlist with flash animations and sparklines for 10 default tickers
- [ ] SSE streaming of market data from simulator (or optional Massive API)
- [ ] Main chart area showing detailed price history for selected ticker
- [ ] Portfolio heatmap (treemap) sized by weight, colored by P&L
- [ ] P&L line chart tracking total portfolio value over time
- [ ] Positions table with ticker, quantity, avg cost, current price, unrealized P&L, % change
- [ ] Trade bar for market orders (buy/sell) with instant fill at current price
- [ ] AI chat panel with LLM integration via LiteLLM/OpenRouter for portfolio analysis and trade execution
- [ ] LLM structured output with auto-execution of trades and watchlist changes
- [ ] Watchlist management (add/remove tickers manually or via AI)
- [ ] Portfolio starting at $10,000 virtual cash
- [ ] SQLite database with lazy initialization and seed data
- [ ] Single Docker container serving frontend static export + FastAPI backend on port 8000
- [ ] Dark terminal-inspired UI with accent colors (yellow #ecad0a, blue #209dd7, purple #753991)
- [ ] Connection status indicator (green/yellow/red dot)
- [ ] Portfolio snapshots recorded every 30 seconds and after each trade (pruned after 24h)
- [ ] Market simulator using geometric Brownian motion with correlated moves and random events
- [ ] Backend unit tests (pytest) for market data, portfolio, LLM, API routes
- [ ] Frontend component tests
- [ ] E2E tests with Playwright and LLM mock mode
- [ ] Start/stop scripts for macOS/Linux

### Out of Scope

- User authentication/login — single-user app, no auth needed
- Limit orders / order book — market orders only for simplicity
- Real-time WebSocket — SSE is sufficient for one-way push
- Multi-user support — hardcoded "default" user, schema supports future expansion
- Mobile-first design — desktop-first, functional on tablet
- Cloud deployment (Terraform/App Runner) — stretch goal, not core build
- Windows PowerShell scripts — defer per PLAN.md S5

## Context

- **Tech stack**: Next.js (static export) + FastAPI (Python/uv) + SQLite, served from single Docker container
- **Market data**: Two implementations behind abstract interface — simulator (default) and Massive API (optional via env var)
- **AI integration**: LiteLLM → OpenRouter → `openrouter/openai/gpt-oss-120b` model with Cerebras inference, structured JSON output
- **Real-time**: SSE via EventSource API, ~500ms update cadence
- **Prior work**: Market data component was previously completed (simulator, Massive client, SSE streaming, price cache). All code has been deleted and needs to be rebuilt.
- **Planning docs**: Comprehensive PLAN.md exists with full spec including API endpoints, database schema, environment variables, Docker setup, and testing strategy
- **Charting**: Canvas-based library preferred (Lightweight Charts or Recharts)
- **Styling**: Tailwind CSS with custom dark theme

## Constraints

- **Single container**: Everything served on port 8000 — no CORS, no service orchestration
- **No external DB**: SQLite only, volume-mounted for persistence
- **Static frontend**: Next.js `output: 'export'` — no SSR, no API routes in Next.js
- **Market orders only**: No order book, no partial fills, no fees
- **No confirmation dialogs**: Trades execute instantly (simulated money, zero stakes)
- **LLM model**: Must use LiteLLM via OpenRouter with Cerebras inference provider
- **Environment-driven**: Simulator vs Massive API selected by `MASSIVE_API_KEY` env var presence

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SSE over WebSockets | One-way push sufficient; simpler, universal browser support | — Pending |
| Static Next.js export | Single origin, no CORS, one port, one container | — Pending |
| SQLite over Postgres | Single-user, no DB server needed, zero config | — Pending |
| Single Docker container | One command to run, no docker-compose orchestration | — Pending |
| uv for Python | Fast, modern, reproducible lockfile | — Pending |
| Market orders only | Eliminates order book complexity | — Pending |
| LLM auto-execution | Simulated money, impressive demo, agentic AI showcase | — Pending |
| Geometric Brownian Motion | Realistic price simulation with configurable drift/volatility | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-09 after initialization*
