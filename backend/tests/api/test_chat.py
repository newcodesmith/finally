"""Comprehensive tests for the LLM chat integration in app.api.chat."""

from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.chat import (
    FALLBACK_RESPONSE,
    SYSTEM_PROMPT,
    ChatRequest,
    LLMResponse,
    _build_portfolio_context,
    chat,
)

# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


class FakePriceCache:
    """Minimal price cache stub that returns preset prices."""

    def __init__(self, prices: dict[str, float] | None = None):
        self._prices = prices or {}

    def get_price(self, ticker: str) -> float | None:
        return self._prices.get(ticker)


class FakeMarketSource:
    """Minimal market source stub that records add/remove calls."""

    def __init__(self):
        self.added: list[str] = []
        self.removed: list[str] = []

    async def add_ticker(self, ticker: str):
        self.added.append(ticker)

    async def remove_ticker(self, ticker: str):
        self.removed.append(ticker)


def _make_request(price_cache=None, market_source=None):
    """Build a fake FastAPI Request with app.state attributes."""
    req = MagicMock()
    req.app.state.price_cache = price_cache or FakePriceCache()
    req.app.state.market_source = market_source or FakeMarketSource()
    return req


def _llm_json(message: str, trades=None, watchlist_changes=None) -> str:
    """Build a serialized LLMResponse JSON string."""
    payload = {
        "message": message,
        "trades": trades or [],
        "watchlist_changes": watchlist_changes or [],
    }
    return json.dumps(payload)


# ---------------------------------------------------------------------------
# _build_portfolio_context tests
# ---------------------------------------------------------------------------


class TestBuildPortfolioContext:
    def test_no_positions(self):
        cache = FakePriceCache({"AAPL": 190.0, "MSFT": 400.0})
        ctx = _build_portfolio_context(
            cash=10000.0,
            positions=[],
            watchlist=["AAPL", "MSFT"],
            price_cache=cache,
        )
        assert "Cash: $10,000.00" in ctx
        assert "Positions: None" in ctx
        assert "Total portfolio value: $10,000.00" in ctx
        assert "Watchlist: AAPL, MSFT" in ctx
        assert "AAPL: $190.00" in ctx
        assert "MSFT: $400.00" in ctx

    def test_multiple_positions(self):
        cache = FakePriceCache({"AAPL": 200.0, "TSLA": 250.0})
        positions = [
            {"ticker": "AAPL", "quantity": 10, "avg_cost": 180.0},
            {"ticker": "TSLA", "quantity": 5, "avg_cost": 200.0},
        ]
        ctx = _build_portfolio_context(
            cash=5000.0,
            positions=positions,
            watchlist=["AAPL", "TSLA"],
            price_cache=cache,
        )
        assert "Cash: $5,000.00" in ctx
        assert "AAPL" in ctx
        assert "TSLA" in ctx
        # AAPL P&L = (200-180)*10 = +200
        assert "+200.00" in ctx
        # TSLA P&L = (250-200)*5 = +250
        assert "+250.00" in ctx
        # Total value = 5000 + 200*10 + 250*5 = 5000 + 2000 + 1250 = 8250
        assert "Total portfolio value: $8,250.00" in ctx

    def test_empty_watchlist(self):
        cache = FakePriceCache()
        ctx = _build_portfolio_context(
            cash=10000.0,
            positions=[],
            watchlist=[],
            price_cache=cache,
        )
        assert "Watchlist: empty" in ctx
        # No "Current prices" section when watchlist is empty
        assert "Current prices" not in ctx

    def test_price_cache_miss_uses_avg_cost(self):
        """When price_cache has no price, avg_cost is used as fallback for current price."""
        cache = FakePriceCache({})  # no prices
        positions = [{"ticker": "XYZ", "quantity": 10, "avg_cost": 50.0}]
        ctx = _build_portfolio_context(
            cash=1000.0,
            positions=positions,
            watchlist=["XYZ"],
            price_cache=cache,
        )
        # When current_price == avg_cost, P&L should be 0
        assert "+0.00" in ctx
        # Value = 10 * 50 = 500; total = 1500
        assert "Total portfolio value: $1,500.00" in ctx

    def test_watchlist_prices_only_shown_for_cached_tickers(self):
        """Only tickers with a cached price appear in 'Current prices'."""
        cache = FakePriceCache({"AAPL": 190.0})
        ctx = _build_portfolio_context(
            cash=10000.0,
            positions=[],
            watchlist=["AAPL", "UNKNOWN"],
            price_cache=cache,
        )
        assert "AAPL: $190.00" in ctx
        assert "UNKNOWN:" not in ctx


