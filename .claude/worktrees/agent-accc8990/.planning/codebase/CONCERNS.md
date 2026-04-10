# Codebase Concerns

**Analysis Date:** 2026-04-09

## Tech Debt

**LLM Response Parsing — Overly Broad Exception Handling**
- Issue: `POST /api/chat` catches all exceptions on LLM call failure and returns a fallback response without distinguishing error types
- Files: `backend/app/api/chat.py` (lines 186-201)
- Impact: Unhandled errors (network, malformed response, invalid JSON from LLM) are logged but not distinguished. If the LLM returns invalid JSON and `model_validate_json()` fails, the user gets a generic "trouble connecting" message, which may obscure API key issues, rate limits, or actual model problems
- Fix approach: Separate exception handling for `litellm` exceptions, JSON parsing errors, and network errors. Log specific error types. Consider retrying on transient failures (429 rate limit, network timeouts)

**Chat History Deserialization — Missing Error Handling**
- Issue: `get_chat_history()` deserializes the `actions` JSON column without try/catch
- Files: `backend/app/db/queries.py` (line 267)
- Impact: If the stored JSON is malformed (database corruption, or a bug during storage), loading chat history will crash the endpoint
- Fix approach: Wrap `json.loads()` in try/except; log and skip malformed actions, or replace with `{}`

**Health Check Does Not Verify Database**
- Issue: `GET /api/health` always returns `{"status": "ok"}` without checking database connectivity or state
- Files: `backend/app/api/health.py`
- Impact: Docker HEALTHCHECK instruction cannot distinguish between a running app and one with database problems. A volume mount failure or database corruption would not be detected
- Fix approach: Query the database on health check (e.g., `SELECT 1 FROM users_profile LIMIT 1`). Return error if the check fails

**Massive API Client — Overly Broad Exception Logging**
- Issue: `_poll_once()` catches all exceptions and logs at ERROR level without distinguishing between transient errors (network, rate limit) and permanent failures (bad API key, malformed response)
- Files: `backend/app/market/massive_client.py` (lines 131-134)
- Impact: Rate limit errors (429) and network timeouts are treated the same as authentication errors (401). No exponential backoff or retry logic. Rapid polling failures may spam logs
- Fix approach: Differentiate HTTP status codes. For 429, back off or skip poll. For 401, log once and disable polling. For network errors, retry with exponential backoff

**Correlation Matrix Fallback — Silent Degradation**
- Issue: When the correlation matrix is not positive definite (can happen with many unknown tickers), the simulator falls back to uncorrelated moves and logs a warning
- Files: `backend/app/market/simulator.py` (lines 173-184)
- Impact: Silent change in simulator behavior may confuse testing and make results non-reproducible. Tests or users adding arbitrary tickers could trigger this degradation without obvious indication
- Fix approach: Make correlation handling more robust; consider limiting unknown tickers or configuring a minimum correlation. Document the fallback behavior clearly

**Trade Execution — Missing Decimal Precision Handling**
- Issue: Fractional share quantities are stored as REAL in SQLite and computed using floating-point arithmetic (e.g., avg_cost calculation in `execute_trade()`)
- Files: `backend/app/db/queries.py` (line 143)
- Impact: Floating-point rounding errors accumulate over multiple trades. Average cost calculations may drift slightly; cumulative P&L may be inaccurate by pennies after many fractional trades
- Fix approach: Use Python `Decimal` type for all monetary calculations (price, quantity for P&L; store as TEXT in SQLite if needed). Or enforce whole-share quantities only in the trade bar validation (though LLM can still use fractions)

**Portfolio Snapshot Pruning — No Safeguard Against Data Loss**
- Issue: `record_portfolio_snapshot()` automatically deletes snapshots older than 24 hours
- Files: `backend/app/db/queries.py` (line 229-231)
- Impact: Long-term P&L data (>24h) is lost. Users cannot view historical portfolio value beyond one day. If used in production with real money, this would be unacceptable
- Fix approach: Increase retention (e.g., 30 days for detail, archive older data), or make retention configurable. Add a warning in schema/docs about the 24-hour limit

