# Market Data Backend — Code Review

**Reviewed by:** Claude Code  
**Date:** 2026-04-03  
**Scope:** `backend/app/market/` (8 modules), `backend/app/main.py`, `backend/app/api/watchlist.py`, `backend/app/api/portfolio.py`, `backend/tests/market/` (6 modules)  
**Test result:** 80 passed, 0 failed

---

## 1. Spec Conformance

### Section 6 — Market Data

| Requirement | Status | Notes |
|---|---|---|
| Two implementations (simulator + Massive) behind one interface | PASS | Strategy pattern correctly applied |
| GBM with correlated moves | PASS | Cholesky decomposition of sector-based correlation matrix |
| ~500ms update interval | PASS | `SimulatorDataSource` defaults to `update_interval=0.5` |
| Correlated moves (tech at 0.6, finance at 0.5, cross-sector at 0.3) | PASS | Matches spec exactly |
| Occasional random events (2-5% moves, ~0.1% probability) | PASS | `event_probability=0.001`, shock range `[0.02, 0.05]` |
| Realistic seed prices | PASS | AAPL $190, GOOGL $175, MSFT $420, etc. |
| Session open price retained on first tick | PASS | `PriceCache._session_opens` never overwritten |
| Massive: REST polling (not WebSocket) | PASS | Polls `get_snapshot_all()` |
| Massive: configurable poll interval (default 15s) | PASS | `poll_interval=15.0` default |
| Massive: first price retained as session open | PARTIAL — see Bug #1 |
| Cache tracks only watchlist tickers | PASS | `remove_ticker()` prunes cache |
| SSE: `GET /api/stream/prices` endpoint | PASS | |
| SSE: ~500ms push cadence | PASS | `_generate_events` sleeps 0.5s per cycle |
| SSE: event payload includes ticker, price, previous_price, session_open_price, timestamp, change_direction | PASS | `to_dict()` matches exactly |
| SSE: client reconnection | PASS | `retry: 1000` directive emitted; `EventSource` handles reconnect |

### Section 7 — Database

| Requirement | Status | Notes |
|---|---|---|
| Portfolio snapshot every 30 seconds | PASS | `SNAPSHOT_TICKS = 60` at 0.5s = 30s |
| Snapshot immediately after each trade | PASS | `portfolio.py` line 106–115 |
| Old snapshots pruned after 24 hours | PASS | `queries.py` `record_portfolio_snapshot()` line 229 |
| Lazy DB init on startup | PASS | `init_db()` called in lifespan |

### Section 8 — API Endpoints

| Endpoint | Status | Notes |
|---|---|---|
| `GET /api/stream/prices` | PASS | |
| `GET /api/watchlist` (returns latest prices) | PASS | Includes full `session_open_price` for session change % calculation |
| `POST /api/watchlist` (auto-adds to market source) | PASS | |
| `DELETE /api/watchlist/{ticker}` (prunes cache) | PASS | |
| `POST /api/portfolio/trade` (auto-adds ticker to watchlist) | PASS | |

### Deviations from Spec

1. **`MARKET_POLL_INTERVAL_SECONDS` env var not implemented.** PLAN.md §5 specifies this variable; `factory.py` hardcodes `poll_interval=15.0` (the default) and never reads it. This is a documentation/spec gap. Simplification opportunity S2 in the plan notes this as acceptable, but the behavior diverges from what `.env.example` might document.

2. **`direction` property label.** The `CLAUDE.md` developer guide at line 4 describes the `direction` property values as `"up"/"down"/"flat"` but the actual implementation uses `"up"/"down"/"unchanged"`. Clarification C4 in PLAN.md noted this ambiguity; the implementation chose correctly ("unchanged" is more semantically precise), but the internal developer docs are wrong and will mislead future developers.

3. **Snapshot callback injected via private attribute access.** `main.py` line 55 sets `source._snapshot_callback = _snapshot_callback` on the `SimulatorDataSource` instance after construction. This bypasses the constructor and accesses a private attribute from outside the class. It works because Python's "private" is convention-only, but it is a fragile coupling. The `MassiveDataSource` has no snapshot mechanism at all (as the spec permits), so this asymmetry is intentional but undocumented.

---

## 2. Code Quality

### Strengths

