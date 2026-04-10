"""Database layer for FinAlly."""

from .connection import get_db
from .schema import init_db
from .queries import (
    get_watchlist_tickers,
    add_watchlist_ticker,
    remove_watchlist_ticker,
    get_cash_balance,
    get_positions,
    execute_trade,
    get_portfolio_history,
    record_portfolio_snapshot,
    get_chat_history,
    save_chat_message,
)

__all__ = [
    "get_db",
    "init_db",
    "get_watchlist_tickers",
    "add_watchlist_ticker",
    "remove_watchlist_ticker",
    "get_cash_balance",
    "get_positions",
    "execute_trade",
    "get_portfolio_history",
    "record_portfolio_snapshot",
    "get_chat_history",
    "save_chat_message",
]
