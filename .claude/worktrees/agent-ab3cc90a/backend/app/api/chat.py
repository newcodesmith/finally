"""Chat API endpoint with LLM integration."""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..db import (
    add_watchlist_ticker,
    execute_trade,
    get_cash_balance,
    get_chat_history,
    get_portfolio_history,
    get_positions,
    get_watchlist_tickers,
    record_portfolio_snapshot,
    remove_watchlist_ticker,
    save_chat_message,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

FALLBACK_RESPONSE = {
    "message": "Sorry, I'm having trouble connecting right now. Please try again.",
    "trades": [],
    "watchlist_changes": [],
}

SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant for a simulated trading workstation.
You help users analyze their portfolio and execute trades using virtual money (no real money is at risk).

Your capabilities:
- Analyze portfolio composition, risk concentration, and P&L
- Suggest and execute trades when the user asks
- Manage the watchlist (add/remove tickers)
- Provide market commentary and trade reasoning

Guidelines:
- Be concise and data-driven in responses
- Reference specific numbers from the portfolio context when relevant
- When the user agrees to a trade or asks you to execute one, include it in the trades array
- Always respond with valid JSON matching the required schema
- For watchlist changes, use the watchlist_changes array

You MUST always respond with JSON matching this exact schema:
{
  "message": "Your conversational response",
  "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}],
  "watchlist_changes": [{"ticker": "PYPL", "action": "add"}]
}
trades and watchlist_changes may be empty arrays if no actions are needed."""


# ---------------------------------------------------------------------------
# Structured output schema
# ---------------------------------------------------------------------------


class TradeAction(BaseModel):
    ticker: str
    side: str
    quantity: float


class WatchlistChange(BaseModel):
    ticker: str
    action: str  # "add" or "remove"


class LLMResponse(BaseModel):
    message: str
    trades: list[TradeAction] = []
    watchlist_changes: list[WatchlistChange] = []


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_portfolio_context(
    cash: float,
    positions: list[dict],
    watchlist: list[str],
    price_cache,
) -> str:
    """Build a portfolio context string for the LLM system prompt."""
    lines = [f"PORTFOLIO CONTEXT:", f"Cash: ${cash:,.2f}"]

    if positions:
        lines.append("\nPositions:")
        total_positions_value = 0.0
        for pos in positions:
            ticker = pos["ticker"]
            qty = pos["quantity"]
            avg_cost = pos["avg_cost"]
            current_price = price_cache.get_price(ticker) or avg_cost
            pnl = (current_price - avg_cost) * qty
            pnl_pct = ((current_price - avg_cost) / avg_cost * 100) if avg_cost else 0
            value = current_price * qty
            total_positions_value += value
            lines.append(
                f"  {ticker}: {qty:.4g} shares @ avg ${avg_cost:.2f}, "
                f"now ${current_price:.2f}, "
                f"P&L: ${pnl:+.2f} ({pnl_pct:+.2f}%), "
                f"value: ${value:.2f}"
            )
        total_value = cash + total_positions_value
        lines.append(f"\nTotal portfolio value: ${total_value:,.2f}")
    else:
        lines.append("Positions: None (no open positions)")
        lines.append(f"Total portfolio value: ${cash:,.2f}")

    lines.append(f"\nWatchlist: {', '.join(watchlist) if watchlist else 'empty'}")

    # Add live prices for watchlist tickers
    price_lines = []
    for ticker in watchlist:
        price = price_cache.get_price(ticker)
        if price is not None:
            price_lines.append(f"{ticker}: ${price:.2f}")
    if price_lines:
        lines.append("Current prices: " + ", ".join(price_lines))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("")
async def chat(body: ChatRequest, request: Request):
    """Process a chat message, call LLM, auto-execute actions, return response."""
    price_cache = request.app.state.price_cache
    market_source = request.app.state.market_source

    # 1. Load portfolio context
    cash = await get_cash_balance()
    positions = await get_positions()
    watchlist = await get_watchlist_tickers()

    portfolio_context = _build_portfolio_context(cash, positions, watchlist, price_cache)

    # 2. Load chat history (last 20 messages)
    history = await get_chat_history(limit=20)

    # 3. Build messages for LLM
    messages = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{portfolio_context}"},
    ]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": body.message})

    # 4. Call LLM
    llm_result: LLMResponse | None = None

    mock_mode = os.environ.get("LLM_MOCK", "false").lower() == "true"
    if mock_mode:
        llm_result = LLMResponse(
            message="I'm running in mock mode. I can see your portfolio but won't make real LLM calls.",
            trades=[],
            watchlist_changes=[],
        )
    else:
        try:
            from litellm import completion
            response = completion(
                model=MODEL,
                messages=messages,
                response_format=LLMResponse,
                reasoning_effort="low",
                extra_body=EXTRA_BODY,
            )
            content = response.choices[0].message.content
            llm_result = LLMResponse.model_validate_json(content)
        except Exception:
            logger.exception("LLM call failed")
            await save_chat_message("user", body.message)
            await save_chat_message("assistant", FALLBACK_RESPONSE["message"])
            return FALLBACK_RESPONSE

    # 5. Auto-execute trades
    executed_trades = []
    trade_errors = []
    for trade_action in llm_result.trades:
        ticker = trade_action.ticker.upper().strip()
        side = trade_action.side.lower()
        quantity = trade_action.quantity

        # Auto-add to watchlist if needed
        if ticker not in watchlist:
            added = await add_watchlist_ticker(ticker)
            if added:
                await market_source.add_ticker(ticker)
                watchlist.append(ticker)

        current_price = price_cache.get_price(ticker)
        if current_price is None:
            trade_errors.append(f"No price for {ticker} — skipped")
            continue

        result = await execute_trade(ticker=ticker, side=side, quantity=quantity, price=current_price)
        if result["success"]:
            executed_trades.append({
                "ticker": ticker,
                "side": side,
                "quantity": quantity,
                "price": current_price,
            })
        else:
            trade_errors.append(f"{ticker} {side} {quantity}: {result['error']}")

    # 6. Auto-execute watchlist changes
    executed_watchlist_changes = []
    for wl_change in llm_result.watchlist_changes:
        ticker = wl_change.ticker.upper().strip()
        action = wl_change.action.lower()

        if action == "add":
            added = await add_watchlist_ticker(ticker)
            if added:
                await market_source.add_ticker(ticker)
            executed_watchlist_changes.append({"ticker": ticker, "action": "add", "success": True})
        elif action == "remove":
            removed = await remove_watchlist_ticker(ticker)
            if removed:
                await market_source.remove_ticker(ticker)
            executed_watchlist_changes.append({"ticker": ticker, "action": "remove", "success": removed})

    # 7. Record post-action portfolio snapshot if any trades executed
    if executed_trades:
        try:
            updated_cash = await get_cash_balance()
            updated_positions = await get_positions()
            positions_value = sum(
                (price_cache.get_price(p["ticker"]) or p["avg_cost"]) * p["quantity"]
                for p in updated_positions
            )
            await record_portfolio_snapshot(updated_cash + positions_value)
        except Exception:
            logger.exception("Failed to record post-chat-trade snapshot")

    # 8. Build actions summary for DB storage
    actions = None
    if executed_trades or executed_watchlist_changes or trade_errors:
        actions = {
            "trades": executed_trades,
            "watchlist_changes": executed_watchlist_changes,
            "errors": trade_errors,
        }

    # Append trade error info to message if any
    final_message = llm_result.message
    if trade_errors:
        final_message += "\n\n⚠️ Some trades could not execute: " + "; ".join(trade_errors)

    # 9. Save messages to DB
    await save_chat_message("user", body.message)
    await save_chat_message("assistant", final_message, actions=actions)

    return {
        "message": final_message,
        "trades": executed_trades,
        "watchlist_changes": executed_watchlist_changes,
        "errors": trade_errors,
    }
