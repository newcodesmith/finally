---
phase: 05-frontend-portfolio-trading
reviewed: 2026-04-09T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - frontend/src/components/AppShell.tsx
  - frontend/src/components/ChatMessage.tsx
  - frontend/src/components/ChatPanel.tsx
  - frontend/src/components/PnlChart.tsx
  - frontend/src/components/PortfolioHeatmap.tsx
  - frontend/src/components/PositionsTable.tsx
  - frontend/src/components/TradeBar.tsx
  - frontend/src/hooks/usePortfolio.ts
  - frontend/src/stores/useChatStore.ts
  - frontend/src/stores/usePortfolioStore.ts
  - frontend/src/types/chat.ts
  - frontend/src/types/portfolio.ts
findings:
  critical: 1
  warning: 6
  info: 3
  total: 10
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-04-09T00:00:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Reviewed 12 frontend source files covering the portfolio/trading UI: stores, hooks, components, and types. The code is well-structured overall with consistent patterns, good TypeScript usage, and clear separation of concerns. The main concerns are:

1. A crash risk in `PnlChart` when `snapshots` data arrives before the async chart library finishes initializing — the data update silently drops, and the inverted conditional render can make the chart container disappear at the wrong time.
2. A trade execution path that does not check `res.ok` before parsing the response as `TradeResponse`, leading to `undefined` fields on HTTP error responses.
3. Input validation gaps in `TradeBar` (arbitrary ticker strings, `Infinity` quantity).
4. Missing array validation on the `fetchSnapshots` response.

---

## Critical Issues

### CR-01: `executeTrade` parses response body without checking `res.ok`

**File:** `frontend/src/stores/usePortfolioStore.ts:72`

**Issue:** `res.json()` is called unconditionally regardless of HTTP status. If the backend returns a 4xx/5xx error body that does not conform to `TradeResponse`, the destructured fields (`json.success`, `json.error`, `json.price`) will all be `undefined`. `json.success` being `undefined` is falsy, so the error path runs — but `json.error` is also `undefined`, meaning `TradeBar` falls back to the generic `'Trade failed'` string. More critically, `json.price` is `undefined`, and `TradeBar` passes it to `formatPrice(result.price)` on the success path — but because `json.success` is falsy the success branch won't execute. However if the backend returns a partially-valid error JSON (e.g., `{detail: "..."}` from FastAPI's default 422), `json.success` remains undefined/falsy and no crash occurs. The real risk is that a network error that still returns an HTTP body (e.g., a proxy 502 with HTML) causes `res.json()` to throw inside the `try` block, which is caught by the outer catch and returns the generic `errorResponse` — this is actually handled. The more impactful bug is that successful trades returning a non-standard body format would silently fail with no useful error.

**Fix:**
```typescript
const res = await fetch('/api/portfolio/trade', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(req),
});

if (!res.ok) {
  // Try to extract a message from the error body
  let errMsg = 'Trade failed';
  try {
    const errBody = await res.json();
    if (errBody?.detail) errMsg = String(errBody.detail);
  } catch { /* ignore parse failure */ }
  const failResponse: TradeResponse = { ...errorResponse, error: errMsg };
  set({ lastTradeResult: failResponse, isTrading: false });
  return failResponse;
}

const json: TradeResponse = await res.json();
```

---

## Warnings

### WR-01: `PnlChart` — async chart init races with snapshot data effect

**File:** `frontend/src/components/PnlChart.tsx:76-91`

**Issue:** The chart is initialized inside an `async` IIFE (dynamic import of `lightweight-charts`). A second `useEffect` watches `snapshots` and calls `seriesRef.current.setData(...)`. If `snapshots` is non-empty before the async init completes (e.g., store already has data on first render), the data effect fires first, finds `seriesRef.current === null`, and silently returns. The chart then renders empty even though data is available. The data effect won't re-run because `snapshots` didn't change.

