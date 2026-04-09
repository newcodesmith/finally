---
phase: 04-frontend-shell-live-data
plan: 02
subsystem: ui
tags: [zustand, sse, eventsource, canvas, sparkline, react, tailwind]

requires:
  - phase: 04-frontend-shell-live-data/01
    provides: "App shell layout, Tailwind theme tokens, TypeScript types, format utilities, CSS flash classes"
provides:
  - "Zustand price store with prices, sparkline history, connection status, selected ticker"
  - "SSE connection hook (useSSE) for live price streaming"
  - "Portfolio polling hook (usePortfolio) for header data"
  - "Complete watchlist panel with PriceCell flash animations, ChangePercent, and Sparkline components"
  - "WatchlistRow with per-ticker Zustand selectors for efficient re-rendering"
affects: [04-frontend-shell-live-data/03, portfolio-ui, chart-area, trade-bar, chat-panel]

tech-stack:
  added: []
  patterns: [zustand-selector-per-row, eventsource-getstate-pattern, canvas-sparkline]

key-files:
  created:
    - frontend/src/stores/usePriceStore.ts
    - frontend/src/hooks/useSSE.ts
    - frontend/src/hooks/usePortfolio.ts
    - frontend/src/components/WatchlistPanel.tsx
    - frontend/src/components/WatchlistRow.tsx
    - frontend/src/components/PriceCell.tsx
    - frontend/src/components/ChangePercent.tsx
    - frontend/src/components/Sparkline.tsx
  modified:
    - frontend/src/app/page.tsx
    - frontend/src/components/AppShell.tsx

key-decisions:
  - "usePriceStore.getState() in SSE callbacks to avoid stale closures"
  - "Per-ticker Zustand selectors in WatchlistRow for render isolation"
  - "Canvas-based sparkline (60x24px) for lightweight rendering"

patterns-established:
  - "Zustand getState() for event-driven updates outside React lifecycle"
  - "Per-item Zustand selector pattern: usePriceStore((s) => s.prices[ticker])"
  - "Canvas sparkline with min/max normalization"

requirements-completed: [UI-WATCH-01, UI-WATCH-02, UI-WATCH-03, UI-WATCH-04]

duration: 2min
completed: 2026-04-09
---

# Phase 04 Plan 02: Watchlist Panel with Live SSE Data Summary

**Zustand price store with SSE streaming, watchlist panel with flash animations, session change %, and canvas sparklines**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-09T21:33:14Z
- **Completed:** 2026-04-09T21:35:24Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Zustand price store manages live prices, sparkline history (capped at 120 points), connection status, and selected ticker
- SSE hook connects to /api/stream/prices with error-count-based connection status (5 errors = disconnected)
- Portfolio hook polls /api/portfolio every 5s for header cash balance and total value
- Complete watchlist panel with sorted tickers, price flash animations, session change %, and sparkline mini-charts
- Per-ticker Zustand selectors ensure only changed rows re-render (T-04-04 threat mitigation)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Zustand price store, SSE hook, and portfolio fetch hook** - `ebc5435` (feat)
2. **Task 2: Build WatchlistPanel, WatchlistRow, PriceCell, ChangePercent, Sparkline, and wire to AppShell** - `2cfb10c` (feat)

## Files Created/Modified
- `frontend/src/stores/usePriceStore.ts` - Zustand store for SSE price data, sparkline history, connection status, selected ticker
- `frontend/src/hooks/useSSE.ts` - EventSource connection with error tracking and auto-reconnect status
- `frontend/src/hooks/usePortfolio.ts` - Portfolio data polling hook (cash balance, total value)
- `frontend/src/components/PriceCell.tsx` - Price display with green/red flash CSS animation (500ms fade)
- `frontend/src/components/ChangePercent.tsx` - Session change % colored by direction
- `frontend/src/components/Sparkline.tsx` - Canvas mini-chart (60x24px) with progressive fill
- `frontend/src/components/WatchlistRow.tsx` - Single ticker row with per-ticker Zustand selector
- `frontend/src/components/WatchlistPanel.tsx` - Scrollable sidebar listing all watchlist tickers
- `frontend/src/app/page.tsx` - Wired useSSE, usePortfolio, and connectionStatus to AppShell
- `frontend/src/components/AppShell.tsx` - Updated to accept live data props and render WatchlistPanel

## Decisions Made
- Used `usePriceStore.getState()` in SSE callbacks to avoid stale closures (per RESEARCH.md Pitfall 5)
- Per-ticker Zustand selectors `(s) => s.prices[ticker]` for render isolation
- Canvas-based sparkline (60x24px) for lightweight, dependency-free rendering
- Button element for WatchlistRow for accessibility (keyboard navigation)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Watchlist panel complete with live data wiring
- Price store and SSE infrastructure ready for chart area and trade components in Plan 03
- selectedTicker in store ready for main chart selection

---
*Phase: 04-frontend-shell-live-data*
*Completed: 2026-04-09*
