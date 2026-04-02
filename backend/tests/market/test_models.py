"""Tests for PriceUpdate dataclass."""

import pytest

from app.market.models import PriceUpdate

FIXED_TS = "2024-01-01T00:00:00+00:00"


class TestPriceUpdate:
    """Unit tests for the PriceUpdate model."""

    def test_price_update_creation(self):
        """Test basic PriceUpdate creation."""
        update = PriceUpdate(
            ticker="AAPL",
            price=190.50,
            previous_price=190.00,
            session_open_price=188.00,
            timestamp=FIXED_TS,
        )
        assert update.ticker == "AAPL"
        assert update.price == 190.50
        assert update.previous_price == 190.00
        assert update.session_open_price == 188.00
        assert update.timestamp == FIXED_TS

    def test_change_calculation(self):
        """Test price change calculation."""
        update = PriceUpdate(
            ticker="AAPL", price=190.50, previous_price=190.00,
            session_open_price=190.00, timestamp=FIXED_TS,
        )
        assert update.change == 0.50

    def test_change_negative(self):
        """Test negative price change."""
        update = PriceUpdate(
            ticker="AAPL", price=189.50, previous_price=190.00,
            session_open_price=190.00, timestamp=FIXED_TS,
        )
        assert update.change == -0.50

    def test_change_percent_up(self):
        """Test percentage change calculation (up)."""
        update = PriceUpdate(
            ticker="AAPL", price=190.00, previous_price=100.00,
            session_open_price=100.00, timestamp=FIXED_TS,
        )
        assert update.change_percent == 90.0

    def test_change_percent_down(self):
        """Test percentage change calculation (down)."""
        update = PriceUpdate(
            ticker="AAPL", price=100.00, previous_price=200.00,
            session_open_price=200.00, timestamp=FIXED_TS,
        )
        assert update.change_percent == -50.0

    def test_change_percent_zero_previous(self):
        """Test percentage change with zero previous price."""
        update = PriceUpdate(
            ticker="AAPL", price=100.00, previous_price=0.00,
            session_open_price=0.00, timestamp=FIXED_TS,
        )
        assert update.change_percent == 0.0

    def test_direction_up(self):
        """Test direction calculation (up)."""
        update = PriceUpdate(
            ticker="AAPL", price=191.00, previous_price=190.00,
            session_open_price=190.00, timestamp=FIXED_TS,
        )
        assert update.direction == "up"

    def test_direction_down(self):
        """Test direction calculation (down)."""
        update = PriceUpdate(
            ticker="AAPL", price=189.00, previous_price=190.00,
            session_open_price=190.00, timestamp=FIXED_TS,
        )
        assert update.direction == "down"

    def test_direction_unchanged(self):
        """Test direction calculation (unchanged)."""
        update = PriceUpdate(
            ticker="AAPL", price=190.00, previous_price=190.00,
            session_open_price=190.00, timestamp=FIXED_TS,
        )
        assert update.direction == "unchanged"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        update = PriceUpdate(
            ticker="AAPL", price=190.50, previous_price=190.00,
            session_open_price=188.00, timestamp=FIXED_TS,
        )
        result = update.to_dict()

        assert result["ticker"] == "AAPL"
        assert result["price"] == 190.50
        assert result["previous_price"] == 190.00
        assert result["session_open_price"] == 188.00
        assert result["timestamp"] == FIXED_TS
        assert result["change"] == 0.50
        assert result["change_percent"] == 0.2632  # (0.50 / 190.00) * 100
        assert result["change_direction"] == "up"
        # direction key should not be present (renamed to change_direction)
        assert "direction" not in result

    def test_to_dict_has_change_direction_not_direction(self):
        """Test that to_dict uses change_direction key, not direction."""
        update = PriceUpdate(
            ticker="AAPL", price=190.00, previous_price=190.00,
            session_open_price=190.00, timestamp=FIXED_TS,
        )
        result = update.to_dict()
        assert "change_direction" in result
        assert "direction" not in result
        assert result["change_direction"] == "unchanged"

    def test_immutability(self):
        """Test that PriceUpdate is immutable."""
        update = PriceUpdate(
            ticker="AAPL", price=190.50, previous_price=190.00,
            session_open_price=190.00, timestamp=FIXED_TS,
        )

        with pytest.raises(AttributeError):
            update.price = 200.00  # Should raise error

    def test_timestamp_defaults_to_iso_string(self):
        """Test that timestamp defaults to an ISO 8601 string."""
        update = PriceUpdate(
            ticker="AAPL", price=190.00, previous_price=190.00,
            session_open_price=190.00,
        )
        # Should be an ISO format string, not a float
        assert isinstance(update.timestamp, str)
        # Should contain the 'T' separator of ISO 8601
        assert "T" in update.timestamp
