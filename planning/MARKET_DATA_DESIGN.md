# Market Data Backend — Implementation Design

This document is the authoritative implementation guide for all market data functionality in FinAlly. It covers the shared price cache contract, the abstract provider interface, the GBM simulator, the Massive (Polygon.io) REST API client, and the SSE streaming endpoint. All code here is ready to implement directly.

---

## 1. Directory Structure

```
backend/
└── market/
    ├── __init__.py           # Exports: price_cache, create_market_provider
    ├── types.py              # PriceEntry TypedDict
    ├── cache.py              # Shared price_cache dict (module-level singleton)
    ├── base.py               # MarketDataProvider ABC
    ├── factory.py            # Provider selection via env vars
    ├── simulator_config.py   # Seed prices, sigmas, betas, GBM constants
    ├── simulator_engine.py   # GBM loop: run_simulator()
    ├── simulator.py          # SimulatorProvider (adapter wrapping engine)
    ├── massive_client.py     # Async HTTP client + snapshot parser
    ├── massive_poller.py     # Poll loop feeding price_cache
    └── massive_provider.py   # MassiveProvider (adapter wrapping poller)
```

The `market/` package is the only place in the backend that writes to `price_cache`. Everything else (SSE endpoint, watchlist API, portfolio API) reads from it.

---

## 2. Shared Types

```python
# backend/market/types.py
from typing import TypedDict


class PriceEntry(TypedDict):
    ticker: str
    price: float               # Current price (2 decimal places)
    previous_price: float      # Price at the previous tick/poll
    session_open_price: float  # First price of the session (never overwritten)
    timestamp: str             # ISO 8601 UTC string, e.g. "2026-04-01T14:32:00.000000+00:00"
    change_direction: str      # "up" | "down" | "unchanged"
```

**`change_direction` values:**

| Value | Meaning |
|---|---|
| `"up"` | `price > previous_price` |
| `"down"` | `price < previous_price` |
| `"unchanged"` | `price == previous_price`, or first tick for this ticker |

On the very first tick for a new ticker, `previous_price` is initialized to the current price, so `change_direction` is `"unchanged"`.

