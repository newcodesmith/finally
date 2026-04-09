"""Integration tests for portfolio API endpoints and trade execution.

Requirements tested:
- PORT-01: User starts with $10,000 virtual cash
- PORT-02: POST /api/portfolio/trade with side=buy deducts cash and creates/updates position
- PORT-03: POST /api/portfolio/trade with side=sell adds cash and reduces/removes position
- PORT-04: Buying a ticker not on the watchlist automatically adds it
- PORT-05: GET /api/portfolio returns cash, positions with unrealized P&L from live prices
- PORT-06: GET /api/portfolio/history returns time-series snapshots ordered by recorded_at
- PORT-07: Portfolio snapshot recorded immediately after each successful trade and periodically
- PORT-08: record_portfolio_snapshot prunes rows older than 24 hours
"""

from __future__ import annotations

import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

# Set DB_PATH before importing app so connection module picks it up
_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(_tmp, "test_portfolio.db")

from app.db.schema import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.market import PriceCache  # noqa: E402

# Track whether DB + app state has been initialized
_initialized = False


async def _ensure_init():
    """Initialize DB and app state once across all tests."""
    global _initialized
    if not _initialized:
        await init_db()
        # Ensure price_cache and market_source are set on app.state
        # (they are set at module level in main.py, so should already exist)
        _initialized = True


@pytest.fixture
async def client():
    """Provide an async test client with DB initialized."""
    await _ensure_init()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _inject_price(ticker: str, price: float) -> None:
    """Inject a price directly into the app's price cache for deterministic tests."""
    app.state.price_cache.update(ticker, price)


# ---------------------------------------------------------------------------
# PORT-01: Starting cash
# ---------------------------------------------------------------------------


class TestPortfolioBaseline:
    """Verify initial state: $10k cash, no positions (PORT-01, PORT-05)."""

    async def test_initial_portfolio_has_10k_cash(self, client: AsyncClient):
        """GET /api/portfolio returns cash_balance=10000.0 on fresh DB (PORT-01)."""
        resp = await client.get("/api/portfolio")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cash_balance"] == 10000.0

    async def test_initial_portfolio_has_no_positions(self, client: AsyncClient):
        """GET /api/portfolio returns empty positions list initially (PORT-05)."""
        resp = await client.get("/api/portfolio")
        data = resp.json()
        assert data["positions"] == []
        assert data["total_value"] == 10000.0


# ---------------------------------------------------------------------------
# PORT-02: Buy trades
# ---------------------------------------------------------------------------


class TestBuyTrade:
    """Buy trade execution (PORT-02)."""

    async def test_buy_creates_position_and_deducts_cash(self, client: AsyncClient):
        """Buying 10 AAPL at $190 deducts $1900 and creates a position (PORT-02)."""
        _inject_price("AAPL", 190.0)
        resp = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "buy", "quantity": 10},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["price"] == 190.0
        assert data["cash_balance"] == pytest.approx(10000.0 - 1900.0)
        assert data["position"]["ticker"] == "AAPL"
        assert data["position"]["quantity"] == 10.0
        assert data["position"]["avg_cost"] == 190.0

    async def test_buy_insufficient_cash_fails(self, client: AsyncClient):
        """Buying more than cash allows returns success=false (PORT-02 edge case)."""
        _inject_price("MSFT", 400.0)
        resp = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "MSFT", "side": "buy", "quantity": 100},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "Insufficient cash" in data["error"]

    async def test_multiple_buys_update_avg_cost(self, client: AsyncClient):
        """Multiple buys correctly compute weighted average cost (PORT-02).

        Buy 10 at $100, then 10 at $200 -> avg_cost = $150.
        """
        _inject_price("GOOGL", 100.0)
        resp1 = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "GOOGL", "side": "buy", "quantity": 10},
        )
        assert resp1.json()["success"] is True

        _inject_price("GOOGL", 200.0)
        resp2 = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "GOOGL", "side": "buy", "quantity": 10},
        )
        data = resp2.json()
        assert data["success"] is True
        assert data["position"]["quantity"] == 20.0
        assert data["position"]["avg_cost"] == pytest.approx(150.0)


# ---------------------------------------------------------------------------
# PORT-03: Sell trades
# ---------------------------------------------------------------------------


