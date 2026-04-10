# Phase 6: Infrastructure & Testing - Research

**Researched:** 2026-04-09
**Domain:** Docker containerization, pytest, Playwright E2E, shell scripting
**Confidence:** HIGH

## Summary

Phase 6 packages the entire FinAlly application into a single Docker container and establishes comprehensive test coverage. The backend (FastAPI/Python 3.12) and frontend (Next.js static export) already exist with working code. The backend already has substantial pytest coverage for market data, portfolio, watchlist, and chat modules. The main work is: (1) writing a multi-stage Dockerfile, (2) creating start/stop shell scripts, (3) filling any backend test gaps for API routes, (4) adding frontend component tests, and (5) setting up E2E Playwright tests against the containerized app.

The static frontend export already exists at `frontend/out/` and the backend already serves static files from a `static/` directory at the project root. The Dockerfile must copy the frontend build output to where the backend expects it. Existing backend tests use `httpx.AsyncClient` with `ASGITransport` and `pytest-asyncio` in auto mode -- new tests should follow the same pattern.

**Primary recommendation:** Build the Dockerfile first (it is the foundation for E2E tests), then scripts, then fill test gaps in order: backend API routes, frontend components, E2E Playwright.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None -- all implementation choices are at Claude's discretion (infrastructure phase).

### Claude's Discretion
All implementation choices are at Claude's discretion -- pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

### Deferred Ideas (OUT OF SCOPE)
None.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Multi-stage Dockerfile (Node build -> Python runtime) | Dockerfile pattern documented below; Node 20 slim -> Python 3.12 slim |
| INFRA-02 | FastAPI serves static frontend + API on port 8000 | Already implemented in `app/main.py` -- static mount at `/` exists |
| INFRA-03 | Docker volume mount for SQLite persistence | `DB_PATH` env var + volume flag in run command |
| INFRA-04 | Start/stop scripts for macOS/Linux | Idempotent bash scripts documented below |
| TEST-01 | Backend pytest tests for market data | Already exist in `backend/tests/market/` (7 test files) |
| TEST-02 | Backend pytest tests for portfolio | Already exist in `backend/tests/test_portfolio.py` (13+ tests) |
| TEST-03 | Backend pytest tests for LLM | Already exist in `backend/tests/test_chat.py` (15+ tests) |
| TEST-04 | Backend pytest tests for API routes | Partially exist; health endpoint untested, need dedicated route tests |
| TEST-05 | Frontend component tests | Need test framework setup (Vitest + React Testing Library) |
| TEST-06 | E2E Playwright tests with docker-compose.test.yml | Need full setup: docker-compose.test.yml, Playwright config, test scripts |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- All project documentation is in the `planning` directory
- Key plan document is `planning/PLAN.md`
- Market data component is complete (see `planning/MARKET_DATA_SUMMARY.md`)
- Backend uses `uv` for Python project management
- Frontend uses Next.js with `output: 'export'` (static export)
- Single container, single port (8000) architecture

## Standard Stack

### Core (Already in Project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | >=0.115.0 | Backend framework | Already in pyproject.toml [VERIFIED: codebase] |
| uvicorn | >=0.32.0 | ASGI server | Already in pyproject.toml [VERIFIED: codebase] |
| pytest | >=8.3.0 | Backend test runner | Already in pyproject.toml dev deps [VERIFIED: codebase] |
| pytest-asyncio | >=0.24.0 | Async test support | Already in pyproject.toml dev deps [VERIFIED: codebase] |
| pytest-cov | >=5.0.0 | Coverage | Already in pyproject.toml dev deps [VERIFIED: codebase] |
| httpx | >=0.27.0 | Async HTTP client (tests use ASGITransport) | Already in pyproject.toml [VERIFIED: codebase] |
| Next.js | 16.2.3 | Frontend framework (static export) | Already in package.json [VERIFIED: codebase] |
| React | 19.2.4 | UI library | Already in package.json [VERIFIED: codebase] |

### New Dependencies Needed

