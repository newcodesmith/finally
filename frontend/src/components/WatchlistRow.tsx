'use client';

import { usePriceStore } from '@/stores/usePriceStore';
import PriceCell from './PriceCell';
import ChangePercent from './ChangePercent';
import Sparkline from './Sparkline';

interface WatchlistRowProps {
  ticker: string;
  isSelected: boolean;
  onClick: () => void;
}

export default function WatchlistRow({ ticker, isSelected, onClick }: WatchlistRowProps) {
  const priceData = usePriceStore((s) => s.prices[ticker]);
  const sparklineData = usePriceStore((s) => s.sparklineHistory[ticker] ?? []);

  const sessionChange =
    priceData && priceData.session_open_price
      ? ((priceData.price - priceData.session_open_price) / priceData.session_open_price) * 100
      : 0;

  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex items-center w-full gap-3 py-2 px-4 border-b border-border text-left transition-colors hover:bg-surface-hover ${
        isSelected ? 'bg-surface-hover border-l-2 border-l-accent-yellow' : ''
      }`}
    >
      {/* Ticker symbol */}
      <span className="text-[13px] font-semibold text-text-primary min-w-[48px] shrink-0">
        {ticker}
      </span>

      {/* Price */}
      {priceData ? (
        <PriceCell price={priceData.price} changeDirection={priceData.change_direction} />
      ) : (
        <span className="text-[13px] text-text-muted tabular-nums">--</span>
      )}

      {/* Session change % */}
      <ChangePercent value={sessionChange} />

      {/* Sparkline */}
      <div className="ml-auto shrink-0">
        <Sparkline data={sparklineData} />
      </div>
    </button>
  );
}
