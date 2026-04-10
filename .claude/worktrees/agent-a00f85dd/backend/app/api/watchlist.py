"""Watchlist API endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..db import add_watchlist_ticker, get_watchlist_tickers, remove_watchlist_ticker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class AddTickerRequest(BaseModel):
    ticker: str


@router.get("")
async def get_watchlist(request: Request):
    """Return current watchlist tickers with latest prices."""
    tickers = await get_watchlist_tickers()
    price_cache = request.app.state.price_cache

    result = []
    for ticker in tickers:
        update = price_cache.get(ticker)
        if update:
            result.append(update.to_dict())
        else:
            # Price not yet available — include ticker with nulls
            result.append({
                "ticker": ticker,
                "price": None,
                "previous_price": None,
                "session_open_price": None,
                "change_direction": "unchanged",
                "timestamp": None,
                "change": None,
                "change_percent": None,
            })

    return result


@router.post("")
async def add_to_watchlist(body: AddTickerRequest, request: Request):
    """Add a ticker to the watchlist."""
    ticker = body.ticker.upper().strip()
    if not ticker:
        raise HTTPException(status_code=422, detail="Ticker cannot be empty")

    added = await add_watchlist_ticker(ticker)
    if added:
        # Start simulating / tracking the new ticker
        market_source = request.app.state.market_source
        await market_source.add_ticker(ticker)
        logger.info("Added ticker to watchlist: %s", ticker)

    return {"ticker": ticker, "added": added}


@router.delete("/{ticker}")
async def remove_from_watchlist(ticker: str, request: Request):
    """Remove a ticker from the watchlist."""
    ticker = ticker.upper().strip()
    removed = await remove_watchlist_ticker(ticker)
    if removed:
        market_source = request.app.state.market_source
        await market_source.remove_ticker(ticker)
        logger.info("Removed ticker from watchlist: %s", ticker)

    return {"ticker": ticker, "removed": removed}
