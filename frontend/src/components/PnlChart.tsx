'use client';

import { useEffect, useRef } from 'react';
import { usePortfolioStore } from '@/stores/usePortfolioStore';
import type { IChartApi, ISeriesApi, UTCTimestamp } from 'lightweight-charts';

export default function PnlChart() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  const snapshots = usePortfolioStore((s) => s.snapshots);

  // Initialize chart (once)
  useEffect(() => {
    if (!containerRef.current) return;

    let chart: IChartApi | null = null;
    let observer: ResizeObserver | null = null;
    let cancelled = false;

    (async () => {
      const { createChart, ColorType, LineSeries } = await import(
        'lightweight-charts'
      );
      if (cancelled || !containerRef.current) return;

      chart = createChart(containerRef.current, {
        layout: {
          background: { type: ColorType.Solid, color: '#161b22' },
          textColor: '#8b949e',
          fontSize: 10,
        },
        grid: {
          vertLines: { color: '#30363d' },
          horzLines: { color: '#30363d' },
        },
        rightPriceScale: {
          borderColor: '#30363d',
        },
        timeScale: {
          borderColor: '#30363d',
          timeVisible: true,
          secondsVisible: true,
        },
        width: containerRef.current.clientWidth,
        height: containerRef.current.clientHeight,
      });

      const series = chart.addSeries(LineSeries, {
        color: '#209dd7',
        lineWidth: 2,
      });

      chartRef.current = chart;
      seriesRef.current = series;

      observer = new ResizeObserver((entries) => {
        if (!chart || !containerRef.current) return;
        const { width, height } = entries[0].contentRect;
        chart.applyOptions({ width, height });
      });
      observer.observe(containerRef.current);
    })();

    return () => {
      cancelled = true;
      if (observer) observer.disconnect();
      if (chart) chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  // Update chart data when snapshots change
  useEffect(() => {
    if (!seriesRef.current) return;

    if (snapshots.length === 0) {
      seriesRef.current.setData([]);
      return;
    }

    const chartData = snapshots.map((snap) => ({
      time: (new Date(snap.recorded_at).getTime() / 1000) as UTCTimestamp,
      value: snap.total_value,
    }));

    seriesRef.current.setData(chartData);
    chartRef.current?.timeScale().fitContent();
  }, [snapshots]);

  if (snapshots.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-text-secondary text-sm">
        No data yet
      </div>
    );
  }

  return <div ref={containerRef} className="w-full h-full" />;
}