- **Consistent use of `from __future__ import annotations`** across all modules — ensures forward-reference annotations resolve correctly on Python 3.12.
- **Frozen dataclass with `slots=True` for `PriceUpdate`** — memory-efficient, immutable, hashable.
- **Guard against zero previous price** in `change_percent` — correct edge-case handling.
- **Structured logging** throughout using module-level `logger = logging.getLogger(__name__)`.
- **`asyncio.to_thread()`** in `MassiveDataSource._poll_once()` — correct pattern for running synchronous blocking code from an async context.
- **No bare `except:` clauses** — all exception handlers catch `Exception` (not `BaseException`), preserving `KeyboardInterrupt` and `SystemExit` propagation.
- **`round(..., 2)` applied consistently** at the cache layer, not in the model — prices stored in the cache are always 2dp.

### Issues

**Issue QC-1 (Minor): `GBMSimulator._rebuild_cholesky` does not handle non-positive-definite matrices.**
`numpy.linalg.cholesky` raises `LinAlgError` if the input matrix is not positive definite. While the hardcoded correlation values (0.3, 0.5, 0.6) will always produce a positive-definite matrix for the default tickers, a user adding many tickers with the same `CROSS_GROUP_CORR = 0.3` could encounter an ill-conditioned matrix if the correlation structure is numerically borderline. There is no try/except around `np.linalg.cholesky(corr)` in `simulator.py` line 173. A crash here would silently kill the simulator background task (caught by the outer `except Exception` in `_run_loop`), but on restart would fail again on the same ticker set.

**Issue QC-2 (Minor): `_iso_now()` defined twice.**
An identical `_iso_now()` helper is defined in both `models.py` (line 9) and `cache.py` (line 12). These should be consolidated into a single shared utility or the one in `models.py` should be imported by `cache.py`. The current duplication is not a bug but violates DRY.

**Issue QC-3 (Minor): `SimulatorDataSource.add_ticker()` not guarded against missing `_sim`.**
`add_ticker()` (line 250) is `async def add_ticker(self, ticker: str) -> None` and checks `if self._sim:` before acting. This is correct. However, since the ABC defines `add_ticker` as a contract that "no-ops if already present", there is no documented behavior for calling `add_ticker` before `start()`. The current implementation silently no-ops, which is acceptable but worth an inline comment.

**Issue QC-4 (Minor): Version counter not thread-safe for reads.**
`cache.py` line 86: the `version` property reads `self._version` without acquiring the lock. Since `_version` is an `int` (a CPython atomic type for simple increments), this is safe in CPython due to the GIL, but is not guaranteed correct in free-threaded Python builds (PEP 703 / Python 3.13+). For future-proofing this should use `with self._lock: return self._version`.

**Issue QC-5 (Cosmetic): `stream.py` module-level `router` and factory pattern conflict.**
`stream.py` line 17 creates a module-level `router = APIRouter(...)` and then `create_stream_router()` closes over it via the inner `@router.get("/prices")` decorator. This means calling `create_stream_router()` twice would register the same route twice on the same router object, causing duplicate route registration. In practice this is never done (only called once in `main.py`), but the module-level router combined with a factory function is architecturally confusing. A clean factory would create a new `APIRouter` inside `create_stream_router()` and return it.

---

## 3. Architecture

### Strategy Pattern

The abstract `MarketDataSource` ABC is clean and minimal — five methods: `start`, `stop`, `add_ticker`, `remove_ticker`, `get_tickers`. Both implementations satisfy the contract. The factory correctly reads the environment variable and returns the appropriate unstarted source. This is a textbook application of the Strategy pattern.

### PriceCache as Single Point of Truth

The cache is the correct single producer/consumer rendezvous point. All readers (`SSE`, `portfolio`, `watchlist API`) read from the cache; all writers (`SimulatorDataSource`, `MassiveDataSource`) write to it. The threading design is sound: a `threading.Lock` protects all mutations. Reads of individual prices (`get`, `get_price`) acquire the lock and return immediately. The `get_all()` snapshot returns a shallow copy of the internal dict, which is correct — the caller gets a stable snapshot that won't be mutated.

### Snapshot Callback Injection

The snapshot callback (periodic portfolio valuation) is injected into `SimulatorDataSource` via `main.py`. This is an implementation of the suggestion in PLAN.md §13 S4 (collapse portfolio snapshot into the price update loop). The `SNAPSHOT_TICKS = 60` constant is class-level on `SimulatorDataSource`, which means it is not configurable without subclassing. This is fine for the project scope.

A subtle issue: `MassiveDataSource` has no snapshot mechanism. When running with a real API key, portfolio snapshots will **only** be recorded after manual trades, not on the 30-second background cadence. This is a spec deviation — PLAN.md §7 says snapshots are "recorded every 30 seconds by a background task." The `MassiveDataSource` background task ticks at 15-second intervals, which could carry the snapshot counter, but no such logic exists.

### Session Open Price Handling