Additionally, the conditional early-return at line 93 (`if (snapshots.length === 0) return <placeholder>`) renders the placeholder JSX instead of the `<div ref={containerRef}>`. When `snapshots` is initially empty, the chart init effect fires and calls `createChart(containerRef.current, ...)` — but `containerRef.current` will be the `<div>` from a *previous* render only if the snapshot count transitions from >0 to 0 then back to >0. On fresh load with empty snapshots, `containerRef.current` is null because the placeholder is rendered, so `createChart` is never called.

The entire conditional-render design means the chart container `<div>` is only present in the DOM when `snapshots.length > 0`. This makes the chart init effect unreliable — it needs the DOM node to exist, but the node only appears when there's data.

**Fix:** Always render the chart container div; use CSS to show/hide the placeholder overlay instead:
```tsx
return (
  <div className="relative w-full h-full">
    <div ref={containerRef} className="w-full h-full" />
    {snapshots.length === 0 && (
      <div className="absolute inset-0 flex items-center justify-center text-text-secondary text-sm pointer-events-none">
        No data yet
      </div>
    )}
  </div>
);
```
This ensures `containerRef` always points to a stable DOM node, so the async chart init always has a valid target, and the data effect will find `seriesRef.current` populated after init completes.

---

### WR-02: `fetchSnapshots` does not validate that response is an array

**File:** `frontend/src/stores/usePortfolioStore.ts:46-48`

**Issue:** The API response is stored directly as `snapshots` with `set({ snapshots: json })`. If the backend returns a wrapped object (e.g., `{ snapshots: [...] }`) or any non-array on error, `snapshots` will be an object. Downstream code in `PnlChart` calls `snapshots.length` and `snapshots.map(...)` which will return `undefined` for `.length` and throw `TypeError: snapshots.map is not a function`.

**Fix:**
```typescript
const json = await res.json();
set({ snapshots: Array.isArray(json) ? json : [] });
```

---

### WR-03: `TradeBar` — `Infinity` passes quantity validation

**File:** `frontend/src/components/TradeBar.tsx:22-23, 49`

**Issue:** `parseFloat(quantity)` accepts scientific notation strings like `"1e308"`, which returns `Infinity`. `Infinity > 0` is `true`, so the disabled check passes and the request is submitted with `quantity: Infinity`. JSON serializes `Infinity` as `null` in most engines (per the JSON spec, `Infinity` is not valid JSON). The backend will receive `null` for quantity and likely return a 422 validation error, but this is a correctness bug in the frontend.

**Fix:**
```typescript
const qty = parseFloat(quantity);
if (!ticker.trim() || !Number.isFinite(qty) || qty <= 0) return;
```
Also update the `isDisabled` check to use `Number.isFinite`:
```typescript
const isDisabled = isTrading || !ticker.trim() || !quantity ||
  !Number.isFinite(parseFloat(quantity)) || parseFloat(quantity) <= 0;
```

---

### WR-04: `TradeBar` — no ticker validation against watchlist

**File:** `frontend/src/components/TradeBar.tsx:53-58`

**Issue:** The ticker input is a free-text field with no validation against the current watchlist. Any string (including typos, lowercase, or garbage) is submitted directly to the backend. Per PLAN.md §13 Q2, the recommended rule is: "the trade bar validates that the ticker exists in the watchlist before submitting." The backend will auto-add the ticker to the watchlist if it isn't present, which means typos permanently pollute the watchlist.

**Fix:** Import the watchlist from the market store and add a validation check before submitting:
```typescript
// In handleTrade, before the store call:
const watchlist = useMarketStore.getState().watchlist;
const isValidTicker = watchlist.some(
  (w) => w.ticker === ticker.trim().toUpperCase()
);
if (!isValidTicker) {
  setFeedback(`${ticker} is not in your watchlist`);
  setFeedbackType('error');
  return;
}
```

---

### WR-05: `useChatStore` — concurrent `sendMessage` calls can interleave messages

**File:** `frontend/src/stores/useChatStore.ts:26, 53, 67`

