---
phase: 04-frontend-shell-live-data
verified: 2026-04-09T22:00:00Z
status: human_needed
score: 13/13 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open http://localhost:8000 and confirm dark terminal aesthetic"
    expected: "Dark background (#0d1117), header bar with 'FinAlly', portfolio value in yellow, Cash label, connection dot that turns green when SSE connects"
    why_human: "Visual appearance and CSS animation timing cannot be verified programmatically"
  - test: "Watch the watchlist for 30 seconds and confirm price flash animations"
    expected: "Prices briefly flash green on uptick and red on downtick, fading over ~500ms"
    why_human: "CSS animation timing and visual behavior requires browser observation"
  - test: "Watch sparklines fill in progressively from SSE data"
    expected: "Sparkline mini-charts grow as prices arrive from the SSE stream since page load"
    why_human: "Progressive canvas rendering over time requires live browser observation"
  - test: "Click a ticker in the watchlist and confirm chart switches"
    expected: "Yellow left border appears on the selected row; main chart updates to show that ticker's price history with accent blue line"
    why_human: "Interactive selection and chart rendering requires browser interaction"
---

# Phase 4: Frontend Shell & Live Data — Verification Report

**Phase Goal:** Users see a dark, terminal-inspired interface with a live-updating watchlist, sparklines, and a main chart area
**Verified:** 2026-04-09T22:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | App renders a dark terminal-inspired layout with correct accent colors | VERIFIED | globals.css defines #0d1117 surface, #161b22 surface-raised; layout.tsx sets backgroundColor #0d1117; AppShell renders full-screen flex layout |
| 2 | Header displays portfolio value in yellow, cash balance, and connection status dot | VERIFIED | Header.tsx: text-accent-yellow for portfolioValue, "Cash" label, formatPrice for cashBalance, ConnectionDot component; all wired |
| 3 | Accent colors yellow #ecad0a, blue #209dd7, purple #753991 defined in theme | VERIFIED | globals.css @theme block: --color-accent-yellow: #ecad0a, --color-accent-blue: #209dd7, --color-accent-purple: #753991 |
| 4 | Next.js project builds successfully with static export | VERIFIED | next.config.ts: output:"export"; out/index.html exists in build output directory |
| 5 | Watchlist panel displays all tickers with current price, session change %, and sparkline | VERIFIED | WatchlistPanel renders WatchlistRow per ticker; each row contains PriceCell, ChangePercent, Sparkline; all wired to usePriceStore |
| 6 | Prices flash green on uptick and red on downtick with ~500ms CSS fade | VERIFIED | PriceCell.tsx: useEffect watches changeDirection, applies flash-up/flash-down CSS classes, clears after 500ms via setTimeout; globals.css defines transition: background-color 500ms ease-out |
| 7 | Sparklines progressively fill in from SSE data since page load | VERIFIED | usePriceStore.updatePrices() appends to sparklineHistory (capped at 120 via shift()); Sparkline.tsx draws canvas path from data array using getContext('2d') |
| 8 | Clicking a ticker highlights it with yellow left border and sets it as selected | VERIFIED | WatchlistRow: onClick calls setSelectedTicker; isSelected applies border-l-2 border-l-accent-yellow; WatchlistPanel wires setSelectedTicker from store |
| 9 | Header shows live portfolio value and connection status from real SSE data | VERIFIED | page.tsx: useSSE() establishes EventSource; usePortfolio() polls /api/portfolio; connectionStatus from usePriceStore; all passed to AppShell → Header |
| 10 | Main chart area displays a line chart for the currently selected ticker | VERIFIED | MainChart.tsx: dynamic import of lightweight-charts inside useEffect; createChart with LineSeries; subscribes to usePriceStore for selectedTicker and sparklineHistory |
| 11 | Chart updates in real-time as new SSE price data arrives | VERIFIED | MainChart useEffect watches [selectedTicker, history]; calls seriesRef.current.setData(chartData) on each update |
| 12 | Selecting a different ticker switches the chart to that ticker's data | VERIFIED | MainChart tracks prevTickerRef; calls chart.timeScale().fitContent() when selectedTicker changes; setData replaces full series data |
| 13 | Chart has correct dark theme styling matching terminal aesthetic | VERIFIED | createChart options: background #0d1117, grid vertLines/horzLines #1c2333, crosshair/borders #30363d, line series color #209dd7 |

