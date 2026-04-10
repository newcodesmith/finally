# Technology Stack

**Analysis Date:** 2026-04-09

## Languages

**Primary:**
- TypeScript — Frontend (Next.js project, not currently deployed)
- Python 3.12+ — Backend (FastAPI, active)

**Secondary:**
- JavaScript/JSX — Frontend build artifacts

## Runtime

**Environment:**
- Python 3.12 (backend runtime, specified in `pyproject.toml`)
- Node 20 (frontend build only, not runtime; static export served by FastAPI)

**Package Managers:**
- `uv` (Python) — Version managed via project, replacements for pip/pipenv. Lockfile: `uv.lock` (present at `backend/uv.lock`)
- `npm` (Node) — Used during Docker build stage, not runtime

## Frameworks

**Core:**
- FastAPI 0.115.0+ — REST API server, SSE streaming, static file serving (Python)
- Uvicorn [standard] 0.32.0+ — ASGI server runtime for FastAPI
- Next.js — Frontend framework (TypeScript, static export mode), not currently active in deployment

**Async/Concurrency:**
- asyncio (Python stdlib) — Built-in async runtime for FastAPI and background tasks
- aiosqlite 0.20.0+ — Async SQLite client for non-blocking database operations

**Testing:**
- pytest 8.3.0+ — Python unit test framework (dev dependency, `backend/tests/`)
- pytest-asyncio 0.24.0+ — Async test support for pytest
- pytest-cov 5.0.0+ — Coverage reporting

**Build/Dev:**
- ruff 0.7.0+ — Python linter/formatter (dev dependency)

## Key Dependencies

**Critical:**
- `fastapi` 0.115.0+ — Request handling, OpenAPI schema generation
- `aiosqlite` 0.20.0+ — Async database access (no thread pool needed)
- `litellm` 1.0.0+ — LLM client abstraction layer (handles OpenRouter API calls with structured outputs)
- `massive` 1.0.0+ — Polygon.io REST client for real market data (optional via MASSIVE_API_KEY)

**Infrastructure:**
- `numpy` 2.0.0+ — Numerical computing; used in GBM simulator for correlated random number generation (`app/market/simulator.py`)
- `rich` 13.0.0+ — Terminal formatting (logging, demo CLI tool)
- `httpx` 0.27.0+ — HTTP client (via LiteLLM dependency chain for API calls)
- `python-dotenv` 1.0.0+ — Environment variable loading from `.env` files

## Configuration

**Environment:**
- `.env` file at project root (gitignored, not committed)
- Loaded by backend on startup via `python-dotenv` at `backend/app/main.py:14`
- Backend looks for `.env` one level above `backend/` directory
- See "Environment Configuration" section below

**Build:**
- `backend/pyproject.toml` — Python project metadata, dependencies, test config, linter/formatter settings
- `backend/uv.lock` — Reproducible lockfile for all Python dependencies
- Frontend project presumed to have `package.json` (not currently deployed; empty `frontend/` directory)
- `backend/app/db/schema.py` — SQLite schema definition (created lazily on first run)

## Platform Requirements

**Development:**
- Python 3.12+
- Node 20+ (for frontend builds, though not currently used)
- Docker (for containerized deployment)
- SQLite 3 (bundled with Python)

**Production:**
- Docker runtime (single image serves both frontend and backend)
- Port 8000 (HTTP)
- SQLite database file with write access to volume mount (`/app/db/finally.db`)
- Network access to OpenRouter API for LLM calls
- Optional: Network access to Massive/Polygon.io API for real market data

## Environment Configuration

**Required Variables:**
- `OPENROUTER_API_KEY` — API key for LLM inference via OpenRouter (used in `app/api/chat.py:29`)
- `JWT_SECRET` — (present in current .env, purpose/usage not yet documented in code)

**Optional Variables:**
- `MASSIVE_API_KEY` — Polygon.io API key; if empty or unset, market simulator is used instead (`app/market/factory.py`)
- `MARKET_POLL_INTERVAL_SECONDS` — Polling interval for Massive API (default: 15 seconds)
- `LLM_MOCK` — Set to "true" for deterministic mock LLM responses (testing mode)
- `DB_PATH` — SQLite database file location (default: `./db/finally.db`, set in `app/db/connection.py:10`)

**Secrets Location:**
- `.env` file at repository root (gitignored)
- Docker: passed via `--env-file .env` at runtime
- No separate secrets manager configured; all secrets in single .env file

## Build Pipeline

**Docker Multi-Stage Build:**
1. Stage 1 (Node 20 slim): Builds Next.js frontend (static export)
2. Stage 2 (Python 3.12 slim): Installs uv, copies backend, runs `uv sync`, copies static files, exposes port 8000

**Build Output:**
- Single Docker image with both frontend and backend
- Frontend served as static files from `static/` directory
- Backend runs FastAPI on port 8000

**Lockfiles:**
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

---

*Stack analysis: 2026-04-09*
