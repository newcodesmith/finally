'use client';

import { usePortfolioStore } from '@/stores/usePortfolioStore';
import { formatPercent } from '@/lib/format';

export default function PortfolioHeatmap() {
  const positions = usePortfolioStore((s) => s.positions);

  if (positions.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-text-secondary text-sm">
        No positions yet &mdash; buy something to get started
      </div>
    );
  }

  const totalPositionValue = positions.reduce((sum, p) => sum + p.value, 0);

  return (
    <div className="flex flex-wrap h-full p-1 gap-1 content-start">
      {positions.map((position) => {
        const weight = totalPositionValue > 0 ? position.value / totalPositionValue : 0;
        const isPositive = position.unrealized_pnl > 0;
        const isNegative = position.unrealized_pnl < 0;

        let bgColor: string;
        if (isPositive) {
          bgColor = 'rgba(38, 166, 65, 0.3)';
        } else if (isNegative) {
          bgColor = 'rgba(248, 81, 73, 0.3)';
        } else {
          bgColor = 'var(--color-surface-hover)';
        }

        return (
          <div
            key={position.ticker}
            className="flex flex-col items-center justify-center rounded"
            style={{
              flexBasis: `${Math.max(weight * 100, 8)}%`,
              minWidth: 60,
              height: 80,
              backgroundColor: bgColor,
            }}
          >
            <span className="text-text-primary font-semibold text-sm">
              {position.ticker}
            </span>
            <span
              className={`text-xs tabular-nums ${
                isPositive
                  ? 'text-semantic-up'
                  : isNegative
                    ? 'text-semantic-down'
                    : 'text-text-muted'
              }`}
            >
              {formatPercent(position.pnl_percent)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
