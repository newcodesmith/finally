# Market Simulator — Approach and Code Structure

## Overview

The simulator generates realistic-looking stock prices entirely in-process using **Geometric Brownian Motion (GBM)** — the standard mathematical model for equity price dynamics. It runs as an asyncio background task, updating prices every 500ms, and writes to the shared `price_cache` dict (see `MARKET_INTERFACE.md`).

The simulator has no external dependencies and produces a visually engaging demo: prices drift and fluctuate naturally, correlated moves create sector-level coherence, and occasional random "events" create dramatic single-ticker spikes.

---

## Mathematical Foundation

### Geometric Brownian Motion

GBM models price as a continuous random process where the log-return at each step follows a normal distribution:

```
S(t+dt) = S(t) * exp((μ - σ²/2) * dt + σ * √dt * Z)
```

Where:
- `S(t)` — current price
- `μ` (mu/drift) — annualized expected return (e.g. `0.05` = 5%/year)
- `σ` (sigma/volatility) — annualized volatility (e.g. `0.25` = 25%/year)
- `dt` — time step in years (500ms ≈ `500 / (252 * 6.5 * 3600 * 1000)` years)
- `Z` — standard normal random variable `N(0, 1)`

At 500ms ticks, the effective `dt` for intraday simulation is tiny, so drift is negligible and the price motion is almost entirely driven by the volatility term. This is appropriate — intraday, stocks look like random walks.

### Correlated Moves

A **market factor** is added to simulate the tendency of stocks (especially in the same sector) to move together. Each tick generates:

1. A **market shock** `Z_market ~ N(0, 1)` — shared across all tickers
2. An **idiosyncratic shock** `Z_idio ~ N(0, 1)` — unique to each ticker

The combined shock for ticker `i` is:

```
Z_i = β_i * Z_market + √(1 - β_i²) * Z_idio
```

Where `β_i` (beta) controls market sensitivity (e.g. `0.7` for tech stocks, `0.3` for defensives). This produces positive correlations within sectors while preserving realistic idiosyncratic variation.

---

## Seed Prices and Volatilities

Each default ticker starts from a realistic seed price and has a calibrated volatility. These are the session "open" prices (retained for the `session_open_price` SSE field).

```python
# backend/market/simulator_config.py

TICKER_CONFIG: dict[str, dict] = {
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

# Annualized drift — small positive number representing long-run expected return.
# At 500ms ticks, this is negligible vs. volatility but keeps the math correct.
ANNUAL_DRIFT = 0.05

# Time step: 500ms expressed as a fraction of a trading year.
# Approximate: 252 trading days * 6.5 hours * 3600 seconds/hour.
SECONDS_PER_TRADING_YEAR = 252 * 6.5 * 3600
TICK_INTERVAL_SECONDS = 0.5
DT = TICK_INTERVAL_SECONDS / SECONDS_PER_TRADING_YEAR  # ~8.5e-8 years per tick

# Random event parameters
EVENT_PROBABILITY = 0.002   # 0.2% chance per ticker per tick (~1 event every ~8 minutes per ticker)
EVENT_MIN_MOVE = 0.02       # 2% minimum event move
EVENT_MAX_MOVE = 0.05       # 5% maximum event move
```

---

## Simulator Engine

