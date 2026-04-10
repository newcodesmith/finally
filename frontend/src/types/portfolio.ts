export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  unrealized_pnl: number;
  pnl_percent: number;
  value: number;
}

export interface PortfolioSnapshot {
  id: string;
  user_id: string;
  total_value: number;
  recorded_at: string;
}

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
  position: { ticker: string; quantity: number; avg_cost: number } | null;
}
