# Coding Conventions

**Analysis Date:** 2026-04-09

## Naming Patterns

**Files:**
- Lowercase with underscores: `cache.py`, `seed_prices.py`, `test_models.py`
- API route files grouped by feature: `api/chat.py`, `api/watchlist.py`, `api/portfolio.py`
- Test files mirror source structure: `tests/market/test_simulator.py` mirrors `app/market/simulator.py`

**Functions and Methods:**
- Snake case: `get_watchlist_tickers()`, `execute_trade()`, `_generate_events()`
- Private/internal functions prefixed with single underscore: `_snapshot_callback()`, `_iso_now()`, `_now()`
- Async functions named with verb: `start()`, `stop()`, `add_ticker()`, `remove_ticker()`

**Variables:**
- Snake case: `price_cache`, `market_source`, `cash_balance`
- Constants in UPPER_SNAKE_CASE: `DEFAULT_DT`, `TRADING_SECONDS_PER_YEAR`, `DEFAULT_WATCHLIST`
- Dictionary keys in camelCase or lowercase depending on JSON context: `{"ticker": "AAPL", "price": 190.50}`

**Types:**
- Classes in PascalCase: `PriceUpdate`, `PriceCache`, `MarketDataSource`, `SimulatorDataSource`, `TradeRequest`, `LLMResponse`
- Type hints use `|` union syntax (Python 3.10+): `ticker: str | None`, `dict[str, float]`

## Code Style

**Formatting:**
- Line length: 100 characters (see `tool.ruff` in `pyproject.toml`)
- Ruff handles formatting and linting
- No explicit formatter config (Ruff is all-in-one for Python)

**Linting:**
- Ruff configured with rules: `E` (pycodestyle errors), `F` (Pyflakes), `I` (isort imports), `N` (pep8 naming), `W` (warnings)
- Line length violations (`E501`) ignored per config
- Run via: `uv run --extra dev ruff check app/ tests/`

**Documentation:**
- Module-level docstring at top of each file: `"""Market data API modules."""`
- Class docstrings describe purpose and key state: See `PriceCache` in `app/market/cache.py` (lines 10-15)
- Method docstrings document inputs, behavior, and return value: See `cache.update()` (lines 23-46)
- Inline comments explain non-obvious logic, e.g., Cholesky decomposition reasoning in `simulator.py` (lines 29-44)

## Import Organization

**Order:**
1. `from __future__ import annotations` (always first)
2. Standard library (`os`, `asyncio`, `logging`, `datetime`)
3. Third-party (`fastapi`, `pydantic`, `aiosqlite`, `numpy`)
4. Local imports (relative: `from ..db`, `from .cache`)

**Path Aliases:**
- No path aliases configured; all imports are explicit relative or absolute
- Example: `from ..db import get_cash_balance` (relative from `app/api/portfolio.py` to `app/db`)

**Barrel Files:**
- `app/db/__init__.py` exports main functions: `get_db`, `init_db`, `get_watchlist_tickers`, etc.
- `app/market/__init__.py` exports key types and factory: `PriceCache`, `PriceUpdate`, `MarketDataSource`, `create_market_data_source`, `create_stream_router`
- Reduces verbosity: `from app.db import get_positions` instead of `from app.db.queries import get_positions`

## Error Handling

**Patterns:**
- HTTP errors via `HTTPException` from FastAPI with explicit status codes and detail messages
  ```python
  if side not in ("buy", "sell"):
      raise HTTPException(status_code=422, detail="side must be 'buy' or 'sell'")
  ```
  See `app/api/portfolio.py` lines 84-87.

- Database errors (constraint violations) caught with broad `except Exception` and logged
  ```python
  except Exception:
      # UNIQUE constraint violation — already exists
      return False
  ```
  See `app/db/queries.py` lines 46-48.

- Async task failures logged without raising (crash-resistant):
  ```python
  except Exception:
      logger.exception("Periodic portfolio snapshot failed")
  ```
  See `app/main.py` lines 45-46.