```python
# backend/market/simulator_engine.py
import asyncio
import math
import random
import logging
from datetime import datetime, timezone

from .simulator_config import (
    TICKER_CONFIG,
    ANNUAL_DRIFT,
    DT,
    TICK_INTERVAL_SECONDS,
    EVENT_PROBABILITY,
    EVENT_MIN_MOVE,
    EVENT_MAX_MOVE,
)
from .types import PriceEntry

logger = logging.getLogger(__name__)


def _gbm_step(price: float, sigma: float, drift: float = ANNUAL_DRIFT) -> float:
    """
    Advance a price by one GBM tick.
    Returns the new price.
    """
    z = random.gauss(0.0, 1.0)
    log_return = (drift - 0.5 * sigma ** 2) * DT + sigma * math.sqrt(DT) * z
    return price * math.exp(log_return)


def _maybe_event(price: float) -> float:
    """
    Apply a random event (sudden 2-5% move) with low probability.
    Direction is random (up or down).
    Returns the (possibly unchanged) price.
    """
    if random.random() < EVENT_PROBABILITY:
        move_pct = random.uniform(EVENT_MIN_MOVE, EVENT_MAX_MOVE)
        direction = 1 if random.random() > 0.5 else -1
        price *= 1 + direction * move_pct
        logger.debug(f"Random event: {direction:+.0%} move applied")
    return price


async def run_simulator(
    price_cache: dict[str, PriceEntry],
    get_watchlist: callable = None,
) -> None:
    """
    Main simulator loop. Runs forever; cancelled on shutdown.

    Args:
        price_cache:   Shared dict written by this task, read by SSE.
        get_watchlist: Optional async callable returning list[str] of active
                       tickers. If None, uses all tickers in TICKER_CONFIG.
                       Pass the DB query fn to support dynamic watchlist changes.
    """
    # Current simulated prices — initialized from seed prices
    current_prices: dict[str, float] = {
        ticker: cfg["seed"] for ticker, cfg in TICKER_CONFIG.items()
    }
    # Session open prices — set once per session, never overwritten
    session_opens: dict[str, float] = dict(current_prices)

    tick = 0

    while True:
        await asyncio.sleep(TICK_INTERVAL_SECONDS)
        tick += 1

        # Determine active tickers
        if get_watchlist is not None:
            try:
                watchlist = await get_watchlist()
            except Exception:
                watchlist = list(current_prices.keys())
        else:
            watchlist = list(TICKER_CONFIG.keys())

        if not watchlist:
            continue

        # Generate market-wide shock for correlated moves
        z_market = random.gauss(0.0, 1.0)

        timestamp = datetime.now(tz=timezone.utc).isoformat()

        for ticker in watchlist:
            cfg = TICKER_CONFIG.get(ticker)
            if cfg is None:
                # Unknown ticker (added dynamically by user) — use defaults
                cfg = {"seed": 100.0, "sigma": 0.30, "beta": 0.70}
                if ticker not in current_prices:
                    current_prices[ticker] = cfg["seed"]
                    session_opens[ticker] = cfg["seed"]

            sigma = cfg["sigma"]
            beta = cfg["beta"]
            old_price = current_prices.get(ticker, cfg["seed"])

            # Correlated GBM step
            z_idio = random.gauss(0.0, 1.0)
            z_combined = beta * z_market + math.sqrt(1 - beta ** 2) * z_idio

            # Apply GBM using the combined shock (override internal gauss call)
            log_return = (
                (ANNUAL_DRIFT - 0.5 * sigma ** 2) * DT
                + sigma * math.sqrt(DT) * z_combined
            )
            new_price = old_price * math.exp(log_return)

            # Optional random event
            new_price = _maybe_event(new_price)

            # Floor at $0.01 to prevent negative prices (shouldn't happen with GBM but defensive)
            new_price = max(new_price, 0.01)
            new_price = round(new_price, 2)

            # Session open: set once, never overwritten
            if ticker not in session_opens:
                session_opens[ticker] = new_price

            # Direction vs. previous price
            if new_price > old_price:
                direction = "up"
            elif new_price < old_price:
                direction = "down"
            else:
                direction = "unchanged"

            current_prices[ticker] = new_price
            price_cache[ticker] = {
                "ticker": ticker,
                "price": new_price,
                "previous_price": old_price,
                "session_open_price": session_opens[ticker],
                "timestamp": timestamp,
                "change_direction": direction,
            }

        # Prune tickers removed from watchlist
        for stale in set(price_cache) - set(watchlist):
            del price_cache[stale]
```

---

## SimulatorProvider (Adapter)

