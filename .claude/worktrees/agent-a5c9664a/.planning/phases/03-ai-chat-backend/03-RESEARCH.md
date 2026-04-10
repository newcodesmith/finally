# Phase 3: AI Chat Backend - Research

**Researched:** 2026-04-09
**Domain:** LLM integration (LiteLLM + OpenRouter/Cerebras), structured output parsing, auto-execution pipeline
**Confidence:** HIGH

## Summary

The AI Chat Backend is **already substantially implemented** in `backend/app/api/chat.py`. The existing code covers all nine CHAT requirements: the POST /api/chat endpoint accepts messages, builds portfolio context from live data, loads the last 20 chat messages as history, calls the LLM via LiteLLM with structured output (Pydantic `response_format`), auto-executes trades and watchlist changes, handles LLM failures gracefully with HTTP 200 fallback, and supports LLM_MOCK=true for deterministic responses.

The primary work for this phase is **verification and testing** -- confirming the existing implementation meets all requirements, writing integration tests for the chat endpoint, and ensuring edge cases (malformed LLM responses, partial trade failures, empty portfolios) are handled correctly.

The LiteLLM library (v1.83.0) is already installed. The Cerebras inference skill pattern (`MODEL = "openrouter/openai/gpt-oss-120b"`, `EXTRA_BODY = {"provider": {"order": ["cerebras"]}}`) is correctly implemented in the existing code.

**Primary recommendation:** Write comprehensive integration tests for the chat endpoint (mock mode, error handling, auto-execution), verify the existing implementation against all CHAT requirements, and fix any gaps found during testing.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CHAT-01 | POST /api/chat accepts user message and returns structured JSON response | Already implemented in `backend/app/api/chat.py` lines 151-287. Returns `{message, trades, watchlist_changes, errors}` |
| CHAT-02 | LLM receives portfolio context (cash, positions, watchlist with prices, total value) | Implemented via `_build_portfolio_context()` helper (lines 99-143). Includes cash, positions with P&L, watchlist, live prices |
| CHAT-03 | LLM receives last 20 chat messages as conversation history | Implemented: `get_chat_history(limit=20)` called at line 165, messages appended to LLM prompt at lines 168-173 |
| CHAT-04 | Structured output includes message, optional trades array, optional watchlist_changes array | `LLMResponse` Pydantic model (lines 79-82) with `response_format=LLMResponse` passed to LiteLLM |
| CHAT-05 | Trades from LLM auto-execute without confirmation | Lines 204-232: iterates `llm_result.trades`, auto-adds to watchlist if needed, calls `execute_trade()` |
| CHAT-06 | Watchlist changes from LLM auto-execute | Lines 235-249: iterates `llm_result.watchlist_changes`, calls `add_watchlist_ticker()` or `remove_watchlist_ticker()` |
| CHAT-07 | Failed trades include error in chat response | Lines 273-276: trade errors appended to message. Lines 282-287: `errors` array returned in response |
| CHAT-08 | LLM failures return fallback message (never 500) | Lines 196-201: except block catches all exceptions, saves fallback message, returns `FALLBACK_RESPONSE` with HTTP 200 |
| CHAT-09 | LLM mock mode returns deterministic responses when LLM_MOCK=true | Lines 178-184: checks `LLM_MOCK` env var, returns fixed `LLMResponse` without calling OpenRouter |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| litellm | 1.83.0 | LLM API abstraction, OpenRouter/Cerebras routing | [VERIFIED: installed in backend venv] Already in pyproject.toml |
| pydantic | (bundled with FastAPI) | Structured output schema, request/response validation | [VERIFIED: used throughout existing codebase] |
| FastAPI | >=0.115.0 | API framework, already serving all endpoints | [VERIFIED: pyproject.toml] |
| aiosqlite | >=0.20.0 | Async SQLite for chat_messages table | [VERIFIED: pyproject.toml] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=8.3.0 | Test framework | Integration tests for chat endpoint |
| pytest-asyncio | >=0.24.0 | Async test support | All chat tests are async |
| httpx | >=0.27.0 | AsyncClient for testing FastAPI | ASGI transport testing pattern |