**SSE Streaming — No Connection Limits**
- Issue: The `/api/stream/prices` endpoint has no rate limiting, max connection count, or payload size validation
- Files: `backend/app/market/stream.py`
- Impact: A client can open unlimited concurrent SSE connections, consuming memory and event loop resources. No protection against DoS
- Fix approach: Add connection limits (middleware or endpoint-level), enforce max clients per IP, or add a simple rate limit

## Security Considerations

**API Endpoints — No Input Validation for Ticker Symbols**
- Risk: Ticker fields are normalized to uppercase but not validated against a whitelist or pattern. Arbitrary strings are accepted as tickers
- Files: `backend/app/api/watchlist.py` (line 51), `backend/app/api/portfolio.py` (line 78), `backend/app/api/chat.py` (lines 207-208)
- Current mitigation: Simulator accepts any string; Massive API client will silently fail to fetch unknown tickers (no error returned to user)
- Recommendations: Validate ticker format (uppercase ASCII letters + digits, length 1-5). Maintain a whitelist of known tickers or use a ticker validation service. Return 422 for invalid tickers

**LLM Chat — Trade Auto-Execution Without Confirmation**
- Risk: The LLM can specify trades that execute immediately without user confirmation, even if structured output parsing fails partially
- Files: `backend/app/api/chat.py` (lines 203-232)
- Current mitigation: Limited by simulated environment (fake money); user can review chat history of executed trades
- Recommendations: Even though fake money, consider requiring explicit user confirmation for LLM-suggested trades. Add a "preview" response mode where trades are shown but not executed until approved

**Environment Variables — API Key Exposure**
- Risk: `.env` file contains `OPENROUTER_API_KEY` and `MASSIVE_API_KEY`. If accidentally committed or leaked in logs, exposes paid API accounts
- Files: `.env` (not committed but listed in git status)
- Current mitigation: `.env` is gitignored
- Recommendations: Ensure `.env` is never printed in logs. Add a check in CI to prevent accidental commits. Use a `.env.example` template with placeholder values for setup instructions

**No Authentication or Multi-User Isolation**
- Risk: All users operate on the same "default" user account. No session tokens, JWT, or API keys required
- Files: All `backend/app/api/*` endpoints, `backend/app/db/queries.py`
- Current mitigation: This is a single-user simulation app; no real user data at risk
- Recommendations: In any production path, add auth before multi-user support. Schema is already designed for multi-user (user_id column); implementation is deferred

## Known Incomplete Implementations

**Dockerfile & Deployment Scripts Missing**
- Problem: The plan (PLAN.md) specifies a Dockerfile with a multi-stage build and start scripts (`scripts/start_mac.sh`, `start_windows.ps1`, etc.), but they do not exist in the repo
- Files: Missing — `Dockerfile`, `docker-compose.yml`, `scripts/start_mac.sh`, `scripts/stop_mac.sh`, `scripts/start_windows.ps1`, `scripts/stop_windows.ps1`
- Impact: Users cannot run the app without manually building and deploying. The "single Docker command" user experience promised in the spec cannot be achieved
- Fix approach: Implement the Dockerfile (multi-stage build, Node.js → Python). Create start/stop shell scripts for macOS/Linux. Optionally provide PowerShell scripts for Windows

**Frontend Implementation — Completely Empty**
- Problem: `frontend/` directory contains no code. The plan requires a Next.js app with watchlist, charts, portfolio heatmap, P&L line chart, trade bar, and AI chat panel
- Files: `frontend/` (empty directory only)
- Impact: Users see a 404 when navigating to the app. No UI exists for any feature
- Fix approach: Scaffold Next.js TypeScript project. Implement all components specified in PLAN.md §10

**E2E Tests — Not Implemented**
- Problem: The plan specifies Playwright E2E tests in `test/` using `docker-compose.test.yml` with scenarios (add/remove ticker, buy/sell, portfolio visualization, chat with mocked LLM)
- Files: `test/` exists but contains only `node_modules/`; no test files present
- Impact: No automated verification of critical user flows (e.g., can users buy stocks, does SSE price streaming work, do AI trades execute)
- Fix approach: Create test suite with Playwright covering all scenarios in PLAN.md §12

