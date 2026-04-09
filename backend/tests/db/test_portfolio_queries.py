"""Tests for portfolio, trade execution, and snapshot query functions."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
import uuid

from app.db.connection import get_db
from app.db.queries import (
    get_cash_balance,
    get_positions,
    execute_trade,
    get_portfolio_history,
    record_portfolio_snapshot,
)


# ---------------------------------------------------------------------------
# Cash balance
# ---------------------------------------------------------------------------


async def test_get_cash_balance_default():
    """Default user should start with $10,000."""
    balance = await get_cash_balance()
    assert balance == 10000.0


async def test_get_cash_balance_nonexistent_user():
    """Non-existent user should return the fallback of $10,000."""
    balance = await get_cash_balance(user_id="no_such_user")
    assert balance == 10000.0


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------


async def test_get_positions_initially_empty():
    """No positions should exist after init."""
    positions = await get_positions()
    assert positions == []


# ---------------------------------------------------------------------------
# execute_trade — buys
# ---------------------------------------------------------------------------


async def test_buy_creates_position():
    """Buying shares should create a new position."""
    result = await execute_trade("AAPL", "buy", 10, 150.0)
    assert result["success"] is True
    assert result["error"] is None
    assert result["cash_balance"] == 10000.0 - 10 * 150.0
    assert result["position"]["ticker"] == "AAPL"
    assert result["position"]["quantity"] == 10
    assert result["position"]["avg_cost"] == 150.0


async def test_buy_updates_cash_balance():
    """Cash should decrease by cost of the purchase."""
    await execute_trade("AAPL", "buy", 10, 150.0)
    balance = await get_cash_balance()
    assert balance == pytest.approx(10000.0 - 1500.0)


async def test_buy_position_appears_in_list():
    """Bought position should appear in get_positions."""
    await execute_trade("AAPL", "buy", 5, 100.0)
    positions = await get_positions()
    assert len(positions) == 1
    assert positions[0]["ticker"] == "AAPL"
    assert positions[0]["quantity"] == 5
    assert positions[0]["avg_cost"] == 100.0


async def test_buy_insufficient_cash():
    """Should fail when cost exceeds cash balance."""
    result = await execute_trade("AAPL", "buy", 1000, 100.0)
    assert result["success"] is False
    assert "Insufficient cash" in result["error"]
    assert result["cash_balance"] == 10000.0
    assert result["position"] is None


async def test_buy_exact_cash():
    """Should succeed when cost exactly equals cash balance."""
    result = await execute_trade("AAPL", "buy", 100, 100.0)
    assert result["success"] is True
    assert result["cash_balance"] == pytest.approx(0.0)


async def test_buy_weighted_average_cost():
    """Multiple buys should calculate weighted average cost correctly."""
    # Buy 10 @ $100
    await execute_trade("AAPL", "buy", 10, 100.0)
    # Buy 10 @ $200
    result = await execute_trade("AAPL", "buy", 10, 200.0)

    assert result["success"] is True
    assert result["position"]["quantity"] == 20
    # Weighted avg: (10*100 + 10*200) / 20 = 150
    assert result["position"]["avg_cost"] == pytest.approx(150.0)


async def test_buy_weighted_average_cost_uneven():
    """Weighted average with uneven quantities."""
    # Buy 3 @ $50
    await execute_trade("AAPL", "buy", 3, 50.0)
    # Buy 7 @ $100
    result = await execute_trade("AAPL", "buy", 7, 100.0)

    assert result["position"]["quantity"] == 10
    # (3*50 + 7*100) / 10 = 850/10 = 85
    assert result["position"]["avg_cost"] == pytest.approx(85.0)


async def test_buy_zero_quantity():
    """Buying zero shares should fail."""
    result = await execute_trade("AAPL", "buy", 0, 100.0)
    assert result["success"] is False
    assert "Quantity must be positive" in result["error"]


async def test_buy_negative_quantity():
    """Buying negative shares should fail."""
    result = await execute_trade("AAPL", "buy", -5, 100.0)
    assert result["success"] is False
    assert "Quantity must be positive" in result["error"]


async def test_buy_normalizes_ticker():
    """Ticker should be uppercased and stripped."""
    result = await execute_trade("  aapl  ", "buy", 1, 100.0)
    assert result["success"] is True
    assert result["position"]["ticker"] == "AAPL"


# ---------------------------------------------------------------------------
# execute_trade — sells
# ---------------------------------------------------------------------------


async def test_sell_reduces_position():
    """Selling part of a position should reduce quantity."""
    await execute_trade("AAPL", "buy", 10, 100.0)
    result = await execute_trade("AAPL", "sell", 3, 120.0)

    assert result["success"] is True
    assert result["position"]["quantity"] == 7
    # avg_cost should remain unchanged on a sell
    assert result["position"]["avg_cost"] == pytest.approx(100.0)


async def test_sell_increases_cash():
    """Selling should increase cash by sale proceeds."""
    await execute_trade("AAPL", "buy", 10, 100.0)
    await execute_trade("AAPL", "sell", 5, 120.0)
    balance = await get_cash_balance()
    # Started with 10k, spent 1000 buying, got 600 selling
    assert balance == pytest.approx(10000.0 - 1000.0 + 600.0)


async def test_sell_entire_position_deletes_row():
    """Selling all shares should delete the position row."""
    await execute_trade("AAPL", "buy", 10, 100.0)
    result = await execute_trade("AAPL", "sell", 10, 120.0)

    assert result["success"] is True
    assert result["position"] is None

    positions = await get_positions()
    assert len(positions) == 0


async def test_sell_insufficient_shares():
    """Should fail when trying to sell more than owned."""
    await execute_trade("AAPL", "buy", 5, 100.0)
    result = await execute_trade("AAPL", "sell", 10, 120.0)

    assert result["success"] is False
    assert "Insufficient shares" in result["error"]


async def test_sell_no_position():
    """Should fail when trying to sell a stock not owned."""
    result = await execute_trade("AAPL", "sell", 5, 100.0)
    assert result["success"] is False
    assert "Insufficient shares" in result["error"]


async def test_sell_at_loss():
    """Selling at a loss should still succeed and update cash correctly."""
    await execute_trade("AAPL", "buy", 10, 100.0)
    result = await execute_trade("AAPL", "sell", 10, 80.0)

    assert result["success"] is True
    balance = await get_cash_balance()
    # 10k - 1000 + 800 = 9800
    assert balance == pytest.approx(9800.0)


async def test_sell_zero_quantity():
    """Selling zero shares should fail."""
    result = await execute_trade("AAPL", "sell", 0, 100.0)
    assert result["success"] is False


# ---------------------------------------------------------------------------
# execute_trade — invalid side
# ---------------------------------------------------------------------------


async def test_invalid_side():
    """Invalid trade side should fail."""
    result = await execute_trade("AAPL", "hold", 5, 100.0)
    assert result["success"] is False
    assert "Invalid side" in result["error"]


# ---------------------------------------------------------------------------
# execute_trade — trade history
# ---------------------------------------------------------------------------


async def test_trade_recorded_in_trades_table():
    """Executed trades should appear in the trades table."""
    await execute_trade("AAPL", "buy", 5, 100.0)

    async with get_db() as db:
        async with db.execute("SELECT * FROM trades") as cur:
            rows = await cur.fetchall()

    assert len(rows) == 1
    assert rows[0]["ticker"] == "AAPL"
    assert rows[0]["side"] == "buy"
    assert rows[0]["quantity"] == 5
    assert rows[0]["price"] == 100.0


async def test_failed_trade_not_recorded():
    """Failed trades should NOT appear in the trades table."""
    await execute_trade("AAPL", "buy", 10000, 100.0)  # insufficient cash

    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) as cnt FROM trades") as cur:
            row = await cur.fetchone()

    assert row["cnt"] == 0


# ---------------------------------------------------------------------------
# Multiple tickers
# ---------------------------------------------------------------------------


async def test_multiple_positions():
    """Should handle positions in multiple tickers independently."""
    await execute_trade("AAPL", "buy", 5, 100.0)
    await execute_trade("GOOGL", "buy", 3, 200.0)

    positions = await get_positions()
    assert len(positions) == 2
    tickers = {p["ticker"] for p in positions}
    assert tickers == {"AAPL", "GOOGL"}


# ---------------------------------------------------------------------------
# Portfolio snapshots
# ---------------------------------------------------------------------------


async def test_record_and_get_snapshot():
    """Recording a snapshot should be retrievable via get_portfolio_history."""
    await record_portfolio_snapshot(12000.0)
    history = await get_portfolio_history()

    assert len(history) == 1
    assert history[0]["total_value"] == 12000.0
    assert "recorded_at" in history[0]


async def test_multiple_snapshots_ordered():
    """Snapshots should be returned in chronological order."""
    await record_portfolio_snapshot(10000.0)
    await record_portfolio_snapshot(10500.0)
    await record_portfolio_snapshot(11000.0)

    history = await get_portfolio_history()
    assert len(history) == 3
    values = [h["total_value"] for h in history]
    assert values == [10000.0, 10500.0, 11000.0]


async def test_snapshot_pruning():
    """Snapshots older than 24 hours should be pruned when a new one is recorded."""
    # Insert an old snapshot directly
    old_time = (datetime.now(tz=timezone.utc) - timedelta(hours=25)).isoformat()
    async with get_db() as db:
        await db.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), "default", 9000.0, old_time),
        )
        await db.commit()

    # Verify the old snapshot is there
    history = await get_portfolio_history()
    assert len(history) == 1

    # Record a new snapshot — should trigger pruning of the old one
    await record_portfolio_snapshot(11000.0)

    history = await get_portfolio_history()
    assert len(history) == 1
    assert history[0]["total_value"] == 11000.0


async def test_snapshot_pruning_keeps_recent():
    """Recent snapshots should NOT be pruned."""
    recent_time = (datetime.now(tz=timezone.utc) - timedelta(hours=23)).isoformat()
    async with get_db() as db:
        await db.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), "default", 9500.0, recent_time),
        )
        await db.commit()

    await record_portfolio_snapshot(11000.0)

    history = await get_portfolio_history()
    assert len(history) == 2


async def test_snapshot_empty_history():
    """No snapshots should return an empty list."""
    history = await get_portfolio_history()
    assert history == []