### Alternatives Considered
None -- the stack is already locked by prior phases.

## Architecture Patterns

### Existing Project Structure (relevant files)
```
backend/
├── app/
│   ├── api/
│   │   ├── chat.py          # ALREADY IMPLEMENTED - full chat endpoint
│   │   ├── portfolio.py     # Trade execution (reused by chat)
│   │   └── watchlist.py     # Watchlist CRUD (reused by chat)
│   ├── db/
│   │   ├── queries.py       # get_chat_history, save_chat_message
│   │   └── schema.py        # chat_messages table DDL
│   └── main.py              # Router registration, app.state
└── tests/
    ├── conftest.py           # Empty - minimal shared fixtures
    ├── test_portfolio.py     # Pattern to follow for chat tests
    └── test_watchlist.py     # Pattern to follow for chat tests
```

### Pattern 1: Integration Test Pattern (from existing codebase)
**What:** Test via httpx AsyncClient with ASGI transport, inject prices into cache, use isolated temp DB
**When to use:** All chat endpoint tests
**Example:**
```python
# Source: backend/tests/test_portfolio.py (existing pattern)
import os, tempfile
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_chat.db")
os.environ["LLM_MOCK"] = "true"

from httpx import ASGITransport, AsyncClient
from app.main import app

@pytest.fixture
async def client():
    await init_db()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

### Pattern 2: LiteLLM Structured Output
**What:** Pass a Pydantic BaseModel subclass as `response_format` to `litellm.completion()`
**When to use:** LLM call in chat endpoint (already implemented)
**Example:**
```python
# Source: .claude/skills/cerebras/SKILL.md
response = completion(
    model=MODEL,
    messages=messages,
    response_format=LLMResponse,  # Pydantic model
    reasoning_effort="low",
    extra_body=EXTRA_BODY,
)
result = LLMResponse.model_validate_json(response.choices[0].message.content)
```

### Pattern 3: Mock Mode Guard
**What:** Check `LLM_MOCK` env var before making external calls, return deterministic response
**When to use:** Testing and development without API key
**Example:**
```python
# Source: backend/app/api/chat.py lines 178-184
mock_mode = os.environ.get("LLM_MOCK", "false").lower() == "true"
if mock_mode:
    llm_result = LLMResponse(
        message="I'm running in mock mode...",
        trades=[],
        watchlist_changes=[],
    )
```

### Anti-Patterns to Avoid
- **Testing with real LLM calls:** Always use `LLM_MOCK=true` for automated tests. Never depend on external API availability.
- **Shared mutable DB state across tests:** Each test file should use its own temp DB path via `DB_PATH` env var (established pattern).
- **Catching exceptions too broadly:** The existing `except Exception` in the LLM call block is intentionally broad (CHAT-08 requires never returning 500). This is correct for production but tests should verify specific failure modes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM API calls | Custom HTTP client to OpenRouter | `litellm.completion()` | Handles auth, retries, model routing, response parsing |
| Structured output parsing | Manual JSON parsing + validation | Pydantic `response_format` + `model_validate_json` | Type safety, validation errors, schema generation |
| Async DB operations | Raw sqlite3 with thread pool | `aiosqlite` via existing `get_db()` context manager | Already established pattern, connection management handled |
| Test HTTP client | Manual request building | `httpx.AsyncClient` with `ASGITransport` | In-process testing, no server needed, established pattern |

## Common Pitfalls

### Pitfall 1: Mock Mode Returns Empty Actions
**What goes wrong:** The current mock mode returns empty `trades=[]` and `watchlist_changes=[]`, so tests using mock mode cannot verify the auto-execution pipeline end-to-end.
**Why it happens:** Mock mode is designed for "safe" operation, but this means the trade/watchlist execution paths are untested in integration.
**How to avoid:** Write tests that directly construct `LLMResponse` objects with trades/watchlist_changes and verify the execution logic. Alternatively, enhance mock mode to support query-specific mock responses (e.g., "buy AAPL" triggers a mock trade response).
**Warning signs:** Tests pass with mock mode but fail in production because auto-execution was never tested.

### Pitfall 2: DB State Bleeding Between Tests
**What goes wrong:** Tests depend on DB state from previous tests (e.g., cash balance reduced by earlier trades).
**Why it happens:** The existing test pattern uses `_initialized` flag that only sets up DB once per module.
**How to avoid:** Either reset DB state between tests or write tests that account for cumulative state. The existing test files use the cumulative approach (test classes ordered to build on each other).
**Warning signs:** Tests pass individually but fail when run together, or vice versa.

### Pitfall 3: LiteLLM Import at Call Time
**What goes wrong:** The `from litellm import completion` import is inside the endpoint function (line 187), not at module top level.
**Why it happens:** Intentional -- avoids import errors when LLM_MOCK=true and litellm is misconfigured.
**How to avoid:** This is actually a reasonable pattern for optional dependencies. Tests should verify that mock mode works without a valid OPENROUTER_API_KEY.
**Warning signs:** Import error at module load time when API key is missing.

### Pitfall 4: Price Cache Empty During Chat
**What goes wrong:** `price_cache.get_price(ticker)` returns `None` for tickers the user asks about, causing trade execution to fail with "No price for X".
**Why it happens:** Market source hasn't generated prices yet, or ticker was just added to watchlist.
**How to avoid:** Tests must inject prices into the cache before testing chat-initiated trades. The chat code already handles None prices gracefully (skips trade, adds to error list).
**Warning signs:** Chat trades always fail in test environment.

## Code Examples

### Testing Chat Endpoint with Mock Mode
```python
# Pattern derived from test_portfolio.py
import os, tempfile
_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(_tmp, "test_chat.db")
os.environ["LLM_MOCK"] = "true"