| Library | Purpose | When to Use |
|---------|---------|-------------|
| Vitest | Frontend unit test runner | TEST-05: component tests [ASSUMED] |
| @testing-library/react | React component testing | TEST-05: component tests [ASSUMED] |
| @testing-library/jest-dom | DOM assertion matchers | TEST-05: component tests [ASSUMED] |
| jsdom | Browser environment for Vitest | TEST-05: headless rendering [ASSUMED] |
| @playwright/test | E2E browser testing | TEST-06: E2E tests [ASSUMED] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Vitest | Jest | Vitest is faster, native ESM/TS support, better for modern Next.js projects |
| Playwright | Cypress | Playwright supports multiple browsers, better Docker integration, official Docker images |

## Architecture Patterns

### Recommended Dockerfile Structure

```dockerfile
# Stage 1: Build frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim AS runtime
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy backend and install deps
COPY backend/pyproject.toml backend/uv.lock ./backend/
WORKDIR /app/backend
RUN uv sync --no-dev --frozen

# Copy backend source
COPY backend/app ./app

# Copy frontend build output to static/ (where main.py expects it)
COPY --from=frontend-builder /app/frontend/out /app/static

WORKDIR /app
EXPOSE 8000

# Create db directory for volume mount
RUN mkdir -p /app/db

CMD ["uv", "run", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Key detail:** `app/main.py` serves static files from `../../static` relative to the app module. In the container, the backend app module is at `/app/backend/app/`, so static dir resolves to `/app/static/`. The frontend build output (`frontend/out/`) must be copied there. [VERIFIED: codebase - main.py line 86]

**DB_PATH:** The connection module reads `DB_PATH` env var, defaulting to `./db/finally.db`. In the container, the working directory is `/app`, so it resolves to `/app/db/finally.db`. Volume mount at `/app/db` persists the database. [VERIFIED: codebase - connection.py line 10]

### Start/Stop Script Pattern

```bash
#!/usr/bin/env bash
# scripts/start_mac.sh - Idempotent start
set -euo pipefail

IMAGE_NAME="finally"
CONTAINER_NAME="finally-app"
VOLUME_NAME="finally-data"
PORT=8000

# Build if needed or --build flag passed
if [[ "${1:-}" == "--build" ]] || ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
    docker build -t "$IMAGE_NAME" .
fi

# Stop existing container if running
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

# Run
docker run -d \
    --name "$CONTAINER_NAME" \
    -v "$VOLUME_NAME:/app/db" \
    -p "$PORT:8000" \
    --env-file .env \
    "$IMAGE_NAME"

echo "FinAlly running at http://localhost:$PORT"
```

### E2E Test Infrastructure

```
test/
├── docker-compose.test.yml   # App container + Playwright container
├── playwright.config.ts      # Playwright configuration
├── e2e/
│   ├── smoke.spec.ts         # Basic app loads, prices stream
│   ├── watchlist.spec.ts     # Add/remove tickers
│   ├── trading.spec.ts       # Buy/sell flows
│   ├── chat.spec.ts          # AI chat with mock
│   └── sse.spec.ts           # SSE connection/reconnection
├── package.json              # Playwright + deps
└── tsconfig.json
```

### docker-compose.test.yml Pattern

```yaml
services:
  app:
    build: ..
    ports:
      - "8000:8000"
    environment:
      - LLM_MOCK=true
      - DB_PATH=/app/db/test.db
    volumes:
      - test-data:/app/db
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 5s
      timeout: 3s
      retries: 10

  playwright:
    image: mcr.microsoft.com/playwright:v1.52.0-noble
    depends_on:
      app:
        condition: service_healthy
    working_dir: /tests
    volumes:
      - ./:/tests
    command: npx playwright test
    environment:
      - BASE_URL=http://app:8000

volumes:
  test-data:
```

### Anti-Patterns to Avoid

- **Installing Node in the Python stage:** Use multi-stage build; Python stage should never need Node. [ASSUMED]
- **Running `npm install` instead of `npm ci`:** `npm ci` is deterministic and faster in Docker builds. [ASSUMED]
- **Copying node_modules into Docker:** Always `npm ci` inside the build stage. The host `node_modules` may have wrong platform binaries. [ASSUMED]
- **Using `latest` tag for Playwright Docker image:** Pin to exact version matching the installed `@playwright/test` version. [ASSUMED]
- **Putting test dependencies in production image:** Use `--no-dev` for uv sync in the runtime stage. [ASSUMED]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Docker health checks | Custom health scripts | curl to /api/health | Simple, standard, already have the endpoint |
| Playwright browser management | Manual browser install | Official Playwright Docker image | Handles all browser deps, tested by Microsoft |
| Frontend test environment | Custom JSDOM setup | Vitest + jsdom environment | Vitest handles env setup automatically |
| Container process management | Custom entrypoint scripts | Direct CMD with uvicorn | Single process container, no supervisor needed |

## Common Pitfalls

### Pitfall 1: Static File Path Resolution in Container
**What goes wrong:** The static files aren't found because the relative path in `main.py` resolves differently in the container vs local development.
**Why it happens:** `main.py` computes `_static_dir` as `os.path.join(os.path.dirname(__file__), "..", "..", "static")`. From `/app/backend/app/main.py`, this resolves to `/app/static/`.
**How to avoid:** Ensure the Dockerfile copies `frontend/out/` to `/app/static/` in the container. Test by hitting `http://localhost:8000/` after container start.
**Warning signs:** 404 on root URL, "No static directory found" in logs. [VERIFIED: codebase]

### Pitfall 2: DB_PATH Not Set in Container
**What goes wrong:** SQLite file created in wrong location, data not persisted across restarts.
**Why it happens:** Default `DB_PATH` is `./db/finally.db` relative to CWD. Container CWD must be `/app` for this to resolve to `/app/db/finally.db`.
**How to avoid:** Set `WORKDIR /app` in final Docker stage. Volume mount at `/app/db`. [VERIFIED: codebase]

### Pitfall 3: Frontend Build Fails on Next.js Static Export
**What goes wrong:** `npm run build` fails because of API calls during build or dynamic routes.
**Why it happens:** Static export cannot use server-side features.
**How to avoid:** Next.js config already has `output: 'export'` and `images: { unoptimized: true }`. Build should work as-is. [VERIFIED: codebase - next.config.ts]

### Pitfall 4: Playwright Tests Flaky Due to SSE Timing
**What goes wrong:** Tests assert on price data before the SSE stream has delivered any updates.
**Why it happens:** SSE events take ~500ms to start flowing; test may run before first event.
**How to avoid:** Use Playwright's `waitForSelector` or `toBeVisible` with appropriate timeouts. Wait for price elements to have non-empty content.
**Warning signs:** Tests pass locally but fail in CI. [ASSUMED]

### Pitfall 5: uv sync Fails in Docker
**What goes wrong:** `uv sync` in Docker cannot resolve or install packages.
**Why it happens:** Missing `uv.lock` file, or wrong Python version in base image.
**How to avoid:** Copy both `pyproject.toml` and `uv.lock` before running `uv sync --frozen`. Use `python:3.12-slim` to match the project's Python requirement. [VERIFIED: pyproject.toml requires-python >= 3.12]

### Pitfall 6: Existing Tests Already Cover Most Requirements
**What goes wrong:** Duplicate test effort writing tests that already exist.
**Why it happens:** Not checking existing test files before planning.
**How to avoid:** The backend already has extensive tests: `tests/market/` (7 files), `test_portfolio.py`, `test_watchlist.py`, `test_chat.py`. New test work should focus on gaps, not rewriting. [VERIFIED: codebase]

## Code Examples

### Existing Test Pattern (follow this for new tests)
```python
# Source: backend/tests/test_portfolio.py [VERIFIED: codebase]
import os
import tempfile
import pytest
from httpx import ASGITransport, AsyncClient

_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")

from app.db.schema import init_db
from app.main import app

_initialized = False

async def _ensure_init():
    global _initialized
    if not _initialized:
        await init_db()
        _initialized = True

@pytest.fixture
async def client():
    await _ensure_init()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

### Vitest Config for Next.js Frontend
```typescript
// Source: standard Vitest + React Testing Library pattern [ASSUMED]
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
    include: ['src/**/*.test.{ts,tsx}'],
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
});
```

### Playwright Config for E2E
```typescript
// Source: standard Playwright config pattern [ASSUMED]
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  retries: 1,
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:8000',
    trace: 'on-first-retry',
  },
});
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Jest for React testing | Vitest preferred for Vite/modern projects | 2023-2024 | Faster, native ESM support [ASSUMED] |
| docker-compose v1 | docker compose v2 (plugin) | 2023 | Use `docker compose` not `docker-compose` [ASSUMED] |
| COPY --from=astral-sh/uv | COPY --from=ghcr.io/astral-sh/uv:latest | Current | Official uv Docker image for multi-stage builds [ASSUMED] |

