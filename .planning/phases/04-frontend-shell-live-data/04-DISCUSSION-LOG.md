# Phase 4: Frontend Shell & Live Data - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-09
**Phase:** 04-frontend-shell-live-data
**Areas discussed:** Layout & panel arrangement, Charting approach, SSE data management, Project scaffolding

---

## Layout & Panel Arrangement

| Option | Description | Selected |
|--------|-------------|----------|
| Sidebar watchlist + main area | Watchlist as fixed left sidebar, main chart fills rest. Classic Bloomberg feel. | |
| Top watchlist + bottom chart | Horizontal watchlist grid across top, chart below. Stock screener layout. | |
| You decide | Let Claude pick the best layout during implementation. | ✓ |

**User's choice:** You decide
**Notes:** User deferred to Claude's discretion for layout arrangement.

---

## Charting Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Lightweight Charts | TradingView's open-source library. Canvas-based, built for financial data, ~40KB. | |
| Recharts | React-friendly SVG charts. Easier API but slower with many data points. | |
| You decide | Let Claude pick based on the trading terminal use case. | ✓ |

**User's choice:** You decide
**Notes:** User deferred to Claude's discretion for charting library selection.

---

## SSE Data Management

| Option | Description | Selected |
|--------|-------------|----------|
| Custom hook + React Context | useMarketData() hook manages EventSource, prices in Context. Simple, no extra deps. | |
| Zustand store | Lightweight external store. Better for high-frequency updates, avoids Context re-render cascading. | |
| You decide | Let Claude pick the state management approach. | ✓ |

**User's choice:** You decide
**Notes:** User deferred to Claude's discretion for SSE state management.

---

## Project Scaffolding

| Option | Description | Selected |
|--------|-------------|----------|
| App Router | Modern Next.js default. Server components by default, 'use client' for interactive parts. | ✓ |
| Pages Router | Classic Next.js. Simpler mental model, every page is client-side. | |
| You decide | Let Claude pick the routing approach. | |

**User's choice:** App Router
**Notes:** User explicitly selected App Router as the Next.js routing approach.

---

## Claude's Discretion

- Layout arrangement and panel sizing
- Charting library selection
- SSE state management approach
- Component organization
- Tailwind theme configuration
- Sparkline rendering approach

## Deferred Ideas

None.