**`session_open_price` semantics:**
- Set **once** per ticker per process lifetime — on the first tick or poll.
- Simulator: set to the configured `seed` price from `TICKER_CONFIG`.
- Massive: set to `day.o` (today's market open) from the first snapshot.
- Survives watchlist removes and re-adds within the same process.
- Used by the frontend to compute the session % change shown in the watchlist panel.
- Different from `previous_price`, which changes every tick and drives flash animations.

---

## 3. Price Cache

```python
# backend/market/cache.py

from .types import PriceEntry

# Single shared price cache. One background task writes; SSE handlers read.
# No lock needed: Python's GIL makes individual dict key assignments atomic.
# The background task is the sole writer; SSE generators are readers only.
price_cache: dict[str, PriceEntry] = {}
```

The cache only holds tickers currently in the watchlist. When a ticker is removed from the watchlist, the background task prunes its entry from the cache on the next tick. When a ticker is added, it appears in the cache after the next tick.

---

## 4. Abstract Interface

```python
# backend/market/base.py
from abc import ABC, abstractmethod


class MarketDataProvider(ABC):
    """
    Abstract base for market data providers.

    Both SimulatorProvider and MassiveProvider implement this interface.
    The FastAPI lifespan event calls start() at startup and stop() at shutdown.
    Providers write to market.cache.price_cache; they do not return data directly.
    """

    @abstractmethod
    async def start(self) -> None:
        """
        Launch the background data task.
        Called once during FastAPI lifespan startup.
        Must return immediately — the implementation creates an asyncio.Task internally.
        """
        ...

    @abstractmethod
    async def stop(self) -> None:
        """
        Cancel the background data task and clean up resources.
        Called during FastAPI lifespan shutdown.
        Must await task cancellation before returning.
        """
        ...
```

---

## 5. Factory Function

The factory reads environment variables and constructs the correct provider. All other code uses the returned `MarketDataProvider` without knowing which implementation is active.

```python
# backend/market/factory.py
import os

from .base import MarketDataProvider
from .simulator import SimulatorProvider
from .massive_provider import MassiveProvider


def create_market_provider() -> MarketDataProvider:
    """
    Select and instantiate the market data provider.

    Decision logic:
    - MASSIVE_API_KEY set and non-empty  →  MassiveProvider
    - Otherwise                          →  SimulatorProvider (default)
    """
    api_key = os.getenv("MASSIVE_API_KEY", "").strip()
    if api_key:
        interval = int(os.getenv("MARKET_POLL_INTERVAL_SECONDS", "15"))
        return MassiveProvider(api_key=api_key, interval_seconds=interval)
    return SimulatorProvider()
```

---

## 6. FastAPI Integration

The provider is created at module load time and started/stopped via the FastAPI lifespan context manager.

```python
# backend/main.py (relevant excerpt)
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .market.factory import create_market_provider

_provider = create_market_provider()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: launch market data background task
    await _provider.start()
    yield
    # Shutdown: cancel background task and release resources
    await _provider.stop()


app = FastAPI(lifespan=lifespan)
```

---

## 7. Simulator

### 7.1 Configuration

All simulation parameters are centralized in one file. Adjust these to tune visual behavior.

```python
# backend/market/simulator_config.py

TICKER_CONFIG: dict[str, dict] = {
    #          seed price   annualized vol   market beta
    "AAPL":  {"seed": 190.00, "sigma": 0.25, "beta": 0.85},
    "GOOGL": {"seed": 175.00, "sigma": 0.28, "beta": 0.80},
    "MSFT":  {"seed": 415.00, "sigma": 0.22, "beta": 0.82},
    "AMZN":  {"seed": 185.00, "sigma": 0.30, "beta": 0.78},
    "TSLA":  {"seed": 245.00, "sigma": 0.55, "beta": 0.75},
    "NVDA":  {"seed": 875.00, "sigma": 0.45, "beta": 0.90},
    "META":  {"seed": 520.00, "sigma": 0.32, "beta": 0.80},
    "JPM":   {"seed": 205.00, "sigma": 0.20, "beta": 0.65},
    "V":     {"seed": 280.00, "sigma": 0.18, "beta": 0.60},
    "NFLX":  {"seed": 625.00, "sigma": 0.38, "beta": 0.70},
}

# Annualized drift. Negligible at 500ms tick interval; included for mathematical
# correctness. Do not set above ~0.10 or prices will visibly trend upward.
ANNUAL_DRIFT: float = 0.05

# Time step expressed as a fraction of a trading year.
# 252 trading days × 6.5 trading hours × 3600 seconds ≈ 5,896,800 seconds/year.
SECONDS_PER_TRADING_YEAR: float = 252 * 6.5 * 3600
TICK_INTERVAL_SECONDS: float = 0.5
DT: float = TICK_INTERVAL_SECONDS / SECONDS_PER_TRADING_YEAR  # ≈ 8.48e-8

# Random event parameters (sudden 2–5% moves for visual drama)
EVENT_PROBABILITY: float = 0.002   # 0.2% per ticker per tick ≈ 1 event per ~8 min
EVENT_MIN_MOVE: float = 0.02       # 2% minimum magnitude
EVENT_MAX_MOVE: float = 0.05       # 5% maximum magnitude

# How many ticks between portfolio value snapshots (S4 optimization from PLAN.md §13)
# 60 ticks × 0.5s = 30 seconds between snapshots
SNAPSHOT_EVERY_N_TICKS: int = 60

# Default config for tickers added dynamically (not in TICKER_CONFIG)
DEFAULT_TICKER_CONFIG: dict = {"seed": 100.0, "sigma": 0.30, "beta": 0.70}
```

**Configuration reference:**

| Constant | Default | Effect |
|---|---|---|
| `ANNUAL_DRIFT` | `0.05` | Long-run upward drift; negligible at intraday timescales |
| `TICK_INTERVAL_SECONDS` | `0.5` | Price update frequency; also sets SSE heartbeat cadence |
| `EVENT_PROBABILITY` | `0.002` | Fraction of ticks that trigger a sudden move |
| `EVENT_MIN_MOVE` | `0.02` | Minimum sudden-event magnitude (2%) |
| `EVENT_MAX_MOVE` | `0.05` | Maximum sudden-event magnitude (5%) |
| Per-ticker `sigma` | varies | Annualized volatility; higher = more movement per tick |
| Per-ticker `beta` | varies | Market correlation (0 = uncorrelated, 1 = perfectly correlated) |
| Per-ticker `seed` | varies | Starting price; also the `session_open_price` for the session |

### 7.2 Mathematical Foundation

**Geometric Brownian Motion (GBM):**

```
S(t+dt) = S(t) × exp((μ - σ²/2) × dt + σ × √dt × Z)
```

Where `μ` is annual drift, `σ` is annual volatility, `dt` is the time step in years, and `Z ~ N(0,1)`.

At 500ms ticks, `dt ≈ 8.5e-8` years — the drift term `(μ - σ²/2) × dt` is ~4e-9, essentially zero. Price motion is almost entirely driven by the volatility term `σ × √dt × Z`. This is correct: intraday prices look like random walks.

**Correlated moves (sector coherence):**

Each tick generates a market-wide shock `Z_market ~ N(0,1)` shared across all tickers, and an idiosyncratic shock `Z_idio ~ N(0,1)` unique to each ticker. The combined shock for ticker `i`:

```
Z_i = β_i × Z_market + √(1 - β_i²) × Z_idio
```

Beta controls market sensitivity. Tech stocks (beta ~0.8–0.9) move together; defensive stocks like V and JPM (beta ~0.6) are more independent.

### 7.3 Simulator Engine

```python
# backend/market/simulator_engine.py
import asyncio
import math
import random
import logging
from collections.abc import Callable, Awaitable
from datetime import datetime, timezone

from .simulator_config import (
    TICKER_CONFIG,
    ANNUAL_DRIFT,
    DT,
    TICK_INTERVAL_SECONDS,
    EVENT_PROBABILITY,
    EVENT_MIN_MOVE,
    EVENT_MAX_MOVE,
    SNAPSHOT_EVERY_N_TICKS,
    DEFAULT_TICKER_CONFIG,
)
from .types import PriceEntry

logger = logging.getLogger(__name__)


def _gbm_step(price: float, sigma: float, z: float) -> float:
    """
    Advance a price by one GBM tick using the provided standard normal variate.
    Separated from random number generation to enable deterministic testing.
    """
    log_return = (ANNUAL_DRIFT - 0.5 * sigma ** 2) * DT + sigma * math.sqrt(DT) * z
    return price * math.exp(log_return)


def _maybe_event(price: float) -> float:
    """
    Apply a random sudden move (2–5%) with EVENT_PROBABILITY chance.
    Direction is random. Returns the (possibly unchanged) price.
    """
    if random.random() < EVENT_PROBABILITY:
        move_pct = random.uniform(EVENT_MIN_MOVE, EVENT_MAX_MOVE)
        direction = 1 if random.random() > 0.5 else -1
        price *= 1 + direction * move_pct
        logger.debug("Random event: %+.1f%% move applied", direction * move_pct * 100)
    return price


async def run_simulator(
    price_cache: dict[str, PriceEntry],
    get_watchlist: Callable[[], Awaitable[list[str]]] | None = None,
    record_snapshot: Callable[[], Awaitable[None]] | None = None,
) -> None:
    """
    Main GBM simulation loop. Runs until cancelled.

    Args:
        price_cache:     Shared dict written by this task, read by SSE handlers.
        get_watchlist:   Async callable returning list of active ticker strings.
                         If None, simulates all tickers in TICKER_CONFIG.
        record_snapshot: Async callable to write a portfolio snapshot to the DB.
                         Called every SNAPSHOT_EVERY_N_TICKS ticks (S4 optimization).
                         If None, snapshot recording is skipped.
    """
    # Internal price state — persists across ticks regardless of watchlist changes
    current_prices: dict[str, float] = {
        ticker: cfg["seed"] for ticker, cfg in TICKER_CONFIG.items()
    }
    # Session open prices — set once, never overwritten
    session_opens: dict[str, float] = dict(current_prices)
    tick = 0

    while True:
        await asyncio.sleep(TICK_INTERVAL_SECONDS)
        tick += 1

        # --- Determine active tickers ---
        if get_watchlist is not None:
            try:
                watchlist = await get_watchlist()
            except Exception as exc:
                logger.warning("get_watchlist failed: %s — using previous set", exc)
                watchlist = list(current_prices.keys())
        else:
            watchlist = list(TICKER_CONFIG.keys())

        if not watchlist:
            continue

        # --- Generate market-wide shock for correlated moves ---
        z_market = random.gauss(0.0, 1.0)
        timestamp = datetime.now(tz=timezone.utc).isoformat()

        for ticker in watchlist:
            cfg = TICKER_CONFIG.get(ticker, DEFAULT_TICKER_CONFIG)

            # Initialize unknown tickers (user-added) on first appearance
            if ticker not in current_prices:
                current_prices[ticker] = cfg["seed"]
                session_opens[ticker] = cfg["seed"]

            sigma = cfg["sigma"]
            beta = cfg["beta"]
            old_price = current_prices[ticker]

            # Correlated GBM step
            z_idio = random.gauss(0.0, 1.0)
            z_combined = beta * z_market + math.sqrt(1 - beta ** 2) * z_idio
            new_price = _gbm_step(old_price, sigma, z_combined)

            # Apply optional random event
            new_price = _maybe_event(new_price)

            # Floor at $0.01; round to cents
            new_price = round(max(new_price, 0.01), 2)

            # Determine change direction
            if new_price > old_price:
                direction = "up"
            elif new_price < old_price:
                direction = "down"
            else:
                direction = "unchanged"

            current_prices[ticker] = new_price
            price_cache[ticker] = PriceEntry(
                ticker=ticker,
                price=new_price,
                previous_price=old_price,
                session_open_price=session_opens[ticker],
                timestamp=timestamp,
                change_direction=direction,
            )

        # --- Prune tickers removed from watchlist ---
        active_set = set(watchlist)
        for stale in set(price_cache) - active_set:
            del price_cache[stale]
            logger.debug("Pruned stale ticker %s from price_cache", stale)

        # --- Portfolio snapshot (S4 optimization: folded into simulator loop) ---
        if record_snapshot is not None and tick % SNAPSHOT_EVERY_N_TICKS == 0:
            try:
                await record_snapshot()
            except Exception as exc:
                logger.warning("Portfolio snapshot failed: %s", exc)
```

### 7.4 Simulator Provider (Adapter)

```python
# backend/market/simulator.py
import asyncio

from .base import MarketDataProvider
from .cache import price_cache
from .simulator_engine import run_simulator


class SimulatorProvider(MarketDataProvider):
    """Wraps run_simulator() as a MarketDataProvider."""

    def __init__(self):
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        # Import here to avoid circular imports at module load time
        from ..db import get_watchlist_tickers, record_portfolio_snapshot

        self._task = asyncio.create_task(
            run_simulator(
                price_cache,
                get_watchlist=get_watchlist_tickers,
                record_snapshot=record_portfolio_snapshot,
            ),
            name="market-simulator",
        )

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
```

---

## 8. Massive (Polygon.io) API Client

### 8.1 HTTP Client

```python
# backend/market/massive_client.py
import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.polygon.io"


class MassiveClient:
    """
    Async HTTP client for the Massive (Polygon.io) REST API.
    Authentication uses the apiKey query parameter on every request.
    """

    def __init__(self, api_key: str, timeout: float = 10.0):
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=timeout)

    async def get_snapshots(self, tickers: list[str]) -> dict:
        """
        Fetch latest price snapshots for a batch of tickers.
        Uses GET /v2/snapshot/locale/us/markets/stocks/tickers.

        Returns the raw API response dict.
        Raises httpx.HTTPStatusError on non-2xx responses.
        """
        url = f"{BASE_URL}/v2/snapshot/locale/us/markets/stocks/tickers"
        params = {
            "tickers": ",".join(tickers),
            "apiKey": self.api_key,
        }
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def aclose(self) -> None:
        await self._client.aclose()
```

### 8.2 Response Parser

The Massive snapshot response uses nested fields. This parser extracts the fields FinAlly needs and updates `price_cache` in place.

**Snapshot response shape (relevant fields):**
```json
{
  "status": "OK",
  "tickers": [
    {
      "ticker": "AAPL",
      "updated": 1640995200000,
      "lastTrade": { "p": 178.52 },
      "day":      { "o": 177.09, "c": 178.52 },
      "prevDay":  { "c": 177.09 }
    }
  ]
}
```

**Price field priority:**
- `lastTrade.p` — most recent trade price; best during market hours.
- `day.c` — today's session close/current price; use when `lastTrade` is absent or stale (after-hours, pre-market).
- `prevDay.c` — previous day's close; used as `previous_price` on the very first poll before any prior cache entry exists.

```python
# backend/market/massive_client.py (continued)

from .types import PriceEntry


def _extract_price(snapshot: dict) -> float:
    """
    Extract the best current price from a single ticker snapshot.
    Prefers lastTrade.p over day.c; falls back to 0.0 if neither is present.
    """
    last_trade = snapshot.get("lastTrade") or {}
    day = snapshot.get("day") or {}
    return float(last_trade.get("p") or day.get("c") or 0.0)


def parse_snapshots(
    raw: dict,
    session_opens: dict[str, float],
    price_cache: dict[str, PriceEntry],
) -> None:
    """
    Parse a raw Massive snapshot response and update price_cache in place.

    Args:
        raw:           Raw JSON dict from get_snapshots().
        session_opens: Mapping of ticker → session open price.
                       Populated on first poll per ticker; never overwritten.
        price_cache:   Shared dict to update in place.
    """
    for snapshot in raw.get("tickers", []):
        ticker = snapshot.get("ticker")
        if not ticker:
            continue

        price = _extract_price(snapshot)
        if price <= 0:
            logger.warning("No valid price for %s in snapshot — skipping", ticker)
            continue

        # previous_price: last known cache value, or prevDay.c on first poll
        prev_day = snapshot.get("prevDay") or {}
        existing = price_cache.get(ticker)
        previous_price = existing["price"] if existing else float(prev_day.get("c", price))

        # session_open_price: set once from day.o, never overwritten
        if ticker not in session_opens:
            day = snapshot.get("day") or {}
            session_opens[ticker] = float(day.get("o") or price)
        session_open_price = session_opens[ticker]

        # change_direction vs. previous cache entry
        if price > previous_price:
            direction = "up"
        elif price < previous_price:
            direction = "down"
        else:
            direction = "unchanged"

        # Timestamp from the snapshot's updated field (Unix ms)
        updated_ms = snapshot.get("updated", 0)
        if updated_ms:
            timestamp = datetime.fromtimestamp(
                updated_ms / 1000, tz=timezone.utc
            ).isoformat()
        else:
            timestamp = datetime.now(tz=timezone.utc).isoformat()

        price_cache[ticker] = PriceEntry(
            ticker=ticker,
            price=round(price, 2),
            previous_price=round(previous_price, 2),
            session_open_price=round(session_open_price, 2),
            timestamp=timestamp,
            change_direction=direction,
        )
```

### 8.3 Poll Loop

```python
# backend/market/massive_poller.py
import asyncio
import logging
from collections.abc import Callable, Awaitable

import httpx

from .massive_client import MassiveClient, parse_snapshots
from .types import PriceEntry

logger = logging.getLogger(__name__)


async def massive_poll_loop(
    api_key: str,
    get_watchlist: Callable[[], Awaitable[list[str]]],
    price_cache: dict[str, PriceEntry],
    interval_seconds: int = 15,
) -> None:
    """
    Background polling loop. Fetches Massive snapshots on a fixed interval
    and writes results to price_cache. Runs until cancelled.

    Args:
        api_key:          Massive/Polygon.io API key.
        get_watchlist:    Async callable returning current watchlist tickers.
        price_cache:      Shared dict to update in place.
        interval_seconds: Poll interval (default 15s; free tier limit is ~4 req/min).
    """
    client = MassiveClient(api_key)
    session_opens: dict[str, float] = {}

    try:
        while True:
            tickers = await get_watchlist()
            if not tickers:
                await asyncio.sleep(interval_seconds)
                continue

            try:
                raw = await client.get_snapshots(tickers)
                parse_snapshots(raw, session_opens, price_cache)

                # Prune tickers removed from watchlist
                active_set = set(tickers)
                for stale in set(price_cache) - active_set:
                    del price_cache[stale]
                    session_opens.pop(stale, None)
                    logger.debug("Pruned stale ticker %s from price_cache", stale)

                logger.debug("Polled %d tickers from Massive API", len(tickers))

            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 429:
                    retry_after = int(exc.response.headers.get("Retry-After", 60))
                    logger.warning("Rate limited by Massive API; sleeping %ds", retry_after)
                    await asyncio.sleep(retry_after)
                    continue  # skip the normal sleep below
                elif status == 403:
                    logger.error("Massive API key is invalid or forbidden. Stopping poller.")
                    return  # Fatal — do not retry
                elif status == 404:
                    logger.warning("Massive API 404 — check ticker format")
                else:
                    logger.error("Massive API HTTP %d: %s", status, exc)

            except httpx.TimeoutException:
                logger.warning("Massive API request timed out")

            except Exception as exc:
                logger.error("Massive API poll error: %s", exc)

            await asyncio.sleep(interval_seconds)

    finally:
        await client.aclose()
```

**Error handling summary:**

| HTTP Status | Action |
|---|---|
| `200 OK` | Parse and update cache |
| `400 Bad Request` | Log error, check ticker format |
| `403 Forbidden` | Log fatal error, stop poller permanently |
| `404 Not Found` | Log warning, continue |
| `429 Too Many Requests` | Read `Retry-After` header, sleep, then continue |
| `5xx` | Log error, retry on next scheduled interval |
| Timeout | Log warning, retry on next scheduled interval |

### 8.4 Massive Provider (Adapter)

```python
# backend/market/massive_provider.py
import asyncio

from .base import MarketDataProvider
from .cache import price_cache
from .massive_poller import massive_poll_loop


class MassiveProvider(MarketDataProvider):
    """Wraps massive_poll_loop() as a MarketDataProvider."""

    def __init__(self, api_key: str, interval_seconds: int = 15):
        self.api_key = api_key
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        from ..db import get_watchlist_tickers

        self._task = asyncio.create_task(
            massive_poll_loop(
                api_key=self.api_key,
                get_watchlist=get_watchlist_tickers,
                price_cache=price_cache,
                interval_seconds=self.interval_seconds,
            ),
            name="massive-poller",
        )

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
```

---

## 9. SSE Streaming Endpoint

The SSE endpoint reads from `price_cache` and pushes updates to all connected clients. It is identical regardless of which provider is active.

```python
# backend/api/stream.py
import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..market.cache import price_cache

router = APIRouter()

SSE_PUSH_INTERVAL = 0.5  # Push every 500ms regardless of provider update cadence


@router.get("/api/stream/prices")
async def stream_prices():
    """
    SSE endpoint. Pushes all tickers in price_cache every 500ms.

    With the simulator: prices change every tick, so every push has new data.
    With Massive (15s poll): the same prices are pushed 30 times between updates.
    The frontend still receives a regular heartbeat confirming the connection is alive;
    change_direction will be "unchanged" between real Massive API updates.

    Clients reconnect automatically via EventSource's built-in retry behavior.
    """
    async def event_generator():
        while True:
            for entry in list(price_cache.values()):
                payload = json.dumps(entry)
                yield f"data: {payload}\n\n"
            await asyncio.sleep(SSE_PUSH_INTERVAL)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Prevent nginx from buffering SSE
        },
    )
```

**SSE event format** (each event is a single `data:` line followed by `\n\n`):
```
data: {"ticker": "AAPL", "price": 189.42, "previous_price": 189.31, "session_open_price": 190.00, "timestamp": "2026-04-01T14:32:00.000000+00:00", "change_direction": "up"}

data: {"ticker": "MSFT", "price": 415.87, "previous_price": 415.91, "session_open_price": 415.00, "timestamp": "2026-04-01T14:32:00.000000+00:00", "change_direction": "down"}

```

---

## 10. Package `__init__.py`

Export the two symbols that the rest of the backend needs.

```python
# backend/market/__init__.py
from .cache import price_cache
from .factory import create_market_provider

__all__ = ["price_cache", "create_market_provider"]
```

---

## 11. DB Helper Signatures

The market providers depend on two async functions from the DB layer. These are implemented in `backend/db/` but their signatures are defined here as the contract.

```python
# Expected signatures in backend/db/__init__.py (or backend/db/queries.py)

async def get_watchlist_tickers() -> list[str]:
    """
    Return the list of ticker strings currently in the watchlist for user "default".
    Called on every simulator tick and every Massive poll.
    Must be fast — reads a small table; a simple SELECT query is fine.
    """
    ...

async def record_portfolio_snapshot() -> None:
    """
    Compute the current total portfolio value (cash + positions × current prices)
    and insert a row into portfolio_snapshots for user "default".
    Called every SNAPSHOT_EVERY_N_TICKS by the simulator (S4 optimization).
    Also called immediately after every manual or AI-executed trade.
    Must not raise — exceptions are caught and logged by the caller.
    """
    ...
```

---

## 12. Behavioral Edge Cases

### Empty watchlist

If `get_watchlist()` returns `[]`, the simulator and Massive poller both skip the tick/poll and sleep until the next interval. `price_cache` remains empty. The SSE endpoint streams no events (the `for` loop over an empty dict is a no-op). The frontend's `EventSource` stays connected and receives no data until a ticker is added.

### Dynamically added tickers

**Simulator:** Any ticker string not in `TICKER_CONFIG` is handled with `DEFAULT_TICKER_CONFIG` (`seed=100.0, sigma=0.30, beta=0.70`). Prices start at $100 and immediately begin GBM simulation. No restart needed.

**Massive:** Any ticker added to the watchlist is included in the next poll's `tickers` parameter. If the ticker is invalid (not on US exchanges), it simply won't appear in the snapshot response. The poller logs a debug message; no error is raised. The ticker will remain absent from `price_cache` until Massive returns data for it.

### After-hours and pre-market (Massive only)

| Market State | Price Source |
|---|---|
| Market open (9:30am–4pm ET) | `lastTrade.p` — most recent trade |
| After market close | `day.c` — today's closing price (stable) |
| Pre-market | `day.c` may not yet be populated; `lastTrade.p` from prior session |

The `_extract_price` function prefers `lastTrade.p` and falls back to `day.c`, which handles all three cases correctly.

### First tick direction

On the very first tick for any ticker, `previous_price` is initialized to the current price (from the cache, which is empty, so it falls back to `prevDay.c` for Massive or the seed price for the simulator). `change_direction` is `"unchanged"` on that first tick.

### Process restart with Massive

On process restart, `session_opens` is reset. The next poll sets a fresh `session_open_price` from `day.o`. Intraday continuity is lost across restarts — this is acceptable given the app is a demo/simulator.

---

## 13. Testing

### Unit: GBM price step

```python
# backend/tests/test_simulator_engine.py
import math
import random
from backend.market.simulator_engine import _gbm_step
from backend.market.simulator_config import DT, ANNUAL_DRIFT


def test_gbm_step_positive_z_increases_price():
    price = 100.0
    new_price = _gbm_step(price, sigma=0.25, z=1.0)
    assert new_price > price


def test_gbm_step_negative_z_decreases_price():
    price = 100.0
    new_price = _gbm_step(price, sigma=0.25, z=-1.0)
    assert new_price < price


def test_gbm_step_never_negative():
    # Even with an extreme negative shock
    price = 0.01
    new_price = _gbm_step(price, sigma=2.0, z=-10.0)
    assert new_price > 0


def test_gbm_step_z_zero_returns_drift_only():
    price = 100.0
    new_price = _gbm_step(price, sigma=0.25, z=0.0)
    expected = price * math.exp((ANNUAL_DRIFT - 0.5 * 0.25**2) * DT)
    assert abs(new_price - expected) < 1e-10
```

### Unit: Simulator writes to cache

```python
# backend/tests/test_simulator_engine.py (continued)
import asyncio
import random
from backend.market.simulator_engine import run_simulator


def test_simulator_writes_all_default_tickers():
    random.seed(42)
    cache = {}

    async def run():
        task = asyncio.create_task(run_simulator(cache, get_watchlist=None))
        await asyncio.sleep(0.6)  # let one tick fire
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(run())

    # All default tickers should be present
    from backend.market.simulator_config import TICKER_CONFIG
    for ticker in TICKER_CONFIG:
        assert ticker in cache, f"{ticker} missing from cache"
        entry = cache[ticker]
        assert entry["price"] > 0
        assert entry["change_direction"] in ("up", "down", "unchanged")
        assert entry["session_open_price"] == TICKER_CONFIG[ticker]["seed"]


def test_simulator_session_open_never_changes():
    random.seed(0)
    cache = {}

    async def run():
        task = asyncio.create_task(run_simulator(cache, get_watchlist=None))
        await asyncio.sleep(2.0)  # let several ticks fire
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(run())

    from backend.market.simulator_config import TICKER_CONFIG
    # session_open_price must equal the seed price throughout the session
    assert cache["AAPL"]["session_open_price"] == TICKER_CONFIG["AAPL"]["seed"]
```

### Unit: Massive snapshot parser

```python
# backend/tests/test_massive_client.py
from backend.market.massive_client import parse_snapshots

SAMPLE_RESPONSE = {
    "status": "OK",
    "tickers": [
        {
            "ticker": "AAPL",
            "updated": 1640995200000,
            "lastTrade": {"p": 178.52},
            "day": {"o": 177.09, "c": 178.52},
            "prevDay": {"c": 177.09},
        }
    ],
}


def test_parse_snapshots_populates_cache():
    session_opens = {}
    cache = {}
    parse_snapshots(SAMPLE_RESPONSE, session_opens, cache)

    assert "AAPL" in cache
    entry = cache["AAPL"]
    assert entry["price"] == 178.52
    assert entry["session_open_price"] == 177.09  # day.o
    assert entry["change_direction"] == "up"       # 178.52 > 177.09


def test_session_open_set_only_once():
    session_opens = {}
    cache = {}
    parse_snapshots(SAMPLE_RESPONSE, session_opens, cache)
    first_open = session_opens["AAPL"]

    # Simulate a second poll where day.o has changed
    modified = {
        "status": "OK",
        "tickers": [{
            **SAMPLE_RESPONSE["tickers"][0],
            "day": {"o": 999.99, "c": 179.00},
            "lastTrade": {"p": 179.00},
        }],
    }
    parse_snapshots(modified, session_opens, cache)

    assert session_opens["AAPL"] == first_open  # unchanged


def test_parse_snapshots_falls_back_to_day_close():
    """When lastTrade is absent, use day.c."""
    response = {
        "status": "OK",
        "tickers": [{"ticker": "TEST", "day": {"o": 50.0, "c": 51.0}, "prevDay": {"c": 49.0}}],
    }
    cache = {}
    parse_snapshots(response, {}, cache)
    assert cache["TEST"]["price"] == 51.0


def test_parse_snapshots_skips_zero_price():
    response = {"status": "OK", "tickers": [{"ticker": "UNKNOWN"}]}
    cache = {}
    parse_snapshots(response, {}, cache)
    assert "UNKNOWN" not in cache
```

### Unit: Factory selects correct provider

```python
# backend/tests/test_factory.py
import os
from unittest.mock import patch
from backend.market.factory import create_market_provider
from backend.market.simulator import SimulatorProvider
from backend.market.massive_provider import MassiveProvider


def test_no_api_key_returns_simulator():
    with patch.dict(os.environ, {"MASSIVE_API_KEY": ""}):
        provider = create_market_provider()
    assert isinstance(provider, SimulatorProvider)


def test_api_key_returns_massive_provider():
    with patch.dict(os.environ, {"MASSIVE_API_KEY": "test-key-123"}):
        provider = create_market_provider()
    assert isinstance(provider, MassiveProvider)
    assert provider.api_key == "test-key-123"


def test_custom_poll_interval():
    with patch.dict(os.environ, {
        "MASSIVE_API_KEY": "test-key",
        "MARKET_POLL_INTERVAL_SECONDS": "30",
    }):
        provider = create_market_provider()
    assert isinstance(provider, MassiveProvider)
    assert provider.interval_seconds == 30
```

---

## 14. Adding a Third Provider (Extension Point)

The interface is designed so that adding a new data source (e.g., a WebSocket feed, a different REST API) requires only:

1. Create `backend/market/websocket_provider.py` implementing `MarketDataProvider`.
2. In your `start()`, launch an asyncio task that writes `PriceEntry` dicts to `price_cache`.
3. Add a condition in `factory.py` to select the new provider based on an env var.

No other files change. The SSE endpoint, portfolio logic, and watchlist API are all agnostic to the data source.

```python
# Skeleton for a hypothetical third provider
# backend/market/websocket_provider.py
import asyncio
from .base import MarketDataProvider
from .cache import price_cache


class WebSocketProvider(MarketDataProvider):
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(
            self._ws_loop(), name="websocket-provider"
        )

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _ws_loop(self) -> None:
        # Connect to WebSocket, receive messages, write to price_cache
        # using the same PriceEntry structure
        ...
```
