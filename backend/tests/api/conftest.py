"""Shared fixtures for API route tests.

Every test gets a fresh in-memory SQLite database and a FastAPI app
with mocked price_cache / market_source on app.state.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.market.models import PriceUpdate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_price_update(
    ticker: str,
    price: float,
    previous_price: float | None = None,
    session_open_price: float | None = None,
    timestamp: str = "2026-04-09T12:00:00+00:00",
) -> PriceUpdate:
    return PriceUpdate(
        ticker=ticker,
        price=price,
        previous_price=previous_price if previous_price is not None else price,
        session_open_price=session_open_price if session_open_price is not None else price,
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def price_cache():
    """A mock price cache that tests can configure per-test."""
    cache = MagicMock()
    # Default: no prices
    cache.get.return_value = None
    cache.get_price.return_value = None
    cache.get_all.return_value = {}
    return cache


@pytest.fixture()
def market_source():
    """A mock market data source."""
    source = AsyncMock()
    return source


@pytest.fixture()
def app(price_cache, market_source):
    """Build a minimal FastAPI app with the three routers and mocked state.

    We import the routers directly (no lifespan) so we never touch the
    real database or market data background tasks.
    """
    from fastapi import FastAPI

    from app.api.health import router as health_router
    from app.api.portfolio import router as portfolio_router
    from app.api.watchlist import router as watchlist_router

    test_app = FastAPI()
    test_app.state.price_cache = price_cache
    test_app.state.market_source = market_source

    test_app.include_router(health_router)
    test_app.include_router(watchlist_router)
    test_app.include_router(portfolio_router)

    return test_app


@pytest.fixture()
async def client(app):
    """Async HTTP client bound to the test app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