The spec (PLAN.md §6) states the first price received per ticker is retained as the session open. The implementation handles this correctly for the simulator (initial prices seeded on `start()` and `add_ticker()` call `cache.update(..., session_open_price=price)`). For the Massive client, the **first poll** sets the session open implicitly because `cache.update()` with no `session_open_price` argument defaults to using the first price seen (cache.py line 50). This is correct behavior, but is implicit rather than explicit — there is no comment explaining the mechanism.

---

## 4. SSE Streaming

### Endpoint Behavior

- Endpoint: `GET /api/stream/prices` — correctly mounted under `/api/stream` prefix.
- Media type `text/event-stream` — correct.
- `Cache-Control: no-cache` and `X-Accel-Buffering: no` headers — appropriate.
- Sends `retry: 1000\n\n` on connect — tells browsers to reconnect after 1 second on drop.
- Version-based change detection: only emits an event when `cache.version != last_version`. Since version increments on every cache write and the SSE loop sleeps 500ms, in practice an event fires every cycle as long as the simulator is running. This is correct.

### Event Shape

The SSE payload is a single `data:` line with a JSON object keyed by ticker:

```
data: {"AAPL": {"ticker": "AAPL", "price": 190.50, ...}, "GOOGL": {...}}
```

This is a **bulk snapshot** of all tickers per event, not per-ticker individual events. The PLAN.md §6 describes "each SSE event contains: ticker, price, previous_price, session_open_price, timestamp, change_direction." This implies per-ticker events, but the bulk approach is fine — the frontend can iterate the top-level keys and process each ticker update.

The `to_dict()` output includes: `ticker`, `price`, `previous_price`, `session_open_price`, `timestamp`, `change`, `change_percent`, `change_direction`. The spec requires `ticker, price, previous_price, session_open_price, timestamp, change_direction` — all present. The extras (`change`, `change_percent`) are additive and useful to the frontend.

### Reconnection

Client disconnect is detected via `await request.is_disconnected()` polled once per loop. This is correct for FastAPI/Starlette. The `asyncio.CancelledError` is caught to allow clean teardown when the server shuts down. There is no heartbeat/keep-alive ping; some reverse proxies timeout idle SSE connections. This is a known limitation for proxied deployments.

### Issue SSE-1 (Minor): No keep-alive heartbeat.

The server never sends a comment ping (`: heartbeat`) to keep idle connections alive. Some nginx/load-balancer configurations have a 60–90 second timeout for connections with no data. In the simulator case this is fine — prices stream every 500ms. If all watched tickers were somehow static for 60 seconds (unlikely but possible with `MassiveDataSource` during market close), a proxied connection could time out. Not a problem for the default Docker deployment but worth noting.

### Issue SSE-2 (Design): Bulk payload grows linearly with watchlist size.

Each SSE event sends all tickers as one JSON blob. With 10 tickers at 500ms intervals this is ~2KB/s per client — negligible. But if a user adds 50+ tickers the payload size grows proportionally. A per-ticker event model would be more scalable. Not a bug, just an architectural note for future scaling.

---

## 5. Test Results

```
80 passed, 0 failed in 2.40s
```

The summary in `MARKET_DATA_SUMMARY.md` claimed 73 tests. The actual count is **80 tests** — 7 more than documented, likely added during a fix pass. All pass.

### Coverage by Module (market package only)

| Module | Stmts | Miss | Cover |
|---|---|---|---|
| `market/__init__.py` | 6 | 0 | 100% |
| `market/cache.py` | 46 | 0 | **100%** |
| `market/factory.py` | 15 | 0 | **100%** |
| `market/interface.py` | 13 | 0 | **100%** |
| `market/massive_client.py` | 69 | 4 | **94%** |
| `market/models.py` | 29 | 0 | **100%** |
| `market/seed_prices.py` | 8 | 0 | **100%** |
| `market/simulator.py` | 149 | 7 | **95%** |
| `market/stream.py` | 36 | 24 | **33%** |

Overall market package coverage: ~91% (excluding stream.py which is untested at the HTTP level).

The non-market app code (`api/`, `db/`, `main.py`) has 0% coverage — these modules have no tests. This is expected scope for the market data review, but represents a significant gap in the overall backend test suite.

---

## 6. Test Coverage Analysis

### What Is Tested

