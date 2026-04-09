# Phase 4: Frontend Shell & Live Data - Research

**Researched:** 2026-04-09
**Domain:** Next.js static export, SSE real-time data, financial charting, Tailwind dark theme
**Confidence:** HIGH

## Summary

Phase 4 is a greenfield frontend build. The `frontend/` directory contains only stale build artifacts (`.next/`, `out/`) from a prior attempt -- no source files exist. The phase scaffolds a Next.js App Router project with static export, establishes a dark terminal-inspired theme with Tailwind CSS, builds a left-sidebar watchlist with live SSE price updates (flash animations, sparklines), and renders a main chart for the selected ticker.

The backend APIs are already implemented: `GET /api/stream/prices` (SSE), `GET /api/watchlist`, and `GET /api/portfolio`. The SSE endpoint sends a single JSON object per event containing all watchlist tickers. The frontend needs to parse this, maintain per-ticker price history for sparklines, and drive flash animations based on `change_direction`.

**Primary recommendation:** Use Lightweight Charts (canvas-based, TradingView) for the main chart, Zustand for SSE price state management, and hand-drawn canvas sparklines. Scaffold fresh with `npx create-next-app@latest` after cleaning stale artifacts.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-02:** Desktop-first, data-dense layout inspired by Bloomberg terminals per PLAN.md
- **D-04:** Sparklines in the watchlist panel must accumulate data from SSE since page load (reset on reload per PLAN.md)
- **D-06:** EventSource connection to `/api/stream/prices` with automatic reconnection (built-in EventSource retry)
- **D-07:** Price history for sparklines accumulated in-memory on the client since page load
- **D-08:** Next.js App Router with static export (`output: 'export'`)
- **D-09:** Tailwind CSS with custom dark theme using project accent colors (yellow #ecad0a, blue #209dd7, purple #753991)
- **D-10:** Frontend is greenfield -- clean `frontend/` directory, fresh `npx create-next-app` setup needed (stale `.next` and `out` artifacts should be cleaned)

### Claude's Discretion
- **D-01:** Layout arrangement and panel sizing
- **D-03:** Charting library selection (Lightweight Charts or Recharts)
- **D-05:** SSE state management approach (Context vs Zustand)
- Component file organization within `frontend/src/`
- Exact Tailwind theme configuration values
- Sparkline rendering approach (canvas vs SVG)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-LAYOUT-01 | Dark terminal-inspired theme (backgrounds ~#0d1117 or #1a1a2e) | Tailwind theme extension in UI-SPEC with surface colors; apply via `globals.css` and `tailwind.config.ts` |
| UI-LAYOUT-02 | Header with portfolio total value, connection status indicator, cash balance | Portfolio value from `GET /api/portfolio` (returns `total_value`, `cash_balance`); SSE status from EventSource events |
| UI-LAYOUT-03 | Connection status dot (green/yellow/red) | Track `onopen`, `onerror` on EventSource; 8px circle component with tooltip |
| UI-LAYOUT-04 | Accent colors: yellow #ecad0a, blue #209dd7, purple #753991 | Tailwind theme `colors.accent` extension; purple reserved for Phase 5 |
| UI-WATCH-01 | Watchlist panel shows ticker, price, session change %, sparkline per ticker | Watchlist data from SSE stream (all tickers per event); session change % = `((price - session_open_price) / session_open_price) * 100` |
| UI-WATCH-02 | Prices flash green (uptick) or red (downtick) with ~500ms CSS fade | CSS `transition: background-color 500ms ease-out`; toggle class based on `change_direction` field |
| UI-WATCH-03 | Sparklines accumulate from SSE data since page load | In-memory array per ticker, max 120 points, canvas mini-chart 60x24px |
| UI-WATCH-04 | Clicking a ticker selects it for the main chart | Zustand selected ticker state; visual: left border 2px yellow + hover bg |
| UI-CHART-01 | Main chart area shows larger price chart for selected ticker | Lightweight Charts `createChart` with `addLineSeries`; data from accumulated SSE history |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| next | 16.2.3 | React framework with App Router and static export | Declared in PLAN.md; App Router is current default [VERIFIED: npm registry] |
| react | 19.2.5 | UI rendering | Peer dependency of Next.js 16 [VERIFIED: npm registry] |
| typescript | 6.0.2 | Type safety | Declared in PLAN.md; Next.js scaffolding includes it [VERIFIED: npm registry] |
| tailwindcss | 4.2.2 | Utility-first CSS with custom dark theme | Declared in PLAN.md and D-09 [VERIFIED: npm registry] |
| lightweight-charts | 5.1.0 | Canvas-based financial charting (TradingView) | Best fit for trading terminal: canvas performance, built-in financial chart types, crosshair/tooltip support [VERIFIED: npm registry] |
| zustand | 5.0.12 | Lightweight state management for SSE price data | Minimal boilerplate, works outside React tree, fine-grained subscriptions reduce re-renders on high-frequency updates [VERIFIED: npm registry] |
| lucide-react | 1.8.0 | Icon library | Declared in UI-SPEC [VERIFIED: npm registry] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @types/react | 19.2.14 | TypeScript types for React | Dev dependency, auto-included by create-next-app [VERIFIED: npm registry] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Lightweight Charts | Recharts | Recharts is SVG-based, simpler React API, but slower with high-frequency updates and lacks built-in financial chart features (crosshair, price axis). For a trading terminal, canvas performance wins. |
| Zustand | React Context + useReducer | Context causes full subtree re-renders on every price tick (~2/sec for 10 tickers). Zustand's selector-based subscriptions only re-render the specific row that changed. Critical for SSE performance. |

### Discretion Recommendations

**D-01 Layout:** Left sidebar watchlist (280px fixed) + main chart (flex-1), per UI-SPEC. This is the standard Bloomberg/terminal pattern. [ASSUMED]

**D-03 Charting:** Use **Lightweight Charts 5.1.0**. Rationale:
- Canvas-based rendering handles real-time updates efficiently [CITED: https://tradingview.github.io/lightweight-charts/]
- Built-in line series, time axis, crosshair, and price formatting -- no manual chart building
- TradingView's official library, purpose-built for financial data
- Official React tutorial shows clean integration pattern with `useRef` + `useEffect` [CITED: https://tradingview.github.io/lightweight-charts/tutorials/react/simple]

**D-05 State Management:** Use **Zustand**. Rationale:
- SSE delivers ~2 events/sec, each containing 10 tickers -- that is 20 price updates/sec
- Context re-renders every consumer on every update; Zustand re-renders only the row whose ticker changed
- Zustand stores work outside React (can update from EventSource callback without hooks)
- Tiny bundle (~1KB gzipped) [ASSUMED]

**Sparkline Rendering:** Use **canvas** (not SVG). At 60x24px with up to 120 data points, canvas is simpler and more performant than SVG path elements. A 15-line utility function suffices. [ASSUMED]

**Installation:**
```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --app --src-dir --no-eslint --import-alias "@/*"
npm install lightweight-charts zustand lucide-react
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/
  src/
    app/
      layout.tsx          # Root layout with Inter font, dark class, SSEProvider
      page.tsx            # Main page composing AppShell
      globals.css         # Tailwind imports + flash animation CSS
    components/
      AppShell.tsx        # Header + sidebar + main layout
      Header.tsx          # Portfolio value, cash, connection dot
      ConnectionDot.tsx   # 8px status indicator
      WatchlistPanel.tsx  # Scrollable sidebar with rows
      WatchlistRow.tsx    # Single ticker row with price, change, sparkline
      PriceCell.tsx       # Price display with flash animation
      ChangePercent.tsx   # Colored +/- percentage
      Sparkline.tsx       # Canvas mini-chart
      MainChart.tsx       # Lightweight Charts wrapper
    stores/
      usePriceStore.ts    # Zustand store for SSE price data + sparkline history
    hooks/
      useSSE.ts           # EventSource connection management
      usePortfolio.ts     # Fetch portfolio data for header
    lib/
      format.ts           # Price/percent formatting utilities
    types/
      market.ts           # PriceUpdate, ConnectionStatus types
  next.config.ts          # output: 'export'
  tailwind.config.ts      # Custom dark theme extension
```

### Pattern 1: Zustand Price Store
**What:** Single store holding latest prices, sparkline history, connection status, and selected ticker.
**When to use:** All components that need price data subscribe to specific slices.
**Example:**
```typescript
// Source: Zustand docs pattern + project requirements
interface PriceData {
  ticker: string;
  price: number;
  previous_price: number;
  session_open_price: number;
  change_direction: 'up' | 'down' | 'unchanged';
  timestamp: string;
}

interface PriceStore {
  prices: Record<string, PriceData>;
  sparklineHistory: Record<string, number[]>;
  connectionStatus: 'connected' | 'reconnecting' | 'disconnected';
  selectedTicker: string | null;
  updatePrices: (data: Record<string, PriceData>) => void;
  setSelectedTicker: (ticker: string) => void;
  setConnectionStatus: (status: PriceStore['connectionStatus']) => void;
}
```

### Pattern 2: SSE EventSource Hook
**What:** Custom hook managing EventSource lifecycle, parsing events, pushing to Zustand store.
**When to use:** Called once at the app root level.
**Example:**
```typescript
// SSE event format from backend (verified from backend/app/market/stream.py):
// data: {"AAPL": {"ticker": "AAPL", "price": 190.50, "previous_price": 190.25,
//         "session_open_price": 189.00, "timestamp": "...",
//         "change": 0.25, "change_percent": 0.1315, "change_direction": "up"}, ...}
//
// NOTE: All tickers arrive in a single JSON object per event, NOT individual events per ticker.
```

### Pattern 3: Lightweight Charts React Integration
**What:** Wrap chart creation in useRef + useEffect; update data via chart API (not React re-renders).
**When to use:** MainChart component for the selected ticker.
**Example:**
```typescript
// Source: https://tradingview.github.io/lightweight-charts/tutorials/react/simple
// Create chart in useEffect with ref to container div
// Store chart and series instances in useRef
// Update data imperatively via series.update() -- NOT by re-rendering the component
// Clean up with chart.remove() in useEffect cleanup
```

### Pattern 4: Price Flash Animation
**What:** CSS transition-based flash on price update, driven by change_direction.
**When to use:** WatchlistRow price cell.
**Example:**
```css
/* globals.css */
.price-cell {
  transition: background-color 500ms ease-out;
}
.flash-up {
  background-color: rgba(38, 166, 65, 0.15);
}
.flash-down {
  background-color: rgba(248, 81, 73, 0.15);
}
```
```typescript
// In PriceCell component: apply flash class on change_direction update,
// remove after 500ms via setTimeout. Use a key or ref to track previous direction.
```

### Anti-Patterns to Avoid
- **Re-rendering chart on every price update:** Lightweight Charts must be updated imperatively via `series.update()`, not by passing data as React props that trigger re-renders.
- **Storing all price state in React Context:** Causes cascading re-renders across the entire app on every SSE tick (20 updates/sec).
- **Creating multiple EventSource connections:** Only one EventSource should exist per app instance; share data via the store.
- **Using `useEffect` dependencies on price data for flash animation:** This causes unnecessary re-renders; use direct DOM manipulation or CSS class toggling with setTimeout.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Financial chart rendering | Custom canvas chart with axes, crosshair, zoom | Lightweight Charts `createChart` + `addLineSeries` | Time axis formatting, price axis, crosshair, auto-scaling are complex; TradingView handles edge cases |
| State management with selectors | Custom pub/sub or Context-based store | Zustand with selectors | Selector-based subscriptions prevent re-render cascades; battle-tested with high-frequency updates |
| CSS utility framework | Custom CSS variables and utility classes | Tailwind CSS with theme extension | Consistent spacing/color system; purges unused CSS for small bundle |
| Number formatting | Manual string concatenation for prices | `Intl.NumberFormat` | Handles comma separators, decimal places, currency symbols correctly across locales |

**Key insight:** The main complexity in this phase is managing high-frequency SSE updates without performance degradation. The charting library and state management choices directly impact whether the UI stays responsive.

## Common Pitfalls

### Pitfall 1: Next.js Static Export Incompatibilities
**What goes wrong:** Using Next.js features that require a server (API routes, middleware, `getServerSideProps`, dynamic routes without `generateStaticParams`).
**Why it happens:** App Router defaults assume server rendering; `output: 'export'` restricts available features.
**How to avoid:** All components must be client components (`'use client'`) or static. No `next/headers`, no server actions. All data fetching via client-side `fetch` or EventSource.
**Warning signs:** Build errors mentioning "dynamic server usage" or "headers() was called."
[VERIFIED: Next.js docs on static export constraints]

### Pitfall 2: EventSource Reconnection Status
**What goes wrong:** Connection status indicator shows wrong state because EventSource `onerror` fires on both temporary and permanent failures.
**Why it happens:** The EventSource API fires `onerror` for any interruption; the browser then auto-retries. There is no "permanently disconnected" event.
**How to avoid:** On `onerror`, set status to "reconnecting". On `onopen`, set to "connected". Track consecutive errors; after N failures (e.g., 5), consider it "disconnected."
**Warning signs:** Status dot stuck on "reconnecting" or flickering between states.
[ASSUMED]

### Pitfall 3: Sparkline Memory Growth
**What goes wrong:** Unbounded price history arrays consume increasing memory over long sessions.
**Why it happens:** Forgetting to cap the array length when appending new prices.
**How to avoid:** Cap sparkline arrays at 120 points (per UI-SPEC). Use `array.push()` + `if (arr.length > MAX) arr.shift()`.
**Warning signs:** Tab memory usage growing steadily over time.
[ASSUMED]

### Pitfall 4: Lightweight Charts in Static Export
**What goes wrong:** Lightweight Charts uses `window` and `document` which don't exist during SSR/pre-rendering.
**Why it happens:** Next.js pre-renders pages even in static export mode.
**How to avoid:** Import Lightweight Charts dynamically: `const { createChart } = await import('lightweight-charts')` inside useEffect, or use `next/dynamic` with `ssr: false` for the chart component.
**Warning signs:** "window is not defined" error during `next build`.
[ASSUMED -- standard pattern for canvas libraries in Next.js]

### Pitfall 5: Stale Closure in EventSource Callback
**What goes wrong:** EventSource `onmessage` captures stale React state from initial render.
**Why it happens:** The callback is set once and closes over the initial state.
**How to avoid:** Since we're using Zustand, call `usePriceStore.getState().updatePrices(data)` directly in the callback -- Zustand's `getState()` always returns current state without closure issues.
**Warning signs:** Price updates not reflected in UI despite SSE events arriving.
[ASSUMED]

### Pitfall 6: Tailwind v4 Configuration Changes
**What goes wrong:** Tailwind v4 uses CSS-based configuration (`@theme` directive in CSS) instead of `tailwind.config.ts`.
**Why it happens:** Tailwind v4 (released 2025) changed the configuration model significantly from v3.
**How to avoid:** When using `create-next-app` with `--tailwind`, check which Tailwind version is installed. If v4, configure theme in `globals.css` using `@theme` blocks instead of a config file.
**Warning signs:** `tailwind.config.ts` values not taking effect; missing theme tokens.
[ASSUMED -- Tailwind v4 was released January 2025]

## Code Examples

### SSE Event Parsing
```typescript
// Source: Verified from backend/app/market/stream.py and models.py
// The SSE endpoint sends ONE event containing ALL tickers as a flat JSON object:
// data: {"AAPL": {...}, "GOOGL": {...}, "MSFT": {...}, ...}

interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number;
  session_open_price: number;
  timestamp: string;
  change: number;
  change_percent: number;
  change_direction: 'up' | 'down' | 'unchanged';
}

// In SSE hook:
const es = new EventSource('/api/stream/prices');
es.onmessage = (event) => {
  const data: Record<string, PriceUpdate> = JSON.parse(event.data);
  usePriceStore.getState().updatePrices(data);
};
```

### Sparkline Canvas Rendering
```typescript
// Source: Standard canvas line drawing pattern
function drawSparkline(
  canvas: HTMLCanvasElement,
  data: number[],
  color: string = '#209dd7'
) {
  const ctx = canvas.getContext('2d');
  if (!ctx || data.length < 2) return;

  const w = canvas.width;
  const h = canvas.height;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  ctx.clearRect(0, 0, w, h);
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = 1;

  data.forEach((val, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((val - min) / range) * h;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });

  ctx.stroke();
}
```

### Portfolio Fetch for Header
```typescript
// Source: Verified from backend/app/api/portfolio.py
// GET /api/portfolio returns:
// { cash_balance: number, positions: [...], total_value: number }

async function fetchPortfolio(): Promise<{
  cash_balance: number;
  total_value: number;
  positions: Array<{
    ticker: string;
    quantity: number;
    avg_cost: number;
    current_price: number;
    unrealized_pnl: number;
    pnl_percent: number;
    value: number;
  }>;
}> {
  const res = await fetch('/api/portfolio');
  return res.json();
}
```

### Watchlist Initial Load
```typescript
// Source: Verified from backend/app/api/watchlist.py
// GET /api/watchlist returns an array of price update objects (or nulls if no price yet):
// [{ ticker: "AAPL", price: 190.50, ..., change_direction: "up" }, ...]
```

## Backend API Response Shapes (Verified)

These are the exact response shapes from the implemented backend code:

**`GET /api/stream/prices` (SSE)**
```json
{"AAPL": {"ticker": "AAPL", "price": 190.50, "previous_price": 190.25, "session_open_price": 189.00, "timestamp": "2026-04-09T...", "change": 0.25, "change_percent": 0.1315, "change_direction": "up"}, "GOOGL": {...}}
```

**`GET /api/watchlist`**
```json
[{"ticker": "AAPL", "price": 190.50, "previous_price": 190.25, "session_open_price": 189.00, "change_direction": "up", "timestamp": "...", "change": 0.25, "change_percent": 0.1315}]
```

**`GET /api/portfolio`**
```json
{"cash_balance": 10000.0, "positions": [], "total_value": 10000.0}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tailwind v3 config file (`tailwind.config.ts`) | Tailwind v4 CSS-based config (`@theme` in CSS) | Jan 2025 | Theme values defined in CSS, not JS config [ASSUMED] |
| Next.js Pages Router | Next.js App Router | Next.js 13+ (stable in 14) | All new projects use App Router; `'use client'` directive required for interactive components [VERIFIED: Next.js docs] |
| React 18 | React 19 | Dec 2024 | Peer dependency of Next.js 16; no breaking changes for this use case [VERIFIED: npm registry] |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Zustand bundle is ~1KB gzipped | Standard Stack | Low -- even if larger, it's still minimal |
| A2 | EventSource onerror fires on both temporary and permanent failures | Pitfalls | Medium -- connection status logic may need adjustment |
| A3 | Sparkline memory cap of 120 points is in UI-SPEC | Pitfalls | Low -- explicitly stated in UI-SPEC |
| A4 | Lightweight Charts requires dynamic import in Next.js static export | Pitfalls | High -- if not handled, build will fail with "window is not defined" |
| A5 | Tailwind v4 uses CSS-based configuration instead of JS config | Pitfalls | High -- scaffolding approach depends on which version create-next-app installs |
| A6 | Zustand getState() avoids stale closure problem in EventSource callbacks | Pitfalls | Medium -- if wrong, price updates won't reflect in UI |

## Open Questions

1. **Tailwind v4 vs v3 in create-next-app**
   - What we know: Tailwind v4.2.2 is current; `create-next-app` may install v3 or v4 depending on template
   - What's unclear: Which version the Next.js 16 template uses by default
   - Recommendation: After scaffolding, check installed version and configure accordingly. If v4, use `@theme` in CSS. If v3, use `tailwind.config.ts`.

2. **Lightweight Charts v5 React Integration**
   - What we know: TradingView provides official React tutorials for Lightweight Charts
   - What's unclear: Whether v5 has any breaking changes from the tutorial examples (most tutorials are for v4)
   - Recommendation: Use the imperative `useRef` + `useEffect` pattern from TradingView's official React tutorial; this is stable across versions

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Frontend build | Yes | 20.13.1 | -- |
| npm | Package management | Yes | 10.5.2 | -- |
| npx | Scaffolding | Yes | (bundled with npm) | -- |

**Missing dependencies with no fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Jest + React Testing Library (via Next.js) |
| Config file | none -- Wave 0 gap |
| Quick run command | `cd frontend && npm test` |
| Full suite command | `cd frontend && npm test -- --coverage` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-LAYOUT-01 | Dark theme renders correct background colors | unit | `npm test -- --testPathPattern=AppShell` | Wave 0 |
| UI-LAYOUT-02 | Header shows portfolio value and cash | unit | `npm test -- --testPathPattern=Header` | Wave 0 |
| UI-LAYOUT-03 | Connection dot reflects status prop | unit | `npm test -- --testPathPattern=ConnectionDot` | Wave 0 |
| UI-LAYOUT-04 | Accent colors applied correctly | unit | `npm test -- --testPathPattern=theme` | Wave 0 |
| UI-WATCH-01 | Watchlist row renders ticker, price, change, sparkline | unit | `npm test -- --testPathPattern=WatchlistRow` | Wave 0 |
| UI-WATCH-02 | Price flash CSS class applied on direction change | unit | `npm test -- --testPathPattern=PriceCell` | Wave 0 |
| UI-WATCH-03 | Sparkline accumulates data points up to max | unit | `npm test -- --testPathPattern=Sparkline` | Wave 0 |
| UI-WATCH-04 | Clicking row updates selected ticker state | unit | `npm test -- --testPathPattern=WatchlistPanel` | Wave 0 |
| UI-CHART-01 | Main chart renders with price data for selected ticker | integration | `npm test -- --testPathPattern=MainChart` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd frontend && npm test -- --bail`
- **Per wave merge:** `cd frontend && npm test -- --coverage`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] Jest + React Testing Library setup (may come with create-next-app or need manual config)
- [ ] Test file stubs for each component
- [ ] Mock for EventSource API in test environment
- [ ] Mock for Lightweight Charts (canvas not available in jsdom)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A (single-user, no auth) |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A |
| V5 Input Validation | No | Phase 4 is read-only (no user input submitted to backend) |
| V6 Cryptography | No | N/A |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via SSE data injection | Tampering | React's JSX auto-escapes content; don't use `dangerouslySetInnerHTML` on price data |
| EventSource to untrusted origin | Information Disclosure | Same-origin only (`/api/stream/prices`); no CORS needed |

## Sources

### Primary (HIGH confidence)
- Backend source code: `backend/app/market/stream.py`, `models.py`, `api/watchlist.py`, `api/portfolio.py` -- verified exact API response shapes
- npm registry -- verified current versions of all recommended packages
- UI-SPEC: `.planning/phases/04-frontend-shell-live-data/04-UI-SPEC.md` -- design contract

### Secondary (MEDIUM confidence)
- [TradingView Lightweight Charts React tutorial](https://tradingview.github.io/lightweight-charts/tutorials/react/simple) -- React integration pattern
- [TradingView Lightweight Charts](https://www.tradingview.com/lightweight-charts/) -- library capabilities

### Tertiary (LOW confidence)
- Tailwind v4 configuration model change -- based on training knowledge, needs verification during scaffolding

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- versions verified against npm registry, backend APIs verified from source code
- Architecture: HIGH -- patterns derived from verified backend API shapes and UI-SPEC design contract
- Pitfalls: MEDIUM -- some based on training knowledge (Tailwind v4, Lightweight Charts SSR) rather than verified docs

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stable ecosystem, 30-day validity)