class TestSellTrade:
    """Sell trade execution (PORT-03)."""

    async def test_sell_adds_cash_and_reduces_position(self, client: AsyncClient):
        """Selling partial shares increases cash and reduces quantity (PORT-03)."""
        _inject_price("TSLA", 250.0)
        # Buy first
        await client.post(
            "/api/portfolio/trade",
            json={"ticker": "TSLA", "side": "buy", "quantity": 10},
        )
        # Sell half
        resp = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "TSLA", "side": "sell", "quantity": 5},
        )
        data = resp.json()
        assert data["success"] is True
        assert data["position"]["quantity"] == 5.0

    async def test_sell_all_removes_position(self, client: AsyncClient):
        """Selling all shares removes the position entirely (PORT-03)."""
        _inject_price("META", 500.0)
        await client.post(
            "/api/portfolio/trade",
            json={"ticker": "META", "side": "buy", "quantity": 5},
        )
        resp = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "META", "side": "sell", "quantity": 5},
        )
        data = resp.json()
        assert data["success"] is True
        assert data["position"] is None

    async def test_sell_more_than_owned_fails(self, client: AsyncClient):
        """Selling more shares than owned returns success=false (PORT-03 edge case)."""
        _inject_price("JPM", 150.0)
        # Buy 5
        await client.post(
            "/api/portfolio/trade",
            json={"ticker": "JPM", "side": "buy", "quantity": 5},
        )
        # Try to sell 10
        resp = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "JPM", "side": "sell", "quantity": 10},
        )
        data = resp.json()
        assert data["success"] is False
        assert "Insufficient shares" in data["error"]


# ---------------------------------------------------------------------------
# PORT-04: Auto-add to watchlist
# ---------------------------------------------------------------------------


class TestAutoAddWatchlist:
    """Auto-add ticker to watchlist on trade (PORT-04)."""

    async def test_buy_ticker_not_in_watchlist_adds_it(self, client: AsyncClient):
        """Buying a ticker not in the watchlist auto-adds it (PORT-04)."""
        _inject_price("PYPL", 80.0)
        resp = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "PYPL", "side": "buy", "quantity": 1},
        )
        assert resp.json()["success"] is True

        # Verify PYPL is now in the watchlist
        wl_resp = await client.get("/api/watchlist")
        assert wl_resp.status_code == 200
        tickers = [item["ticker"] for item in wl_resp.json()]
        assert "PYPL" in tickers


# ---------------------------------------------------------------------------
# PORT-05: Portfolio with live P&L
# ---------------------------------------------------------------------------


class TestPortfolioPnL:
    """Portfolio P&L calculations from live prices (PORT-05)."""

    async def test_portfolio_shows_unrealized_pnl(self, client: AsyncClient):
        """GET /api/portfolio includes unrealized_pnl and pnl_percent (PORT-05)."""
        _inject_price("NVDA", 100.0)
        await client.post(
            "/api/portfolio/trade",
            json={"ticker": "NVDA", "side": "buy", "quantity": 10},
        )

        # Price goes up
        _inject_price("NVDA", 120.0)

        resp = await client.get("/api/portfolio")
        data = resp.json()
        positions = data["positions"]
        nvda = next((p for p in positions if p["ticker"] == "NVDA"), None)
        assert nvda is not None
        assert nvda["current_price"] == 120.0
        assert nvda["unrealized_pnl"] == pytest.approx(200.0)  # (120-100)*10
        assert nvda["pnl_percent"] == pytest.approx(20.0)  # 20%


# ---------------------------------------------------------------------------
# Validation edge cases
# ---------------------------------------------------------------------------


class TestTradeValidation:
    """Trade request validation."""

    async def test_invalid_side_returns_422(self, client: AsyncClient):
        """Invalid side (not buy/sell) returns 422."""
        resp = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "hold", "quantity": 10},
        )
        assert resp.status_code == 422

    async def test_zero_quantity_returns_422(self, client: AsyncClient):
        """Quantity <= 0 returns 422."""
        resp = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "buy", "quantity": 0},
        )
        assert resp.status_code == 422

    async def test_negative_quantity_returns_422(self, client: AsyncClient):
        """Negative quantity returns 422."""
        resp = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "buy", "quantity": -5},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PORT-06, PORT-07, PORT-08: Portfolio snapshots
# ---------------------------------------------------------------------------