**Issue:** Each `sendMessage` call reads the current messages array with `get().messages` and appends to it. If two `sendMessage` calls overlap (e.g., user submits a message and the loading indicator isn't enforced at the call site), both will read the same `messages` snapshot, and the later `set(...)` will overwrite the earlier one, dropping a message. The `isLoading` flag is checked in the UI (`handleSubmit` in `ChatPanel` guards on `isLoading`), but `sendMessage` itself does not guard against concurrent invocation.

**Fix:** Guard at the start of `sendMessage`:
```typescript
sendMessage: async (text: string) => {
  if (get().isLoading) return; // Prevent concurrent sends
  // ...rest of implementation
```

---

### WR-06: `PnlChart` cleanup may call `chart.remove()` on an already-removed chart

**File:** `frontend/src/components/PnlChart.tsx:66-72`

**Issue:** The cleanup function closes over the `chart` local variable in the outer `useEffect` scope. However, `chart` is assigned inside the `async` IIFE. If the component unmounts before the async import resolves, `cancelled` is set to `true` and the async block exits early — but `chart` remains `null`, so `if (chart) chart.remove()` is a no-op (correct). However, if the component unmounts *after* the async block runs but `chart` hasn't been assigned to the closure variable yet (JS microtask boundary), the cleanup fires with `chart === null` while `chartRef.current` holds the chart instance — resulting in a chart that is never removed from the DOM and its internal event listeners (including the ResizeObserver) may leak.

`chartRef.current` is set to `null` in cleanup, but the actual `chart.remove()` relies on the closure-captured `chart` variable, not `chartRef.current`.

**Fix:** Use a ref to hold the chart instance for cleanup:
```typescript
// In cleanup:
return () => {
  cancelled = true;
  if (observer) observer.disconnect();
  if (chartRef.current) {
    chartRef.current.remove();
    chartRef.current = null;
  }
  seriesRef.current = null;
};
```

---

## Info

### IN-01: `AppShell` — `portfolioValue` and `cashBalance` props are redundant

**File:** `frontend/src/components/AppShell.tsx:16-18`

**Issue:** `portfolioValue` and `cashBalance` are passed as props to `AppShell` with hardcoded defaults of `10000`. These values are forwarded to `Header`. Meanwhile, child components use `usePortfolioStore` directly for live values. If the parent page doesn't pass live store values here, `Header` will display stale defaults while child components show live data. The prop interface creates a false seam — the store should be the single source of truth.

**Fix:** Remove these props from `AppShell` and have `Header` read directly from `usePortfolioStore`, the same pattern used by `PositionsTable`, `PnlChart`, and `PortfolioHeatmap`.

---

### IN-02: `useChatStore` — error catch block swallows exception silently

**File:** `frontend/src/stores/useChatStore.ts:59`

**Issue:** The `catch` block uses bare `catch { }` with no logging. When a network error or JSON parse error occurs, there is no way to diagnose it during development. The user sees a generic error message, but the developer has no visibility into the root cause.

**Fix:**
```typescript
} catch (err) {
  console.error('[ChatStore] sendMessage failed:', err);
  // ...existing error message handling
}
```

---

### IN-03: `ExecutedTrade` and `WatchlistChangeResult` use `string` for discriminated fields

**File:** `frontend/src/types/chat.ts:3, 9`

**Issue:** `ExecutedTrade.side` is typed as `string` (line 3) rather than `'buy' | 'sell'`. `WatchlistChangeResult.action` is typed as `string` (line 10) rather than `'add' | 'remove'`. The `ChatMessage.tsx` component uses these values in conditionals (`trade.side === 'buy'`, `change.action === 'add'`). Narrower union types would make the intent explicit and catch typos at compile time.

**Fix:**
```typescript
export interface ExecutedTrade {
  ticker: string;
  side: 'buy' | 'sell';
  quantity: number;
  price: number;
}

export interface WatchlistChangeResult {
  ticker: string;
  action: 'add' | 'remove';
  success: boolean;
}
```

---

_Reviewed: 2026-04-09T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
