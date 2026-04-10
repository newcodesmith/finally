import { create } from 'zustand';
import type { Position, PortfolioSnapshot, TradeRequest, TradeResponse } from '@/types/portfolio';

interface PortfolioStore {
  cashBalance: number;
  totalValue: number;
  positions: Position[];
  snapshots: PortfolioSnapshot[];
  lastTradeResult: TradeResponse | null;
  isTrading: boolean;

  fetchPortfolio: () => Promise<void>;
  fetchSnapshots: () => Promise<void>;
  executeTrade: (req: TradeRequest) => Promise<TradeResponse>;
}

export const usePortfolioStore = create<PortfolioStore>((set, get) => ({
  cashBalance: 10000,
  totalValue: 10000,
  positions: [],
  snapshots: [],
  lastTradeResult: null,
  isTrading: false,

  fetchPortfolio: async () => {
    try {
      const res = await fetch('/api/portfolio');
      if (res.ok) {
        const json = await res.json();
        set({
          cashBalance: json.cash_balance,
          totalValue: json.total_value,
          positions: json.positions ?? [],
        });
      }
    } catch {
      // Silently fail — keep last known values
    }
  },

  fetchSnapshots: async () => {
    try {
      const res = await fetch('/api/portfolio/history');
      if (res.ok) {
        const json = await res.json();
        set({ snapshots: json });
      }
    } catch {
      // Silently fail — keep last known values
    }
  },

  executeTrade: async (req: TradeRequest) => {
    set({ isTrading: true });
    const errorResponse: TradeResponse = {
      success: false,
      error: 'Network error',
      ticker: req.ticker,
      side: req.side,
      quantity: req.quantity,
      price: 0,
      cash_balance: get().cashBalance,
      position: null,
    };

    try {
      const res = await fetch('/api/portfolio/trade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
      });
      const json: TradeResponse = await res.json();
      set({ lastTradeResult: json, isTrading: false });

      if (json.success) {
        // Refresh portfolio data after successful trade
        get().fetchPortfolio();
      }

      return json;
    } catch {
      set({ lastTradeResult: errorResponse, isTrading: false });
      return errorResponse;
    }
  },
}));
