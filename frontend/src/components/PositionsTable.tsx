'use client';

import { usePortfolioStore } from '@/stores/usePortfolioStore';
import { formatPrice, formatPercent } from '@/lib/format';

function formatQuantity(qty: number): string {
  const fixed = qty.toFixed(4);
  return parseFloat(fixed).toString();
}

export default function PositionsTable() {
  const positions = usePortfolioStore((s) => s.positions);

  if (positions.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-text-muted text-sm">
        No positions
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-surface-raised">
          <tr className="text-text-muted uppercase tracking-wider border-b border-border">
            <th className="text-left px-2 py-1.5 font-medium">Ticker</th>
            <th className="text-right px-2 py-1.5 font-medium">Qty</th>
            <th className="text-right px-2 py-1.5 font-medium">Avg Cost</th>
            <th className="text-right px-2 py-1.5 font-medium">Price</th>
            <th className="text-right px-2 py-1.5 font-medium">P&L ($)</th>
            <th className="text-right px-2 py-1.5 font-medium">P&L (%)</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((pos) => {
            const pnlColor =
              pos.unrealized_pnl > 0
                ? 'text-semantic-up'
                : pos.unrealized_pnl < 0
                  ? 'text-semantic-down'
                  : 'text-text-secondary';
            const pnlPrefix = pos.unrealized_pnl > 0 ? '+' : '';

            return (
              <tr
                key={pos.ticker}
                className="border-b border-border hover:bg-surface-hover"
              >
                <td className="text-left px-2 py-1.5 text-text-primary font-semibold">
                  {pos.ticker}
                </td>
                <td className="text-right px-2 py-1.5 text-text-secondary tabular-nums">
                  {formatQuantity(pos.quantity)}
                </td>
                <td className="text-right px-2 py-1.5 text-text-secondary tabular-nums">
                  {formatPrice(pos.avg_cost)}
                </td>
                <td className="text-right px-2 py-1.5 text-text-primary tabular-nums">
                  {formatPrice(pos.current_price)}
                </td>
                <td className={`text-right px-2 py-1.5 tabular-nums ${pnlColor}`}>
                  {pnlPrefix}{formatPrice(pos.unrealized_pnl)}
                </td>
                <td className={`text-right px-2 py-1.5 tabular-nums ${pnlColor}`}>
                  {formatPercent(pos.pnl_percent)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
