# Phase 4: Frontend Shell & Live Data - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the Next.js frontend shell: project scaffolding with App Router and Tailwind CSS, dark terminal-inspired layout with header, watchlist panel with live-updating prices (flash animations, sparklines), and main chart area for the selected ticker. All data comes from the backend SSE stream at `/api/stream/prices`.

</domain>

<decisions>
## Implementation Decisions

### Layout & Panel Arrangement
- **D-01:** Claude's discretion on layout arrangement — choose the best terminal-inspired layout during implementation (sidebar watchlist vs top grid, panel proportions, etc.)
- **D-02:** Desktop-first, data-dense layout inspired by Bloomberg terminals per PLAN.md

### Charting Approach
- **D-03:** Claude's discretion on charting library — choose between Lightweight Charts (canvas-based, financial-focused) and Recharts (SVG, React-friendly) based on the trading terminal use case
- **D-04:** Sparklines in the watchlist panel must accumulate data from SSE since page load (reset on reload per PLAN.md)

### SSE Data Management
- **D-05:** Claude's discretion on state management approach — choose between custom hook + React Context or Zustand based on update frequency and complexity
- **D-06:** EventSource connection to `/api/stream/prices` with automatic reconnection (built-in EventSource retry)
- **D-07:** Price history for sparklines accumulated in-memory on the client since page load

### Project Scaffolding
- **D-08:** Next.js App Router (user selected) with static export (`output: 'export'`)
- **D-09:** Tailwind CSS with custom dark theme using project accent colors (yellow #ecad0a, blue #209dd7, purple #753991)
- **D-10:** Frontend is greenfield — clean `frontend/` directory, fresh `npx create-next-app` setup needed (stale `.next` and `out` artifacts should be cleaned)

### Claude's Discretion
- Layout arrangement and panel sizing
- Charting library selection (Lightweight Charts or Recharts)
- SSE state management approach (Context vs Zustand)
- Component file organization within `frontend/src/`
- Exact Tailwind theme configuration values
- Sparkline rendering approach (canvas vs SVG)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Visual Design & Layout
- `planning/PLAN.md` 10 — Frontend Design section: layout elements, component descriptions, technical notes
- `planning/PLAN.md` 2 — User Experience section: visual design spec, color scheme, price flash behavior

### SSE Protocol
- `planning/PLAN.md` 6 — Market Data section: SSE streaming format, event fields, price cache behavior
- `.planning/phases/01-foundation-market-data-engine/01-CONTEXT.md` — SSE & Price Cache decisions: event format, change_direction values

### Backend API
- `planning/PLAN.md` 8 — API Endpoints section: all REST endpoints the frontend will call

### Architecture
- `planning/PLAN.md` 3 — Architecture Overview: static export served by FastAPI, single origin
- `.planning/codebase/STACK.md` — Technology stack: Node 20 for build, Python runtime details
- `.planning/codebase/STRUCTURE.md` — Directory layout: where frontend output goes (`static/`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- No existing frontend code — greenfield build
- Backend SSE endpoint at `GET /api/stream/prices` already implemented (Phase 1)
- Backend watchlist API at `GET /api/watchlist` already implemented (Phase 2)
- Backend portfolio API at `GET /api/portfolio` already implemented (Phase 2)

### Established Patterns
- Backend uses snake_case JSON keys in API responses
- SSE events contain: ticker, price, previous_price, session_open_price, timestamp, change_direction
- change_direction values: "up", "down", "unchanged" (first tick = "unchanged")
- Dark theme colors: backgrounds ~#0d1117 or #1a1a2e, muted gray borders

### Integration Points
- SSE: `GET /api/stream/prices` — EventSource connection for live price updates
- Watchlist: `GET /api/watchlist` — initial load of watchlist with prices
- Portfolio: `GET /api/portfolio` — header portfolio value and cash balance
- Static export: `frontend/out/` build output served by FastAPI from `static/` directory
- All API calls to same origin (`/api/*`) — no CORS needed

</code_context>

<specifics>
## Specific Ideas

- Price flash effect: brief green/red background highlight on price change, fading over ~500ms via CSS transitions (per PLAN.md)
- Connection status indicator: small colored dot (green/yellow/red) in the header (per PLAN.md)
- Sparklines fill in progressively from SSE data since page load — intentionally reset on reload (per PLAN.md)
- Header shows portfolio total value (updating live) and cash balance

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-frontend-shell-live-data*
*Context gathered: 2026-04-09*
