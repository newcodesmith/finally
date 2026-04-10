# Testing Patterns

**Analysis Date:** 2026-04-09

## Test Framework

**Runner:**
- pytest 8.3.0+ (see `pyproject.toml`)
- Config: `pyproject.toml` lines 34-40
- Async support via pytest-asyncio 0.24.0+

**Assertion Library:**
- pytest's built-in `assert` statements (no external assertion library)

**Run Commands:**
```bash
uv run --extra dev pytest -v              # Run all tests with verbose output
uv run --extra dev pytest --cov=app       # Run with coverage report
uv run --extra dev ruff check app/ tests/ # Lint code (ruff)
```

**Coverage:**
- Tool: pytest-cov 5.0.0+
- Configuration in `pyproject.toml` lines 50-62
- Source: `app/` directory
- Omit: `tests/*` files themselves
- View coverage: `uv run --extra dev pytest --cov=app --cov-report=html`

## Test File Organization

**Location:**
- Co-located in `tests/` directory matching `app/` structure
- `tests/market/` mirrors `app/market/`
- `tests/` is at the same level as `app/`

**Naming:**
- Test files: `test_*.py` (pytest discovery pattern)
- Test classes: `Test*` (PascalCase)
- Test functions: `test_*` (snake_case)

**Structure:**
```
backend/
├── app/
│   ├── market/
│   │   ├── models.py
│   │   ├── cache.py
│   │   ├── simulator.py
│   │   └── ...
│   └── db/
│       ├── queries.py
│       └── ...
├── tests/
│   ├── conftest.py       # Shared fixtures
│   ├── market/
│   │   ├── test_models.py
│   │   ├── test_cache.py
│   │   ├── test_simulator.py
│   │   └── ...
│   └── __init__.py
└── pyproject.toml
```

## Test Structure

**Suite Organization:**

```python
# tests/market/test_models.py
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
```

**Patterns:**

- **Test class grouping:** Each class has a docstring describing what it tests. Classes organize tests by feature/class.
  See `TestPriceUpdate` in `tests/market/test_models.py` (lines 10-142).

- **Setup/Teardown:** No explicit `setUp()` or `tearDown()` methods; fixtures handle setup instead (see Fixtures section).

- **Assertion pattern:** Direct `assert` statements with clear test names that explain what is being verified.
  Example: `test_direction_up()`, `test_change_percent_zero_previous()` are self-documenting.

- **Constants:** Fixed values (timestamps, test data) defined at module level: `FIXED_TS = "2024-01-01T00:00:00+00:00"` in `test_models.py`.

## Mocking

**Framework:** Python's `unittest.mock` (standard library)

**Patterns:**

```python
# tests/market/test_stream.py
from unittest.mock import MagicMock

class MockRequest:
    """Minimal Request stub for testing _generate_events."""

    def __init__(self, disconnect_after_calls: int = 0) -> None:
        self._calls = 0
        self._disconnect_after = disconnect_after_calls
        self.client = MagicMock()
        self.client.host = "127.0.0.1"

    async def is_disconnected(self) -> bool:
        self._calls += 1
        return self._calls > self._disconnect_after
```

See `tests/market/test_stream.py` lines 14-26.

**What to Mock:**
- External dependencies: HTTP clients, file I/O, network calls
- FastAPI Request objects when testing generators (see `MockRequest` above)
- Complex async state (use lightweight mocks)

