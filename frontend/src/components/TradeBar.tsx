'use client';

import { useState, useEffect, useRef } from 'react';
import { usePortfolioStore } from '@/stores/usePortfolioStore';
import { formatPrice } from '@/lib/format';

export default function TradeBar() {
  const [ticker, setTicker] = useState('');
  const [quantity, setQuantity] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);
  const [feedbackType, setFeedbackType] = useState<'success' | 'error' | null>(null);
  const isTrading = usePortfolioStore((s) => s.isTrading);
  const feedbackTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (feedbackTimer.current) clearTimeout(feedbackTimer.current);
    };
  }, []);

  const handleTrade = async (side: 'buy' | 'sell') => {
    const qty = parseFloat(quantity);
    if (!ticker || !qty || qty <= 0) return;

    const result = await usePortfolioStore.getState().executeTrade({
      ticker,
      side,
      quantity: qty,
    });

    if (result.success) {
      const action = side === 'buy' ? 'Bought' : 'Sold';
      setFeedback(`${action} ${qty} ${ticker} @ ${formatPrice(result.price)}`);
      setFeedbackType('success');
      setTicker('');
      setQuantity('');
    } else {
      setFeedback(result.error ?? 'Trade failed');
      setFeedbackType('error');
    }

    if (feedbackTimer.current) clearTimeout(feedbackTimer.current);
    feedbackTimer.current = setTimeout(() => {
      setFeedback(null);
      setFeedbackType(null);
    }, 3000);
  };

  const isDisabled = isTrading || !ticker || !quantity || parseFloat(quantity) <= 0;

  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-surface-raised border-t border-border">
      <input
        type="text"
        value={ticker}
        onChange={(e) => setTicker(e.target.value.toUpperCase())}
        placeholder="Ticker"
        className="w-20 px-2 py-1 text-xs bg-surface border border-border rounded text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-blue"
      />
      <input
        type="number"
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        placeholder="Qty"
        min={0}
        step={1}
        className="w-20 px-2 py-1 text-xs bg-surface border border-border rounded text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-blue tabular-nums"
      />
      <button
        onClick={() => handleTrade('buy')}
        disabled={isDisabled}
        className="px-3 py-1 text-xs font-semibold text-white bg-semantic-up rounded hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        Buy
      </button>
      <button
        onClick={() => handleTrade('sell')}
        disabled={isDisabled}
        className="px-3 py-1 text-xs font-semibold text-white bg-semantic-down rounded hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        Sell
      </button>
      {feedback && (
        <span
          className={`text-xs ml-2 ${
            feedbackType === 'success' ? 'text-semantic-up' : 'text-semantic-down'
          }`}
        >
          {feedback}
        </span>
      )}
    </div>
  );
}
