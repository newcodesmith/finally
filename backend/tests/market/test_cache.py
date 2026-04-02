"""Tests for PriceCache."""

from app.market.cache import PriceCache


class TestPriceCache:
    """Unit tests for the PriceCache."""

    def test_update_and_get(self):
        """Test updating and getting a price."""
        cache = PriceCache()
        update = cache.update("AAPL", 190.50)
        assert update.ticker == "AAPL"
        assert update.price == 190.50
        assert cache.get("AAPL") == update

    def test_first_update_is_unchanged(self):
        """Test that the first update has unchanged direction."""
        cache = PriceCache()
        update = cache.update("AAPL", 190.50)
        assert update.direction == "unchanged"
        assert update.previous_price == 190.50

    def test_direction_up(self):
        """Test price update with upward direction."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        update = cache.update("AAPL", 191.00)
        assert update.direction == "up"
        assert update.change == 1.00

    def test_direction_down(self):
        """Test price update with downward direction."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        update = cache.update("AAPL", 189.00)
        assert update.direction == "down"
        assert update.change == -1.00

    def test_remove(self):
        """Test removing a ticker from cache."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.remove("AAPL")
        assert cache.get("AAPL") is None

    def test_remove_clears_session_open(self):
        """Test that removing a ticker also clears its session open."""
        cache = PriceCache()
        cache.update("AAPL", 190.00, session_open_price=185.00)
        cache.remove("AAPL")
        # After remove + re-add, session open should reset
        update = cache.update("AAPL", 200.00)
        assert update.session_open_price == 200.00  # New session open

    def test_remove_nonexistent(self):
        """Test removing a ticker that doesn't exist."""
        cache = PriceCache()
        cache.remove("AAPL")  # Should not raise

    def test_get_all(self):
        """Test getting all prices."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.update("GOOGL", 175.00)
        all_prices = cache.get_all()
        assert set(all_prices.keys()) == {"AAPL", "GOOGL"}

    def test_version_increments(self):
        """Test that version counter increments."""
        cache = PriceCache()
        v0 = cache.version
        cache.update("AAPL", 190.00)
        assert cache.version == v0 + 1
        cache.update("AAPL", 191.00)
        assert cache.version == v0 + 2

    def test_get_price_convenience(self):
        """Test the convenience get_price method."""
        cache = PriceCache()
        cache.update("AAPL", 190.50)
        assert cache.get_price("AAPL") == 190.50
        assert cache.get_price("NOPE") is None

    def test_len(self):
        """Test __len__ method."""
        cache = PriceCache()
        assert len(cache) == 0
        cache.update("AAPL", 190.00)
        assert len(cache) == 1
        cache.update("GOOGL", 175.00)
        assert len(cache) == 2

    def test_contains(self):
        """Test __contains__ method."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        assert "AAPL" in cache
        assert "GOOGL" not in cache

    def test_custom_timestamp(self):
        """Test updating with a custom timestamp."""
        cache = PriceCache()
        custom_ts = "2024-01-01T12:00:00+00:00"
        update = cache.update("AAPL", 190.50, timestamp=custom_ts)
        assert update.timestamp == custom_ts

    def test_price_rounding(self):
        """Test that prices are rounded to 2 decimal places."""
        cache = PriceCache()
        update = cache.update("AAPL", 190.12345)
        assert update.price == 190.12

    def test_session_open_price_set_on_first_update(self):
        """Test that session_open_price is set from the provided value on first update."""
        cache = PriceCache()
        update = cache.update("AAPL", 190.00, session_open_price=185.00)
        assert update.session_open_price == 185.00

    def test_session_open_price_defaults_to_first_price(self):
        """Test that session_open_price defaults to the first price if not provided."""
        cache = PriceCache()
        update = cache.update("AAPL", 190.00)
        assert update.session_open_price == 190.00

    def test_session_open_price_never_overwritten(self):
        """Test that subsequent updates do not change the session open price."""
        cache = PriceCache()
        cache.update("AAPL", 190.00, session_open_price=185.00)
        update2 = cache.update("AAPL", 195.00, session_open_price=999.00)
        # session_open_price must stay at 185, not be overwritten by 999
        assert update2.session_open_price == 185.00

    def test_session_open_price_persists_across_updates(self):
        """Test that session open price remains constant across many updates."""
        cache = PriceCache()
        cache.update("AAPL", 190.00, session_open_price=185.00)
        for price in [191.00, 192.00, 188.00, 194.00]:
            update = cache.update("AAPL", price)
            assert update.session_open_price == 185.00
