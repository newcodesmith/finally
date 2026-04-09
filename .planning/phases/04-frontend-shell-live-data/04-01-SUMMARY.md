---
phase: 04-frontend-shell-live-data
plan: 01
subsystem: ui
tags: [nextjs, tailwind, typescript, react, static-export, dark-theme]

# Dependency graph
requires: []
provides:
  - Next.js 16 project scaffold with static export
  - Tailwind v4 dark terminal theme with all color tokens
  - AppShell layout (48px header + 280px sidebar + flex-1 main)
  - Header component with portfolio value, cash balance, connection dot
  - PriceUpdate and ConnectionStatus TypeScript types
  - formatPrice and formatPercent utilities
  - Price flash animation CSS classes
affects: [04-02, 04-03, 05-frontend-portfolio-trading]

# Tech tracking
tech-stack:
  added: [next@16.2.3, react@19, tailwindcss@4.2.2, lightweight-charts@5.1.0, zustand@5.0.12, lucide-react]
  patterns: [tailwind-v4-theme-directive, client-component-only-static-export, system-font-stack]

key-files:
  created:
    - frontend/package.json
    - frontend/next.config.ts
    - frontend/src/app/globals.css
    - frontend/src/app/layout.tsx
    - frontend/src/app/page.tsx
    - frontend/src/components/AppShell.tsx
    - frontend/src/components/Header.tsx
    - frontend/src/components/ConnectionDot.tsx
    - frontend/src/types/market.ts
    - frontend/src/lib/format.ts
  modified:
    - .gitignore

key-decisions:
  - "Used system font stack instead of Google Fonts (Inter) to avoid network dependency during build"
  - "Tailwind v4 @theme CSS directive for color tokens (not tailwind.config.ts)"
  - "Fixed root .gitignore lib/ pattern to /lib/ to avoid blocking frontend/src/lib/"

patterns-established:
  - "Tailwind v4 theme: @theme directive in globals.css with --color-* custom properties"
  - "All page/component files use 'use client' directive for static export compatibility"
  - "AppShell accepts sidebar and children slots for composable layout"

requirements-completed: [UI-LAYOUT-01, UI-LAYOUT-02, UI-LAYOUT-03, UI-LAYOUT-04]

# Metrics
duration: 5min
completed: 2026-04-09
---

# Phase 04 Plan 01: Frontend Shell Summary

**Next.js 16 static export with Tailwind v4 dark terminal theme, 280px sidebar layout, and header with portfolio value/cash/connection dot**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-09T21:26:12Z
- **Completed:** 2026-04-09T21:31:16Z
- **Tasks:** 2
- **Files modified:** 15

## Accomplishments
- Fresh Next.js 16 project with App Router, TypeScript, Tailwind v4, and static export
- Dark terminal theme with surface colors (#0d1117, #161b22, #1c2333), accent colors (yellow, blue, purple), and semantic colors (green/red for price direction)
- Layout shell with 48px header, 280px sidebar, and flex-1 main area
- Header with FinAlly name, yellow portfolio value, cash balance, and connection status dot
- Shared types (PriceUpdate, ConnectionStatus) and formatting utilities (formatPrice, formatPercent) ready for Plan 02

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold Next.js project, configure Tailwind dark theme, create layout shell** - `9d264ed` (feat)
2. **Task 2: Build Header component with portfolio value, cash balance, and connection status dot** - `560542c` (feat)
3. **Scaffolded static assets** - `0c1171c` (chore)

## Files Created/Modified
- `frontend/package.json` - Next.js project with lightweight-charts, zustand, lucide-react dependencies
- `frontend/next.config.ts` - Static export configuration (output: 'export')
- `frontend/src/app/globals.css` - Tailwind v4 theme with dark surface colors and flash animation CSS
- `frontend/src/app/layout.tsx` - Root layout with dark background and system font stack
- `frontend/src/app/page.tsx` - Main page rendering AppShell
- `frontend/src/components/AppShell.tsx` - Layout shell with Header, 280px sidebar, flex-1 main
- `frontend/src/components/Header.tsx` - Header bar with portfolio value, cash, connection dot
- `frontend/src/components/ConnectionDot.tsx` - 8px status indicator with color mapping and tooltip
- `frontend/src/types/market.ts` - PriceUpdate interface and ConnectionStatus type
- `frontend/src/lib/format.ts` - formatPrice (Intl.NumberFormat) and formatPercent utilities
- `.gitignore` - Fixed lib/ pattern to /lib/ (scoped to root only)

## Decisions Made
- Used system font stack instead of Google Fonts to avoid network dependency during build (Google Fonts fetch failed in sandboxed build environment; system font fallback is equivalent for Inter)
- Tailwind v4 uses @theme CSS directive -- configured all tokens in globals.css instead of tailwind.config.ts
- Fixed root .gitignore: `lib/` -> `/lib/` to prevent it from matching `frontend/src/lib/`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed root .gitignore blocking frontend/src/lib/**
- **Found during:** Task 1 (staging files for commit)
- **Issue:** Root .gitignore had `lib/` which matched all lib directories recursively, preventing frontend/src/lib/format.ts from being tracked
- **Fix:** Changed `lib/` to `/lib/` to scope it to root-level only
- **Files modified:** .gitignore
- **Verification:** git add succeeded after fix
- **Committed in:** 9d264ed (Task 1 commit)

**2. [Rule 3 - Blocking] Removed Google Fonts dependency from layout**
- **Found during:** Task 1 (build verification)
- **Issue:** Geist font from next/font/google failed to fetch during build (network sandboxing)
- **Fix:** Removed Google Font import, using system font stack via Tailwind theme --font-family-sans
- **Files modified:** frontend/src/app/layout.tsx
- **Verification:** Build completed successfully
- **Committed in:** 9d264ed (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes necessary for build to succeed. No scope creep.

## Issues Encountered
- Next.js build requires `dangerouslyDisableSandbox` due to PostCSS/Turbopack spawning child processes. All subsequent builds in this phase will need this.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Layout shell ready for Plan 02 (WatchlistPanel in sidebar slot, SSE connection)
- All shared types and utilities available for import
- Flash animation CSS classes (.flash-up, .flash-down) ready for PriceCell component
- Dependencies installed: lightweight-charts (Plan 03), zustand (Plan 02), lucide-react

---
*Phase: 04-frontend-shell-live-data*
*Completed: 2026-04-09*