import pytest
from httpx import ASGITransport, AsyncClient
from app.db.schema import init_db
from app.main import app

@pytest.fixture
async def client():
    await init_db()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

class TestChatMockMode:
    async def test_chat_returns_structured_response(self, client):
        resp = await client.post("/api/chat", json={"message": "Hello"})
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "trades" in data
        assert "watchlist_changes" in data

    async def test_chat_saves_history(self, client):
        await client.post("/api/chat", json={"message": "What is my balance?"})
        # Verify messages were saved
        from app.db.queries import get_chat_history
        history = await get_chat_history(limit=20)
        assert len(history) >= 2  # user + assistant
        assert history[-2]["role"] == "user"
        assert history[-1]["role"] == "assistant"
```

### Testing LLM Failure Handling
```python
# Verify CHAT-08: graceful fallback on LLM failure
async def test_llm_failure_returns_200_with_fallback(self, client, monkeypatch):
    os.environ["LLM_MOCK"] = "false"
    # Mock litellm.completion to raise an exception
    def mock_completion(*args, **kwargs):
        raise ConnectionError("Simulated network failure")
    monkeypatch.setattr("app.api.chat.completion", mock_completion, raising=False)
    # Or patch the import inside the function

    resp = await client.post("/api/chat", json={"message": "Hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert "trouble connecting" in data["message"].lower()
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ with pytest-asyncio |
| Config file | `backend/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd backend && uv run --extra dev pytest tests/test_chat.py -v` |
| Full suite command | `cd backend && uv run --extra dev pytest -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CHAT-01 | POST /api/chat returns structured JSON | integration | `uv run --extra dev pytest tests/test_chat.py::TestChatEndpoint::test_returns_structured_json -x` | No - Wave 0 |
| CHAT-02 | LLM receives portfolio context | unit | `uv run --extra dev pytest tests/test_chat.py::TestChatContext::test_portfolio_context_built -x` | No - Wave 0 |
| CHAT-03 | LLM receives last 20 messages | integration | `uv run --extra dev pytest tests/test_chat.py::TestChatHistory::test_history_loaded -x` | No - Wave 0 |
| CHAT-04 | Structured output schema | unit | `uv run --extra dev pytest tests/test_chat.py::TestLLMResponse::test_schema_validation -x` | No - Wave 0 |
| CHAT-05 | Trades auto-execute | integration | `uv run --extra dev pytest tests/test_chat.py::TestAutoExecution::test_trade_executes -x` | No - Wave 0 |
| CHAT-06 | Watchlist changes auto-execute | integration | `uv run --extra dev pytest tests/test_chat.py::TestAutoExecution::test_watchlist_change -x` | No - Wave 0 |
| CHAT-07 | Failed trades in response | integration | `uv run --extra dev pytest tests/test_chat.py::TestAutoExecution::test_failed_trade_error -x` | No - Wave 0 |
| CHAT-08 | LLM failures return 200 fallback | integration | `uv run --extra dev pytest tests/test_chat.py::TestErrorHandling::test_llm_failure_fallback -x` | No - Wave 0 |
| CHAT-09 | Mock mode deterministic | integration | `uv run --extra dev pytest tests/test_chat.py::TestMockMode::test_mock_response -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && uv run --extra dev pytest tests/test_chat.py -v`
- **Per wave merge:** `cd backend && uv run --extra dev pytest -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_chat.py` -- covers CHAT-01 through CHAT-09
- [ ] No framework install needed (pytest already configured)
- [ ] No conftest changes needed (existing pattern sufficient)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Single-user app, no auth |
| V3 Session Management | No | No sessions |
| V4 Access Control | No | Single-user, hardcoded "default" user |
| V5 Input Validation | Yes | Pydantic BaseModel for request validation, ticker normalization (upper + strip) |
| V6 Cryptography | No | No crypto operations |

### Known Threat Patterns for LLM Integration

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection via user message | Tampering | System prompt hardcoded, user message is last in context. Low risk in simulated environment. |
| LLM returning invalid JSON | Tampering | Pydantic `model_validate_json()` rejects malformed responses; caught by except block |
| LLM requesting excessive trades | Elevation | Trades go through same validation as manual trades (cash/share checks). No elevated privileges. |
| API key exposure in logs | Information Disclosure | LiteLLM handles auth headers; key only in .env (gitignored) |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `openrouter/openai/gpt-oss-120b` model string is valid on OpenRouter with Cerebras provider | Standard Stack | LLM calls fail at runtime; mock mode unaffected [ASSUMED -- model string from PLAN.md but flagged as potentially incorrect in Section 13 Q1] |
| A2 | LiteLLM 1.83.0 supports `response_format` with Pydantic models for OpenRouter | Architecture | Structured output fails; would need manual JSON mode [ASSUMED -- code exists but untested against live API in this session] |

## Open Questions

1. **Model string validity (PLAN.md Q1)**
   - What we know: PLAN.md Section 13 flags that `openrouter/openai/gpt-oss-120b` may not be a valid model name
   - What's unclear: Whether this model exists on OpenRouter with Cerebras provider support
   - Recommendation: Test with a real API call during or after phase execution. Mock mode covers all automated testing, so this only blocks live demo.

2. **Mock mode coverage for auto-execution**
   - What we know: Current mock returns empty trades/watchlist_changes arrays
   - What's unclear: Whether tests should enhance mock mode to return actionable responses
   - Recommendation: Test auto-execution by directly testing the execution pipeline with constructed `LLMResponse` objects, bypassing the mock mode limitation.

## Sources

### Primary (HIGH confidence)
- `backend/app/api/chat.py` - full implementation reviewed line by line
- `backend/app/db/queries.py` - chat history and message saving functions
- `backend/tests/test_portfolio.py` - established testing patterns
- `.claude/skills/cerebras/SKILL.md` - LiteLLM/Cerebras usage patterns
- `backend/pyproject.toml` - dependency versions and test configuration

### Secondary (MEDIUM confidence)
- `planning/PLAN.md` Section 9 - LLM integration specification
- `planning/PLAN.md` Section 7 - chat_messages schema

### Tertiary (LOW confidence)
- Model string validity (`openrouter/openai/gpt-oss-120b`) - flagged by PLAN.md itself as unverified

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all dependencies already installed and in use
- Architecture: HIGH - implementation already exists, follows established patterns
- Pitfalls: HIGH - derived from actual code review, not speculation

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stable -- implementation exists, only testing needed)
