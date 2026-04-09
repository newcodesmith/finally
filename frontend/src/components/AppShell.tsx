'use client';

import { ReactNode } from 'react';

interface AppShellProps {
  sidebar?: ReactNode;
  children?: ReactNode;
}

export default function AppShell({ sidebar, children }: AppShellProps) {
  return (
    <div className="flex flex-col h-screen overflow-hidden bg-surface">
      {/* Content area: sidebar + main */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar — 280px fixed width */}
        <aside className="w-[280px] shrink-0 bg-surface-raised border-r border-border overflow-y-auto">
          {sidebar ?? (
            <div className="p-4 text-text-secondary text-sm">Watchlist</div>
          )}
        </aside>

        {/* Main content area */}
        <main className="flex-1 overflow-hidden">
          {children ?? (
            <div className="p-4 text-text-secondary text-sm">Chart</div>
          )}
        </main>
      </div>
    </div>
  );
}
