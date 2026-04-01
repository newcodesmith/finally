# Massive API (formerly Polygon.io) — Reference for FinAlly

## Overview

Massive (formerly Polygon.io) provides real-time and historical US stock market data via REST API. The domain `polygon.io` now redirects to `massive.com`, but the API base URL `https://api.polygon.io` is unchanged. Existing Polygon.io API keys continue to work.

**Base URL:** `https://api.polygon.io`  
**Auth:** Query parameter `apiKey=YOUR_KEY` on every request  
**Docs:** `https://massive.com/docs/stocks`

---

## Authentication

All requests require an API key passed as a query parameter. There is no header-based auth option.

```
GET https://api.polygon.io/v2/snapshot/.../tickers?tickers=AAPL,MSFT&apiKey=YOUR_KEY
```

In FinAlly, the key is read from the `MASSIVE_API_KEY` environment variable.

---

## Pricing Tiers

| Tier | Price | Calls/min | Data Delay |
|------|-------|-----------|------------|
| Free (Starter) | $0 | ~5 req/min | 15 min delayed |
| Starter | ~$29/mo | Unlimited | Real-time |
| Developer | ~$79/mo | Unlimited | Real-time |
| Advanced | ~$199/mo | Unlimited | Real-time + WebSocket |

> **FinAlly implication:** Free tier data is 15 minutes delayed. The default `MARKET_POLL_INTERVAL_SECONDS=15` is appropriate for free tier. Real-time prices require a paid plan.

---

## Key Endpoints

### 1. Snapshot — Multiple Tickers (Primary endpoint for FinAlly)

Fetches latest price data for a comma-separated list of tickers in a single request. This is the main polling endpoint.

```
GET /v2/snapshot/locale/us/markets/stocks/tickers
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tickers` | string | No | Comma-separated list (e.g. `AAPL,MSFT,GOOGL`). Omit for all tickers. |
| `include_otc` | boolean | No | Include OTC securities (default: `false`) |
| `apiKey` | string | Yes | Your API key |

**Example request:**
```
GET https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,MSFT,GOOGL&apiKey=YOUR_KEY
```

**Response shape:**
```json
{
  "status": "OK",
  "count": 3,
  "tickers": [
    {
      "ticker": "AAPL",
      "todaysChangePerc": 0.7654,
      "todaysChange": 1.43,
      "updated": 1640995200000,
      "day": {
        "o": 177.09,
        "h": 180.57,
        "l": 176.41,
        "c": 178.52,
        "v": 82438734,
        "vw": 178.12
      },
      "min": {
        "av": 70765891,
        "t": 1640995140000,
        "n": 1234,
        "o": 178.45,
        "h": 178.60,
        "l": 178.40,
        "c": 178.52,
        "v": 98234,
        "vw": 178.50
      },
      "prevDay": {
        "o": 175.00,
        "h": 177.75,
        "l": 174.50,
        "c": 177.09,
        "v": 74567890,
        "vw": 176.45
      },
      "lastQuote": {
        "P": 178.55,
        "S": 4,
        "p": 178.50,
        "s": 8,
        "t": 1640995200000000000
      },
      "lastTrade": {
        "c": [14, 41],
        "i": "990000",
        "p": 178.52,
        "s": 100,
        "t": 1640995199000000000,
        "x": 4
      }
    }
  ]
}
```

**Key fields for FinAlly:**

| Field | Description |
|-------|-------------|
| `ticker` | Ticker symbol |
| `lastTrade.p` | Price of the most recent trade — **best current price during market hours** |
| `day.c` | Today's closing/current price — **use after hours when `lastTrade` is stale** |
| `day.o` | Today's open price — use as `session_open_price` on first poll |
| `prevDay.c` | Previous day's closing price — use as `previous_price` for direction comparison |
| `todaysChangePerc` | % change from previous close |
| `updated` | Unix millisecond timestamp of last update |

---

### 2. Snapshot — Single Ticker

```
GET /v2/snapshot/locale/us/markets/stocks/tickers/{stocksTicker}
```

Same response shape as the batch endpoint but for one ticker. Less efficient for FinAlly's multi-ticker use case — prefer the batch endpoint.

---

### 3. Previous Close

Returns the previous trading day's OHLCV bar for a ticker.

```
GET /v2/aggs/ticker/{stocksTicker}/prev
```

