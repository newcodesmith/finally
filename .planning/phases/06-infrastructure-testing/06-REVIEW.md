---
phase: 06-infrastructure-testing
reviewed: 2026-04-09T12:00:00Z
depth: standard
files_reviewed: 19
files_reviewed_list:
  - Dockerfile
  - .dockerignore
  - scripts/start_mac.sh
  - scripts/stop_mac.sh
  - backend/tests/test_health.py
  - frontend/vitest.config.ts
  - frontend/src/test/setup.ts
  - frontend/src/components/PriceCell.test.tsx
  - frontend/src/components/TradeBar.test.tsx
  - frontend/src/components/Header.test.tsx
  - frontend/src/components/ChatMessage.test.tsx
  - frontend/package.json
  - test/docker-compose.test.yml
  - test/playwright.config.ts
  - test/package.json
  - test/tsconfig.json
  - test/e2e/smoke.spec.ts
  - test/e2e/watchlist.spec.ts
  - test/e2e/trading.spec.ts
  - test/e2e/chat.spec.ts
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-04-09T12:00:00Z
**Depth:** standard
**Files Reviewed:** 19
**Status:** issues_found

## Summary

This review covers the Docker infrastructure (Dockerfile, .dockerignore, start/stop scripts), backend health check test, frontend unit tests (vitest), and E2E test suite (Playwright). The overall quality is solid with good test coverage patterns and appropriate use of mocks. The critical finding is a healthcheck that will always fail in the Docker Compose test environment because `curl` is not installed in the slim Python image. Several warnings address test reliability concerns and a security consideration in the start script.

## Critical Issues

### CR-01: Docker Compose healthcheck uses `curl` which is not installed in the image

**File:** `test/docker-compose.test.yml:14`
**Issue:** The healthcheck command is `["CMD", "curl", "-f", "http://localhost:8000/api/health"]`, but the Dockerfile uses `python:3.12-slim` as the runtime base image and never installs `curl`. The `python:3.12-slim` image does not include `curl`. This means the healthcheck will always fail, the container will never report as healthy, and any `docker compose up --wait` or `depends_on` with `condition: service_healthy` will hang or time out.
**Fix:** Use Python's built-in `urllib` for the healthcheck instead of `curl`:
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]
  interval: 5s
  timeout: 3s
  retries: 30
  start_period: 30s
```

## Warnings

### WR-01: Shell script uses unquoted variable for `$ENV_FLAG` allowing word splitting

**File:** `scripts/start_mac.sh:29`
**Issue:** The variable `$ENV_FLAG` on line 29 is intentionally unquoted to allow it to expand to nothing when `.env` is absent. However, this relies on word splitting behavior, which means if the `.env` file path were ever to contain spaces, the command would break. More importantly, if `IFS` is modified upstream, this pattern fails silently. The current code works for the default case but is fragile.
**Fix:** Use an array to conditionally build the docker run arguments:
```bash
DOCKER_ARGS=()
if [[ -f .env ]]; then
    DOCKER_ARGS+=(--env-file .env)
fi

docker run -d \
    --name "$CONTAINER_NAME" \
    -v "$VOLUME_NAME:/app/db" \
    -p "$PORT:8000" \
    "${DOCKER_ARGS[@]}" \
    "$IMAGE_NAME"
```

### WR-02: E2E watchlist removal test uses `not.toBeVisible` which may produce false negatives

**File:** `test/e2e/watchlist.spec.ts:33`
**Issue:** The assertion `await expect(page.getByText('NFLX')).not.toBeVisible({ timeout: 5000 })` will pass if the text "NFLX" appears anywhere on the page but is hidden (e.g., in a hidden DOM element). More critically, `getByText('NFLX')` matches any element containing "NFLX" -- if there's a chart label or other reference, this test will fail for the wrong reason. Using a more scoped locator would improve reliability.
**Fix:** Scope the assertion to the watchlist panel specifically:
```typescript
const watchlistPanel = page.locator('[data-testid="watchlist"]'); // or appropriate selector
await expect(watchlistPanel.getByText('NFLX')).not.toBeVisible({ timeout: 5000 });
```

### WR-03: E2E trading tests depend on shared database state across tests

**File:** `test/e2e/trading.spec.ts:52-73`
**Issue:** The third test (`portfolio endpoint returns updated data after trade`) asserts `initialData.cash_balance === 10000` on line 59. However, E2E tests in this file run sequentially (Playwright `workers: 1`), and the previous two tests execute buy/sell trades that modify the database. If tests share the same database (which they do via the Docker volume in `docker-compose.test.yml`), the initial cash balance will not be $10,000 by the time this test runs. This test will fail unless the database is reset between tests.
**Fix:** Either reset the database state before each test (e.g., via an API endpoint like `/api/test/reset`), or change the assertion to be relative rather than absolute:
```typescript
// Instead of:
expect(initialData.cash_balance).toBe(10000);
// Use:
const initialCash = initialData.cash_balance;
// ... execute trade ...
expect(updatedData.cash_balance).toBeLessThan(initialCash);
```

### WR-04: Backend health test uses module-level side effects for DB_PATH override

**File:** `backend/tests/test_health.py:11-14`
**Issue:** Lines 11-12 set `os.environ["DB_PATH"]` at module import time, then lines 14-15 import `init_db` and `app` after the env var is set. This works but is fragile: if pytest imports this module after another test module that already imported `app.main`, the env var override may not take effect because the app module is already cached in `sys.modules`. This pattern couples test correctness to import order.
**Fix:** Use a pytest fixture with `monkeypatch` to set the env var, or use a `conftest.py` that sets up a test database path consistently across all test modules. At minimum, document that this file must not be co-imported with other test modules that import `app.main`.

## Info

### IN-01: Hardcoded `waitForTimeout` in E2E trading test

**File:** `test/e2e/trading.spec.ts:45`
**Issue:** `await page.waitForTimeout(1000)` is a fixed sleep used to wait for the trade feedback to clear before filling the form again. Playwright discourages `waitForTimeout` because it adds unnecessary slowness and can still be flaky under load.
**Fix:** Wait for the feedback text to disappear instead:
```typescript
await expect(page.getByText(/Bought 10 AAPL/)).not.toBeVisible({ timeout: 5000 });
```

### IN-02: Frontend test setup file is minimal

**File:** `frontend/src/test/setup.ts:1`
**Issue:** The setup file only imports `@testing-library/jest-dom/vitest`. There is no global cleanup (e.g., `afterEach(() => cleanup())`) configured. While React Testing Library's auto-cleanup works when `globals: true` is set in vitest config (which it is), this is worth noting as an implicit dependency on vitest's global injection behavior.
**Fix:** No action required -- the current config is correct. This is informational only.

### IN-03: `.dockerignore` excludes `backend/tests` but not `frontend/src/test` or `test/`

**File:** `.dockerignore:7-14`
**Issue:** The `.dockerignore` excludes `backend/tests` (line 7) and `test` (line 14, the E2E directory), which is correct. The frontend test files under `frontend/src/test/` and `frontend/src/components/*.test.tsx` are copied into the build stage but are excluded from the final image because only `frontend/out` (the static export) is copied to stage 2. This is fine -- no test code reaches the production image. Noting for completeness that the frontend build stage does include test files, which marginally increases build context size.
**Fix:** Optionally add `frontend/src/test` and `frontend/src/components/*.test.*` to `.dockerignore` to reduce build context, but this is low priority since they do not affect the final image.

---

_Reviewed: 2026-04-09T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
