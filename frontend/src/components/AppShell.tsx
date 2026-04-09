'use client';

import { ReactNode } from 'react';
import Header from './Header';
import WatchlistPanel from './WatchlistPanel';
import MainChart from './MainChart';
import type { ConnectionStatus } from '@/types/market';

interface AppShellProps {
  portfolioValue?: number;
  cashBalance?: number;
  connectionStatus?: ConnectionStatus;
  children?: ReactNode;
}

export default function AppShell({
  portfolioValue = 10000,
  cashBalance = 10000,
  connectionStatus = 'disconnected',
  children,
}: AppShellProps) {
  return (
    <div className="flex flex-col h-screen overflow-hidden bg-surface">
      {/* Header — 48px fixed */}
      <Header
        portfolioValue={portfolioValue}
        cashBalance={cashBalance}
        connectionStatus={connectionStatus}
      />

      {/* Content area: sidebar + main */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar — 280px fixed width */}
        <aside className="w-[280px] shrink-0 bg-surface-raised border-r border-border overflow-y-auto">
          <WatchlistPanel />
        </aside>

        {/* Main content area */}
        <main className="flex-1 overflow-hidden">
          {children ?? <MainChart />}
        </main>
      </div>
    </div>
  );
}
