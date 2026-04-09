// ---- Market Data / SSE ----

export interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number | null;
  session_open_price: number | null;
  change_direction: 'up' | 'down' | 'unchanged';
  timestamp: string | null;
  change: number | null;
  change_percent: number | null;
}

// ---- Portfolio ----

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  unrealized_pnl: number;
  pnl_percent: number;
  value: number;
}

export interface Portfolio {
  cash_balance: number;
  positions: Position[];
  total_value: number;
}

export interface PortfolioSnapshot {
  recorded_at: string;
  total_value: number;
}

// ---- Trade ----

export interface TradeRequest {
  ticker: string;
  side: 'buy' | 'sell';
  quantity: number;
}

export interface TradeResponse {
  success: boolean;
  error: string | null;
  ticker: string;
  side: string;
  quantity: number;
  price: number;
  cash_balance: number;
  position: {
    ticker: string;
    quantity: number;
    avg_cost: number;
  } | null;
}

// ---- Watchlist ----

export interface WatchlistItem extends PriceUpdate {}

// ---- Chat ----

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  trades?: ExecutedTrade[];
  watchlist_changes?: WatchlistChange[];
  errors?: string[];
}

export interface ExecutedTrade {
  ticker: string;
  side: string;
  quantity: number;
  price: number;
}

export interface WatchlistChange {
  ticker: string;
  action: string;
  success: boolean;
}

export interface ChatResponse {
  message: string;
  trades: ExecutedTrade[];
  watchlist_changes: WatchlistChange[];
  errors: string[];
}

// ---- Connection ----

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected';
