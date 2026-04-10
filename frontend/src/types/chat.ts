export interface ExecutedTrade {
  ticker: string;
  side: string;
  quantity: number;
  price: number;
}

export interface WatchlistChangeResult {
  ticker: string;
  action: string;
  success: boolean;
}

export interface ChatActions {
  trades: ExecutedTrade[];
  watchlist_changes: WatchlistChangeResult[];
  errors: string[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  actions?: ChatActions;
  timestamp: string;
}

export interface ChatApiResponse {
  message: string;
  trades: ExecutedTrade[];
  watchlist_changes: WatchlistChangeResult[];
  errors: string[];
}
