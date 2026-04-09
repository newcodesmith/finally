'use client';

import { useRef, useEffect } from 'react';

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
}

export default function Sparkline({
  data,
  width = 80,
  height = 24,
  color = '#209dd7',
}: SparklineProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || data.length < 2) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, width, height);

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const padding = 2;
    const chartHeight = height - padding * 2;
    const stepX = (width - 2) / (data.length - 1);

    // Determine color based on trend
    const isUp = data[data.length - 1] >= data[0];
    const lineColor = isUp ? '#3fb950' : '#f85149';

    ctx.beginPath();
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 1.2;
    ctx.lineJoin = 'round';

    data.forEach((val, i) => {
      const x = 1 + i * stepX;
      const y = padding + chartHeight - ((val - min) / range) * chartHeight;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });

    ctx.stroke();
  }, [data, width, height, color]);

  if (data.length < 2) {
    return <div style={{ width, height }} className="opacity-30 flex items-center justify-center text-[8px] text-terminal-text-dim">---</div>;
  }

  return <canvas ref={canvasRef} style={{ width, height }} />;
}
