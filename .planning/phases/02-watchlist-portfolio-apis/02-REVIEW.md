---
phase: 02-watchlist-portfolio-apis
reviewed: 2026-04-09T12:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - backend/app/api/chat.py
  - backend/app/api/health.py
  - backend/app/db/__init__.py
  - backend/app/db/connection.py
  - backend/pyproject.toml
  - backend/tests/market/test_stream.py
  - backend/tests/test_portfolio.py
  - backend/tests/test_watchlist.py
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-04-09T12:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Reviewed the backend API layer (chat, health, portfolio, watchlist), database connection module, pyproject.toml, and integration tests. The code is generally well-structured with proper use of async patterns, parameterized SQL queries (no injection risk), and clean separation of concerns. However, there is one critical race condition in the trade execution path, several warnings around error handling and input validation, and a few informational items.

## Critical Issues

### CR-01: Race condition in trade execution -- no transaction isolation

**File:** `backend/app/db/queries.py:111-196`
**Issue:** The `execute_trade` function reads the current cash balance and position, performs validation, then writes updates -- all within a single `aiosqlite` connection but without explicit transaction control beyond the default. Because `get_db()` opens a new connection each call and the function does multiple read-then-write steps, concurrent requests (e.g., two rapid buy requests) can both read the same cash balance, both pass validation, and both deduct -- resulting in a negative cash balance. While SQLite's write lock serializes at the DB level, the `aiosqlite` connection uses WAL mode (set in `connection.py:17`), which allows concurrent readers. Two coroutines could interleave: both read cash=10000, both validate a $9000 purchase passes, both write.

**Fix:** Wrap the entire read-validate-write sequence in an explicit `BEGIN IMMEDIATE` transaction to acquire a write lock before the reads:
```python
async with get_db() as db:
    await db.execute("BEGIN IMMEDIATE")
    try:
        # ... read cash, read position, validate, write updates ...
        await db.commit()
    except Exception:
        await db.rollback()
        raise
```

## Warnings

### WR-01: Broad exception catch in add_watchlist_ticker silences real errors

**File:** `backend/app/db/queries.py:46-48`
**Issue:** The `except Exception` block assumes any exception is a UNIQUE constraint violation and returns `False`. Database connection errors, disk full errors, or schema issues would all be silently swallowed, making debugging difficult. The function would report "already exists" when the real problem is a database failure.

**Fix:** Catch the specific `aiosqlite.IntegrityError` instead:
```python
from sqlite3 import IntegrityError

try:
    await db.execute(...)
    await db.commit()
    return True
except IntegrityError:
    return False
```

### WR-02: Sell quantity comparison uses floating-point equality

**File:** `backend/app/db/queries.py:157-169`
**Issue:** `if quantity > owned` uses direct float comparison. Due to floating-point arithmetic, after multiple buy/sell operations, `owned` could be a value like `5.000000000000001` or `4.999999999999999`. A user trying to sell all shares (quantity=5, owned=4.999999999999999) would get "Insufficient shares." Similarly, `if new_qty <= 0` on line 169 could leave a near-zero ghost position (e.g., quantity=1e-15) that never gets cleaned up.

**Fix:** Use a small epsilon for the comparison, or round quantities to a fixed precision (e.g., 8 decimal places) on every read/write:
```python
EPSILON = 1e-9
if quantity > owned + EPSILON:
    return {"success": False, "error": ...}
new_qty = owned - quantity
if new_qty < EPSILON:
    # Treat as fully sold
    await db.execute("DELETE FROM positions ...")
```

### WR-03: Chat endpoint TradeAction.side and WatchlistChange.action lack validation

**File:** `backend/app/api/chat.py:69-76`
**Issue:** `TradeAction.side` is typed as `str` with no constraint. The LLM could return `side: "short"` or `side: "SELL"` (uppercase). While `side` is lowercased on line 208, invalid values like `"short"` would pass through to `execute_trade` which returns a generic error dict, but the error is not surfaced to the user -- it is only captured in `trade_errors`. Similarly, `WatchlistChange.action` accepts any string; an invalid action (not "add"/"remove") silently does nothing (falls through the if/elif on lines 240-249 without any error).

**Fix:** Use `Literal` types on the Pydantic models for stricter validation, or add an `else` clause:
```python
from typing import Literal

class TradeAction(BaseModel):
    ticker: str
    side: Literal["buy", "sell"]
    quantity: float

class WatchlistChange(BaseModel):
    ticker: str
    action: Literal["add", "remove"]
```

### WR-04: DB_PATH evaluated at import time, not at connection time

**File:** `backend/app/db/connection.py:10`
**Issue:** `DB_PATH = os.environ.get("DB_PATH", "./db/finally.db")` is evaluated once at module import. The test file `test_portfolio.py` works around this by setting `os.environ["DB_PATH"]` before importing the module (lines 23-24). However, `test_watchlist.py` uses `monkeypatch.setattr(conn_mod, "DB_PATH", db_file)` (line 27) which is more fragile -- it patches the module attribute but any code that captured the value in a local variable or closure would miss the patch. This creates a latent test isolation bug: if import order changes, tests could hit the wrong database.

**Fix:** Read the environment variable inside `get_db()` to always use the current value:
```python
@asynccontextmanager
async def get_db():
    db_path = os.environ.get("DB_PATH", "./db/finally.db")
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        yield db
```

## Info

### IN-01: Health endpoint does not verify database connectivity

**File:** `backend/app/api/health.py:9-10`
**Issue:** The health check returns `{"status": "ok"}` unconditionally without verifying the SQLite database is accessible. This makes Docker HEALTHCHECK less useful -- the container could report healthy while the database is corrupted or missing.

**Fix:** Add a lightweight database check:
```python
@router.get("/api/health")
async def health_check():
    try:
        async with get_db() as db:
            await db.execute("SELECT 1")
        return {"status": "ok"}
    except Exception:
        return JSONResponse({"status": "error"}, status_code=503)
```

### IN-02: Test file test_portfolio.py uses shared mutable state across tests

**File:** `backend/tests/test_portfolio.py:23-41`
**Issue:** The test file sets `os.environ["DB_PATH"]` at module level (line 24) and uses a global `_initialized` flag (line 31). All test classes share the same database and cumulative state -- e.g., `TestBuyTrade` buys AAPL, then `TestSellTrade` runs against the modified cash balance. This makes tests order-dependent and prevents parallel execution. If a test fails, subsequent tests may fail for unrelated reasons due to polluted state.

**Fix:** Consider using the same pattern as `test_watchlist.py` -- a `monkeypatch` fixture that creates a fresh temp DB for each test or test class, and use the app lifespan context to properly initialize.

### IN-03: Unused import in chat.py

**File:** `backend/app/api/chat.py:7`
**Issue:** `Optional` is imported from `typing` but never used in the file. All optional types use `| None` syntax or default values instead.

**Fix:** Remove the unused import:
```python
# Remove this line:
from typing import Optional
```

---

_Reviewed: 2026-04-09T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
