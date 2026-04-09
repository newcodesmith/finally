'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import type { PriceUpdate, WatchlistItem } from '@/types';
import { addToWatchlist, removeFromWatchlist } from '@/lib/api';
import { formatPrice, formatPercent } from '@/lib/format';
import Sparkline from './Sparkline';

interface WatchlistProps {
  watchlist: WatchlistItem[];
  prices: Record<string, PriceUpdate>;
  history: Record<string, number[]>;
  selectedTicker: string;
  onSelectTicker: (ticker: string) => void;
  onWatchlistChange: () => void;
}

export default function Watchlist({
  watchlist,
  prices,
  history,
  selectedTicker,
  onSelectTicker,
  onWatchlistChange,
}: WatchlistProps) {
  const [addInput, setAddInput] = useState('');
  const [adding, setAdding] = useState(false);
  // Track previous prices for flash animation
  const prevPricesRef = useRef<Record<string, number>>({});
  const [flashKeys, setFlashKeys] = useState<Record<string, 'up' | 'down'>>({});

  // Detect price changes and trigger flash
  useEffect(() => {
    const newFlashes: Record<string, 'up' | 'down'> = {};
    for (const [ticker, update] of Object.entries(prices)) {
      const prev = prevPricesRef.current[ticker];
      if (prev !== undefined && prev !== update.price) {
        newFlashes[ticker] = update.price > prev ? 'up' : 'down';
      }
      prevPricesRef.current[ticker] = update.price;
    }
    if (Object.keys(newFlashes).length > 0) {
      setFlashKeys(newFlashes);
      const timer = setTimeout(() => setFlashKeys({}), 500);
      return () => clearTimeout(timer);
    }
  }, [prices]);

  const handleAdd = useCallback(async () => {
    const ticker = addInput.trim().toUpperCase();
    if (!ticker) return;
    setAdding(true);
    try {
      await addToWatchlist(ticker);
      setAddInput('');
      onWatchlistChange();
    } catch (e) {
      console.error('Failed to add ticker:', e);
    } finally {
      setAdding(false);
    }
  }, [addInput, onWatchlistChange]);

  const handleRemove = useCallback(async (ticker: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await removeFromWatchlist(ticker);
      onWatchlistChange();
    } catch (err) {
      console.error('Failed to remove ticker:', err);
    }
  }, [onWatchlistChange]);

  // Merge watchlist items with live SSE prices
  const tickers = watchlist.map((item) => {
    const live = prices[item.ticker];
    return live || item;
  });

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-3 py-2 border-b border-terminal-border flex items-center justify-between">
        <span className="text-[10px] text-terminal-text-muted uppercase tracking-wider font-semibold">
          Watchlist
        </span>
        <span className="text-[10px] text-terminal-text-dim">{tickers.length} tickers</span>
      </div>

      {/* Add ticker input */}
      <div className="px-3 py-2 border-b border-terminal-border flex gap-1">
        <input
          type="text"
          value={addInput}
          onChange={(e) => setAddInput(e.target.value.toUpperCase())}
          onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
          placeholder="Add ticker..."
          className="flex-1 bg-terminal-bg border border-terminal-border rounded px-2 py-1 text-xs text-terminal-text placeholder-terminal-text-dim focus:border-accent-blue focus:outline-none"
        />
        <button
          onClick={handleAdd}
          disabled={adding || !addInput.trim()}
          className="px-2 py-1 text-[10px] bg-accent-blue/20 text-accent-blue rounded hover:bg-accent-blue/30 disabled:opacity-30 transition-colors"
        >
          +
        </button>
      </div>

      {/* Ticker list */}
      <div className="flex-1 overflow-y-auto">
        {tickers.map((item) => {
          const isSelected = item.ticker === selectedTicker;
          const flashClass = flashKeys[item.ticker]
            ? flashKeys[item.ticker] === 'up'
              ? 'flash-up'
              : 'flash-down'
            : '';
          const changePercent = item.change_percent;
          const dirColor =
            item.change_direction === 'up'
              ? 'text-price-up'
              : item.change_direction === 'down'
              ? 'text-price-down'
              : 'text-terminal-text-muted';

          return (
            <div
              key={item.ticker}
              onClick={() => onSelectTicker(item.ticker)}
              className={`
                px-3 py-2 cursor-pointer border-b border-terminal-border/50 transition-colors
                flex items-center gap-2
                ${isSelected ? 'bg-terminal-panel border-l-2 border-l-accent-blue' : 'hover:bg-terminal-surface'}
                ${flashClass}
              `}
            >
              {/* Ticker symbol */}
              <div className="flex-shrink-0 w-14">
                <div className="text-xs font-semibold text-terminal-text">{item.ticker}</div>
              </div>

              {/* Sparkline */}
              <div className="flex-shrink-0">
                <Sparkline data={history[item.ticker] || []} width={80} height={24} />
              </div>

              {/* Price + Change */}
              <div className="flex-1 text-right">
                <div className="text-xs font-medium text-terminal-text">
                  {item.price !== null ? `$${formatPrice(item.price)}` : '---'}
                </div>
                <div className={`text-[10px] ${dirColor}`}>
                  {changePercent !== null ? formatPercent(changePercent) : '---'}
                </div>
              </div>

              {/* Remove button */}
              <button
                onClick={(e) => handleRemove(item.ticker, e)}
                className="flex-shrink-0 w-4 h-4 flex items-center justify-center text-terminal-text-dim hover:text-price-down text-[10px] opacity-0 group-hover:opacity-100 transition-opacity"
                style={{ opacity: isSelected ? 0.6 : 0 }}
                onMouseEnter={(e) => (e.currentTarget.style.opacity = '1')}
                onMouseLeave={(e) => (e.currentTarget.style.opacity = isSelected ? '0.6' : '0')}
              >
                x
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
