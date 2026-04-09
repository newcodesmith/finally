"""Tests for /api/portfolio endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch


# ---------------------------------------------------------------------------
# GET /api/portfolio
# ---------------------------------------------------------------------------


class TestGetPortfolio:
    async def test_empty_portfolio(self, client, price_cache):
        with (
            patch("app.api.portfolio.get_cash_balance", new_callable=AsyncMock, return_value=10000.0),
            patch("app.api.portfolio.get_positions", new_callable=AsyncMock, return_value=[]),
        ):
            resp = await client.get("/api/portfolio")

        assert resp.status_code == 200
        data = resp.json()
        assert data["cash_balance"] == 10000.0
        assert data["positions"] == []
        assert data["total_value"] == 10000.0

    async def test_portfolio_with_positions(self, client, price_cache):
        price_cache.get_price.side_effect = lambda t: {"AAPL": 200.0, "GOOGL": 180.0}.get(t)

        positions = [
            {"ticker": "AAPL", "quantity": 10, "avg_cost": 190.0},
            {"ticker": "GOOGL", "quantity": 5, "avg_cost": 170.0},
        ]
        with (
            patch("app.api.portfolio.get_cash_balance", new_callable=AsyncMock, return_value=5000.0),
            patch("app.api.portfolio.get_positions", new_callable=AsyncMock, return_value=positions),
        ):
            resp = await client.get("/api/portfolio")

        data = resp.json()
        assert data["cash_balance"] == 5000.0
        assert len(data["positions"]) == 2

        aapl = data["positions"][0]
        assert aapl["ticker"] == "AAPL"
        assert aapl["current_price"] == 200.0
        assert aapl["unrealized_pnl"] == 100.0  # (200-190)*10
        assert aapl["value"] == 2000.0

        googl = data["positions"][1]
        assert googl["ticker"] == "GOOGL"
        assert googl["current_price"] == 180.0
        assert googl["unrealized_pnl"] == 50.0  # (180-170)*5
        assert googl["value"] == 900.0

        # total = cash + AAPL(2000) + GOOGL(900)
        assert data["total_value"] == 7900.0

    async def test_portfolio_falls_back_to_avg_cost_when_no_price(self, client, price_cache):
        """When price_cache has no price for a ticker, use avg_cost."""
        price_cache.get_price.return_value = None

        positions = [{"ticker": "XYZ", "quantity": 10, "avg_cost": 50.0}]
        with (
            patch("app.api.portfolio.get_cash_balance", new_callable=AsyncMock, return_value=9500.0),
            patch("app.api.portfolio.get_positions", new_callable=AsyncMock, return_value=positions),
        ):
            resp = await client.get("/api/portfolio")

        data = resp.json()
        xyz = data["positions"][0]
        assert xyz["current_price"] == 50.0  # fell back to avg_cost
        assert xyz["unrealized_pnl"] == 0.0
        assert xyz["pnl_percent"] == 0.0

    async def test_portfolio_pnl_percent_calculation(self, client, price_cache):
        price_cache.get_price.return_value = 95.0

        positions = [{"ticker": "BAD", "quantity": 4, "avg_cost": 100.0}]
        with (
            patch("app.api.portfolio.get_cash_balance", new_callable=AsyncMock, return_value=9600.0),
            patch("app.api.portfolio.get_positions", new_callable=AsyncMock, return_value=positions),
        ):
            resp = await client.get("/api/portfolio")

        pos = resp.json()["positions"][0]
        # (95-100)/100 * 100 = -5.0
        assert pos["pnl_percent"] == -5.0
        assert pos["unrealized_pnl"] == -20.0  # (95-100)*4


# ---------------------------------------------------------------------------
# POST /api/portfolio/trade
# ---------------------------------------------------------------------------


class TestTrade:
    async def test_buy_success(self, client, price_cache, market_source):
        price_cache.get_price.return_value = 150.0

        trade_result = {
            "success": True,
            "error": None,
            "cash_balance": 8500.0,
            "position": {"ticker": "AAPL", "quantity": 10, "avg_cost": 150.0},
        }
        with (
            patch("app.api.portfolio.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"]),
            patch("app.api.portfolio.execute_trade", new_callable=AsyncMock, return_value=trade_result),
            patch("app.api.portfolio.get_positions", new_callable=AsyncMock, return_value=[]),
            patch("app.api.portfolio.record_portfolio_snapshot", new_callable=AsyncMock),
        ):
            resp = await client.post("/api/portfolio/trade", json={
                "ticker": "AAPL",
                "side": "buy",
                "quantity": 10,
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["ticker"] == "AAPL"
        assert data["side"] == "buy"
        assert data["quantity"] == 10
        assert data["price"] == 150.0
        assert data["cash_balance"] == 8500.0

    async def test_sell_success(self, client, price_cache, market_source):
        price_cache.get_price.return_value = 200.0

        trade_result = {
            "success": True,
            "error": None,
            "cash_balance": 12000.0,
            "position": {"ticker": "AAPL", "quantity": 5, "avg_cost": 150.0},
        }
        with (
            patch("app.api.portfolio.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"]),
            patch("app.api.portfolio.execute_trade", new_callable=AsyncMock, return_value=trade_result),
            patch("app.api.portfolio.get_positions", new_callable=AsyncMock, return_value=[]),
            patch("app.api.portfolio.record_portfolio_snapshot", new_callable=AsyncMock),
        ):
            resp = await client.post("/api/portfolio/trade", json={
                "ticker": "AAPL",
                "side": "sell",
                "quantity": 5,
            })

        data = resp.json()
        assert data["success"] is True
        assert data["side"] == "sell"

    async def test_invalid_side_returns_422(self, client, price_cache):
        resp = await client.post("/api/portfolio/trade", json={
            "ticker": "AAPL",
            "side": "short",
            "quantity": 10,
        })
        assert resp.status_code == 422

    async def test_zero_quantity_returns_422(self, client, price_cache):
        resp = await client.post("/api/portfolio/trade", json={
            "ticker": "AAPL",
            "side": "buy",
            "quantity": 0,
        })
        assert resp.status_code == 422

    async def test_negative_quantity_returns_422(self, client, price_cache):
        resp = await client.post("/api/portfolio/trade", json={
            "ticker": "AAPL",
            "side": "buy",
            "quantity": -5,
        })
        assert resp.status_code == 422

    async def test_insufficient_cash(self, client, price_cache, market_source):
        price_cache.get_price.return_value = 1000.0

        trade_result = {
            "success": False,
            "error": "Insufficient cash: need $10000.00, have $5000.00",
            "cash_balance": 5000.0,
            "position": None,
        }
        with (
            patch("app.api.portfolio.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"]),
            patch("app.api.portfolio.execute_trade", new_callable=AsyncMock, return_value=trade_result),
        ):
            resp = await client.post("/api/portfolio/trade", json={
                "ticker": "AAPL",
                "side": "buy",
                "quantity": 10,
            })

        data = resp.json()
        assert data["success"] is False
        assert "Insufficient cash" in data["error"]

    async def test_insufficient_shares(self, client, price_cache, market_source):
        price_cache.get_price.return_value = 150.0

        trade_result = {
            "success": False,
            "error": "Insufficient shares: trying to sell 100, own 5",
            "cash_balance": 10000.0,
            "position": None,
        }
        with (
            patch("app.api.portfolio.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"]),
            patch("app.api.portfolio.execute_trade", new_callable=AsyncMock, return_value=trade_result),
        ):
            resp = await client.post("/api/portfolio/trade", json={
                "ticker": "AAPL",
                "side": "sell",
                "quantity": 100,
            })

        data = resp.json()
        assert data["success"] is False
        assert "Insufficient shares" in data["error"]

    async def test_no_price_available_returns_422(self, client, price_cache, market_source):
        price_cache.get_price.return_value = None

        with patch(
            "app.api.portfolio.get_watchlist_tickers",
            new_callable=AsyncMock,
            return_value=["AAPL"],
        ):
            resp = await client.post("/api/portfolio/trade", json={
                "ticker": "AAPL",
                "side": "buy",
                "quantity": 10,
            })

        assert resp.status_code == 422
        assert "No price available" in resp.json()["detail"]

    async def test_ticker_uppercased_and_stripped(self, client, price_cache, market_source):
        price_cache.get_price.return_value = 100.0

        trade_result = {
            "success": True,
            "error": None,
            "cash_balance": 9000.0,
            "position": {"ticker": "MSFT", "quantity": 10, "avg_cost": 100.0},
        }
        with (
            patch("app.api.portfolio.get_watchlist_tickers", new_callable=AsyncMock, return_value=["MSFT"]),
            patch("app.api.portfolio.execute_trade", new_callable=AsyncMock, return_value=trade_result),
            patch("app.api.portfolio.get_positions", new_callable=AsyncMock, return_value=[]),
            patch("app.api.portfolio.record_portfolio_snapshot", new_callable=AsyncMock),
        ):
            resp = await client.post("/api/portfolio/trade", json={
                "ticker": "  msft  ",
                "side": "buy",
                "quantity": 10,
            })

        data = resp.json()
        assert data["ticker"] == "MSFT"

    async def test_auto_add_to_watchlist_when_not_present(self, client, price_cache, market_source):
        """Trading a ticker not on the watchlist should auto-add it."""
        price_cache.get_price.return_value = 50.0

        trade_result = {
            "success": True,
            "error": None,
            "cash_balance": 9500.0,
            "position": {"ticker": "PYPL", "quantity": 10, "avg_cost": 50.0},
        }
        mock_add = AsyncMock(return_value=True)
        with (
            patch("app.api.portfolio.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"]),
            patch("app.api.portfolio.add_watchlist_ticker", mock_add),
            patch("app.api.portfolio.execute_trade", new_callable=AsyncMock, return_value=trade_result),
            patch("app.api.portfolio.get_positions", new_callable=AsyncMock, return_value=[]),
            patch("app.api.portfolio.record_portfolio_snapshot", new_callable=AsyncMock),
        ):
            resp = await client.post("/api/portfolio/trade", json={
                "ticker": "PYPL",
                "side": "buy",
                "quantity": 10,
            })

        assert resp.json()["success"] is True
        mock_add.assert_awaited_once_with("PYPL")
        market_source.add_ticker.assert_awaited_once_with("PYPL")

    async def test_no_auto_add_when_already_in_watchlist(self, client, price_cache, market_source):
        price_cache.get_price.return_value = 150.0

        trade_result = {
            "success": True,
            "error": None,
            "cash_balance": 8500.0,
            "position": {"ticker": "AAPL", "quantity": 10, "avg_cost": 150.0},
        }
        mock_add = AsyncMock(return_value=True)
        with (
            patch("app.api.portfolio.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"]),
            patch("app.api.portfolio.add_watchlist_ticker", mock_add),
            patch("app.api.portfolio.execute_trade", new_callable=AsyncMock, return_value=trade_result),
            patch("app.api.portfolio.get_positions", new_callable=AsyncMock, return_value=[]),
            patch("app.api.portfolio.record_portfolio_snapshot", new_callable=AsyncMock),
        ):
            resp = await client.post("/api/portfolio/trade", json={
                "ticker": "AAPL",
                "side": "buy",
                "quantity": 10,
            })

        assert resp.json()["success"] is True
        mock_add.assert_not_awaited()

    async def test_post_trade_snapshot_recorded(self, client, price_cache, market_source):
        price_cache.get_price.return_value = 100.0

        trade_result = {
            "success": True,
            "error": None,
            "cash_balance": 9000.0,
            "position": {"ticker": "AAPL", "quantity": 10, "avg_cost": 100.0},
        }
        positions_after = [{"ticker": "AAPL", "quantity": 10, "avg_cost": 100.0}]
        mock_snapshot = AsyncMock()

        with (
            patch("app.api.portfolio.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"]),
            patch("app.api.portfolio.execute_trade", new_callable=AsyncMock, return_value=trade_result),
            patch("app.api.portfolio.get_positions", new_callable=AsyncMock, return_value=positions_after),
            patch("app.api.portfolio.record_portfolio_snapshot", mock_snapshot),
        ):
            resp = await client.post("/api/portfolio/trade", json={
                "ticker": "AAPL",
                "side": "buy",
                "quantity": 10,
            })

        assert resp.json()["success"] is True
        # Snapshot should be recorded: cash(9000) + AAPL(10 * 100) = 10000
        mock_snapshot.assert_awaited_once_with(10000.0)

    async def test_snapshot_failure_does_not_break_trade(self, client, price_cache, market_source):
        """If snapshot recording fails, the trade response should still succeed."""
        price_cache.get_price.return_value = 100.0

        trade_result = {
            "success": True,
            "error": None,
            "cash_balance": 9000.0,
            "position": {"ticker": "AAPL", "quantity": 10, "avg_cost": 100.0},
        }
        with (
            patch("app.api.portfolio.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"]),
            patch("app.api.portfolio.execute_trade", new_callable=AsyncMock, return_value=trade_result),
            patch("app.api.portfolio.get_positions", new_callable=AsyncMock, side_effect=RuntimeError("db error")),
            patch("app.api.portfolio.record_portfolio_snapshot", new_callable=AsyncMock),
        ):
            resp = await client.post("/api/portfolio/trade", json={
                "ticker": "AAPL",
                "side": "buy",
                "quantity": 10,
            })

        # Trade itself still succeeds
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_failed_trade_does_not_record_snapshot(self, client, price_cache, market_source):
        price_cache.get_price.return_value = 1000.0

        trade_result = {
            "success": False,
            "error": "Insufficient cash",
            "cash_balance": 5000.0,
            "position": None,
        }
        mock_snapshot = AsyncMock()
        with (
            patch("app.api.portfolio.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"]),
            patch("app.api.portfolio.execute_trade", new_callable=AsyncMock, return_value=trade_result),
            patch("app.api.portfolio.record_portfolio_snapshot", mock_snapshot),
        ):
            resp = await client.post("/api/portfolio/trade", json={
                "ticker": "AAPL",
                "side": "buy",
                "quantity": 10,
            })

        assert resp.json()["success"] is False
        mock_snapshot.assert_not_awaited()

    async def test_fractional_shares(self, client, price_cache, market_source):
        price_cache.get_price.return_value = 200.0

        trade_result = {
            "success": True,
            "error": None,
            "cash_balance": 9900.0,
            "position": {"ticker": "AAPL", "quantity": 0.5, "avg_cost": 200.0},
        }
        with (
            patch("app.api.portfolio.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"]),
            patch("app.api.portfolio.execute_trade", new_callable=AsyncMock, return_value=trade_result),
            patch("app.api.portfolio.get_positions", new_callable=AsyncMock, return_value=[]),
            patch("app.api.portfolio.record_portfolio_snapshot", new_callable=AsyncMock),
        ):
            resp = await client.post("/api/portfolio/trade", json={
                "ticker": "AAPL",
                "side": "buy",
                "quantity": 0.5,
            })

        data = resp.json()
        assert data["success"] is True
        assert data["quantity"] == 0.5

    async def test_missing_fields_returns_422(self, client):
        resp = await client.post("/api/portfolio/trade", json={"ticker": "AAPL"})
        assert resp.status_code == 422

    async def test_trade_response_shape(self, client, price_cache, market_source):
        """Verify all expected keys are in the response."""
        price_cache.get_price.return_value = 150.0

        trade_result = {
            "success": True,
            "error": None,
            "cash_balance": 8500.0,
            "position": {"ticker": "AAPL", "quantity": 10, "avg_cost": 150.0},
        }
        with (
            patch("app.api.portfolio.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"]),
            patch("app.api.portfolio.execute_trade", new_callable=AsyncMock, return_value=trade_result),
            patch("app.api.portfolio.get_positions", new_callable=AsyncMock, return_value=[]),
            patch("app.api.portfolio.record_portfolio_snapshot", new_callable=AsyncMock),
        ):
            resp = await client.post("/api/portfolio/trade", json={
                "ticker": "AAPL",
                "side": "buy",
                "quantity": 10,
            })

        data = resp.json()
        expected_keys = {"success", "error", "ticker", "side", "quantity", "price", "cash_balance", "position"}
        assert set(data.keys()) == expected_keys


# ---------------------------------------------------------------------------
# GET /api/portfolio/history
# ---------------------------------------------------------------------------


class TestPortfolioHistory:
    async def test_empty_history(self, client):
        with patch(
            "app.api.portfolio.get_portfolio_history",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await client.get("/api/portfolio/history")

        assert resp.status_code == 200
        assert resp.json() == []

    async def test_history_returns_snapshots(self, client):
        snapshots = [
            {"recorded_at": "2026-04-09T12:00:00+00:00", "total_value": 10000.0},
            {"recorded_at": "2026-04-09T12:00:30+00:00", "total_value": 10050.0},
        ]
        with patch(
            "app.api.portfolio.get_portfolio_history",
            new_callable=AsyncMock,
            return_value=snapshots,
        ):
            resp = await client.get("/api/portfolio/history")

        data = resp.json()
        assert len(data) == 2
        assert data[0]["total_value"] == 10000.0
        assert data[1]["total_value"] == 10050.0
        assert data[0]["recorded_at"] == "2026-04-09T12:00:00+00:00"
