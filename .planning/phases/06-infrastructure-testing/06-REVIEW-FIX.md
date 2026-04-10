---
phase: 06-infrastructure-testing
fixed_at: 2026-04-09T12:15:00Z
review_path: .planning/phases/06-infrastructure-testing/06-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 06: Code Review Fix Report

**Fixed at:** 2026-04-09T12:15:00Z
**Source review:** .planning/phases/06-infrastructure-testing/06-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5
- Fixed: 5
- Skipped: 0

## Fixed Issues

### CR-01: Docker Compose healthcheck uses `curl` which is not installed in the image

**Files modified:** `test/docker-compose.test.yml`
**Commit:** 564b92c
**Applied fix:** Replaced `curl -f` healthcheck command with `python -c "import urllib.request; urllib.request.urlopen(...)"` which is available in the python:3.12-slim base image without installing additional packages.

### WR-01: Shell script uses unquoted variable for `$ENV_FLAG` allowing word splitting

**Files modified:** `scripts/start_mac.sh`
**Commit:** 3eb3b48
**Applied fix:** Replaced the string-based `ENV_FLAG` variable with a bash array `DOCKER_ARGS=()` and proper array expansion `"${DOCKER_ARGS[@]}"`. This handles the empty case correctly without relying on word splitting, and is safe if paths contain spaces.

### WR-02: E2E watchlist removal test uses `not.toBeVisible` which may produce false negatives

**Files modified:** `frontend/src/components/WatchlistPanel.tsx`, `test/e2e/watchlist.spec.ts`
**Commit:** 7fb8c2c
**Applied fix:** Added `data-testid="watchlist"` to the WatchlistPanel root div. Updated the E2E test to scope the NFLX removal assertion to `page.locator('[data-testid="watchlist"]')` so it only checks within the watchlist panel, avoiding false matches from chart labels or other page content.

### WR-03: E2E trading tests depend on shared database state across tests

**Files modified:** `test/e2e/trading.spec.ts`
**Commit:** 5c8adc0
**Applied fix:** Replaced the absolute assertion `expect(initialData.cash_balance).toBe(10000)` with a relative pattern: capture `initialCash` from the portfolio endpoint, then assert `expect(updatedData.cash_balance).toBeLessThan(initialCash)`. This makes the test resilient to prior tests having modified the database state.

### WR-04: Backend health test uses module-level side effects for DB_PATH override

**Files modified:** `backend/tests/test_health.py`
**Commit:** 22710f1
**Applied fix:** Added an explicit patch of `app.db.connection.DB_PATH` inside `_ensure_init()` as a safety net against import-order issues. If another test module imports `app.main` before this file's env var override takes effect, the module-level `DB_PATH` will still be corrected before `init_db()` runs. The env-var-before-import pattern is retained as the primary mechanism.

## Skipped Issues

None -- all in-scope findings were fixed.

---

_Fixed: 2026-04-09T12:15:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
