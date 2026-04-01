# Market Data Interface — Unified Python API

## Overview

The backend uses a single abstract interface for all market data. Two concrete implementations exist behind it:

- **`SimulatorProvider`** — default; generates prices via geometric Brownian motion in-process with no external dependencies.
- **`MassiveProvider`** — optional; polls the Massive (Polygon.io) REST API when `MASSIVE_API_KEY` is set.

All downstream code (SSE streaming, price cache, portfolio endpoints) is written against the interface. Switching between providers requires only a one-line change in the startup factory function.

---

## Price Cache (Shared Contract)

Both providers write to a shared in-memory dict called `price_cache`. This dict is the single source of truth for current prices across the entire backend.

### Type

```python
# backend/market/types.py
from typing import TypedDict

class PriceEntry(TypedDict):
    ticker: str
    price: float               # Current price
    previous_price: float      # Price at the previous tick/poll
    session_open_price: float  # First price of the session (never changes)
    timestamp: str             # ISO 8601 UTC string
    change_direction: str      # "up" | "down" | "unchanged"
```

### Shared instance

```python
# backend/market/cache.py

# The single shared price cache. All providers write here; SSE reads here.
price_cache: dict[str, PriceEntry] = {}
```

The cache is a plain module-level dict. No locks are needed: Python's GIL ensures that dict reads and writes of individual keys are atomic. The background task (one writer) and SSE handlers (many readers) do not conflict.

---

## Abstract Interface

```python
# backend/market/base.py
from abc import ABC, abstractmethod


class MarketDataProvider(ABC):
    """
    Abstract base class for market data providers.
    Subclasses must implement start() and stop().
    Both providers write to the shared price_cache in market.cache.
    """

    @abstractmethod
    async def start(self) -> None:
        """
        Start the background data task.
        Called once during application startup (FastAPI lifespan).
        Must not block — the implementation launches an asyncio.Task internally.
        """
        ...

    @abstractmethod
    async def stop(self) -> None:
        """
        Gracefully stop the background data task.
        Called during application shutdown (FastAPI lifespan).
        """
        ...
```

---

## Factory Function (Provider Selection)

```python
# backend/market/factory.py
import os
from .base import MarketDataProvider
from .simulator import SimulatorProvider
from .massive_provider import MassiveProvider


def create_market_provider() -> MarketDataProvider:
    """
    Select and construct the appropriate market data provider based on env vars.

    - If MASSIVE_API_KEY is set and non-empty: returns MassiveProvider.
    - Otherwise: returns SimulatorProvider.
    """
    api_key = os.getenv("MASSIVE_API_KEY", "").strip()
    if api_key:
        interval = int(os.getenv("MARKET_POLL_INTERVAL_SECONDS", "15"))
        return MassiveProvider(api_key=api_key, interval_seconds=interval)
    return SimulatorProvider()
```

---

## Simulator Implementation

```python
# backend/market/simulator.py
import asyncio
from .base import MarketDataProvider
from .cache import price_cache
from .simulator_engine import run_simulator  # see MARKET_SIMULATOR.md


class SimulatorProvider(MarketDataProvider):
    def __init__(self):
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(
            run_simulator(price_cache),
            name="market-simulator",
        )

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
```

---

## Massive Provider Implementation

```python
# backend/market/massive_provider.py
import asyncio
from .base import MarketDataProvider
from .cache import price_cache
from .massive_poller import massive_poll_loop
from ..db import get_watchlist_tickers  # async DB query returning list[str]


class MassiveProvider(MarketDataProvider):
    def __init__(self, api_key: str, interval_seconds: int = 15):
        self.api_key = api_key
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
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
```

---

## FastAPI Integration (Lifespan)

```python
# backend/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .market.factory import create_market_provider

_provider = create_market_provider()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _provider.start()
    yield
    await _provider.stop()


app = FastAPI(lifespan=lifespan)
```

---

## SSE Streaming Endpoint

The SSE endpoint reads from `price_cache` and pushes updates to all connected clients. It is identical regardless of which provider is running.

```python
# backend/api/stream.py
import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from ..market.cache import price_cache

router = APIRouter()


@router.get("/api/stream/prices")
async def stream_prices():
    """
    SSE endpoint. Pushes all tickers in price_cache every 500ms.
    Client reconnects automatically via EventSource retry behavior.
    """
    async def event_generator():
        while True:
            for entry in list(price_cache.values()):
                payload = json.dumps(entry)
                yield f"data: {payload}\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

> **Note on update cadence:** The SSE endpoint always pushes at 500ms regardless of how often the provider updates the cache. With the simulator (updates every 500ms) this is 1:1. With Massive (updates every 15s) the same price is pushed 30 times between updates — this is intentional. The frontend still sees a regular heartbeat confirming the SSE connection is alive, and the `change_direction` field will be `"unchanged"` between real updates.

---

## Directory Structure

```
backend/
└── market/
    ├── __init__.py
    ├── base.py              # MarketDataProvider ABC
    ├── cache.py             # price_cache dict (shared state)
    ├── factory.py           # create_market_provider() factory
    ├── types.py             # PriceEntry TypedDict
    ├── simulator.py         # SimulatorProvider (wraps simulator_engine)
    ├── simulator_engine.py  # GBM simulation loop (see MARKET_SIMULATOR.md)
    ├── massive_provider.py  # MassiveProvider (wraps massive_poller)
    ├── massive_client.py    # Async HTTP client for Massive API
    └── massive_poller.py    # Poll loop that feeds price_cache
```

---

## `change_direction` Values

The `change_direction` field in `PriceEntry` has exactly three valid values:

| Value | Meaning |
|-------|---------|
| `"up"` | Current price is higher than `previous_price` |
| `"down"` | Current price is lower than `previous_price` |
| `"unchanged"` | Current price equals `previous_price` (or first tick) |

On the very first tick for a new ticker (no prior entry in cache), `previous_price` is initialized to the current price, so the direction is `"unchanged"`.

---

## `session_open_price` Semantics

- Set **once** per ticker per process lifetime — on the first tick/poll that produces a price for that ticker.
- **Simulator:** set to the configured seed price (e.g. AAPL → `190.00`).
- **Massive:** set to `day.o` from the first snapshot response for that ticker.
- **Never overwritten** — survives watchlist removes/re-adds within the same process.
- Used by the frontend to compute the session change % shown in the watchlist panel.
- Distinct from `previous_price`, which updates every tick and drives the `change_direction` flash animation.

---

## Response Shape Used by Frontend

All SSE events and the `GET /api/watchlist` response include these price fields. The exact JSON shape both providers guarantee:

```json
{
  "ticker": "AAPL",
  "price": 189.42,
  "previous_price": 189.31,
  "session_open_price": 188.00,
  "timestamp": "2026-04-01T14:32:00.000Z",
  "change_direction": "up"
}
```

---

## Adding a Third Provider (Future)

To add a new data source (e.g., a WebSocket feed):

1. Create `backend/market/websocket_provider.py` implementing `MarketDataProvider`.
2. Write to `price_cache` using the same `PriceEntry` structure.
3. Add a condition in `factory.py` to select the new provider based on an env var.
4. No other files change.
