'use client';

import { useEffect, useRef } from 'react';
import { usePriceStore } from '@/stores/usePriceStore';
import { formatPrice } from '@/lib/format';
import type { IChartApi, ISeriesApi, Time, LineSeriesPartialOptions } from 'lightweight-charts';

const EMPTY_ARRAY: number[] = [];

export default function MainChart() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const prevTickerRef = useRef<string | null>(null);

  const selectedTicker = usePriceStore((s) => s.selectedTicker);
  const priceData = usePriceStore((s) => s.prices[s.selectedTicker ?? '']);
  const history = usePriceStore(
    (s) => s.sparklineHistory[s.selectedTicker ?? '']
  ) ?? EMPTY_ARRAY;

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
          background: { type: ColorType.Solid, color: '#0d1117' },
          textColor: '#8b949e',
          fontSize: 11,
        },
        grid: {
          vertLines: { color: '#1c2333' },
          horzLines: { color: '#1c2333' },
        },
        crosshair: {
          vertLine: { color: '#30363d' },
          horzLine: { color: '#30363d' },
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

  // Update chart data when selectedTicker or history changes
  useEffect(() => {
    if (!seriesRef.current || !chartRef.current || history.length === 0) return;

    const baseTime = Math.floor(Date.now() / 1000) - history.length;
    const chartData = history.map((price, i) => ({
      time: (baseTime + i) as Time,
      value: price,
    }));

    seriesRef.current.setData(chartData);

    // Fit content when ticker changes
    if (selectedTicker !== prevTickerRef.current) {
      chartRef.current.timeScale().fitContent();
      prevTickerRef.current = selectedTicker;
    }
  }, [selectedTicker, history]);

  const hasData = selectedTicker && priceData;

  return (
    <div className="flex-1 flex flex-col h-full bg-surface">
      {/* Chart header */}
      <div className="px-4 pt-4 pb-2 flex items-baseline justify-between">
        {hasData ? (
          <>
            <span className="text-[20px] font-semibold text-text-primary">
              {selectedTicker}
            </span>
            <span className="text-[20px] font-semibold text-accent-yellow tabular-nums">
              {formatPrice(priceData.price)}
            </span>
          </>
        ) : (
          <span className="text-text-muted text-sm">
            Waiting for market data...
          </span>
        )}
      </div>

      {/* Chart container */}
      <div className="flex-1 relative mx-4 mb-4" ref={containerRef} />
    </div>
  );
}
