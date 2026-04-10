"""Integration tests for watchlist API endpoints.

Requirements covered:
- WATCH-01: GET /api/watchlist returns default tickers with price data
- WATCH-02: POST /api/watchlist adds a new ticker with market source sync
- WATCH-03: DELETE /api/watchlist/{ticker} removes a ticker
- WATCH-04: GET /api/watchlist returns correct price field structure
"""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path, monkeypatch):
    """Point DB_PATH to a temp file before any app module is used."""
    db_file = str(tmp_path / "test_watchlist.db")
    monkeypatch.setenv("DB_PATH", db_file)

    # Patch the module-level DB_PATH in the connection module
    import app.db.connection as conn_mod

    monkeypatch.setattr(conn_mod, "DB_PATH", db_file)


@pytest.fixture()
async def client():
    """Create async test client with lifespan support (DB init + market source)."""
    from app.main import app

    # Use the lifespan context to properly init DB and start market source
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac


# ---------------------------------------------------------------------------
# WATCH-01 / WATCH-04: GET /api/watchlist
# ---------------------------------------------------------------------------


async def test_get_watchlist_returns_10_default_tickers(client: AsyncClient):
    """GET /api/watchlist returns 200 with 10 default seeded tickers (WATCH-01)."""
    resp = await client.get("/api/watchlist")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 10


async def test_get_watchlist_item_has_required_keys(client: AsyncClient):
    """Each item in GET response has required price fields (WATCH-04)."""
    resp = await client.get("/api/watchlist")
    data = resp.json()
    required_keys = {
        "ticker",
        "price",
        "previous_price",
        "session_open_price",
        "change_direction",
        "timestamp",
    }
    for item in data:
        assert required_keys.issubset(item.keys()), (
            f"Missing keys: {required_keys - item.keys()} in {item}"
        )


async def test_get_watchlist_price_types(client: AsyncClient):
    """Price fields are either float or None (cache may not be populated yet) (WATCH-04)."""
    resp = await client.get("/api/watchlist")
    data = resp.json()
    for item in data:
        price = item["price"]
        assert price is None or isinstance(price, (int, float)), (
            f"price should be numeric or None, got {type(price)}"
        )


# ---------------------------------------------------------------------------
# WATCH-02: POST /api/watchlist
# ---------------------------------------------------------------------------


async def test_add_ticker_success(client: AsyncClient):
    """POST /api/watchlist with new ticker returns {ticker, added: true} (WATCH-02)."""
    resp = await client.post("/api/watchlist", json={"ticker": "PYPL"})
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"ticker": "PYPL", "added": True}


async def test_add_duplicate_ticker(client: AsyncClient):
    """POST /api/watchlist with existing ticker returns {ticker, added: false}."""
    # AAPL is in default watchlist
    resp = await client.post("/api/watchlist", json={"ticker": "AAPL"})
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"ticker": "AAPL", "added": False}


async def test_add_empty_ticker_returns_422(client: AsyncClient):
    """POST /api/watchlist with empty ticker string returns 422."""
    resp = await client.post("/api/watchlist", json={"ticker": ""})
    assert resp.status_code == 422


async def test_add_ticker_then_appears_in_get(client: AsyncClient):
    """After POST adding a ticker, GET /api/watchlist includes it (WATCH-02)."""
    await client.post("/api/watchlist", json={"ticker": "PYPL"})
    resp = await client.get("/api/watchlist")
    tickers = [item["ticker"] for item in resp.json()]
    assert "PYPL" in tickers


async def test_add_ticker_lowercase_uppercased(client: AsyncClient):
    """POST /api/watchlist lowercases input is uppercased (WATCH-02)."""
    resp = await client.post("/api/watchlist", json={"ticker": "pypl"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "PYPL"


# ---------------------------------------------------------------------------
# WATCH-03: DELETE /api/watchlist/{ticker}
# ---------------------------------------------------------------------------


async def test_remove_ticker_success(client: AsyncClient):
    """DELETE /api/watchlist/AAPL returns {ticker, removed: true} (WATCH-03)."""
    resp = await client.delete("/api/watchlist/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"ticker": "AAPL", "removed": True}


async def test_remove_nonexistent_ticker(client: AsyncClient):
    """DELETE /api/watchlist/NONEXIST returns {ticker, removed: false}."""
    resp = await client.delete("/api/watchlist/NONEXIST")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"ticker": "NONEXIST", "removed": False}


async def test_remove_ticker_then_not_in_get(client: AsyncClient):
    """After DELETE removing a ticker, GET /api/watchlist no longer includes it (WATCH-03)."""
    await client.delete("/api/watchlist/AAPL")
    resp = await client.get("/api/watchlist")
    tickers = [item["ticker"] for item in resp.json()]
    assert "AAPL" not in tickers