- **`test_models.py` (13 tests):** Full coverage of `PriceUpdate` — creation, change calculations, direction logic, `to_dict()` output, immutability, timestamp default.
- **`test_cache.py` (18 tests):** Full coverage — update, get, remove, version counter, session open price invariants, rounding, `__len__`, `__contains__`.
- **`test_simulator.py` (17 tests):** GBM math correctness, ticker add/remove, Cholesky rebuild, correlation lookup, default seed prices, price positivity stress test.
- **`test_simulator_source.py` (10 tests):** Async integration — start/stop lifecycle, cache population, update cadence, add/remove ticker, empty watchlist, error resilience.
- **`test_factory.py` (7 tests):** All four factory branches (no key, empty key, whitespace key, valid key), cache/key injection.
- **`test_massive.py` (15 tests):** Poll logic, malformed snapshot handling, API error resilience, timestamp conversion, ticker normalization, start/stop lifecycle.

### What Is Missing

**M1. `stream.py` has 33% coverage — the SSE generator is not tested.**
The `_generate_events` async generator (lines 62–87) is entirely untested. There are no tests for: correct `retry:` header emission, version-based change detection behavior, disconnect detection, correct JSON payload format. This is the highest-value gap.

**M2. No test for `SimulatorDataSource` snapshot callback.**
The `_snapshot_callback` mechanism (`simulator.py` lines 278–283) is untested. No test verifies that the callback fires every `SNAPSHOT_TICKS` ticks or that exceptions in the callback are swallowed and logged.

**M3. No test for `MassiveDataSource.start()` with non-empty initial tickers.**
`test_start_immediate_poll` tests the start path, but doesn't verify that the `_tickers` list is properly initialized from the argument (the `start()` method does `self._tickers = list(tickers)` on line 44, then polls — tests set `_tickers` manually rather than passing them to `start()`).

**M4. No test for simultaneous add/remove concurrency.**
`PriceCache` uses `threading.Lock` but there is no multi-threaded test exercising concurrent reads and writes.

**M5. No negative-price floor test.**
While GBM prices theoretically can never go negative (exponential function), no test confirms that the cache stores only positive prices after a large number of steps.

**M6. `massive_client.py` uncovered lines 86–88 (`_poll_loop` body) and line 127 (`_fetch_snapshots` full execution).**
The poll loop itself (`_poll_loop`) is never called in tests — only `_poll_once` is exercised directly. The test `test_stop_cancels_task` starts the source and then immediately stops it before the 10-second interval fires, so the loop body runs zero times.

---

## 7. Bugs & Issues

### Bug #1 (Low): `MassiveDataSource` does not explicitly pass `session_open_price` on first poll.

**File:** `backend/app/market/massive_client.py`, line 109
**Severity:** Low — functional behavior is correct, but it is implicit.

`_poll_once()` calls `self._cache.update(ticker=snap.ticker, price=price, timestamp=timestamp)` without a `session_open_price` argument. The `PriceCache.update()` method handles this correctly: on the first update for a ticker, if `session_open_price` is not provided, it defaults to `price` (cache.py line 50). So the session open is correctly set to the first observed price. However, `SimulatorDataSource` is explicit (`session_open_price=price`), and `MassiveDataSource` is implicit. This creates an inconsistency in the codebase that will confuse future maintainers.

**Fix:** Pass `session_open_price=price` on the first update, or add a comment in `_poll_once()` explaining the implicit mechanism.

### Bug #2 (Low): `_rebuild_cholesky` will crash on a near-singular correlation matrix.

**File:** `backend/app/market/simulator.py`, line 173
**Severity:** Low — will not occur with default tickers, but could occur with user-added tickers.

`np.linalg.cholesky(corr)` raises `numpy.linalg.LinAlgError: Matrix is not positive definite` if the correlation matrix is numerically singular. With the current correlation structure (all off-diagonal values ≥ 0.3), a 10-ticker matrix will be positive definite. But if a user adds ~10+ unknown tickers all with `CROSS_GROUP_CORR = 0.3`, the matrix can become ill-conditioned. The exception would propagate up through `add_ticker()` → `_rebuild_cholesky()`, crashing the caller (the watchlist `POST` handler). The `_run_loop`'s outer `except Exception` would not help here since the crash happens during `add_ticker`, not during `step()`.

**Fix:** Wrap `np.linalg.cholesky(corr)` in a try/except. On failure, fall back to `np.eye(n)` (uncorrelated) with a warning log.

### Bug #3 (Medium): `stream.py` module-level `router` object is shared state.

**File:** `backend/app/market/stream.py`, lines 17 and 20
**Severity:** Medium — works correctly in production, but causes test isolation issues and is architecturally incorrect.

The module-level `router = APIRouter(...)` object is created once at import time. `create_stream_router()` registers a route on it via `@router.get("/prices")`. If `create_stream_router()` is called a second time (e.g., in tests that create multiple app instances), it re-registers the same path on the same shared router, either raising an error or silently having duplicate routes. This is not a problem today because `create_stream_router()` is called exactly once in `main.py`, but it is an architectural trap.

