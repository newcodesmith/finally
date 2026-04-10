'use client';

import { MessageSquare } from 'lucide-react';
import Header from './Header';
import WatchlistPanel from './WatchlistPanel';
import MainChart from './MainChart';
import PortfolioHeatmap from './PortfolioHeatmap';
import PnlChart from './PnlChart';
import PositionsTable from './PositionsTable';
import TradeBar from './TradeBar';
import ChatPanel from './ChatPanel';
import { useChatStore } from '@/stores/useChatStore';
import type { ConnectionStatus } from '@/types/market';

interface AppShellProps {
  portfolioValue?: number;
  cashBalance?: number;
  connectionStatus?: ConnectionStatus;
}

export default function AppShell({
  portfolioValue = 10000,
  cashBalance = 10000,
  connectionStatus = 'disconnected',
}: AppShellProps) {
  const isOpen = useChatStore((s) => s.isOpen);
  const toggleOpen = useChatStore((s) => s.toggleOpen);

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
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Top: Main chart — takes remaining height */}
          <div className="flex-1 min-h-0">
            <MainChart />
          </div>

          {/* Bottom panel: portfolio views — fixed 240px */}
          <div className="h-[240px] shrink-0 border-t border-border flex">
            {/* Left: Heatmap ~40% */}
            <div className="w-2/5 border-r border-border overflow-hidden">
              <PortfolioHeatmap />
            </div>
            {/* Middle: P&L chart ~30% */}
            <div className="w-[30%] border-r border-border overflow-hidden">
              <PnlChart />
            </div>
            {/* Right: Positions table ~30% */}
            <div className="flex-1 overflow-auto">
              <PositionsTable />
            </div>
          </div>

          {/* Trade bar at bottom */}
          <TradeBar />
        </main>

        {/* Chat sidebar — collapsible right panel */}
        {isOpen && (
          <aside className="w-[340px] shrink-0 bg-surface-raised border-l border-border flex flex-col">
            <ChatPanel />
          </aside>
        )}
      </div>

      {/* Chat toggle button — floating bottom-right */}
      {!isOpen && (
        <button
          onClick={toggleOpen}
          className="fixed bottom-4 right-4 z-50 bg-accent-purple text-white rounded-full w-12 h-12 flex items-center justify-center shadow-lg hover:opacity-90"
          title="Open AI Assistant"
        >
          <MessageSquare className="w-5 h-5" />
        </button>
      )}
    </div>
  );
}
