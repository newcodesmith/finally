import { create } from 'zustand';
import type { PriceUpdate, ConnectionStatus } from '@/types/market';

const MAX_SPARKLINE_POINTS = 120;

interface PriceStore {
  prices: Record<string, PriceUpdate>;
  sparklineHistory: Record<string, number[]>;
  connectionStatus: ConnectionStatus;
  selectedTicker: string | null;
  updatePrices: (data: Record<string, PriceUpdate>) => void;
  setSelectedTicker: (ticker: string) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
}

export const usePriceStore = create<PriceStore>((set, get) => ({
  prices: {},
  sparklineHistory: {},
  connectionStatus: 'disconnected',
  selectedTicker: null,

  updatePrices: (data) => {
    const current = get();
    const newPrices = { ...current.prices };
    const newHistory = { ...current.sparklineHistory };

    for (const [ticker, update] of Object.entries(data)) {
      newPrices[ticker] = update;
      const history = newHistory[ticker] ? [...newHistory[ticker]] : [];
      history.push(update.price);
      if (history.length > MAX_SPARKLINE_POINTS) {
        history.shift();
      }
      newHistory[ticker] = history;
    }

    // Auto-select first ticker if none selected
    const selectedTicker = current.selectedTicker ?? Object.keys(data)[0] ?? null;

    set({ prices: newPrices, sparklineHistory: newHistory, selectedTicker });
  },

  setSelectedTicker: (ticker) => set({ selectedTicker: ticker }),
  setConnectionStatus: (status) => set({ connectionStatus: status }),
}));
