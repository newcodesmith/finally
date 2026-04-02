"""Portfolio API endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..db import (
    add_watchlist_ticker,
    execute_trade,
    get_cash_balance,
    get_portfolio_history,
    get_positions,
    get_watchlist_tickers,
    record_portfolio_snapshot,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class TradeRequest(BaseModel):
    ticker: str
    side: str
    quantity: float


@router.get("")
async def get_portfolio(request: Request):
    """Return current portfolio: cash, positions with live P&L, total value."""
    price_cache = request.app.state.price_cache

    cash = await get_cash_balance()
    positions_raw = await get_positions()

    positions = []
    positions_value = 0.0

    for pos in positions_raw:
        ticker = pos["ticker"]
        quantity = pos["quantity"]
        avg_cost = pos["avg_cost"]

        current_price = price_cache.get_price(ticker)
        if current_price is None:
            current_price = avg_cost  # Fall back to avg_cost if no live price

        unrealized_pnl = (current_price - avg_cost) * quantity
        pnl_percent = ((current_price - avg_cost) / avg_cost * 100) if avg_cost else 0.0
        position_value = current_price * quantity
        positions_value += position_value

        positions.append({
            "ticker": ticker,
            "quantity": quantity,
            "avg_cost": avg_cost,
            "current_price": current_price,
            "unrealized_pnl": round(unrealized_pnl, 2),
            "pnl_percent": round(pnl_percent, 4),
            "value": round(position_value, 2),
        })

    total_value = cash + positions_value

    return {
        "cash_balance": round(cash, 2),
        "positions": positions,
        "total_value": round(total_value, 2),
    }


@router.post("/trade")
async def trade(body: TradeRequest, request: Request):
    """Execute a market order trade."""
    ticker = body.ticker.upper().strip()
    side = body.side.lower().strip()
    quantity = body.quantity
    price_cache = request.app.state.price_cache
    market_source = request.app.state.market_source

    if side not in ("buy", "sell"):
        raise HTTPException(status_code=422, detail="side must be 'buy' or 'sell'")
    if quantity <= 0:
        raise HTTPException(status_code=422, detail="quantity must be positive")

    # Auto-add ticker to watchlist if not already there
    watchlist = await get_watchlist_tickers()
    if ticker not in watchlist:
        added = await add_watchlist_ticker(ticker)
        if added:
            await market_source.add_ticker(ticker)
            logger.info("Auto-added %s to watchlist for trade", ticker)

    # Get current price
    current_price = price_cache.get_price(ticker)
    if current_price is None:
        raise HTTPException(status_code=422, detail=f"No price available for {ticker}. Try again shortly.")

    result = await execute_trade(ticker=ticker, side=side, quantity=quantity, price=current_price)

    if result["success"]:
        # Record a portfolio snapshot immediately after the trade
        try:
            positions_raw = await get_positions()
            positions_value = sum(
                (price_cache.get_price(p["ticker"]) or p["avg_cost"]) * p["quantity"]
                for p in positions_raw
            )
            total_value = result["cash_balance"] + positions_value
            await record_portfolio_snapshot(total_value)
        except Exception:
            logger.exception("Failed to record post-trade snapshot")

    return {
        "success": result["success"],
        "error": result["error"],
        "ticker": ticker,
        "side": side,
        "quantity": quantity,
        "price": current_price,
        "cash_balance": result["cash_balance"],
        "position": result["position"],
    }


@router.get("/history")
async def get_history():
    """Return portfolio value snapshots over time."""
    rows = await get_portfolio_history()
    return rows