# ---------------------------------------------------------------------------
# LLMResponse parsing tests
# ---------------------------------------------------------------------------


class TestLLMResponseParsing:
    def test_valid_json_parses(self):
        raw = _llm_json(
            "Hello!",
            trades=[{"ticker": "AAPL", "side": "buy", "quantity": 5}],
            watchlist_changes=[{"ticker": "PYPL", "action": "add"}],
        )
        result = LLMResponse.model_validate_json(raw)
        assert result.message == "Hello!"
        assert len(result.trades) == 1
        assert result.trades[0].ticker == "AAPL"
        assert result.trades[0].side == "buy"
        assert result.trades[0].quantity == 5
        assert len(result.watchlist_changes) == 1
        assert result.watchlist_changes[0].action == "add"

    def test_empty_trades_and_watchlist(self):
        raw = _llm_json("Just a message.")
        result = LLMResponse.model_validate_json(raw)
        assert result.message == "Just a message."
        assert result.trades == []
        assert result.watchlist_changes == []

    def test_missing_optional_fields_default_to_empty(self):
        raw = json.dumps({"message": "Hi there"})
        result = LLMResponse.model_validate_json(raw)
        assert result.trades == []
        assert result.watchlist_changes == []

    def test_fractional_quantity(self):
        raw = _llm_json(
            "Buying fractional",
            trades=[{"ticker": "AAPL", "side": "buy", "quantity": 0.5}],
        )
        result = LLMResponse.model_validate_json(raw)
        assert result.trades[0].quantity == 0.5


# ---------------------------------------------------------------------------
# Mock mode tests
# ---------------------------------------------------------------------------


