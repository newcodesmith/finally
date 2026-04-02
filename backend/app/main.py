"""FinAlly FastAPI application entry point."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Load .env from project root (one level above backend/)
_env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(_env_path)

from .api.chat import router as chat_router
from .api.health import router as health_router
from .api.portfolio import router as portfolio_router
from .api.watchlist import router as watchlist_router
from .db import get_watchlist_tickers, init_db, record_portfolio_snapshot
from .market import PriceCache, create_market_data_source, create_stream_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

price_cache = PriceCache()


async def _snapshot_callback() -> None:
    """Called by SimulatorDataSource every ~30 seconds to record a portfolio snapshot."""
    from .db import get_cash_balance, get_positions

    try:
        cash = await get_cash_balance()
        positions = await get_positions()
        positions_value = sum(
            (price_cache.get_price(p["ticker"]) or p["avg_cost"]) * p["quantity"]
            for p in positions
        )
        await record_portfolio_snapshot(cash + positions_value)
    except Exception:
        logger.exception("Periodic portfolio snapshot failed")


def _make_market_source():
    """Create market source; inject snapshot callback into simulator if applicable."""
    from .market.simulator import SimulatorDataSource

    source = create_market_data_source(price_cache)
    if isinstance(source, SimulatorDataSource):
        source._snapshot_callback = _snapshot_callback
    return source


market_source = _make_market_source()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database (create tables + seed data)
    await init_db()

    # Start market data source with tickers from DB
    tickers = await get_watchlist_tickers()
    await market_source.start(tickers)
    logger.info("Market data source started with tickers: %s", tickers)

    yield

    # Cleanup
    await market_source.stop()
    logger.info("Market data source stopped")


app = FastAPI(title="FinAlly API", version="0.1.0", lifespan=lifespan)

# Make shared state accessible to route handlers
app.state.price_cache = price_cache
app.state.market_source = market_source

# Register API routes
app.include_router(health_router)
app.include_router(watchlist_router)
app.include_router(portfolio_router)
app.include_router(chat_router)

# SSE streaming
stream_router = create_stream_router(price_cache)
app.include_router(stream_router)

# Serve static frontend files (built Next.js export)
_static_dir = os.path.join(os.path.dirname(__file__), "..", "..", "static")
if os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
    logger.info("Serving static files from: %s", _static_dir)
else:
    logger.info("No static directory found at %s — frontend not served", _static_dir)