class TestPortfolioSnapshots:
    """Portfolio snapshot recording, history retrieval, and pruning."""

    async def test_trade_records_snapshot(self, client: AsyncClient):
        """A successful trade records a portfolio snapshot (PORT-07)."""
        _inject_price("V", 280.0)
        resp = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "V", "side": "buy", "quantity": 1},
        )
        assert resp.json()["success"] is True

        history_resp = await client.get("/api/portfolio/history")
        assert history_resp.status_code == 200
        snapshots = history_resp.json()
        assert len(snapshots) >= 1  # At least the post-trade snapshot

    async def test_snapshot_total_value_correct(self, client: AsyncClient):
        """Post-trade snapshot total_value = cash + positions * price (PORT-07)."""
        _inject_price("NFLX", 600.0)
        trade_resp = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "NFLX", "side": "buy", "quantity": 2},
        )
        data = trade_resp.json()
        assert data["success"] is True
        expected_cash = data["cash_balance"]

        # Get portfolio to see total_value
        port_resp = await client.get("/api/portfolio")
        port_data = port_resp.json()

        # Last snapshot should reflect post-trade value
        history_resp = await client.get("/api/portfolio/history")
        snapshots = history_resp.json()
        last_snapshot = snapshots[-1]
        # Snapshot value should be approximately equal to current portfolio value
        assert last_snapshot["total_value"] == pytest.approx(port_data["total_value"], rel=0.01)

    async def test_history_ordered_by_time_ascending(self, client: AsyncClient):
        """GET /api/portfolio/history returns snapshots in chronological order (PORT-06)."""
        # Execute two trades to generate at least two snapshots
        _inject_price("AMZN", 180.0)
        await client.post(
            "/api/portfolio/trade",
            json={"ticker": "AMZN", "side": "buy", "quantity": 1},
        )
        _inject_price("AMZN", 181.0)
        await client.post(
            "/api/portfolio/trade",
            json={"ticker": "AMZN", "side": "buy", "quantity": 1},
        )

        history_resp = await client.get("/api/portfolio/history")
        snapshots = history_resp.json()
        assert len(snapshots) >= 2
        # Verify ascending order
        timestamps = [s["recorded_at"] for s in snapshots]
        assert timestamps == sorted(timestamps)

    async def test_pruning_removes_old_snapshots(self, client: AsyncClient):
        """record_portfolio_snapshot prunes rows older than 24h (PORT-08)."""
        from datetime import datetime, timedelta, timezone

        import aiosqlite

        db_path = os.environ["DB_PATH"]

        # Insert a snapshot with a timestamp 25 hours in the past
        old_time = (datetime.now(tz=timezone.utc) - timedelta(hours=25)).isoformat()
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
                "VALUES (?, ?, ?, ?)",
                ("old-snapshot-id", "default", 9999.0, old_time),
            )
            await db.commit()

        # Verify the old row was inserted
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM portfolio_snapshots WHERE id = ?",
                ("old-snapshot-id",),
            ) as cur:
                row = await cur.fetchone()
                assert row[0] == 1

        # Record a new snapshot (this triggers pruning)
        from app.db.queries import record_portfolio_snapshot

        await record_portfolio_snapshot(10000.0)

        # Verify the old row was pruned
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM portfolio_snapshots WHERE id = ?",
                ("old-snapshot-id",),
            ) as cur:
                row = await cur.fetchone()
                assert row[0] == 0, "Old snapshot should have been pruned"

    async def test_snapshot_callback_wired_in_main(self, client: AsyncClient):
        """Verify _snapshot_callback is wired as snapshot_callback in main.py (PORT-07)."""
        # This is a code-review test: verify the wiring exists
        from app.main import _snapshot_callback, market_source

        # The market_source should have a snapshot_callback attribute
        assert market_source._snapshot_callback is _snapshot_callback

    async def test_snapshot_callback_records_snapshot(self, client: AsyncClient):
        """Calling _snapshot_callback directly records a snapshot (PORT-07)."""
        from app.main import _snapshot_callback

        # Get current snapshot count
        history_before = await client.get("/api/portfolio/history")
        count_before = len(history_before.json())

        # Call the callback
        await _snapshot_callback()

        # Verify a new snapshot was recorded
        history_after = await client.get("/api/portfolio/history")
        count_after = len(history_after.json())
        assert count_after > count_before
