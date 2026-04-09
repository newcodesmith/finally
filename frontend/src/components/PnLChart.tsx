'use client';

import { useRef, useEffect, useCallback } from 'react';
import { formatUSD } from '@/lib/format';
import type { PortfolioSnapshot } from '@/types';

interface PnLChartProps {
  snapshots: PortfolioSnapshot[];
}

export default function PnLChart({ snapshots }: PnLChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const drawChart = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const rect = container.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    if (snapshots.length < 2) {
      ctx.fillStyle = '#6e7681';
      ctx.font = '10px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText('Collecting data...', width / 2, height / 2);
      return;
    }

    const data = snapshots.map((s) => s.total_value);
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const padding = { top: 8, right: 50, bottom: 8, left: 4 };
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;
    const stepX = chartW / (data.length - 1);

    const isUp = data[data.length - 1] >= data[0];
    const lineColor = isUp ? '#3fb950' : '#f85149';

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
    ctx.fillStyle = isUp ? 'rgba(63, 185, 80, 0.06)' : 'rgba(248, 81, 73, 0.06)';
    ctx.fill();

    // Line
    ctx.beginPath();
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 1.2;
    ctx.lineJoin = 'round';
    data.forEach((val, i) => {
      const x = padding.left + i * stepX;
      const y = padding.top + chartH - ((val - min) / range) * chartH;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Latest value label
    const lastVal = data[data.length - 1];
    const lastY = padding.top + chartH - ((lastVal - min) / range) * chartH;
    ctx.fillStyle = lineColor;
    ctx.font = '9px "JetBrains Mono", monospace';
    ctx.textAlign = 'left';
    ctx.fillText(formatUSD(lastVal), width - padding.right + 4, lastY + 3);
  }, [snapshots]);

  useEffect(() => {
    drawChart();
  }, [drawChart]);

  useEffect(() => {
    const handleResize = () => drawChart();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [drawChart]);

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] text-terminal-text-muted uppercase tracking-wider font-semibold">
          Portfolio Value
        </span>
      </div>
      <div ref={containerRef} className="flex-1 min-h-0">
        <canvas ref={canvasRef} />
      </div>
    </div>
  );
}
