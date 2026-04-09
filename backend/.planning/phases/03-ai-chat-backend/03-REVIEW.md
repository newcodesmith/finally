---
phase: 03-ai-chat-backend
reviewed: 2026-04-09T00:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - backend/tests/test_chat.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-04-09
**Depth:** standard
**Files Reviewed:** 1
**Status:** issues_found

## Summary

One test file reviewed: `backend/tests/test_chat.py`. The file tests the chat API endpoint and LLM integration across eight requirement areas (CHAT-01 through CHAT-09). The overall structure is sound — async client fixtures, monkeypatching for LLM mocking, and clear test class organization.

Four warnings were found: the `disable_mock` fixture does not reset the `LLM_MOCK` env var to the correct initial state when tests alter it mid-run; `TestChatHistory` accumulates shared state across test methods and produces fragile count assertions; `TestAutoExecution.test_trade_auto_executes_buy` uses a `>=` quantity assertion that allows false positives from prior test runs; and the `_make_mock_completion` helper returns a synchronous lambda which will fail silently if the production `litellm.completion` is async. Three info items cover unnecessary assertions about the `errors` field that assume undocumented response shape, the missing `conftest.py` teardown for the temp DB, and a `_MockChoice` dynamic-type construction that hides the attribute contract.

---

## Warnings

### WR-01: `disable_mock` fixture restores from a snapshot that may already be `"false"`

**File:** `backend/tests/test_chat.py:265`
**Issue:** The fixture captures `os.environ.get("LLM_MOCK", "true")` at setup time. The module-level line `os.environ["LLM_MOCK"] = "true"` (line 20) runs once at import, but if a prior test in the same session had already altered the env var to `"false"` without restoring it, the fixture will lock in `"false"` as the "original" value, and after the fixture yields it will restore to `"false"` instead of `"true"`. Subsequent mock-dependent tests (`TestMockMode`, `TestChatContext`) would then call the real LLM path.

**Fix:**
```python
@pytest.fixture
def disable_mock():
    """Temporarily set LLM_MOCK=false so the real (monkeypatched) LLM path executes."""
    os.environ["LLM_MOCK"] = "false"
    yield
    os.environ["LLM_MOCK"] = "true"   # always restore to the module-level default
```

---

### WR-02: `TestChatHistory` count assertions are order-dependent and fragile

**File:** `backend/tests/test_chat.py:148-169`
**Issue:** Both `test_chat_saves_user_and_assistant_messages` (line 148) and `test_history_accumulates` (line 155) call `get_chat_history` against the **shared** database that accumulates messages from every prior test in the session (since `_initialized` is a module-level flag preventing re-initialization). `test_history_accumulates` asserts `len(history) >= 6` — this assertion is vacuously true after any other test class has already deposited messages, making it unable to verify that exactly these three calls produced exactly six new messages. If the implementation regresses (e.g., only user messages are saved), the test still passes.

**Fix:** Capture the history length before sending messages and assert the delta:
```python
async def test_history_accumulates(self, client: AsyncClient):
    from app.db.queries import get_chat_history

    before = await get_chat_history(limit=200)
    before_count = len(before)

    for i in range(3):
        resp = await client.post("/api/chat", json={"message": f"Accumulation test {i}"})
        assert resp.status_code == 200

    after = await get_chat_history(limit=200)
    assert len(after) >= before_count + 6
```

---

### WR-03: `test_trade_auto_executes_buy` quantity assertion allows accumulated position from prior tests

**File:** `backend/tests/test_chat.py:304-306`
**Issue:** The assertion `aapl_pos[0]["quantity"] >= 5` is satisfied even if prior tests (e.g., `TestChatContext.test_context_includes_positions` which also buys 5 AAPL) have already accumulated shares. If the auto-execution is broken and the chat call does not execute the trade, the assertion still passes because of residual position from other tests.

