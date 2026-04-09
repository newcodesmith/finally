'use client';

import { useRef, useEffect, useCallback } from 'react';
import { formatPrice } from '@/lib/format';

interface MainChartProps {
  ticker: string;
  history: number[];
  currentPrice?: number;
  changeDirection?: 'up' | 'down' | 'unchanged';
}

export default function MainChart({ ticker, history, currentPrice, changeDirection }: MainChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const drawChart = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const rect = container.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height - 32; // Leave room for header

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    if (history.length < 2) {
      ctx.fillStyle = '#8b949e';
      ctx.font = '12px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText('Waiting for price data...', width / 2, height / 2);
      return;
    }

    const data = history;
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const padding = { top: 20, right: 60, bottom: 30, left: 10 };
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;
    const stepX = chartW / (data.length - 1);

    const isUp = data[data.length - 1] >= data[0];
    const lineColor = isUp ? '#3fb950' : '#f85149';
    const fillColor = isUp ? 'rgba(63, 185, 80, 0.08)' : 'rgba(248, 81, 73, 0.08)';

    // Grid lines
    ctx.strokeStyle = '#21262d';
    ctx.lineWidth = 0.5;
    const gridLines = 5;
    for (let i = 0; i <= gridLines; i++) {
      const y = padding.top + (chartH / gridLines) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();

      // Price labels on right
      const priceVal = max - (range / gridLines) * i;
      ctx.fillStyle = '#6e7681';
      ctx.font = '9px "JetBrains Mono", monospace';
      ctx.textAlign = 'left';
      ctx.fillText(`$${formatPrice(priceVal)}`, width - padding.right + 5, y + 3);
    }

    // Fill area
    ctx.beginPath();
    ctx.moveTo(padding.left, padding.top + chartH);
    data.forEach((val, i) => {
      const x = padding.left + i * stepX;
      const y = padding.top + chartH - ((val - min) / range) * chartH;
      ctx.lineTo(x, y);
    });
    ctx.lineTo(padding.left + (data.length - 1) * stepX, padding.top + chartH);
    ctx.closePath();
    ctx.fillStyle = fillColor;
    ctx.fill();

    // Price line
    ctx.beginPath();
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 1.5;
    ctx.lineJoin = 'round';
    data.forEach((val, i) => {
      const x = padding.left + i * stepX;
      const y = padding.top + chartH - ((val - min) / range) * chartH;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Current price dot
    const lastX = padding.left + (data.length - 1) * stepX;
    const lastY = padding.top + chartH - ((data[data.length - 1] - min) / range) * chartH;
    ctx.beginPath();
    ctx.arc(lastX, lastY, 3, 0, Math.PI * 2);
    ctx.fillStyle = lineColor;
    ctx.fill();

    // Dashed line from last point to right edge
    ctx.beginPath();
    ctx.setLineDash([3, 3]);
    ctx.strokeStyle = lineColor + '60';
    ctx.lineWidth = 1;
    ctx.moveTo(lastX, lastY);
    ctx.lineTo(width - padding.right, lastY);
    ctx.stroke();
    ctx.setLineDash([]);
  }, [history]);

  useEffect(() => {
    drawChart();
  }, [drawChart]);

  useEffect(() => {
    const handleResize = () => drawChart();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [drawChart]);

  const priceColor =
    changeDirection === 'up'
      ? 'text-price-up'
      : changeDirection === 'down'
      ? 'text-price-down'
      : 'text-terminal-text';

  return (
    <div ref={containerRef} className="h-full flex flex-col">
      {/* Chart header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold text-terminal-text">{ticker}</span>
          {currentPrice !== undefined && (
            <span className={`text-sm font-semibold ${priceColor}`}>
              ${formatPrice(currentPrice)}
            </span>
          )}
        </div>
        <span className="text-[10px] text-terminal-text-dim uppercase">Session Chart</span>
      </div>
      {/* Chart canvas */}
      <div className="flex-1 min-h-0">
        <canvas ref={canvasRef} />
      </div>
    </div>
  );
}
