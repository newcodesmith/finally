"""Tests for /api/watchlist endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from tests.api.conftest import make_price_update


# ---------------------------------------------------------------------------
# GET /api/watchlist
# ---------------------------------------------------------------------------


class TestGetWatchlist:
    async def test_empty_watchlist(self, client):
        with patch("app.api.watchlist.get_watchlist_tickers", new_callable=AsyncMock, return_value=[]):
            resp = await client.get("/api/watchlist")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_tickers_with_prices(self, client, price_cache):
        aapl_update = make_price_update("AAPL", 190.0, 189.5, 188.0)
        price_cache.get.side_effect = lambda t: aapl_update if t == "AAPL" else None

        with patch(
            "app.api.watchlist.get_watchlist_tickers",
            new_callable=AsyncMock,
            return_value=["AAPL"],
        ):
            resp = await client.get("/api/watchlist")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["ticker"] == "AAPL"
        assert data[0]["price"] == 190.0
        assert data[0]["previous_price"] == 189.5
        assert data[0]["session_open_price"] == 188.0
        assert data[0]["change_direction"] == "up"

    async def test_ticker_without_price_returns_nulls(self, client, price_cache):
        price_cache.get.return_value = None

        with patch(
            "app.api.watchlist.get_watchlist_tickers",
            new_callable=AsyncMock,
            return_value=["XYZ"],
        ):
            resp = await client.get("/api/watchlist")

        data = resp.json()
        assert len(data) == 1
        entry = data[0]
        assert entry["ticker"] == "XYZ"
        assert entry["price"] is None
        assert entry["previous_price"] is None
        assert entry["session_open_price"] is None
        assert entry["change_direction"] == "unchanged"
        assert entry["timestamp"] is None

    async def test_multiple_tickers_mixed(self, client, price_cache):
        """Some tickers have prices, some don't."""
        msft_update = make_price_update("MSFT", 420.0)
        price_cache.get.side_effect = lambda t: msft_update if t == "MSFT" else None

        with patch(
            "app.api.watchlist.get_watchlist_tickers",
            new_callable=AsyncMock,
            return_value=["MSFT", "UNKNOWN"],
        ):
            resp = await client.get("/api/watchlist")

        data = resp.json()
        assert len(data) == 2
        assert data[0]["ticker"] == "MSFT"
        assert data[0]["price"] == 420.0
        assert data[1]["ticker"] == "UNKNOWN"
        assert data[1]["price"] is None


# ---------------------------------------------------------------------------
# POST /api/watchlist
# ---------------------------------------------------------------------------


class TestAddToWatchlist:
    async def test_add_new_ticker(self, client, market_source):
        with patch(
            "app.api.watchlist.add_watchlist_ticker",
            new_callable=AsyncMock,
            return_value=True,
        ):
            resp = await client.post("/api/watchlist", json={"ticker": "PYPL"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "PYPL"
        assert data["added"] is True
        market_source.add_ticker.assert_awaited_once_with("PYPL")

    async def test_add_duplicate_ticker(self, client, market_source):
        with patch(
            "app.api.watchlist.add_watchlist_ticker",
            new_callable=AsyncMock,
            return_value=False,
        ):
            resp = await client.post("/api/watchlist", json={"ticker": "AAPL"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["added"] is False
        # Should NOT call market_source when ticker was already present
        market_source.add_ticker.assert_not_awaited()

    async def test_add_ticker_uppercased(self, client, market_source):
        with patch(
            "app.api.watchlist.add_watchlist_ticker",
            new_callable=AsyncMock,
            return_value=True,
        ):
            resp = await client.post("/api/watchlist", json={"ticker": "aapl"})

        data = resp.json()
        assert data["ticker"] == "AAPL"

    async def test_add_ticker_stripped(self, client, market_source):
        with patch(
            "app.api.watchlist.add_watchlist_ticker",
            new_callable=AsyncMock,
            return_value=True,
        ):
            resp = await client.post("/api/watchlist", json={"ticker": "  MSFT  "})

        data = resp.json()
        assert data["ticker"] == "MSFT"

    async def test_add_empty_ticker_returns_422(self, client):
        """Empty string after strip should fail."""
        resp = await client.post("/api/watchlist", json={"ticker": "   "})
        assert resp.status_code == 422

    async def test_missing_ticker_field_returns_422(self, client):
        resp = await client.post("/api/watchlist", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/watchlist/{ticker}
# ---------------------------------------------------------------------------


class TestRemoveFromWatchlist:
    async def test_remove_existing_ticker(self, client, market_source):
        with patch(
            "app.api.watchlist.remove_watchlist_ticker",
            new_callable=AsyncMock,
            return_value=True,
        ):
            resp = await client.delete("/api/watchlist/AAPL")

        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["removed"] is True
        market_source.remove_ticker.assert_awaited_once_with("AAPL")

    async def test_remove_nonexistent_ticker(self, client, market_source):
        with patch(
            "app.api.watchlist.remove_watchlist_ticker",
            new_callable=AsyncMock,
            return_value=False,
        ):
            resp = await client.delete("/api/watchlist/NOPE")

        data = resp.json()
        assert data["ticker"] == "NOPE"
        assert data["removed"] is False
        market_source.remove_ticker.assert_not_awaited()

    async def test_remove_ticker_uppercased(self, client, market_source):
        with patch(
            "app.api.watchlist.remove_watchlist_ticker",
            new_callable=AsyncMock,
            return_value=True,
        ):
            resp = await client.delete("/api/watchlist/aapl")

        data = resp.json()
        assert data["ticker"] == "AAPL"
