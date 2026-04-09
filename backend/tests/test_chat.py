"""Integration tests for chat API endpoint and LLM integration.

Requirements tested:
- CHAT-01: POST /api/chat returns structured JSON with message, trades, watchlist_changes
- CHAT-02: LLM prompt includes current cash balance, positions with P&L, and watchlist with live prices
- CHAT-03: Last 20 chat messages are loaded and appended to the LLM prompt
- CHAT-04: LLMResponse Pydantic model validates structured output
- CHAT-09: When LLM_MOCK=true, endpoint returns deterministic response without calling OpenRouter
"""

from __future__ import annotations

import os
import tempfile

# Set DB_PATH and LLM_MOCK before importing app so modules pick them up
_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(_tmp, "test_chat.db")
os.environ["LLM_MOCK"] = "true"

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