class TestMockMode:
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LLM_MOCK": "true"})
    @patch("app.api.chat.get_cash_balance", new_callable=AsyncMock, return_value=10000.0)
    @patch("app.api.chat.get_positions", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"])
    @patch("app.api.chat.get_chat_history", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.save_chat_message", new_callable=AsyncMock)
    async def test_mock_mode_returns_mock_response(
        self, mock_save, mock_history, mock_watchlist, mock_positions, mock_cash
    ):
        request = _make_request(price_cache=FakePriceCache({"AAPL": 190.0}))
        body = ChatRequest(message="Hello")

        result = await chat(body, request)

        assert "mock mode" in result["message"].lower()
        assert result["trades"] == []
        assert result["watchlist_changes"] == []

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LLM_MOCK": "true"})
    @patch("app.api.chat.get_cash_balance", new_callable=AsyncMock, return_value=10000.0)
    @patch("app.api.chat.get_positions", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_watchlist_tickers", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_chat_history", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.save_chat_message", new_callable=AsyncMock)
    async def test_mock_mode_does_not_call_litellm(
        self, mock_save, mock_history, mock_watchlist, mock_positions, mock_cash
    ):
        request = _make_request()
        body = ChatRequest(message="Hello")

        # completion is imported lazily inside the else branch; patch it at the
        # litellm module level to detect if it gets called.
        with patch("litellm.completion") as mock_completion:
            await chat(body, request)
            mock_completion.assert_not_called()

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LLM_MOCK": "true"})
    @patch("app.api.chat.get_cash_balance", new_callable=AsyncMock, return_value=10000.0)
    @patch("app.api.chat.get_positions", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_watchlist_tickers", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_chat_history", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.save_chat_message", new_callable=AsyncMock)
    async def test_mock_mode_saves_both_messages(
        self, mock_save, mock_history, mock_watchlist, mock_positions, mock_cash
    ):
        request = _make_request()
        body = ChatRequest(message="Hi there")

        await chat(body, request)

        # Should save user message and assistant message
        assert mock_save.call_count == 2
        user_call = mock_save.call_args_list[0]
        assert user_call[0][0] == "user"
        assert user_call[0][1] == "Hi there"
        assistant_call = mock_save.call_args_list[1]
        assert assistant_call[0][0] == "assistant"


# ---------------------------------------------------------------------------
# LLM call and error handling tests
# ---------------------------------------------------------------------------


class TestLLMCallFlow:
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False)
    @patch("app.api.chat.get_cash_balance", new_callable=AsyncMock, return_value=10000.0)
    @patch("app.api.chat.get_positions", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"])
    @patch("app.api.chat.get_chat_history", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.save_chat_message", new_callable=AsyncMock)
    async def test_successful_llm_call(
        self, mock_save, mock_history, mock_watchlist, mock_positions, mock_cash
    ):
        """A successful LLM call parses the response and returns it."""
        llm_json = _llm_json("Here is my analysis.")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = llm_json

        request = _make_request(price_cache=FakePriceCache({"AAPL": 190.0}))
        body = ChatRequest(message="Analyze my portfolio")

        with patch("litellm.completion", return_value=mock_response):
            result = await chat(body, request)

        assert result["message"] == "Here is my analysis."
        assert result["trades"] == []

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False)
    @patch("app.api.chat.get_cash_balance", new_callable=AsyncMock, return_value=10000.0)
    @patch("app.api.chat.get_positions", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_watchlist_tickers", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_chat_history", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.save_chat_message", new_callable=AsyncMock)
    async def test_llm_failure_returns_fallback_not_500(
        self, mock_save, mock_history, mock_watchlist, mock_positions, mock_cash
    ):
        """When the LLM call raises, we return the fallback response (HTTP 200)."""
        request = _make_request()
        body = ChatRequest(message="Hello")

        with patch("litellm.completion", side_effect=Exception("Network error")):
            result = await chat(body, request)

        assert result["message"] == FALLBACK_RESPONSE["message"]
        assert result["trades"] == []
        assert result["watchlist_changes"] == []

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False)
    @patch("app.api.chat.get_cash_balance", new_callable=AsyncMock, return_value=10000.0)
    @patch("app.api.chat.get_positions", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_watchlist_tickers", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_chat_history", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.save_chat_message", new_callable=AsyncMock)
    async def test_llm_failure_saves_fallback_messages(
        self, mock_save, mock_history, mock_watchlist, mock_positions, mock_cash
    ):
        """On LLM failure, both user and assistant fallback messages are saved."""
        request = _make_request()
        body = ChatRequest(message="Help")

        with patch("litellm.completion", side_effect=RuntimeError("timeout")):
            await chat(body, request)

        assert mock_save.call_count == 2
        assert mock_save.call_args_list[0][0] == ("user", "Help")
        assert mock_save.call_args_list[1][0] == ("assistant", FALLBACK_RESPONSE["message"])

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False)
    @patch("app.api.chat.get_cash_balance", new_callable=AsyncMock, return_value=10000.0)
    @patch("app.api.chat.get_positions", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_watchlist_tickers", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_chat_history", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.save_chat_message", new_callable=AsyncMock)
    async def test_malformed_llm_response_returns_fallback(
        self, mock_save, mock_history, mock_watchlist, mock_positions, mock_cash
    ):
        """Malformed JSON from the LLM triggers the fallback path."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "not valid json at all"

        request = _make_request()
        body = ChatRequest(message="Hello")

        with patch("litellm.completion", return_value=mock_response):
            result = await chat(body, request)

        assert result["message"] == FALLBACK_RESPONSE["message"]


# ---------------------------------------------------------------------------
# Trade auto-execution tests
# ---------------------------------------------------------------------------


class TestTradeAutoExecution:
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False)
    @patch("app.api.chat.get_cash_balance", new_callable=AsyncMock, return_value=10000.0)
    @patch("app.api.chat.get_positions", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"])
    @patch("app.api.chat.get_chat_history", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.save_chat_message", new_callable=AsyncMock)
    @patch(
        "app.api.chat.execute_trade",
        new_callable=AsyncMock,
        return_value={"success": True, "error": None, "cash_balance": 9050.0, "position": {"ticker": "AAPL", "quantity": 5, "avg_cost": 190.0}},
    )
    @patch("app.api.chat.record_portfolio_snapshot", new_callable=AsyncMock)
    async def test_trade_executes_and_appears_in_response(
        self, mock_snapshot, mock_trade, mock_save, mock_history, mock_watchlist, mock_positions, mock_cash
    ):
        llm_json = _llm_json(
            "Buying 5 AAPL shares.",
            trades=[{"ticker": "AAPL", "side": "buy", "quantity": 5}],
        )
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = llm_json

        cache = FakePriceCache({"AAPL": 190.0})
        request = _make_request(price_cache=cache)
        body = ChatRequest(message="Buy 5 AAPL")

        with patch("litellm.completion", return_value=mock_response):
            result = await chat(body, request)

        assert len(result["trades"]) == 1
        assert result["trades"][0]["ticker"] == "AAPL"
        assert result["trades"][0]["side"] == "buy"
        assert result["trades"][0]["quantity"] == 5
        assert result["trades"][0]["price"] == 190.0
        mock_trade.assert_called_once_with(ticker="AAPL", side="buy", quantity=5, price=190.0)

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False)
    @patch("app.api.chat.get_cash_balance", new_callable=AsyncMock, return_value=10000.0)
    @patch("app.api.chat.get_positions", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"])
    @patch("app.api.chat.get_chat_history", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.save_chat_message", new_callable=AsyncMock)
    @patch(
        "app.api.chat.execute_trade",
        new_callable=AsyncMock,
        return_value={
            "success": False,
            "error": "Insufficient cash: need $100000.00, have $10000.00",
            "cash_balance": 10000.0,
            "position": None,
        },
    )
    async def test_trade_error_appended_to_message(
        self, mock_trade, mock_save, mock_history, mock_watchlist, mock_positions, mock_cash
    ):
        llm_json = _llm_json(
            "Buying lots of AAPL!",
            trades=[{"ticker": "AAPL", "side": "buy", "quantity": 1000}],
        )
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = llm_json

        cache = FakePriceCache({"AAPL": 190.0})
        request = _make_request(price_cache=cache)
        body = ChatRequest(message="Buy 1000 AAPL")

        with patch("litellm.completion", return_value=mock_response):
            result = await chat(body, request)

        assert "Some trades could not execute" in result["message"]
        assert "Insufficient cash" in result["errors"][0]
        assert result["trades"] == []

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False)
    @patch("app.api.chat.get_cash_balance", new_callable=AsyncMock, return_value=10000.0)
    @patch("app.api.chat.get_positions", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"])
    @patch("app.api.chat.get_chat_history", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.save_chat_message", new_callable=AsyncMock)
    async def test_trade_skipped_when_no_price(
        self, mock_save, mock_history, mock_watchlist, mock_positions, mock_cash
    ):
        """Trade is skipped with an error when price_cache has no price for the ticker."""
        llm_json = _llm_json(
            "Buying NOPRICE.",
            trades=[{"ticker": "NOPRICE", "side": "buy", "quantity": 1}],
        )
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = llm_json

        cache = FakePriceCache({"AAPL": 190.0})  # no NOPRICE entry
        market_source = FakeMarketSource()
        request = _make_request(price_cache=cache, market_source=market_source)
        body = ChatRequest(message="Buy NOPRICE")

        with patch("litellm.completion", return_value=mock_response), \
             patch("app.api.chat.add_watchlist_ticker", new_callable=AsyncMock, return_value=True), \
             patch("app.api.chat.execute_trade", new_callable=AsyncMock) as mock_trade:
            result = await chat(body, request)

        mock_trade.assert_not_called()
        assert "No price for NOPRICE" in result["errors"][0]

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False)
    @patch("app.api.chat.get_cash_balance", new_callable=AsyncMock, return_value=10000.0)
    @patch("app.api.chat.get_positions", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_watchlist_tickers", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_chat_history", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.save_chat_message", new_callable=AsyncMock)
    @patch("app.api.chat.add_watchlist_ticker", new_callable=AsyncMock, return_value=True)
    @patch(
        "app.api.chat.execute_trade",
        new_callable=AsyncMock,
        return_value={"success": True, "error": None, "cash_balance": 9050.0, "position": {"ticker": "AAPL", "quantity": 5, "avg_cost": 190.0}},
    )
    @patch("app.api.chat.record_portfolio_snapshot", new_callable=AsyncMock)
    async def test_trade_auto_adds_ticker_to_watchlist(
        self, mock_snapshot, mock_trade, mock_add_wl, mock_save, mock_history, mock_watchlist, mock_positions, mock_cash
    ):
        """Trading a ticker not on the watchlist auto-adds it."""
        llm_json = _llm_json(
            "Buying AAPL.",
            trades=[{"ticker": "AAPL", "side": "buy", "quantity": 5}],
        )
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = llm_json

        cache = FakePriceCache({"AAPL": 190.0})
        market_source = FakeMarketSource()
        request = _make_request(price_cache=cache, market_source=market_source)
        body = ChatRequest(message="Buy AAPL")

        with patch("litellm.completion", return_value=mock_response):
            await chat(body, request)

        # Ticker was not in watchlist, so add_watchlist_ticker should be called
        mock_add_wl.assert_called_once_with("AAPL")
        assert "AAPL" in market_source.added


# ---------------------------------------------------------------------------
# Watchlist changes tests
# ---------------------------------------------------------------------------


class TestWatchlistChanges:
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False)
    @patch("app.api.chat.get_cash_balance", new_callable=AsyncMock, return_value=10000.0)
    @patch("app.api.chat.get_positions", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"])
    @patch("app.api.chat.get_chat_history", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.save_chat_message", new_callable=AsyncMock)
    @patch("app.api.chat.add_watchlist_ticker", new_callable=AsyncMock, return_value=True)
    @patch("app.api.chat.remove_watchlist_ticker", new_callable=AsyncMock, return_value=True)
    async def test_add_and_remove_watchlist(
        self, mock_remove_wl, mock_add_wl, mock_save, mock_history, mock_watchlist, mock_positions, mock_cash
    ):
        llm_json = _llm_json(
            "Updated your watchlist.",
            watchlist_changes=[
                {"ticker": "PYPL", "action": "add"},
                {"ticker": "AAPL", "action": "remove"},
            ],
        )
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = llm_json

        market_source = FakeMarketSource()
        request = _make_request(price_cache=FakePriceCache({"AAPL": 190.0}), market_source=market_source)
        body = ChatRequest(message="Add PYPL and remove AAPL")

        with patch("litellm.completion", return_value=mock_response):
            result = await chat(body, request)

        assert len(result["watchlist_changes"]) == 2
        assert result["watchlist_changes"][0] == {"ticker": "PYPL", "action": "add", "success": True}
        assert result["watchlist_changes"][1] == {"ticker": "AAPL", "action": "remove", "success": True}
        mock_add_wl.assert_called_once_with("PYPL")
        mock_remove_wl.assert_called_once_with("AAPL")
        assert "PYPL" in market_source.added
        assert "AAPL" in market_source.removed

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False)
    @patch("app.api.chat.get_cash_balance", new_callable=AsyncMock, return_value=10000.0)
    @patch("app.api.chat.get_positions", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"])
    @patch("app.api.chat.get_chat_history", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.save_chat_message", new_callable=AsyncMock)
    @patch("app.api.chat.remove_watchlist_ticker", new_callable=AsyncMock, return_value=False)
    async def test_remove_nonexistent_ticker_reports_failure(
        self, mock_remove_wl, mock_save, mock_history, mock_watchlist, mock_positions, mock_cash
    ):
        llm_json = _llm_json(
            "Removed NOPE.",
            watchlist_changes=[{"ticker": "NOPE", "action": "remove"}],
        )
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = llm_json

        market_source = FakeMarketSource()
        request = _make_request(price_cache=FakePriceCache(), market_source=market_source)
        body = ChatRequest(message="Remove NOPE")

        with patch("litellm.completion", return_value=mock_response):
            result = await chat(body, request)

        assert result["watchlist_changes"][0]["success"] is False
        # remove_ticker on market_source should NOT be called when DB remove returns False
        assert market_source.removed == []


# ---------------------------------------------------------------------------
# Post-trade snapshot tests
# ---------------------------------------------------------------------------


class TestPostTradeSnapshot:
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False)
    @patch("app.api.chat.get_cash_balance", new_callable=AsyncMock, return_value=9050.0)
    @patch(
        "app.api.chat.get_positions",
        new_callable=AsyncMock,
        return_value=[{"ticker": "AAPL", "quantity": 5, "avg_cost": 190.0}],
    )
    @patch("app.api.chat.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"])
    @patch("app.api.chat.get_chat_history", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.save_chat_message", new_callable=AsyncMock)
    @patch(
        "app.api.chat.execute_trade",
        new_callable=AsyncMock,
        return_value={"success": True, "error": None, "cash_balance": 9050.0, "position": {"ticker": "AAPL", "quantity": 5, "avg_cost": 190.0}},
    )
    @patch("app.api.chat.record_portfolio_snapshot", new_callable=AsyncMock)
    async def test_snapshot_recorded_after_successful_trade(
        self, mock_snapshot, mock_trade, mock_save, mock_history, mock_watchlist, mock_positions, mock_cash
    ):
        llm_json = _llm_json(
            "Bought AAPL.",
            trades=[{"ticker": "AAPL", "side": "buy", "quantity": 5}],
        )
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = llm_json

        cache = FakePriceCache({"AAPL": 190.0})
        request = _make_request(price_cache=cache)
        body = ChatRequest(message="Buy 5 AAPL")

        with patch("litellm.completion", return_value=mock_response):
            await chat(body, request)

        mock_snapshot.assert_called_once()
        # Snapshot value = updated_cash + positions_value
        # get_cash_balance returns 9050, positions: 5 * 190 = 950
        # total = 9050 + 950 = 10000
        snapshot_value = mock_snapshot.call_args[0][0]
        assert snapshot_value == 10000.0

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False)
    @patch("app.api.chat.get_cash_balance", new_callable=AsyncMock, return_value=10000.0)
    @patch("app.api.chat.get_positions", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"])
    @patch("app.api.chat.get_chat_history", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.save_chat_message", new_callable=AsyncMock)
    @patch("app.api.chat.record_portfolio_snapshot", new_callable=AsyncMock)
    async def test_no_snapshot_when_no_trades(
        self, mock_snapshot, mock_save, mock_history, mock_watchlist, mock_positions, mock_cash
    ):
        llm_json = _llm_json("No trades today.")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = llm_json

        request = _make_request(price_cache=FakePriceCache({"AAPL": 190.0}))
        body = ChatRequest(message="What do you think?")

        with patch("litellm.completion", return_value=mock_response):
            await chat(body, request)

        mock_snapshot.assert_not_called()


# ---------------------------------------------------------------------------
# Chat history storage tests
# ---------------------------------------------------------------------------


class TestChatHistoryStorage:
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False)
    @patch("app.api.chat.get_cash_balance", new_callable=AsyncMock, return_value=10000.0)
    @patch("app.api.chat.get_positions", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"])
    @patch("app.api.chat.get_chat_history", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.save_chat_message", new_callable=AsyncMock)
    @patch(
        "app.api.chat.execute_trade",
        new_callable=AsyncMock,
        return_value={"success": True, "error": None, "cash_balance": 9050.0, "position": {"ticker": "AAPL", "quantity": 5, "avg_cost": 190.0}},
    )
    @patch("app.api.chat.record_portfolio_snapshot", new_callable=AsyncMock)
    async def test_actions_saved_with_assistant_message(
        self, mock_snapshot, mock_trade, mock_save, mock_history, mock_watchlist, mock_positions, mock_cash
    ):
        llm_json = _llm_json(
            "Bought AAPL.",
            trades=[{"ticker": "AAPL", "side": "buy", "quantity": 5}],
        )
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = llm_json

        cache = FakePriceCache({"AAPL": 190.0})
        request = _make_request(price_cache=cache)
        body = ChatRequest(message="Buy 5 AAPL")

        with patch("litellm.completion", return_value=mock_response):
            await chat(body, request)

        # Second save_chat_message call is the assistant message with actions
        assistant_call = mock_save.call_args_list[1]
        assert assistant_call[0][0] == "assistant"
        actions = assistant_call[1].get("actions") or assistant_call[0][2] if len(assistant_call[0]) > 2 else assistant_call[1].get("actions")
        assert actions is not None
        assert len(actions["trades"]) == 1
        assert actions["trades"][0]["ticker"] == "AAPL"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False)
    @patch("app.api.chat.get_cash_balance", new_callable=AsyncMock, return_value=10000.0)
    @patch("app.api.chat.get_positions", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL"])
    @patch("app.api.chat.get_chat_history", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.save_chat_message", new_callable=AsyncMock)
    async def test_no_actions_saved_when_no_trades_or_changes(
        self, mock_save, mock_history, mock_watchlist, mock_positions, mock_cash
    ):
        llm_json = _llm_json("Just chatting.")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = llm_json

        request = _make_request(price_cache=FakePriceCache({"AAPL": 190.0}))
        body = ChatRequest(message="Hello")

        with patch("litellm.completion", return_value=mock_response):
            await chat(body, request)

        # Assistant message should have actions=None
        assistant_call = mock_save.call_args_list[1]
        # save_chat_message(role, content, actions=None)
        if len(assistant_call[0]) > 2:
            assert assistant_call[0][2] is None
        else:
            assert assistant_call[1].get("actions") is None


# ---------------------------------------------------------------------------
# Prompt construction tests
# ---------------------------------------------------------------------------


class TestPromptConstruction:
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False)
    @patch("app.api.chat.get_cash_balance", new_callable=AsyncMock, return_value=5000.0)
    @patch(
        "app.api.chat.get_positions",
        new_callable=AsyncMock,
        return_value=[{"ticker": "AAPL", "quantity": 10, "avg_cost": 150.0}],
    )
    @patch("app.api.chat.get_watchlist_tickers", new_callable=AsyncMock, return_value=["AAPL", "MSFT"])
    @patch(
        "app.api.chat.get_chat_history",
        new_callable=AsyncMock,
        return_value=[
            {"role": "user", "content": "Hi", "created_at": "2026-01-01T00:00:00"},
            {"role": "assistant", "content": "Hello!", "created_at": "2026-01-01T00:00:01"},
        ],
    )
    @patch("app.api.chat.save_chat_message", new_callable=AsyncMock)
    async def test_messages_include_system_history_and_user(
        self, mock_save, mock_history, mock_watchlist, mock_positions, mock_cash
    ):
        """The LLM receives system prompt + portfolio context, chat history, and user message."""
        captured_messages = None

        def fake_completion(**kwargs):
            nonlocal captured_messages
            captured_messages = kwargs["messages"]
            resp = MagicMock()
            resp.choices = [MagicMock()]
            resp.choices[0].message.content = _llm_json("Response.")
            return resp

        cache = FakePriceCache({"AAPL": 190.0, "MSFT": 400.0})
        request = _make_request(price_cache=cache)
        body = ChatRequest(message="What should I buy?")

        with patch("litellm.completion", side_effect=fake_completion):
            await chat(body, request)

        assert captured_messages is not None
        # First message is system prompt with portfolio context
        assert captured_messages[0]["role"] == "system"
        assert SYSTEM_PROMPT in captured_messages[0]["content"]
        assert "Cash: $5,000.00" in captured_messages[0]["content"]
        assert "AAPL" in captured_messages[0]["content"]

        # History messages follow
        assert captured_messages[1] == {"role": "user", "content": "Hi"}
        assert captured_messages[2] == {"role": "assistant", "content": "Hello!"}

        # User's new message is last
        assert captured_messages[-1] == {"role": "user", "content": "What should I buy?"}

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False)
    @patch("app.api.chat.get_cash_balance", new_callable=AsyncMock, return_value=10000.0)
    @patch("app.api.chat.get_positions", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_watchlist_tickers", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_chat_history", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.save_chat_message", new_callable=AsyncMock)
    async def test_empty_history_still_has_system_and_user(
        self, mock_save, mock_history, mock_watchlist, mock_positions, mock_cash
    ):
        """With no chat history, messages are just [system, user]."""
        captured_messages = None

        def fake_completion(**kwargs):
            nonlocal captured_messages
            captured_messages = kwargs["messages"]
            resp = MagicMock()
            resp.choices = [MagicMock()]
            resp.choices[0].message.content = _llm_json("Sure.")
            return resp

        request = _make_request()
        body = ChatRequest(message="Hello")

        with patch("litellm.completion", side_effect=fake_completion):
            await chat(body, request)

        assert len(captured_messages) == 2
        assert captured_messages[0]["role"] == "system"
        assert captured_messages[1]["role"] == "user"
        assert captured_messages[1]["content"] == "Hello"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False)
    @patch("app.api.chat.get_cash_balance", new_callable=AsyncMock, return_value=10000.0)
    @patch("app.api.chat.get_positions", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_watchlist_tickers", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.get_chat_history", new_callable=AsyncMock, return_value=[])
    @patch("app.api.chat.save_chat_message", new_callable=AsyncMock)
    async def test_llm_called_with_correct_model_and_params(
        self, mock_save, mock_history, mock_watchlist, mock_positions, mock_cash
    ):
        """Verify the LLM is called with the correct model, response_format, and extra_body."""
        captured_kwargs = {}

        def fake_completion(**kwargs):
            captured_kwargs.update(kwargs)
            resp = MagicMock()
            resp.choices = [MagicMock()]
            resp.choices[0].message.content = _llm_json("Ok.")
            return resp

        request = _make_request()
        body = ChatRequest(message="Test")

        with patch("litellm.completion", side_effect=fake_completion):
            await chat(body, request)

        assert captured_kwargs["model"] == "openrouter/openai/gpt-oss-120b"
        assert captured_kwargs["response_format"] == LLMResponse
        assert captured_kwargs["reasoning_effort"] == "low"
        assert captured_kwargs["extra_body"] == {"provider": {"order": ["cerebras"]}}
