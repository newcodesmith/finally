'use client';

import type { Position, PriceUpdate } from '@/types';
import { formatUSD, formatPercent } from '@/lib/format';

interface PortfolioHeatmapProps {
  positions: Position[];
  prices: Record<string, PriceUpdate>;
}

interface TreemapRect {
  ticker: string;
  value: number;
  pnlPercent: number;
  x: number;
  y: number;
  w: number;
  h: number;
}

function layoutTreemap(items: { ticker: string; value: number; pnlPercent: number }[], width: number, height: number): TreemapRect[] {
  if (items.length === 0) return [];

  const totalValue = items.reduce((sum, i) => sum + i.value, 0);
  if (totalValue <= 0) return [];

  const sorted = [...items].sort((a, b) => b.value - a.value);
  const rects: TreemapRect[] = [];

  let x = 0;
  let y = 0;
  let remainW = width;
  let remainH = height;
  let isHorizontal = width >= height;

  for (const item of sorted) {
    const ratio = item.value / totalValue;
    let w: number, h: number;

    if (isHorizontal) {
      w = remainW * ratio * (sorted.length / (sorted.length - rects.length));
      w = Math.min(w, remainW);
      h = remainH;
    } else {
      w = remainW;
      h = remainH * ratio * (sorted.length / (sorted.length - rects.length));
      h = Math.min(h, remainH);
    }

    // Simple slice-and-dice
    const fraction = item.value / totalValue;
    if (isHorizontal) {
      w = remainW * fraction;
      h = remainH;
      rects.push({ ...item, x, y, w, h });
      x += w;
      remainW -= w;
    } else {
      w = remainW;
      h = remainH * fraction;
      rects.push({ ...item, x, y, w, h });
      y += h;
      remainH -= h;
    }
  }

  return rects;
}

function getPnlColor(pnlPercent: number): string {
  if (pnlPercent > 3) return 'rgba(63, 185, 80, 0.7)';
  if (pnlPercent > 1) return 'rgba(63, 185, 80, 0.45)';
  if (pnlPercent > 0) return 'rgba(63, 185, 80, 0.25)';
  if (pnlPercent > -1) return 'rgba(248, 81, 73, 0.25)';
  if (pnlPercent > -3) return 'rgba(248, 81, 73, 0.45)';
  return 'rgba(248, 81, 73, 0.7)';
}

export default function PortfolioHeatmap({ positions, prices }: PortfolioHeatmapProps) {
  if (positions.length === 0) {
    return (
      <div className="h-full flex flex-col">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] text-terminal-text-muted uppercase tracking-wider font-semibold">
            Portfolio Map
          </span>
        </div>
        <div className="flex-1 flex items-center justify-center text-terminal-text-dim text-xs text-center px-4">
          No positions yet -- buy something to get started
        </div>
      </div>
    );
  }

  // Compute live values
  const items = positions.map((pos) => {
    const livePrice = prices[pos.ticker]?.price ?? pos.current_price;
    const value = livePrice * pos.quantity;
    const pnlPercent = pos.avg_cost > 0 ? ((livePrice - pos.avg_cost) / pos.avg_cost) * 100 : 0;
    return { ticker: pos.ticker, value, pnlPercent };
  });

  const WIDTH = 260;
  const HEIGHT = 200;
  const rects = layoutTreemap(items, WIDTH, HEIGHT);

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] text-terminal-text-muted uppercase tracking-wider font-semibold">
          Portfolio Map
        </span>
      </div>
      <div className="flex-1 flex items-center justify-center overflow-hidden">
        <svg width={WIDTH} height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`}>
          {rects.map((rect) => (
            <g key={rect.ticker}>
              <rect
                x={rect.x + 1}
                y={rect.y + 1}
                width={Math.max(rect.w - 2, 0)}
                height={Math.max(rect.h - 2, 0)}
                fill={getPnlColor(rect.pnlPercent)}
                rx={2}
              />
              {rect.w > 35 && rect.h > 25 && (
                <>
                  <text
                    x={rect.x + rect.w / 2}
                    y={rect.y + rect.h / 2 - 4}
                    textAnchor="middle"
                    fill="#e6edf3"
                    fontSize="10"
                    fontFamily="JetBrains Mono, monospace"
                    fontWeight="600"
                  >
                    {rect.ticker}
                  </text>
                  <text
                    x={rect.x + rect.w / 2}
                    y={rect.y + rect.h / 2 + 10}
                    textAnchor="middle"
                    fill={rect.pnlPercent >= 0 ? '#3fb950' : '#f85149'}
                    fontSize="8"
                    fontFamily="JetBrains Mono, monospace"
                  >
                    {formatPercent(rect.pnlPercent)}
                  </text>
                </>
              )}
            </g>
          ))}
        </svg>
      </div>
    </div>
  );
}