## Existing Test Coverage Inventory

This is critical for planning -- these tests already exist and satisfy requirements:

| Requirement | Test File | Status |
|-------------|-----------|--------|
| TEST-01 (market data) | `tests/market/test_simulator.py`, `test_cache.py`, `test_factory.py`, `test_massive.py`, `test_models.py`, `test_stream.py`, `test_simulator_source.py` | **EXISTS** [VERIFIED: codebase] |
| TEST-02 (portfolio) | `tests/test_portfolio.py` (13+ tests covering PORT-01 through PORT-08) | **EXISTS** [VERIFIED: codebase] |
| TEST-03 (LLM/chat) | `tests/test_chat.py` (15+ tests covering CHAT-01 through CHAT-09) | **EXISTS** [VERIFIED: codebase] |
| TEST-04 (API routes) | `tests/test_watchlist.py` covers watchlist routes; portfolio and chat routes covered in their test files; health endpoint **UNTESTED** | **PARTIAL** [VERIFIED: codebase] |
| TEST-05 (frontend) | No test files exist in `frontend/src/` | **MISSING** [VERIFIED: codebase] |
| TEST-06 (E2E) | `test/` directory contains only `node_modules` | **MISSING** [VERIFIED: codebase] |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Vitest is the best test runner for this Next.js 16 + React 19 stack | Standard Stack | Low -- Jest would also work, slightly different config |
| A2 | Playwright v1.52+ Docker image works with the test setup | Architecture Patterns | Medium -- may need version adjustment |
| A3 | `uv run uvicorn` works in Docker with `--no-dev` | Architecture Patterns | Medium -- may need `uv run --no-dev` or direct uvicorn path |
| A4 | `COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv` is the current install pattern | Code Examples | Low -- well documented approach |
| A5 | Frontend static export at `frontend/out/` is the correct build output path | Architecture Patterns | Low -- verified `output: 'export'` in next.config.ts, `out/` directory exists |

## Open Questions (RESOLVED)

1. **uv CMD syntax in Docker** (RESOLVED)
   - What we know: uv manages the backend deps and venv
   - Resolution: Use `uv run uvicorn app.main:app` — uv resolves the venv automatically. The `--no-dev` flag is not needed since uvicorn is a production dep. If this fails in Docker, fallback to direct venv path `/app/backend/.venv/bin/uvicorn app.main:app`.

2. **Frontend test scope for TEST-05** (RESOLVED)
   - What we know: 15 components exist in `frontend/src/components/`, plus 2 hooks, 3 stores
   - Resolution: Test 4 logic-heavy components: PriceCell (flash animation), TradeBar (form validation), ChatMessage (rendering), Header (value display). Skip pure layout components.

3. **E2E test scope for TEST-06** (RESOLVED)
   - What we know: Plan specifies core user flows with LLM_MOCK=true
   - Resolution: 4 spec files covering success criteria flows: smoke test (app loads, prices stream), watchlist CRUD, buy/sell trades with portfolio update, AI chat with mock responses.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | INFRA-01, INFRA-03, TEST-06 | Yes | 29.2.1 | -- |
| Docker daemon | INFRA-01 | Yes | Running | -- |
| Node.js | Frontend build (in Docker) | Yes (host: v20.13.1) | 20-slim in Docker | -- |
| Python 3.12 | Backend runtime | Yes (venv: 3.12.13) | 3.12-slim in Docker | -- |
| uv | Backend deps | Yes (host: 0.10.12) | Install in Docker | -- |
| Playwright | TEST-06 | No (not installed globally) | Install in test/ | -- |
| Vitest | TEST-05 | No (not in package.json) | Install as devDep | -- |

