'use client';

import type { Position, PriceUpdate } from '@/types';
import { formatPrice, formatUSD, formatPercent, pnlColor } from '@/lib/format';

interface PositionsTableProps {
  positions: Position[];
  prices: Record<string, PriceUpdate>;
}

export default function PositionsTable({ positions, prices }: PositionsTableProps) {
  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] text-terminal-text-muted uppercase tracking-wider font-semibold">
          Positions
        </span>
        <span className="text-[10px] text-terminal-text-dim">{positions.length} open</span>
      </div>

      {positions.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-terminal-text-dim text-xs">
          No open positions
        </div>
      ) : (
        <div className="flex-1 overflow-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-terminal-text-muted text-[10px] uppercase border-b border-terminal-border">
                <th className="text-left py-1 pr-2 font-medium">Ticker</th>
                <th className="text-right py-1 pr-2 font-medium">Qty</th>
                <th className="text-right py-1 pr-2 font-medium">Avg Cost</th>
                <th className="text-right py-1 pr-2 font-medium">Price</th>
                <th className="text-right py-1 pr-2 font-medium">P&L</th>
                <th className="text-right py-1 font-medium">%</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((pos) => {
                const livePrice = prices[pos.ticker]?.price ?? pos.current_price;
                const pnl = (livePrice - pos.avg_cost) * pos.quantity;
                const pnlPct = pos.avg_cost > 0 ? ((livePrice - pos.avg_cost) / pos.avg_cost) * 100 : 0;

                return (
                  <tr
                    key={pos.ticker}
                    className="border-b border-terminal-border/30 hover:bg-terminal-surface/50"
                  >
                    <td className="py-1.5 pr-2 font-semibold text-terminal-text">{pos.ticker}</td>
                    <td className="py-1.5 pr-2 text-right text-terminal-text-muted">
                      {pos.quantity % 1 === 0 ? pos.quantity : pos.quantity.toFixed(2)}
                    </td>
                    <td className="py-1.5 pr-2 text-right text-terminal-text-muted">
                      ${formatPrice(pos.avg_cost)}
                    </td>
                    <td className="py-1.5 pr-2 text-right text-terminal-text">
                      ${formatPrice(livePrice)}
                    </td>
                    <td className={`py-1.5 pr-2 text-right font-medium ${pnlColor(pnl)}`}>
                      {pnl >= 0 ? '+' : ''}{formatUSD(pnl).replace('$', '$')}
                    </td>
                    <td className={`py-1.5 text-right ${pnlColor(pnlPct)}`}>
                      {formatPercent(pnlPct)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
