---
phase: 4
slug: frontend-shell-live-data
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-09
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Build verification (`next build` with static export) + TypeScript compiler (`tsc --noEmit`) |
| **Config file** | frontend/next.config.ts (output: 'export') |
| **Quick run command** | `cd frontend && npm run build` |
| **Full suite command** | `cd frontend && npx tsc --noEmit && npm run build` |
| **Estimated runtime** | ~20 seconds |

**Note:** Jest + React Testing Library unit tests are deferred to Phase 6 (TEST-05: frontend component tests). Phase 4 is a greenfield UI build where the primary correctness signal is "it builds and renders." Build checks catch type errors, import failures, and static export incompatibilities. Visual correctness is verified by the human checkpoint in Plan 03.

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm run build`
- **After every plan wave:** Run `cd frontend && npx tsc --noEmit && npm run build`
- **Before `/gsd-verify-work`:** Build must succeed + human checkpoint approved
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|--------|
| 04-01-01 | 01 | 1 | UI-LAYOUT-01 | — | N/A | build | `npm run build` | ⬜ pending |
| 04-01-02 | 01 | 1 | UI-LAYOUT-02 | — | N/A | build | `npm run build` | ⬜ pending |
| 04-01-03 | 01 | 1 | UI-LAYOUT-03 | — | N/A | build | `npm run build` | ⬜ pending |
| 04-01-04 | 01 | 1 | UI-LAYOUT-04 | — | N/A | build | `npm run build` | ⬜ pending |
| 04-02-01 | 02 | 2 | UI-WATCH-01 | T-04-01 | JSX auto-escape | build+types | `npx tsc --noEmit && npm run build` | ⬜ pending |
| 04-02-02 | 02 | 2 | UI-WATCH-02 | — | N/A | build+types | `npx tsc --noEmit && npm run build` | ⬜ pending |
| 04-02-03 | 02 | 2 | UI-WATCH-03 | T-04-03 | MAX_SPARKLINE_POINTS=120 | build+types | `npx tsc --noEmit && npm run build` | ⬜ pending |
| 04-02-04 | 02 | 2 | UI-WATCH-04 | — | N/A | build+types | `npx tsc --noEmit && npm run build` | ⬜ pending |
| 04-03-01 | 03 | 3 | UI-CHART-01 | T-04-05 | Chart data capped at 120 pts | build+types | `npx tsc --noEmit && npm run build` | ⬜ pending |
| 04-03-02 | 03 | 3 | ALL | — | N/A | visual | human checkpoint | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. The `next build` command with `output: 'export'` validates:
- All TypeScript compiles without errors
- All imports resolve correctly
- No server-only APIs used in client components
- Static export produces valid HTML output

No additional test framework setup is needed for this phase.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Price flash green/red animation | UI-WATCH-02 | CSS animation timing requires visual confirmation | 1. Open app 2. Observe price changes 3. Verify green flash on uptick, red on downtick, ~500ms fade |
| Sparkline progressive fill | UI-WATCH-03 | Canvas rendering requires visual confirmation | 1. Open app 2. Watch sparklines fill in over 30s 3. Verify progressive accumulation |
| Dark terminal aesthetic | UI-LAYOUT-01 | Subjective visual quality | 1. Open app 2. Verify dark backgrounds, muted borders, accent colors match spec |
| Chart real-time updates | UI-CHART-01 | Dynamic rendering requires visual confirmation | 1. Open app 2. Verify chart updates as SSE data arrives 3. Click different ticker, chart switches |

*These are covered by the human checkpoint in Plan 04-03, Task 2.*

---

## Unit Test Deferral

Frontend component unit tests (Jest + React Testing Library) are explicitly deferred to **Phase 6** which owns requirement **TEST-05** (frontend component tests). Rationale:

1. Phase 4 is greenfield scaffolding -- components are being created for the first time and their interfaces may shift across tasks
2. Build verification (`next build`) catches the highest-value errors for a new frontend: type errors, broken imports, SSR/static-export incompatibilities
3. Adding Jest setup, mocks for EventSource, mocks for canvas, and mocks for Lightweight Charts would consume significant context budget (~30% of a plan) with lower marginal value than the build+visual strategy
4. Phase 6 can test against stable component interfaces after the full UI is assembled

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify (build commands)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (N/A -- no Wave 0 gaps)
- [x] No watch-mode flags
- [x] Feedback latency < 20s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (build-only automation strategy)
