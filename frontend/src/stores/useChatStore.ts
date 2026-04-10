import { create } from 'zustand';
import type { ChatMessage, ChatApiResponse } from '@/types/chat';
import { usePortfolioStore } from '@/stores/usePortfolioStore';

interface ChatStore {
  messages: ChatMessage[];
  isLoading: boolean;
  isOpen: boolean;
  sendMessage: (text: string) => Promise<void>;
  toggleOpen: () => void;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  isLoading: false,
  isOpen: false,

  sendMessage: async (text: string) => {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };

    set({ messages: [...get().messages, userMessage], isLoading: true });

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data: ChatApiResponse = await res.json();

      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.message,
        actions: {
          trades: data.trades ?? [],
          watchlist_changes: data.watchlist_changes ?? [],
          errors: data.errors ?? [],
        },
        timestamp: new Date().toISOString(),
      };

      set({ messages: [...get().messages, assistantMessage], isLoading: false });

      // Refresh portfolio data if trades were executed
      if (data.trades && data.trades.length > 0) {
        usePortfolioStore.getState().fetchPortfolio();
      }
    } catch {
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
        timestamp: new Date().toISOString(),
      };

      set({ messages: [...get().messages, errorMessage], isLoading: false });
    }
  },

  toggleOpen: () => set({ isOpen: !get().isOpen }),
}));
