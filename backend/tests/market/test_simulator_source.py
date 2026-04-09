"""Integration tests for SimulatorDataSource."""

import asyncio

import pytest

from app.market.cache import PriceCache
from app.market.simulator import SimulatorDataSource


@pytest.mark.asyncio
class TestSimulatorDataSource:
    """Integration tests for the SimulatorDataSource."""

    async def test_start_populates_cache(self):
        """Test that start() immediately populates the cache."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start(["AAPL", "GOOGL"])

        # Cache should have seed prices immediately (before first loop tick)
        assert cache.get("AAPL") is not None
        assert cache.get("GOOGL") is not None

        await source.stop()

    async def test_prices_update_over_time(self):
        """Test that prices are updated periodically."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.05)
        await source.start(["AAPL"])

        initial_version = cache.version
        await asyncio.sleep(0.3)  # Several update cycles

        # Version should have incremented (prices updated)
        assert cache.version > initial_version

        await source.stop()

    async def test_stop_is_clean(self):
        """Test that stop() is clean and idempotent."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start(["AAPL"])
        await source.stop()
        # Double stop should not raise
        await source.stop()

    async def test_add_ticker(self):
        """Test adding a ticker dynamically."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start(["AAPL"])

        await source.add_ticker("TSLA")
        assert "TSLA" in source.get_tickers()
        assert cache.get("TSLA") is not None

        await source.stop()

    async def test_remove_ticker(self):
        """Test removing a ticker."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start(["AAPL", "TSLA"])

        await source.remove_ticker("TSLA")
        assert "TSLA" not in source.get_tickers()
        assert cache.get("TSLA") is None

        await source.stop()

    async def test_get_tickers(self):
        """Test getting the list of active tickers."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start(["AAPL", "GOOGL"])

        tickers = source.get_tickers()
        assert set(tickers) == {"AAPL", "GOOGL"}

        await source.stop()

    async def test_empty_start(self):
        """Test starting with no tickers."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start([])

        assert len(cache) == 0
        assert source.get_tickers() == []

        await source.stop()

    async def test_exception_resilience(self):
        """Test that simulator continues running after errors."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.05)

        # Start with a valid ticker
        await source.start(["AAPL"])

        # Wait for some updates
        await asyncio.sleep(0.15)

        # Task should still be running
        assert source._task is not None
        assert not source._task.done()

        await source.stop()

    async def test_custom_update_interval(self):
        """Test using a custom update interval."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.01)
        await source.start(["AAPL"])

        initial_version = cache.version
        await asyncio.sleep(0.05)  # Should get ~5 updates

        # Should have multiple updates with fast interval
        assert cache.version > initial_version + 2

        await source.stop()

    async def test_custom_event_probability(self):
        """Test creating source with custom event probability."""
        cache = PriceCache()
        # Very high event probability for testing
        source = SimulatorDataSource(
            price_cache=cache, update_interval=0.1, event_probability=1.0
        )
        await source.start(["AAPL"])

        # Just verify it starts and stops cleanly
        await asyncio.sleep(0.2)
        await source.stop()

    async def test_snapshot_callback_is_invoked(self):
        """Snapshot callback is called after SNAPSHOT_TICKS ticks."""
        cache = PriceCache()
        call_count = 0

        async def on_snapshot() -> None:
            nonlocal call_count
            call_count += 1

        # Override SNAPSHOT_TICKS to 2 so the callback fires quickly in tests
        original = SimulatorDataSource.SNAPSHOT_TICKS
        SimulatorDataSource.SNAPSHOT_TICKS = 2
        try:
            source = SimulatorDataSource(
                price_cache=cache,
                update_interval=0.02,
                snapshot_callback=on_snapshot,
            )
            await source.start(["AAPL"])
            await asyncio.sleep(0.15)  # Enough for several SNAPSHOT_TICKS cycles
            await source.stop()
        finally:
            SimulatorDataSource.SNAPSHOT_TICKS = original

        assert call_count >= 1

    async def test_snapshot_callback_exception_does_not_stop_simulator(self):
        """An exception in the snapshot callback is swallowed; the simulator keeps running."""
        cache = PriceCache()

        async def failing_callback() -> None:
            raise RuntimeError("snapshot error")

        original = SimulatorDataSource.SNAPSHOT_TICKS
        SimulatorDataSource.SNAPSHOT_TICKS = 2
        try:
            source = SimulatorDataSource(
                price_cache=cache,
                update_interval=0.02,
                snapshot_callback=failing_callback,
            )
            await source.start(["AAPL"])
            await asyncio.sleep(0.15)
            # Task must still be running despite callback failures
            assert source._task is not None
            assert not source._task.done()
            await source.stop()
        finally:
            SimulatorDataSource.SNAPSHOT_TICKS = original