**Score:** 13/13 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/package.json` | Next.js project with dependencies | VERIFIED | Contains lightweight-charts@^5.1.0, zustand@^5.0.12, lucide-react |
| `frontend/next.config.ts` | Static export config | VERIFIED | output: "export", images.unoptimized: true |
| `frontend/src/app/globals.css` | Tailwind theme with dark colors and flash animations | VERIFIED | @theme directive, all color tokens, .flash-up, .flash-down, .price-cell |
| `frontend/src/components/AppShell.tsx` | Top-level layout with header, sidebar, main area | VERIFIED | 45 lines; renders Header, WatchlistPanel in aside[w-280px], MainChart in main |
| `frontend/src/components/Header.tsx` | Header bar with portfolio value, cash, connection dot | VERIFIED | 42 lines; text-accent-yellow, formatPrice, ConnectionDot |
| `frontend/src/components/ConnectionDot.tsx` | 8px colored circle with tooltip | VERIFIED | 25 lines; w-2 h-2 rounded-full; statusConfig maps all 3 states; title attribute |
| `frontend/src/types/market.ts` | TypeScript interfaces for price data and connection status | VERIFIED | Exports PriceUpdate (8 fields) and ConnectionStatus type |
| `frontend/src/lib/format.ts` | Price and percent formatting utilities | VERIFIED | Exports formatPrice (Intl.NumberFormat) and formatPercent |
| `frontend/src/stores/usePriceStore.ts` | Zustand store for SSE price data | VERIFIED | 45 lines; exports usePriceStore; MAX_SPARKLINE_POINTS=120; all required state fields |
| `frontend/src/hooks/useSSE.ts` | EventSource connection management hook | VERIFIED | 41 lines; new EventSource('/api/stream/prices'); getState() pattern; error count tracking |
| `frontend/src/hooks/usePortfolio.ts` | Portfolio data fetching hook | VERIFIED | 32 lines; exports usePortfolio; fetches /api/portfolio every 5s; returns cash_balance, total_value |
| `frontend/src/components/WatchlistPanel.tsx` | Scrollable sidebar listing all watchlist tickers | VERIFIED | 35 lines; "Watchlist" header; sorted ticker list; WatchlistRow for each ticker |
| `frontend/src/components/WatchlistRow.tsx` | Single ticker row with price, change%, sparkline | VERIFIED | 52 lines; per-ticker Zustand selector; PriceCell, ChangePercent, Sparkline rendered |
| `frontend/src/components/PriceCell.tsx` | Price display with green/red flash animation | VERIFIED | 46 lines; flash-up/flash-down classes; 500ms setTimeout; formatPrice |
| `frontend/src/components/Sparkline.tsx` | Canvas mini-chart 60x24px | VERIFIED | 61 lines; getContext('2d'); min/max normalization; default 60x24 dimensions |
| `frontend/src/components/MainChart.tsx` | Lightweight Charts wrapper for selected ticker | VERIFIED | 130 lines; dynamic import; createChart; ResizeObserver; chart.remove() cleanup |
| `frontend/out/index.html` | Static build output | VERIFIED | File exists at frontend/out/index.html |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| page.tsx | AppShell.tsx | import and render | WIRED | `import AppShell from '@/components/AppShell'`; rendered with live props |
| AppShell.tsx | Header.tsx | import and render | WIRED | `import Header from './Header'`; rendered with portfolioValue, cashBalance, connectionStatus props |
| next.config.ts | static export | output: 'export' | WIRED | `output: "export"` present |
| useSSE.ts | usePriceStore.ts | usePriceStore.getState() | WIRED | `usePriceStore.getState().updatePrices(data)` and `setConnectionStatus` calls in EventSource callbacks |
| WatchlistRow.tsx | usePriceStore.ts | Zustand selector | WIRED | `usePriceStore((s) => s.prices[ticker])` and `s.sparklineHistory[ticker]` selectors |
| PriceCell.tsx | globals.css | flash-up/flash-down classes | WIRED | `flash-up`, `flash-down` applied via setFlashClass state; classes defined in globals.css |
| Sparkline.tsx | canvas rendering | getContext('2d') | WIRED | `canvas.getContext('2d')` with full path drawing implementation |
| MainChart.tsx | usePriceStore.ts | Zustand subscription for selectedTicker | WIRED | `usePriceStore((s) => s.selectedTicker)` and `s.sparklineHistory[...]` |
| MainChart.tsx | lightweight-charts | dynamic import of createChart | WIRED | `await import('lightweight-charts')` inside useEffect |
| AppShell.tsx | MainChart.tsx | render in main area | WIRED | `{children ?? <MainChart />}` — MainChart is default in main content area |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| WatchlistPanel.tsx | tickers | usePriceStore.prices (Object.keys) | Yes — populated by useSSE from /api/stream/prices | FLOWING |
| WatchlistRow.tsx | priceData | usePriceStore((s) => s.prices[ticker]) | Yes — from SSE EventSource | FLOWING |
| WatchlistRow.tsx | sparklineData | usePriceStore((s) => s.sparklineHistory[ticker]) | Yes — accumulated from SSE events | FLOWING |
| PriceCell.tsx | price, changeDirection | Props from WatchlistRow | Yes — from live SSE data | FLOWING |
| Sparkline.tsx | data | Props from WatchlistRow (sparklineHistory) | Yes — from SSE accumulation | FLOWING |
| MainChart.tsx | history | usePriceStore sparklineHistory[selectedTicker] | Yes — from SSE accumulation | FLOWING |
| Header.tsx | portfolioValue, cashBalance | usePortfolio() fetches /api/portfolio | Yes — REST poll every 5s | FLOWING |
| Header.tsx | connectionStatus | usePriceStore.connectionStatus | Yes — set by useSSE onopen/onerror | FLOWING |

### Behavioral Spot-Checks

Step 7b: SKIPPED — SSE requires live backend; visual verification requires browser. These are routed to human verification below.

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Static build output exists | ls frontend/out/index.html | File found | PASS |
| next.config.ts has output export | grep "output.*export" frontend/next.config.ts | output: "export" found | PASS |
| PriceStore caps at 120 points | grep "MAX_SPARKLINE_POINTS" frontend/src/stores/usePriceStore.ts | MAX_SPARKLINE_POINTS = 120 | PASS |
| SSE connects to correct endpoint | grep "EventSource" frontend/src/hooks/useSSE.ts | new EventSource('/api/stream/prices') | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| UI-LAYOUT-01 | 04-01-PLAN.md | Dark terminal-inspired theme (#0d1117) | SATISFIED | globals.css: --color-surface: #0d1117; layout.tsx: backgroundColor '#0d1117' |
| UI-LAYOUT-02 | 04-01-PLAN.md | Header with portfolio total value, connection status, cash balance | SATISFIED | Header.tsx renders all three; wired to real data in page.tsx |
| UI-LAYOUT-03 | 04-01-PLAN.md | Connection status dot (green/yellow/red) | SATISFIED | ConnectionDot.tsx: 3-state color mapping with title tooltip |
| UI-LAYOUT-04 | 04-01-PLAN.md | Accent colors: yellow #ecad0a, blue #209dd7, purple #753991 | SATISFIED | globals.css @theme: all three accent colors defined |
| UI-WATCH-01 | 04-02-PLAN.md | Watchlist panel shows ticker, price, session change %, sparkline | SATISFIED | WatchlistRow renders all four elements from live Zustand data |
| UI-WATCH-02 | 04-02-PLAN.md | Prices flash green/red with ~500ms CSS fade | SATISFIED | PriceCell.tsx: flash-up/flash-down with 500ms setTimeout; CSS transition 500ms ease-out |
| UI-WATCH-03 | 04-02-PLAN.md | Sparklines accumulate from SSE data since page load | SATISFIED | usePriceStore.updatePrices appends history; Sparkline renders from accumulated array |
| UI-WATCH-04 | 04-02-PLAN.md | Clicking ticker selects it for main chart | SATISFIED | WatchlistRow onClick → setSelectedTicker; yellow border on isSelected; MainChart subscribes to selectedTicker |
| UI-CHART-01 | 04-03-PLAN.md | Main chart area shows larger price chart for selected ticker | SATISFIED | MainChart.tsx: Lightweight Charts line series in accent blue, updates from Zustand sparklineHistory |

All 9 requirements for Phase 4 are satisfied. REQUIREMENTS.md marks all as [x] Complete.

**Orphaned requirements check:** No requirements mapped to Phase 4 in REQUIREMENTS.md that are missing from plan coverage.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

No TODO/FIXME comments, no placeholder returns, no hardcoded empty props, no stub implementations found across any Phase 4 files.

### Human Verification Required

#### 1. Dark Terminal Aesthetic Visual Check

**Test:** Run the app (backend + frontend) and open http://localhost:8000 in a browser.
**Expected:** Dark background (#0d1117), header bar with "FinAlly" on the left, portfolio value in yellow (#ecad0a), "Cash $10,000.00" label, and a colored connection dot on the right. All visible without scrolling.
**Why human:** CSS color rendering, font rendering, and layout proportions require visual inspection.

#### 2. Live Price Flash Animation

**Test:** Watch the watchlist panel for 30+ seconds with SSE connected (connection dot green).
**Expected:** Prices briefly flash a green background on uptick and a red background on downtick, fading over approximately 500ms. Flashes reset and can re-trigger on subsequent ticks.
**Why human:** CSS animation timing (500ms fade) and visual behavior requires live browser observation; cannot be verified by reading code alone.

#### 3. Sparkline Progressive Fill

**Test:** Open the app and watch the sparkline mini-charts in the watchlist sidebar over 60+ seconds.
**Expected:** Each sparkline starts empty or with 1-2 points and progressively accumulates data as SSE events arrive. After 1 minute the sparklines should show visible price trend shapes.
**Why human:** Progressive canvas rendering over time requires a running app and live observation.

#### 4. Ticker Selection and Chart Switch

**Test:** Click a ticker in the watchlist (e.g., TSLA). Then click a different ticker (e.g., AAPL).
**Expected:** The first clicked ticker shows a yellow left border. The main chart switches to display that ticker's price history as a blue line. Clicking a second ticker moves the yellow border and switches the chart.
**Why human:** Interactive click behavior, visual selection state, and chart rendering require browser interaction and observation.

### Gaps Summary

No automated gaps found. All 13 truths verified, all 17 artifacts exist and are substantive, all 10 key links confirmed wired, all 8 data flows confirmed active. All 9 requirement IDs satisfied.

The only items requiring resolution are the 4 human verification checks above, which depend on a running app with a live backend SSE stream. These are standard visual/interactive checks that the Phase 03 plan (Task 2) documented as a blocking human checkpoint — the SUMMARY for 04-03 states "Visual verification passed."

If the prior visual verification approval is accepted as sufficient, this phase can be considered fully passed. Otherwise, the 4 human checks above should be re-run against the current build.

---

_Verified: 2026-04-09T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
