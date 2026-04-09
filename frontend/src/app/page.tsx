'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSSE } from '@/lib/useSSE';
import { getPortfolio, getWatchlist, getPortfolioHistory } from '@/lib/api';
import type { Portfolio, WatchlistItem, PortfolioSnapshot } from '@/types';
import Header from '@/components/Header';
import Watchlist from '@/components/Watchlist';
import MainChart from '@/components/MainChart';
import PortfolioHeatmap from '@/components/PortfolioHeatmap';
import PnLChart from '@/components/PnLChart';
import PositionsTable from '@/components/PositionsTable';
import TradeBar from '@/components/TradeBar';
import ChatPanel from '@/components/ChatPanel';

export default function Home() {
  const { prices, history, status } = useSSE();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [snapshots, setSnapshots] = useState<PortfolioSnapshot[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string>('AAPL');
  const [chatOpen, setChatOpen] = useState(true);

  const refreshPortfolio = useCallback(async () => {
    try {
      const data = await getPortfolio();
      setPortfolio(data);
    } catch (e) {
      console.error('Failed to fetch portfolio:', e);
    }
  }, []);

  const refreshWatchlist = useCallback(async () => {
    try {
      const data = await getWatchlist();
      setWatchlist(data);
    } catch (e) {
      console.error('Failed to fetch watchlist:', e);
    }
  }, []);

  const refreshSnapshots = useCallback(async () => {
    try {
      const data = await getPortfolioHistory();
      setSnapshots(data);
    } catch (e) {
      console.error('Failed to fetch history:', e);
    }
  }, []);

  // Initial data load
  useEffect(() => {
    refreshPortfolio();
    refreshWatchlist();
    refreshSnapshots();
  }, [refreshPortfolio, refreshWatchlist, refreshSnapshots]);

  // Refresh portfolio every 5 seconds to pick up live price changes
  useEffect(() => {
    const interval = setInterval(() => {
      refreshPortfolio();
      refreshSnapshots();
    }, 5000);
    return () => clearInterval(interval);
  }, [refreshPortfolio, refreshSnapshots]);

  // Compute live total value from SSE prices
  const liveTotalValue = portfolio
    ? portfolio.cash_balance +
      portfolio.positions.reduce((sum, pos) => {
        const livePrice = prices[pos.ticker]?.price ?? pos.current_price;
        return sum + livePrice * pos.quantity;
      }, 0)
    : null;

  const onTradeComplete = useCallback(() => {
    refreshPortfolio();
    refreshWatchlist();
    refreshSnapshots();
  }, [refreshPortfolio, refreshWatchlist, refreshSnapshots]);

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Header */}
      <Header
        totalValue={liveTotalValue}
        cashBalance={portfolio?.cash_balance ?? null}
        connectionStatus={status}
      />

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left column - Watchlist */}
        <div className="w-[320px] flex-shrink-0 border-r border-terminal-border overflow-y-auto">
          <Watchlist
            watchlist={watchlist}
            prices={prices}
            history={history}
            selectedTicker={selectedTicker}
            onSelectTicker={setSelectedTicker}
            onWatchlistChange={refreshWatchlist}
          />
        </div>

        {/* Center column */}
        <div className="flex-1 flex flex-col overflow-hidden min-w-0">
          {/* Top row: Chart + Heatmap */}
          <div className="flex flex-1 min-h-0">
            {/* Main chart */}
            <div className="flex-1 border-b border-terminal-border p-3 min-w-0">
              <MainChart
                ticker={selectedTicker}
                history={history[selectedTicker] || []}
                currentPrice={prices[selectedTicker]?.price}
                changeDirection={prices[selectedTicker]?.change_direction}
              />
            </div>
            {/* Portfolio heatmap */}
            <div className="w-[300px] flex-shrink-0 border-l border-b border-terminal-border p-3">
              <PortfolioHeatmap
                positions={portfolio?.positions || []}
                prices={prices}
              />
            </div>
          </div>

          {/* Bottom row: Positions + P&L + Trade */}
          <div className="h-[280px] flex-shrink-0 flex overflow-hidden">
            {/* Positions table */}
            <div className="flex-1 border-r border-terminal-border overflow-auto p-3">
              <PositionsTable
                positions={portfolio?.positions || []}
                prices={prices}
              />
            </div>
            {/* P&L chart + Trade bar */}
            <div className="w-[380px] flex-shrink-0 flex flex-col">
              <div className="flex-1 border-b border-terminal-border p-3 overflow-hidden">
                <PnLChart snapshots={snapshots} />
              </div>
              <div className="p-3">
                <TradeBar
                  watchlist={watchlist}
                  onTradeComplete={onTradeComplete}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Right column - Chat panel */}
        {chatOpen && (
          <div className="w-[360px] flex-shrink-0 border-l border-terminal-border">
            <ChatPanel
              onClose={() => setChatOpen(false)}
              onActionComplete={onTradeComplete}
            />
          </div>
        )}

        {/* Chat toggle when closed */}
        {!chatOpen && (
          <button
            onClick={() => setChatOpen(true)}
            className="fixed bottom-4 right-4 bg-accent-purple hover:bg-accent-purple/80 text-white px-4 py-2 rounded-lg text-sm font-medium shadow-lg z-50 transition-colors"
          >
            AI Chat
          </button>
        )}
      </div>
    </div>
  );
}
