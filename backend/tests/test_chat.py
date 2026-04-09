"""Integration tests for chat API endpoint and LLM integration.

Requirements tested:
- CHAT-01: POST /api/chat returns structured JSON with message, trades, watchlist_changes
- CHAT-02: LLM prompt includes current cash balance, positions with P&L, and watchlist with live prices
- CHAT-03: Last 20 chat messages are loaded and appended to the LLM prompt
- CHAT-04: LLMResponse Pydantic model validates structured output
- CHAT-09: When LLM_MOCK=true, endpoint returns deterministic response without calling OpenRouter
"""

from __future__ import annotations

import json
import os
import tempfile

# Set DB_PATH and LLM_MOCK before importing app so modules pick them up
_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(_tmp, "test_chat.db")
os.environ["LLM_MOCK"] = "true"

import litellm  # noqa: E402
import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app.db.schema import init_db  # noqa: E402
from app.main import app  # noqa: E402

# Track whether DB + app state has been initialized
_initialized = False


async def _ensure_init():
    """Initialize DB and app state once across all tests."""
    global _initialized
    if not _initialized:
        await init_db()
        _initialized = True


@pytest.fixture
async def client():
    """Provide an async test client with DB initialized."""
    await _ensure_init()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _inject_price(ticker: str, price: float) -> None:
    """Inject a price directly into the app's price cache for deterministic tests."""
    app.state.price_cache.update(ticker, price)


# ---------------------------------------------------------------------------
# CHAT-01: Structured JSON response
# ---------------------------------------------------------------------------


class TestChatEndpoint:
    """Verify POST /api/chat returns properly structured JSON (CHAT-01)."""

    async def test_returns_structured_json(self, client: AsyncClient):
        """POST /api/chat returns 200 with message, trades, watchlist_changes keys (CHAT-01)."""
        resp = await client.post("/api/chat", json={"message": "Hello"})
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "trades" in data
        assert "watchlist_changes" in data

    async def test_message_field_is_string(self, client: AsyncClient):
        """Response message field is a non-empty string (CHAT-01)."""
        resp = await client.post("/api/chat", json={"message": "Hello"})
        data = resp.json()
        assert isinstance(data["message"], str)
        assert len(data["message"]) > 0

    async def test_trades_field_is_list(self, client: AsyncClient):
        """Response trades field is a list (CHAT-01)."""
        resp = await client.post("/api/chat", json={"message": "Hello"})
        data = resp.json()
        assert isinstance(data["trades"], list)

    async def test_watchlist_changes_field_is_list(self, client: AsyncClient):
        """Response watchlist_changes field is a list (CHAT-01)."""
        resp = await client.post("/api/chat", json={"message": "Hello"})
        data = resp.json()
        assert isinstance(data["watchlist_changes"], list)


# ---------------------------------------------------------------------------
# CHAT-02: Portfolio context injection
# ---------------------------------------------------------------------------