**Deployment Artifacts — No Cloud Support**
- Problem: The plan mentions "optional cloud deployment" to AWS App Runner or Render with Terraform, but nothing is implemented
- Files: No `deploy/` directory; no Terraform configs
- Impact: Cannot deploy to cloud; only local Docker is possible
- Fix approach: This is optional/stretch goal; defer unless prioritized

## Fragile Areas

**Correlation Matrix in Simulator — Numerical Stability Risk**
- Files: `backend/app/market/simulator.py` (lines 155-184)
- Why fragile: When many unknown tickers are added with default `CROSS_GROUP_CORR = 0.3`, the correlation matrix may not be positive definite, triggering fallback to uncorrelated mode. Users adding arbitrary tickers could unknowingly change market behavior
- Safe modification: Do not add tickers dynamically without testing correlation matrix stability. Consider enforcing a ticker whitelist or using a more robust correlation construction
- Test coverage: `tests/market/test_simulator.py` exists but should verify that adding diverse tickers maintains positive definiteness

**Database Write Contention During High-Frequency Updates**
- Files: `backend/app/db/queries.py` (trade execution, snapshot recording), `backend/app/main.py` (snapshot callback)
- Why fragile: Both the simulator loop (~60 ticks/min, calling `_snapshot_callback()` every 60 ticks = ~30s) and manual trades trigger `record_portfolio_snapshot()`. All calls use `get_db()` which opens individual connections to SQLite. SQLite is single-writer; concurrent writes will serialize with potential lock contention if too many async tasks await DB operations
- Safe modification: Monitor for slow snapshot writes under load. If issues arise, batch snapshots or use a queue. Current design is safe for demo; becomes a problem under stress testing
- Test coverage: No stress tests for concurrent trade execution + snapshot recording

**Chat Message Actions Storage — JSON Schema Mismatch**
- Files: `backend/app/api/chat.py` (lines 265-271), `backend/app/db/queries.py` (line 267)
- Why fragile: The `actions` field stores a JSON blob with `{trades, watchlist_changes, errors}` structure. If the structure changes (new fields added, nesting changed), old messages in the database become incompatible. No schema versioning or migration
- Safe modification: Always make JSON schema changes backward-compatible. Document the schema. Consider adding a `schema_version` field if major changes occur
- Test coverage: Unit tests should verify round-trip of actions JSON for all variants

**SSE Stream Generation — No Backpressure Handling**
- Files: `backend/app/market/stream.py`
- Why fragile: The stream generator pushes events at fixed intervals (~500ms) without checking if the client is still listening or if buffering is overflowing. If a client is slow to consume, events may accumulate in memory
- Safe modification: Use FastAPI's StreamingResponse with proper exception handling for client disconnects. Add logging of dropped clients
- Test coverage: No tests for SSE client disconnect handling

## Performance Bottlenecks

**Correlation Matrix Rebuild — O(n²) on Ticker Change**
- Problem: Every time a ticker is added/removed, `_rebuild_cholesky()` recomputes the entire correlation matrix and Cholesky decomposition, which is O(n²) for n tickers
- Files: `backend/app/market/simulator.py` (lines 155-184, called from `add_ticker()` and `remove_ticker()`)
- Current capacity: O(n²) is acceptable up to ~100 tickers; for the demo (10-20 tickers), no issue
- Scaling path: If supporting thousands of dynamic tickers, consider incremental updates to the correlation matrix or precomputed correlation sets

**Price Cache Iteration — O(n) on Every SSE Event**
- Problem: `PriceCache.get_all()` returns a shallow copy of the entire prices dict, called by SSE streaming to serialize all prices for SSE events
- Files: `backend/app/market/cache.py` (line 64), `backend/app/market/stream.py` (used to generate events)
- Current capacity: O(n) where n = number of tickers (~10-20); acceptable
- Scaling path: For large watchlists, consider sending only delta updates (changed prices) instead of all prices every 500ms

**Portfolio Calculation on Every API Call**
- Problem: `GET /api/portfolio` iterates through all positions and looks up current prices, computing P&L on each request
- Files: `backend/app/api/portfolio.py` (lines 42-54)
- Current capacity: <1ms for 10 positions; acceptable
- Scaling path: Cache total portfolio value and invalidate on trade/price update; compute P&L incrementally

