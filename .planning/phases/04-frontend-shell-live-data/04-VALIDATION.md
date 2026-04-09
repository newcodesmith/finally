---
phase: 4
slug: frontend-shell-live-data
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | jest 29.x / React Testing Library |
| **Config file** | frontend/jest.config.ts (Wave 0 installs) |
| **Quick run command** | `cd frontend && npx jest --bail` |
| **Full suite command** | `cd frontend && npx jest --coverage` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx jest --bail`
- **After every plan wave:** Run `cd frontend && npx jest --coverage`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | UI-LAYOUT-01 | — | N/A | unit | `npx jest --testPathPattern layout` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | UI-LAYOUT-02 | — | N/A | unit | `npx jest --testPathPattern header` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | UI-LAYOUT-03 | — | N/A | unit | `npx jest --testPathPattern theme` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | UI-LAYOUT-04 | — | N/A | unit | `npx jest --testPathPattern status` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 1 | UI-WATCH-01 | — | N/A | unit | `npx jest --testPathPattern watchlist` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 1 | UI-WATCH-02 | — | N/A | unit | `npx jest --testPathPattern price` | ❌ W0 | ⬜ pending |
| 04-02-03 | 02 | 1 | UI-WATCH-03 | — | N/A | unit | `npx jest --testPathPattern sparkline` | ❌ W0 | ⬜ pending |
| 04-02-04 | 02 | 1 | UI-WATCH-04 | — | N/A | unit | `npx jest --testPathPattern flash` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 2 | UI-CHART-01 | — | N/A | unit | `npx jest --testPathPattern chart` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/jest.config.ts` — Jest configuration for Next.js with TypeScript
- [ ] `frontend/src/__tests__/` — test directory structure
- [ ] Jest + React Testing Library + jest-dom — install via npm

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Price flash green/red animation | UI-WATCH-04 | CSS animation timing requires visual confirmation | 1. Open app 2. Observe price changes 3. Verify green flash on uptick, red on downtick, ~500ms fade |
| Sparkline progressive fill | UI-WATCH-03 | Canvas rendering requires visual confirmation | 1. Open app 2. Watch sparklines fill in over 30s 3. Verify progressive accumulation |
| Dark terminal aesthetic | UI-LAYOUT-01 | Subjective visual quality | 1. Open app 2. Verify dark backgrounds, muted borders, accent colors match spec |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