**Missing dependencies with no fallback:** None -- all can be installed.

**Missing dependencies with fallback:** None needed -- standard npm/pip installs.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Backend Framework | pytest 8.3+ with pytest-asyncio (auto mode) |
| Backend Config | `backend/pyproject.toml` [tool.pytest.ini_options] |
| Backend Quick Run | `cd backend && uv run --extra dev pytest -x -q` |
| Backend Full Suite | `cd backend && uv run --extra dev pytest -v --cov=app` |
| Frontend Framework | Vitest (to be installed) |
| Frontend Quick Run | `cd frontend && npx vitest run --reporter=verbose` |
| E2E Framework | Playwright (to be installed) |
| E2E Run | `cd test && docker compose -f docker-compose.test.yml up --abort-on-container-exit` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | Docker build succeeds | smoke | `docker build -t finally .` | N/A (Dockerfile) |
| INFRA-02 | Frontend + API on port 8000 | E2E | Playwright smoke test | Wave 0 |
| INFRA-03 | SQLite persists via volume | E2E | Playwright or manual verify | Wave 0 |
| INFRA-04 | Start/stop scripts idempotent | smoke | `bash scripts/start_mac.sh && bash scripts/start_mac.sh` | Wave 0 |
| TEST-01 | Market data tests pass | unit | `cd backend && uv run --extra dev pytest tests/market/ -x` | YES |
| TEST-02 | Portfolio tests pass | unit | `cd backend && uv run --extra dev pytest tests/test_portfolio.py -x` | YES |
| TEST-03 | LLM tests pass | unit | `cd backend && uv run --extra dev pytest tests/test_chat.py -x` | YES |
| TEST-04 | API route tests pass | unit | `cd backend && uv run --extra dev pytest tests/ -x` | PARTIAL (missing health) |
| TEST-05 | Frontend component tests pass | unit | `cd frontend && npx vitest run` | Wave 0 |
| TEST-06 | E2E Playwright tests pass | E2E | `cd test && docker compose -f docker-compose.test.yml up --abort-on-container-exit` | Wave 0 |

### Wave 0 Gaps

- [ ] `frontend/vitest.config.ts` -- Vitest configuration
- [ ] `frontend/src/test/setup.ts` -- test setup (jsdom, matchers)
- [ ] `test/docker-compose.test.yml` -- E2E test infrastructure
- [ ] `test/playwright.config.ts` -- Playwright configuration
- [ ] `test/package.json` -- Playwright + dependencies
- [ ] `backend/tests/test_health.py` -- health endpoint test (fills TEST-04 gap)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Single-user app, no auth |
| V3 Session Management | No | No sessions |
| V4 Access Control | No | No auth |
| V5 Input Validation | Yes (existing) | Pydantic models on all API inputs [VERIFIED: codebase] |
| V6 Cryptography | No | No crypto operations |

### Known Threat Patterns for Docker

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secrets in Docker image | Information Disclosure | Use `--env-file` at runtime, never COPY .env [ASSUMED] |
| Running as root in container | Elevation of Privilege | Add non-root USER in Dockerfile [ASSUMED] |
| Exposed debug ports | Information Disclosure | Only expose port 8000 [ASSUMED] |

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `backend/pyproject.toml`, `frontend/package.json`, `backend/app/main.py`, `backend/app/db/connection.py`, `frontend/next.config.ts`
- Existing test files: `backend/tests/` (all files inspected)
- Docker daemon: verified running, version 29.2.1

### Secondary (MEDIUM confidence)
- Docker multi-stage build patterns (well-established practice)
- uv Docker installation via ghcr.io image

### Tertiary (LOW confidence)
- Vitest + React Testing Library configuration for Next.js 16 (assumed based on general patterns)
- Playwright Docker image version (assumed v1.52.0)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all backend deps verified in pyproject.toml; frontend deps verified in package.json
- Architecture (Dockerfile): HIGH -- all paths verified against codebase
- Architecture (E2E): MEDIUM -- standard patterns but untested against this specific app
- Pitfalls: HIGH -- all critical paths verified against source code
- Test gaps: HIGH -- every existing test file inspected

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stable infrastructure patterns)
