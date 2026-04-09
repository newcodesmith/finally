'use client';

import { useEffect, useRef } from 'react';
import { usePriceStore } from '@/stores/usePriceStore';
import type { PriceUpdate } from '@/types/market';

export function useSSE() {
  const errorCount = useRef(0);

  useEffect(() => {
    const es = new EventSource('/api/stream/prices');

    es.onopen = () => {
      errorCount.current = 0;
      usePriceStore.getState().setConnectionStatus('connected');
    };

    es.onmessage = (event: MessageEvent) => {
      try {
        const data: Record<string, PriceUpdate> = JSON.parse(event.data);
        usePriceStore.getState().updatePrices(data);
      } catch {
        // Malformed SSE data — ignore
      }
    };

    es.onerror = () => {
      errorCount.current += 1;
      if (errorCount.current >= 5) {
        usePriceStore.getState().setConnectionStatus('disconnected');
      } else {
        usePriceStore.getState().setConnectionStatus('reconnecting');
      }
    };

    return () => {
      es.close();
      usePriceStore.getState().setConnectionStatus('disconnected');
    };
  }, []);
}
