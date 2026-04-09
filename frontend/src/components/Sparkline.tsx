'use client';

import { useEffect, useRef } from 'react';

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
}

export default function Sparkline({
  data,
  width = 60,
  height = 24,
  color = '#209dd7',
}: SparklineProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, width, height);

    if (data.length < 2) return;

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;

    for (let i = 0; i < data.length; i++) {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((data[i] - min) / range) * height;

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }

    ctx.stroke();
  }, [data, width, height, color]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className="block"
    />
  );
}