**Fix:** Move `router = APIRouter(...)` inside `create_stream_router()` so each call returns a fresh router.

### Bug #4 (Low): `conftest.py` fixture `event_loop_policy` is not used by any test.

**File:** `backend/tests/conftest.py`, lines 6–11
**Severity:** Low — dead code, no functional impact.

The `event_loop_policy` fixture is defined but never referenced. `pytest-asyncio` with `asyncio_mode = "auto"` manages the event loop automatically and does not require a `event_loop_policy` fixture. It is likely a leftover from an earlier version of the test setup.

### Bug #5 (Design): `test_simulator.py` line 48 accesses private attribute `_tickers` directly.

**File:** `backend/tests/market/test_simulator.py`, line 48
**Severity:** Low — test correctness is fine, but tests that reach into private internals are fragile.

`assert len(sim._tickers) == 1` tests the internal state of `GBMSimulator` rather than observable behavior. A better assertion would use `sim.get_tickers()`, which is the public API. This couples the test to the implementation detail that tickers are stored in a `list[str]` attribute called `_tickers`.

---

## 8. Recommendations

Prioritized from most impactful to least:

### P1 — Fix the stream router factory (Bug #3)

Move `router = APIRouter(...)` inside `create_stream_router()`. This is a one-line fix that eliminates a latent test isolation bug and aligns with the factory pattern's intent.

```python
def create_stream_router(price_cache: PriceCache) -> APIRouter:
    router = APIRouter(prefix="/api/stream", tags=["streaming"])
    @router.get("/prices")
    ...
    return router
```

### P2 — Add tests for `stream.py`

`stream.py` is entirely untested (33% coverage, and the tested lines are only imports). Add tests using `httpx.AsyncClient` with a `TestClient` or `AsyncClient` from `starlette.testclient` to verify:
- The `retry:` directive is emitted on connect.
- Prices from the cache appear in the SSE payload.
- Disconnect detection terminates the generator.

### P3 — Protect `_rebuild_cholesky` from `LinAlgError` (Bug #2)

Add a try/except around `np.linalg.cholesky(corr)` in `simulator.py` with a fallback to the identity matrix. This prevents an obscure crash path when users add many tickers.

### P4 — Add `MassiveDataSource` snapshot support

When using the Massive API, portfolio snapshots currently only occur post-trade. The 30-second background snapshot interval specified in PLAN.md §7 is silently absent. Either pass a `snapshot_callback` to `MassiveDataSource` in `main.py` and wire it to the poll loop, or document clearly that the snapshot cadence is trade-driven only when using the Massive client.

### P5 — Fix the `CLAUDE.md` direction value documentation

`backend/CLAUDE.md` line 4 documents `direction` as `"up"/"down"/"flat"` but the actual value is `"unchanged"`. This will mislead frontend developers who read the dev guide.

### P6 — Fix `MARKET_DATA_SUMMARY.md` test count

The summary doc reports 73 tests; the actual count is 80. Update the count.

### P7 — Consolidate the duplicate `_iso_now()` helper

Move `_iso_now()` to a single shared location (e.g., `app/market/models.py` re-exported) and import it in `cache.py` rather than redefining it.

### P8 — Make the `version` property lock-safe (Issue QC-4)

For correctness under future free-threaded Python builds, acquire the lock in the `version` property before reading `_version`.

### P9 — Read `MARKET_POLL_INTERVAL_SECONDS` in the factory

Either implement `MARKET_POLL_INTERVAL_SECONDS` env-var support in `factory.py` (to match PLAN.md §5) or explicitly remove the variable from the spec and `.env.example`. The current silent ignore creates a configuration discrepancy.

### P10 — Replace private-attribute test assertions with public API

In `test_simulator.py` line 48, replace `len(sim._tickers) == 1` with `len(sim.get_tickers()) == 1` to reduce test coupling to internals.

---

## Summary

The market data backend is well-constructed and production-ready for its scope. The core design — strategy pattern over an ABC, PriceCache as single point of truth, GBM with Cholesky-correlated moves, SSE streaming — is sound and correctly implemented. All 80 tests pass. The market package itself achieves ~91% line coverage.

The three issues that warrant attention before downstream development depends on this code are:

1. **The stream router factory bug (Bug #3)** — a shared module-level router will cause problems in tests or multi-instance scenarios.
2. **The missing `_rebuild_cholesky` error guard (Bug #2)** — reachable via the watchlist API.
3. **The missing SSE tests (M1)** — the most user-visible component is the least tested.

Everything else is minor polish or documentation accuracy.