**Example:**
```
GET https://api.polygon.io/v2/aggs/ticker/AAPL/prev?apiKey=YOUR_KEY
```

**Response:**
```json
{
  "status": "OK",
  "resultsCount": 1,
  "ticker": "AAPL",
  "results": [
    {
      "T": "AAPL",
      "o": 177.09,
      "h": 180.57,
      "l": 176.41,
      "c": 178.52,
      "v": 82438734,
      "vw": 178.12,
      "t": 1640908800000
    }
  ]
}
```

---

### 4. Daily Aggregates (OHLCV Bars)

Returns OHLCV bars for a ticker over a date range.

```
GET /v2/aggs/ticker/{stocksTicker}/range/{multiplier}/{timespan}/{from}/{to}
```

**Example — daily bars for AAPL over the past month:**
```
GET https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/day/2025-03-01/2025-03-31?adjusted=true&sort=asc&apiKey=YOUR_KEY
```

**Parameters:**

| Parameter | Description |
|-----------|-------------|
| `multiplier` | Bar size multiplier (e.g. `1` for "1 day") |
| `timespan` | `minute`, `hour`, `day`, `week`, `month`, `quarter`, `year` |
| `from` | Start date `YYYY-MM-DD` or Unix ms timestamp |
| `to` | End date `YYYY-MM-DD` or Unix ms timestamp |
| `adjusted` | Adjust for splits/dividends (default: `true`) |
| `sort` | `asc` or `desc` (default: `asc`) |
| `limit` | Max results (default: 120, max: 50,000) |

**Response:**
```json
{
  "ticker": "AAPL",
  "status": "OK",
  "resultsCount": 22,
  "adjusted": true,
  "results": [
    {
      "v": 82438734,
      "vw": 178.12,
      "o": 177.09,
      "c": 178.52,
      "h": 180.57,
      "l": 176.41,
      "t": 1640908800000,
      "n": 654321
    }
  ]
}
```

**Field key:** `v`=volume, `vw`=VWAP, `o`=open, `c`=close, `h`=high, `l`=low, `t`=Unix ms timestamp, `n`=number of transactions.

---

### 5. Grouped Daily (All Tickers, One Day)

Returns EOD bars for all US stocks in one request for a given date. Useful for bulk initialization.

```
GET /v2/aggs/grouped/locale/us/market/stocks/{date}
```

**Example:**
```
GET https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/2025-03-31?adjusted=true&apiKey=YOUR_KEY
```

---

## Error Handling

| HTTP Status | Meaning | Action |
|-------------|---------|--------|
| `200 OK` | Success | Parse response normally |
| `400 Bad Request` | Invalid parameters | Log error, check ticker format |
| `403 Forbidden` | Invalid API key | Fatal — log and disable Massive client |
| `404 Not Found` | Ticker not found | Skip ticker, log warning |
| `429 Too Many Requests` | Rate limited | Read `Retry-After` header, back off |
| `5xx` | Server error | Log, retry on next scheduled poll |

**Rate limit handling:**
```python
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", 60))
    await asyncio.sleep(retry_after)
```

**Missing tickers:** If a ticker is invalid or not traded on US exchanges, it simply won't appear in the snapshot `tickers` array. The client must handle this gracefully — log a warning but do not raise an exception.

---

## Python Implementation

### Dependencies

```toml
# backend/pyproject.toml
[project]
dependencies = [
    "httpx>=0.27",
    ...
]
```

### Async client

```python
# backend/market/massive_client.py
import httpx
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

BASE_URL = "https://api.polygon.io"


class MassiveClient:
    """Async HTTP client for the Massive (Polygon.io) REST API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=10.0)

    async def get_snapshots(self, tickers: list[str]) -> dict:
        """
        Fetch latest price snapshots for a list of tickers.
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

    async def get_previous_close(self, ticker: str) -> float | None:
        """
        Fetch previous trading day's closing price.
        Returns None if the ticker is not found or data is unavailable.
        """
        url = f"{BASE_URL}/v2/aggs/ticker/{ticker}/prev"
        params = {"apiKey": self.api_key}
        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("resultsCount", 0) > 0:
                return data["results"][0]["c"]
        except Exception:
            logger.warning(f"Could not fetch previous close for {ticker}")
        return None

    async def aclose(self):
        await self._client.aclose()
```

### Parsing snapshots into FinAlly's internal format

