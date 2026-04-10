---
phase: 6
slug: infrastructure-testing
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-09
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Backend Framework** | pytest 8.3+ with pytest-asyncio (auto mode) |
| **Backend Config** | `backend/pyproject.toml` [tool.pytest.ini_options] |
| **Backend Quick Run** | `cd backend && uv run --extra dev pytest -x -q` |
| **Backend Full Suite** | `cd backend && uv run --extra dev pytest -v --cov=app` |
| **Frontend Framework** | Vitest (to be installed in Wave 1) |
| **Frontend Quick Run** | `cd frontend && npx vitest run --reporter=verbose` |
| **E2E Framework** | Playwright (to be installed in Wave 2) |
| **E2E Run** | `cd test && npx playwright test --reporter=list` |

---

## Sampling Rate

- **After every task commit:** Run backend quick command
- **After every plan wave:** Run full suite command for affected layer
- **Before `/gsd-verify-work`:** All suites must be green
- **Max feedback latency:** ~30 seconds (backend), ~15 seconds (frontend), ~120 seconds (E2E)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | INFRA-01, INFRA-02, INFRA-03 | smoke | `docker build -t finally .` | N/A | ⬜ pending |
| 06-01-02 | 01 | 1 | INFRA-04 | smoke | `bash scripts/start_mac.sh && bash scripts/start_mac.sh` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 1 | TEST-01, TEST-02, TEST-03, TEST-04 | unit | `cd backend && uv run --extra dev pytest -v --tb=short` | ✅ | ⬜ pending |
| 06-02-02 | 02 | 1 | TEST-05 | unit | `cd frontend && npx vitest run` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 2 | TEST-06 | config | `cd test && npm install` | ❌ W0 | ⬜ pending |
| 06-03-02 | 03 | 2 | TEST-06 | E2E | `cd test && npx playwright test --reporter=list` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/vitest.config.ts` — Vitest configuration
- [ ] `frontend/src/test/setup.ts` — test setup with jsdom
- [ ] `test/playwright.config.ts` — Playwright configuration
- [ ] `test/docker-compose.test.yml` — E2E test infrastructure

*Existing backend test infrastructure covers TEST-01 through TEST-04.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SQLite persists across container restart | INFRA-03 | Volume persistence requires start/stop/start cycle | Run start, trade, stop, start, verify position exists |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-09