```python
# backend/market/simulator.py
import asyncio
from .base import MarketDataProvider
from .cache import price_cache
from .simulator_engine import run_simulator
from ..db import get_watchlist_tickers  # async fn returning list[str]


class SimulatorProvider(MarketDataProvider):
    """Wraps the GBM simulator engine as a MarketDataProvider."""

    def __init__(self):
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(
            run_simulator(price_cache, get_watchlist=get_watchlist_tickers),
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

## Dynamic Ticker Support

When a user adds a ticker not in `TICKER_CONFIG` (e.g., via the watchlist or AI chat), the simulator handles it gracefully:

- If the ticker is unknown, it initializes with `seed=$100.00`, `sigma=0.30`, `beta=0.70`.
- The seed price and session open are set on the first tick the ticker appears.
- No restart or reconfiguration is needed — the simulator reads the watchlist dynamically.

If you want to pre-seed a custom price for a dynamically added ticker, extend `TICKER_CONFIG` at startup.

---

## Portfolio Snapshot Integration (Optional Optimization)

Per PLAN.md §13 simplification S4, the portfolio snapshot background task can be folded into the simulator loop instead of running as a separate coroutine. Add a tick counter and write a snapshot every 60 ticks (30 seconds at 500ms cadence):

```python
# Inside run_simulator(), after the per-ticker loop:
SNAPSHOT_EVERY_N_TICKS = 60  # 60 * 0.5s = 30 seconds

if tick % SNAPSHOT_EVERY_N_TICKS == 0:
    try:
        await record_portfolio_snapshot()  # async DB write
    except Exception as e:
        logger.warning(f"Portfolio snapshot failed: {e}")
```

This eliminates a separate `asyncio.create_task` and reduces SQLite write contention.

---

## Behavioral Properties

| Property | Value |
|----------|-------|
| Tick interval | 500ms |
| Price floor | $0.01 |
| Price precision | 2 decimal places |
| Sector correlation | Controlled by per-ticker `beta` (0–1) |
| Random event probability | ~0.2% per ticker per tick |
| Random event magnitude | 2–5% move (up or down) |
| Drift | 5% annualized (negligible at intraday timescales) |
| Session open price | Seed price from `TICKER_CONFIG`; never changes during process lifetime |

---

## Testing the Simulator

The simulator's randomness is seeded from Python's global random state. For deterministic unit tests, seed before calling:

```python
import random

def test_gbm_step_increases_on_positive_z():
    random.seed(42)
    from backend.market.simulator_engine import _gbm_step
    # With seed 42, gauss(0, 1) returns a known value
    price = 100.0
    new_price = _gbm_step(price, sigma=0.25)
    assert new_price != price  # price changed
    assert new_price > 0       # GBM never goes negative


def test_simulator_writes_to_cache():
    import asyncio, random
    random.seed(0)
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
    assert "AAPL" in cache
    entry = cache["AAPL"]
    assert entry["change_direction"] in ("up", "down", "unchanged")
    assert entry["price"] > 0
    assert entry["session_open_price"] == 190.00  # AAPL seed price
```

---

## Configuration Reference

All simulation parameters live in `backend/market/simulator_config.py`. Adjust these to tune the visual behavior:

| Constant | Default | Effect |
|----------|---------|--------|
| `ANNUAL_DRIFT` | `0.05` | Long-run upward drift; negligible at 500ms |
| `TICK_INTERVAL_SECONDS` | `0.5` | How often prices update (affects SSE cadence) |
| `EVENT_PROBABILITY` | `0.002` | Frequency of sudden moves (~1 per 8 min per ticker) |
| `EVENT_MIN_MOVE` | `0.02` | Minimum event magnitude (2%) |
| `EVENT_MAX_MOVE` | `0.05` | Maximum event magnitude (5%) |
| Per-ticker `sigma` | varies | Annualized volatility; higher = more movement |
| Per-ticker `beta` | varies | Market correlation; higher = moves with the market more |
| Per-ticker `seed` | varies | Starting price; also the session open reference price |