```python
# backend/market/massive_client.py (continued)
from datetime import datetime, timezone


def extract_price(ticker_snapshot: dict) -> float:
    """
    Extract the best current price from a ticker snapshot.
    Prefers lastTrade.p (most recent trade) over day.c (session close).
    """
    last_trade = ticker_snapshot.get("lastTrade") or {}
    day = ticker_snapshot.get("day") or {}
    return last_trade.get("p") or day.get("c") or 0.0


def parse_snapshots(
    raw: dict,
    session_opens: dict[str, float],
    price_cache: dict[str, dict],
) -> None:
    """
    Parse a raw snapshot API response and update price_cache in place.

    session_opens: dict mapping ticker -> open price at session start.
                   Populated on first poll per ticker; never overwritten.
    price_cache:   shared dict written by the background task, read by SSE.
    """
    for t in raw.get("tickers", []):
        ticker = t["ticker"]
        price = extract_price(t)
        prev_day = t.get("prevDay") or {}
        previous_price = prev_day.get("c", price)

        # Capture session open once on first poll
        day = t.get("day") or {}
        if ticker not in session_opens:
            session_opens[ticker] = day.get("o") or price
        session_open_price = session_opens[ticker]

        # Change direction vs. previous poll value (not prevDay)
        existing = price_cache.get(ticker)
        last_known = existing["price"] if existing else previous_price
        if price > last_known:
            direction = "up"
        elif price < last_known:
            direction = "down"
        else:
            direction = "unchanged"

        updated_ms = t.get("updated", 0)
        timestamp = datetime.fromtimestamp(
            updated_ms / 1000, tz=timezone.utc
        ).isoformat()

        price_cache[ticker] = {
            "ticker": ticker,
            "price": price,
            "previous_price": last_known,
            "session_open_price": session_open_price,
            "timestamp": timestamp,
            "change_direction": direction,
        }
```

### Full polling loop

```python
# backend/market/massive_poller.py
import asyncio
import logging
from collections.abc import Callable, Awaitable

import httpx

from .massive_client import MassiveClient, parse_snapshots

logger = logging.getLogger(__name__)


async def massive_poll_loop(
    api_key: str,
    get_watchlist: Callable[[], Awaitable[list[str]]],
    price_cache: dict[str, dict],
    interval_seconds: int = 15,
) -> None:
    """
    Background task: polls Massive API on interval, writes to price_cache.

    Args:
        api_key:          Massive/Polygon.io API key.
        get_watchlist:    Async callable returning current watchlist tickers.
        price_cache:      Shared mutable dict; keys are ticker strings.
        interval_seconds: Poll interval (default 15s for free tier).
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

                # Prune stale tickers removed from watchlist
                current_set = set(tickers)
                for stale in set(price_cache) - current_set:
                    del price_cache[stale]
                    session_opens.pop(stale, None)

                logger.debug(f"Polled {len(tickers)} tickers from Massive API")

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 429:
                    retry_after = int(e.response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited; sleeping {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue
                elif status == 403:
                    logger.error("Massive API key invalid or forbidden. Stopping poller.")
                    return
                else:
                    logger.error(f"Massive API HTTP {status}: {e}")

            except httpx.TimeoutException:
                logger.warning("Massive API request timed out")

            except Exception as e:
                logger.error(f"Massive API poll error: {e}")

            await asyncio.sleep(interval_seconds)

    finally:
        await client.aclose()
```

---

## Behavioral Notes

### After-hours / pre-market

- **During market hours (9:30am–4:00pm ET):** `lastTrade.p` reflects the most recent trade price.
- **After market close:** `day.c` is stable. `lastTrade.p` may be stale (from the last trade of the day). The client uses `lastTrade.p` if present, falling back to `day.c`.
- **Pre-market:** Limited data. `day.o` may not yet be populated before the open.

### Session open price

On the first successful poll, `day.o` (today's market open) is stored as `session_open_price` for each ticker and **never overwritten** during the session. This is the reference price for computing session change % in the watchlist panel. Using `day.o` is more accurate than capturing the first `lastTrade.p` (which could be mid-session).

### Tickers not returned

If a ticker in the watchlist is not found in the snapshot response (invalid symbol, OTC-only, etc.), it simply won't appear in the `tickers` array. The poller treats missing tickers as no-ops: the previous cache entry persists until the next successful poll returns data, or until the ticker is removed from the watchlist.
