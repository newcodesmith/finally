# FinAlly — AI Trading Workstation

A Bloomberg-inspired trading terminal with live market data, simulated portfolio management, and an AI assistant that can analyze your positions and execute trades through natural language.

Built as a capstone for an agentic AI coding course — the entire application is constructed by orchestrated AI coding agents.

## Features

- **Live price streaming** — prices flash green/red on tick via SSE
- **Simulated portfolio** — start with $10,000 virtual cash, buy/sell at market price
- **Portfolio heatmap** — treemap sized by weight, colored by P&L
- **P&L chart** — total portfolio value over time
- **AI chat assistant** — ask questions, get analysis, and have trades executed via natural language
- **Watchlist management** — add/remove tickers manually or through the AI

## Quick Start

```bash
cp .env.example .env
# Add your OPENROUTER_API_KEY to .env
./scripts/start_mac.sh
```

Open [http://localhost:8000](http://localhost:8000).

### Windows

```powershell
.\scripts\start_windows.ps1
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key for AI chat |
| `MASSIVE_API_KEY` | No | Polygon.io key for real market data (simulator used if unset) |
| `LLM_MOCK` | No | Set `true` for deterministic mock LLM responses (testing) |

## Architecture

Single Docker container on port 8000:

- **Frontend**: Next.js (TypeScript, static export)
- **Backend**: FastAPI (Python/uv)
- **Database**: SQLite (volume-mounted at `db/finally.db`)
- **Real-time**: Server-Sent Events (`/api/stream/prices`)
- **AI**: LiteLLM → OpenRouter (Cerebras inference)

## Development

```bash
# Stop the container
./scripts/stop_mac.sh

# Rebuild after code changes
./scripts/start_mac.sh --build
```

## Testing

E2E tests use Playwright against a Docker-composed test environment with `LLM_MOCK=true`:

```bash
cd test
docker compose -f docker-compose.test.yml up --abort-on-container-exit
```

Unit tests live in `frontend/` and `backend/` respectively.
