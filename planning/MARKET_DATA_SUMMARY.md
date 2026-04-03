# Market Data Backend — Summary

**Status:** Complete, tested, reviewed, all issues resolved.

## What Was Built

A complete market data subsystem in `backend/app/market/` (8 modules, ~500 lines) providing live price simulation and real market data via a unified interface.

### Architecture

```
MarketDataSource (ABC)
├── SimulatorDataSource  →  GBM simulator (default, no API key needed)
└── MassiveDataSource    →  Polygon.io REST poller (when MASSIVE_API_KEY set)
        │
        ▼
   PriceCache (thread-safe, in-memory)
        │
        ├──→ SSE stream endpoint (/api/stream/prices)
        ├──→ Portfolio valuation
        └──→ Trade execution
```

### Modules

| File | Purpose |
|------|---------|
| `models.py` | `PriceUpdate` — immutable frozen dataclass (ticker, price, previous_price, timestamp, change, direction) |
| `interface.py` | `MarketDataSource` — abstract base class defining `start/stop/add_ticker/remove_ticker/get_tickers` |
| `cache.py` | `PriceCache` — thread-safe price store with version counter for SSE change detection |
| `seed_prices.py` | Realistic seed prices, per-ticker GBM params (drift/volatility), correlation groups |
| `simulator.py` | `GBMSimulator` (Geometric Brownian Motion with Cholesky-correlated moves) + `SimulatorDataSource` |
| `massive_client.py` | `MassiveDataSource` — REST polling client for Polygon.io via the `massive` package |
| `factory.py` | `create_market_data_source()` — selects simulator or Massive based on `MASSIVE_API_KEY` env var |
| `stream.py` | `create_stream_router()` — FastAPI SSE endpoint factory using version-based change detection |

### Key Design Decisions

- **Strategy pattern** — both data sources implement the same ABC; downstream code is source-agnostic
- **PriceCache as single point of truth** — producers write, consumers read; no direct coupling
- **GBM with correlated moves** — Cholesky decomposition of sector-based correlation matrix; tech stocks correlate at 0.6, finance at 0.5, cross-sector at 0.3
- **Random shock events** — ~0.1% chance per tick per ticker of a 2-5% move for visual drama
- **SSE over WebSockets** — simpler, one-way push, universal browser support

## Test Suite

**100 tests, all passing.** 7 test modules in `backend/tests/market/`.

| Module | Tests | Coverage |
|--------|-------|----------|
| test_models.py | 13 | models.py: 100% |
| test_cache.py | 18 | cache.py: 100% |
| test_simulator.py | 19 | simulator.py: 95% |
| test_simulator_source.py | 12 | (integration tests) |
| test_factory.py | 7 | factory.py: 100% |
| test_massive.py | 20 | massive_client.py: 94% |
| test_stream.py | 14 | stream.py: 90% |

Overall market package coverage: ~96%.

## Code Review & Fixes Applied

A comprehensive code review identified and resolved all issues:

**Round 1 (initial build):**
1. **pyproject.toml build config** — added `[tool.hatch.build.targets.wheel] packages = ["app"]`
2. **Lazy imports removed** — `massive` is a core dependency; imports moved to top level
3. **SSE return type fixed** — `_generate_events` annotated as `AsyncGenerator[str, None]`
4. **Public `get_tickers()`** — added to `GBMSimulator` to avoid private attribute access
5. **Correlation constants cleaned up** — removed unused `DEFAULT_CORR`, consolidated into `CROSS_GROUP_CORR`
6. **Unused test imports removed** — `pytest`, `math`, `asyncio` cleaned from 4 test files
7. **Massive test mocks fixed** — `source._client` set in tests, patches target correct names

**Round 2 (post-review):**
8. **Stream router factory** (Bug #3) — moved `APIRouter()` creation inside `create_stream_router()` so each call returns a fresh router
9. **Cholesky crash guard** (Bug #2) — `np.linalg.cholesky()` wrapped in try/except with identity-matrix fallback
10. **Duplicate `_iso_now()` removed** (QC-2) — `cache.py` now imports `_iso_now` from `models.py`
11. **`version` property lock-safe** (QC-4) — acquires `self._lock` before reading `_version`
12. **MassiveDataSource snapshot callback** (P4) — accepts `snapshot_callback` constructor param; fires it after each poll cycle
13. **Explicit `session_open_price`** (Bug #1) — `MassiveDataSource._poll_once()` explicitly passes `session_open_price=price` matching the simulator
14. **Factory reads `MARKET_POLL_INTERVAL_SECONDS`** (P9) — Massive poller respects env var (default 15s)
15. **`snapshot_callback` via factory** (P4) — `create_market_data_source()` accepts and threads `snapshot_callback` to both sources; `main.py` no longer uses private attribute injection
16. **CLAUDE.md direction value** (P5) — `"flat"` corrected to `"unchanged"`
17. **Unused `event_loop_policy` fixture removed** (Bug #4) — `tests/conftest.py` cleaned up
18. **Private `_tickers` test assertion** (P10) — replaced `sim._tickers` with `sim.get_tickers()`
19. **SSE tests added** (M1) — new `test_stream.py` covers retry directive, payload fields, version dedup, disconnect, empty cache, multi-ticker, and router factory isolation
20. **Snapshot callback tests added** (M2, M3) — added to `test_simulator_source.py` and `test_massive.py`

## Demo

A Rich terminal demo is available at `backend/market_data_demo.py`:

```bash
cd backend
uv run market_data_demo.py
```

Displays a live-updating dashboard with all 10 tickers, sparklines, color-coded direction arrows, and an event log for notable price moves. Runs 60 seconds or until Ctrl+C.

## Usage for Downstream Code

```python
from app.market import PriceCache, create_market_data_source

# Startup
cache = PriceCache()
source = create_market_data_source(cache)  # Reads MASSIVE_API_KEY
await source.start(["AAPL", "GOOGL", "MSFT", ...])

# Read prices
update = cache.get("AAPL")          # PriceUpdate or None
price = cache.get_price("AAPL")     # float or None
all_prices = cache.get_all()        # dict[str, PriceUpdate]

# Dynamic watchlist
await source.add_ticker("TSLA")
await source.remove_ticker("GOOGL")

# Shutdown
await source.stop()
```
