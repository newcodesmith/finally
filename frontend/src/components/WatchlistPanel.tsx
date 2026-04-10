'use client';

import { useShallow } from 'zustand/react/shallow';
import { usePriceStore } from '@/stores/usePriceStore';
import WatchlistRow from './WatchlistRow';

export default function WatchlistPanel() {
  const tickers = usePriceStore(useShallow((s) => Object.keys(s.prices)));
  const selectedTicker = usePriceStore((s) => s.selectedTicker);
  const setSelectedTicker = usePriceStore((s) => s.setSelectedTicker);

  const sortedTickers = [...tickers].sort();

  return (
    <div className="h-full flex flex-col" data-testid="watchlist">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border">
        <span className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">
          Watchlist
        </span>
      </div>

      {/* Ticker rows */}
      <div className="flex-1 overflow-y-auto">
        {sortedTickers.map((ticker) => (
          <WatchlistRow
            key={ticker}
            ticker={ticker}
            isSelected={ticker === selectedTicker}
            onClick={() => setSelectedTicker(ticker)}
          />
        ))}
      </div>
    </div>
  );
}
