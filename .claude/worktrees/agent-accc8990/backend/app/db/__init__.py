"""Database layer for FinAlly."""

from .connection import get_db
from .queries import (
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
from .schema import init_db

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
