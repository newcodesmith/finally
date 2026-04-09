"""Tests for watchlist query functions."""

from __future__ import annotations

import pytest

from app.db.queries import (
    get_watchlist_tickers,
    add_watchlist_ticker,
    remove_watchlist_ticker,
)
from app.db.schema import DEFAULT_WATCHLIST


async def test_get_watchlist_tickers_returns_default():
    """Should return the 10 default tickers after init."""
    tickers = await get_watchlist_tickers()
    assert len(tickers) == 10
    assert set(tickers) == set(DEFAULT_WATCHLIST)


async def test_get_watchlist_tickers_ordered_by_added_at():
    """Tickers should be returned in insertion order (added_at ASC)."""
    tickers = await get_watchlist_tickers()
    # Default tickers were all inserted with the same timestamp,
    # so order may vary. Add a new one and verify it's last.
    await add_watchlist_ticker("PYPL")
    tickers = await get_watchlist_tickers()
    assert tickers[-1] == "PYPL"


async def test_add_watchlist_ticker_returns_true():
    """Adding a new ticker should return True."""
    result = await add_watchlist_ticker("PYPL")
    assert result is True


async def test_add_watchlist_ticker_appears_in_list():
    """A newly added ticker should appear in the watchlist."""
    await add_watchlist_ticker("PYPL")
    tickers = await get_watchlist_tickers()
    assert "PYPL" in tickers


async def test_add_duplicate_returns_false():
    """Adding a ticker that already exists should return False."""
    result = await add_watchlist_ticker("AAPL")
    assert result is False


async def test_add_duplicate_does_not_increase_count():
    """Adding a duplicate should not create a second row."""
    await add_watchlist_ticker("AAPL")
    tickers = await get_watchlist_tickers()
    assert tickers.count("AAPL") == 1


async def test_add_ticker_normalizes_case():
    """Ticker should be uppercased and stripped."""
    result = await add_watchlist_ticker("  pypl  ")
    assert result is True
    tickers = await get_watchlist_tickers()
    assert "PYPL" in tickers


async def test_remove_watchlist_ticker_returns_true():
    """Removing an existing ticker should return True."""
    result = await remove_watchlist_ticker("AAPL")
    assert result is True


async def test_remove_watchlist_ticker_removes_from_list():
    """A removed ticker should no longer appear in the watchlist."""
    await remove_watchlist_ticker("AAPL")
    tickers = await get_watchlist_tickers()
    assert "AAPL" not in tickers


async def test_remove_nonexistent_returns_false():
    """Removing a ticker not in the watchlist should return False."""
    result = await remove_watchlist_ticker("PYPL")
    assert result is False


async def test_remove_ticker_normalizes_case():
    """Remove should work with mixed case input."""
    result = await remove_watchlist_ticker("  aapl  ")
    assert result is True
    tickers = await get_watchlist_tickers()
    assert "AAPL" not in tickers


async def test_add_then_remove():
    """Add and then remove a ticker — list should be back to original size."""
    original = await get_watchlist_tickers()
    await add_watchlist_ticker("PYPL")
    await remove_watchlist_ticker("PYPL")
    current = await get_watchlist_tickers()
    assert len(current) == len(original)
    assert "PYPL" not in current


async def test_remove_all_tickers():
    """Removing all tickers should result in an empty list."""
    tickers = await get_watchlist_tickers()
    for t in tickers:
        await remove_watchlist_ticker(t)
    assert await get_watchlist_tickers() == []


async def test_get_watchlist_tickers_different_user():
    """Different user_id should return an empty watchlist (no cross-contamination)."""
    tickers = await get_watchlist_tickers(user_id="other_user")
    assert tickers == []