- Fallback responses for LLM failures (graceful degradation):
  ```python
  FALLBACK_RESPONSE = {
      "message": "Sorry, I'm having trouble connecting right now. Please try again.",
      ...
  }
  ```
  See `app/api/chat.py` lines 32-36.

## Logging

**Framework:** Python's `logging` module

**Patterns:**
- Module-level logger: `logger = logging.getLogger(__name__)`
- Use logger throughout module for info/warning/exception calls
- Log important lifecycle events (startup, shutdown, ticker changes):
  ```python
  logger.info("Market data source started with tickers: %s", tickers)
  logger.info("Added ticker to watchlist: %s", ticker)
  logger.exception("Periodic portfolio snapshot failed")
  ```
- Configured in `app/main.py` with:
  ```python
  logging.basicConfig(
      level=logging.INFO,
      format="%(asctime)s %(levelname)s %(name)s — %(message)s",
  )
  ```

## Comments

**When to Comment:**
- Explain WHY, not WHAT. If code is self-documenting, skip the comment.
- Complex algorithms: see GBM explanation in `app/market/simulator.py` (lines 29-44)
- Non-obvious design decisions: see `cache.py` comments on Cholesky (line 65), session open immutability (lines 43-46)
- Data format details: SSE event structure documented in `app/market/stream.py`

**Inline Comments:**
- Sparse; used only for tricky math or state transitions
- Example: `# Set session open price on first update; never overwrite it` in `cache.py` line 43

**Module Docstrings:**
- Required at top of every file
- Brief, one-sentence or short paragraph describing the module's purpose
- Examples: `"""Thread-safe in-memory price cache."""`, `"""Database schema creation and seed data."""`

## Function Design

**Size:**
- Keep functions focused: single responsibility
- Examples: `update()` in `PriceCache` handles one price update, `execute_trade()` handles one trade with clear return dict structure
- Async methods are allowed to be longer to avoid callback nesting; see `execute_trade()` in `queries.py` (~60 lines)

**Parameters:**
- Positional for required args: `def update(self, ticker: str, price: float)`
- Optional args via default or keyword: `session_open_price: float | None = None`
- Pass Request object to access shared state in FastAPI routes: `async def get_portfolio(request: Request)`
- Use Pydantic models for request bodies: `async def trade(body: TradeRequest, request: Request)`

**Return Values:**
- Functions return dicts with explicit keys for complex results:
  ```python
  return {
      "success": result["success"],
      "error": result["error"],
      "ticker": ticker,
      "side": side,
      "quantity": quantity,
      "price": current_price,
      "cash_balance": result["cash_balance"],
      "position": result["position"],
  }
  ```
  See `app/api/portfolio.py` lines 117-126.

- Single values when simple: `return bool`, `return float`, `return list[dict]`

- Immutable dataclasses for value objects: `PriceUpdate` is frozen with `@dataclass(frozen=True, slots=True)`

## Module Design

**Exports:**
- Barrel files (`__init__.py`) collect and re-export public APIs:
  ```python
  # app/db/__init__.py
  from .connection import get_db
  from .schema import init_db
  from .queries import (get_positions, execute_trade, ...)
  ```
  See actual file at `app/db/__init__.py`.

- Private functions start with `_` (e.g., `_iso_now()`, `_snapshot_callback()`) and are not exported

**Abstraction via Interfaces:**
- `MarketDataSource` is an ABC (Abstract Base Class) in `app/market/interface.py`
- Two implementations: `SimulatorDataSource` and `MassiveDataSource`
- Factory pattern: `create_market_data_source()` returns one or the other based on env vars
- See `app/market/factory.py` for factory function

**Dependency Injection:**
- Shared state (price cache, market source) passed via FastAPI `app.state`:
  ```python
  app.state.price_cache = price_cache
  app.state.market_source = market_source
  ```
  And accessed in routes: `price_cache = request.app.state.price_cache`
- Avoids globals; makes testing easier

---

*Convention analysis: 2026-04-09*
