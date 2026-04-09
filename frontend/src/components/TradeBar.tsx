'use client';

import { useState, useCallback } from 'react';
import type { WatchlistItem } from '@/types';
import { executeTrade } from '@/lib/api';

interface TradeBarProps {
  watchlist: WatchlistItem[];
  onTradeComplete: () => void;
}

export default function TradeBar({ watchlist, onTradeComplete }: TradeBarProps) {
  const [ticker, setTicker] = useState('');
  const [quantity, setQuantity] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const handleTrade = useCallback(async (side: 'buy' | 'sell') => {
    const tickerVal = ticker.trim().toUpperCase();
    const qtyVal = parseFloat(quantity);

    if (!tickerVal) {
      setMessage({ text: 'Enter a ticker', type: 'error' });
      return;
    }
    if (isNaN(qtyVal) || qtyVal <= 0) {
      setMessage({ text: 'Enter a valid quantity', type: 'error' });
      return;
    }

    // Validate ticker is in watchlist
    const inWatchlist = watchlist.some((w) => w.ticker === tickerVal);
    if (!inWatchlist) {
      setMessage({ text: `${tickerVal} not in watchlist. Add it first.`, type: 'error' });
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      const result = await executeTrade({ ticker: tickerVal, side, quantity: qtyVal });
      if (result.success) {
        setMessage({
          text: `${side.toUpperCase()} ${qtyVal} ${tickerVal} @ $${result.price.toFixed(2)}`,
          type: 'success',
        });
        setTicker('');
        setQuantity('');
        onTradeComplete();
      } else {
        setMessage({ text: result.error || 'Trade failed', type: 'error' });
      }
    } catch (e) {
      setMessage({ text: 'Trade request failed', type: 'error' });
    } finally {
      setLoading(false);
    }
  }, [ticker, quantity, watchlist, onTradeComplete]);

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] text-terminal-text-muted uppercase tracking-wider font-semibold">
          Trade
        </span>
      </div>
      <div className="flex gap-1.5 items-center">
        <input
          type="text"
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          placeholder="AAPL"
          className="w-20 bg-terminal-bg border border-terminal-border rounded px-2 py-1.5 text-xs text-terminal-text placeholder-terminal-text-dim focus:border-accent-blue focus:outline-none"
        />
        <input
          type="number"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          placeholder="Qty"
          min="0"
          step="1"
          className="w-16 bg-terminal-bg border border-terminal-border rounded px-2 py-1.5 text-xs text-terminal-text placeholder-terminal-text-dim focus:border-accent-blue focus:outline-none"
        />
        <button
          onClick={() => handleTrade('buy')}
          disabled={loading}
          className="px-3 py-1.5 text-[10px] font-semibold bg-price-up/20 text-price-up border border-price-up/30 rounded hover:bg-price-up/30 disabled:opacity-30 transition-colors uppercase"
        >
          Buy
        </button>
        <button
          onClick={() => handleTrade('sell')}
          disabled={loading}
          className="px-3 py-1.5 text-[10px] font-semibold bg-price-down/20 text-price-down border border-price-down/30 rounded hover:bg-price-down/30 disabled:opacity-30 transition-colors uppercase"
        >
          Sell
        </button>
      </div>
      {message && (
        <div className={`mt-1.5 text-[10px] ${message.type === 'success' ? 'text-price-up' : 'text-price-down'}`}>
          {message.text}
        </div>
      )}
    </div>
  );
}