**What NOT to Mock:**
- Pure business logic (PriceUpdate, PriceCache, GBMSimulator) — test directly
- Database connections (use real async context) — tests are isolated in-memory
- Market data sources (test actual implementations; they're lightweight)

## Fixtures and Factories

**Test Data:**

No explicit fixture definitions in `conftest.py` (it's currently empty). Instead:
- Inline fixture creation within test methods: `cache = PriceCache()`, `sim = GBMSimulator(tickers=["AAPL"])`
- Module-level constants for reusable data: `FIXED_TS = "2024-01-01T00:00:00+00:00"`

Example from `tests/market/test_cache.py`:
```python
def test_update_and_get(self):
    """Test updating and getting a price."""
    cache = PriceCache()
    update = cache.update("AAPL", 190.50)
    assert update.ticker == "AAPL"
    assert update.price == 190.50
    assert cache.get("AAPL") == update
```

See `tests/market/test_cache.py` lines 9-15.

**Async Fixture Pattern:**

For async tests, use pytest-asyncio's `@pytest.mark.asyncio` decorator:
```python
@pytest.mark.asyncio
class TestSimulatorDataSource:
    """Integration tests for the SimulatorDataSource."""

    async def test_start_populates_cache(self):
        """Test that start() immediately populates the cache."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start(["AAPL", "GOOGL"])
        assert cache.get("AAPL") is not None
        await source.stop()
```

See `tests/market/test_simulator_source.py` lines 11-25.

**Location:**
- Fixtures would live in `tests/conftest.py` if needed for multiple test modules (currently empty)
- Inline factories preferred for clarity and isolation

## Coverage

**Requirements:** None explicitly enforced in CI/CD

**View Coverage:**
```bash
uv run --extra dev pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

**Coverage Config:**
- Source directory: `app/`
- Omit: Test files themselves and __pycache__
- Exclude lines: pragma comments, `__repr__`, `NotImplementedError`, type checking blocks
- See `tool.coverage` in `pyproject.toml` lines 50-62

## Test Types

**Unit Tests:**
- **Scope:** Single class or function
- **Examples:**
  - `TestPriceUpdate` in `tests/market/test_models.py` — tests `PriceUpdate` dataclass properties
  - `TestPriceCache` in `tests/market/test_cache.py` — tests `PriceCache` methods in isolation
  - `TestGBMSimulator` in `tests/market/test_simulator.py` — tests math and state management
- **Approach:** Create minimal dependencies, assert on return values and state

**Integration Tests:**
- **Scope:** Multiple components working together
- **Examples:**
  - `TestSimulatorDataSource` in `tests/market/test_simulator_source.py` — tests simulator + cache together
  - `TestGenerateEvents` in `tests/market/test_stream.py` — tests generator + cache interaction with mock requests
- **Approach:** Spin up real objects, test interactions, verify side effects

**E2E Tests:**
- **Framework:** Not yet implemented (stretch goal)
- **Planned location:** `test/` directory (separate from backend/tests/)
- **Strategy:** Docker-based using docker-compose.test.yml with Playwright
- **Environment:** `LLM_MOCK=true` for deterministic responses

## Common Patterns

**Async Testing:**

```python
@pytest.mark.asyncio
class TestSimulatorDataSource:
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
```

See `tests/market/test_simulator_source.py` lines 27-39.

**Notes:**
- Use `@pytest.mark.asyncio` on test class or individual methods
- `asyncio_mode = "auto"` in pytest config handles event loop automatically
- Cleanup via `await source.stop()` to avoid resource leaks

**Error Testing:**

```python
def test_change_percent_zero_previous(self):
    """Test percentage change with zero previous price."""
    update = PriceUpdate(
        ticker="AAPL", price=100.00, previous_price=0.00,
        session_open_price=0.00, timestamp=FIXED_TS,
    )
    assert update.change_percent == 0.0
```

And edge-case error handling with exceptions:
```python
def test_immutability(self):
    """Test that PriceUpdate is immutable."""
    update = PriceUpdate(
        ticker="AAPL", price=190.50, previous_price=190.00,
        session_open_price=190.00, timestamp=FIXED_TS,
    )

    with pytest.raises(AttributeError):
        update.price = 200.00  # Should raise error
```

See `tests/market/test_models.py` lines 122-130.

**Helper Functions for Streaming Tests:**

```python
async def collect_events(cache: PriceCache, disconnect_after: int = 1, interval: float = 0.01) -> list[str]:
    """Collect all yielded SSE events from the generator."""
    request = MockRequest(disconnect_after_calls=disconnect_after)
    events = []
    async for event in _generate_events(cache, request, interval=interval):
        events.append(event)
    return events
```

See `tests/market/test_stream.py` lines 29-35. Allows clean SSE testing without complex async orchestration.

## Test Statistics

**Current Test Count:**
- Market data tests: ~150 assertions across 10+ test classes
- Total test file lines: 1,152 (market/ tests)
- Coverage areas: models, cache, simulator, stream, factory, massive API stubs

**Areas with Tests:**
- `app/market/`: Complete coverage (models, cache, simulator, streaming, factory)
- `app/db/`: Partial (queries module tested indirectly via API tests)
- `app/api/`: Not yet (stretch goal — integration tests planned)

**Areas without Tests:**
- `app/api/portfolio.py`, `app/api/watchlist.py`, `app/api/chat.py` — no unit tests yet
- Database operations (`app/db/queries.py`) — tested via integration
- API route handlers — E2E tests planned for these

---

*Testing analysis: 2026-04-09*