**Fix:** Snapshot the position before the chat call and assert the increase:
```python
portfolio_before = await client.get("/api/portfolio")
before_qty = next(
    (p["quantity"] for p in portfolio_before.json()["positions"] if p["ticker"] == "AAPL"),
    0.0,
)

resp = await client.post("/api/chat", json={"message": "Buy 5 AAPL"})
# ...existing assertions on data...

portfolio = await client.get("/api/portfolio")
aapl_pos = [p for p in portfolio.json()["positions"] if p["ticker"] == "AAPL"]
assert len(aapl_pos) >= 1
assert aapl_pos[0]["quantity"] >= before_qty + 5
```

---

### WR-04: `_make_mock_completion` returns a synchronous callable; async `litellm.completion` will silently fail

**File:** `backend/tests/test_chat.py:257-260`
**Issue:** `_make_mock_completion` returns `lambda **kwargs: _MockLLMResponse(content)` — a plain synchronous function. If the production code calls `await litellm.completion(...)` (i.e., uses the async API), `monkeypatch.setattr` replaces it with a sync callable. Python will then `await` the returned `_MockLLMResponse` object, which is not awaitable. This raises `TypeError: object _MockLLMResponse is not awaitable` at runtime, causing every `TestAutoExecution` and `TestFailedTrades` test to fail or — worse — to trigger the fallback path rather than the intended monkeypatched path, producing false greens on CHAT-07 and CHAT-08 tests.

Verify whether `chat.py` uses `await litellm.acompletion` or the sync `litellm.completion`. If async:
```python
import asyncio

def _make_mock_completion(response_dict: dict):
    """Return an async callable that mimics litellm.acompletion."""
    content = json.dumps(response_dict)
    async def _mock(**kwargs):
        return _MockLLMResponse(content)
    return _mock
```
And update the `monkeypatch.setattr` target to match (`litellm.acompletion`).

---

## Info

### IN-01: `TestFailedTrades` asserts `data["errors"]` — field not in PLAN.md schema

**File:** `backend/tests/test_chat.py:413, 427`
**Issue:** Lines 413 and 427 assert `data["errors"]` exists in the response and contains specific strings. The PLAN.md structured output schema (section 9) defines only `message`, `trades`, and `watchlist_changes`. An `errors` field is an implementation extension. If the field is intentional and permanent, it should be documented in the schema. If it may be removed or renamed, these assertions will produce `KeyError` rather than a descriptive test failure.

**Fix:** Guard the assertion or use `.get()`:
```python
errors = data.get("errors", [])
assert any("Insufficient cash" in e for e in errors), (
    f"Expected 'Insufficient cash' in errors; got: {data}"
)
```

---

### IN-02: Temp DB directory is never cleaned up

**File:** `backend/tests/test_chat.py:18-19`
**Issue:** `tempfile.mkdtemp()` creates a directory that is never removed. On repeated test runs this accumulates temp directories. This is low severity (the OS eventually cleans `/tmp`) but can fill disk in CI environments with many test runs.

**Fix:** Use a pytest session-scoped fixture with cleanup, or use `tmp_path_factory` via a `conftest.py`:
```python
# conftest.py
import pytest, tempfile, shutil, os

@pytest.fixture(scope="session", autouse=True)
def temp_db_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("chat_db")
    os.environ["DB_PATH"] = str(d / "test_chat.db")
    os.environ["LLM_MOCK"] = "true"
    yield d
    shutil.rmtree(d, ignore_errors=True)
```

---

### IN-03: `_MockChoice` uses an anonymous type for the `message` attribute

**File:** `backend/tests/test_chat.py:246-248`
**Issue:** `type("M", (), {"content": content})()` creates an anonymous class at call time. This is difficult to inspect in tracebacks and hides the attribute contract. If the production code accesses any attribute other than `.content` (e.g., `.finish_reason`), the access will raise `AttributeError` with an unhelpful type name `M`.

**Fix:** Replace with a simple dataclass or named class:
```python
from dataclasses import dataclass

@dataclass
class _MockMessage:
    content: str
    finish_reason: str = "stop"

@dataclass
class _MockChoice:
    message: _MockMessage

    def __init__(self, content: str):
        self.message = _MockMessage(content=content)
```

---

_Reviewed: 2026-04-09_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