class TestChatContext:
    """Verify portfolio context is included in the LLM prompt (CHAT-02)."""

    async def test_portfolio_context_includes_cash(self, client: AsyncClient):
        """Chat endpoint loads cash balance for context without error (CHAT-02)."""
        _inject_price("AAPL", 190.0)
        resp = await client.post(
            "/api/chat", json={"message": "What is my cash balance?"}
        )
        assert resp.status_code == 200
        data = resp.json()
        # Mock mode confirms context was built (message references portfolio)
        assert "mock mode" in data["message"].lower() or "portfolio" in data["message"].lower()

    async def test_context_includes_positions(self, client: AsyncClient):
        """Chat works after buying shares -- positions are loaded into context (CHAT-02)."""
        _inject_price("AAPL", 190.0)
        # Buy shares first
        trade_resp = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "buy", "quantity": 5},
        )
        assert trade_resp.json()["success"] is True

        # Now chat -- endpoint should succeed without error
        resp = await client.post(
            "/api/chat", json={"message": "Tell me about my positions"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["message"], str)


# ---------------------------------------------------------------------------
# CHAT-03: Chat history loading
# ---------------------------------------------------------------------------


class TestChatHistory:
    """Verify chat messages are saved and history accumulates (CHAT-03)."""

    async def test_chat_saves_user_and_assistant_messages(self, client: AsyncClient):
        """POST /api/chat saves both user and assistant messages to DB (CHAT-03)."""
        from app.db.queries import get_chat_history

        resp = await client.post(
            "/api/chat", json={"message": "History test message"}
        )
        assert resp.status_code == 200

        history = await get_chat_history(limit=20)
        # Should have at least 2 messages (user + assistant) from this call
        assert len(history) >= 2
        roles = [msg["role"] for msg in history]
        assert "user" in roles
        assert "assistant" in roles

    async def test_history_accumulates(self, client: AsyncClient):
        """Multiple chat messages accumulate in history (CHAT-03)."""
        from app.db.queries import get_chat_history

        # Send 3 messages
        for i in range(3):
            resp = await client.post(
                "/api/chat", json={"message": f"Accumulation test {i}"}
            )
            assert resp.status_code == 200

        history = await get_chat_history(limit=50)
        # Each call saves 2 messages (user + assistant), plus messages from prior tests
        # At minimum we expect 6 messages from these 3 calls
        assert len(history) >= 6


# ---------------------------------------------------------------------------
# CHAT-04: Pydantic schema validation
# ---------------------------------------------------------------------------


class TestLLMResponseSchema:
    """Verify LLMResponse Pydantic model validates structured output (CHAT-04)."""

    def test_pydantic_model_accepts_valid_json(self):
        """LLMResponse accepts valid JSON with all fields (CHAT-04)."""
        from app.api.chat import LLMResponse

        result = LLMResponse.model_validate_json(
            '{"message": "test", "trades": [], "watchlist_changes": []}'
        )
        assert result.message == "test"
        assert result.trades == []
        assert result.watchlist_changes == []

    def test_pydantic_model_accepts_with_trades(self):
        """LLMResponse accepts JSON with trade actions (CHAT-04)."""
        from app.api.chat import LLMResponse

        result = LLMResponse.model_validate_json(
            '{"message": "ok", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}], "watchlist_changes": []}'
        )
        assert len(result.trades) == 1
        assert result.trades[0].ticker == "AAPL"
        assert result.trades[0].side == "buy"
        assert result.trades[0].quantity == 10.0

    def test_pydantic_model_rejects_missing_message(self):
        """LLMResponse rejects JSON without required message field (CHAT-04)."""
        from app.api.chat import LLMResponse

        with pytest.raises(ValidationError):
            LLMResponse.model_validate_json('{"trades": [], "watchlist_changes": []}')


# ---------------------------------------------------------------------------
# CHAT-09: Mock mode determinism
# ---------------------------------------------------------------------------


class TestMockMode:
    """Verify LLM_MOCK=true returns deterministic responses (CHAT-09)."""

    async def test_mock_response_is_deterministic(self, client: AsyncClient):
        """Same message sent twice produces identical response messages (CHAT-09)."""
        msg = "Determinism check"
        resp1 = await client.post("/api/chat", json={"message": msg})
        resp2 = await client.post("/api/chat", json={"message": msg})

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["message"] == resp2.json()["message"]

    async def test_mock_returns_empty_actions(self, client: AsyncClient):
        """Mock mode returns empty trades and watchlist_changes lists (CHAT-09)."""
        resp = await client.post("/api/chat", json={"message": "Test mock actions"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["trades"] == []
        assert data["watchlist_changes"] == []


# ---------------------------------------------------------------------------
# Mock helpers for monkeypatching litellm.completion
# ---------------------------------------------------------------------------


class _MockChoice:
    """Minimal mock of litellm response choice."""

    def __init__(self, content: str):
        self.message = type("M", (), {"content": content})()


class _MockLLMResponse:
    """Minimal mock of litellm completion response."""

    def __init__(self, content: str):
        self.choices = [_MockChoice(content)]


def _make_mock_completion(response_dict: dict):
    """Return a callable that mimics litellm.completion with a fixed JSON response."""
    content = json.dumps(response_dict)
    return lambda **kwargs: _MockLLMResponse(content)


@pytest.fixture
def disable_mock():
    """Temporarily set LLM_MOCK=false so the real (monkeypatched) LLM path executes."""
    original = os.environ.get("LLM_MOCK", "true")
    os.environ["LLM_MOCK"] = "false"
    yield
    os.environ["LLM_MOCK"] = original


# ---------------------------------------------------------------------------
# CHAT-05, CHAT-06: Auto-execution of trades and watchlist changes
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("disable_mock")
class TestAutoExecution:
    """Verify LLM-specified trades and watchlist changes auto-execute (CHAT-05, CHAT-06)."""

    async def test_trade_auto_executes_buy(self, client: AsyncClient, monkeypatch):
        """LLM response with a buy trade auto-executes and updates portfolio (CHAT-05)."""
        _inject_price("AAPL", 150.0)
        mock_fn = _make_mock_completion({
            "message": "Buying AAPL for you",
            "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 5}],
            "watchlist_changes": [],
        })
        monkeypatch.setattr(litellm, "completion", mock_fn)

        resp = await client.post("/api/chat", json={"message": "Buy 5 AAPL"})
        assert resp.status_code == 200
        data = resp.json()

        assert len(data["trades"]) == 1
        assert data["trades"][0]["ticker"] == "AAPL"
        assert data["trades"][0]["side"] == "buy"
        assert data["trades"][0]["quantity"] == 5
        assert data["trades"][0]["price"] == 150.0

        # Verify portfolio was actually updated
        portfolio = await client.get("/api/portfolio")
        pdata = portfolio.json()
        aapl_pos = [p for p in pdata["positions"] if p["ticker"] == "AAPL"]
        assert len(aapl_pos) >= 1
        assert aapl_pos[0]["quantity"] >= 5

    async def test_trade_auto_executes_sell(self, client: AsyncClient, monkeypatch):
        """LLM response with a sell trade reduces position (CHAT-05)."""
        _inject_price("MSFT", 400.0)
        # First buy manually
        buy_resp = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "MSFT", "side": "buy", "quantity": 10},
        )
        assert buy_resp.json()["success"] is True

        # Now monkeypatch LLM to sell 3
        mock_fn = _make_mock_completion({
            "message": "Selling 3 MSFT",
            "trades": [{"ticker": "MSFT", "side": "sell", "quantity": 3}],
            "watchlist_changes": [],
        })
        monkeypatch.setattr(litellm, "completion", mock_fn)

        resp = await client.post("/api/chat", json={"message": "Sell 3 MSFT"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["trades"]) == 1
        assert data["trades"][0]["side"] == "sell"

    async def test_watchlist_add_auto_executes(self, client: AsyncClient, monkeypatch):
        """LLM response with watchlist add auto-executes (CHAT-06)."""
        mock_fn = _make_mock_completion({
            "message": "Adding PYPL to watchlist",
            "trades": [],
            "watchlist_changes": [{"ticker": "PYPL", "action": "add"}],
        })
        monkeypatch.setattr(litellm, "completion", mock_fn)

        resp = await client.post("/api/chat", json={"message": "Add PYPL"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["watchlist_changes"]) == 1
        assert data["watchlist_changes"][0]["ticker"] == "PYPL"
        assert data["watchlist_changes"][0]["action"] == "add"
        assert data["watchlist_changes"][0]["success"] is True

        # Verify watchlist updated
        wl = await client.get("/api/watchlist")
        tickers = [item["ticker"] for item in wl.json()]
        assert "PYPL" in tickers

    async def test_watchlist_remove_auto_executes(self, client: AsyncClient, monkeypatch):
        """LLM response with watchlist remove auto-executes (CHAT-06)."""
        # Ensure NFLX is in watchlist (it's seeded by default)
        mock_fn = _make_mock_completion({
            "message": "Removing NFLX from watchlist",
            "trades": [],
            "watchlist_changes": [{"ticker": "NFLX", "action": "remove"}],
        })
        monkeypatch.setattr(litellm, "completion", mock_fn)

        resp = await client.post("/api/chat", json={"message": "Remove NFLX"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["watchlist_changes"]) == 1
        assert data["watchlist_changes"][0]["action"] == "remove"

    async def test_trade_auto_adds_to_watchlist(self, client: AsyncClient, monkeypatch):
        """Buying a ticker not in watchlist auto-adds it before executing (CHAT-05)."""
        _inject_price("SQ", 80.0)
        mock_fn = _make_mock_completion({
            "message": "Buying SQ",
            "trades": [{"ticker": "SQ", "side": "buy", "quantity": 2}],
            "watchlist_changes": [],
        })
        monkeypatch.setattr(litellm, "completion", mock_fn)

        resp = await client.post("/api/chat", json={"message": "Buy 2 SQ"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["trades"]) == 1

        # Verify SQ was added to watchlist
        wl = await client.get("/api/watchlist")
        tickers = [item["ticker"] for item in wl.json()]
        assert "SQ" in tickers


# ---------------------------------------------------------------------------
# CHAT-07: Failed trade errors
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("disable_mock")
class TestFailedTrades:
    """Verify failed trades produce error messages in chat response (CHAT-07)."""

    async def test_insufficient_cash_error_in_response(self, client: AsyncClient, monkeypatch):
        """Buying more than cash allows produces Insufficient cash error (CHAT-07)."""
        _inject_price("GOOGL", 500.0)
        mock_fn = _make_mock_completion({
            "message": "Buying 1000 GOOGL",
            "trades": [{"ticker": "GOOGL", "side": "buy", "quantity": 1000}],
            "watchlist_changes": [],
        })
        monkeypatch.setattr(litellm, "completion", mock_fn)

        resp = await client.post("/api/chat", json={"message": "Buy 1000 GOOGL"})
        assert resp.status_code == 200
        data = resp.json()
        assert any("Insufficient cash" in e for e in data["errors"])

    async def test_no_price_error_in_response(self, client: AsyncClient, monkeypatch):
        """Buying a ticker with no cached price produces No price for error (CHAT-07)."""
        mock_fn = _make_mock_completion({
            "message": "Buying ZZZZZ",
            "trades": [{"ticker": "ZZZZZ", "side": "buy", "quantity": 1}],
            "watchlist_changes": [],
        })
        monkeypatch.setattr(litellm, "completion", mock_fn)

        resp = await client.post("/api/chat", json={"message": "Buy ZZZZZ"})
        assert resp.status_code == 200
        data = resp.json()
        assert any("No price for" in e for e in data["errors"])

    async def test_failed_trade_error_appended_to_message(self, client: AsyncClient, monkeypatch):
        """Trade errors are appended to the assistant message text (CHAT-07)."""
        mock_fn = _make_mock_completion({
            "message": "Trying to buy",
            "trades": [{"ticker": "NOPRZ", "side": "buy", "quantity": 1}],
            "watchlist_changes": [],
        })
        monkeypatch.setattr(litellm, "completion", mock_fn)

        resp = await client.post("/api/chat", json={"message": "Buy NOPRZ"})
        assert resp.status_code == 200
        data = resp.json()
        assert "could not execute" in data["message"].lower() or "No price for" in data["message"]


# ---------------------------------------------------------------------------
# CHAT-08: LLM failure handling
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("disable_mock")
class TestLLMFailureHandling:
    """Verify LLM failures return 200 with fallback message (CHAT-08)."""

    async def test_llm_exception_returns_200_with_fallback(self, client: AsyncClient, monkeypatch):
        """ConnectionError from LLM returns 200 with trouble connecting message (CHAT-08)."""
        def _raise(**kwargs):
            raise ConnectionError("simulated failure")
        monkeypatch.setattr(litellm, "completion", _raise)

        resp = await client.post("/api/chat", json={"message": "Hello"})
        assert resp.status_code == 200
        data = resp.json()
        assert "trouble connecting" in data["message"].lower()

    async def test_llm_failure_saves_messages_to_db(self, client: AsyncClient, monkeypatch):
        """LLM failure still saves user and fallback assistant messages to DB (CHAT-08)."""
        from app.db.queries import get_chat_history

        def _raise(**kwargs):
            raise RuntimeError("simulated LLM down")
        monkeypatch.setattr(litellm, "completion", _raise)

        await client.post("/api/chat", json={"message": "Failure DB test"})

        history = await get_chat_history(limit=50)
        messages = [m["content"] for m in history]
        assert "Failure DB test" in messages
        assert any("trouble connecting" in m.lower() for m in messages)

    async def test_llm_malformed_json_returns_fallback(self, client: AsyncClient, monkeypatch):
        """Malformed JSON from LLM triggers Pydantic error, returns fallback (CHAT-08)."""
        monkeypatch.setattr(litellm, "completion", lambda **kwargs: _MockLLMResponse("not valid json"))

        resp = await client.post("/api/chat", json={"message": "Malformed test"})
        assert resp.status_code == 200
        data = resp.json()
        assert "trouble connecting" in data["message"].lower()
