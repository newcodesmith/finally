"""Factory for creating market data sources."""

from __future__ import annotations

import logging
import os
from collections.abc import Awaitable, Callable

from .cache import PriceCache
from .interface import MarketDataSource
from .massive_client import MassiveDataSource
from .simulator import SimulatorDataSource

logger = logging.getLogger(__name__)


def create_market_data_source(
    price_cache: PriceCache,
    snapshot_callback: Callable[[], Awaitable[None]] | None = None,
) -> MarketDataSource:
    """Create the appropriate market data source based on environment variables.

    - MASSIVE_API_KEY set and non-empty → MassiveDataSource (real market data)
    - Otherwise → SimulatorDataSource (GBM simulation)

    snapshot_callback: optional async callable invoked periodically to record a
        portfolio value snapshot (~every 30s for the simulator, every poll cycle
        for the Massive client).

    Returns an unstarted source. Caller must await source.start(tickers).
    """
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()

    if api_key:
        poll_interval = float(os.environ.get("MARKET_POLL_INTERVAL_SECONDS", "15"))
        logger.info(
            "Market data source: Massive API (real data, poll interval %.1fs)",
            poll_interval,
        )
        return MassiveDataSource(
            api_key=api_key,
            price_cache=price_cache,
            poll_interval=poll_interval,
            snapshot_callback=snapshot_callback,
        )
    else:
        logger.info("Market data source: GBM Simulator")
        return SimulatorDataSource(price_cache=price_cache, snapshot_callback=snapshot_callback)