## Scaling Limits

**SQLite Single-Writer Limit**
- Current capacity: Works for single-user demo with ~100 trades/day
- Limit: SQLite's write lock becomes a bottleneck at >10 concurrent writes/second (e.g., high-frequency trading bot)
- Scaling path: Switch to PostgreSQL or MySQL for multi-user production; no schema changes needed (all columns already in place)

**In-Memory Price Cache**
- Current capacity: ~10-20 tickers with full price history (PriceUpdate objects)
- Limit: No memory bound; adding 10,000 tickers would consume ~10MB per PriceUpdate object (small but unbounded)
- Scaling path: Implement an LRU cache with max size, or use a time-series database for historical prices

**SSE Client Connections**
- Current capacity: ~100 concurrent EventSource connections before event loop becomes saturated
- Limit: No connection pool limits; could exhaust memory if thousands of clients connect
- Scaling path: Add explicit max client limits, implement per-IP rate limiting, or scale to multiple app instances behind a load balancer

## Missing Critical Features

**No Limit Orders**
- What's missing: Only market orders are supported; users cannot set buy/sell at a specific price
- Blocks: Cannot implement stop-loss strategies, wait for pullbacks, or other risk management
- Note: This is intentional simplification per PLAN.md; acceptable for demo

**No Portfolio Risk Metrics**
- What's missing: No Value at Risk (VaR), Sharpe ratio, correlation with market index, or other quantitative risk measures
- Blocks: Advanced users cannot assess portfolio risk
- Note: Stretch goal; not required for MVP

**No Trade Alerts or Notifications**
- What's missing: No email/SMS alerts when price hits a level, trade executes, or portfolio P&L crosses a threshold
- Blocks: Users must constantly watch the app to catch opportunities
- Note: Not in spec; defer

## Test Coverage Gaps

**Untested Area: LLM Mock Mode Behavior**
- What's not tested: When `LLM_MOCK=true`, the endpoint returns deterministic mock responses. No test verifies that mock responses have correct structure or that auto-execution works with mocked trades
- Files: `backend/app/api/chat.py` (lines 179-184)
- Risk: Mock mode could diverge from real LLM behavior; E2E tests may pass but real LLM calls fail
- Priority: High (blocks E2E test suite)

**Untested Area: Massive API Polling and Error Recovery**
- What's not tested: The Massive poller's retry logic, error handling for 401/429 status codes, and behavior when watchlist tickers are added/removed during polling
- Files: `backend/app/market/massive_client.py` (lines 87-141)
- Risk: Polling failures, rate limits, or API key rotations are not covered; unknown behavior in production
- Priority: High (if Massive API is used in production)

**Untested Area: SSE Client Disconnect and Reconnection**
- What's not tested: EventSource automatic reconnection, partial message loss during network disruption, or behavior when SSE stream is interrupted
- Files: `backend/app/market/stream.py`
- Risk: Frontend may experience stale prices if SSE drops silently; user doesn't know prices are outdated
- Priority: Medium (important for UX but mitigated by fallback pricing in portfolio endpoint)

**Untested Area: Concurrent Trade Execution**
- What's not tested: Two trades executing simultaneously on the same ticker (e.g., buy while sell is pending), or database race conditions on cash_balance updates
- Files: `backend/app/db/queries.py` (execute_trade function)
- Risk: In a multi-user system (future), could result in cash balance or position inconsistencies
- Priority: Medium (not urgent for single-user demo; high for production migration)

**Untested Area: Portfolio Snapshot Pruning Edge Cases**
- What's not tested: Behavior when 24-hour window shrinks snapshots to zero (fresh start), or when record_portfolio_snapshot fails but prune succeeds (data loss)
- Files: `backend/app/db/queries.py` (lines 218-233)
- Risk: Incomplete snapshots, empty P&L history, or unhandled failure during pruning
- Priority: Low (demo scenario unlikely to trigger, but edge case exists)

---

*Concerns audit: 2026-04-09*
